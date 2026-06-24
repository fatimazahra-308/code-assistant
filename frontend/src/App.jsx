import { useState } from "react";

const API = "http://localhost:8000";

export default function App() {
  const [repoPath, setRepoPath] = useState("");
  const [indexStatus, setIndexStatus] = useState("");
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  async function handleIndex(e) {
    e.preventDefault();
    if (!repoPath.trim()) return;
    setIndexStatus("Indexing… (this can take a moment for large repos)");
    try {
      const res = await fetch(`${API}/index`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repo_path: repoPath }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Indexing failed");
      setIndexStatus(
        `✓ Indexed ${data.files_indexed} files (${data.chunks_indexed} chunks)`
      );
    } catch (err) {
      setIndexStatus(`✗ ${err.message}`);
    }
  }

  async function handleAsk(e) {
    e.preventDefault();
    if (!question.trim()) return;
    setLoading(true);
    setResult(null);
    try {
      const res = await fetch(`${API}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });
      setResult(await res.json());
    } catch (err) {
      setResult({ answer: `Error: ${err.message}`, sources: [] });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="container">
      <h1>🧑‍💻 Codebase Assistant</h1>
      <p className="subtitle">
        Index a repository and ask questions in plain English — answers cite the
        exact files and line ranges.
      </p>

      <section className="card">
        <h2>1. Index a repository</h2>
        <form onSubmit={handleIndex} className="row">
          <input
            type="text"
            value={repoPath}
            placeholder="Absolute path to a local repo, e.g. C:\\Users\\me\\my-project"
            onChange={(e) => setRepoPath(e.target.value)}
          />
          <button type="submit">Index</button>
        </form>
        {indexStatus && <p className="status">{indexStatus}</p>}
      </section>

      <section className="card">
        <h2>2. Ask about the code</h2>
        <form onSubmit={handleAsk} className="row">
          <input
            type="text"
            value={question}
            placeholder="e.g. Where is user authentication handled?"
            onChange={(e) => setQuestion(e.target.value)}
          />
          <button type="submit" disabled={loading}>
            {loading ? "Thinking…" : "Ask"}
          </button>
        </form>
      </section>

      {result && (
        <section className="card answer">
          <h2>Answer</h2>
          <pre className="answer-text">{result.answer}</pre>
          {result.sources?.length > 0 && (
            <>
              <h3>Referenced files</h3>
              <ul className="sources">
                {result.sources.map((s, i) => (
                  <li key={i}>
                    <code>
                      {s.path}:{s.start}-{s.end}
                    </code>
                  </li>
                ))}
              </ul>
            </>
          )}
        </section>
      )}
    </div>
  );
}
