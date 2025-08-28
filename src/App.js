import React from "react";
import { BrowserRouter as Router, Routes, Route, Link } from "react-router-dom";
import Summarizer from "./Summarizer";
import ChatbotPage from "./ChatBotPage";
import "./App.css";

function App() {
  return (
    <Router>
      <div>
        {/* Navbar */}
        <nav className="navbar">
          <div className="nav-container">
            <h1 className="logo">Tweet Analyzer</h1>
            <div className="nav-links">
              <Link to="/">Summarizer</Link>
              <Link to="/chatbot">Chatbot</Link>
            </div>
          </div>
        </nav>

        {/* Routes */}
        <Routes>
          <Route path="/" element={<Summarizer />} />
          <Route path="/chatbot" element={<ChatbotPage />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
