# MAIA Mainframe Operations Runbook
## Architecture Decision Records + Incident History + SOPs

---

## ARCHITECTURE DECISION RECORDS (ADRs)

### ADR-001: TAXCALC as a Separate Shared Module (1998-04-01)
**Status:** Active  
**Decision:** Keep tax calculation logic in a dedicated COBOL module called TAXCALC, not inlined into PAYROLL or BILLING.  
**Context:** Both PAYROLL and BILLING need to compute tax. India's Finance Ministry changes tax slabs annually in the budget. In 1997, both programs had their own tax logic and we had to update two programs and run two sets of tests every budget year — and they got out of sync once, causing a reconciliation issue.  
**Decision:** Extract into TAXCALC. One source of truth. One recompile per budget cycle.  
**Consequences:** Any program needing tax computation MUST CALL TAXCALC. Do not re-implement tax logic inline. When tax slabs change, only TAXCALC needs to be changed and regression-tested against PAYROLL and BILLING outputs.  
**Current callers:** PAYROLL, BILLING  
**Signed:** Architecture Board, April 1998

---

### ADR-002: CREDITVAL Built per RBI Mandate (2015-09-12)
**Status:** Active — Regulatory requirement  
**Decision:** Create CREDITVAL as a standalone module for real-time credit limit validation.  
**Context:** RBI Circular 2015/243 mandated that all banks must perform real-time credit limit checks for customer transactions above INR 50,000. The check must be auditable and traceable.  
**Decision:** CREDITVAL is a separate module that (a) validates against CREDIT.MASTER.DATA, (b) writes an audit trail to CREDIT.AUDIT.LOG, and (c) returns exception codes to the caller.  
**Exception codes:**
- CE01 = Credit limit breached → Risk team must review within 24 hours — compliance requirement
- CE02 = Customer flagged for manual review → Compliance team notification required  
- ER = Record not found in CREDIT.MASTER.DATA → Error handling required by caller

**WARNING:** CREDITVAL must remain a standalone module for RBI audit inspection. Do not merge its logic into PAYROLL, BILLING, or CUSTMGMT. Any change to CREDITVAL requires written sign-off from Risk & Compliance and a 30-day parallel run.  
**Current callers:** PAYROLL (salary advance), BILLING (large invoices), CUSTMGMT (plan upgrades)  
**Signed:** Risk & Compliance, September 2015

---

## INCIDENT RECORDS

### INCIDENT-001: PAYJOB Space Exhaustion (2024-01-01)
**Severity:** HIGH  
**Time:** 01:17 AM  
**Duration:** 2 hours 40 minutes  
**Impact:** Payroll delayed for 50,000 employees. Month-end payroll missed the 03:00 AM SLA.  
**Return Code:** S B37 — dataset space exhausted  
**Root Cause:** EMP.MASTER.DATA record count reached 47,832 during the run. The SPACE=(TRK,(100,10)) allocation in PAYJOB STEP010 for PAYROLL.OUT.DATA was insufficient for the current employee count. The dataset filled completely at 47,832 records and the job abended.  
**Fix Applied:** Increased SPACE allocation in PAYJOB from (TRK,(100,10)) to (TRK,(200,20)) via a JCL change request.  
**Restart Procedure:** Delete PAYROLL.OUT.DATA, fix JCL, resubmit PAYJOB from the beginning. Do not restart mid-step — PAYROLL is not checkpoint-restartable and will duplicate records.  
**Resolved by:** Ramesh Kumar (ramesh.kumar@company.com)  
**Prevention:** Monitor EMP.MASTER.DATA record count monthly. Alert when it exceeds 45,000 records so JCL can be updated before month-end.

---

