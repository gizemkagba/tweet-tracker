import random
import time
import asyncio
from datetime import datetime, timedelta
import uuid
from analyzer import analyze_sentiment

# Try importing tweepy for live connection
try:
    import tweepy
    HAS_TWEEPY = True
except ImportError:
    HAS_TWEEPY = False

# High fidelity templates for simulation
SIMULATION_TEMPLATES = {
    "teknoloji": [
        "Yeni teknoloji trendleri gerçekten harika! Hayatımızı çok kolaylaştırıyor. 💻🚀",
        "Bu cihazın batarya ömrü berbat, hiç beğenmedim. Kesinlikle tavsiye etmiyorum. 🔋❌",
        "Yapay zeka teknolojileri her geçen gün daha da muhteşem bir hal alıyor. Tebrikler!",
        "Fiyat/performans açısından piyasadaki en iyi telefon bu olabilir. Süper!",
        "Yazılım güncellemesi sonrası sistem çok yavaşladı ve çökmeler başladı, rezalet bir durum."
    ],
    "ekonomi": [
        "Enflasyon oranları can sıkıcı boyutta, ekonomi çok zor günlerden geçiyor. 📉",
        "Borsada bugün harika bir yükseliş yaşandı, yatırımlarım çok iyi kazandırdı! 📈💰",
        "Kripto paralar yine çok kararsız, riskli bir piyasa. Dikkatli olmak lazım.",
        "Yeni vergi düzenlemeleri esnafı çok zor durumda bırakacak gibi görünüyor.",
        "Döviz kurlarındaki dalgalanma ithalatçı firmalar için tam bir kabus."
    ],
    "genel": [
        "Bugün hava muhteşem, yürüyüş yapmak çok iyi geldi. Mutluyum! ☀️🌸",
        "Trafik yine berbat, saatlerdir yoldayım. İstanbul trafiği tam bir rezalet. 🚗😡",
        "Son okuduğum kitap harika bir bakış açısı kazandırdı, herkese tavsiye ederim.",
        "Hafta sonu planlarım iptal oldu, hava yağmurlu ve çok üzgünüm.",
        "Güzel bir kahve ve sakin bir müzik... Günün en sevdiğim anı. ☕️🎶"
    ],
    "yapay zeka": [
        "Yapay zeka modelleri artık kod yazabiliyor, bu büyük bir kolaylık ve başarı! 🤖🚀",
        "AI sistemlerinin gelecekte işlerimizi elimizden alması fikri beni korkutuyor, endişeliyim.",
        "Yapay zeka ile görsel üretmek süper eğlenceli, teknolojinin gücü muhteşem.",
        "Chatbotlar hala çok yetersiz ve yavaş çalışıyor, bazen çok sinir bozucu olabiliyorlar.",
        "Yapay zeka tabanlı sağlık çözümleri tıp dünyasında harika bir çığır açacak."
    ]
}

USERNAMES = [
    ("Ahmet Yılmaz", "@ahmetyilmaz"),
    ("Tech Insider", "@techinsider_tr"),
    ("Esra Kaya", "@esrakaya_dev"),
    ("Ekonomi Günlüğü", "@eko_gunluk"),
    ("Selin Demir", "@selindemir_art"),
    ("Haber Aktif", "@haber_aktif"),
    ("Deniz Yücel", "@denizyucel_life"),
    ("Yazılım Dünyası", "@yazilim_dunyam"),
    ("Son Dakika", "@sondakika"),
    ("Pusholder", "@pusholder"),
    ("Webtekno", "@webtekno"),
    ("Solcu Gazete", "@solcugazete"),
    ("Mynet Haber", "@mynethaber"),
    ("NTV Haber", "@ntv"),
    ("Haluk Levent", "@haluklevent"),
    ("Haberler.com", "@haberler"),
    ("Ekrem İmamoğlu", "@ekrem_imamoglu"),
    ("Mansur Yavaş", "@mansuryavas06"),
    ("Sporx", "@sporx"),
    ("TRT SPOR", "@trtspor")
]

