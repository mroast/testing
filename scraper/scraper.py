# scraper/scraper.py
import asyncio
import os
import re
import json
import logging
from typing import List, Optional

from twscrape import API
from .text_utils import clean_text, translate_to_english, is_spammy, format_tweet
from .reddit_search import search_reddit_query
from config import load_env

# optional LLM keyword generation
try:
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_ollama import ChatOllama
    LLAMA_OK = True
except Exception:
    LLAMA_OK = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def sanitize_filename(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_\- ]", "_", name).strip()

async def create_api() -> API:
    env = load_env()
    api = API()
    for creds in env.get("accounts", []):
        cookies = f"auth_token={creds.get('auth_token','')}; ct0={creds.get('ct0','')}"
        try:
            await api.pool.add_account(
                username=creds.get('username'),
                password="dummy",
                email=creds.get('email'),
                email_password=creds.get('email_password'),
                cookies=cookies
            )
            logging.info(f"Added account {creds.get('username')}")
        except Exception as e:
            logging.error(f"Failed to add account {creds.get('username')}: {e}")
    return api

def _simple_keyword_generation(query: str, max_keywords: int = 6) -> List[str]:
    # fallback: split, plus whole query and some hashtag forms
    tokens = [t.strip() for t in re.split(r"[\s,./]+", query) if len(t.strip()) > 2]
    kws = []
    kws.append(query)
    for t in tokens:
        if t.lower() not in query.lower():
            continue
        kws.append(t)
        kws.append(f"#{t}")
        if len(kws) >= max_keywords:
            break
    # dedupe while preserving order
    out = []
    for k in kws:
        if k not in out:
            out.append(k)
    return out[:max_keywords]

def generate_search_terms(query: str, max_keywords: int = 6, timeout: int = 8) -> List[str]:
    """
    Use a small LLM (Ollama via LangChain) to generate a short list of
    search phrases for Twitter and Reddit. If LLM not available or fails,
    fall back to a simple heuristic.
    """
    if LLAMA_OK:
        try:
            prompt = ChatPromptTemplate.from_messages([
                ("system", "You are an assistant that converts a user search intent into a short list of concise search phrases suitable for Twitter and Reddit. Return only a newline-separated list of phrases, max {n}."),
                ("human", "User intent: {q}\nReturn up to {n} search phrases, one per line.")
            ])
            prompt = prompt.partial(n=max_keywords)
            llm = ChatOllama(model=os.getenv("OLLAMA_MODEL", "gemma3:1b"), temperature=0)
            chain = prompt | llm
            out = chain.invoke({"q": query})
            raw = getattr(out, "content", str(out)).strip()
            # try JSON list, newline splitting, or comma splitting
            if raw.startswith("["):
                try:
                    import json as _j
                    parsed = _j.loads(raw)
                    if isinstance(parsed, list):
                        return [p.strip() for p in parsed if p and p.strip()][:max_keywords]
                except Exception:
                    pass
            # newline split
            lines = [l.strip() for l in re.split(r"[\r\n]+", raw) if l.strip()]
            if lines:
                return lines[:max_keywords]
            # fallback comma split
            parts = [p.strip() for p in raw.split(",") if p.strip()]
            if parts:
                return parts[:max_keywords]
        except Exception:
            logging.warning("LLM keyword generation failed - falling back to heuristic", exc_info=True)

    return _simple_keyword_generation(query, max_keywords=max_keywords)

async def fetch_tweets_for_keyword(api: API, keyword: str, limit: int = 200) -> List[dict]:
    results = []
    idx = 0
    async for tweet in api.search(keyword, limit=limit * 2):
        try:
            if not is_spammy(tweet):
                formatted = format_tweet(tweet, keyword, idx)
                # add source tag so later summarizer knows
                formatted["source"] = "twitter"
                results.append(formatted)
                idx += 1
        except Exception as e:
            logging.warning(f"Skipped tweet due to formatting error: {e}")
        if len(results) >= limit:
            break
    return results

