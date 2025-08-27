import asyncio
import json
import logging
from twscrape import API
from twscrape.exc import RateLimitError # type: ignore
from configparser import ConfigParser
from pathlib import Path


# ------------------------------
# Logging setup
# ------------------------------
logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("twscrape").setLevel(logging.INFO)

# ------------------------------
# Load credentials
# ------------------------------
config = ConfigParser()
config.read("config.ini")

accounts = [
    {"username": config["X"]["username1"], "auth_token": config["X"]["auth_token1"], "ct0": config["X"]["ct0_1"]},
    {"username": config["X"]["username2"], "auth_token": config["X"]["auth_token2"], "ct0": config["X"]["ct0_2"]}
]

# ------------------------------
# JSON serializer for datetime
# ------------------------------
def tweet_serializer(obj):
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    return str(obj)

# ------------------------------
# File paths
# ------------------------------
query = "pakistan agriculture"
output_file = Path(f"{query}_tweets.json")
results = []

if output_file.exists():
    with open(output_file, "r", encoding="utf-8") as f:
        results = json.load(f)

scraped_ids = {t["id"] for t in results}

# ------------------------------
# Main scraping function
# ------------------------------
async def main():
    api = API()

    # Add accounts
    for acc in accounts:
        cookies = f"auth_token={acc['auth_token']}; ct0={acc['ct0']}"
        try:
            await api.pool.add_account(
                username=acc["username"],
                password="dummy",
                email="dummy",
                email_password="dummy",
                cookies=cookies
            )
            logging.info(f"✅ Added account {acc['username']}")
        except Exception as e:
            logging.error(f"❌ Failed to add {acc['username']}: {e}")

    # Scraping parameters
    total_limit = 100
    per_account_limit = 500
    total_scraped = 0
    account_index = 0

    while total_scraped < total_limit:
        acc = accounts[account_index % len(accounts)]
        await api.pool.set_active(acc["username"], active=True)
        logging.info(f"🔍 Scraping {per_account_limit} tweets with {acc['username']}")

        scraped_this_account = 0
        try:
            async for tweet in api.search(query, limit=per_account_limit * 2):
                if tweet.id in scraped_ids:
                    continue
                tdict = tweet.dict()
                tdict["scraped_by"] = acc["username"]
                results.append(tdict)
                scraped_ids.add(tweet.id)
                scraped_this_account += 1
                total_scraped += 1

                if scraped_this_account >= per_account_limit or total_scraped >= total_limit:
                    break

        except RateLimitError:
            logging.warning(f"⚠️ Rate limit hit for {acc['username']}, switching account...")
        
        logging.info(f"✅ Scraped {scraped_this_account} tweets with {acc['username']}")
        account_index += 1  # move to next account if limit hit or finished

        if total_scraped >= total_limit:
            break

    # Save results
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=tweet_serializer)

    logging.info(f"✅ Saved {len(results)} tweets to {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
