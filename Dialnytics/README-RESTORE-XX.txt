===========================================================
  Dialnytics — RESTORE to XX (YY update wapas hataya)
===========================================================

Ye zip aap ko YY se PEHLE wali (XX) state py le jata hai.
YY k saare changes (EchoDial transfer / leave / conference
aur admin UI tabdeeliyan) poori tarah HATA diye gaye hain.
Calling bilkul waisi ho jayegi jaisi YY se pehle thi.

-----------------------------------------------------------
  FILES (ye 5 files purani XX wali py wapas aa gayi hain)
-----------------------------------------------------------
  backend/main.py
  frontend/static/js/dialer.js
  frontend/templates/dialer_rail.html
  frontend/templates/base.html       (dialer.js?v=20261119 — XX wala)
  frontend/templates/users.html

Apne project mein inhi jagah py copy kar k Render py deploy
kar dein. Deploy k baad dialer ko aik dafa refresh karein.

-----------------------------------------------------------
  AHEM
-----------------------------------------------------------
Agar restore k baad bhi call "Call declined" (SIP 603) de to
phir masla EchoDial trunk/account py hai (dialer/update py
nahi). Us soorat mein EchoDial portal py balance aur account
status check karein, aur chaahein to /static/sip-test.html se
603 ka exact reason capture kar k mujhe bhej dein.
