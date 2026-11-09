Update Y - Poora interface responsive + dialer fit

Nayi files (add karein):
  Dialnytics/frontend/static/css/responsive.css
  Dialnytics/frontend/static/js/responsive.js
Replace karein:
  Dialnytics/frontend/templates/base.html      (nayi files load + cache refresh)
  Dialnytics/frontend/templates/dialer_rail.html
  Dialnytics/frontend/static/js/dialer.js
  Dialnytics/frontend/static/js/mobile-nav.js

Kya badla:
- Mobile pe har table ki row card ban jati ha (label + value), koi column nahi katta.
- Billing / Invoice ke side-by-side boxes phone aur tablet pe neeche neeche.
- Dialer har screen pe fit, scroll nahi; call ke dauran "Calling..." aik dafa.
- Laptop/bari screen pe kuch nahi badla.
Database change koi nahi. Note: update W (glass.css v6) pehle laga hona chahiye.
