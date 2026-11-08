"""
alerts.py
Alert engine — pure SQL / Cypher rules. Zero Claude. Zero LLM cost.

Runs every 30 seconds. Evaluates fixed threshold rules against SQLite + Neo4j.
Returns structured alert objects that the React dashboard polls.
"""
import sqlite3
from datetime import datetime
from .stores.smf_store import DB_PATH
from .stores import graph

# ── Severity colours used by React ──────────────────────────────
SEV = {"CRITICAL": "red", "HIGH": "orange", "MEDIUM": "yellow", "LOW": "blue"}


def _sql(query: str, params=()) -> list[dict]:
    with sqlite3.connect(DB_PATH) as c:
        c.row_factory = sqlite3.Row
        return [dict(r) for r in c.execute(query, params).fetchall()]


# ── Individual rule functions ────────────────────────────────────

def rule_lpar_cpu_high() -> list[dict]:
    """LPAR CPU > 85% in the last 2 readings → HIGH alert."""
    rows = _sql("""
        SELECT lpar, peak_mips, cpu_pct, ts
        FROM lpar_performance
        WHERE ts >= datetime('now','-2 minutes')
          AND cpu_pct > 85
        ORDER BY cpu_pct DESC
    """)
    alerts = []
    for r in rows:
        alerts.append({
            "id":       f"cpu_high_{r['lpar']}",
            "name":     "LPAR CPU Near Capacity",
            "severity": "CRITICAL" if r["cpu_pct"] > 95 else "HIGH",
            "lpar":     r["lpar"],
            "message":  (f"{r['lpar']} at {r['cpu_pct']}% CPU "
                         f"({r['peak_mips']:,} peak MIPS)"),
            "ts":       r["ts"],
        })
    return alerts


def rule_job_failed() -> list[dict]:
    """Any job failure in the last 30 minutes → CRITICAL alert."""
    rows = _sql("""
        SELECT job, date, start_time, rc, error, ts
        FROM job_history
        WHERE rc != 0
          AND ts >= datetime('now','-30 minutes')
        ORDER BY ts DESC
    """)
    alerts = []
    for r in rows:
        alerts.append({
            "id":       f"job_fail_{r['job']}_{r['ts']}",
            "name":     "Job Failure Detected",
            "severity": "CRITICAL",
            "job":      r["job"],
            "message":  (f"{r['job']} failed RC={r['rc']} — "
                         f"{(r['error'] or '')[:70]}"),
            "ts":       r["ts"],
        })
    return alerts


def rule_rha_spike() -> list[dict]:
    """Rolling 4-reading average MIPS > 9000 → billing tier risk."""
    rows = _sql("""
        SELECT lpar,
               ROUND(AVG(peak_mips)) AS rolling_avg,
               MAX(peak_mips)        AS top_mips,
               MAX(ts)               AS ts
        FROM (
            SELECT lpar, peak_mips, ts
            FROM lpar_performance
            ORDER BY ts DESC LIMIT 12
        )
        GROUP BY lpar
        HAVING rolling_avg > 9000
    """)
    alerts = []
    for r in rows:
        alerts.append({
            "id":       f"rha_{r['lpar']}",
            "name":     "R4HA Billing Tier Risk",
            "severity": "HIGH",
            "lpar":     r["lpar"],
            "message":  (f"Rolling avg {int(r['rolling_avg']):,} MSU on "
                         f"{r['lpar']} — approaching tier boundary"),
            "ts":       r["ts"],
        })
    return alerts


def rule_job_overtime() -> list[dict]:
    """Job running > 150% of its average → MEDIUM alert."""
    rows = _sql("""
        SELECT h.job, h.elapsed_mins, h.ts,
               AVG(h2.elapsed_mins) AS avg_mins
        FROM job_history h
        JOIN job_history h2 ON h2.job = h.job
        WHERE h.ts >= datetime('now','-10 minutes')
          AND h.rc = 0
        GROUP BY h.job, h.elapsed_mins, h.ts
        HAVING h.elapsed_mins > avg_mins * 1.5
           AND avg_mins > 0
        ORDER BY h.ts DESC
        LIMIT 5
    """)
    alerts = []
    for r in rows:
        pct = int(r["elapsed_mins"] / r["avg_mins"] * 100 - 100)
        alerts.append({
            "id":       f"overtime_{r['job']}",
            "name":     "Job Running Over Average",
            "severity": "MEDIUM",
            "job":      r["job"],
            "message":  (f"{r['job']} ran {r['elapsed_mins']:.0f} min "
                         f"({pct}% over average {r['avg_mins']:.0f} min)"),
            "ts":       r["ts"],
        })
    return alerts


def rule_lpar_contention() -> list[dict]:
    """Two jobs on same LPAR with overlapping schedules → LOW alert."""
    try:
        rows = graph.run("""
            MATCH (j1:Job)-[:RUNS_ON]->(l:LPAR)<-[:RUNS_ON]-(j2:Job)
            WHERE j1.name < j2.name
            RETURN j1.name AS job1, j2.name AS job2, l.name AS lpar
        """)
    except Exception:
        return []
    alerts = []
    for r in rows:
        alerts.append({
            "id":       f"contention_{r['job1']}_{r['job2']}",
            "name":     "Jobs Share LPAR",
            "severity": "LOW",
            "lpar":     r["lpar"],
            "message":  (f"{r['job1']} and {r['job2']} both "
                         f"run on {r['lpar']} — contention risk at peak"),
            "ts":       datetime.now().isoformat(timespec="seconds"),
        })
    return alerts


# ── Main evaluation function ─────────────────────────────────────

def evaluate_all() -> list[dict]:
    """Run all rules. Returns deduplicated list of active alerts."""
    all_alerts = []
    for rule in [
        rule_lpar_cpu_high,
        rule_job_failed,
        rule_rha_spike,
        rule_job_overtime,
        rule_lpar_contention,
    ]:
        try:
            all_alerts.extend(rule())
        except Exception as e:
            print(f"Alert rule error ({rule.__name__}): {e}")

    # Deduplicate by id — keep most severe
    seen: dict[str, dict] = {}
    sev_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    for a in all_alerts:
        aid = a["id"]
        if aid not in seen or (
            sev_order.get(a["severity"], 9) <
            sev_order.get(seen[aid]["severity"], 9)
        ):
            seen[aid] = a

    result = sorted(seen.values(),
                    key=lambda x: sev_order.get(x["severity"], 9))
    for a in result:
        a["color"] = SEV.get(a["severity"], "grey")
    return result
