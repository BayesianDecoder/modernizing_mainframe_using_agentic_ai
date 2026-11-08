"""
recommendations.py
Turns a schedule-related alert (LPAR CPU spike, job contention, R4HA risk)
into a concrete, one-shot rescheduling suggestion.

This is deliberately separate from alerts.py: the alert engine stays pure
SQL/Cypher and zero-LLM (it must keep working even if the model provider is
down or rate-limited). This module is the optional, best-effort layer on
top — called once per newly-seen alert, cached, and allowed to silently
produce nothing if the LLM call fails.

Not a tool-calling agent: the context (job schedule, dependencies, runbook
history) is fetched directly via the existing store functions in one shot,
then handed to the model for synthesis only. A multi-round MCP tool loop
isn't needed here, and would burn far more of the free-tier quota per alert
than this design does.
"""
import asyncio, os, time

from .stores import graph, vector_store

MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest")

# Cache suggestions per alert id so the 30s alert-evaluation loop doesn't
# re-call the LLM every cycle for an alert that's still active — only once
# per hour per unique alert.
_CACHE_TTL_SECONDS = 3600
_cache: dict[str, tuple[str, float]] = {}

_PROMPT = """You are a mainframe scheduling advisor. You'll be given one active \
alert about an LPAR (a mainframe partition), the jobs currently scheduled on \
it with their dependencies, and any relevant runbook history.

Suggest ONE concrete rescheduling action in at most 2 sentences — name the \
specific job and a specific new time if you recommend moving something. If \
the runbook already prescribes a fix for this exact situation, use it rather \
than inventing a new one — but the runbook's fix may involve a job that isn't \
in the "JOBS ON <lpar>" list below (e.g. an unmodeled utility job); if so, \
describe that fix in words rather than pretending one of the listed jobs is \
the one to move. Before suggesting a new time for a listed job, check its \
"depends on" list: never suggest moving a job earlier than its dependencies' \
own SLA, or you'll suggest a time it could never actually start. If no \
schedule change would actually help, say so in one short sentence instead of \
forcing a suggestion."""


def _lpar_context(lpar: str) -> str:
    rows = graph.run("""
        MATCH (j:Job)-[:RUNS_ON]->(:LPAR {name:$l})
        OPTIONAL MATCH (dep:Job)-[:TRIGGERS]->(j)
        OPTIONAL MATCH (j)-[:TRIGGERS]->(nxt:Job)
        RETURN j.name AS name, j.schedule AS schedule, j.sla AS sla,
               collect(DISTINCT dep.name) AS depends_on,
               collect(DISTINCT nxt.name) AS triggers
    """, l=lpar)
    lines = []
    for r in rows:
        deps = ", ".join(d for d in r["depends_on"] if d) or "none"
        trig = ", ".join(t for t in r["triggers"] if t) or "none"
        lines.append(f"- {r['name']}: scheduled {r['schedule']}, SLA {r['sla']}, "
                      f"depends on [{deps}], triggers [{trig}]")
    return "\n".join(lines) or "(no job schedule data found for this LPAR)"


def _runbook_context(alert: dict) -> str:
    query = f"{alert.get('name','')} {alert.get('message','')}"
    hits = vector_store.search(query, n=2)
    if not hits:
        return "(no relevant runbook entries found)"
    return "\n\n".join(
        f"[{h['source']}, relevance {h['relevance']}]\n{h['text']}" for h in hits
    )


def get_cached(alert_id: str) -> str | None:
    """Non-blocking cache lookup only — never calls the LLM. Used so the
    alert loop can re-attach an already-known suggestion instantly on every
    cycle, without waiting on anything."""
    cached = _cache.get(alert_id)
    if cached and (time.time() - cached[1]) < _CACHE_TTL_SECONDS:
        return cached[0]
    return None


async def suggest_reschedule(alert: dict) -> str | None:
    """Return a cached or freshly-generated one-line reschedule suggestion
    for this alert, or None if it's not schedule-related or the LLM call
    fails (alerts must still display with no suggestion attached)."""
    aid = alert["id"]
    cached = _cache.get(aid)
    if cached and (time.time() - cached[1]) < _CACHE_TTL_SECONDS:
        return cached[0]

    lpar = alert.get("lpar")
    if not lpar:
        return None

    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_core.messages import SystemMessage, HumanMessage

    context = (
        f"ALERT: [{alert['severity']}] {alert['name']} — {alert['message']}\n\n"
        f"JOBS ON {lpar}:\n{_lpar_context(lpar)}\n\n"
        f"RELEVANT RUNBOOK HISTORY:\n{_runbook_context(alert)}"
    )

    llm = ChatGoogleGenerativeAI(model=MODEL, api_key=os.getenv("GEMINI_API_KEY"))
    # A heavily-throttled free tier can stall the request indefinitely rather
    # than failing fast with a 429 — without a timeout, that would leave this
    # alert's entry in main.py's in-flight set stuck forever, permanently
    # blocking any future retry for it.
    resp = await asyncio.wait_for(
        llm.ainvoke([SystemMessage(content=_PROMPT), HumanMessage(content=context)]),
        timeout=45,
    )
    text = (resp.text or "").strip()
    if text:
        _cache[aid] = (text, time.time())
    return text or None
