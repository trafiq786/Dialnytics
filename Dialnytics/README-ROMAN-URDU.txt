==========================================================
  CRM — 50k leads sahi show + Power Dialer sab tak pohnche
==========================================================

MASLA
-----
50k leads add hui thin lekin:
 - "Total leads" sirf 1000 dikha raha tha
 - List mein sirf 1000 nazar aati thin (delete karo to agli 1000)
 - Power Dialer bhi sirf 1000 tak dial kar sakta tha

WAJAH
-----
 - CRM page aur stats dono sirf latest 1000 (LIMIT 1000) se bante the.
 - /api/crm/leads ka GET route tha hi nahi -> Power Dialer /crm page
   (1000) se leads uthata tha.

AB KYA THEEK HUA
----------------
1) STATS (Total/Consented/Callbacks/Do-not-call) ab DB ke REAL COUNT se
   -> poore 50k ka sahi number dikhega.
2) CRM list ke upar note: "Showing latest 1000 of 50000 ... Power Dialer
   mein sab available". (Table latest 1000 hi rakhta hai taake page tez
   rahe -- 50k rows ek table mein browser hang kar deta.)
3) NAYA GET /api/crm/leads -> Power Dialer ab SAARI leads load karta hai
   (default 50,000 tak, env CRM_PICKER_MAX se badal sakte ho).
4) Power Dialer lead-picker 50k par freeze na ho -> ek dafa pehli 800
   dikhata hai + search se narrow. "Select all" phir bhi SAARI matching
   select karta hai (phir queue banate waqt max 5000 per queue).

BADLI FILES
-----------
  backend/main.py                       (real counts + GET /api/crm/leads)
  frontend/templates/crm.html           (stats + "1000 of N" note)
  frontend/templates/power_dialer.html  (cache-bust ?v=6)
  frontend/static/js/crm.js             (stats real totals)
  frontend/static/js/power-dialer.js    (picker render cap)

DEPLOY ke baad CRM aur Power Dialer dono pages HARD-REFRESH (Ctrl+F5).

NOTE: Ek queue max 5000 leads leta hai (POWER_QUEUE_MAX). 50k ko kai
batches mein dial karna hoga (ya env se barha sakte ho).
