# MAIA Live — Claude Code Handoff Prompt

## What You Are Taking Over

You are continuing development of **MAIA** (Mainframe Agentic Intelligence Assistant), a live full-stack web application that uses Claude as an AI brain to analyse mainframe systems. The project is fully scaffolded and partially working. Your job is to make it production-ready.

**GitHub:** https://github.com/BayesianDecoder/modernizing_mainframe_using_agentic_ai  
**Blog:** https://openmainframeproject.org/blog/summer-mentorship-2025-a-vijay-aditya/  
**Context:** This is an Open Mainframe Project LFX Mentorship 2025 project.

---

## The Problem MAIA Solves

Mainframe estates have three core problems:

1. **Operational waste** — Batch jobs run at 3 AM processing empty files. IBM bills on Rolling 4-Hour Average (R4HA) MSU — one bad scheduling overlap on one night sets the bill for the entire month. A single scheduling fix can save $340,000 annually.

2. **Knowledge opacity** — The average COBOL developer is 58 years old. When they retire, 30 years of institutional knowledge leaves with them. "What breaks if CREDITVAL changes?" currently takes 1 week and 3 engineers.

3. **Modernisation blindness** — 74% of mainframe migrations fail or overrun because teams don't know the dependency map before they start. TSB Bank 2018: £48.65M in compensation for exactly this failure.

MAIA answers all three by parsing COBOL/JCL into a knowledge graph, loading performance data into SQLite, embedding runbooks into ChromaDB, and letting Claude reason across all three stores to produce evidence-based answers and recommendations.

---

## Architecture — Non-Negotiable Decisions

These decisions were deliberately made. Do not change them.

### The Six Layers (stops at Layer 3)

```
Layer 0 — Data Ingestion   (z/OSMF REST API + file upload + SMF offload)
Layer 1 — Knowledge Stores (Neo4j graph + ChromaDB vectors + SQLite SMF)
Layer 2 — Intelligence     (Claude reads schema, writes own Cypher/SQL via MCP)
Layer 3 — Recommendations  (4 specialist agents, human reads and decides)
❌ Layer 4 — Automation REMOVED (too risky for real mainframe)
❌ Layer 5 — Learning REMOVED
```

**Why automation was removed:** Mainframe changes go through Change Approval Boards, regulatory sign-offs, and multi-week parallel run validation. An AI that executes changes would never be approved in a real enterprise. MAIA produces recommendations. Humans execute them.

### Claude as the Brain — Schema-Only Context

Claude does NOT receive the full data. It receives only the schema (~300 tokens), with prompt caching enabled. Claude then **writes its own Cypher and SQL queries** and sends them to the MCP servers, which execute them against live data.

```python
# THIS IS THE CRITICAL PATTERN — do not change it
SCHEMA = """
You are MAIA. Write your own queries. Never assume data — always query first.

Neo4j: Program(name,complexity,lines), Job(name,schedule,sla,lpar),
       CALLS, EXECUTES, TRIGGERS, RUNS_ON, READS relationships
SQLite: job_history(job,lpar,elapsed_mins,mips,rc,status,error,ts)
        lpar_performance(lpar,avg_mips,peak_mips,cpu_pct,ts)
ChromaDB: runbooks, ADRs, incidents (semantic search)
"""
# Claude writes: MATCH (n)-[:CALLS*1..6]->(p:Program {name:'CREDITVAL'}) RETURN n
# MCP server executes it. Claude reads the result.
```

This approach means:
- Token cost stays ~300 tokens regardless of estate size (scales to 10,000+ programs)
- Prompt caching saves 90% on message 2+ in a session
- Claude can answer ANY question the schema supports, not just pre-defined ones

### Three MCP Servers — Pure Executors

```
localhost:8081  neo4j_query(cypher: str)      → runs whatever Cypher Claude writes
localhost:8082  sqlite_query(sql: str)         → runs whatever SQL Claude writes
localhost:8083  chromadb_search(query: str)    → semantic search
```

The MCP servers do zero reasoning. They just execute. Claude does all the reasoning.

### Alert Engine — Zero Claude Cost

The live dashboard alerts run on a separate loop polling SQLite and Neo4j every 30 seconds. No LLM involved. No token cost. Just fixed SQL/Cypher threshold rules.

