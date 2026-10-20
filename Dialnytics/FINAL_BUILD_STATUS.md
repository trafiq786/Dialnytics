# Dialnytics integrated code build — testing deferred

This archive combines the latest provided Dialnytics premium UI with Supabase-backed users, payments, scripts, sessions, 1-number/1-user assignments, signed Telnyx webhooks, and experimental Voice API incoming SIP-leg routing.

## Added in this revision

- On a new login, previously issued sessions are revoked in Supabase. Tracked inbound Voice API calls belonging to the user are marked ended and Telnyx hangup requests are issued for their stored inbound call-control IDs.
- Admin force logout now issues the same carrier-side hangup requests for tracked inbound calls and returns actual success/failure counts.
- Browser session guard already tears down local WebRTC legs after a confirmed session revocation.

## Important limitations

- **Not live-tested or verified.** Syntax compilation does not prove Telnyx delivery or bridging.
- Outbound browser/WebRTC calls may not expose a server-side Telnyx call-control ID, so the server cannot guarantee carrier-side termination of those calls. Local browser disconnect occurs when the heartbeat detects session revocation.
- The current incoming Voice API SIP destination and bridge request fields have not been confirmed against a live Telnyx connection. Test with a non-production number before moving an existing number.
- Session heartbeat checks every 5 seconds; it is not instantaneous.
- A carrier hangup can fail (network/provider error); the endpoint returns counts and server logs include failures.
- Render Free may sleep and delay incoming webhooks. Local recording files are not persistent on ephemeral hosting.
- Do not replace production without reviewing migration scripts, environment variables, and completing call tests.

## Existing setup

- Supabase tables and unique caller ID index were created by the user.
- Environment variable names: DATABASE_URL, TELNYX_API_KEY, TELNYX_CONNECTION_ID, TELNYX_VOICE_APP_ID, TELNYX_PUBLIC_KEY, ADMIN_PASSWORD, AGENT_PASSWORD.
- Never upload .env, credentials, or users.json to GitHub.
