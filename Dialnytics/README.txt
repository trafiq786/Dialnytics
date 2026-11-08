DIALNYTICS UPDATE T  -  Live listen se call kat-na (2026-11-08)
==============================================================
S ke upar lagao. 4 backend files:
  backend/call_transfer.py, backend/main.py, backend/ring_group.py, backend/live_listen.py

MASLA (Render log: 90018 "Call has already ended")
------------------------------------------------
Listen par caller ko conference mein le jaate hi Telnyx ne agent ki leg band kar di
(Telnyx ka default: jodd tootte hi doosri leg hang up). Phir caller akela reh gaya aur call kat gayi.

FIX
---
1. Har jagah jahan agent ki leg caller se judti hai (Advanced outgoing, incoming, ring group,
   transfer) ab Telnyx ko "park_after_unbridge: self" bheja jata hai: jodd toote to agent ki
   leg band nahi hoti, ruki rehti hai. Normal hang up pehle ki tarah server khud karta hai.
2. Agent conference mein na aa sake to server caller ko wapas agent se jod deta hai
   (call nahi katti) aur saaf message deta hai.
3. Listen ka kaam ab alag thread mein chalta hai (baqi app slow nahi hota).

ZAROORI
-------
Ye sirf NAYI calls par lagta hai. Jo call deploy se PEHLE shuru hui thi, use mat suno
(wo purane tareeqe se judi hai). Deploy ke baad nayi call karke test karo.

TEST
----
1. Deploy -> Ctrl+F5.
2. Advanced user se nayi outgoing call (mobile par), 10 sec baat.
3. Super admin -> Team -> Live call -> Listen. Call nahi katni chahiye; awaz aani chahiye.
4. Phir ek incoming call par bhi Listen.
Render log mein "Live listen: call ... moved into conference" aur "listener joined" lines aayengi.
