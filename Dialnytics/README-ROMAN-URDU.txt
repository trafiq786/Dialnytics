==========================================================
  CRM IMPORT 500 ERROR FIX ("Internal Server Error" / JSON)
==========================================================

MASLA
-----
Sheet upload par "Unexpected token 'I', Internal S... is not valid JSON"
= server 500 (Internal Server Error) de raha tha.

WAJAH (asli bug)
----------------
Import dedup mein existing numbers load karte waqt code ne dict row ko
integer-index kiya:  {row[0] for row in fetchall()}  -- par rows DICT hain
(row_factory=dict_row), is liye row[0] -> KeyError -> 500.

Isi liye:
 - PEHLI dafa (jab CRM KHAALI thi) import chal gaya tha -- fetchall khaali,
   loop chala hi nahi, error aaya hi nahi.
 - AB (jab CRM mein leads hain) dedup SELECT rows deta hai -> row[0] ->
   crash -> har upload 500.

FIX
---
row[0]  ->  row["phone"]   (ek line)

AB
--
Sheet upload phir se chalega -- naye unique numbers add, duplicate skip.

BADLI FILE
----------
  backend/main.py   (one-line: row["phone"])

DEPLOY -> CRM page Ctrl+F5 -> sheet dobara upload karo.
