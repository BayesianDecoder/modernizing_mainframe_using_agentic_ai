      *================================================================
      * PROGRAM:     REPORTING
      * AUTHOR:      VIJAY-ADITYA
      * DATE:        2021-02-14
      * DESCRIPTION: NIGHTLY CONSOLIDATED REPORT GENERATION
      *              READS PAYROLL AND BILLING OUTPUT FILES
      *              CALLS CUSTMGMT TO SYNC CUSTOMER COUNTS
      *              WRITES MANAGEMENT REPORT AND SUMMARY DASHBOARD
      *================================================================
       IDENTIFICATION DIVISION.
       PROGRAM-ID. REPORTING.
       AUTHOR. VIJAY-ADITYA.
       DATE-WRITTEN. 2021-02-14.

       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT PAY-INPUT    ASSIGN TO 'PAYROLL.OUT.DATA'
                               ORGANIZATION IS SEQUENTIAL.
           SELECT BILL-INPUT   ASSIGN TO 'BILL.OUT.DATA'
                               ORGANIZATION IS SEQUENTIAL.
           SELECT RPT-OUTPUT   ASSIGN TO 'REPORT.OUT.DATA'
                               ORGANIZATION IS SEQUENTIAL.
           SELECT DASH-OUTPUT  ASSIGN TO 'DASHBOARD.DATA'
                               ORGANIZATION IS SEQUENTIAL.

       DATA DIVISION.
       FILE SECTION.
       FD  PAY-INPUT.
       01  PAY-RECORD.
           05  PR-EMP-ID         PIC 9(8).
           05  PR-NET-PAY        PIC 9(8)V99.
           05  PR-STATUS         PIC X(2).

       FD  BILL-INPUT.
       01  BILL-RECORD.
           05  BL-CUST-ID        PIC 9(10).
           05  BL-TOTAL-DUE      PIC 9(10)V99.
           05  BL-STATUS         PIC X(4).

       FD  RPT-OUTPUT.
       01  RPT-LINE              PIC X(132).

       FD  DASH-OUTPUT.
       01  DASH-RECORD           PIC X(500).

       WORKING-STORAGE SECTION.
       01  WS-TOTALS.
           05  WS-TOTAL-PAYROLL  PIC 9(12)V99 VALUE ZERO.
           05  WS-TOTAL-BILLING  PIC 9(12)V99 VALUE ZERO.
           05  WS-EMP-COUNT      PIC 9(6)     VALUE ZERO.
           05  WS-CUST-COUNT     PIC 9(6)     VALUE ZERO.
           05  WS-GRAND-TOTAL    PIC 9(14)V99 VALUE ZERO.

       01  WS-FLAGS.
           05  WS-PAY-EOF        PIC X(1) VALUE 'N'.
           05  WS-BILL-EOF       PIC X(1) VALUE 'N'.

       01  WS-DUMMY-ID           PIC 9(10) VALUE ZERO.
       01  WS-DUMMY-PLAN         PIC X(5)  VALUE SPACES.

       PROCEDURE DIVISION.
       MAIN-PARA.
           CALL 'CUSTMGMT' USING WS-DUMMY-ID WS-DUMMY-PLAN
           OPEN INPUT  PAY-INPUT BILL-INPUT
           OPEN OUTPUT RPT-OUTPUT DASH-OUTPUT
           PERFORM READ-PAYROLL-PARA UNTIL WS-PAY-EOF = 'Y'
           PERFORM READ-BILLING-PARA UNTIL WS-BILL-EOF = 'Y'
           COMPUTE WS-GRAND-TOTAL = WS-TOTAL-PAYROLL + WS-TOTAL-BILLING
           PERFORM WRITE-REPORTS-PARA
           CLOSE PAY-INPUT BILL-INPUT RPT-OUTPUT DASH-OUTPUT
           STOP RUN.

       READ-PAYROLL-PARA.
           READ PAY-INPUT
               AT END MOVE 'Y' TO WS-PAY-EOF
               NOT AT END
                   ADD PR-NET-PAY TO WS-TOTAL-PAYROLL
                   ADD 1 TO WS-EMP-COUNT
           END-READ.

       READ-BILLING-PARA.
           READ BILL-INPUT
               AT END MOVE 'Y' TO WS-BILL-EOF
               NOT AT END
                   ADD BL-TOTAL-DUE TO WS-TOTAL-BILLING
                   ADD 1 TO WS-CUST-COUNT
           END-READ.

       WRITE-REPORTS-PARA.
           MOVE SPACES TO RPT-LINE
           STRING 'TOTAL PAYROLL: '   WS-TOTAL-PAYROLL
                  ' TOTAL BILLING: '  WS-TOTAL-BILLING
                  ' GRAND TOTAL: '    WS-GRAND-TOTAL
               INTO RPT-LINE
           WRITE RPT-LINE.
