      *================================================================
      * PROGRAM:     CUSTMGMT
      * AUTHOR:      VIJAY-ADITYA
      * DATE:        2017-11-08
      * DESCRIPTION: CUSTOMER PROFILE MANAGEMENT
      *              CALLED BY: BILLING (plan sync), REPORTING (counts)
      *              READS:     CUST.MASTER.DATA, PLAN.TABLE.DATA
      *              WRITES:    CUST.MASTER.DATA (plan updates)
      *================================================================
       IDENTIFICATION DIVISION.
       PROGRAM-ID. CUSTMGMT.
       AUTHOR. VIJAY-ADITYA.
       DATE-WRITTEN. 2017-11-08.

       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT CUST-PROFILE ASSIGN TO 'CUST.MASTER.DATA'
                               ORGANIZATION IS INDEXED
                               ACCESS MODE IS RANDOM
                               RECORD KEY IS CP-CUST-ID.
           SELECT PLAN-TABLE   ASSIGN TO 'PLAN.TABLE.DATA'
                               ORGANIZATION IS INDEXED
                               ACCESS MODE IS RANDOM
                               RECORD KEY IS PT-PLAN-CODE.

       DATA DIVISION.
       FILE SECTION.
       FD  CUST-PROFILE.
       01  CUST-PROFILE-REC.
           05  CP-CUST-ID         PIC 9(10).
           05  CP-PLAN-CODE       PIC X(5).
           05  CP-STATUS          PIC X(2).
           05  CP-LAST-UPDATED    PIC X(10).
           05  CP-CREDIT-SCORE    PIC 9(4).

       FD  PLAN-TABLE.
       01  PLAN-TABLE-REC.
           05  PT-PLAN-CODE       PIC X(5).
           05  PT-PLAN-NAME       PIC X(30).
           05  PT-MONTHLY-FEE     PIC 9(6)V99.
           05  PT-CREDIT-LIMIT    PIC 9(10)V99.

       LINKAGE SECTION.
       01  LK-CUST-ID             PIC 9(10).
       01  LK-NEW-PLAN            PIC X(5).

       WORKING-STORAGE SECTION.
       01  WS-TODAY               PIC X(10).

       PROCEDURE DIVISION USING LK-CUST-ID LK-NEW-PLAN.
       MAIN-PARA.
           OPEN I-O CUST-PROFILE
           OPEN INPUT PLAN-TABLE
           MOVE LK-CUST-ID TO CP-CUST-ID
           READ CUST-PROFILE KEY IS CP-CUST-ID
               INVALID KEY
                   MOVE 'NF' TO CP-STATUS
               NOT INVALID KEY
                   IF LK-NEW-PLAN NOT = SPACES
                       MOVE LK-NEW-PLAN TO CP-PLAN-CODE
                       MOVE FUNCTION CURRENT-DATE(1:10) TO CP-LAST-UPDATED
                       MOVE 'UP' TO CP-STATUS
                       REWRITE CUST-PROFILE-REC
                   END-IF
           END-READ
           CLOSE CUST-PROFILE PLAN-TABLE
           GOBACK.
