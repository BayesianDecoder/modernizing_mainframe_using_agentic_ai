      *================================================================
      * PROGRAM:     PAYROLL
      * AUTHOR:      VIJAY-ADITYA
      * DATE:        2019-03-15
      * DESCRIPTION: MONTHLY PAYROLL PROCESSING FOR 50,000 EMPLOYEES
      *              READS EMPLOYEE MASTER AND TIMESHEET DATA
      *              CALLS TAXCALC FOR TAX COMPUTATION
      *              CALLS CREDITVAL FOR SALARY ADVANCE VALIDATION
      *================================================================
       IDENTIFICATION DIVISION.
       PROGRAM-ID. PAYROLL.
       AUTHOR. VIJAY-ADITYA.
       DATE-WRITTEN. 2019-03-15.

       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT EMP-FILE    ASSIGN TO 'EMP.MASTER.DATA'
                              ORGANIZATION IS SEQUENTIAL.
           SELECT TIME-FILE   ASSIGN TO 'TIME.SHEET.DATA'
                              ORGANIZATION IS SEQUENTIAL.
           SELECT PAY-OUTPUT  ASSIGN TO 'PAYROLL.OUT.DATA'
                              ORGANIZATION IS SEQUENTIAL.
           SELECT AUDIT-FILE  ASSIGN TO 'AUDIT.DATA'
                              ORGANIZATION IS SEQUENTIAL.

       DATA DIVISION.
       FILE SECTION.
       FD  EMP-FILE.
       01  EMP-RECORD.
           05  EMP-ID            PIC 9(8).
           05  EMP-NAME          PIC X(30).
           05  EMP-GRADE         PIC X(3).
           05  EMP-HOURLY-RATE   PIC 9(5)V99.
           05  EMP-DEPT          PIC X(10).
           05  EMP-ADVANCE-AMT   PIC 9(7)V99.

       FD  TIME-FILE.
       01  TIME-RECORD.
           05  TM-EMP-ID         PIC 9(8).
           05  TM-HOURS-WORKED   PIC 9(3)V99.
           05  TM-OVERTIME-HRS   PIC 9(2)V99.

       FD  PAY-OUTPUT.
       01  PAY-RECORD.
           05  PR-EMP-ID         PIC 9(8).
           05  PR-GROSS-PAY      PIC 9(8)V99.
           05  PR-TAX-AMOUNT     PIC 9(6)V99.
           05  PR-NET-PAY        PIC 9(8)V99.
           05  PR-STATUS         PIC X(2).

       FD  AUDIT-FILE.
       01  AUDIT-RECORD          PIC X(200).

       WORKING-STORAGE SECTION.
           COPY PAYROLL-COPY.

       01  WS-FLAGS.
           05  WS-EOF-FLAG       PIC X(1) VALUE 'N'.
           05  WS-ERROR-FLAG     PIC X(1) VALUE 'N'.

       01  WS-COUNTERS.
           05  WS-RECORDS-READ   PIC 9(6) VALUE ZERO.
           05  WS-RECORDS-PROC   PIC 9(6) VALUE ZERO.
           05  WS-ERRORS         PIC 9(4) VALUE ZERO.

       01  WS-CALC.
           05  WS-GROSS-PAY      PIC 9(8)V99 VALUE ZERO.
           05  WS-TAX-AMOUNT     PIC 9(6)V99 VALUE ZERO.
           05  WS-NET-PAY        PIC 9(8)V99 VALUE ZERO.
           05  WS-OVERTIME-MULT  PIC 9(1)V99 VALUE 1.50.

       PROCEDURE DIVISION.
       MAIN-PARA.
           PERFORM INIT-PARA
           PERFORM PROCESS-PARA UNTIL WS-EOF-FLAG = 'Y'
           PERFORM CLOSE-PARA
           STOP RUN.

       INIT-PARA.
           OPEN INPUT  EMP-FILE
           OPEN INPUT  TIME-FILE
           OPEN OUTPUT PAY-OUTPUT
           OPEN EXTEND AUDIT-FILE
           READ EMP-FILE
               AT END MOVE 'Y' TO WS-EOF-FLAG
           END-READ.

       PROCESS-PARA.
           ADD 1 TO WS-RECORDS-READ
           COMPUTE WS-GROSS-PAY =
               TM-HOURS-WORKED * EMP-HOURLY-RATE +
               TM-OVERTIME-HRS * EMP-HOURLY-RATE * WS-OVERTIME-MULT
           CALL 'TAXCALC' USING EMP-GRADE
                                WS-GROSS-PAY
                                WS-TAX-AMOUNT
           IF EMP-ADVANCE-AMT > ZERO
               CALL 'CREDITVAL' USING EMP-ID
                                      EMP-ADVANCE-AMT
           END-IF
           COMPUTE WS-NET-PAY = WS-GROSS-PAY - WS-TAX-AMOUNT
           PERFORM WRITE-OUTPUT-PARA
           READ EMP-FILE
               AT END MOVE 'Y' TO WS-EOF-FLAG
           END-READ.

       WRITE-OUTPUT-PARA.
           MOVE EMP-ID         TO PR-EMP-ID
           MOVE WS-GROSS-PAY   TO PR-GROSS-PAY
           MOVE WS-TAX-AMOUNT  TO PR-TAX-AMOUNT
           MOVE WS-NET-PAY     TO PR-NET-PAY
           MOVE 'OK'           TO PR-STATUS
           WRITE PAY-RECORD
           ADD 1 TO WS-RECORDS-PROC.

       CLOSE-PARA.
           CLOSE EMP-FILE TIME-FILE PAY-OUTPUT AUDIT-FILE
           DISPLAY 'PAYROLL COMPLETE. PROCESSED: ' WS-RECORDS-PROC
                   ' ERRORS: ' WS-ERRORS.
