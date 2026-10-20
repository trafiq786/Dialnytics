# Dialnytics coding checkpoint (NOT production-ready)

Changes made in this coding pass:
- Default admin/agent seed accounts no longer claim the same hard-coded telephone number.
- New user creation requires confirmation before **transferring** an already-assigned Caller ID; it removes the old user's assignment instead of sharing the number.
- User synchronization removes obsolete caller-ID assignment rows.
- Added authenticated `GET /api/incoming/pending` for read-only visibility into recent verified inbound webhook events assigned to a user.
- No Telnyx credentials or database secrets are included.

**Important limitations:**
- This is a coding checkpoint, NOT the verified final ZIP.
- `GET /api/incoming/pending` is diagnostic only. It does not cause the browser to ring and does not connect a Voice API carrier leg to WebRTC.
- The Telnyx Voice API inbound routing, bridging/answer/hangup orchestration, browser incoming integration and active-call termination on session revocation remain incomplete.
- A live Supabase connection and actual Telnyx inbound calls have not been tested.
- Do not deploy this package over the working production site.
- The existing Supabase unique index `one_user_per_caller_id` is required.
