# Dialnytics source build — testing deferred

This ZIP is a **code-only integration build**, not a verified final release.

## Included
- Supabase-backed user, payment, script and session operations from prior checkpoint.
- One-number/one-user assignment enforcement (requires unique database index).
- Telnyx signed webhook verification and inbound event recording.
- Incoming SIP/WebRTC popup handler present in frontend.
- New 5-second browser session heartbeat and local WebRTC teardown on revoked login.
- Admin force-logout endpoint.

## NOT COMPLETE / NOT VERIFIED
- Voice API incoming-call leg routing to the assigned WebRTC client.
- Carrier-side termination of an existing call on login revocation.
- End-to-end Supabase connectivity, live inbound/outbound Telnyx calling, and UI testing.

**Do not assign a production Telnyx number to the Voice API application or replace the live service until those are implemented and validated.**
No API keys, passwords or database URLs are bundled.
