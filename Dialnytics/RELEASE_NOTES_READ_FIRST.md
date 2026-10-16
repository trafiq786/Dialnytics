# Dialnytics integration build - read before deployment

## Implemented in this package
- PostgreSQL-backed users, caller-ID assignments, payments, scripts, sessions and call history.
- PostgreSQL-backed contacts (requires SUPABASE_MIGRATION_02.sql).
- Single active login session per user in PostgreSQL, with admin session revocation API.
- Ed25519 verification of Telnyx API v2 webhook payloads.
- Incoming call event storage, participant tracking, and atomic answer/decline state transitions.
- On group decline, a Telnyx hangup API request is attempted; the API response must be verified.
- Existing premium UI and outbound WebRTC dialer are retained.

## NOT completed / not verified
- Simultaneous carrier/WebRTC ringing to multiple users is NOT implemented. Telnyx call legs, dial/bridge and associated routing are still needed.
- Group first-answer winner is recorded in the database but not bridged to the PSTN caller.
- Previous active WebRTC call termination after another login is NOT implemented.
- Call recordings themselves are stored on the Render local filesystem, not persistent object storage.
- Some dashboard counters still use process memory rather than persisted call records.
- This package has NOT been tested against the live Supabase database or Telnyx account.

## Deployment safeguards
1. Back up any production data and review the SQL migration.
2. Run SUPABASE_MIGRATION_02.sql in Supabase before deploying.
3. Ensure DATABASE_URL, TELNYX_API_KEY, TELNYX_CONNECTION_ID, TELNYX_PUBLIC_KEY, ADMIN_PASSWORD, AGENT_PASSWORD are present as server environment variables.
4. Do NOT attach production phone numbers to the new Voice API App on the basis of this package.
5. Test in a separate environment before production; unverified integrations can fail at runtime.
