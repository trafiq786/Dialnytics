===========================================================
  AI — LOCAL PRESENCE (owned caller-ID, area-code matched)
===========================================================

KYA ADD HUA
-----------
Jab kisi user par "Local Presence" ON ho, to uski har EchoDial call par
backend us destination ke AREA CODE ki ek OWNED caller-ID pool se chun kar
bhejta hai — call local lagti hai. Agar us area code ki CLI pool mein na ho,
to us user ka apna number use hota hai (safe fallback). Sab per-user hai;
baqi users bilkul normal.

Misal: user ka number area 252 ka hai, call 660 waley number par -> system
pool se 660 wali approved CLI pick kar ke bhejta hai. Destination ko 660
(local) dikhta hai. Delay koi nahi (ek chhota DB lookup).


BADLE / NAYE FILES (apne repo mein isi jagah replace karo)
----------------------------------------------------------
  backend/main.py                         (schema + /api/pick-cli + admin routes)
  frontend/templates/base.html            (nav mein "Local Presence" link + dialer.js version)
  frontend/templates/dialer_rail.html     (data-localpresence attribute)
  frontend/templates/local_presence.html  (NAYA admin page)
  frontend/static/js/dialer.js            (echodial call ab area-matched CLI pick karti hai)


DATABASE
--------
Koi manual SQL nahi chalani. App start hote hi khud ban jata hai:
  - dialnytics_users mein naya column: local_presence (default false)
  - naya table: local_presence_clis (number, area_code)


ISTEMAAL (STEP BY STEP)
-----------------------
1) Deploy karo (Render par push). App restart par DB khud migrate ho jayega.

2) Admin panel -> sidebar mein naya link "Local Presence" (📍) -> kholo.

3) "Import CSV" se apni owned numbers ki CSV upload karo (column A, ek number
   per row — 10-digit US). Area code khud nikal lega, duplicates skip. Baar
   baar import kar sakte ho. Upar "numbers in pool" + top area codes dikhte hain.

4) **Pehle SIRF 1 test user** par "Turn on" dabao (test-on-one-user-first).
   Baqi users ko abhi haath mat lagao.

5) Us test user se: dialer **hard-refresh** (Ctrl+F5 — nayi dialer.js version),
   phir koi US number dial karo jiska **area code pool mein mojood ho**.
   -> ConnexCS CDR mein dekho: jo CLI gayi wo us area code ki honi chahiye.

6) Sahi chale to baqi users par ON kar do. Jis par OFF hai wo apne assigned
   number se hi call karega (koi farq nahi).


ZAROORI — OWNERSHIP + CONNEXCS SIDE
-----------------------------------
- Pool mein SIRF apne OWNED / authorized numbers daalo. Kisi aur ke ya random
  numbers ko caller-ID banana illegal spoofing hai.

- ConnexCS par ye CLIs pass honi chahiye. Agar call par "405 CLI Restriction
  in effect" aaye, to ya to customer ke CLI panel mein ye numbers allow karo,
  ya us customer ki CLI restriction OFF kar do (kyunke ye sab owned/approved
  hain). Carrier (Econet) par bhi ye numbers approved hone chahiye.


ROLLBACK
--------
Kisi bhi user ka "Turn off" dabao -> wo foran apne normal number par aa jata
hai. Poora feature band karna ho to purani 4 files wapas daal do (local_presence.html
bas ignore ho jayega). DB column/table rehne do — koi nuqsan nahi.

Sawal ho to batao.
