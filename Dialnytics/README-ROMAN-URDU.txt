==========================================================
  CRM IMPORT v2 — FN/LN format + BADE files (lakhs rows)
==========================================================

AB KYA SUPPORT HUA
------------------
1) NAAM 2 columns mein (First/Last): FN, LN, FNAME, LNAME, FIRST, LAST,
   GIVENNAME, SURNAME -> khud jud kar "Full Name" ban jata hai.
   (jaise FN=Max, LN=Tromba -> "Max Tromba")

2) ADDRESS columns (ADDR/ADDRESS/STREET + CITY + ST/STATE + ZIP/ZIP4)
   -> agar notes khaali ho to ye address lead ke NOTES mein chala jata hai
   (CRM mein nazar aata hai, zaaya nahi hota).

3) US 10-digit numbers -> khud +1 (country auto-detect, pehle wala fix).

4) Consent khaali -> phir bhi import (permission assumed) -- pehle wala fix.

5) BADE files: pehle sirf 500 rows ki limit thi. Ab limit 250,000 rows.
   Aur insert fast ho gaya (ek dafa existing numbers load, phir batches
   mein daalta hai) -- lakhs rows seconds-minute mein.

TUMHARI FILE (Leads__3.csv) KA NATEEJA (simulate)
-------------------------------------------------
  Total rows      : 244,546
  ADD honge       : 169,277  (naam + +1 number + address notes mein)
  SKIP honge      : 75,269   (duplicate numbers aapas mein)

BADLI FILE
----------
  backend/main.py   (import: FN/LN, address->notes, 250k limit, fast insert)

NOTE / EHTIYAT
--------------
- Itne bade (1.7 lakh) leads EK user ke CRM mein bhari ho sakte hain --
  CRM list/Power Dialer thoda slow lag sakta hai. Behtar ho to area/campaign
  ke hisab se chhoti files mein baanto.
- Agar bada import request time-out kare (bohot bade file par), file ko
  2 hisson mein baant kar do dafa upload kar lena.
- Limit badalni ho to Render env: CRM_IMPORT_MAX (default 250000).

COMPLIANCE
----------
US cold leads -- dial se pehle DNC/TCPA scrub apni zimmedari par.
