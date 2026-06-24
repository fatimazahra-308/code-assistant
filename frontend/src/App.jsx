import { useState, useRef, useEffect } from "react";

const API = "http://localhost:8000";
const EXAMPLES = [
  "Where is authentication handled?",
  "How does the main flow work?",
  "Explain the data model",
];

export default function App() {
  const [repoPath, setRepoPath] = useState("");
  const [indexInfo, setIndexInfo] = useState(null);
  const [indexing, setIndexing] = useState(false);
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function indexRepo(e) {
    e.preventDefault();
    if (!repoPath.trim()) return;
    setIndexing(true);
    setIndexInfo(null);
    try {
      const res = await fetch(`${API}/index`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repo_path: repoPath }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Indexing failed");
      setIndexInfo({ files: data.files_indexed, chunks: data.chunks_indexed });
      setMessages([]);
    } catch (err) {
      setIndexInfo({ error: err.message });
    } finally {
      setIndexing(false);
    }
  }

  async function ask(q) {
    const query = (q ?? question).trim();
    if (!query || !indexInfo || indexInfo.error) return;
    setMessages((m) => [...m, { role: "user", text: query }]);
    setQuestion("");
    setLoading(true);
    try {
      const res = await fetch(`${API}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: query }),
      });
      const data = await res.json();
      setMessages((m) => [...m, { role: "assistant", text: data.answer, sources: data.sources }]);
    } catch (err) {
      setMessages((m) => [...m, { role: "assistant", text: `Error: ${err.message}`, sources: [] }]);
    } finally {
      setLoading(false);
    }
  }

  const ready = indexInfo && !indexInfo.error;

  return (
    <div className="app">
      <header className="topbar">
        <div className="logo">
          {"</>"} Codebase<span>AI</span>
        </div>
        <span className="sub">Ask a repository questions — answers cite exact file:line ranges</span>
      </header>

      <form className="indexbar" onSubmit={indexRepo}>
        <input
          value={repoPath}
          onChange={(e) => setRepoPath(e.target.value)}
          placeholder="Absolute path to a local repo, e.g. C:\Users\me\my-project"
        />
        <button type="submit" disabled={indexing}>
          {indexing ? "Indexing…" : "Index repo"}
        </button>
        {ready && (
          <span className="badge ok">
            ✓ {indexInfo.files} files · {indexInfo.chunks} chunks
          </span>
        )}
        {indexInfo?.error && <span className="badge err">✗ {indexInfo.error}</span>}
      </form>

      <main className="chat">
        <div className="messages">
          {messages.length === 0 && (
            <div className="welcome">
              <h2>Understand any codebase, fast</h2>
              <p>Index a repository above, then ask:</p>
              <div className="examples">
                {EXAMPLES.map((ex) => (
                  <button key={ex} onClick={() => ask(ex)} disabled={!ready}>
                    {ex}
                  </button>
                ))}
              </div>
              {!ready && <p className="hint">⬆ Index a repository to get started</p>}
            </div>
          )}
          {messages.map((m, i) => (
            <div key={i} className={`msg ${m.role}`}>
              <div className="avatar">{m.role === "user" ? "🙂" : "🤖"}</div>
              <div className="bubble">
                <p>{m.text}</p>
                {m.sources?.length > 0 && (
                  <div className="cites">
                    {m.sources.map((s, j) => (
                      <code key={j} className="filechip">
                        {s.path}:{s.start}-{s.end}
                      </code>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
          {loading && (
            <div className="msg assistant">
              <div className="avatar">🤖</div>
              <div className="bubble typing">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          )}
          <div ref={endRef} />
        </div>

        <form
          className="composer"
          onSubmit={(e) => {
            e.preventDefault();
            ask();
          }}
        >
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder={ready ? "Ask about the code…" : "Index a repository first…"}
            disabled={!ready}
          />
          <button type="submit" disabled={loading || !ready}>
            ➤
          </button>
        </form>
      </main>
    </div>
  );
}
