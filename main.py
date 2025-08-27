import time
import json
from configparser import ConfigParser
from datetime import datetime
import asyncio
from twikit import Client

Query = 'pakistan rain'
Limit = 20
Filter = 'Latest'

# Load Credentials
config = ConfigParser()
config.read('config.ini')
username = config['X']['username']
email = config['X']['email']
password = config['X']['password']

# Initialize client
client = Client(language='en-US')

async def main():
    # Attempt to load cookies
    try:
        client.load_cookies('cookies.json')
        print('cookies loaded successfully')
    except Exception as e:
        print(f'failed to load cookies : {e}')
        await client.login(auth_info_1=username, auth_info_2=email, password=password)
        client.save_cookies('cookies.json')
        print('logged in and cookies saved')

    # Fetch tweets
    tweets = await client.search_tweet(Query, Filter, Limit)

    tweet_data = []
    tweet_count = 0
    for tweet in tweets:
        tweet_count += 1
        print(tweet.text)

        # Save selected fields from tweet object
        tweet_data.append({
            "id": tweet.id,
            "screen_name": tweet.user.screen_name if tweet.user else None,
            "name": tweet.user.name if tweet.user else None,
            "text": tweet.text,
            "created_at": str(tweet.created_at),
            "like_count": tweet.favorite_count,
            "retweet_count": tweet.retweet_count,
            "reply_count": tweet.reply_count,
            "quote_count": tweet.quote_count,
            "view_count": tweet.view_count,
        })  


    # Save to JSON file
    filename = f"{Query}_tweets.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(tweet_data, f, ensure_ascii=False, indent=4)

    print(f'{datetime.now()} - done {tweet_count} tweets found')
    print(f"Tweets saved to {filename}")

if __name__ == "__main__":
    asyncio.run(main())
