==========================================================
  CRM IMPORT v5 — "File is too large" FIX
==========================================================

MASLA
-----
Deploy ke baad bhi "File is too large" aa raha tha. Wajah: CSV ka
upload byte-limit sirf ~250 KB tha (rows ginne se PEHLE hi rok deta).

AB KYA HUA
----------
- CSV upload limit ab 30 MB (Excel 15 MB).
- Agar CSV phir bhi bada ho to REJECT nahi karta -- poori lines tak
  padh leta hai aur 50k row-limit baaki trim kar deta hai.
- Help text update ("Max 500 rows" -> "up to 50,000 per upload").

Yani ab tumhari 14 MB wali file bhi chadhegi: pehle 50,000 leads
import, baqi skip.

BADLI FILES
-----------
  backend/main.py                 (upload size limit + big-CSV trim)
  frontend/templates/crm.html     (help text)

DEPLOY ke baad CRM page HARD-REFRESH (Ctrl+F5).
