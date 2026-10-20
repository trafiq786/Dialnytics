# Dialnytics update 07 — staging release

## Required
1. Back up Supabase and project. Run SUPABASE_MIGRATION_07_LIVE_AND_PROVIDER.sql.
2. Upload changed files, deploy to staging first, test all call paths.

## Included
- Live Monitoring admin page, browser heartbeat every 5s, UI refresh every 3s.
- Provider Switch admin readiness page. **Twilio switch is disabled** until genuine Twilio calling implementation, verified number assignment, incoming webhooks, and active-call handling exist. This is NOT a complete dual-provider switch.
- Adaptive CSS and mobile navigation toggle.

## Still requires validation / work
- Incoming decline carrier-side repeat ring: existing logic retained; cannot certify fixed without paired carrier event trace and SIP leg mapping.
- Call Logs/Contacts direct dial: existing /dialer -> /dashboard?number=...&call=1 path retained; requires browser validation with WebRTC ready event.
- Presence is browser-reported, not carrier-authoritative. It can miss calls from other devices and can be stale for up to 20 seconds.
- Provider history, switch-all, Twilio integration, and active-call safe switching NOT included.
