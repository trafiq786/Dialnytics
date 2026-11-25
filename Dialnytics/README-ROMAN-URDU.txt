==========================================================
  SPEED FIX — dialer/CRM slow (50k leads par)
==========================================================

WAJAH
-----
1) crm_leads par INDEX nahi tha -> har query (CRM page, counts,
   dashboard, dedup, picker) 50k rows seq-scan karti thi = slow.
2) Power Dialer picker SAARI 50k leads browser mein load kar raha tha
   (~bohat bada JSON) = tab slow/hang.

AB KYA THEEK HUA
----------------
1) DB INDEXES khud ban jate hain (deploy par, ek dafa):
     crm_leads(user_id), (user_id,phone), (user_id,followup_at)
     power_queue_items(queue_id,position), (lead_id)
   -> har query bohat tez.
2) Picker ab sirf recent 5,000 leads browser mein lata hai (halka).
3) NAYA button "Queue ALL eligible" -> poori 50k ko SERVER par queue
   karta hai (browser mein 50k load kiye baghair). Yahi use karo bade
   list dial karne ke liye.

KAISE 50k DIAL KARO (ab)
------------------------
Create Queue -> dialog -> Mode/Delay set -> "Queue ALL eligible" dabao
-> server poori eligible list queue kar deta hai -> Start.
(Chhote hath se chunne ke liye search + Select all abhi bhi hai, 5k sample.)

BADLI FILES
-----------
  backend/main.py                       (indexes + /api/power/queue/all + picker cap)
  frontend/templates/power_dialer.html  (Queue ALL button, ?v=8)
  frontend/static/js/power-dialer.js    (queue-all handler)
  frontend/templates/crm.html           (cumulative)
  frontend/static/js/crm.js             (cumulative)

DEPLOY ke baad CRM + Power Dialer dono HARD-REFRESH (Ctrl+F5).

NOTE: Pehla deploy thoda der le sakta hai (index ban raha hota hai 50k par)
-- ek dafa ka kaam hai, phir tez.
