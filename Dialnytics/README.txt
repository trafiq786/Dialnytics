Update BB - Dashboard sahi aur live

Replace karein:
  Dialnytics/backend/main.py
  Dialnytics/frontend/templates/dashboard.html
  Dialnytics/frontend/templates/base.html
  Dialnytics/frontend/static/js/dialer.js
(Is mein AA, Z, X ke changes b shamil hain. Database change koi nahi.)

Kya theek hua:
- "Today / This Week / This Month" ab user ke apne time zone se (browser ka) - pehle Pakistan time fix tha,
  is liye UK/US agents ka "Today" ghalat hota tha.
- Dashboard har 20 second mein khud update hota ha, aur call khatam hote hi b.
- Contacts Added: sirf us period mein add hue contacts (pehle sab time ke).
- Follow-ups Scheduled: CRM leads ke follow-ups jo us period mein hain (pehle hamesha 0).
- Call Outcomes: "Answered" aur "Not answered" (pehle "Outgoing" ghalat label tha).
- Disposition (nakli 100%) ki jagah asli Call Breakdown: Outgoing aur Incoming (answered / missed).
- Ways to Improve: asli data se tips (missed calls, kam pick-up, chhoti calls, follow-ups).
