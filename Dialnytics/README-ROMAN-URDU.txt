==========================================================
  CRM — "Delete all" button (+ sab recent fixes cumulative)
==========================================================

NAYA
----
CRM page par (search/filter ke saath) naya "Delete all" button.
 - Dabane par confirm: "Delete ALL <N> leads? ... cannot be undone."
 - Haan karne par SAARI leads ek saath delete (50k bhi instant --
   single SQL statement). Queue rows bhi saaf.

ISME PICHLA SAB SHAAMIL (cumulative main.py):
  - Queue limit 50,000
  - CRM stats real COUNT, GET /api/crm/leads (Power Dialer sab leads)
  - Picker/queue table render cap (freeze na ho)
  - CSV 30MB upload, FN/LN, address->notes, US +1, 50k se zyada -> skip

BADLI FILES
-----------
  backend/main.py                       (POST /api/crm/leads/delete-all)
  frontend/templates/crm.html           (Delete all button, crm.js ?v=5)
  frontend/static/js/crm.js             (delete-all handler)
  frontend/templates/power_dialer.html  (?v=7)
  frontend/static/js/power-dialer.js

DEPLOY ke baad CRM page HARD-REFRESH (Ctrl+F5).

EHTIYAT: "Delete all" wapas nahi aata -- confirm soch kar dabao.
