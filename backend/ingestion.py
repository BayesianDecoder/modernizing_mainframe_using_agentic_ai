"""ingestion.py — seeds Neo4j, ChromaDB, SQLite from data/ files."""
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from backend.parser import parse_all_cobol, parse_all_jcl, parser_mode


# ── Seed historical SMF data ─────────────────────────────────────
def seed_smf_history():
    from .stores.smf_store import insert_lpar, insert_job, DB_PATH, init_db
    import sqlite3, random
    from datetime import datetime, timedelta

    init_db()   # ensure tables exist even when called standalone
    print("  📊  Seeding SMF history (14 days)...")
    conn = sqlite3.connect(DB_PATH)
    # Check if already seeded. A single pass inserts ~18-22 job_history rows
    # (well under the old ">50" threshold), so that guard never tripped on a
    # second run — every re-run of ingestion (e.g. via start.sh) kept
    # duplicating the same 14-day block on top of itself.
    count = conn.execute("SELECT COUNT(*) FROM job_history").fetchone()[0]
    conn.close()
    if count > 0:
        print("       Already seeded — skipping")
        return

    JOB_PATTERNS = [
        ("PAYJOB",  "LPAR-1", 108, 4100),
        ("BILLJOB", "LPAR-2", 133, 5200),
        ("NIGHTLY", "LPAR-3", 141, 7100),
    ]
    LPAR_BASE = {
        "LPAR-1": [2100,4100,4200,2200,2100,2000,2200,3100,3800,4200,
                   4100,4300,3800,4100,4200,4400,4100,3600,2800,2400,2200,2100,2000,2100],
        "LPAR-2": [1200,1800,1500,5200,5100,5300,2100,2400,2800,3100,
                   3200,3400,2900,3100,3300,3500,3200,2700,2100,1800,1600,1500,1400,1300],
        "LPAR-3": [1100,1300,1200,1400,1300,1200,7100,7200,4200,2800,
                   2900,3100,2700,2800,2900,3200,2900,2400,1900,1600,1400,1300,1200,1200],
    }
    LABEL = {"LPAR-1":"Production-Payments","LPAR-2":"Batch-Processing","LPAR-3":"Customer-Reporting"}

    base = datetime.now() - timedelta(days=14)
    for day in range(14):
        d = base + timedelta(days=day)
        # LPAR readings — every 30 minutes
        for hour in range(24):
            for lpar, bases in LPAR_BASE.items():
                m   = bases[hour]
                mips = int(m + random.gauss(0, m*0.06))
                cpu  = round(min(99.9, mips/m*65 + random.gauss(0,3)), 1)
                ts   = d.replace(hour=hour, minute=random.randint(0,29), second=0)
                with sqlite3.connect(DB_PATH) as c:
                    c.execute("""
                        INSERT INTO lpar_performance (lpar,label,date,hour,ts,avg_mips,peak_mips,cpu_pct)
                        VALUES (?,?,?,?,?,?,?,?)
                    """, (lpar, LABEL[lpar], ts.strftime("%Y-%m-%d"),
                          ts.strftime("%H:%M"), ts.isoformat(timespec="seconds"),
                          int(mips*0.92), mips, cpu))

        # Job runs
        for job, lpar, base_mins, base_mips in JOB_PATTERNS:
            # NIGHTLY runs every day; others only on certain days
            if job != "NIGHTLY" and d.day not in [1,15]:
                continue
            # Introduce failures for BILLJOB on specific dates
            is_failure = (job=="BILLJOB" and d.day in [1] and
                          d.month in [4,6] and random.random()<0.7)
            elapsed = base_mins + random.gauss(0, base_mins*0.08)
            mips    = base_mips + random.gauss(0, base_mips*0.05)
            if is_failure:
                elapsed *= 2.1; mips *= 1.6
            ts = d.replace(hour=1 if job=="PAYJOB" else (3 if job=="BILLJOB" else 6),
                           minute=random.randint(0,15), second=0)
            with sqlite3.connect(DB_PATH) as c:
                c.execute("""
                    INSERT INTO job_history
                    (job,lpar,date,start_time,end_time,elapsed_mins,mips,cpu_secs,rc,status,error,ts)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                """, (job, lpar, ts.strftime("%Y-%m-%d"),
                      ts.strftime("%H:%M:%S"), ts.strftime("%H:%M:%S"),
                      round(elapsed,1), int(mips),
                      int(elapsed*60*mips/100),
                      8 if is_failure else 0,
                      "FAILED" if is_failure else "SUCCESS",
                      "CHARGE.DETAIL.DATA HELD BY CICS TRANSACTION CHRG." if is_failure else "",
                      ts.isoformat(timespec="seconds")))
    print(f"       Seeded 14 days of LPAR + job history")


def run():
    from .stores import graph, smf_store, vector_store

    print("\n" + "="*55)
    print("  MAIA Live — Ingestion Pipeline")
    print("="*55)

    # ── SQLite ───────────────────────────────────────────────────
    print("\n💾  Initialising SQLite...")
    smf_store.init_db()
    seed_smf_history()

    # ── COBOL + JCL → Neo4j ─────────────────────────────────────
    print(f"\n📂  Parsing COBOL / JCL  [{parser_mode()}]...")
    cobol_dir = ROOT / "data" / "cobol"
    jcl_dir   = ROOT / "data" / "jcl"

    cobol_objects = parse_all_cobol(str(cobol_dir))
    programs = [p.to_dict() for p in cobol_objects]
    for p in cobol_objects:
        cond = f" (conditional:{p.conditional_calls})" if p.conditional_calls else ""
        print(f"     {p.name:12s} complexity:{p.complexity_score} "
              f"calls:{p.calls}{cond}")

    jcl_objects = parse_all_jcl(str(jcl_dir))
    jobs = [j.to_dict() for j in jcl_objects]
    for j in jcl_objects:
        print(f"     {j.name:10s} lpar:{j.lpar} deps:{j.depends_on}")

    print("\n🌐  Loading Neo4j...")
    try:
        graph.create_schema()
        graph.load_programs(programs)
        graph.load_jobs(jobs)
        graph.load_relationships(programs, jobs)
        s = graph.stats()
        print(f"     ✅  {s}")
    except Exception as e:
        print(f"     ⚠️  Neo4j error: {e}")

    # ── Docs → ChromaDB ─────────────────────────────────────────
    print("\n🔍  Embedding runbooks into ChromaDB...")
    docs_dir = ROOT / "data" / "docs"
    total = 0
    for f in list(docs_dir.glob("*.md")) + list(docs_dir.glob("*.txt")):
        try:
            n = vector_store.ingest_file(str(f))
            print(f"     {f.name}: {n} chunks")
            total += n
        except Exception as e:
            print(f"     ⚠️  {f.name}: {e}")

    print(f"\n{'='*55}")
    print(f"  ✅  Ingestion complete")
    print(f"      Programs:{len(programs)}  Jobs:{len(jobs)}  "
          f"Vector chunks:{total}")
    print(f"{'='*55}\n")


if __name__ == "__main__":
    run()
