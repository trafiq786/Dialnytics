# Dialnytics Update 08 — Twilio + Calling Cost (STAGING)

## Scope
- Existing Telnyx routes and UI preserved; new provider selection on Admin > Customer Details.
- Twilio browser Voice SDK: outgoing/incoming, answer, reject and hangup basic controls.
- Per-customer incoming/outgoing estimated USD call cost, with Today / This Week / This Month filters.
- All other original files retained, except targeted changes in backend/main.py, templates/base.html, templates/dialer_rail.html, templates/customer_detail.html, static/js/dialer.js and requirements.txt.

## BEFORE deploying (mandatory)
1. Back up Supabase. Run SUPABASE_MIGRATION_08_TWILIO_COST.sql in Supabase SQL Editor.
2. Set Render secret env vars: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_API_KEY_SID, TWILIO_API_KEY_SECRET, TWILIO_TWIML_APP_SID, PUBLIC_BASE_URL (https://your-public-host without trailing slash).
3. In Twilio create a TwiML App with Voice Request URL `https://YOUR-HOST/twilio/voice/outgoing`, HTTP POST.
4. Set Twilio US purchased number Voice webhook `https://YOUR-HOST/twilio/voice/incoming`, HTTP POST.
5. Set outgoing caller permissions and geographical permissions in Twilio, ensure number is voice-capable and account fully enabled.
6. Admin > Customers > Customer Details > Calling Provider Switch. Assign an owned Twilio number, select Twilio, save. User refreshes browser.
7. Test with ONE dedicated test user and real test number first. Do NOT switch active callers.

## Cost caveats
Cost Analytics is ESTIMATED, not provider billing reconciliation. Default configurable per-minute estimates:
TELNYX_EST_INCOMING_USD_MIN=0.0052
TELNYX_EST_OUTGOING_USD_MIN=0.007
TWILIO_EST_INCOMING_USD_MIN=0.0085
TWILIO_EST_OUTGOING_USD_MIN=0.014
Rates may differ for UK/mobile/international destinations and multiple call legs. No number rental/taxes/subscriptions included. Totals are seconds/60 times configured flat rate; no carrier rounding. Do not treat as actual provider invoice.

## Limits and safety
- This is an unverified staging build. Real Twilio/Telnyx calls and webhook signatures have NOT been end-to-end tested here.
- Twilio-specific advanced controls (hold, transfer, conference, recording) remain Telnyx-specific and are NOT implemented for Twilio.
- Twilio outgoing carrier callback currently does not fully reconcile child CallSid to browser-created call logs; browser-recorded duration is an estimate. Incoming provider webhook tracks call attempts and basic status.
- Incoming calls require the browser to be open and Twilio Voice Device registered; no mobile background push.
- Ensure applicable calling consent, DNC and telecom compliance; do not deploy to production until tested.
- Never paste secrets into GitHub or chat. Configure them as Render environment variables.
