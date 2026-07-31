import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB_PATH = os.path.join(BASE_DIR, "tweets.db")
from datetime import datetime

def get_connection(db_path=DEFAULT_DB_PATH):
    """Establish a connection to the SQLite database."""
    conn = sqlite3.connect(db_path)
    # Return row objects so we can access values by column name
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path=DEFAULT_DB_PATH):
    """Initialize the database and create tables if they do not exist."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    # Create tweets table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tweets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tweet_id TEXT UNIQUE,
            created_at TEXT,
            author_name TEXT,
            author_handle TEXT,
            text TEXT,
            likes INTEGER DEFAULT 0,
            retweets INTEGER DEFAULT 0,
            replies INTEGER DEFAULT 0,
            keyword TEXT,
            sentiment_score REAL,
            sentiment_label TEXT
        )
    """)
    
    # Create index on keyword and created_at for fast querying
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_keyword ON tweets(keyword)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON tweets(created_at)")
    
    conn.commit()
    conn.close()

def insert_tweets(tweets, db_path=DEFAULT_DB_PATH):
    """
    Insert a list of tweets into the database.
    Each tweet is a dictionary containing all necessary fields.
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    inserted_count = 0
    for tweet in tweets:
        try:
            cursor.execute("""
                INSERT INTO tweets (
                    tweet_id, created_at, author_name, author_handle, 
                    text, likes, retweets, replies, keyword, 
                    sentiment_score, sentiment_label
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                tweet.get('tweet_id'),
                tweet.get('created_at'),
                tweet.get('author_name'),
                tweet.get('author_handle'),
                tweet.get('text'),
                tweet.get('likes', 0),
                tweet.get('retweets', 0),
                tweet.get('replies', 0),
                tweet.get('keyword'),
                tweet.get('sentiment_score', 0.0),
                tweet.get('sentiment_label', 'Neutral')
            ))
            inserted_count += 1
        except sqlite3.IntegrityError:
            # Tweet ID already exists, we skip it
            continue
            
    conn.commit()
    conn.close()
    return inserted_count

def get_filtered_tweets(keyword=None, start_date=None, end_date=None, db_path=DEFAULT_DB_PATH):
    """
    Retrieve tweets matching filter criteria.
    Dates should be in ISO format (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    query = "SELECT * FROM tweets WHERE 1=1"
    params = []
    
    if keyword:
        query += " AND keyword = ?"
        params.append(keyword)
        
    if start_date:
        query += " AND created_at >= ?"
        params.append(start_date)
        
    if end_date:
        query += " AND created_at <= ?"
        params.append(end_date)
        
    query += " ORDER BY created_at DESC"
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

def get_sentiment_summary(keyword=None, start_date=None, end_date=None, db_path=DEFAULT_DB_PATH):
    """Get the count of positive, neutral, and negative tweets."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    query = "SELECT sentiment_label, COUNT(*) as count FROM tweets WHERE 1=1"
    params = []
    
    if keyword:
        query += " AND keyword = ?"
        params.append(keyword)
        
    if start_date:
        query += " AND created_at >= ?"
        params.append(start_date)
        
    if end_date:
        query += " AND created_at <= ?"
        params.append(end_date)
        
    query += " GROUP BY sentiment_label"
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    result = {'Positive': 0, 'Neutral': 0, 'Negative': 0}
    for row in rows:
        label = row['sentiment_label']
        if label in result:
            result[label] = row['count']
            
    return result

def get_keyword_summary(db_path=DEFAULT_DB_PATH):
    """Get the total tweets tracked per keyword."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT keyword, COUNT(*) as count FROM tweets GROUP BY keyword ORDER BY count DESC")
    rows = cursor.fetchall()
    conn.close()
    
    return {row['keyword']: row['count'] for row in rows}

def get_tweets_over_time(db_path=DEFAULT_DB_PATH):
    """Get tweet counts grouped by month for charting."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    # Group by the month part of created_at (YYYY-MM)
    cursor.execute("""
        SELECT SUBSTR(created_at, 1, 7) as date_str, COUNT(*) as count 
        FROM tweets 
        GROUP BY date_str 
        ORDER BY date_str ASC 
        LIMIT 12
    """)
    rows = cursor.fetchall()
    conn.close()
    
    return [(row['date_str'], row['count']) for row in rows]

def get_overall_stats(db_path=DEFAULT_DB_PATH):
    """Get total counts and average engagement metrics."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            COUNT(*) as total_tweets,
            COALESCE(SUM(likes), 0) as total_likes,
            COALESCE(SUM(retweets), 0) as total_retweets,
            COALESCE(AVG(sentiment_score), 0.0) as avg_sentiment
        FROM tweets
    """)
    row = cursor.fetchone()
    conn.close()
    
    return {
        'total_tweets': row['total_tweets'],
        'total_likes': row['total_likes'],
        'total_retweets': row['total_retweets'],
        'avg_sentiment': round(row['avg_sentiment'], 2)
    }

def clear_database(db_path=DEFAULT_DB_PATH):
    """Clear all data in the database."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tweets")
    conn.commit()
    conn.close()
