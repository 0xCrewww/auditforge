"""
audit_routes.py — API routes for the audit pipeline.

POST /api/audit      — Submit a Solidity file for audit
GET  /api/audit/{id} — Retrieve audit result
GET  /api/stats      — Token usage statistics
"""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import FileResponse

from backend.base import tracker
from backend.pipeline import create_audit_run, run_audit, get_audit_run, estimate_lines

router = APIRouter(prefix="/api")


@router.post("/audit")
async def submit_audit(file: UploadFile = File(...)) -> dict[str, Any]:
    """
    Submit a Solidity file for security audit.

    Accepts a .sol file upload and starts the multi-agent audit pipeline.
    Returns the audit ID for status polling.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    content = await file.read()
    source_code = content.decode("utf-8", errors="replace")

    if len(source_code.strip()) < 10:
        raise HTTPException(status_code=400, detail="File is too small or empty")

    if len(source_code) > 500_000:
        raise HTTPException(status_code=400, detail="File too large (max 500KB)")

    # Create audit run
    audit_id = create_audit_run(file.filename, source_code)

    # Start pipeline in background
    asyncio.create_task(run_audit(audit_id, source_code))

    return {
        "audit_id": audit_id,
        "status": "running",
        "filename": file.filename,
        "estimated_lines": estimate_lines(source_code),
        "message": "Audit started. Poll GET /api/audit/{audit_id} for results.",
    }


@router.get("/audit/{audit_id}")
async def get_audit(audit_id: str) -> dict[str, Any]:
    """
    Retrieve audit results by ID.

    Returns the full audit report if completed, or status info if still running.
    """
    run = get_audit_run(audit_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Audit not found")

    result: dict[str, Any] = {
        "audit_id": run["id"],
        "status": run["status"],
        "filename": run["filename"],
        "created_at": run["created_at"],
        "updated_at": run["updated_at"],
    }

    if run["status"] == "completed":
        result["report"] = run["report"]
    elif run["status"] == "failed":
        result["error"] = run["report"]

    return result


@router.get("/stats")
async def get_stats() -> dict[str, Any]:
    """
    Get token usage statistics across all audits.
    """
    return tracker.get_stats()
