"""
simulator.py
Replaces z/OSMF in the prototype.

Every 10 seconds:
  → inserts realistic LPAR MIPS readings into SQLite
  → occasionally generates job completions
  → randomly injects anomalies (spikes, failures) for live demo

LPAR pattern mirrors a real mainframe day:
  00-01h  quiet    LPAR-1~2100  LPAR-2~1200  LPAR-3~1100
  01-03h  PAYJOB   LPAR-1~4100  (payroll processing)
  03-06h  BILLJOB  LPAR-2~5200  (billing run)
  06-09h  NIGHTLY  LPAR-3~7100  (reporting — highest load)
  09-17h  business LPAR-1~4200  LPAR-2~3100  LPAR-3~2800
  17-00h  quiet    all ~2000
"""
import asyncio, random, math
from datetime import datetime
from .stores.smf_store import insert_lpar, insert_job

# ── Realistic MIPS by hour for each LPAR ────────────────────────
BASE = {
    "LPAR-1": [2100,4100,4200,2200,2100,2000,2200,3100,3800,4200,
               4100,4300,3800,4100,4200,4400,4100,3600,2800,2400,
               2200,2100,2000,2100],
    "LPAR-2": [1200,1800,1500,5200,5100,5300,2100,2400,2800,3100,
               3200,3400,2900,3100,3300,3500,3200,2700,2100,1800,
               1600,1500,1400,1300],
    "LPAR-3": [1100,1300,1200,1400,1300,1200,7100,7200,4200,2800,
               2900,3100,2700,2800,2900,3200,2900,2400,1900,1600,
               1400,1300,1200,1200],
}
LABEL = {
    "LPAR-1": "Production-Payments",
    "LPAR-2": "Batch-Processing",
    "LPAR-3": "Customer-Reporting",
}

# ── Anomaly state ────────────────────────────────────────────────
class AnomalyState:
    def __init__(self):
        self.active: dict[str, int] = {}   # anomaly_id → remaining_cycles

    def inject(self, aid: str, cycles: int = 4):
        self.active[aid] = cycles

    def tick(self):
        done = [k for k, v in self.active.items() if v <= 1]
        for k in done: del self.active[k]
        for k in self.active: self.active[k] -= 1

    def has(self, aid: str) -> bool:
        return aid in self.active

_anomaly = AnomalyState()
_cycle   = 0

# ── Job schedule ─────────────────────────────────────────────────
# In the demo, NIGHTLY runs every ~6 minutes, others less often
JOB_SCHEDULE = [
    # (job, lpar, base_elapsed, base_mips, run_every_N_cycles)
    ("NIGHTLY",  "LPAR-3", 141, 7100, 36),   # every 6 min
    ("PAYJOB",   "LPAR-1", 108, 4100, 60),   # every 10 min
    ("BILLJOB",  "LPAR-2", 133, 5200, 72),   # every 12 min
]


async def run_simulator():
    """Background loop — never stops."""
    global _cycle
    await asyncio.sleep(3)   # let FastAPI start first

    while True:
        _cycle += 1
        hour = datetime.now().hour
        _anomaly.tick()

        # ── Randomly inject anomalies ────────────────────────────
        rand = random.random()
        if rand < 0.08:
            _anomaly.inject("lpar3_spike", cycles=4)   # ~40s spike
        elif rand < 0.13:
            _anomaly.inject("rha_risk", cycles=6)
        elif rand < 0.16:
            _anomaly.inject("billjob_fail")            # 1-shot

        # ── Generate LPAR readings ───────────────────────────────
        for lpar, label in LABEL.items():
            base  = BASE[lpar][hour]
            noise = random.gauss(0, base * 0.06)       # ±6% noise
            mips  = max(500, int(base + noise))

            # Apply anomalies
            if lpar == "LPAR-3" and _anomaly.has("lpar3_spike"):
                mips = int(mips * 1.35)                # +35%
            if _anomaly.has("rha_risk"):
                mips = int(mips * 1.20)                # all LPARs +20%

            cpu = round(min(99.9, mips / BASE[lpar][hour] * 65 +
                            random.gauss(0, 3)), 1)
            if lpar == "LPAR-3" and _anomaly.has("lpar3_spike"):
                cpu = round(min(99.9, cpu * 1.4), 1)

            insert_lpar(lpar, label, int(mips * 0.92), mips, cpu)

        # ── Generate job completions ─────────────────────────────
        for job, lpar, base_elapsed, base_mips, every_n in JOB_SCHEDULE:
            if _cycle % every_n != 0:
                continue

            is_failure = (job == "BILLJOB" and _anomaly.has("billjob_fail"))
            elapsed = base_elapsed + random.gauss(0, base_elapsed * 0.08)
            mips    = base_mips    + random.gauss(0, base_mips * 0.05)

            if is_failure:
                elapsed *= 2.1   # double runtime from contention
                mips    *= 1.6
                insert_job(
                    job=job, lpar=lpar,
                    elapsed_mins=round(elapsed, 1),
                    mips=int(mips), rc=8,
                    status="FAILED",
                    error="CHARGE.DETAIL.DATA HELD BY CICS TRANSACTION CHRG. DATASET CONTENTION.",
                )
                _anomaly.active.pop("billjob_fail", None)
            else:
                insert_job(
                    job=job, lpar=lpar,
                    elapsed_mins=round(elapsed, 1),
                    mips=int(mips), rc=0,
                    status="SUCCESS",
                )

        await asyncio.sleep(10)
