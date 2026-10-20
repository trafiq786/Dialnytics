# Dialnytics staging security patch

This package is NOT the complete incoming group calling or Supabase migration.

Changes: Telnyx API v2 Ed25519 webhook signature validation with a 5-minute timestamp window. Requires TELNYX_PUBLIC_KEY in Render.

Before production: implement durable database persistence for all records, transactional call ownership, Telnyx call-control fan-out and hangup/bridge operations, and session revocation that terminates active WebRTC calls. Test webhook replay and Telnyx incoming call behavior.

Do not attach a production phone number to the Voice API app yet. Existing local users.json and memory-based state are still not production-safe.