```python
# Alerts fire when:
# - LPAR CPU > 85%
# - Job RC != 0 in last 30 minutes
# - R4HA rolling average > 9,000 MSU
# - Job ran 150% over its average time
# - Two jobs share an LPAR
```

---

## Project Structure

```
maia-live/
├── backend/
│   ├── main.py            FastAPI — 6 REST endpoints + 2 background tasks
│   ├── parser.py          Enhanced regex COBOL/JCL parser (no tree-sitter — COBOL not bundled)
│   ├── simulator.py       Live data generator — inserts LPAR/job data every 10s
│   ├── alerts.py          Alert rule engine — pure SQL/Cypher, zero Claude
│   ├── claude_brain.py    Claude + schema-only context + MCP + LangSmith
│   ├── ingestion.py       Seeds Neo4j, ChromaDB, SQLite from data/ files
│   └── stores/
│       ├── graph.py       Neo4j driver — load and query the knowledge graph
│       ├── smf_store.py   SQLite — job history + LPAR performance time-series
│       └── vector_store.py ChromaDB — runbook embeddings + semantic search
├── mcp_servers/
│   ├── neo4j_server.py    FastMCP port 8081 — executes Claude's Cypher
│   ├── sqlite_server.py   FastMCP port 8082 — executes Claude's SQL
│   └── chromadb_server.py FastMCP port 8083 — semantic search
├── data/
│   ├── cobol/             6 COBOL programs: PAYROLL, BILLING, TAXCALC,
│   │                                        CREDITVAL, CUSTMGMT, REPORTING
│   ├── jcl/               3 JCL jobs: PAYJOB, BILLJOB, NIGHTLY
│   ├── docs/RUNBOOK.md    ADRs + incident history → ChromaDB
│   └── smf/               sample_records.json (reference format only)
├── frontend/
│   └── src/
│       ├── App.jsx         Shell — 4 tabs + header stats + LangSmith badge
│       └── components/
│           ├── Dashboard.jsx    Live alert cards (polls /api/alerts every 30s)
│           ├── LPARMonitor.jsx  Recharts LineChart (polls /api/lpar every 10s)
│           ├── JobHistory.jsx   Job runs table (polls /api/jobs every 30s)
│           └── Chat.jsx         Claude chat → /api/chat
├── requirements.txt
├── .env.example
└── start.sh
```

---

## The Sample Mainframe Estate

These are the programs and jobs you are working with:

### COBOL Programs

| Program | Calls | Called By | Key Fact |
|---|---|---|---|
| PAYROLL | TAXCALC, CREDITVAL* | — | *CREDITVAL is conditional (inside IF) |
| BILLING | TAXCALC, CREDITVAL*, CUSTMGMT* | — | Reads CHARGE.DETAIL.DATA (CICS contention risk) |
| TAXCALC | — | PAYROLL, BILLING | Shared tax module. ADR-001: never inline. |
| CREDITVAL | — | PAYROLL, BILLING, CUSTMGMT | RBI compliance. CE01 exception = 24hr risk review |
| CUSTMGMT | — | BILLING, REPORTING | Customer plan updates |
| REPORTING | CUSTMGMT | — | Reads PAYROLL.OUT.DATA + BILL.OUT.DATA |

### Batch Jobs

| Job | LPAR | Schedule | SLA | Depends On | Triggers |
|---|---|---|---|---|---|
| PAYJOB | LPAR-1 | 1st of month 01:00 AM | 03:00 AM | — | BILLJOB |
| BILLJOB | LPAR-2 | 1st of month 03:30 AM | 06:00 AM | PAYJOB | NIGHTLY |
| NIGHTLY | LPAR-3 | Every night 06:30 AM | 09:00 AM | PAYJOB, BILLJOB | — |

### Known Problems (in the data)
- **BILLJOB fails at quarter-end** — CHARGE.DETAIL.DATA held by CICS transaction CHRG. Fix: CEMT CANCEL TASK(CHRG). Permanent fix: delay to 04:00 AM on March/June/Sept/Dec.
- **LPAR-3 peaks at 98.6% CPU** at 07:30 AM — NIGHTLY overlapping with business hours.
- The simulator randomly injects these failures every few minutes so the dashboard shows live alerts.

---

## Environment Variables Required

```bash
# .env file
ANTHROPIC_API_KEY=sk-ant-...        # Required — Claude brain
CLAUDE_MODEL=claude-sonnet-4-6      # Required

NEO4J_URI=neo4j+s://xxx.neo4j.io   # Required — free at neo4j.com/cloud/aura-free
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password

LANGSMITH_API_KEY=ls__...           # Optional — tracing at smith.langchain.com
LANGSMITH_PROJECT=MAIA-Live
```

