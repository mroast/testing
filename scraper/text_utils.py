# scraper/text_utils.py
import re
import emoji
from langdetect import detect, DetectorFactory
from deep_translator import GoogleTranslator
import logging

DetectorFactory.seed = 0
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def clean_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    # remove emojis
    text = emoji.replace_emoji(text, replace="")
    # remove mentions, urls, preserve hashtags separately
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"@\w+", "", text)
    # keep hashtags list separate; remove raw tags from cleaned text
    text = re.sub(r"#\w+", "", text)
    # remove non-ascii and weird punctuation, keep basic punctuation
    text = re.sub(r"[^\x00-\x7F]+", " ", text)
    text = re.sub(r"[^\w\s.,!?'-]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def translate_to_english(text: str) -> str:
    try:
        if not text or len(text.strip()) < 3:
            return text
        lang = detect(text)
        if lang != "en":
            # If translation fails, return original text but log it
            return GoogleTranslator(source="auto", target="en").translate(text)
    except Exception as e:
        logging.debug(f"Translation failed for text (len={len(text)}): {e}")
    return text

def is_spammy(tweet) -> bool:
    # tweet.rawContent exists in twscrape Tweet object (based on your code)
    raw = getattr(tweet, "rawContent", "") or ""
    cleaned = clean_text(raw).lower()
    if len(cleaned.strip()) < 15:
        return True
    if raw.count("#") > 6:
        return True
    if re.fullmatch(r"(#\w+\s*)+", raw.strip()):
        return True
    if "http" in raw and len(raw.split()) < 5:
        return True
    # filter obvious retweets/share patterns
    if raw.lower().strip().startswith("rt "):
        return True
    return False

def format_tweet(tweet, query, index):
    raw = getattr(tweet, "rawContent", "") or ""
    cleaned = clean_text(raw)
    translated = translate_to_english(cleaned)

    hashtags = list(getattr(tweet, "hashtags", [])) if hasattr(tweet, "hashtags") else []
    urls_in_text = re.findall(r"https?://\S+", raw) if raw else []

    return {
        "id": getattr(tweet, "id", ""),
        "username": getattr(tweet.user, "username", "") if getattr(tweet, "user", None) else "",
        "name": getattr(tweet.user, "displayname", "") if getattr(tweet, "user", None) else "",
        "text": translated,
        "raw_text": raw,
        "query": query,
        "tweet_count": index + 1,
        "likes": getattr(tweet, "likeCount", 0),
        "retweets": getattr(tweet, "retweetCount", 0),
        "replies": getattr(tweet, "replyCount", 0),
        "bookmarks": getattr(tweet, "bookmarkCount", 0),
        "views": getattr(tweet, "viewCount", 0),
        "created_at": getattr(tweet, "date", None).strftime("%Y-%m-%d %H:%M:%S") if getattr(tweet, "date", None) else "",
        "hashtags": hashtags,
        "content_urls": urls_in_text,
        "url": f"https://twitter.com/{getattr(tweet.user, 'username', '')}/status/{getattr(tweet, 'id', '')}"
    }
