"""
main.py — FastAPI backend for MAIA Live.

Endpoints:
  GET  /api/alerts        live alert list (pure SQL/Cypher, no Claude)
  GET  /api/lpar          recent LPAR MIPS readings (last 40)
  GET  /api/jobs          recent job history (last 30)
  GET  /api/stats         dashboard header metrics
  GET  /api/mcp-status    MCP server health
  POST /api/chat          Claude chat (schema-only context + MCP)
  POST /api/ingest        trigger ingestion pipeline

Background tasks:
  simulator — inserts live LPAR + job data every 10s
  alerts    — re-evaluates alert rules every 30s
"""
import asyncio, os, sys
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.stores  import smf_store
from backend         import alerts as alert_engine
from backend         import simulator as sim
from backend         import claude_brain
from backend         import recommendations


# ── In-memory alert cache (updated by background task) ──────────
_active_alerts: list[dict] = []

# Only these alert types are inherently "when should this run" questions —
# job failures/overtime need root-cause investigation, not just a retime.
_RESCHEDULABLE_PREFIXES = ("cpu_high_", "contention_", "rha_")


# Alert ids with a generation task currently in flight — without this, an
# alert that stays active across several 30s cycles before its first
# suggestion finishes would get a NEW concurrent Gemini call spawned every
# cycle, piling up redundant calls against an already-tight quota.
_reco_pending: set[str] = set()


async def _attach_suggestion(alert: dict):
    """Runs as a fire-and-forget task — never awaited by alert_loop itself,
    so a slow or stuck LLM call can never delay alerts from publishing."""
    try:
        suggestion = await recommendations.suggest_reschedule(alert)
        if suggestion:
            alert["suggestion"] = suggestion
    except Exception as e:
        print(f"Reschedule suggestion error: {e}")
    finally:
        _reco_pending.discard(alert["id"])


async def alert_loop():
    """Re-evaluates alert rules every 30 seconds. No Claude for the rules
    themselves, and alerts are published to _active_alerts immediately,
    every cycle, unconditionally — schedule-related alerts (CPU spikes, job
    overlap, R4HA risk) additionally get a cached, best-effort reschedule
    suggestion, but generating one NEVER blocks this loop or delays alerts
    from showing up: a first-seen alert publishes without a suggestion, a
    background task fills the cache, and the suggestion attaches on the
    very next cycle (and every cycle after, from cache) once it's ready."""
    global _active_alerts
    await asyncio.sleep(5)
    while True:
        try:
            alerts = alert_engine.evaluate_all()
            _active_alerts = alerts  # publish first — unconditional, instant
            if os.getenv("GEMINI_API_KEY"):
                for a in alerts:
                    if a["id"].startswith(_RESCHEDULABLE_PREFIXES):
                        cached = recommendations.get_cached(a["id"])
                        if cached:
                            a["suggestion"] = cached
                        elif a["id"] not in _reco_pending:
                            _reco_pending.add(a["id"])
                            asyncio.create_task(_attach_suggestion(a))
        except Exception as e:
            print(f"Alert loop error: {e}")
        await asyncio.sleep(30)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialise SQLite schema
    smf_store.init_db()
    # Start background tasks
    asyncio.create_task(sim.run_simulator())
    asyncio.create_task(alert_loop())
    yield


app = FastAPI(title="MAIA Live API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Endpoints ────────────────────────────────────────────────────

@app.get("/api/alerts")
def get_alerts():
    return {
        "alerts": _active_alerts,
        "count":  len(_active_alerts),
        "critical": sum(1 for a in _active_alerts if a["severity"] == "CRITICAL"),
        "high":     sum(1 for a in _active_alerts if a["severity"] == "HIGH"),
    }


@app.get("/api/lpar")
def get_lpar():
    return {"data": smf_store.recent_lpar(40)}


@app.get("/api/jobs")
def get_jobs():
    return {"data": smf_store.recent_jobs(30)}


@app.get("/api/stats")
def get_stats():
    from backend.stores.graph import stats as gstats, run as neo4j_run
    recent = smf_store.recent_lpar(12)
    peak   = max((r["peak_mips"] for r in recent), default=0)
    failed = len(smf_store.failed_jobs_recent())
    try:
        g = gstats()
    except Exception:
        g = {}
    return {
        "programs":    g.get("prg", 6),
        "jobs":        g.get("jobs", 3),
        "alerts":      len(_active_alerts),
        "peak_mips":   peak,
        "failed_jobs": failed,
    }


@app.get("/api/mcp-status")
def get_mcp_status():
    return claude_brain.mcp_status()


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []


def _root_cause(exc: BaseException) -> BaseException:
    """Unwrap nested ExceptionGroups (raised by anyio task groups inside the
    MCP client) down to the real underlying error, e.g. a Gemini 429 —
    otherwise the user only ever sees an opaque 'unhandled errors in a
    TaskGroup' message."""
    while isinstance(exc, BaseExceptionGroup) and exc.exceptions:
        exc = exc.exceptions[0]
    return exc


@app.post("/api/chat")
async def post_chat(req: ChatRequest):
    if not os.getenv("GEMINI_API_KEY"):
        return {"reply": "❌ Set GEMINI_API_KEY in .env to enable Gemini."}
    try:
        reply = await claude_brain.chat(req.message, req.history)
        return {"reply": reply}
    except Exception as e:
        return {"reply": f"❌ Gemini error: {_root_cause(e)}"}


@app.post("/api/ingest")
def post_ingest():
    try:
        from backend.ingestion import run as ingest_run
        ingest_run()
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@app.get("/")
def root():
    return {"status": "MAIA Live API running",
            "docs": "http://localhost:8000/docs"}
