//BILLJOB  JOB (ACCT-BIL),'CUSTOMER BILLING RUN',
//             CLASS=A,MSGCLASS=X,NOTIFY=&SYSUID
//*
//* JOB:      BILLJOB
//* SCHEDULE: 1ST OF EVERY MONTH AT 03:30 AM
//* LPAR:     LPAR-2
//* OWNER:    BILLING-TEAM
//* SLA:      MUST COMPLETE BY 06:00 AM
//* DEPENDS:  PAYJOB
//* TRIGGERS: NIGHTLY
//*
//* DESCRIPTION:
//*   Runs BILLING.CBL to generate monthly invoices for all customers.
//*   Reads CHARGE.DETAIL.DATA which may be held by CICS at quarter-end.
//*   Calls TAXCALC for GST, CREDITVAL for invoice validation,
//*   CUSTMGMT to update customer plan status.
//*
//* KNOWN ISSUES:
//*   INCIDENT-002 (Apr 2024, Jun 2024): CHARGE.DETAIL.DATA held by
//*   CICS transaction CHRG at quarter-end. Causes RC=8 and 4+ hour
//*   delay. Fix: CEMT CANCEL TASK(CHRG) then restart.
//*   Permanent fix: delay BILLJOB to 04:00 AM on quarter-end months
//*   (March, June, September, December).
//*   — NOTE FROM RAMESH (retiring Dec 2024): This happens EVERY
//*     quarter end. Please implement the permanent fix.
//*
//JOBLIB   DD DSN=PROD.LOADLIB,DISP=SHR
//*
//****** STEP 010 — AWAIT PAYJOB COMPLETION ******
//STEP010  EXEC PGM=IEFBR14
//PAYCHECK DD DSN=PAYROLL.OUT.DATA,DISP=SHR
//*
//****** STEP 020 — BILLING RUN ******
//STEP020  EXEC PGM=BILLING,
//             REGION=256M,
//             COND=(0,NE,STEP010),
//             PARM='FULL-BILL'
//STEPLIB  DD DSN=PROD.LOADLIB,DISP=SHR
//CUSTFILE DD DSN=CUST.MASTER.DATA,
//            DISP=SHR
//CHARGEIN DD DSN=CHARGE.DETAIL.DATA,
//            DISP=SHR
//TAXRATES DD DSN=TAX.RATE.DATA,
//            DISP=SHR
//CREDMAST DD DSN=CREDIT.MASTER.DATA,
//            DISP=SHR
//PLANFILE DD DSN=PLAN.TABLE.DATA,
//            DISP=SHR
//BILLOUT  DD DSN=BILL.OUT.DATA,
//            DISP=(NEW,CATLG,DELETE),
//            SPACE=(TRK,(200,20),RLSE),
//            DCB=(RECFM=FB,LRECL=300,BLKSIZE=0)
//ERRFILE  DD DSN=BILLING.ERROR.DATA,
//            DISP=(NEW,CATLG,DELETE),
//            SPACE=(TRK,(10,5))
//SYSOUT   DD SYSOUT=*
//SYSPRINT DD SYSOUT=*
//SYSUDUMP DD SYSOUT=*
//*
