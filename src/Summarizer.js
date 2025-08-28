import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import { TwitterTweetEmbed } from "react-twitter-embed"; // ✅ reliable
import "./App.css";

function Summarizer() {
  const [query, setQuery] = useState("");
  const [summary, setSummary] = useState("");
  const [topTweets, setTopTweets] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchCounter, setSearchCounter] = useState(0); // new counter

  const handleSummarize = async () => {
    setLoading(true);
    try {
      const res = await fetch("http://localhost:8000/summarize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
      });
      const data = await res.json();

      if (data.summary) setSummary(data.summary);
      else setSummary("No summary available.");

      // Extract tweet IDs
      const tweetsWithIds = (data.top_tweets || []).map((t) => {
        const parts = t.tweet_url.split("/");
        const tweetId = parts[parts.length - 1];
        return { ...t, tweetId };
      });

      setTopTweets(tweetsWithIds);
      setSearchCounter((prev) => prev + 1); // increment to force re-render
    } catch (err) {
      console.error(err);
      setSummary("Error fetching summary.");
    }
    setLoading(false);
  };

  return (
    <div className="container">
      <h2 className="title">Tweet Summarizer</h2>
      <input
        type="text"
        placeholder="Enter keyword..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        className="input-box"
      />
      <button onClick={handleSummarize} disabled={loading} className="btn">
        {loading ? "Summarizing..." : "Summarize"}
      </button>

      {summary && (
        <div className="summary-box">
          <h3>Summary</h3>
          <ReactMarkdown>{summary}</ReactMarkdown>
        </div>
      )}

      {topTweets.length > 0 && (
        <div className="top-tweets">
          <h3>Top Tweets</h3>
          {topTweets.map((t) => (
            <div
              key={`${t.tweetId}-${searchCounter}`} // ✅ unique key each search
              className="tweet-embed"
            >
              {t.tweetId && <TwitterTweetEmbed tweetId={t.tweetId} />}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default Summarizer;
