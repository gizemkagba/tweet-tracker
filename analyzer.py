try:
    from textblob import TextBlob
    HAS_TEXTBLOB = True
except ImportError:
    HAS_TEXTBLOB = False

# Turkish word lists for sentiment mapping (since python NLTK/TextBlob is mostly English out-of-the-box)
TR_POSITIVE_WORDS = {
    "harika", "süper", "iyi", "güzel", "muhteşem", "başarılı", "tebrik", 
    "beğendim", "sevdim", "bayıldım", "mutlu", "faydalı", "hızlı", 
    "tavsiye", "efsane", "harikasınız", "teşekkür", "teşekkürler", "kazandı",
    "love", "nice", "great", "good", "awesome", "perfect"
}

TR_NEGATIVE_WORDS = {
    "kötü", "berbat", "rezalet", "başarısız", "beğenmedim", "nefret", 
    "üzgün", "kızgın", "yavaş", "zor", "kaybetti", "pahalı", "hata", 
    "bozuk", "çalışmıyor", "berbat", "berbatlık", "şikayet", "korkunç",
    "bad", "worst", "hate", "terrible", "awful", "error", "broken"
}

def analyze_sentiment(text):
    """
    Analyze sentiment of a given text and return (score, label).
    - score is a float between -1.0 and 1.0.
    - label is 'Positive', 'Neutral', or 'Negative'.
    """
    if not text:
        return 0.0, "Neutral"
        
    text_lower = text.lower()
    
    # Apply a quick rule-based check for Turkish keywords first
    pos_count = sum(1 for word in TR_POSITIVE_WORDS if word in text_lower)
    neg_count = sum(1 for word in TR_NEGATIVE_WORDS if word in text_lower)
    
    if pos_count > 0 or neg_count > 0:
        total = pos_count + neg_count
        score = (pos_count - neg_count) / total
        
        if score > 0.1:
            label = "Positive"
        elif score < -0.1:
            label = "Negative"
        else:
            label = "Neutral"
            
        return round(score, 2), label

    # Fallback to TextBlob if available
    if HAS_TEXTBLOB:
        try:
            blob = TextBlob(text)
            polarity = blob.sentiment.polarity
            
            if polarity > 0.1:
                label = "Positive"
            elif polarity < -0.1:
                label = "Negative"
            else:
                label = "Neutral"
                
            return round(polarity, 2), label
        except Exception:
            pass
            
    return 0.0, "Neutral"
