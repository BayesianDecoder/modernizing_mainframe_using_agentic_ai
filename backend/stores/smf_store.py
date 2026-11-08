"""SQLite store — job history + LPAR performance (live inserts by simulator)."""
import sqlite3, json
from pathlib import Path
from datetime import datetime, timezone


DB_PATH = str(Path(__file__).parent.parent.parent / ".maia_smf.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS job_history (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            job          TEXT NOT NULL,
            lpar         TEXT,
            date         TEXT,
            start_time   TEXT,
            end_time     TEXT,
            elapsed_mins REAL,
            mips         INTEGER,
            cpu_secs     INTEGER,
            rc           INTEGER DEFAULT 0,
            status       TEXT DEFAULT 'SUCCESS',
            error        TEXT,
            note         TEXT,
            ts           TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS lpar_performance (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            lpar       TEXT NOT NULL,
            label      TEXT,
            date       TEXT,
            hour       TEXT,
            ts         TEXT DEFAULT (datetime('now')),
            avg_mips   INTEGER,
            peak_mips  INTEGER,
            cpu_pct    REAL
        );
        CREATE INDEX IF NOT EXISTS idx_jh_job  ON job_history(job);
        CREATE INDEX IF NOT EXISTS idx_jh_date ON job_history(date);
        CREATE INDEX IF NOT EXISTS idx_lp_lpar ON lpar_performance(lpar);
        CREATE INDEX IF NOT EXISTS idx_lp_ts   ON lpar_performance(ts);
        """)


def _utc_ts() -> str:
    """Formatted to match SQLite's own datetime('now') exactly (space
    separator, UTC, no offset suffix) — every alerts.py rule compares ts
    against datetime('now','-N minutes'), which is always UTC. Storing ts
    as local wall-clock time (as this used to do) meant that comparison was
    silently wrong by the local UTC offset for the entire lifetime of this
    project — a row from hours ago could still look "recent"."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def insert_lpar(lpar: str, label: str, avg_mips: int,
                peak_mips: int, cpu_pct: float):
    now = datetime.now()
    with get_conn() as c:
        c.execute("""
            INSERT INTO lpar_performance
            (lpar,label,date,hour,ts,avg_mips,peak_mips,cpu_pct)
            VALUES (?,?,?,?,?,?,?,?)
        """, (lpar, label,
              now.strftime("%Y-%m-%d"),
              now.strftime("%H:%M"),
              _utc_ts(),
              avg_mips, peak_mips, cpu_pct))


def insert_job(job: str, lpar: str, elapsed_mins: float,
               mips: int, rc: int = 0,
               status: str = "SUCCESS", error: str = "",
               note: str = ""):
    now = datetime.now()
    with get_conn() as c:
        c.execute("""
            INSERT INTO job_history
            (job,lpar,date,start_time,end_time,elapsed_mins,
             mips,cpu_secs,rc,status,error,note,ts)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (job, lpar,
              now.strftime("%Y-%m-%d"),
              now.strftime("%H:%M:%S"),
              now.strftime("%H:%M:%S"),
              elapsed_mins,
              mips,
              int(elapsed_mins * 60 * mips / 100),
              rc, status, error, note,
              _utc_ts()))


def recent_lpar(n: int = 40) -> list[dict]:
    with get_conn() as c:
        rows = c.execute("""
            SELECT * FROM lpar_performance
            ORDER BY ts DESC LIMIT ?
        """, (n,)).fetchall()
    return [dict(r) for r in reversed(rows)]


def recent_jobs(n: int = 30) -> list[dict]:
    with get_conn() as c:
        rows = c.execute("""
            SELECT * FROM job_history
            ORDER BY ts DESC LIMIT ?
        """, (n,)).fetchall()
    return [dict(r) for r in rows]


def job_stats(job: str) -> dict:
    with get_conn() as c:
        r = c.execute("""
            SELECT job,
                   COUNT(*)                           AS runs,
                   ROUND(AVG(elapsed_mins),1)         AS avg_mins,
                   MAX(elapsed_mins)                  AS max_mins,
                   ROUND(AVG(mips))                   AS avg_mips,
                   MAX(mips)                          AS peak_mips,
                   SUM(CASE WHEN rc=0 THEN 1 ELSE 0 END) AS ok,
                   SUM(CASE WHEN rc!=0 THEN 1 ELSE 0 END) AS fail
            FROM job_history WHERE job=?
        """, (job,)).fetchone()
    return dict(r) if r else {}


def failed_jobs_recent() -> list[dict]:
    with get_conn() as c:
        rows = c.execute("""
            SELECT * FROM job_history
            WHERE rc != 0
            ORDER BY ts DESC LIMIT 20
        """).fetchall()
    return [dict(r) for r in rows]


def peak_mips_recent() -> list[dict]:
    with get_conn() as c:
        rows = c.execute("""
            SELECT lpar, date, hour, ts, peak_mips, cpu_pct
            FROM lpar_performance
            ORDER BY peak_mips DESC LIMIT 10
        """).fetchall()
    return [dict(r) for r in rows]
