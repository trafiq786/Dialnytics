===========================================================
  SIP AUTO-PROVIDER  +  Add-ons UI (Conference)
  (user banao -> SIP khud, alag provider nahi)
===========================================================

KYA BANA
--------
1) GLOBAL SIP (Render env) — WSS/domain/password ek dafa, sab users same.
   Har user ka apna NUMBER hi SIP username banta hai. Ab per-user "SIP
   Provider" banane ki zaroorat NAHI.

2) USER CREATE karte waqt:
   - "Calling Provider" dropdown mein ab carrier LABELS aate hain
     (Infinity-USA, Econnet, Didlogic ... + Telnyx/Twilio).
   - Label chuno -> number type karo (= CLI = SIP username). Bas.
   - WSS/domain/password kuch nahi mangta (global se khud lagta hai).
   - Provider label sirf RECORD ke liye (kis carrier par user hai);
     routing ConnexCS mein hoti hai.

3) PROVIDER LIST editable — Create User page par niche
   "⚙ Manage provider list" -> naam add/edit karo (ek per line) -> Save.

4) ADD-ONS UI: edit popup mein ab "Conference (3-way)" toggle (har user par
   ON/OFF). 3-way ab sirf is toggle se (partner-plan coupling hata di).

5) Local presence: per-call CLI From header mein lagti rahegi (registration
   username nahi badalta — wo user ka fixed number).


RENDER ENV (ek dafa set karo)  << ZAROORI >>
--------------------------------------------
  SIP_WSS       = wss://dialnytics.sip.direct/ws
  SIP_DOMAIN    = dialnytics.sip.direct
  SIP_PASSWORD  = <wahi password jo tum ConnexCS SIP auth mein use karte ho>

Jab tak ye 3 set na hon, naya global-SIP mode OFF rehta hai (purane
sip_provider_id wale users phir bhi chalte hain — kuch nahi tootta).


CONNEXCS SIDE (tum manually — jaisa tum ne kaha)
------------------------------------------------
Har user ke liye ConnexCS customer mein ek SIP User Auth banao:
  - Username = us user ka NUMBER, sirf digits (e.g. +1 580 808 3238 ->
    username "15808083238")
  - Password = wahi SIP_PASSWORD (sab same)
Bas. Dialnytics is username/password se register karta hai, aur CLI usi
number se jati hai.


BADLI FILES  (latest code ke upar)
----------------------------------
  backend/main.py                       (global SIP, echo_cfg_for, labels, create)
  frontend/templates/users.html         (provider labels + manage + Conference toggle)
  frontend/templates/dialer_rail.html   (data-conf = conf_enabled)

DATABASE: koi manual SQL nahi — provider_label column khud ban jata hai.


ISTEMAAL / TEST (test-on-one)
-----------------------------
1) Render par SIP_WSS / SIP_DOMAIN / SIP_PASSWORD set karo. Deploy.
2) ConnexCS mein ek TEST number ke liye SIP User Auth banao
   (username = digits, password = SIP_PASSWORD).
3) Create User -> "Calling Provider" dropdown se label (jaise Infinity-USA)
   chuno -> number type karo (wahi jiska ConnexCS auth banaya) -> Create.
4) Us user se login -> dialer -> US call -> connect check karo.
   (CDR mein username ab us number ka hoga, 1004 nahi.)
5) Sahi chale to baqi users isi tarah banao — alag provider nahi banana.

PROVIDER NAAM ADD karna ho: Create User page -> "⚙ Manage provider list".


BACKWARD COMPAT
---------------
- Purane users jinke paas sip_provider_id hai -> waise hi chalte hain
  (echo_cfg_for pehle unka provider dekhta hai).
- SIP Providers page (ECONNET-CS etc.) abhi bhi hai; naye users ke liye
  zaroorat nahi.

Sawal ho to batao.
