Update CC - Call status sahi waqt pe

Replace karein:
  Dialnytics/frontend/static/js/dialer.js
  Dialnytics/frontend/templates/base.html   (dialer.js?v=20261113 - cache refresh)
(BB ke baad lagayein - base.html mein BB wala version b ha.)

- Call milte hi 1.5 sec baad "Ringing" (UK/US network aksar ringing ka signal nahi bhejte the,
  is liye "Calling..." atka rehta tha).
- Samne wala answer kare tou foran "Active" + timer. Advanced calling mein bilkul foran,
  normal calling mein ~1 sec "Connecting" (awaz confirm hone tak).
- Answer ke baad dobara "Ringing" nahi aata.
