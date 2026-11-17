# Update VV: EchoDial SIP test page (sirf test, live dialer ko haath nahi lagta)

Ye sirf ye dekhne ke liye hai ke echodial ka WSS (wss://sip.echodial.ai:5060) browser se judta hai aur call lagti hai ya nahi. Agar chal gaya, phir poora integration karenge.

## Files
- frontend/static/sip-test.html (naya test page)
- backend/voice_helpers.py (CSP mein echodial allow kiya — iske baghair browser nahi judega)

## Deploy
Dono files GitHub pe upload karein, phir Render → Manual Deploy.

## Test kaise karein
1. Browser (laptop Chrome behtar) mein kholein:
   **https://dialnytics.co.uk/static/sip-test.html**
2. Password wale khaane mein echodial ka password likhein (ye sirf aap ke browser mein rahega, kahin send nahi hoga).
3. **Connect** dabayein. Mic ki ijazat "Allow" karein.
   - "WebSocket connected" aur status **connected** (hara) aa jaye → WSS chal raha hai ✓
   - "WebSocket disconnected" ya error → WSS nahi chal raha (neeche dekhein).
4. Number mein koi chalu US number likhein (country code 1 ke saath, bina +, jaise 17045978991).
5. **Call** dabayein.
   - Ring ja kar baat ho jaye → poora raasta kaam kar raha hai ✓
   - Error aaye → neeche wala log (kaali screen) ka screenshot bhejein.

## Agar connect hi na ho
- Pehli dafa fail ho to "Pehle REGISTER karein" wala box tick kar ke dobara Connect karein.
- Phir bhi na ho → kaali screen (log) ka screenshot bhej dein. Us se pata chalega ke WSS port 5060 pe waqai hai ya nahi.

## Test ke baad
Ye page baad mein hata denge. Isy kisi aur ko na dein, kyun ke is se aap ka SIP account istemal hota hai.
