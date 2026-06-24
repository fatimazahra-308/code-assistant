# 🧑‍💻 Codebase Assistant — Code-Aware RAG

A full-stack **RAG assistant for source code**. Point it at a local repository
and ask questions in plain English — *"Where is authentication handled?"*,
*"How does the payment flow work?"* — and get explanations that **cite the exact
files and line ranges** the answer is based on.

> **Stack:** Python · FastAPI · Anthropic Claude (`claude-opus-4-8`) ·
> sentence-transformers · NumPy vector search · React (Vite)

## Why this project

This is the same problem real developer tools (Cursor, Copilot Chat, Sourcegraph)
solve, which makes it relatable to interviewers. The differentiator here is
**code-aware chunking**: instead of splitting files at arbitrary character
counts, the indexer breaks on **logical boundaries** (function/class/method
definitions) so each retrieved chunk is a coherent unit — which improves
retrieval precision over naive fixed-size chunking.

## How it works

```
  repo path ─► walk files ─► chunk by function/class ─► embed ─► NumPy store
                                                                    │
  question ─► embed ─► top-k similar chunks ◄────────────────────────┘
                              │
                              ▼
              Claude (engineer persona) ─► explanation + file:line citations
```

| Step | Where | What happens |
|------|-------|--------------|
| Walk | `indexer.index_repo` | Recurse the repo, skip `node_modules`/`.git`/etc., keep source files |
| Chunk | `indexer._chunk_file` | Break on `def`/`class`/`function`/`func` boundaries, cap chunk size |
| Embed + store | `indexer.index_repo` | `all-MiniLM-L6-v2` embeddings → in-memory NumPy store |
| Retrieve | `indexer.retrieve` | Cosine top-k chunks for the question |
| Generate | `indexer.answer` | Claude explains using only retrieved code, citing `path:start-end` |

## Running it

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env          # then add your ANTHROPIC_API_KEY
uvicorn main:app --reload     # serves http://localhost:8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev                   # serves http://localhost:5173
```

In the UI, paste the **absolute path** to a local repository, click **Index**,
then ask questions. (Tip: index this very `projects/` folder as a quick test.)

### Verify it offline (no API key needed)

```bash
cd backend
python test_indexer.py   # mocks Claude; verifies walk → chunk → embed → retrieve
```

## API

| Method | Endpoint  | Body                          | Returns                              |
|--------|-----------|-------------------------------|--------------------------------------|
| POST   | `/index`  | `{ "repo_path": "..." }`      | `{ files_indexed, chunks_indexed }`  |
| POST   | `/ask`    | `{ "question": "..." }`       | `{ answer, sources[] }`              |
| GET    | `/health` | —                             | `{ status: "ok" }`                   |

## Possible extensions

- Use a proper AST parser (`tree-sitter`) for language-accurate chunking.
- Clone a GitHub repo by URL instead of requiring a local path.
- Add agentic multi-step retrieval (let Claude issue follow-up searches via tool use).
- Swap the in-memory `VectorStore` for ChromaDB / FAISS to persist and scale.

## Resume bullet

> Developed a code-aware RAG assistant that indexes a Git repository by function
> and answers natural-language questions about the codebase, using logical-unit
> chunking to improve retrieval precision and citing exact file/line ranges in
> every answer.
