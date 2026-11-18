===========================================================
  Dialnytics — Update AC  (XX ke upar; AB ko shamil karta hai)
  EchoDial: SIP code screen par (diagnostic) + ring + leave
===========================================================

"Aik ring k baad call end" ka matlab: ring to ab local tone
ki wajah se sunai deti hai, LEKIN asal call trunk ki taraf
se ~1-2 second baad khatam ho rahi hai. Asal wajah SIP code
mein chhupi hai, jo ab tak agent ko "Call ended" generic
dikh raha tha.

IS UPDATE MEIN (naya):
  Admin ko ab call end/fail hone par SCREEN PAR hi SIP code
  nazar aayega, jaise:
     "Call ended — SIP 480 Unavailable [remote]"
     "Call ended — SIP 603 Declined [remote]"
     "Call ended — SIP 500 ... [remote]"
  [remote] = doosri taraf (trunk/client) ne band ki.
  [local]  = hamari taraf se band hui.

  >>> Agli call karke jo poora text aaye wo mujhe bhej dein.
      Us SIP code se main 100% bata dunga ke trunk kya reject
      kar raha hai (CLI, route, balance, ya answer supervision).

Isme AB wali dono cheezein bhi shamil hain:
  - EchoDial ring tone (dial karte hi ring)
  - EchoDial Leave call (browser-bridge)

-----------------------------------------------------------
  FILES (sirf 4, backend/main.py bilkul nahi badla)
-----------------------------------------------------------
  frontend/static/js/dialer.js
  frontend/templates/dialer_rail.html
  frontend/templates/base.html          (dialer.js?v=20261124)
  frontend/templates/users.html

Deploy k baad dialer Ctrl+F5 se refresh karein, phir aik
call karke SIP code wali line mujhe bhej dein.
