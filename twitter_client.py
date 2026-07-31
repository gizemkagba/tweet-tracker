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

class TwitterClient:
    def __init__(self, mode="twikit", api_key=None, api_secret=None, access_token=None, access_token_secret=None, bearer_token=None,
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
                self.mode = "twikit"

    def search_tweets(self, keyword, start_date=None, end_date=None, limit=50, progress_callback=None):
        """
        Fetch tweets containing a specific keyword.
        Supports progress reporting via progress_callback(current, total, status_message).
        """
        if self.mode == "live" and self.client:
            return self._search_live(keyword, start_date, end_date, limit, progress_callback)
        elif self.mode == "twikit" and self.twikit_username and self.twikit_password:
            return asyncio.run(self._search_twikit(keyword, start_date, end_date, limit, progress_callback))
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
