# ⚒️ AuditForge

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)
![Agents](https://img.shields.io/badge/Agents-5%20%2B%201_Synthesis-orange)
![Powered by MiMo](https://img.shields.io/badge/Powered_by-MiMo-purple)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi&logoColor=white)

> **Multi-agent Smart Contract Security Audit Pipeline** — 5 specialized AI agents analyze Solidity contracts for vulnerabilities, logic flaws, gas inefficiencies, and ERC compliance. Results are synthesized into a professional audit report.

---

## 🏗️ Architecture

```
                         ┌─────────────────┐
                         │  Upload .sol     │
                         │  POST /api/audit │
                         └────────┬─────────┘
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │   Chunked Source Input   │
                    └────────────┬────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                   │
              ▼                  ▼                   ▼
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │  🔍 Vuln     │  │  🧠 Logic    │  │  ⛽ Gas       │
    │  Scanner     │  │  Auditor     │  │  Analyst     │
    │  (OWASP/SWC) │  │  (State/     │  │  (EVM-level  │
    │              │  │   Logic)     │  │   Opcodes)   │
    └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
           │                 │                  │
           │         ┌──────┴───────┐          │
           │         │  📋 Compliance│          │
           │         │  Checker      │          │
           │         │  (ERC-20/721) │          │
           │         └──────┬───────┘          │
           │                │                  │
           └────────────────┼──────────────────┘
                            ▼
                ┌───────────────────────┐
                │  📄 Report Generator  │
                │  (Merge + Format)     │
                └───────────┬───────────┘
                            ▼
                ┌───────────────────────┐
                │  🔗 Synthesis Agent   │
                │  (Cross-cutting QA)   │
                └───────────┬───────────┘
                            ▼
                  ┌─────────────────┐
                  │  Final Report   │
                  │  GET /audit/:id │
                  └─────────────────┘
```

## 🤖 Agents

| Agent | Focus | Checks |
|-------|-------|--------|
| **Vulnerability Scanner** | OWASP Smart Contract Top 10, SWC Registry | Reentrancy, overflow, access control, delegatecall, tx.origin, front-running, DoS, signature replay |
| **Logic Auditor** | Business logic & state machine | State transitions, invariant violations, economic/game-theoretic attacks, edge cases |
| **Gas Analyst** | EVM-level optimization | Storage packing, loop optimization, calldata vs memory, unchecked blocks, custom errors |
| **Compliance Checker** | ERC standard verification | ERC-20, ERC-721, ERC-1155, ERC-4626, ERC-1967, ERC-165 interface detection |
| **Report Generator** | Report formatting | Merge findings, deduplicate, prioritize by severity, produce publication-ready report |
| **Synthesis Agent** | Final QA & polish | Cross-cutting analysis, severity adjustment, executive summary, quality assurance |

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- OpenAI API key (or compatible endpoint)

### Local Development

```bash
git clone https://github.com/0xCrewww/auditforge.git
cd auditforge

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API key

# Run
python -m backend.app
```

Open `http://localhost:8000` in your browser.

### Docker

```bash
cp .env.example .env
# Edit .env with your API key

docker-compose up --build
```

## 📡 API

### `POST /api/audit`

Upload a Solidity file for audit.

```bash
curl -X POST http://localhost:8000/api/audit \
  -F "file=@MyContract.sol"
```

Response:
```json
{
  "audit_id": "uuid-here",
  "status": "running",
  "filename": "MyContract.sol",
  "estimated_lines": 150,
  "message": "Audit started. Poll GET /api/audit/{audit_id} for results."
}
```

### `GET /api/audit/{id}`

Retrieve audit results. Poll until `status` is `completed` or `failed`.

```bash
curl http://localhost:8000/api/audit/{audit_id}
```

### `GET /api/stats`

Token usage statistics across all audits.

```bash
curl http://localhost:8000/api/stats
```

## 🔢 Token Consumption — Honest Disclosure

Each audit consumes tokens across 6 LLM calls (4 parallel agents + report generator + synthesis):

| Phase | Typical Tokens | Notes |
|-------|---------------|-------|
| Vulnerability Scanner | ~3,000–8,000 | Detailed scan with code snippets |
| Logic Auditor | ~3,000–8,000 | Deep business logic analysis |
| Gas Analyst | ~3,000–8,000 | Optimization code suggestions |
| Compliance Checker | ~3,000–8,000 | ERC standard verification |
| Report Generator | ~5,000–15,000 | Merges all agent outputs |
| Synthesis | ~5,000–15,000 | Final polish & cross-cutting analysis |
| **Total per audit** | **~22,000–62,000** | Depends on contract size & complexity |

Token tracking is persistent via SQLite. Check `/api/stats` for cumulative usage.

## 📁 Project Structure

```
auditforge/
├── backend/
│   ├── __init__.py
│   ├── app.py                    # FastAPI application
│   ├── base.py                   # Shared LLM caller + token tracker
│   ├── pipeline.py               # Orchestration (fan-out + synthesis)
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── vulnerability_scanner.py
│   │   ├── logic_auditor.py
│   │   ├── gas_analyst.py
│   │   ├── compliance_checker.py
│   │   ├── report_generator.py
│   │   └── synthesis.py
│   └── routes/
│       ├── __init__.py
│       └── audit_routes.py
├── frontend/
│   └── index.html                # Single-page UI
├── docs/
│   ├── ARCHITECTURE.md
│   └── EXAMPLE_RUN.md
├── proofs/
│   └── proof.txt
├── .env.example
├── .gitignore
├── docker-compose.yml
├── Dockerfile
├── LICENSE
├── README.md
└── requirements.txt
```

## 📄 License

MIT License. See [LICENSE](LICENSE) for details.

---

*Built with ❤️ for the MiMo Orbit grant program. Powered by MiMo.*
