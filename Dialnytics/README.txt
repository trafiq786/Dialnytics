DIALNYTICS UPDATE M  -  "Leave call" (2026-11-06)
====================================================

KYA NAYA HAI
------------
3-way call mein agent nikal sakta hai aur baqi do log (jaise client + bahar ka US agent)
baat karte rehte hain. Sirf woh users jinhe ADMIN allow kare.

Flow:
 1. Client ko call karo.
 2. "Add Call" se US agent ka number milao (chaho to "Merge" karke teeno baat karo).
 3. Neeche peela button "Leave call · they keep talking" dabao, confirm karo.
 4. Server dono phone lines ko aapas mein jod deta hai, aap ki dono browser calls band.
 5. Dialer mein hara card: "Still talking without you" + timer + "End their call".
 6. Jab un mein se koi phone rakhe, call band; Call Logs mein poora time aa jata hai
    (aap ke nikalne ke baad ka time bhi).

ADMIN SETTING
-------------
Users -> Edit -> naya checkbox "Leave call". Tick karo -> Save.
User ko dialer refresh (Ctrl+F5) karna hoga.

SHARTEIN
--------
- Sirf Telnyx lines (Twilio par checkbox band rehta hai).
- OUTGOING calls ke liye us user ka "Advanced calling" bhi ON hona chahiye
  (warna server calls ko control nahi karta aur dialer saaf error dikhata hai).
  Incoming calls par ye zaroori nahi.
- Exactly 2 aur log call par hon (aap + 2).
- Aap ke nikalne ke baad bhi DONO lines aap ke Telnyx account par per-minute chalti hain.
- Hifazat: jis call mein team ka koi member nahi, woh 120 minute baad khud kat jati hai.
  Badalna ho to Render env: LEAVE_MAX_MINUTES=60 (ya jo chaho).

FILES (sirf yehi badli hain)
----------------------------
backend/call_transfer.py        leave(), left calls, 2-ghante limit, database table
backend/main.py                 3 nayi API + admin checkbox save
frontend/templates/users.html   admin checkbox "Leave call"
frontend/templates/dialer_rail.html   Leave button + "still talking" card
frontend/templates/base.html    dialer.js?v=20261106 (cache)  [update L ki glass wali base.html par bani hai]
frontend/static/js/dialer.js    Leave call logic

DATABASE
--------
Kuch manually nahi chalana. App start par khud ban jata hai:
 - dialnytics_users.conf_leave (default false = sab ke liye band)
 - naya table left_calls

DEPLOY
------
Files repo mein replace karo -> GitHub push -> Render deploy -> Ctrl+F5.

PEHLA TEST (zaroor karo)
------------------------
Main isay live Telnyx ke bina test nahi kar saka (server logic local database par test kiya).
 1. Admin: apne test user ke liye "Leave call" (aur "Advanced calling") ON.
 2. Apne mobile ko call karo, phir Add Call se doosra mobile milao.
 3. "Leave call" dabao -> dono mobiles ek doosre ko sun sakein, aap ki browser call band ho.
 4. Ek mobile kaato -> doosra bhi kat jaye, card gayab, Call Logs mein time sahi.
 5. Dobara karo aur card se "End their call" dabao -> dono kat jayein.
Agar step 3 par error aaye: dialer ka message + Render log mein "Leave call bridge failed"
wali line bhej dena.
