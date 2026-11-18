===========================================================
  Dialnytics — Update AB  (XX ke upar)
  EchoDial: Leave call  +  Ringing tone fix
===========================================================

Ye zip XX k UPAR lagta hai aur DO cheezein deta hai (ZZ +
ringback dono is mein shamil hain — agar ZZ deploy nahi
kiya to bhi sirf ye laga dein):

1) RINGING TONE FIX (naya)
   Masla: EchoDial par call lagao to "ring-ring" sunai nahi
   deti thi, seedha client se connect lagta tha.
   Wajah: EchoDial khud in-band ringback nahi bhejta, aur
   dialer local ring tone sirf Telnyx par baja raha tha.
   Hal: Ab EchoDial par bhi dial karte hi local ring tone
   bajta hai, aur jaise hi call uthti hai (ya asli audio
   aati hai) wo khud ruk jata hai.

   NOTE: Agar phir bhi ring k baghair seedha connect ho, to
   iska matlab aap ka EchoDial trunk INVITE ka jawab foran
   "200 OK" de raha hai (answer supervision OFF). Wo TRUNK
   setting hai — EchoDial support se bolein ke call uthne se
   pehle "180/183 (ringing/progress)" bhejein aur answer
   supervision ON karein. Dialer ki taraf se ab ring tone
   lag chuka hai.

2) LEAVE CALL (ZZ wala, browser-bridge)
   EchoDial par Leave call ab SIP REFER se NAHI (jo decline
   deta tha), balki do caller aap ke BROWSER k zariye aapas
   mein jure rehte hain. Tab khula rakhna zaroori hai.
   (Tafseel ZZ README mein thi — wahi behaviour.)

-----------------------------------------------------------
  FILES (sirf 4, backend/main.py bilkul nahi badla)
-----------------------------------------------------------
  frontend/static/js/dialer.js
  frontend/templates/dialer_rail.html
  frontend/templates/base.html          (dialer.js?v=20261123)
  frontend/templates/users.html

Deploy k baad dialer aik dafa refresh karein (Ctrl+F5).

Ye saare changes sirf EchoDial par asar karte hain; Telnyx
aur Twilio users jaise the waise rahenge.
