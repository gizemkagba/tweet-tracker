import os
import json
import asyncio
import urllib.parse
from playwright.async_api import async_playwright

COOKIES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "playwright_cookies.json")

def parse_num(text):
    if not text:
        return 0
    text = text.lower().strip()
    try:
        # e.g., "4.2k" or "4,200" or just "42"
        text = text.replace(',', '').replace('.', '')
        if 'k' in text:
            return int(float(text.replace('k', '')) * 1000)
        if 'm' in text:
            return int(float(text.replace('m', '')) * 1000000)
        return int(''.join(filter(str.isdigit, text)) or 0)
    except:
        return 0

def launch_real_chrome():
    import subprocess
    import os
    import time
    
    # Kill any existing chrome debugging instances first to avoid conflict
    try:
        os.system("pkill -f 'Google Chrome --remote-debugging-port=9222'")
        time.sleep(1)
    except:
        pass
        
    chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    user_data_dir = os.path.join(os.path.expanduser("~"), ".chrome_dev_profile")
    
    cmd = [
        chrome_path,
        "--remote-debugging-port=9222",
        f"--user-data-dir={user_data_dir}",
        "--no-first-run",
        "--no-default-browser-check"
    ]
    
    process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)  # Give it time to start up and bind to port
    return process

async def login_x(username, password, email, progress_callback=None):
    if progress_callback:
        progress_callback(10, 100, "Gerçek Google Chrome tarayıcısı başlatılıyor...")
        
    # Start actual system Chrome in debugging mode
    chrome_proc = launch_real_chrome()
    
    async with async_playwright() as p:
        try:
            # Connect to the running Chrome instance over CDP (CDP bypasses macOS automation permission restrictions completely!)
            browser = await p.chromium.connect_over_cdp("http://localhost:9222")
            context = browser.contexts[0]
            page = context.pages[0] if context.pages else await context.new_page()
            
            if progress_callback:
                progress_callback(30, 100, "X Giriş Sayfasına gidiliyor...")
            await page.goto("https://x.com/i/flow/login")
            
            success = False
            
            for attempt in range(60):  # Check every 2 seconds for 120 seconds
                await asyncio.sleep(2)
                
                try:
                    # Check if we successfully reached the home page
                    if await page.query_selector('[data-testid="SideNav_NewTweet_Button"], [data-testid="SearchBox_Search_Input"]'):
                        # Save storage state (cookies + localStorage)
                        await context.storage_state(path=COOKIES_FILE)
                        if progress_callback:
                            progress_callback(100, 100, "Giriş Başarılı! Oturum çerezleri kaydedildi.")
                        success = True
                        break
                    
                    # 2. For ALL pages (especially security/knowledge check steps):
                    # Dispatch event triggers on whatever text the user OR browser has filled,
                    # ensuring that next/continue buttons turn active/black immediately!
                    # Note: We NEVER clear or type text here, so we never conflict with what the user is typing!
                    await page.evaluate("""() => {
                        document.querySelectorAll('input').forEach(input => {
                            if (input.value && input.value.trim() !== "") {
                                input.dispatchEvent(new Event('input', { bubbles: true }));
                                input.dispatchEvent(new Event('change', { bubbles: true }));
                            }
                        });
                    }""")
                    
                    # 3. Automatically click enabled "Devam Et", "Next", "Log in" buttons
                    next_button = await page.query_selector('button:has-text("Devam Et"), button:has-text("Next"), button:has-text("Log in"), button:has-text("Giriş yap"), button:has-text("Giriş Yap")')
                    if next_button and await next_button.is_visible():
                        is_disabled = await next_button.is_disabled()
                        if not is_disabled:
                            await next_button.click()
                            
                except Exception as loop_err:
                    # Log or ignore transient errors (element detached, not editable, etc.)
                    pass
                        
            if not success:
                raise Exception("Giriş işlemi zaman aşımına uğradı (120 saniye içinde Twitter anasayfasına ulaşılamadı).")
        finally:
            # Terminate Chrome process safely
            try:
                chrome_proc.terminate()
            except:
                pass

