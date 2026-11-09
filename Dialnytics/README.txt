DIALNYTICS UPDATE V  -  Power Dialer: bada queue (2026-11-09)
=============================================================
U2 ke upar lagao. 3 files:
  backend/main.py
  frontend/templates/power_dialer.html
  frontend/static/js/power-dialer.js

MASLA: "Add selected leads to queue" par kuch nahi hota tha.
  - Server ki limit 500 leads thi (aap ne 849 bheje) -> server ne mana kiya.
  - Error popup ke PEECHE likha jata tha, is liye nazar nahi aata tha.
FIX:
  - Limit 5000 leads per queue (Render env POWER_QUEUE_MAX se badal sakte ho).
  - Saare leads ek hi database command mein jate hain (849 leads bhi foran).
  - Error / "Creating queue..." ab popup ke andar dikhta hai.
Deploy -> Ctrl+F5.
