# Update WW: EchoDial provider (outbound), hybrid inbound

EchoDial (ConnexCS) ab dialer mein ek provider hai, Telnyx/Twilio ki tarah.
- Outbound call EchoDial se (browser WebRTC / JsSIP, wss://sip.echodial.ai:443/ws).
- Caller ID = us user ka apna number (CLI). Number wahi rehta hai, sirf provider badalta hai.
- Inbound HYBRID: inbound EchoDial se NAHI — purane tareeqe (Twilio) se. (Jaise pehle twilio_in hybrid.)
- EchoDial users par abhi Advanced calling / transfer / recording / live-listen nahi chalega
  (wo Telnyx Call Control par bane hain). Basic calling: dial, answer, mute, hold, hangup, keypad.

## Pehle ye karein (warna calls fail hongi)
1. **Apne saare DIDs EchoDial par "approved CLI"** karwayein. Jo number kisi user ko assign hai,
   wo EchoDial par approve hona zaroori hai, warna us ki call "405 CLI Restriction" degi.
2. **Render mein ye Environment variables** add karein:
   - ECHODIAL_WSS   = wss://sip.echodial.ai:443/ws
   - ECHODIAL_DOMAIN = sip.echodial.ai
   - ECHODIAL_USER  = dialnytics
   - ECHODIAL_PASS  = (EchoDial password — chat mein nahi, seedha Render mein)

## Files
- backend/main.py              (PROVIDERS, /api/echodial-token, set-provider, provider-switch, hybrid sync)
- backend/voice_helpers.py     (CSP: echodial WSS allowed — zaroori)
- frontend/templates/base.html (echodial par JsSIP load; hybrid par Twilio bhi)
- frontend/templates/customer_detail.html (per-user "Switch provider — keep same number")
- frontend/static/js/dialer.js  (EchoDial calling path — isolated; Telnyx/Twilio par koi asar nahi)
- frontend/static/js/jssip.min.js (SIP library — nayi file)
- frontend/static/css/style.css (EchoDial pill color)

## Deploy aur TEST (sirf 1 user par pehle)
1. Saari files GitHub par upload, Render par 4 env variables, phir Deploy.
2. Ek TEST user kholein: Customers → us user → "Switch provider — keep same number" → **EchoDial** → Switch.
3. Us user ka number EchoDial par approved CLI hona chahiye.
4. Us user ke dialer ko refresh karein. Status "Ready" aana chahiye.
5. Outbound call karein. Theek chale to baqi users par rollout.

## Baad mein (bulk switch)
Jab test theek ho, saare users ek saath move karne ke liye ye endpoint hai (abhi button nahi):
POST /admin/provider-switch  (from_provider, to_provider)
Bata dena, main is ke liye ek button laga doon ga.

## Agar kuch toote
Render → Events → pichhle deploy ke saamne Rollback. EchoDial ka code isolated hai,
is liye Telnyx/Twilio users mutasir nahi hone chahiyen.
