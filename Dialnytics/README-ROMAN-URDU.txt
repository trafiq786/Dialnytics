===========================================================
  ALL-IN-ONE  —  Auto-invoice + Routing (switch + hybrid)
  (deploy crash "No module named 'mailer'" ka fix)
===========================================================

KYA HUA THA
-----------
ROUTING.zip ki main.py `mailer` aur `auto_invoice` ko import karti hai, lekin
wo 2 nayi files repo mein nahi gayi thin -> app boot par crash:
   ModuleNotFoundError: No module named 'mailer'

FIX = bas ye saari files ek saath daal do (yahan sab ikatthe hain).


IN SAARI FILES KO APNE REPO MEIN ISI JAGAH RAKHO (replace/add)
--------------------------------------------------------------
  backend/mailer.py                        (NAYA  <- ye missing tha)
  backend/auto_invoice.py                  (NAYA  <- ye missing tha)
  backend/main.py                          (BADLA)
  frontend/templates/base.html             (BADLA)
  frontend/templates/renewals.html         (NAYA)
  frontend/templates/routing.html          (NAYA)

Khaas tor par confirm karo ke  backend/mailer.py  aur  backend/auto_invoice.py
repo mein mojood hain (yehi do reh gaye the). Phir Render par deploy -> app
theek chalega.


DEPLOY KE BAAD CHECK
--------------------
- App start ho jaye (crash nahi).
- Sidebar mein 2 naye links: Finance -> "Renewals" (📅), Calling -> "Routing" (🔀).
- Dono pages khul jayein.

Baqi istemaal/test ki tafseel pehle wali 2 READMEs mein hai (AUTO-INVOICE aur
ROUTING). Khulasa:
  * Renewals: SMTP_USER + SMTP_PASS (Zoho app password) set karo, phir 1 test
    customer par "Run now", phir "Auto-invoice ON".
  * Routing: From/To provider -> "Switch all users" (target provider ACTIVE
    ho). Hybrid ke liye "Re-sync hybrid".

DATABASE: koi manual SQL nahi — app start par khud migrate ho jata hai
(auto_invoice_log table + settings).

Sawal ho to batao.
