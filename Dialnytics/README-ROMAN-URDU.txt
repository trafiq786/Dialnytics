==========================================================
  CALL LOG ROWS FIX v2 — cache-bust (ab asar dikhega)
==========================================================

MASLA
-----
Pichli fix sahi thi lekin glass.css ?v=6 hi raha -> browser/Render
PURANI cached glass.css serve kar raha tha, is liye wavy rows waise hi.

AB
--
- glass.css fix (dn-detail glass group se bahar) -- waisa hi.
- base.html mein glass.css ?v=6 -> ?v=7 (cache-bust). Ab browser nayi
  file fetch karega -> rows clean (flat lines).

BADLI FILES
-----------
  frontend/static/css/glass.css   (dn-detail fix)
  frontend/templates/base.html    (glass.css ?v=7)

DEPLOY -> koi bhi page Ctrl+Shift+R (ek dafa). Ab wavy/pill look gayab.
