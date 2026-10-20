# Dialnytics - recording control, demo accounts, and user removal

## What changed
- Added REC/STOP control to the in-call dialer UI, including the dashboard rail. Recording remains restricted to accounts with recording permission. The existing browser recorder currently captures the remote audio stream only, not a guaranteed two-way mix.
- Added admin-only 1-hour demo checkbox when creating a user. Demo time starts on the first successful login, stored in PostgreSQL. Every authenticated request checks expiry; the browser session heartbeat will eventually log the user out. No payment is collected for a demo account.
- Added admin-only Delete button, which **soft-deletes** the account (is_active=false), revokes sessions, releases caller ID, and attempts to hang up tracked inbound calls. Financial history remains retained. This does not guarantee hangup of every outbound carrier leg.

## Required migration BEFORE deploying
Run `SUPABASE_MIGRATION_03_DEMO.sql` in the existing Supabase project's SQL editor. It only adds demo fields to `dialnytics_users`.

## Deployment
Upload the updated project files to GitHub as one commit. Keep Render Root Directory `Dialnytics`, and the existing environment variables. Deploy only after the migration. Avoid sharing database passwords or Telnyx keys.

## Known limitations
- Live calling and database migrations have NOT been end-to-end tested. Python syntax and template parsing checks only.
- Recording files are still written to Render's local ephemeral filesystem. They can disappear after redeploy/restart; `/media` is not private storage. Configure authenticated durable object storage before real customer recordings. Do not assume that both sides of the conversation are captured.
- Demo expiration relies on request/session checks; active carrier-side outbound calls are not guaranteed to terminate at the exact 60-minute boundary.
- User deletion is a soft-delete for audit history, not irreversible personal-data erasure. Carrier-side outbound call termination is not guaranteed.
- Review applicable recording-consent and data-retention requirements before enabling call recording for customers.
