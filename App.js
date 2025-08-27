import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import "./App.css"; // Import CSS file

function App() {
  const [query, setQuery] = useState("");
  const [summary, setSummary] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSummarize = async () => {
    setLoading(true);
    try {
      const res = await fetch("http://localhost:8000/summarize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
      });
      const data = await res.json();
      if (data.summary) {
        setSummary(data.summary);
      } else {
        setSummary("No summary available.");
      }
    } catch (error) {
      console.error(error);
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
      <button
        onClick={handleSummarize}
        disabled={loading}
        className="btn"
      >
        {loading ? "Summarizing..." : "Summarize"}
      </button>

      {summary && (
        <div className="summary-box">
          <h3>Summary</h3>
          <ReactMarkdown>{summary}</ReactMarkdown>
        </div>
      )}
    </div>
  );
}

export default App;