async def search_x_playwright(keyword, start_date=None, end_date=None, limit=None, progress_callback=None):
    # If no limit is specified, set a large target limit (e.g., 10000 tweets) to get everything in the date range
    target_limit = limit if limit is not None else 10000
    
    if not os.path.exists(COOKIES_FILE):
        raise Exception("Giriş oturumu bulunamadı. Lütfen önce Ayarlar sekmesinden giriş yapın.")
        
    if progress_callback:
        progress_callback(10, 100, "Canlı arama modülü başlatılıyor...")
        
    tweets_data = []
    
    async with async_playwright() as p:
        # Run search in headless mode so it runs quietly in the background!
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(storage_state=COOKIES_FILE)
        page = await context.new_page()
        
        # Build search query
        query = keyword
        if start_date and end_date:
            query = f"{keyword} since:{start_date} until:{end_date}"
            
        url = f"https://x.com/search?q={urllib.parse.quote(query)}&f=live"
        
        if progress_callback:
            progress_callback(30, 100, f"'{keyword}' araması için canlı X.com sayfasına gidiliyor...")
            
        await page.goto(url)
        
        # Check if we are redirected to login (session expired)
        await asyncio.sleep(3)
        if "login" in page.url:
            await browser.close()
            # Delete expired cookies
            if os.path.exists(COOKIES_FILE):
                os.remove(COOKIES_FILE)
            raise Exception("Giriş oturumu zaman aşımına uğramış. Lütfen Ayarlar sekmesinden tekrar giriş yapın.")
            
        try:
            await page.wait_for_selector('article[data-testid="tweet"]', timeout=15000)
        except Exception as e:
            await browser.close()
            # If no tweets are found, return empty list
            return []
            
        if progress_callback:
            progress_callback(50, 100, "Tweetler taranıyor...")
            
        seen_ids = set()
        scroll_attempts = 0
        max_scroll_attempts = 150  # Up to 150 scrolls (~3000+ tweets) to allow deep fetches
        no_new_tweets_count = 0
        
        while len(tweets_data) < target_limit and scroll_attempts < max_scroll_attempts:
            # Batch extract all tweets in one single browser evaluation (extremely fast!)
            raw_tweets = await page.evaluate("""() => {
                return Array.from(document.querySelectorAll('article[data-testid="tweet"]')).map(el => {
                    const link = el.querySelector('a[href*="/status/"]');
                    const userEl = el.querySelector('[data-testid="User-Name"]');
                    const timeEl = el.querySelector('time');
                    const textEl = el.querySelector('[data-testid="tweetText"]');
                    const likeEl = el.querySelector('[data-testid="like"]');
                    const rtEl = el.querySelector('[data-testid="retweet"]');
                    const replyEl = el.querySelector('[data-testid="reply"]');
                    
                    return {
                        tweet_id: link ? link.getAttribute('href').split('/status/')[1].split('?')[0] : null,
                        author_name: userEl ? userEl.innerText.split('\\n')[0] : '',
                        author_handle: userEl ? (userEl.innerText.split('\\n')[1] || '') : '',
                        created_at: timeEl ? timeEl.getAttribute('datetime') : '',
                        text: textEl ? textEl.innerText : '',
                        likes_text: likeEl ? likeEl.innerText : '0',
                        rt_text: rtEl ? rtEl.innerText : '0',
                        reply_text: replyEl ? replyEl.innerText : '0'
                    };
                });
            }""")
            
            new_found = False
            
            for t in raw_tweets:
                try:
                    tweet_id = t['tweet_id']
                    if not tweet_id or tweet_id in seen_ids:
                        continue
                        
                    seen_ids.add(tweet_id)
                    new_found = True
                    
                    # Parse numbers and analyze sentiment
                    likes = parse_num(t['likes_text'])
                    retweets = parse_num(t['rt_text'])
                    replies = parse_num(t['reply_text'])
                    tweet_text = t['text']
                    
                    # Simple sentiment analysis
                    text_lower = tweet_text.lower()
                    pos_words = ["harika", "güzel", "iyi", "başarılı", "tebrik", "kazandı", "mutlu", "seviyorum", "yükseldi", "arttı", "mükemmel"]
                    neg_words = ["kötü", "başarısız", "kaybetti", "üzgün", "nefret", "düştü", "azaldı", "enflasyon", "kriz", "felaket", "berbat", "yazık"]
                    
                    pos_count = sum(1 for w in pos_words if w in text_lower)
                    neg_count = sum(1 for w in neg_words if w in text_lower)
                    
                    if pos_count > neg_count:
                        score = 0.5
                        label = "Positive"
                    elif neg_count > pos_count:
                        score = -0.5
                        label = "Negative"
                    else:
                        score = 0.0
                        label = "Neutral"
                        
                    tweets_data.append({
                        'tweet_id': tweet_id,
                        'created_at': t['created_at'],
                        'author_name': t['author_name'],
                        'author_handle': t['author_handle'],
                        'text': tweet_text,
                        'likes': likes,
                        'retweets': retweets,
                        'replies': replies,
                        'keyword': keyword,
                        'sentiment_score': score,
                        'sentiment_label': label
                    })
                    
                    if len(tweets_data) >= target_limit:
                        break
                        
                except Exception as e:
                    continue
            
            if len(tweets_data) >= target_limit:
                break
                
            if not new_found:
                no_new_tweets_count += 1
            else:
                no_new_tweets_count = 0  # Reset on progress
                
            # If we scrolled 5 times consecutively and found absolutely no new tweets, 
            # we have reached the end of the results range!
            if no_new_tweets_count >= 5:
                break
                
            # Scroll down to load more
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            scroll_attempts += 1
            await asyncio.sleep(1.2)  # Reduced from 2.5s to 1.2s for double performance!
            
            if progress_callback:
                progress_callback(50 + min(int((scroll_attempts / max_scroll_attempts) * 45), 45), 100, f"Tweetler taranıyor ({len(tweets_data)} tweet bulundu)...")
                
        await browser.close()
        
    return tweets_data
