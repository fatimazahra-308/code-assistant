"""FastAPI server for the codebase Q&A assistant."""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import indexer

app = FastAPI(title="Codebase Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class IndexRequest(BaseModel):
    repo_path: str


class Question(BaseModel):
    question: str


@app.post("/index")
async def index(req: IndexRequest):
    try:
        return indexer.index_repo(req.repo_path)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/ask")
async def ask(payload: Question):
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="Question is empty.")
    return indexer.answer(payload.question)


@app.get("/health")
async def health():
    return {"status": "ok"}
