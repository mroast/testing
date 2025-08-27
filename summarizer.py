import google.generativeai as genai
import json
from twscrape_test import output_file,query
from configparser import ConfigParser

# Load API key from config
config = ConfigParser()
config.read('config.ini') 
key = config['X']['gemini_key']

genai.configure(api_key=key)

# Pick model
model = genai.GenerativeModel("gemini-2.5-flash")

# Load tweets from JSON file
with open(f"{output_file}", "r", encoding="utf-8") as f:
    tweets = json.load(f)

# Extract tweet texts (fallback for both possible keys)
tweet_texts = [tweet.get("rawContent") or tweet.get("text") for tweet in tweets if tweet.get("rawContent") or tweet.get("text")]

# Combine into one input
tweets_combined = "\n".join(tweet_texts)

# Prompt Gemini
prompt = f"""
You are a tweet summarizer and trend analyzer.
The search keyword was: {query}.

Here are the collected tweets:
{tweets_combined}

Task:
1. Summarize the main ideas and opinions in these tweets.
2. Highlight recurring themes, patterns, or concerns.
3. Present the summary in a clear, short, bullet-point style.
"""

response = model.generate_content(prompt)
summary = response.text.strip()

print("Summary:\n")
print(summary)

# Save to file
file_name = f"{query}_summary.txt"
with open(file_name, "w", encoding="utf-8") as f:
    f.write(summary)

print(f"✅ Summary saved to {file_name}")


# import google.generativeai as genai
# import json
# from main import Query
# from twscrape_test import query
# from configparser import ConfigParser
# # Configure API key

# config = ConfigParser()
# config.read('config.ini') 
# key = config['X']['gemini_key']

# genai.configure(api_key=f"{key}")

# # Pick a model (Gemini 2.0 Flash is fastest)
# model = genai.GenerativeModel("gemini-2.5-flash")

# # Load tweets from JSON file
# with open(f"{query}_tweets.json", "r", encoding="utf-8") as f:
#     tweets = json.load(f)

# # Extract tweet texts
# # tweet_texts = [tweet["text"] for tweet in tweets]
# tweet_texts = [tweet["rawContent"] for tweet in tweets if "rawContent" in tweet]


# # Combine them into one input for summarization
# tweets_combined = "\n".join(tweet_texts)

# # Prompt Gemini for summarization
# prompt = f"""
# Role : you are a data and tweets summarizer and analyzer i will give you the tweets and summarize them shortly
# the keyword searched was {query}
# tweets: {tweets_combined}

# Summarize these tweets and present in  nice format
# """

# response = model.generate_content(prompt)
# summary= response.text.strip()
# print("Summary:\n")
# print(response.text)

# # saving it in a file
# with open(f"{query}_summary.txt","w",encoding="utf-8") as f:
#     f.write(summary)

# print("✅ Summary saved to tweets_summary.txt")