---

## FastAPI Endpoints

```
GET  /api/alerts      Current active alerts (no Claude)
GET  /api/lpar        Last 40 LPAR MIPS readings (no Claude)
GET  /api/jobs        Last 30 job completions (no Claude)
GET  /api/stats       Header metrics: programs, jobs, alerts, peak MIPS (no Claude)
GET  /api/mcp-status  MCP server health + LangSmith status
POST /api/chat        Claude chat {message, history} → {reply}
POST /api/ingest      Trigger ingestion pipeline
```

---

## How to Run (for your reference)

```bash
# One-time setup
pip install -r requirements.txt
cd frontend && npm install && cd ..
cp .env.example .env   # fill in keys

# One-time data load
python -m backend.ingestion

# Start everything
./start.sh
# Opens at http://localhost:5173
```

---

## Important Technical Constraints

### 1. Parser — No tree-sitter for COBOL
`tree-sitter-languages` does NOT bundle a COBOL grammar. The symbol `tree_sitter_cobol` does not exist in the shared library. Do not try to use tree-sitter for COBOL. The enhanced regex parser in `backend/parser.py` is the correct solution — it correctly detects:
- All CALL statements
- Whether each CALL is conditional (inside IF/EVALUATE)
- Dataset names from ASSIGN TO clauses
- Copybooks
- Paragraph names
- Complexity scoring

### 2. Simulator replaces z/OSMF
In production, COBOL comes from z/OSMF Datasets API, job history from z/OSMF Jobs API, and LPAR performance from SMF Type-72 records offloaded every 4 hours. In this prototype, the simulator (`backend/simulator.py`) generates realistic live data into SQLite every 10 seconds. It also injects anomalies (LPAR spikes, job failures) randomly every 2-3 minutes.

When connecting to a real mainframe:
- Replace `simulator.py` with z/OSMF API calls
- The rest of the architecture stays identical
- Layer 1 onwards never needs to know where data came from

### 3. Claude Brain — Always use schema blocks
The system prompt must ALWAYS be sent as a list of blocks with the schema block marked with `cache_control: ephemeral`. Do not send it as a plain string — that breaks prompt caching.

```python
system = [
    {"type": "text", "text": "You are MAIA."},
    {"type": "text", "text": SCHEMA, "cache_control": {"type": "ephemeral"}},
]
```

### 4. LangSmith via wrap_anthropic
LangSmith is integrated via `langsmith.wrappers.wrap_anthropic(client)`. This wraps the Anthropic client so every `client.messages.create()` call is traced automatically — no decorators needed on individual functions. It is gracefully disabled if `LANGSMITH_API_KEY` is not set.

### 5. MCP Fallback
If MCP servers are not running, `claude_brain.py` falls back to in-process tool execution (same Python functions, just called directly instead of via HTTP). This means the app works for development without running the three server processes.

---

## What Is Already Working

- ✅ FastAPI backend with all 6 endpoints
- ✅ Live simulator generating LPAR + job data every 10 seconds
- ✅ Alert engine with 5 rules polling every 30 seconds
- ✅ Claude brain with schema-only context + prompt caching
- ✅ LangSmith integration via wrap_anthropic
- ✅ 3 MCP servers (neo4j, sqlite, chromadb) as pure executors
- ✅ Enhanced regex COBOL/JCL parser
- ✅ Ingestion pipeline seeds 14 days of history into SQLite
- ✅ Neo4j knowledge graph loaded from parsed COBOL/JCL
- ✅ ChromaDB with runbook, ADRs, incident records embedded
- ✅ React frontend with 4 tabs (Dashboard, LPAR Monitor, Job History, Chat)
- ✅ Live Recharts line chart for LPAR performance
- ✅ Alert severity cards with colour coding
- ✅ Chat interface connected to Claude

---

## What Still Needs Work

### Priority 1 — Make Chat Actually Good
The chat works but responses can be generic. Claude needs better guidance on:
- For impact questions: always call neo4j_query first, then smf_job_history for cost
- For failure questions: always call chromadb_search for runbook + sqlite_query for history
- For cost questions: always call sqlite_query with R4HA calculation

