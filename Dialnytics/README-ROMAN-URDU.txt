==========================================================
  CALL LOG DETAIL — rows ka scalloped/wavy look FIX
==========================================================

MASLA
-----
Call details popup (aur jahan bhi .dn-detail rows hain) mein har row
ajeeb "wavy / scalloped" pill jaisa dikh raha tha.

WAJAH
-----
glass.css mein ".dn-detail" (jo ek ROW hai: Number/Contact/Direction...)
ko galti se modal/drawer CONTAINERS (.dn-drawer, .power-lead-dialog,
.profile-menu, .tour-box) ke SAATH group kiya gaya tha. Is wajah se HAR
row ko glass-card background + border + shadow + border-radius 26px mil
jata tha -> stacked rounded rows = scalloped/wavy edges.

FIX
---
".dn-detail" ko glass container groups se nikaal diya (4 jagah). Ab:
 - Drawer/popup ka glass look WAISA hi (container par).
 - Rows ab saaf flat lines (label left, value right, patli divider) —
   jaisa hona chahiye. Light + dark dono theme theek.

BADLI FILE
----------
  frontend/static/css/glass.css

DEPLOY ke baad koi bhi page HARD-REFRESH (Ctrl+F5). CSS ?v nahi tha to
browser cache clear karna pad sakta hai (Ctrl+Shift+R).
