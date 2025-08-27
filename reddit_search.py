# scraper/reddit_search.py
import os
import re
import json
import logging
import praw
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

reddit = praw.Reddit(
    client_id=os.getenv("CLIENT_ID"),
    client_secret=os.getenv("CLIENT_SECRET"),
    user_agent=os.getenv("USER_AGENT", "local-scraper")
)

def _clean_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"http\S+|www\S+", "", text)
    text = re.sub(r"\[.*?\]\(.*?\)", "", text)
    text = re.sub(r"\n+", " ", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()

def search_reddit_query(query: str, post_limit: int = 25, comment_limit: int = 30):
    """Return list of posts (with some comments) for the query."""
    results = []
    try:
        for post in reddit.subreddit("all").search(query, limit=post_limit):
            post_data = {
                "id": post.id,
                "source": "reddit",
                "subreddit": str(post.subreddit),
                "title": _clean_text(post.title),
                "body": _clean_text(post.selftext),
                "author": str(post.author),
                "score": post.score,
                "created_utc": post.created_utc,
                "comments": []
            }

            # Fetch limited comments (safe)
            try:
                post.comments.replace_more(limit=0)
                for i, comment in enumerate(post.comments.list()):
                    if i >= comment_limit:
                        break
                    post_data["comments"].append({
                        "comment_id": comment.id,
                        "body": _clean_text(getattr(comment, "body", "")),
                        "author": str(getattr(comment, "author", "")),
                        "score": getattr(comment, "score", 0),
                        "created_utc": getattr(comment, "created_utc", 0),
                        "parent_id": getattr(comment, "parent_id", "")
                    })
            except Exception:
                # swallow comment fetching issues (still keep post)
                logging.debug("Failed to fetch comments for reddit post", exc_info=True)

            results.append(post_data)
    except Exception as e:
        logging.error(f"Error during Reddit search for '{query}': {e}", exc_info=True)
    return results