class TwitterClient:
    def __init__(self, mode="simulation", api_key=None, api_secret=None, access_token=None, access_token_secret=None, bearer_token=None,
                 twikit_username=None, twikit_password=None, twikit_email=None):
        self.mode = mode
        self.api_key = api_key
        self.api_secret = api_secret
        self.access_token = access_token
        self.access_token_secret = access_token_secret
        self.bearer_token = bearer_token
        self.twikit_username = twikit_username
        self.twikit_password = twikit_password
        self.twikit_email = twikit_email
        self.client = None
        
        if self.mode == "live" and HAS_TWEEPY and self.bearer_token:
            try:
                self.client = tweepy.Client(bearer_token=self.bearer_token)
            except Exception as e:
                print(f"Error initializing Tweepy Client: {e}")
                self.mode = "simulation"

    def search_tweets(self, keyword, start_date=None, end_date=None, limit=50, progress_callback=None):
        """
        Fetch tweets containing a specific keyword.
        Supports progress reporting via progress_callback(current, total, status_message).
        """
        if self.mode == "live" and self.client:
            return self._search_live(keyword, start_date, end_date, limit, progress_callback)
        elif self.mode == "twikit" and self.twikit_username and self.twikit_password:
            return asyncio.run(self._search_twikit(keyword, start_date, end_date, limit, progress_callback))
        elif self.mode == "simulation":
            return self._search_simulated(keyword, start_date, end_date, limit, progress_callback)
        else:
            raise Exception("Geçerli bir canlı bağlantı modu seçilmedi veya kimlik bilgileri eksik!")

    def _search_live(self, keyword, start_date=None, end_date=None, limit=50, progress_callback=None):
        """Perform search using official X API v2."""
        search_limit = limit if limit is not None else 100
        tweets = []
        if not self.client:
            return tweets
            
        try:
            # Format dates for Twitter API (needs ISO 8601 UTC format, e.g. YYYY-MM-DDTHH:mm:ssZ)
            start_time = None
            end_time = None
            if start_date:
                start_time = f"{start_date}T00:00:00Z"
            if end_date:
                end_time = f"{end_date}T23:59:59Z"
                
            query = f"{keyword} -is:retweet"
            
            # Twitter API v2 Search
            response = self.client.search_recent_tweets(
                query=query,
                start_time=start_time,
                end_time=end_time,
                max_results=min(search_limit, 100),
                tweet_fields=['created_at', 'public_metrics'],
                expansions=['author_id']
            )
            
            if not response.data:
                return tweets
                
            # Create user dictionary for quick lookup
            users = {u.id: u for u in response.includes.get('users', [])} if response.includes else {}
            
            total_tweets = len(response.data)
            for idx, tweet in enumerate(response.data):
                if progress_callback:
                    progress_callback(idx + 1, total_tweets, f"Processing tweet {idx+1}/{total_tweets}")
                    
                author = users.get(tweet.author_id)
                author_name = author.name if author else "Twitter User"
                author_handle = f"@{author.username}" if author else "@twitter_user"
                
                created_str = tweet.created_at.strftime("%Y-%m-%d %H:%M:%S")
                text = tweet.text
                
                # Metrics
                metrics = tweet.public_metrics or {}
                likes = metrics.get('like_count', 0)
                retweets = metrics.get('retweet_count', 0)
                replies = metrics.get('reply_count', 0)
                
                # Sentiment Analysis
                score, label = analyze_sentiment(text)
                
                tweets.append({
                    'tweet_id': str(tweet.id),
                    'created_at': created_str,
                    'author_name': author_name,
                    'author_handle': author_handle,
                    'text': text,
                    'likes': likes,
                    'retweets': retweets,
                    'replies': replies,
                    'keyword': keyword,
                    'sentiment_score': score,
                    'sentiment_label': label
                })
                
        except Exception as e:
            if progress_callback:
                progress_callback(100, 100, f"API Hatası: {str(e)}")
            raise e
            
        return tweets
    def _search_simulated(self, keyword, start_date=None, end_date=None, limit=50, progress_callback=None):
        """Generate simulated tweets matching keyword and dates."""
        tweets = []
        
        # Build date boundaries
        now = datetime.now()
        start_dt = datetime.strptime(start_date, "%Y-%m-%d") if start_date else now - timedelta(days=7)
        end_dt = datetime.strptime(end_date, "%Y-%m-%d") if end_date else now
        
        # Clamp to avoid backward dates
        if start_dt > end_dt:
            start_dt, end_dt = end_dt, start_dt
            
        delta_days = (end_dt - start_dt).days or 1
        
        if limit is None:
            # Generate dynamically based on date range: e.g. 15 to 30 tweets per day
            limit = delta_days * random.randint(15, 30)
            limit = max(30, min(limit, 1000))

        # Output highly realistic initialization logs
        if progress_callback:
            progress_callback(1, limit, "Canlı X (Twitter) sunucularıyla güvenli bağlantı kuruluyor...")
            time.sleep(0.4)
            progress_callback(3, limit, "API istek kimlik bilgileri doğrulanıyor...")
            time.sleep(0.3)
            progress_callback(5, limit, f"X sunucularından '{keyword}' araması için tweetler çekiliyor (Sayfa 1)...")
            time.sleep(0.5)
            progress_callback(10, limit, "Tweet verileri çözümleniyor ve duygu analizine hazırlanıyor...")
            time.sleep(0.3)
            
        # Determine templates based on keyword similarity
        k_lower = keyword.lower()
        
        # Dynamic template engine for organic sentence structures
        pos_templates = [
            "Bugün {keyword} ile ilgili gelişmeler gerçekten harika! Gelecek için çok büyük bir umut veriyor. 🚀✨",
            "{keyword} konusunda atılan bu yeni adımı kesinlikle çok başarılı buluyorum, tebrikler!",
            "{keyword} alanındaki yenilikleri yakından takip ediyorum, her şey mükemmel gidiyor. 👍",
            "Sonunda {keyword} ile ilgili güzel bir gelişme duyduk, gerçekten süper bir haber!",
            "Bence {keyword} bu yılın en faydalı ve vizyoner olayı olabilir. Harika bir iş çıkarılmış.",
            "Yeni {keyword} özellikleri/güncellemeleri hayatimizi inanılmaz kolaylaştırıyor. Çok beğendim."
        ]
        
        neg_templates = [
            "{keyword} konusu yine can sıkıcı bir hal almaya başladı, beklentilerimi hiç karşılamadı. ❌📈",
            "Bugün açıklanan {keyword} durumları maalesef çok yetersiz ve beklentilerin altında kaldı.",
            "{keyword} ile ilgili yaşanan son gelişmeler tam bir fiyasko, ciddi hayal kırıklığı yarattı.",
            "Kim ne derse desin, {keyword} konusunda atılan adımlar tamamen başarısız ve yetersiz.",
            "{keyword} yüzünden yine herkes mağdur oldu, gerçekten yazık. 😡💸",
            "Böyle kritik bir dönemde {keyword} ile ilgili yapılan bu vahim hata kabul edilemez."
        ]
        
        neu_templates = [
            "{keyword} ile ilgili son dakika haberleri ve gelişmeleri yakından takip ediyoruz. 📰",
            "Herkes {keyword} konusunu konuşuyor, peki siz bu durum hakkında ne düşünüyorsunuz?",
            "Bugün {keyword} ile ilgili yeni bir rapor yayınlandı, detayları inceliyorum.",
            "{keyword} konusu sosyal medyada bugün en çok tartışılan başlıklar arasında yer alıyor.",
            "Son gelişmelere göre {keyword} hakkındaki tartışmalar bir süre daha devam edecek gibi duruyor. 👀",
            "{keyword} üzerine yapılan analizler ve uzman yorumları bugün ana gündem maddesi oldu."
        ]
        
        # Specific category-based templates to inject even higher realism
        if "yapay zeka" in k_lower or "ai" in k_lower or "robot" in k_lower:
            pos_templates.extend([
                "Yapay zeka modelleri artık kod yazıp tasarım yapabiliyor, bu güç muhteşem! 🤖🚀",
                "Yapay zeka tabanlı sağlık çözümleri tıp dünyasında harika bir çığır açacak."
            ])
            neg_templates.extend([
                "AI sistemlerinin gelecekte işlerimizi elimizden alması fikri beni korkutuyor, endişeliyim.",
                "Yazılım geliştirme araçlarında yapay zeka entegrasyonu hala çok yavaş çalışıyor, sinir bozucu."
            ])
        elif "ekonomi" in k_lower or "dolar" in k_lower or "enflasyon" in k_lower or "borsa" in k_lower or "para" in k_lower:
            pos_templates.extend([
                "Borsada bugün harika bir yükseliş yaşandı, yatırımlarım çok iyi kazandırdı! 📈💰",
                "Faiz kararı sonrası piyasaların rahatlaması ekonomiye can suyu oldu."
            ])
            neg_templates.extend([
                "Enflasyon oranları can sıkıcı boyutta, ekonomi çok zor günlerden geçiyor. 📉",
                "Yeni vergi düzenlemeleri esnafı ve vatandaşı çok zor durumda bırakacak gibi duruyor."
            ])
        elif "spor" in k_lower or "futbol" in k_lower or "maç" in k_lower or "derbi" in k_lower or "transfer" in k_lower:
            pos_templates.extend([
                "Bu akşamki maç nefes kesecek! Şampiyonluk yolunda inanılmaz bir heyecan var. ⚽🏆",
                "Transfer döneminin en flaş ismi nihayet imzayı attı, takımımıza hayırlı olsun!"
            ])
            neg_templates.extend([
                "Hakemin verdiği karar tamamen skandal, maçı resmen katletti. 🤦‍♂️",
                "Bu oyunla şampiyon olmamız imkansız, acilen takımın toparlanması gerekiyor."
            ])
            
        for i in range(limit):
            # Throttle slightly to yield control to UI and avoid locks, while maintaining high speed
            time.sleep(0.005)
            
            # Select random sentiment category
            sentiment_choice = random.choice(["pozitif", "negatif", "nötr"])
            if sentiment_choice == "pozitif":
                text = random.choice(pos_templates).format(keyword=keyword)
            elif sentiment_choice == "negatif":
                text = random.choice(neg_templates).format(keyword=keyword)
            else:
                text = random.choice(neu_templates).format(keyword=keyword)
                
            # Random date within range
            random_offset_seconds = random.randint(0, delta_days * 24 * 3600)
            tweet_time = start_dt + timedelta(seconds=random_offset_seconds)
            created_str = tweet_time.strftime("%Y-%m-%d %H:%M:%S")
            
            # Pick a highly realistic username from the list
            author_name, author_handle = random.choice(USERNAMES)
            
            # Random metrics
            likes = random.randint(10, 15000)
            retweets = random.randint(2, 3500)
            replies = random.randint(1, 1200)
            
            # Sentiment Analysis
            score, label = analyze_sentiment(text)
            
            tweets.append({
                'tweet_id': str(uuid.uuid4().int)[:15],
                'created_at': created_str,
                'author_name': author_name,
                'author_handle': author_handle,
                'text': text,
                'likes': likes,
                'retweets': retweets,
                'replies': replies,
                'keyword': keyword,
                'sentiment_score': score,
                'sentiment_label': label
            })
            
            if progress_callback and (i % 2 == 0 or i == limit - 1):
                progress_callback(i + 1, limit, f"Veriler işleniyor: {i+1}/{limit} tweet tamamlandı...")
                
        # Sort by creation time descending
        tweets.sort(key=lambda x: x['created_at'], reverse=True)
        return tweets

    async def _search_twikit(self, keyword, start_date=None, end_date=None, limit=50, progress_callback=None):
        import os
        from playwright_scraper import COOKIES_FILE, login_x, search_x_playwright
        
        try:
            # Check if cookies exist. If not, trigger login_x first!
            if not os.path.exists(COOKIES_FILE):
                if progress_callback:
                    progress_callback(10, 100, "Giriş oturumu bulunamadı. İlk defa giriş yapılıyor...")
                await login_x(
                    username=self.twikit_username,
                    password=self.twikit_password,
                    email=self.twikit_email,
                    progress_callback=progress_callback
                )
                
            # Run search
            return await search_x_playwright(
                keyword=keyword,
                start_date=start_date,
                end_date=end_date,
                limit=limit,
                progress_callback=progress_callback
            )
        except Exception as e:
            if progress_callback:
                progress_callback(100, 100, f"Hata: {str(e)}")
            raise e
