DIALNYTICS UPDATE Q  -  Chalti call ka voicemail ki wajah se kat jana (2026-11-08)
==================================================================================
Update P ke upar lagao. Sirf 1 file: backend/main.py

MASLA
-----
Incoming call uthate hi "Call ended" aa jata tha aur doosri taraf "Calling" atka rehta tha.
Wajah: agent ke uthate waqt Telnyx ki ek purani ringing leg band hoti thi; server samjhta
tha kisi ne nahi uthaya -> voicemail -> voicemail ka answer fail (call pehle hi uth chuki
thi, Telnyx 422) -> code chalti hui call KAAT deta tha.

FIX
---
1. Ringing leg band hone par server 1.5 second ruk kar dobara dekhta hai ke call uth to
   nahi gayi; uth gayi ho to voicemail nahi.
2. Voicemail ka answer fail ho to server Telnyx se poochta hai: call abhi zinda hai?
   Zinda hai to kuch nahi kaat-ta, call log wapas "answered" kar deta hai.
3. Render log mein Telnyx ki asli wajah ek line mein (lamba traceback nahi).

TEST
----
Apne doosre number par call karo -> wahan uthao -> dono taraf awaz, koi "Call ended" nahi.
Render log mein "Voicemail skipped ... already connected" aaye to fix ne kaam kiya.
