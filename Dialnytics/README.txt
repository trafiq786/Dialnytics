DIALNYTICS UPDATE P  -  Live call: Listen / Whisper / Join (2026-11-08)
=======================================================================
Update O ke upar lagao.

KAUN SUN SAKTA HAI
------------------
- Super admin (aap): har company ki live calls.
- Company owner: SIRF jab aap us company ke liye allow karo, aur sirf apni team.
  Allow karna: Companies -> company kholo -> "Live call listening" -> Turn on.

KAISE
-----
Team page -> jo agent call par hai us ke card par hara "Live call" button ->
neeche popup: kis number se baat, incoming/outgoing, timer + buttons:
  Listen   : chupchap sunna (aap ka mic band, kisi ko pata nahi)
  Whisper  : sirf agent aap ko sunta hai
  Join     : sab aap ko sunte hain
  Stop listening, Call logs, Recordings
Sunne wali call aap ke APNE dialer mein chupchap aati hai (ringing nahi dikhti).

SHARTEIN
--------
- Sunne wale (aap/owner) ki login par Telnyx calling line ho aur dialer khula + signed in ho.
- Sirf Telnyx lines. Outgoing calls sirf tab jab us agent ka Advanced calling ON ho;
  incoming calls hamesha.
- Sunne wale ki leg ka per-minute charge alag lagta hai.
- Pehli dafa koi sunta hai to call Telnyx conference mein shift hoti hai
  (agent/caller ko aadha second ki atkan mehsoos ho sakti hai).
- Listen ke dauran us call par Transfer / Leave call na karein.

FILES
-----
backend/live_listen.py  (NAYI file)
backend/call_transfer.py, backend/main.py
frontend/templates/team.html, team_member.html, company_detail.html, base.html
frontend/static/js/dialer.js
Database khud update hota hai.

PEHLA TEST
----------
1. Companies -> apni test company -> Live call listening: Turn on.
2. Agent (Telnyx line) se apne mobile par call (outgoing ho to agent ka Advanced calling ON).
3. Aap doosre browser/computer par apne login se Team page -> Live call -> Listen.
   10-15 sec mein "Listening" aana chahiye aur dono taraf ki awaz aani chahiye.
4. Whisper -> sirf agent sune. Join -> sab sunein. Stop -> aap nikal jao, call chalti rahe.
Masla ho to Render logs mein "Live listen" wali lines bhejo.
