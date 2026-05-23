"""
pipeline.py — Orchestrates the multi-agent audit pipeline.

Flow:
1. Receive Solidity source code
2. Fan out to 4 analysis agents in parallel (vulnerability, logic, gas, compliance)
3. Feed all outputs to report_generator
4. Feed draft report to synthesis agent for final polish
5. Store result and return

All runs are tracked in SQLite with status updates.
"""

from __future__ import annotations

import asyncio
import json
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.base import tracker, DB_PATH
from backend.agents import vulnerability_scanner, logic_auditor, gas_analyst
from backend.agents import compliance_checker, report_generator, synthesis


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def create_audit_run(filename: str, source_code: str) -> str:
    """Create a new audit run record and return its ID."""
    audit_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    conn = _get_conn()
    conn.execute(
        "INSERT INTO audit_runs (id, status, filename, contract_source, report, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (audit_id, "running", filename, source_code, "", now, now),
    )
    conn.commit()
    conn.close()
    return audit_id


def update_audit_run(audit_id: str, *, status: str = "", report: str = "") -> None:
    """Update an audit run record."""
    conn = _get_conn()
    updates = []
    params = []
    if status:
        updates.append("status = ?")
        params.append(status)
    if report:
        updates.append("report = ?")
        params.append(report)
    updates.append("updated_at = ?")
    params.append(datetime.now(timezone.utc).isoformat())
    params.append(audit_id)
    conn.execute(
        f"UPDATE audit_runs SET {', '.join(updates)} WHERE id = ?",
        params,
    )
    conn.commit()
    conn.close()


def get_audit_run(audit_id: str) -> dict[str, Any] | None:
    """Retrieve an audit run by ID."""
    conn = _get_conn()
    row = conn.execute("SELECT * FROM audit_runs WHERE id = ?", (audit_id,)).fetchone()
    conn.close()
    if row is None:
        return None
    return dict(row)


def _get_agent_token_stats(audit_id: str) -> dict[str, Any]:
    """Get token stats for this audit run."""
    stats = tracker.get_stats()
    return {
        "total_tokens": stats.get("total_tokens", 0),
        "by_agent": stats.get("by_agent", {}),
    }


async def run_audit(audit_id: str, source_code: str) -> None:
    """
    Execute the full audit pipeline. This runs in the background.
    """
    try:
        # Phase 1: Fan out to 4 analysis agents in parallel
        vuln_task = vulnerability_scanner.scan(source_code)
        logic_task = logic_auditor.audit(source_code)
        gas_task = gas_analyst.analyze(source_code)
        compliance_task = compliance_checker.check(source_code)

        vuln_output, logic_output, gas_output, compliance_output = await asyncio.gather(
            vuln_task, logic_task, gas_task, compliance_task,
            return_exceptions=True,
        )

        # Check for errors
        for name, result in [
            ("vulnerability_scanner", vuln_output),
            ("logic_auditor", logic_output),
            ("gas_analyst", gas_output),
            ("compliance_checker", compliance_output),
        ]:
            if isinstance(result, Exception):
                raise RuntimeError(f"Agent '{name}' failed: {result}")

        # Phase 2: Generate formatted report
        token_stats = _get_agent_token_stats(audit_id)
        draft_report = await report_generator.generate_report(
            vuln_output=vuln_output,
            logic_output=logic_output,
            gas_output=gas_output,
            compliance_output=compliance_output,
            token_stats=token_stats,
        )

        # Phase 3: Final synthesis
        token_stats = _get_agent_token_stats(audit_id)
        final_report = await synthesis.synthesize(
            draft_report=draft_report,
            token_stats=token_stats,
        )

        # Store the result
        update_audit_run(audit_id, status="completed", report=final_report)

    except Exception as exc:
        update_audit_run(audit_id, status="failed", report=f"Error: {exc}")


def estimate_lines(source_code: str) -> int:
    """Count non-empty, non-comment lines."""
    count = 0
    in_block_comment = False
    for line in source_code.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        if in_block_comment:
            if "*/" in stripped:
                in_block_comment = False
            continue
        if stripped.startswith("/*"):
            if "*/" not in stripped:
                in_block_comment = True
            continue
        if stripped.startswith("//"):
            continue
        count += 1
    return count
