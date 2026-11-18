===========================================================
  Dialnytics — Update AD
  Fix: EchoDial user ka number change karna
===========================================================

Masla:
  EchoDial user ka number "Change number" se badalne par
  error aata tha:
     {"detail":"Number is not owned by this Echodial account"}

Wajah:
  change-number endpoint har provider ke liye check karta
  tha ke number provider ke "owned numbers" mein hai. EchoDial
  mein number MANUALLY type hota hai (CLI provider approve
  karta hai, koi owned-number list nahi) — is liye ye check
  galat rok raha tha. (Create-user mein ye pehle se skip hota
  tha; change-number mein reh gaya tha.)

Fix:
  Ab provider == 'echodial' ho to ye ownership check skip ho
  jata hai — EchoDial par koi bhi (E.164) number manually set
  ho jayega. Telnyx/Twilio par check jaise tha waise hi hai.

FILE (sirf 1):
  backend/main.py

Deploy ke baad EchoDial user ka number change ho jayega.
Note: jo number CLI ke tor par set karo wo EchoDial (ConnexCS)
par approved CLI hona chahiye, warna wahi 503 routing masla.
