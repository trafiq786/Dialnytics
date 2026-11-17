# Update VV2: CSP mein port 5060 allow (sirf 1 file)

Pichhli VV mein echodial allow to tha, lekin port 5060 ke baghair, is liye browser ne block kiya
("violates Content Security Policy" wala error).

Ye sirf us ek file ko update karta hai jo CSP banati hai, ab har port allow hai.

## File
- backend/voice_helpers.py

## Deploy
Sirf yahi file GitHub pe upload karein (purani jagah replace), phir Render → Manual Deploy.
Deploy ke baad test page dobara kholein aur Connect karein.
