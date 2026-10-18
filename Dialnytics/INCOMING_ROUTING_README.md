# Incoming routing implementation (unverified)

This build adds Telnyx Voice API `POST /v2/calls` with `link_to`, `bridge_intent`, and `bridge_on_answer` for the single assigned user's SIP username. On a verified `call.initiated` webhook it looks up the number assignment in Supabase and originates a SIP leg to `sip:<sip_username>@sip.telnyx.com`. Duplicate initial events do not create extra legs.

Prerequisites: `TELNYX_API_KEY`, `TELNYX_CONNECTION_ID`, `TELNYX_VOICE_APP_ID`, `TELNYX_PUBLIC_KEY`, `DATABASE_URL`, user has previously signed in and generated their WebRTC credential, browser is online and Telnyx registered. The DID must ultimately be routed to the Voice API application.

This has not been tested against Telnyx or Supabase. Voice API application `connection_id` behavior, SIP URI delivery to on-demand WebRTC credentials, and auto-bridge must be validated in a live test before moving a production DID. Do not replace production until verified. Render Free sleeping can prevent reliable inbound calls. Existing security, persistence and active-call revocation limitations remain.
