// src/ChatBotPage.js
import React, { useState, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import "./ChatBotPage.css";

function ChatbotPage() {
  const [query, setQuery] = useState("");
  const [summary, setSummary] = useState("");
  const [topTweets, setTopTweets] = useState([]);
  const [loading, setLoading] = useState(false);
  const [chatInput, setChatInput] = useState("");
  const [chatHistory, setChatHistory] = useState([]);

  const handleSummarize = async () => {
    setLoading(true);
    const response = await fetch("http://127.0.0.1:8000/summarize", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    });
    const data = await response.json();
    setSummary(data.summary);
    setTopTweets(data.top_tweets || []);
    setLoading(false);
  };

  const handleChat = async () => {
    if (!chatInput.trim()) return;
    const response = await fetch("http://127.0.0.1:8000/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: chatInput, context: summary }),
    });
    const data = await response.json();
    setChatHistory([...chatHistory, { q: chatInput, a: data.answer }]);
    setChatInput("");
  };

  // Reload Twitter widgets whenever topTweets changes
  useEffect(() => {
    if (window.twttr) {
      window.twttr.widgets.load();
    }
  }, [topTweets]);

  return (
    <div className="container">
      <h2>Summarizer + Chatbot</h2>

      {/* Summarizer Section */}
      <input
        type="text"
        placeholder="Enter your topic..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />
      <button onClick={handleSummarize} disabled={loading}>
        {loading ? "Summarizing..." : "Summarize"}
      </button>

      {summary && (
        <div className="summary-box">
          <h3>Summary:</h3>
          <ReactMarkdown>{summary}</ReactMarkdown>
        </div>
      )}

      {topTweets.length > 0 && (
        <div className="top-tweets">
          <h3>Top Tweets</h3>
          {topTweets.map((t, i) => (
            <div key={i} className="tweet-embed">
              <blockquote className="twitter-tweet">
                <a href={t.tweet_url} aria-label="Embedded tweet"></a>
              </blockquote>
              {t.media && t.media.length > 0 && (
                <div className="tweet-media-container">
                  {t.media.map((url, idx) =>
                    url.match(/\.(jpeg|jpg|gif|png)$/) ? (
                      <img
                        key={idx}
                        src={url}
                        alt="tweet media"
                        className="tweet-media"
                      />
                    ) : (
                      <video key={idx} controls className="tweet-media">
                        <source src={url} type="video/mp4" />
                      </video>
                    )
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Chatbot Section */}
      {summary && (
        <div className="chatbox">
          <h3>Ask questions about the topic:</h3>
          <div className="chat-history">
            {chatHistory.map((chat, i) => (
              <div key={i} className="chat-message">
                <p><strong>You:</strong> {chat.q}</p>
                <p><strong>Bot:</strong> {chat.a}</p>
              </div>
            ))}
          </div>
          <input
            type="text"
            placeholder="Ask something..."
            value={chatInput}
            onChange={(e) => setChatInput(e.target.value)}
          />
          <button onClick={handleChat}>Ask</button>
        </div>
      )}
    </div>
  );
}

export default ChatbotPage;
