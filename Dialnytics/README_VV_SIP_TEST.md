# Update VV: EchoDial SIP test page (sirf test, live dialer ko haath nahi lagta)

Ye sirf ye dekhne ke liye hai ke echodial ka WSS (wss://sip.echodial.ai:5060) browser se judta hai aur call lagti hai ya nahi.

## Files
- frontend/static/sip-test.html (test page)
- frontend/static/jssip.min.js (SIP library — isi ke saath page chalta hai)
- backend/voice_helpers.py (CSP mein echodial allow — iske baghair browser block karta hai)

## Deploy
Teeno files GitHub pe upload karein, phir Render → Manual Deploy.
Render mein koi variable add NAHI karna. Password aap page pe khud likhenge.

## Test
1. Laptop Chrome mein kholein: **https://dialnytics.co.uk/static/sip-test.html**
   (Upar "JsSIP loaded ✓" aana chahiye.)
2. Password likhein, **Connect** dabayein, mic "Allow" karein.
   - "WebSocket connected ✓" + status hara → WSS chal raha hai.
   - "disconnected" / error (code) → WSS nahi chal raha.
3. Number likhein (jaise 17045978991), **Call** dabayein.
   - Ring + baat → poora raasta theek ✓
   - "Call FAILED" + koi number (jaise 403/404/488) → us ka matlab main bata doon ga.

## Mujhe batayein
- Status hara hua ya laal?
- Kaali screen (log) ka screenshot — us mein saari details hoti hain.

Pehli dafa call se na chale to "Pehle REGISTER karein" tick kar ke dobara Connect karein.
