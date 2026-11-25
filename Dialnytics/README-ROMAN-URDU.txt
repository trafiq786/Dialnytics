==========================================================
  CRM IMPORT v3 — limit 50k + COPY (bohot fast)
==========================================================

TABDEELI
--------
1) LIMIT ab 50,000 rows per import (pehle 250k thi).
2) INSERT ab PostgreSQL COPY se hota hai -> 50k rows chand seconds mein
   (pura import 1-2 minute se kaafi kam). Dedup pehle Python mein ho jata
   hai (ek dafa existing numbers load), phir seedha COPY.

(Pichle sab fixes isme shaamil: FN/LN naam, address->notes, US +1
 auto, khaali consent allow.)

ZAROORI
-------
- Tumhari Leads__3.csv mein 2.44 lakh rows hain -> ab 50k limit se ZYADA
  hai, is liye poori ek dafa nahi chadhegi. Do tareeqe:
    (a) File ko 50k-50k ke hisson mein baant kar alag alag upload karo, YA
    (b) Render env CRM_IMPORT_MAX ko barha do (jaise 100000) -- lekin
        50k hi rakhna behtar hai (CRM/Power Dialer light rahega).

- Har upload: naye unique numbers add honge, duplicate khud skip.

BADLI FILE
----------
  backend/main.py

NOTE: COPY tez hai lekin ek hi transaction -- 50k tak bilkul theek.
