=========================================================
  ADD-ONS UI FIX  —  Conference (3-way) toggle edit popup mein
=========================================================

KYA THEEK HUA
-------------
1) Edit popup (user Edit) ke add-ons mein ab naya toggle:
   "Conference (3-way / Add call)" — har user par seedha ON/OFF.
   (Pehle sirf Create form mein tha, edit mein nahi.)

2) 3-way ab SIRF is toggle se control hota hai (conf_enabled).
   Pehle wo galti se partner-plan + "Leave call" ke saath bandha tha —
   isi liye kuch users ka 3-way band rehता tha. Ab wo coupling hata di.
   conf_enabled default ON hai (sab users ko 3-way milta hai), toggle
   off karke kisi user se le sakte ho.

3) Edit popup khulne par Conference ki current value sahi dikhti hai,
   aur Save par save hoti hai.

BADLI FILES
-----------
  backend/main.py                       (/users/save mein conf_enabled)
  frontend/templates/users.html         (edit popup Conference toggle + JS)
  frontend/templates/dialer_rail.html   (data-conf ab sirf conf_enabled)

DATABASE: koi nayi table nahi (conf_enabled pehle se hai).

TEST
----
1) Deploy.
2) Kisi user ko Edit karo -> add-ons mein "Conference (3-way)" dikhega,
   ON hona chahiye (default). Save.
3) Us agent se dialer HARD-REFRESH (Ctrl+F5) -> call par "Add Call" dabao
   -> 3-way chal jayega (EchoDial par bhi).

NOTE: Conference har provider par chalta hai (Twilio lines par abhi nahi).
