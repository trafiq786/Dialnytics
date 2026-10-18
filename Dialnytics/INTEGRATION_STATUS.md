# Dialnytics PostgreSQL integration — STAGING ONLY

## Implemented in this build
- Database-backed user account records and caller ID assignment inserts.
- Database-backed single active login session per user; prior session revoked on new login.
- Database-backed PKR payment rows for new-user payments and renewals.
- Database-backed scripts save/edit/delete.
- Verified Telnyx webhook signatures, and incoming event metadata recorded in incoming_call_groups / call_participants.

## Not implemented or verified
- Ringing multiple WebRTC devices, first-answer-wins arbitration, decline-all call control.
- Force disconnect of already established calls when a session is revoked.
- Persistent contacts, recordings media, voicemail, campaign and outgoing call history.
- DB-backed session revocation push to already open tabs (requests are checked).
- Real Supabase integration testing and end-to-end Telnyx call tests.
- Migration of any pre-existing local users. Only default admin and agent are seeded when DB is empty.

## Safety
DO NOT deploy to the live service or move any phone number to the Voice API application yet.
Test with a separate staging Render service and separate test number. DATABASE_URL, ADMIN_PASSWORD,
AGENT_PASSWORD, TELNYX_API_KEY, TELNYX_CONNECTION_ID, TELNYX_PUBLIC_KEY belong only in Render secrets.
Do not upload users.json, .env, or local recordings to a public Git repository.

The app requires psycopg[binary] and a reachable Supabase PostgreSQL database.
Current implementation reads the database for each authenticated request and is not performance tuned.
