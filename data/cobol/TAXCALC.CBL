      *================================================================
      * PROGRAM:     TAXCALC
      * AUTHOR:      VIJAY-ADITYA
      * DATE:        1998-04-01
      * DESCRIPTION: TAX SLAB CALCULATION — SHARED MODULE
      *              CALLED BY: PAYROLL, BILLING
      *              READS:     TAX.RATE.DATA (indexed by grade/plan)
      *
      *              NOTE (ADR-001, 1998-04-01):
      *              Kept as separate module because tax slabs change
      *              every budget year. One recompile here updates all
      *              callers. DO NOT inline this logic into PAYROLL
      *              or BILLING — that would require syncing two files
      *              every budget cycle.
      *================================================================
       IDENTIFICATION DIVISION.
       PROGRAM-ID. TAXCALC.
       AUTHOR. VIJAY-ADITYA.
       DATE-WRITTEN. 1998-04-01.

       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT TAX-FILE ASSIGN TO 'TAX.RATE.DATA'
                           ORGANIZATION IS INDEXED
                           ACCESS MODE IS RANDOM
                           RECORD KEY IS TR-GRADE.

       DATA DIVISION.
       FILE SECTION.
       FD  TAX-FILE.
       01  TAX-RECORD.
           05  TR-GRADE          PIC X(5).
           05  TR-RATE           PIC 9(2)V99.
           05  TR-SLAB-MIN       PIC 9(8)V99.
           05  TR-SLAB-MAX       PIC 9(8)V99.
           05  TR-SURCHARGE      PIC 9(1)V99.

       LINKAGE SECTION.
       01  LK-GRADE              PIC X(5).
       01  LK-GROSS-AMOUNT       PIC 9(8)V99.
       01  LK-TAX-AMOUNT         PIC 9(6)V99.

       WORKING-STORAGE SECTION.
       01  WS-EFFECTIVE-RATE     PIC 9(2)V99.
       01  WS-SURCHARGE-AMT      PIC 9(4)V99.

       PROCEDURE DIVISION USING LK-GRADE
                                LK-GROSS-AMOUNT
                                LK-TAX-AMOUNT.
       MAIN-PARA.
           MOVE LK-GRADE TO TR-GRADE
           READ TAX-FILE KEY IS TR-GRADE
               INVALID KEY
                   MOVE ZERO TO LK-TAX-AMOUNT
               NOT INVALID KEY
                   COMPUTE LK-TAX-AMOUNT =
                       LK-GROSS-AMOUNT * TR-RATE / 100
                   IF LK-GROSS-AMOUNT > TR-SLAB-MAX
                       COMPUTE WS-SURCHARGE-AMT =
                           LK-TAX-AMOUNT * TR-SURCHARGE / 100
                       ADD WS-SURCHARGE-AMT TO LK-TAX-AMOUNT
                   END-IF
           END-READ
           GOBACK.