async def fetch_tweets(query: str, max_results: int = 300, keywords: Optional[List[str]] = None) -> List[dict]:
    """
    If keywords provided, attempt to use them (piloting). Otherwise do a single search with query.
    """
    api = await create_api()
    results = []
    if not keywords:
        # single pass
        async for tweet in api.search(query, limit=max_results * 5):
            try:
                if not is_spammy(tweet):
                    formatted = format_tweet(tweet, query, len(results))
                    formatted["source"] = "twitter"
                    results.append(formatted)
            except Exception as e:
                logging.warning(f"Skipped tweet due to formatting error: {e}")
            if len(results) >= max_results:
                break
        logging.info(f"Collected {len(results)} tweets for query: {query}")
        return results

    # distribute max_results across keywords evenly
    per_kw = max(1, max_results // max(1, len(keywords)))
    logging.info(f"Using {len(keywords)} keywords, ~{per_kw} tweets/keyword target.")
    for kw in keywords:
        fetched = await fetch_tweets_for_keyword(api, kw, limit=per_kw)
        # avoid duplicates by id
        existing_ids = {r.get("id") for r in results}
        for ft in fetched:
            if ft.get("id") not in existing_ids:
                results.append(ft)
                existing_ids.add(ft.get("id"))
        if len(results) >= max_results:
            break

    logging.info(f"Collected {len(results)} tweets using keywords for query: {query}")
    return results

def save_tweets(tweets: list, query: str, raw: bool = True):
    folder = "data/raw" if raw else "data/processed"
    os.makedirs(folder, exist_ok=True)
    safe = sanitize_filename(query)
    filename = f"{safe}_{'raw' if raw else 'processed'}.json"
    path = os.path.join(folder, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(tweets, f, ensure_ascii=False, indent=2)
    logging.info(f"Saved {len(tweets)} items to {path}")

async def scrape_and_save(query: str, max_results: int = 300, reddit_posts: int = 25, reddit_comments: int = 30, use_llm_keywords: bool = True):
    """
    Top-level combined scraper:
      - generate search phrases (optional LLM)
      - fetch tweets (distributed across keywords if available)
      - search reddit using the keywords
      - combine and save into a single raw list (twitter + reddit mapped into same format)
    """
    # 1) generate keywords (LLM or fallback)
    keywords = None
    if use_llm_keywords:
        try:
            keywords = generate_search_terms(query, max_keywords=6)
            logging.info(f"Generated search keywords: {keywords}")
        except Exception:
            keywords = None

    # 2) fetch tweets (use keywords if available)
    tweets = await fetch_tweets(query, max_results=max_results, keywords=keywords)

    # 3) fetch reddit results per keyword (if any); otherwise use query
    reddit_results = []
    reddit_qs = keywords or [query]
    for q in reddit_qs[:3]:  # limit number of different reddit queries to 3
        try:
            posts = search_reddit_query(q, post_limit=reddit_posts, comment_limit=reddit_comments)
            # normalize reddit posts into items with 'text' and meta similar to tweets
            for p in posts:
                # Compose a text field for summarization: title + body + top comments
                comments_text = " ".join([c.get("body", "") for c in p.get("comments", [])[:5]])
                composed = " ".join([p.get("title", ""), p.get("body", ""), comments_text]).strip()
                item = {
                    "id": p.get("post_id"),
                    "source": "reddit",
                    "subreddit": p.get("subreddit"),
                    "text": composed,
                    "raw_text": composed,
                    "query": q,
                    "score": p.get("score"),
                    "created_at": p.get("created_utc"),
                    "url": f"https://reddit.com/{p.get('post_id')}"
                }
                reddit_results.append(item)
        except Exception:
            logging.exception("Reddit search failed for query: %s", q)

    # 4) combine and save: prefer tweets first then reddit
    combined = []
    # ensure tweet items have 'text' and 'source' already set in format_tweet
    for t in tweets:
        # format_tweet already sets text, url, etc. ensure source present
        t.setdefault("source", "twitter")
        combined.append(t)

    for r in reddit_results:
        combined.append(r)

    # save combined raw
    save_tweets(combined, query, raw=True)
    return combined
