===========================================================
  Dialnytics — Update YY
  EchoDial py Transfer + Leave call + Conference (3-way)
===========================================================

Ye update EchoDial (EchoNet / ConnexCS) waly users k liye wohi
advanced features on karta hai jo pehle sirf Telnyx py thy:

  • Conference (Add call + Merge)  -> browser mein mix hoti hai
  • Transfer (kisi number ya teammate ko)
  • Leave call (aap nikal jao, do log aapas mein baat karte rahein)

Telnyx aur Twilio users py KOI farq nahi — un ka code bilkul
waisa hi chalta hai jaise pehle tha. Ye naya code sirf tab chalta
hai jab user ka provider "echodial" ho.


-----------------------------------------------------------
  FILES (sirf ye 4 files badli hain)
-----------------------------------------------------------
  backend/main.py
  frontend/static/js/dialer.js
  frontend/templates/dialer_rail.html
  frontend/templates/base.html      (dialer.js ka version v=20261121)

Apne project mein inhi jagah py purani files k upar copy kar dein,
phir Render py deploy kar dein.


-----------------------------------------------------------
  HAR FEATURE KAISE KAAM KARTA HAI
-----------------------------------------------------------
1) CONFERENCE (3-way)
   - Call k doran "+ Add call" -> doosra number dial karo
   - Phir "Merge" -> dono callers + aap, sab aik dusre ko sunte hain
   - Ye browser k andar audio mix karke hoti hai (koi server
     setup nahi chahiye). EchoDial py ye ready hai.

2) TRANSFER
   - Call k doran "Transfer" dabao
   - Teammate chuno -> caller us teammate k NUMBER py chala jata
     hai (SIP REFER se), aur aapki side band ho jati hai.
   - Ya "Transfer to a phone number" -> koi bhi number type karo.
   - Teammate wali list ab EchoDial k liye alag endpoint se aati
     hai: us company k sab active users jin ka apna number set hai.

3) LEAVE CALL
   - Pehle admin ko us user k liye "Leave call" on karna hoga
     (Users page -> us user ki settings).
   - Jab aap + 2 log call py hon (aap ne 2 callers jore hon),
     "Leave call" dabao -> aap nikal jate ho, do caller aapas mein
     jure rehte hain (attended SIP transfer / REFER-with-Replaces).


-----------------------------------------------------------
  DEPLOY SE PEHLE (zaroori)
-----------------------------------------------------------
  • Render env vars set hon: ECHODIAL_WSS, ECHODIAL_DOMAIN,
    ECHODIAL_USER, ECHODIAL_PASS  (ye pehle se lage hue hain).
  • Jo bhi number caller-ID (CLI) k tor py use karna hai, wo
    EchoDial py approved DID hona chahiye — warna provider
    "405 CLI Restriction" deta hai (ye hum pehle test kar chuke).


-----------------------------------------------------------
  TESTING — PEHLE SIRF 1 USER PY
-----------------------------------------------------------
  Ye features yahan (mere environment) se live test nahi ho sakte,
  is liye deploy k baad SIRF AIK test user (provider=echodial) py
  check karein, phir baqi users py:

  1. Transfer to number:
     - Test user se aik call karo (apne doosre number py).
     - Call connect ho jaye to "Transfer to a phone number" ->
       teesra number daal do. Dekho ke caller us number py
       pohanchta hai aur aapki side band ho jati hai.

  2. Transfer to teammate:
     - "Transfer" -> list mein se aik teammate chuno (jis ka
       number set ho). Caller us k number py jana chahiye.

  3. Conference:
     - Call k doran "+ Add call" -> doosra number -> "Merge".
       Teeno aawaz aapas mein sunai deni chahiye.

  4. Leave call:
     - Admin se us user ka "Leave call" on karwao.
     - 2 callers jore k "Leave call" dabao. Dono baat karte
       rehne chahiyein, aap nikal jaoge.

  NOTE (Leave call): ye feature SIP trunk ki
  "REFER-with-Replaces" support py depend karta hai. Agar
  EchoDial trunk ye support na kare to dialer khud ko band
  NAHI karega — aapko message milega "Could not connect them…
  You are still on the call" aur aap normal 3-way ki tarah call
  py rahoge. Is case mein EchoDial (ConnexCS) support se bol
  dena ke "attended transfer / REFER with Replaces" enable
  kar dein. Transfer aur Conference is par depend nahi karte.


-----------------------------------------------------------
  FIX (is update mein shamil): "Advanced calling is only
  for Telnyx lines" wala message
-----------------------------------------------------------
  EchoDial user ko edit karte waqt "Advanced calling" aur
  "Live listening" ab khud disabled dikhte hain — kyunke ye
  sirf Telnyx ki server-routing features hain. EchoDial py
  transfer unke baghair hi chalta hai, is liye ab wo error
  nahi aayega.

  "Leave call" checkbox EchoDial k liye ON kiya ja sakta hai.

  (Agar kisi EchoDial user py pehle se Advanced calling on
  tha, to save karne py wo khud khamoshi se off ho jayega —
  koi error nahi.)

  File: frontend/templates/users.html bhi is update mein
  shamil hai.
