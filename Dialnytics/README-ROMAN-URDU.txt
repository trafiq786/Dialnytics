===========================================================
  ADD-ONS AT CREATE  +  EchoDial env line removed
===========================================================

KYA BANA
--------
1) USER CREATE form (Create User page) par naya "Add-ons & features" section —
   create karte waqt hi chuno user ko kya milega:
     - Call recording
     - Conference (add call)      [default ON]
     - Call transfer
     - Live monitoring (listen / whisper / barge)
     - Leave call
     - Hybrid calling (outbound SIP, inbound Twilio)
     - Power Dialer / Campaigns
     - SMS texting
   Jo tick karo ge wo naye user par set ho jayega (wahi flags jo edit popup
   mein hain). Provider-side wale (transfer/monitoring/sms) apne proper setup
   ke sath on hote hain, baqi seedha column set.

2) "Conference (add call)" ab ek asli per-user toggle hai (naya column
   conf_enabled, default TRUE). Purane sab users par pehle jaisa ON rehta hai
   (default true) — kuch nahi tootta. Naye user par tum uncheck karke rok
   sakte ho.

3) EchoDial (generic env line) HATA DIYA dropdowns se — kyunke tum ne apna
   provider "ECONNET-CS" add kar liya hai. Ab Provider list mein sirf tumhare
   naam wale SIP providers (ECONNET-CS waghaira) + Telnyx/Twilio dikhte hain.
   (Env fallback backend mein mojood hai taake koi purana user na toote, bas
   dropdown mein "EchoDial" option nahi aata.)


BADLE FILES  (apne repo mein replace karo)
------------------------------------------
  backend/main.py                          (BADLA)
  frontend/templates/users.html            (BADLA — create form add-ons)
  frontend/templates/dialer_rail.html      (BADLA — data-conf ab conf_enabled)

Ye sab pichli zips ke UPAR aata hai. backend/main.py ismein SAARE features
(auto-invoice + routing + hybrid toggle + ab add-ons) samete hue hai — yehi
latest hai. customer_detail.html (HYBRID-TOGGLE zip wali) jaisi hai waisi
rehne do — is zip mein nahi hai, dobara daalne ki zaroorat nahi.

DATABASE: koi manual SQL nahi — conf_enabled column app start par khud ban
jata hai (default true, purane users safe).


ISTEMAAL / TEST
---------------
1) Deploy (Render push).
2) Create User page kholo -> niche naya "Add-ons & features" section.
3) Ek test user banao kuch add-ons tick karke -> banne ke baad us user ki
   detail/edit mein wo add-ons on dikhne chahiyein.
4) Provider dropdown mein "EchoDial" ab nahi — sirf ECONNET-CS (aur baqi)
   dikhega. Confirm karo naya user ECONNET-CS par ban raha hai.


NOTE (feature functionality)
----------------------------
Toggle set karne se flag on hota hai. Transfer / monitoring (whisper/barge) /
leave ka EchoDial par POORA chalna wo alag kaam hai (jo plan diya tha —
Phase 1/2/3, kuch ke liye ConnexCS API). Ye zip sirf "add-ons ka option
create par" de raha hai + conference toggle + EchoDial line hatana. Feature
build alag se hoga.

Sawal ho to batao.
