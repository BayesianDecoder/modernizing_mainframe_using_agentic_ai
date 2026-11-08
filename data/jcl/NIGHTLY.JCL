//NIGHTLY  JOB (ACCT-RPT),'NIGHTLY REPORTING',
//             CLASS=B,MSGCLASS=X,NOTIFY=&SYSUID
//*
//* JOB:      NIGHTLY
//* SCHEDULE: EVERY NIGHT AT 06:30 AM
//* LPAR:     LPAR-3
//* OWNER:    OPS-TEAM
//* SLA:      MUST COMPLETE BY 09:00 AM
//* DEPENDS:  PAYJOB, BILLJOB
//* TRIGGERS: NONE
//*
//* DESCRIPTION:
//*   Runs REPORTING.CBL to generate the nightly management report
//*   and dashboard summary. Reads PAYROLL.OUT.DATA and BILL.OUT.DATA
//*   from previous jobs. Calls CUSTMGMT for customer count sync.
//*
//* KNOWN ISSUES:
//*   INCIDENT-003 (Jun 2024): LPAR-3 peaked at 98.6% CPU between
//*   07:30 and 08:30 AM due to overlap with IEBGENER utility jobs.
//*   IEBGENER moved to 05:00 AM window.
//*   Note: When BILLJOB runs late (quarter-end), NIGHTLY also runs
//*   late and misses 09:00 AM SLA, delaying business reports.
//*
//JOBLIB   DD DSN=PROD.LOADLIB,DISP=SHR
//*
//****** STEP 010 — CHECK PREREQUISITES ******
//STEP010  EXEC PGM=IEFBR14
//PAYINPUT DD DSN=PAYROLL.OUT.DATA,DISP=SHR
//BILLINPUT DD DSN=BILL.OUT.DATA,DISP=SHR
//*
//****** STEP 020 — REPORTING RUN ******
//STEP020  EXEC PGM=REPORTING,
//             REGION=384M,
//             COND=(0,NE,STEP010),
//             PARM='NIGHTLY,ALL-REPORTS'
//STEPLIB  DD DSN=PROD.LOADLIB,DISP=SHR
//PAYDATA  DD DSN=PAYROLL.OUT.DATA,
//            DISP=SHR
//BILLDATA DD DSN=BILL.OUT.DATA,
//            DISP=SHR
//CUSTFILE DD DSN=CUST.MASTER.DATA,
//            DISP=SHR
//PLANFILE DD DSN=PLAN.TABLE.DATA,
//            DISP=SHR
//RPTOUT   DD DSN=REPORT.OUT.DATA,
//            DISP=(NEW,CATLG,DELETE),
//            SPACE=(TRK,(50,10),RLSE),
//            DCB=(RECFM=FBA,LRECL=133,BLKSIZE=0)
//DASHOUT  DD DSN=DASHBOARD.DATA,
//            DISP=(NEW,CATLG,DELETE),
//            SPACE=(TRK,(10,5))
//SYSOUT   DD SYSOUT=*
//SYSPRINT DD SYSOUT=*
//SYSUDUMP DD SYSOUT=*
//*