Consider adding few-shot examples of good Claude traces to the SCHEMA string.

### Priority 2 — Recommendations Tab
Currently Chat is reactive (user asks). Need a **Recommendations** tab that shows proactive findings from the 4 specialist agents:

```
💰 Cost Intelligence Agent     → scans SMF for R4HA spikes, names contributing jobs
⚡ Performance & Impact Agent  → watches SLA breaches, diagnoses root cause
🔄 Modernisation Agent         → scores programs, produces sequenced roadmap
🔧 Operational Control Agent   → finds recurring failure patterns in SMF history
```

Each agent produces a structured recommendation card:
```json
{
  "agent": "Cost Intelligence",
  "severity": "HIGH",
  "finding": "BILLJOB and NIGHTLY overlap between 06:30-08:00 AM on quarter-end months",
  "evidence": {"peak_mips": 12400, "tier_boundary": 10000},
  "recommendation": "Move NIGHTLY to 08:30 AM on March/June/Sept/Dec",
  "dependency_check": "NIGHTLY depends on BILLJOB — 08:30 AM safe after BILLJOB completes",
  "projected_saving": "$340,000 annually"
}
```

Add `POST /api/recommendations/run` endpoint to trigger agent scans.
Add `GET /api/recommendations` to fetch latest results.
Store results in SQLite `recommendations` table.

### Priority 3 — Impact Analysis Tab
A visual dependency explorer. User selects a program from a dropdown, clicks "Analyse", and sees:
- A table of all impacted nodes with hop count and SLA
- The actual Cypher query Claude wrote (transparency)
- A risk badge (LOW/MEDIUM/HIGH/CRITICAL)

This uses the existing `neo4j_query` tool — Claude writes the traversal query.

### Priority 4 — Real z/OSMF Connection
Add a settings panel where users can enter z/OSMF credentials:
```
Host: https://mainframe.company.com:10443
Username: MAINFRAME_ID
Password: ••••••••
```

Button: "Test Connection" → tries `GET /zosmf/info`
Button: "Run Live Ingestion" → pulls COBOL/JCL from real PDS libraries

The ingestion pipeline already handles the parsed program/job format — you just need a `zosmf.py` module that fetches from the real API instead of reading local files.

```python
# z/OSMF connection pattern
import requests

session = requests.Session()
session.auth = (username, password)
session.headers["X-CSRF-ZOSMF-HEADER"] = "*"
session.verify = False  # self-signed certs are common

# Get all COBOL members
members = session.get(
    f"https://{host}/zosmf/datasets?dslevel=PROD.COBOL.SOURCE"
).json()["items"]

for member in members:
    source = session.get(
    f"https://{host}/zosmf/datasets/PROD.COBOL.SOURCE({member['member']})/content"
    ).text
    # → feed to parser.py
```

### Priority 5 — Export and Sharing
- Export a recommendation as a PDF one-pager
- Export the dependency graph as a CSV for the ops team
- Copy chat conversation to clipboard

---

## Key Design Principles — Never Violate These

1. **Claude never modifies anything.** All writes to mainframe systems go through human-operated change management. MAIA is read-only from the mainframe's perspective.

2. **Every answer is grounded.** Claude must cite the actual program names, MIPS numbers, return codes, and dates from tool results. No hallucinated data. The SCHEMA block includes this as Rule 1.

3. **Alert engine has zero LLM cost.** Dashboard alerts must remain pure SQL/Cypher threshold rules. Never route dashboard alerts through Claude.

4. **Schema stays constant.** The context file injected to Claude must contain schema only (structure), not data (values). Data comes through tool calls. This is what keeps token cost constant as the estate grows.

5. **MCP servers are dumb.** They execute and return. They do no reasoning, filtering, or interpretation. All intelligence lives in Claude.

---

## Glossary of Mainframe Terms You Will Encounter

| Term | Meaning |
|---|---|
| z/OS | IBM's mainframe operating system |
| LPAR | Logical Partition — a virtual slice of the mainframe |
| COBOL | The primary mainframe language (800 billion lines in production globally) |
| JCL | Job Control Language — scripts that tell the mainframe how to run COBOL programs |
| SMF | System Management Facility — mainframe's black box recorder |
| z/OSMF | z/OS Management Facility — REST API into z/OS (port 10443) |
| JES | Job Entry Subsystem — the batch job scheduler |
| RACF | Resource Access Control Facility — mainframe security |
| MSU | Million Service Units — IBM's billing unit |
| R4HA | Rolling 4-Hour Average — IBM's billing calculation method |
| SLA | Service Level Agreement — job must complete by this time |
| RC | Return Code — 0 = success, 4 = warning, 8+ = failure |
| PDS | Partitioned Dataset — where COBOL source files live |
| ABEND | Abnormal End — program crash |
| CICS | Customer Information Control System — online transaction processor |
| MCP | Model Context Protocol — standard for LLM-to-tool communication |

