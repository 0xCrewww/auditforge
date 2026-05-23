"""
base.py — Shared LLM caller with exponential-backoff retry and SQLite token tracking.

Every agent imports `call_llm` from here so that token accounting is centralised
and retries are handled uniformly.
"""

from __future__ import annotations

import asyncio
import json
import os
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from openai import AsyncOpenAI

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o")
MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "3"))
RETRY_BACKOFF = float(os.getenv("LLM_RETRY_BACKOFF", "2.0"))

DB_PATH = Path(os.getenv("TOKEN_DB_PATH", "tokens.db"))

# ---------------------------------------------------------------------------
# Token Tracker (SQLite)
# ---------------------------------------------------------------------------

@dataclass
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    model: str = ""
    agent: str = ""
    call_id: str = ""
    timestamp: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "model": self.model,
            "agent": self.agent,
            "call_id": self.call_id,
            "timestamp": self.timestamp,
        }


class TokenTracker:
    """Persistent token tracker backed by SQLite."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        conn = self._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS token_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                call_id TEXT NOT NULL,
                agent TEXT NOT NULL,
                model TEXT NOT NULL,
                prompt_tokens INTEGER NOT NULL DEFAULT 0,
                completion_tokens INTEGER NOT NULL DEFAULT 0,
                total_tokens INTEGER NOT NULL DEFAULT 0,
                timestamp TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_runs (
                id TEXT PRIMARY KEY,
                status TEXT NOT NULL DEFAULT 'pending',
                filename TEXT NOT NULL DEFAULT '',
                contract_source TEXT NOT NULL DEFAULT '',
                report TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()

    def record(self, usage: TokenUsage) -> None:
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO token_usage (call_id, agent, model, prompt_tokens, completion_tokens, total_tokens, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (usage.call_id, usage.agent, usage.model,
             usage.prompt_tokens, usage.completion_tokens, usage.total_tokens,
             usage.timestamp),
        )
        conn.commit()
        conn.close()

    def get_stats(self) -> dict[str, Any]:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT COUNT(*) as total_calls, "
            "SUM(prompt_tokens) as total_prompt_tokens, "
            "SUM(completion_tokens) as total_completion_tokens, "
            "SUM(total_tokens) as total_tokens "
            "FROM token_usage"
        ).fetchone()
        by_agent = {}
        for r in conn.execute(
            "SELECT agent, COUNT(*) as calls, SUM(total_tokens) as tokens "
            "FROM token_usage GROUP BY agent"
        ).fetchall():
            by_agent[r["agent"]] = {"calls": r["calls"], "tokens": r["tokens"] or 0}
        by_model = {}
        for r in conn.execute(
            "SELECT model, COUNT(*) as calls, SUM(total_tokens) as tokens "
            "FROM token_usage GROUP BY model"
        ).fetchall():
            by_model[r["model"]] = {"calls": r["calls"], "tokens": r["tokens"] or 0}
        conn.close()
        return {
            "total_llm_calls": row["total_calls"] or 0,
            "total_prompt_tokens": row["total_prompt_tokens"] or 0,
            "total_completion_tokens": row["total_completion_tokens"] or 0,
            "total_tokens": row["total_tokens"] or 0,
            "by_agent": by_agent,
            "by_model": by_model,
        }


# Singleton
tracker = TokenTracker()

# ---------------------------------------------------------------------------
# LLM Caller
# ---------------------------------------------------------------------------

_client: Optional[AsyncOpenAI] = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)
    return _client


async def call_llm(
    *,
    agent_name: str,
    system_prompt: str,
    user_prompt: str,
    model: str | None = None,
    temperature: float = 0.2,
    max_tokens: int = 4096,
) -> str:
    """
    Call the LLM with retry + token tracking. Returns the assistant content string.
    """
    client = _get_client()
    mdl = model or LLM_MODEL
    last_exc: Optional[Exception] = None

    for attempt in range(MAX_RETRIES):
        try:
            response = await client.chat.completions.create(
                model=mdl,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            content = response.choices[0].message.content or ""
            # Track tokens
            usage = TokenUsage(
                prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
                completion_tokens=response.usage.completion_tokens if response.usage else 0,
                total_tokens=response.usage.total_tokens if response.usage else 0,
                model=mdl,
                agent=agent_name,
                call_id=str(uuid.uuid4()),
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
            tracker.record(usage)
            return content
        except Exception as exc:
            last_exc = exc
            if attempt < MAX_RETRIES - 1:
                wait = RETRY_BACKOFF ** (attempt + 1)
                await asyncio.sleep(wait)

    raise RuntimeError(
        f"LLM call failed after {MAX_RETRIES} attempts: {last_exc}"
    )
