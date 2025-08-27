import json
import subprocess

# File paths
INPUT_FILE = "tweets_20250826_152359.json"
OUTPUT_FILE = "summary.txt"

# 1. Load tweets from JSON
with open(INPUT_FILE, "r", encoding="utf-8") as f:
    tweets = json.load(f)

# 2. Extract tweet texts
tweet_texts = [tweet.get("text", "") for tweet in tweets]
all_tweets_text = "\n".join(tweet_texts)

# 3. Build the prompt for Gemma
prompt = f"you are tweets summarizer you will just recieve tweets data and summarizer it and dont ask other questions, Summarize the following tweets into a short, news-style summary:\n\n{all_tweets_text}"

# 4. Run Ollama with Gemma-3:1b
process = subprocess.run(
    ["ollama", "run", "gemma3:4b"],
    input=prompt.encode("utf-8"),
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)

# 5. Save summary to file
summary = process.stdout.decode("utf-8").strip()
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write(summary)

print("✅ Summary saved to", OUTPUT_FILE)
