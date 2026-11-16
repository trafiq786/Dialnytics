# Update OO: conference call mein awaz ki deri kam

## Kya badla
Conference (Add Call → Merge) mein teeno logon ki awaz agent ke browser mein milti hai. Pehle:
- Browser har line ki aati hui awaz ka 1–2 second tak ka buffer bana leta tha.
- Awaz milaane wala hissa doosri sample rate pe chalta tha, is liye har awaz ko convert karna parta tha.

Ab:
- Har line ka buffer jitna network ijazat de utna chhota rakha jata hai.
- Mixer 48 kHz pe chalta hai, jo calls ki apni rate hai. Koi conversion nahi.

## Files
- frontend/static/js/dialer.js
- frontend/templates/base.html (naya version number, taake browser purani file na chalaye)

## Deploy ke baad
Users ek dafa page refresh karein, phir conference test karein.

## Agar agent ko line pe rehna zaroori nahi
"Leave call" istemal karein. Server dono ko seedha jod deta hai, aur agent ke browser se awaz guzarti hi nahi, is liye koi deri nahi. Outgoing calls pe Leave call ke liye Advanced calling on honi chahiye.
