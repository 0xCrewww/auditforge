# AuditForge Architecture

## Overview

AuditForge is a multi-agent smart contract security audit pipeline. It uses 5 specialized AI agents running on an OpenAI-compatible LLM backend to analyze Solidity smart contracts from multiple angles simultaneously.

## Pipeline Flow

### 1. Input Phase
- User uploads a `.sol` file via the web UI or `POST /api/audit`
- File is validated (exists, non-empty, under 500KB)
- An audit run record is created in SQLite with status `running`
- The pipeline task is dispatched as a background asyncio task

### 2. Parallel Analysis Phase (Fan-Out)
Four agents run **concurrently** via `asyncio.gather()`:

| Agent | Input | Output | Focus |
|-------|-------|--------|-------|
| `vulnerability_scanner` | Raw Solidity source | Markdown findings | OWASP/SWC-based vulnerability detection |
| `logic_auditor` | Raw Solidity source | Markdown findings | Business logic, state machines, economic attacks |
| `gas_analyst` | Raw Solidity source | Markdown findings | EVM-level gas optimization opportunities |
| `compliance_checker` | Raw Solidity source | Markdown findings | ERC-20/721/1155/4626/1967 compliance |

Each agent has its own system prompt that defines:
- The agent's expertise and focus area
- The exact output format expected
- Severity classification scheme

### 3. Report Generation Phase
The `report_generator` agent receives all 4 parallel agent outputs and:
- Merges findings from all sources
- Deduplicates overlapping findings
- Assigns unique IDs (V-XXX, L-XXX, G-XXX, C-XXX)
- Prioritizes by severity (Critical → Informational)
- Produces a structured Markdown audit report

### 4. Synthesis Phase
The `synthesis` agent performs final quality assurance:
- Cross-cutting analysis (do findings interact or amplify?)
- Severity consistency check
- Executive summary refinement
- Final Markdown polish

### 5. Storage & Delivery
- Final report is stored in the `audit_runs` SQLite table
- Client polls `GET /api/audit/{id}` until status is `completed`
- Report can be downloaded as `.md` from the UI

## Token Tracking

Every LLM call is recorded in SQLite with:
- `call_id` (UUID)
- `agent` name
- `model` name
- `prompt_tokens`, `completion_tokens`, `total_tokens`
- ISO timestamp

The `GET /api/stats` endpoint provides aggregate statistics.

## Technology Stack

| Component | Technology |
|-----------|-----------|
| Backend framework | FastAPI |
| LLM client | AsyncOpenAI (OpenAI-compatible) |
| Database | SQLite (via Python stdlib) |
| Frontend | Vanilla HTML/CSS/JS |
| Containerization | Docker + docker-compose |
| Python version | 3.11+ |

## Design Decisions

1. **Fan-out with asyncio.gather**: The 4 analysis agents have no data dependency and can run truly in parallel, reducing total latency to ~1x LLM latency instead of 4x.

2. **SQLite for simplicity**: Token tracking and audit storage use SQLite — no external database dependency. Suitable for single-instance deployment.

3. **Markdown as internal format**: All agents produce Markdown. This is human-readable, easy to merge/deduplicate, and can be rendered to HTML in the frontend.

4. **Single synthesis pass**: Instead of iterative refinement, a single synthesis pass suffices for cross-cutting analysis. This balances quality with token cost.

5. **Background task execution**: Audits run as asyncio background tasks so the API remains responsive during the multi-minute analysis process.
