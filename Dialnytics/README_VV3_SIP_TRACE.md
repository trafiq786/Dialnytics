# Update VV3: Test page mein SIP trace (provider ko dikhane ke liye)

Provider ko "logs" chahiye. Ab test page call ke waqt raw SIP messages dikhata hai:
hamari INVITE (us se server) aur server ka 405 jawab. Yahi un ko bhejna hai.

## File
- frontend/static/sip-test.html (sirf yahi; jssip.min.js aur voice_helpers.py pehle se theek hain)

## Deploy
Sirf sip-test.html GitHub pe replace karein, phir Render → Manual Deploy.

## Test
1. Page refresh karein.
2. WSS: wss://sip.echodial.ai:443/ws  (ya jo chal raha tha)
3. Username dialnytics, password, "Pehle REGISTER karein" tick, Connect.
4. "REGISTER ok" aaye to number daal ke Call.
5. Neeche naya **SIP trace** box bhar jayega — us mein "SENT ... INVITE" aur "RECEIVED ... 405" dikhega.
6. **Copy** dabayein, aur poora trace provider ko bhej dein.