### INCIDENT-002: BILLJOB Dataset Contention (2024-04-01 and 2024-06-01)
**Severity:** CRITICAL  
**First occurrence:** 2024-04-01 03:44 AM  
**Duration:** 4 hours 17 minutes  
**Second occurrence:** 2024-06-01 (same root cause)  
**Impact:** 8,000 customer bills delayed. NIGHTLY also delayed. Business reports not available at 09:00 AM. Customer helpdesk calls spiked by 340%.  
**Return Code:** RC=8 — dataset not available  
**Root Cause:** CHARGE.DETAIL.DATA was held in exclusive enqueue by CICS online transaction CHRG (charge posting transaction). At quarter-end, CICS processes a high volume of pending charge records from the previous quarter. This process ran until 04:12 AM on April 1. BILLJOB attempted to open CHARGE.DETAIL.DATA at 03:30 AM and waited, retrying every 3 seconds. The retries inflated CPU usage on LPAR-2 and caused BILLJOB's elapsed time to double from 133 minutes to 257 minutes.  
**Immediate Fix:** Issue CEMT CANCEL TASK(TRAN(CHRG)) from TSO or CICS master terminal to release the enqueue. Wait 2 minutes for cleanup. Then restart BILLJOB from STEP020 (STEP010 only checks file availability, safe to skip on restart).  
**Permanent Recommendation:** Change BILLJOB start time from 03:30 AM to 04:00 AM on quarter-end months (March, June, September, December). CICS charge posting is always complete by 04:00 AM even on the heaviest quarter-end days. This has been verified against CICS transaction logs for the last 3 years.  
**Note from Ramesh Kumar (retiring December 2024):** This happens EVERY quarter end without fail. I have reported it to the scheduling team in March, April, and June 2024. Please implement the 04:00 AM start time change before I leave. The scheduling request takes 2 weeks to process through CAB so start it now.  
**Resolved by:** Ramesh Kumar

---

### INCIDENT-003: NIGHTLY CPU Spike on LPAR-3 (2024-06-15)
**Severity:** MEDIUM  
**Time:** 07:30 AM  
**Duration:** 90 minutes of degraded performance  
**Impact:** NIGHTLY ran 45 minutes late. Business reports not available until 09:45 AM. No data loss.  
**Return Code:** RC=0 (completed successfully but late)  
**Root Cause:** LPAR-3 peaked at 98.6% CPU utilisation between 07:30 and 08:30 AM. NIGHTLY (reporting job, runs on LPAR-3 from 06:30 AM) was running simultaneously with a set of IEBGENER utility jobs that process month-end archive files. The IEBGENER jobs were scheduled at 07:30 AM by the archive team without checking LPAR-3 workload.  
**Fix Applied:** Moved IEBGENER archive jobs to 05:00 AM window, which is consistently quiet on LPAR-3. LPAR-3 is busy 06:30-09:00 AM (NIGHTLY window) and 09:00 AM onwards (business hours reporting). 05:00 AM is consistently below 20% CPU.  
**Prevention:** Any new batch jobs scheduled on LPAR-3 must be reviewed against the NIGHTLY window (06:30-09:00 AM) and the business hours window (09:00 AM-17:00 PM). LPAR-3 has no spare capacity during these periods.

---

## STANDARD OPERATING PROCEDURES

### SOP-001: BILLJOB Failure Response
When BILLJOB fails with RC=8:
1. Check SYSOUT for exact error message
2. If message contains "DATA SET NOT AVAILABLE" or "ENQUEUE":
   a. Log into CICS master terminal
   b. Issue: CEMT INQ TASK to find the holding task
   c. If TRAN=CHRG is shown: CEMT CANCEL TASK(TRAN(CHRG))
   d. Wait 2 minutes for enqueue to release
   e. Restart BILLJOB from STEP020 (not STEP010)
3. If BILLJOB restart will complete after 10:00 AM, notify BILLING-TEAM immediately
4. NIGHTLY will be delayed by the same amount — notify OPS-TEAM
5. If delay exceeds 4 hours, escalate to duty manager

### SOP-002: PAYJOB Emergency Restart
When PAYJOB fails mid-run:
1. NEVER restart PAYROLL mid-step — it will re-process records and duplicate pay
2. Always restart from the very beginning of STEP010
3. Before restarting: delete PAYROLL.OUT.DATA completely
4. Check that EMP.MASTER.DATA is not locked by any other process
5. Notify PAYROLL-TEAM immediately if restart is needed — they manage pay disbursement timing
6. Restart cannot happen on the 1st of the month after 06:00 AM — payroll must be complete before bank systems open

### SOP-003: High LPAR CPU Response
When any LPAR exceeds 85% CPU utilisation:
1. Check which jobs are currently running on that LPAR (SDSF / D A,L command)
2. If NIGHTLY is running and IEBGENER utilities are also running on LPAR-3, cancel IEBGENER — they can be rerun at 05:00 AM
3. If BILLJOB is running late and causing LPAR-2 spike, check for CICS contention (see SOP-001)
4. If PAYJOB is causing LPAR-1 spike, do not cancel — payroll has highest business priority
5. Escalate to capacity planning team if any LPAR exceeds 90% CPU for more than 30 minutes
