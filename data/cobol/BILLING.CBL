      *================================================================
      * PROGRAM:     BILLING
      * AUTHOR:      VIJAY-ADITYA
      * DATE:        2020-07-22
      * DESCRIPTION: CUSTOMER BILLING GENERATION
      *              READS CUSTOMER MASTER AND CHARGE DETAIL FILES
      *              CALLS TAXCALC FOR GST/TAX COMPUTATION
      *              CALLS CREDITVAL FOR LARGE INVOICE VALIDATION
      *              CALLS CUSTMGMT TO UPDATE CUSTOMER PLAN STATUS
      *              NOTE: CHARGE.DETAIL.DATA MAY BE LOCKED BY CICS
      *              AT QUARTER-END — SEE INCIDENT-002
      *================================================================
       IDENTIFICATION DIVISION.
       PROGRAM-ID. BILLING.
       AUTHOR. VIJAY-ADITYA.
       DATE-WRITTEN. 2020-07-22.

       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT CUST-FILE    ASSIGN TO 'CUST.MASTER.DATA'
                               ORGANIZATION IS INDEXED
                               ACCESS MODE IS SEQUENTIAL
                               RECORD KEY IS CUST-ID.
           SELECT CHARGE-FILE  ASSIGN TO 'CHARGE.DETAIL.DATA'
                               ORGANIZATION IS SEQUENTIAL.
           SELECT BILL-OUTPUT  ASSIGN TO 'BILL.OUT.DATA'
                               ORGANIZATION IS SEQUENTIAL.
           SELECT ERR-FILE     ASSIGN TO 'BILLING.ERROR.DATA'
                               ORGANIZATION IS SEQUENTIAL.

       DATA DIVISION.
       FILE SECTION.
       FD  CUST-FILE.
       01  CUST-RECORD.
           05  CUST-ID           PIC 9(10).
           05  CUST-NAME         PIC X(40).
           05  CUST-PLAN         PIC X(5).
           05  CUST-BALANCE      PIC 9(10)V99.
           05  CUST-CREDIT-LIMIT PIC 9(10)V99.

       FD  CHARGE-FILE.
       01  CHARGE-RECORD.
           05  CH-CUST-ID        PIC 9(10).
           05  CH-CHARGE-AMT     PIC 9(8)V99.
           05  CH-CHARGE-DATE    PIC X(10).
           05  CH-CHARGE-TYPE    PIC X(3).

       FD  BILL-OUTPUT.
       01  BILL-RECORD.
           05  BL-CUST-ID        PIC 9(10).
           05  BL-BILL-AMOUNT    PIC 9(10)V99.
           05  BL-TAX-AMOUNT     PIC 9(8)V99.
           05  BL-TOTAL-DUE      PIC 9(10)V99.
           05  BL-STATUS         PIC X(4).

       FD  ERR-FILE.
       01  ERR-RECORD            PIC X(100).

       WORKING-STORAGE SECTION.
           COPY BILLING-COPY.

       01  WS-FLAGS.
           05  WS-EOF-FLAG       PIC X(1) VALUE 'N'.

       01  WS-TOTALS.
           05  WS-BILL-AMOUNT    PIC 9(10)V99 VALUE ZERO.
           05  WS-TAX-AMT        PIC 9(8)V99  VALUE ZERO.
           05  WS-TOTAL-DUE      PIC 9(10)V99 VALUE ZERO.

       01  WS-THRESHOLD          PIC 9(8)V99  VALUE 50000.00.

       PROCEDURE DIVISION.
       MAIN-PARA.
           PERFORM OPEN-FILES-PARA
           PERFORM PROCESS-CUSTOMERS-PARA UNTIL WS-EOF-FLAG = 'Y'
           PERFORM CLOSE-FILES-PARA
           STOP RUN.

       OPEN-FILES-PARA.
           OPEN INPUT  CUST-FILE CHARGE-FILE
           OPEN OUTPUT BILL-OUTPUT ERR-FILE
           READ CUST-FILE
               AT END MOVE 'Y' TO WS-EOF-FLAG
           END-READ.

       PROCESS-CUSTOMERS-PARA.
           PERFORM ACCUMULATE-CHARGES-PARA
           CALL 'TAXCALC'   USING CUST-PLAN
                                  WS-BILL-AMOUNT
                                  WS-TAX-AMT
           IF WS-BILL-AMOUNT > WS-THRESHOLD
               CALL 'CREDITVAL' USING CUST-ID
                                      WS-BILL-AMOUNT
           END-IF
           CALL 'CUSTMGMT'  USING CUST-ID
                                  CUST-PLAN
           COMPUTE WS-TOTAL-DUE = WS-BILL-AMOUNT + WS-TAX-AMT
           PERFORM WRITE-BILL-PARA
           MOVE ZERO TO WS-BILL-AMOUNT WS-TAX-AMT WS-TOTAL-DUE
           READ CUST-FILE
               AT END MOVE 'Y' TO WS-EOF-FLAG
           END-READ.

       ACCUMULATE-CHARGES-PARA.
           READ CHARGE-FILE
               AT END CONTINUE
               NOT AT END
                   IF CH-CUST-ID = CUST-ID
                       ADD CH-CHARGE-AMT TO WS-BILL-AMOUNT
                   END-IF
           END-READ.

       WRITE-BILL-PARA.
           MOVE CUST-ID         TO BL-CUST-ID
           MOVE WS-BILL-AMOUNT  TO BL-BILL-AMOUNT
           MOVE WS-TAX-AMT      TO BL-TAX-AMOUNT
           MOVE WS-TOTAL-DUE    TO BL-TOTAL-DUE
           MOVE 'SENT'          TO BL-STATUS
           WRITE BILL-RECORD.

       CLOSE-FILES-PARA.
           CLOSE CUST-FILE CHARGE-FILE BILL-OUTPUT ERR-FILE.
