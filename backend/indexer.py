"""Index a code repository and answer natural-language questions about it.

Indexing strategy: walk a local repo directory, keep source files, and chunk
each file by *logical units* (functions / classes where detectable, otherwise
sliding windows of lines). Each chunk keeps its file path and line range so the
assistant can cite exactly where an answer came from.

Retrieval uses a small **in-memory vector store** (NumPy cosine similarity over
sentence-transformers embeddings) — no external vector DB and no C++ compiler
required. Claude generates the explanation. Swap the store for ChromaDB/FAISS
to scale to very large repos.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass

import anthropic
import numpy as np
from sentence_transformers import SentenceTransformer

_model = SentenceTransformer("all-MiniLM-L6-v2")

_anthropic = anthropic.Anthropic()
MODEL = "claude-opus-4-8"

# File extensions we treat as source code.
CODE_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".rb", ".rs",
    ".c", ".cpp", ".h", ".hpp", ".cs", ".php", ".kt", ".swift",
    ".md", ".txt", ".yml", ".yaml", ".json", ".sql",
}
# Directories to skip while walking.
SKIP_DIRS = {".git", "node_modules", "venv", ".venv", "__pycache__", "dist", "build", "target"}

# Lines that start a new logical unit in common languages.
_UNIT_START = re.compile(
    r"^\s*(def |class |func |function |public |private |protected |export |async )"
)


@dataclass
class CodeChunk:
    path: str
    start_line: int
    end_line: int
    text: str


# ── Minimal in-memory vector store ─────────────────────────────────────────
class VectorStore:
    """Normalized embeddings + cosine top-k search (dot product)."""

    def __init__(self) -> None:
        self._vectors: np.ndarray | None = None
        self._texts: list[str] = []
        self._metas: list[dict] = []

    def reset(self) -> None:
        self.__init__()

    def add(self, texts: list[str], metas: list[dict]) -> None:
        if not texts:
            return
        emb = _model.encode(texts, normalize_embeddings=True).astype(np.float32)
        self._vectors = emb if self._vectors is None else np.vstack([self._vectors, emb])
        self._texts.extend(texts)
        self._metas.extend(metas)

    def query(self, text: str, k: int) -> list[tuple[str, dict]]:
        if self._vectors is None:
            return []
        q = _model.encode([text], normalize_embeddings=True).astype(np.float32)[0]
        scores = self._vectors @ q
        top = np.argsort(scores)[::-1][:k]
        return [(self._texts[i], self._metas[i]) for i in top]

    def count(self) -> int:
        return len(self._texts)


_store = VectorStore()


def _chunk_file(text: str, max_lines: int = 60) -> list[tuple[int, int, str]]:
    """Split a file into chunks that break on logical-unit boundaries."""
    lines = text.splitlines()
    chunks: list[tuple[int, int, str]] = []
    buf: list[str] = []
    start = 1
    for i, line in enumerate(lines, start=1):
        # Start a new chunk when we hit a new unit and already have content.
        if _UNIT_START.match(line) and len(buf) > 5:
            chunks.append((start, i - 1, "\n".join(buf)))
            buf, start = [], i
        buf.append(line)
        if len(buf) >= max_lines:
            chunks.append((start, i, "\n".join(buf)))
            buf, start = [], i + 1
    if buf:
        chunks.append((start, len(lines), "\n".join(buf)))
    return [c for c in chunks if c[2].strip()]


def index_repo(repo_path: str) -> dict:
    """Walk a local directory and index all source files. Returns a summary."""
    if not os.path.isdir(repo_path):
        raise ValueError(f"Not a directory: {repo_path}")

    _store.reset()  # re-indexing a new repo starts clean

    texts, metas = [], []
    file_count = 0
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fname in files:
            ext = os.path.splitext(fname)[1].lower()
            if ext not in CODE_EXTENSIONS:
                continue
            full = os.path.join(root, fname)
            rel = os.path.relpath(full, repo_path)
            try:
                with open(full, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except OSError:
                continue
            file_count += 1
            for start, end, chunk in _chunk_file(content):
                texts.append(f"File: {rel} (lines {start}-{end})\n{chunk}")
                metas.append({"path": rel, "start": start, "end": end})

    _store.add(texts, metas)
    return {"files_indexed": file_count, "chunks_indexed": len(texts)}


def retrieve(question: str, k: int = 6) -> list[CodeChunk]:
    hits = _store.query(question, k)
    return [
        CodeChunk(path=m["path"], start_line=m["start"], end_line=m["end"], text=t)
        for t, m in hits
    ]


SYSTEM_PROMPT = (
    "You are an expert software engineer helping a developer understand a "
    "codebase. Answer the question using ONLY the provided code snippets. "
    "Reference specific files and line ranges in your explanation (e.g. "
    "`auth/login.py:10-25`). Explain how the relevant pieces fit together. If "
    "the snippets do not contain enough information, say what is missing. Do not "
    "invent files or functions that are not shown."
)


def answer(question: str) -> dict:
    chunks = retrieve(question)
    if not chunks:
        return {
            "answer": "No code has been indexed yet, or nothing relevant was found.",
            "sources": [],
        }

    context = "\n\n---\n\n".join(c.text for c in chunks)
    response = _anthropic.messages.create(
        model=MODEL,
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Code snippets:\n{context}\n\nQuestion: {question}",
            }
        ],
    )
    answer_text = next((b.text for b in response.content if b.type == "text"), "")
    return {
        "answer": answer_text,
        "sources": [
            {"path": c.path, "start": c.start_line, "end": c.end_line}
            for c in chunks
        ],
    }
