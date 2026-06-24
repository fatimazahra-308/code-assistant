"""Offline self-test for the codebase RAG pipeline.

Verifies walk -> chunk -> embed -> retrieve end-to-end WITHOUT an API key or
internet: the Claude call is mocked. Run with:  python test_indexer.py
"""
import os
import tempfile
from types import SimpleNamespace

os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-dummy")

import indexer  # noqa: E402

indexer._anthropic.messages.create = lambda **kwargs: SimpleNamespace(
    content=[SimpleNamespace(type="text", text="MOCKED: auth lives in auth/login.py:1-3")]
)

LOGIN_PY = (
    "def authenticate(user, password):\n"
    "    # verify the user's credentials\n"
    "    return verify(user, password)\n\n"
    "class SessionManager:\n"
    "    def create_session(self, user):\n"
    "        return Token(user)\n"
)
MAIN_PY = (
    "from auth.login import authenticate\n\n"
    "def handle_request(req):\n"
    "    return authenticate(req.user, req.password)\n"
)


def main() -> None:
    with tempfile.TemporaryDirectory() as repo:
        os.makedirs(os.path.join(repo, "auth"))
        with open(os.path.join(repo, "auth", "login.py"), "w", encoding="utf-8") as f:
            f.write(LOGIN_PY)
        with open(os.path.join(repo, "main.py"), "w", encoding="utf-8") as f:
            f.write(MAIN_PY)

        summary = indexer.index_repo(repo)
        assert summary["files_indexed"] == 2, summary
        assert summary["chunks_indexed"] > 0, summary
        print(f"PASS  index     -> {summary}")

        chunks = indexer.retrieve("where is authentication handled?")
        assert chunks, "no chunks retrieved"
        assert any("login.py" in c.path for c in chunks), "auth file not retrieved"
        print(f"PASS  retrieve  -> {len(chunks)} chunk(s), auth file found")

        result = indexer.answer("where is authentication handled?")
        assert result["answer"], "empty answer"
        assert result["sources"], "no citations returned"
        print(f"PASS  answer    -> answer + {len(result['sources'])} citation(s)")

    print("\nALL TESTS PASSED")
    print("(Claude call was mocked — set ANTHROPIC_API_KEY and run the server for real answers.)")


if __name__ == "__main__":
    main()
