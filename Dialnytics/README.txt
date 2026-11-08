DIALNYTICS UPDATE R  -  Advanced call: uthate hi kat jana (2026-11-08)
=====================================================================
P + Q ke upar lagao. Sirf 1 file: backend/call_transfer.py

MASLA: client uthata tha -> server foran jodne ki koshish karta tha (update O ka tez raasta);
Telnyx ka koi bhi "abhi nahi" jawab aata to code dono calls kaat deta tha.
FIX:   tez raasta fail ho to ab KABHI call nahi katti; purana pakka raasta
       (browser leg answer hone ki khabar par jodna) khud jod deta hai.

Render log mein agar "early bridge not possible yet" dikhe to wahi case tha, aur call
phir bhi judni chahiye ("connected" line aayegi).
