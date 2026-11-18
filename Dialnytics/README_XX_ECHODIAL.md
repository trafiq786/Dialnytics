# Update XX: EchoDial provider + manual number entry (WW ka updated version)

Ye WW ki jagah use karein — is mein WW ka sab kuch hai, PLUS:
- User banate waqt AUR provider change karte waqt ab **number khud type** kar sakte hain
  ("✎ Type manually" link). EchoDial chunne par ye khud text box ban jata hai.
- EchoDial ke liye number kisi list se nahi, aap jo approved CLI type karein wahi lagti hai.

## Pehle ye karein (warna calls fail hongi)
1. Apne DIDs EchoDial par **approved CLI** karwayein.
2. Render mein 4 Environment variables:
   - ECHODIAL_WSS    = wss://sip.echodial.ai:443/ws
   - ECHODIAL_DOMAIN = sip.echodial.ai
   - ECHODIAL_USER   = dialnytics
   - ECHODIAL_PASS   = (password — seedha Render mein)

## Files
- backend/main.py
- backend/voice_helpers.py
- frontend/templates/base.html
- frontend/templates/customer_detail.html
- frontend/templates/users.html
- frontend/static/js/dialer.js
- frontend/static/js/jssip.min.js
- frontend/static/css/style.css

## Deploy aur TEST (pehle 1 user)
1. Saari files upload + 4 env vars + Deploy.
2. Customers → test user → "Switch provider — keep same number" → EchoDial → Switch.
   (Ya "Change number / provider" mein provider EchoDial chunein, "✎ Type manually" se CLI type karein.)
3. Us user ka number EchoDial par approved CLI ho.
4. User dialer refresh kare → "Ready" → outbound call test.
5. Theek chale to baqi par rollout (ya /admin/provider-switch se bulk — button baad mein).

## Yaad rahe
- EchoDial sirf aap ke browser se live chalti hai; maine yahan se live test nahi kiya,
  sirf code check kiya. Is liye PEHLE 1 user par azmayein.
- EchoDial par abhi Advanced calling/transfer/recording/live-listen nahi (Telnyx-only features).
- Inbound hybrid (Twilio se).
- Kuch toote to Render → Events → Rollback. Telnyx/Twilio users mehfooz.
