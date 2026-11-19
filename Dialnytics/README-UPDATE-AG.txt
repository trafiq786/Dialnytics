===========================================================
  Dialnytics — Update AG
  Fix: SIP Providers ka WSS CSP se block ho raha tha
===========================================================

Masla:
  SIP Providers page par naya provider (jaise webphone.srws.cc)
  add karne ke baad, browser se connect karte waqt console mein:
     "Connecting to 'wss://webphone.srws.cc/ws' violates the
      Content Security Policy... blocked."
  Kyunke CSP (security policy) mein sirf telnyx/twilio/echodial
  allowed thе. Naye providers blocked ho rahe thе.

Fix:
  Ab CSP DYNAMIC hai — jo bhi SIP provider aap admin panel se
  add karte ho, uska WSS host khud-ba-khud CSP ki allow-list
  mein aa jata hai. Koi code change nahi chahiye har naye
  provider ke liye. (~60 sec cache; add/delete par foran update.)

FILES (sirf 2, backend):
  backend/main.py
  backend/voice_helpers.py

Deploy ke baad:
  - Provider pehle se SIP Providers page par add hai to bas
    deploy karo; ya add karo.
  - Phir sip-test.html / dialer se connect karo — ab WSS block
    nahi hoga.

NOTE: WSS field mein poora URL daalna: wss://host:port/path
  (jaise wss://webphone.srws.cc/ws) — IP nahi, hostname.
  SIP domain alag field mein (jaise 45.132.15.162).
