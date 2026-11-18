===========================================================
  Dialnytics — Update AE
  Admin: apne SIP Providers khud add/delete karo
===========================================================

KYA MILA:
  Admin panel mein naya page "SIP Providers" (sidebar mein,
  Website Orders ke neeche). Yahan aap koi bhi browser-calling
  (WebRTC/SIP) provider add kar sakte ho:
     - Provider name
     - WSS URL (websocket)
     - SIP username
     - SIP password
     - (optional) SIP domain — khali chhodo to WSS se nikal lega

  Add karte hi wo provider "Calling Provider" list mein aa jata
  hai — jaise EchoDial. Phir:
     - User banate waqt usay chuno, ya
     - Customer -> user -> "Change number / provider" ya
       "Switch provider" se usay us provider par daal do.
  User ka apna number (CLI) + calling sab chalega.

  Page par har provider ke saamne kitne users us par hain wo
  bhi dikhta hai, aur "Delete" button hai (pehle us ke users
  kisi aur provider par move karne honge).

KAISE KAAM KARTA HAI (technical):
  Ye naye providers EchoDial hi ki pipeline use karte hain
  (provider = 'echodial'), bas config (wss/user/pass) us
  chune provider se aata hai. Is liye dialer.js aur calling
  ka code BILKUL nahi badla — sirf backend + admin pages.
  Telnyx/Twilio/EchoDial sab waise hi chalte hain.

FILES:
  backend/main.py
  frontend/templates/base.html            (sidebar link)
  frontend/templates/sip_providers.html    (naya page)
  frontend/templates/users.html            (create-user form)
  frontend/templates/customer_detail.html  (change/switch provider)

DB: deploy par khud ek nayi table "sip_providers" aur users
  mein "sip_provider_id" column ban jayega (migration auto).

PEHLE 1 USER PAR TEST:
  1. Deploy ke baad "SIP Providers" page kholo -> ek provider
     add karo (wss/user/pass jo aap ke paas hain).
  2. Ek test user ko us par daalo (Change number/provider ya
     naya user banate waqt).
  3. Us user ke dialer se call test karo.
  Yaad rahe: user ki CLI us provider par APPROVED honi chahiye
  warna routing 503 (ye provider ki taraf ka masla hai).
