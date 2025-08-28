import os
import json
import asyncio
import google.generativeai as genai
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from configparser import ConfigParser
from twscrape import API
import logging

# ---------- LOGGING ----------
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(message)s')

# ---------- CONFIG ----------
config = ConfigParser()
config.read("config.ini")

GEMINI_KEY = config["X"]["gemini_key"]
USERNAME = config["X"]["username1"]
AUTH_TOKEN = config["X"]["auth_token1"]
CT0 = config["X"]["ct0_1"]

genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

# ---------- FASTAPI APP ----------
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- TWITTER SCRAPER ----------
async def scrape_tweets(keyword: str, limit: int = 50):
    api = API()
    cookies = f"auth_token={AUTH_TOKEN}; ct0={CT0}"

    try:
        await api.pool.add_account(
            username=USERNAME,
            password="dummy",
            email="dummy",
            email_password="dummy",
            cookies=cookies
        )
    except Exception as e:
        logging.warning(f"Could not add account: {e}")

    await api.pool.set_active(USERNAME, active=True)

    tweets = []
    async for tweet in api.search(keyword, limit=limit):
        tweets.append(tweet.dict())

    logging.info(f"Scraped {len(tweets)} tweets for keyword '{keyword}'")
    return tweets

# ---------- TOP TWEETS WITH MEDIA ----------
def get_top_tweets(tweets: list[dict], top_n: int = 3):
    top = []
    for t in tweets:
        text = t.get("rawContent", "").strip()
        media_urls = []

        if "media" in t:
            for key in ["photos", "videos", "animated"]:
                media_list = t["media"].get(key, [])
                media_urls.extend(media_list)

        tweet_url = t.get("url")
        logging.info(f"Processing tweet: {tweet_url}")
        logging.info(f"Media URLs: {media_urls}")

        if text or media_urls:
            top.append({
                "text": text,
                "tweet_url": tweet_url,
                "media": media_urls
            })

    logging.info(f"Selected top {len(top[:top_n])} tweets: {[t['tweet_url'] for t in top[:top_n]]}")
    return top[:top_n]

# ---------- SUMMARIZER ----------
def summarize_tweets(query: str, tweets: list[str]) -> str:
    tweets_combined = "\n".join(tweets)
    prompt = f"""
Role: You are a data & tweet summarizer.
The searched keyword was: {query}

Tweets:
{tweets_combined}

Task: Summarize these tweets in a **clear Markdown format**:
- Use `##` for headings
- Use `-` for bullet points
- Use `**` for highlighting
"""
    response = model.generate_content(prompt)
    return response.text.strip()

# ---------- CHATBOT ----------
def answer_question(question: str, context: str) -> str:
    prompt = f"""
You are a helpful assistant. Only answer questions using the context below. 
If the answer is not in the context, respond: "I only answer based on the summary provided."

Context:
{context}

Question: {question}

Answer in a concise, clear manner:
"""
    response = model.generate_content(prompt)
    return response.text.strip()

# ---------- API ENDPOINTS ----------
@app.post("/summarize")
async def summarize(request: Request):
    body = await request.json()
    query = body.get("query")
    limit = body.get("limit", 50)

    tweets = await scrape_tweets(query, limit=limit)
    if not tweets:
        logging.info("No tweets returned from scraper")
        return {"error": "No tweets found"}

    tweet_texts = [t.get("rawContent", "") for t in tweets if "rawContent" in t]
    summary = summarize_tweets(query, tweet_texts)
    top_tweets = get_top_tweets(tweets, top_n=3)

    return {
        "query": query,
        "summary": summary,
        "tweets_fetched": len(tweet_texts),
        "top_tweets": top_tweets
    }

@app.post("/chat")
async def chat(request: Request):
    body = await request.json()
    question = body.get("question")
    context = body.get("context")

    if not question or not context:
        return {"answer": "Missing question or context."}

    answer = answer_question(question, context)
    return {"answer": answer}
