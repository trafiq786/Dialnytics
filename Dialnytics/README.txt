DIALNYTICS UPDATE N2  -  Advanced calling + transfer fix (2026-11-07)
====================================================================
Update M ke upar lagao.

MASLA
-----
Server jab kisi phone number ko khud dial karta tha (Advanced calling ki outgoing call,
aur bahar ke number par Transfer) to Telnyx ko SIP connection ki ID bhejta tha.
Telnyx is kaam ke liye sirf Call Control App (Voice API app) ki ID leta hai:
"Invalid value for connection_id (Call Control App ID)" -> call foran fail.

FIX
---
- N2: client uthane par server pehle aap ki (ruki hui) browser call answer karta hai,
  phir dono ko jodta hai (pehle Telnyx "Call not answered yet" de raha tha).
- Server ab dial ke liye TELNYX_VOICE_APP_ID wali Voice API app use karta hai
  (wohi jo incoming calls ke liye pehle se lagi hai).
- Render logs mein ab har Advanced call ki line aati hai (dialing / fail ki asli wajah / SIP code).
- "Leave call" ka button ab tab hi dikhta hai jab leave mumkin ho
  (outgoing call + Advanced calling off ho to button nahi dikhega).

TELNYX MEIN 1 CHEEZ CHECK KARO (zaroori)
--------------------------------------
Voice -> Programmable Voice (Voice API Applications) -> jo app Dialnytics ki hai
(jis ki ID Render mein TELNYX_VOICE_APP_ID hai) -> Outbound tab:
  Outbound Voice Profile = "Dialnytics Profile"   (khali ho to choose karke Save)
Is ke baghair server se dial ki gayi calls nahi lagengi.

FILES
-----
backend/call_transfer.py
frontend/static/js/dialer.js
frontend/templates/base.html   (dialer.js?v=20261107)

TEST
----
1. Deploy -> dialer logout/login.
2. Advanced calling wale user se apne mobile par call -> ring ho, awaz aaye.
3. Phir: client call -> Add Call -> US agent -> Leave call.
4. Transfer -> bahar ka number -> ab ring jani chahiye.
Masla ho to Render logs mein "Advanced outbound" wali line bhejo.
