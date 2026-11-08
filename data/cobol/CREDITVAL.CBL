      *================================================================
      * PROGRAM:     CREDITVAL
      * AUTHOR:      VIJAY-ADITYA
      * DATE:        2015-09-12
      * DESCRIPTION: CREDIT LIMIT VALIDATION — RBI COMPLIANCE MODULE
      *              CALLED BY: PAYROLL (advance), BILLING (invoice),
      *                         CUSTMGMT (plan upgrade)
      *
      *              BUILT PER RBI CIRCULAR 2015/243:
      *              Real-time credit validation mandatory for all
      *              customer transactions above INR 50,000.
      *
      *              EXCEPTION CODES:
      *              CE01 = Credit limit breached
      *                     → Risk team must review within 24 hours
      *              CE02 = Customer flagged for review
      *                     → Compliance team must be notified
      *              ER   = Record not found in CREDIT.MASTER.DATA
      *
      *              WARNING: DO NOT MERGE THIS LOGIC INTO CALLING
      *              PROGRAMS. Must remain standalone for RBI audit.
      *================================================================
       IDENTIFICATION DIVISION.
       PROGRAM-ID. CREDITVAL.
       AUTHOR. VIJAY-ADITYA.
       DATE-WRITTEN. 2015-09-12.

       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT CREDIT-MASTER ASSIGN TO 'CREDIT.MASTER.DATA'
                                ORGANIZATION IS INDEXED
                                ACCESS MODE IS RANDOM
                                RECORD KEY IS CM-CUST-ID.
           SELECT AUDIT-LOG     ASSIGN TO 'CREDIT.AUDIT.LOG'
                                ORGANIZATION IS SEQUENTIAL.

       DATA DIVISION.
       FILE SECTION.
       FD  CREDIT-MASTER.
       01  CREDIT-RECORD.
           05  CM-CUST-ID         PIC 9(10).
           05  CM-CREDIT-LIMIT    PIC 9(10)V99.
           05  CM-CURRENT-USAGE   PIC 9(10)V99.
           05  CM-STATUS          PIC X(4).
           05  CM-REVIEW-FLAG     PIC X(1).

       FD  AUDIT-LOG.
       01  AUDIT-RECORD.
           05  AL-TIMESTAMP       PIC X(26).
           05  AL-CUST-ID         PIC 9(10).
           05  AL-AMOUNT          PIC 9(10)V99.
           05  AL-RESULT          PIC X(4).

       LINKAGE SECTION.
       01  LK-CUST-ID             PIC 9(10).
       01  LK-AMOUNT              PIC 9(10)V99.

       WORKING-STORAGE SECTION.
       01  WS-EXCEPTION-CODE      PIC X(4) VALUE SPACES.
       01  WS-PROJECTED-USAGE     PIC 9(10)V99.

       PROCEDURE DIVISION USING LK-CUST-ID LK-AMOUNT.
       MAIN-PARA.
           MOVE LK-CUST-ID TO CM-CUST-ID
           OPEN INPUT  CREDIT-MASTER
           OPEN EXTEND AUDIT-LOG
           READ CREDIT-MASTER KEY IS CM-CUST-ID
               INVALID KEY
                   MOVE 'ER'   TO CM-STATUS
                   MOVE 'ER'   TO WS-EXCEPTION-CODE
               NOT INVALID KEY
                   COMPUTE WS-PROJECTED-USAGE =
                       CM-CURRENT-USAGE + LK-AMOUNT
                   IF WS-PROJECTED-USAGE > CM-CREDIT-LIMIT
                       MOVE 'CE01' TO WS-EXCEPTION-CODE
                       MOVE 'OVER' TO CM-STATUS
                   ELSE IF CM-REVIEW-FLAG = 'Y'
                       MOVE 'CE02' TO WS-EXCEPTION-CODE
                       MOVE 'REVW' TO CM-STATUS
                   ELSE
                       MOVE 'OK'   TO CM-STATUS
                       MOVE SPACES TO WS-EXCEPTION-CODE
                       ADD LK-AMOUNT TO CM-CURRENT-USAGE
                       REWRITE CREDIT-RECORD
                   END-IF
           END-READ
           PERFORM WRITE-AUDIT-PARA
           CLOSE CREDIT-MASTER AUDIT-LOG
           GOBACK.

       WRITE-AUDIT-PARA.
           MOVE FUNCTION CURRENT-DATE TO AL-TIMESTAMP
           MOVE LK-CUST-ID            TO AL-CUST-ID
           MOVE LK-AMOUNT             TO AL-AMOUNT
           MOVE CM-STATUS             TO AL-RESULT
           WRITE AUDIT-RECORD.
