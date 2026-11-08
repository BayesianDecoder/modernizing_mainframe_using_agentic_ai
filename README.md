# MAIA — Modernizing the Mainframe with Agentic AI

> **Prototype** — built for the [Open Mainframe Project LFX Mentorship (Summer 2025)](https://openmainframeproject.org/blog/summer-mentorship-2025-a-vijay-aditya/) and shown at the OSS Korea 2026 Mentorship Showcase.

MAIA turns a mainframe estate into something you can ask questions about in plain English. It parses COBOL programs and JCL jobs into a knowledge graph, embeds runbooks and incident history into a vector store, keeps live operational telemetry in a time-series database, and lets an LLM (Gemini) reason across all three — writing its own Cypher and SQL at question-time — to answer things like:

- *"What breaks if CREDITVAL changes?"*
- *"Why does BILLJOB keep failing?"*
- *"Which LPAR is approaching its billing tier boundary?"*

...with real, cited data instead of a guess.

---

## What actually works today

| Tab | What it does |
|---|---|
| 🔔 **Dashboard** | Live alert cards from 5 pure SQL/Cypher threshold rules — LPAR CPU spikes, job failures, R4HA billing tier risk, jobs running over their average, LPAR contention. Schedule-related alerts also get an AI-generated reschedule suggestion grounded in the real job graph and runbook history. |
| 📊 **LPAR Monitor** | Live-updating chart of MIPS and CPU % per LPAR, polling every 10 seconds. |
| 📋 **Job History** | Recent batch job completions from the simulator, filterable by job name. |
| 💬 **Ask MAIA** | Free-form chat — Gemini receives a ~300-token schema (never the actual data), writes its own Cypher / SQL / semantic-search queries, and answers grounded in whatever comes back. |

Everything runs against a **live simulator** that generates realistic LPAR telemetry and batch job completions every 10 seconds — including a fake IBM mainframe day's rhythm (payroll at 1–3 AM, billing at 3–6 AM, reporting peaking hardest at 6–9 AM) and randomly injected anomalies, so the dashboard always has something real to show.

---

## Architecture

```
COBOL / JCL source files
        │
        ▼
   parser.py ──────────────────────────────► Neo4j  (dependency graph)
   tree-sitter AST | enhanced regex          Cypher queries via MCP

   data/docs/RUNBOOK.md ──────────────────► ChromaDB  (semantic search)
   sentence-transformer embeddings           natural language queries via MCP

   simulator.py (fake z/OSMF) ────────────► SQLite  (time-series)
   10-second tick, realistic MIPS patterns   SQL queries via MCP

                        │
              alerts.py ◄─────── pure SQL + Cypher, zero LLM
                        │
            recommendations.py ◄─ optional fire-and-forget Gemini call
                        │
          FastAPI (main.py) ◄──► claude_brain.py (Gemini + LangChain + MCP)
                        │
            React frontend (Vite + Tailwind + Recharts)
```

Three separate stores because the questions this system answers are three genuinely different shapes: graph traversal ("what depends on what"), time-series aggregation ("what's LPAR-3's CPU right now"), and semantic search ("what does the runbook say about this failure").

Three local MCP servers (FastMCP, ports 8081–8083) act as thin tool executors — Gemini writes the query, the server runs it, the result comes back. This is real MCP tool-calling, not prompt-stuffing.

---

## Tech stack

**Backend:** Python 3.12, FastAPI, Neo4j (Aura free tier works), SQLite, ChromaDB, tree-sitter with a locally compiled COBOL grammar, LangChain + `langchain-mcp-adapters`, Google Gemini, FastMCP

**Frontend:** React 18, Vite, Tailwind CSS, Recharts

---

## Getting started

### 1. Clone and set up the Python environment

```bash
git clone https://github.com/BayesianDecoder/modernizing_mainframe_using_agentic_ai.git
cd modernizing_mainframe_using_agentic_ai

python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Build the COBOL tree-sitter grammar (one-time)

Needs `git` and a C compiler. If this step fails, the parser falls back to enhanced regex (still works, slightly lower coverage).

```bash
backend/grammars/build_cobol_grammar.sh
```

See [backend/grammars/README.md](backend/grammars/README.md) for details.

### 3. Set up the frontend

```bash
cd frontend && npm install && cd ..
```

### 4. Configure secrets

```bash
cp .env.example .env
```

Open `.env` and fill in:

| Variable | Where to get it |
|---|---|
| `GEMINI_API_KEY` | [aistudio.google.com](https://aistudio.google.com) — free key works |
| `GEMINI_MODEL` | `gemini-flash-lite-latest` (default, lowest quota burn) |
| `NEO4J_URI` | A free [Neo4j Aura](https://neo4j.com/cloud/platform/aura-graph-database/) instance |
| `NEO4J_USERNAME` / `NEO4J_PASSWORD` | From the same Aura console |
| `LANGSMITH_*` | Optional — enables tracing at [smith.langchain.com](https://smith.langchain.com) |

### 5. Seed the stores

```bash
python -m backend.ingestion
```

This parses the COBOL/JCL files, loads Neo4j, embeds the runbook into ChromaDB, and seeds 14 days of historical LPAR + job data into SQLite.

### 6. Run everything

```bash
./start.sh
```

This starts the 3 MCP servers, the FastAPI backend, and the Vite dev server in one shot.

| Service | URL |
|---|---|
| React dashboard | http://localhost:5173 |
| FastAPI (Swagger docs) | http://localhost:8000/docs |
| Neo4j MCP server | http://localhost:8081 |
| SQLite MCP server | http://localhost:8082 |
| ChromaDB MCP server | http://localhost:8083 |

---

## Project structure

```
backend/
  main.py              FastAPI app — endpoints, background tasks (simulator, alert loop)
  parser.py            COBOL (tree-sitter AST + regex fallback) and JCL parser
  ingestion.py         Seeds all three stores from data/
  simulator.py         Fake z/OSMF — generates live LPAR telemetry and job completions
  alerts.py            Pure SQL/Cypher alert rules — zero LLM
  recommendations.py   AI scheduling advisor — optional, cached, fire-and-forget
  claude_brain.py      Gemini + LangChain + MCP tool-calling loop for the chat tab
  stores/
    graph.py           Neo4j driver and load functions
    smf_store.py       SQLite schema, insert helpers, query helpers
    vector_store.py    ChromaDB collection — ingest and search
  grammars/
    cobol.so           Compiled tree-sitter COBOL grammar (built locally, not committed)
    build_cobol_grammar.sh
    README.md

mcp_servers/
  neo4j_server.py      FastMCP — exposes neo4j_query(cypher) on port 8081
  sqlite_server.py     FastMCP — exposes sqlite_query(sql) on port 8082
  chromadb_server.py   FastMCP — exposes chromadb_search(query) on port 8083

data/
  cobol/               6 fictional COBOL programs: PAYROLL BILLING TAXCALC CREDITVAL CUSTMGMT REPORTING
  jcl/                 3 JCL jobs: PAYJOB BILLJOB NIGHTLY
  docs/                RUNBOOK.md — incident history, ADRs, SOPs (embedded into ChromaDB)
  smf/                 sample_records.json

frontend/src/          React + Vite + Tailwind UI
```

---



---

## Acknowledgments

- **Author:** A. Vijay Aditya, IIT (BHU) Varanasi — [blog post](https://openmainframeproject.org/blog/summer-mentorship-2025-a-vijay-aditya/) · [LinkedIn](https://linkedin.com/in/a-vijay-aditya/)
- **Mentor:** Suresh Tadishetty
- **Program:** [LFX Mentorship, Summer 2025](https://mentorship.lfx.linuxfoundation.org/) — Open Mainframe Project (Linux Foundation)
- **Showcase:** OSS Korea 2026 Mentorship Showcase

---

## License

MIT
