Update JJ - Power Dialer Start fix
Replace:
  Dialnytics/backend/main.py
  Dialnytics/frontend/static/js/power-dialer.js
  Dialnytics/frontend/static/js/dialer-extras.js
  Dialnytics/frontend/templates/power_dialer.html, base.html
(II ke baad. Is main.py mein pichle sab changes hain.)
Phir FIX_LEAD_NUMBERS.sql Supabase SQL Editor mein aik dafa chalayein.

- UK numbers "+44 0 7980..." (extra 0) ab khud "+44 7980..." ban jate hain: dialer, power dialer, CRM import.
- Start dabane pe agar call nahi lagti tou wajah ab Start button ke neeche peeli line mein dikhti ha.
- Jis lead ka naam khali/"null" ho wahan "Unnamed lead" dikhta ha.
