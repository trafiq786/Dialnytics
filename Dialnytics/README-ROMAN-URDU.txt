===========================================================
  SIP AUTO-PROVIDER  +  Add-ons UI  +  MOVE-TO-GLOBAL-SIP
  (user banao -> SIP khud, alag provider nahi)
  (purane users ko naye system par ek-click)
===========================================================

KYA BANA
--------
1) GLOBAL SIP (Render env) — WSS/domain/password ek dafa, sab users same.
   Har user ka apna NUMBER hi SIP username banta hai. Ab per-user "SIP
   Provider" banane ki zaroorat NAHI.

2) USER CREATE karte waqt:
   - "Calling Provider" dropdown mein carrier LABELS (Infinity-USA,
     Econnet, Didlogic ... + Telnyx/Twilio).
   - Label chuno -> number type karo (= CLI = SIP username). Bas.
   - WSS/domain/password kuch nahi mangta (global se khud lagta hai).
   - Provider label sirf RECORD ke liye.

3) PROVIDER LIST editable — Create User page par "⚙ Manage provider list".

4) ADD-ONS UI: edit popup mein "Conference (3-way)" toggle (har user par
   ON/OFF). Full-width card layout (UI fix shaamil).

5) >>> NAYA: MOVE-TO-GLOBAL-SIP <<<  (purane 1001/1004 wale users migrate)
   Purane users jinke paas apna alag "SIP Provider" laga hai (sip_provider_id)
   unko global SIP par le aao -> phir unka apna NUMBER hi SIP username banega.

   (a) EK USER:  Customers -> user kholo -> "Calling Provider & Number" card
       -> niche "🆕 Move to global SIP (new system)" -> (optional label)
       -> "Move to global SIP".
       Ye sirf tab dikhta hai jab user purane per-user SIP par ho.

   (b) SAB EK SAATH (bulk):  Routing page -> "🆕 Move to global SIP" panel
       -> (optional label) -> "Move N user(s) to global SIP".
       Panel batata hai kitne users abhi purane system par hain.

   Dono: sip_provider_id clear hota hai, number (CLI) aur hybrid inbound
   barqarar rehte hain. Koi call drop nahi.


RENDER ENV (ek dafa set karo)  << ZAROORI >>
--------------------------------------------
  SIP_WSS       = wss://dialnytics.sip.direct/ws
  SIP_DOMAIN    = dialnytics.sip.direct
  SIP_PASSWORD  = <wahi password jo ConnexCS SIP auth mein use karte ho>

Jab tak ye 3 set na hon: global-SIP mode + migration button OFF rehte hain
(purane sip_provider_id wale users phir bhi chalte hain — kuch nahi tootta).


PURANE USERS KO MIGRATE KARNE KA TAREEQA
----------------------------------------
Har purane user ke liye (ya bulk se sab ke liye):
  1) ConnexCS mein us user ke NUMBER ki SIP User Auth banao
     (username = sirf digits, e.g. 15808083238 ; password = SIP_PASSWORD).
  2) Dialnytics mein button dabao:
     - Ek user:  Customer page -> "Move to global SIP"
     - Sab:      Routing page -> "Move N user(s) to global SIP"
  3) User dialer HARD-REFRESH kare (Ctrl+F5) -> ab apne number se register.

Tip: pehle EK user par test karo (uska ConnexCS auth banao -> Customer page
se migrate -> refresh -> US call -> CDR mein username ab number ka hoga).
Theek chale to Routing se bulk kar do.


BADLI FILES  (latest code ke upar)
----------------------------------
  backend/main.py                        (global SIP, migration routes)
  frontend/templates/users.html          (provider labels + Conference toggle + UI fix)
  frontend/templates/dialer_rail.html    (data-conf = conf_enabled)
  frontend/templates/routing.html        (bulk Move-to-global-SIP panel)
  frontend/templates/customer_detail.html(per-user Move-to-global-SIP button)

DATABASE: koi manual SQL nahi — provider_label column khud ban jata hai.


BACKWARD COMPAT
---------------
- Purane users (sip_provider_id wale) deploy ke baad bhi waise hi chalte hain.
  echo_cfg_for pehle unka provider dekhta hai. Migration tab hi hoti hai jab
  tum button dabao. Koi disruption nahi.
- SIP Providers page (ECONNET-CS etc.) abhi bhi hai; naye users ke liye
  zaroorat nahi.

Sawal ho to batao.
