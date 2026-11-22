===========================================================
  HYBRID TOGGLE  —  har user ki detail mein manual ON/OFF
===========================================================

KYA BANA
--------
Ab hybrid sirf auto (number Twilio ka ho to) par nahi — har customer ki
detail page par ek manual toggle hai:

  Customers -> (koi user) -> "Number / Provider" card ke neeche:
  "Hybrid calling — inbound on Twilio"
     Status: Hybrid ON / off
     [ Turn hybrid ON ]  ya  [ Turn hybrid OFF ]

  ON  -> us user ka inbound Twilio DID par aayega (twilio_in = true). Agar
         number Twilio ka hai to us ka voice webhook bhi khud app par set
         ho jata hai.
  OFF -> inbound wapas us ke apne provider number par.

Note:
- Yeh har provider ke user par dikhai deta hai (sirf echodial nahi).
- Agar Twilio server par configured na ho, ya user ka number Twilio ka na
  ho, to toggle ON to ho jayega par ek ⚠️ warning dikhayega ke inbound tab
  tak nahi aayega jab tak number Twilio ka na ho. Upar "change number" se
  Twilio number do.


BADLE FILES  (apne repo mein replace karo)
------------------------------------------
  backend/main.py                          (BADLA)
  frontend/templates/customer_detail.html  (BADLA)

Ye ALL-IN-ONE.zip ke UPAR aati hain. backend/main.py ismein SAARE features
(auto-invoice + routing + ab hybrid toggle) samete hue hai — yehi latest hai.
Baqi files (mailer.py, auto_invoice.py, renewals.html, routing.html,
base.html) pehle wali ALL-IN-ONE.zip se already lagi hui honi chahiye —
unhe dobara daalne ki zaroorat nahi.

DATABASE: koi nayi table nahi (twilio_in column pehle se mojood hai).

TEST: ek user ki detail kholo -> "Turn hybrid ON" -> status ON ho jaye.
Us ko Twilio number assign ho to us number par baahar se call karo ->
dialer par ring aani chahiye. "Turn hybrid OFF" -> wapas normal.

Sawal ho to batao.