---

## LangSmith Traces — What to Look For

When a user asks "What breaks if CREDITVAL changes?", the LangSmith trace at `smith.langchain.com` should show:

```
Run: MAIA Chat
├── messages.create()     [thinking — decides to call neo4j_query]
├── tool: neo4j_query
│   cypher: "MATCH (n)-[:CALLS|EXECUTES|TRIGGERS*1..6]
│            ->(p:Program {name:'CREDITVAL'})
│            RETURN DISTINCT n.name, labels(n)[0], n.sla"
│   result: [PAYROLL, BILLING, PAYJOB, BILLJOB, NIGHTLY]
├── tool: smf_job_history
│   sql: "SELECT job, AVG(mips), AVG(elapsed_mins) FROM job_history
│         WHERE job IN ('PAYJOB','BILLJOB','NIGHTLY') GROUP BY job"
│   result: [PAYJOB 4100 MIPS, BILLJOB 5200 MIPS, NIGHTLY 7100 MIPS]
└── messages.create()     [synthesises final answer]

Total: ~3s  |  ~1800 tokens input  |  ~300 tokens output  |  ~$0.024
Cache: ~1400 tokens read from cache (schema block — 90% saved)
```

If you see Claude answering without calling any tools, that is a bug. Improve the SCHEMA to make it clearer that Claude must always query before answering.

---

## How to Test Everything Is Working

```bash
# 1. Parser test
python3 -c "
from backend.parser import parse_all_cobol, parse_all_jcl
progs = parse_all_cobol('data/cobol')
for p in progs:
    print(p.name, '→ calls:', p.calls, '| conditional:', p.conditional_calls)
"
# Expected: PAYROLL calls TAXCALC always, CREDITVAL conditionally

# 2. Ingestion test
python -m backend.ingestion
# Expected: 6 programs, 3 jobs loaded into Neo4j; 14 days in SQLite; 8 chunks in ChromaDB

# 3. Alert engine test (no Claude needed)
python3 -c "
import os; os.environ['NEO4J_URI']='...'; os.environ['NEO4J_USERNAME']='neo4j'
os.environ['NEO4J_PASSWORD']='...'
from backend.alerts import evaluate_all
alerts = evaluate_all()
print(f'{len(alerts)} active alerts')
for a in alerts: print(a['severity'], a['message'])
"

# 4. Claude chat test
python3 -c "
import os; os.environ['ANTHROPIC_API_KEY']='sk-ant-...'
from backend.claude_brain import chat
reply = chat('What COBOL programs exist?', [])
print(reply[:200])
"
# Expected: Claude calls neo4j_query, names all 6 programs from the graph

# 5. Full stack test
./start.sh
# Open http://localhost:5173
# Dashboard should show alerts within 30 seconds
# LPAR chart should show data within 10 seconds
# Chat should respond to 'What breaks if CREDITVAL changes?'
```

---

## File to Read First

Start with **`backend/claude_brain.py`** — it is the heart of the system and defines the SCHEMA constant that controls everything Claude does. Then read **`backend/alerts.py`** to understand the separation between live monitoring (no Claude) and chat intelligence (Claude). Then **`backend/simulator.py`** to understand what live data looks like.

The frontend is standard React with Tailwind and Recharts. Nothing unusual.

---

## Final Note

This project was built for OSS Korea 2025 LFX Mentorship Showcase (August 11, 2026, Seoul). It is a real submission, not a toy. The architecture decisions reflect what would actually be deployed in a large bank or insurance company. When in doubt, choose the more conservative option — mainframe teams are extremely risk-averse and the system must earn their trust through demonstrated accuracy before they will accept any of its recommendations.

The goal is not to automate mainframe operations. The goal is to make the tribal knowledge held in COBOL source code, SMF records, and the heads of retiring engineers permanently accessible to everyone on the team, searchable in plain English, and actionable without a mainframe specialist in the room.
