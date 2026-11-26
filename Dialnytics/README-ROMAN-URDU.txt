==========================================================
  CALL TIMER — Active ke saath duration + start time
==========================================================

KYA HUA
-------
Floating phone / dialer mein ab call Active hone par:
 - LIVE timer (00:00 se ticking, har second) number ke neeche.
 - "Started 5:41 PM" (call kis waqt active hui).
Timer sirf Active/On-hold par; ringing/calling par nahi, call khatam
hote hi gayab.

BADLI FILES
-----------
  frontend/static/js/dialer.js        (timer in-call view mein paint)
  frontend/templates/dialer_rail.html (timer element + style)
  frontend/templates/base.html        (dialer.js ?v=20261126e)

DEPLOY ke baad dialer page HARD-REFRESH (Ctrl+F5).
