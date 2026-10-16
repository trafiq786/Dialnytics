# Dialnytics — Power Dialer + CRM update

## Added
- Premium responsive CRM lead management, editing, notes, status, follow-up and CSV import.
- Dedicated Power Dialer with Auto Next and Manual Next, 3–30-second delay, queue progress, Pause/Resume/Stop, and call disposition.
- PostgreSQL-backed leads, queue snapshots and dispositions, scoped to authenticated user.
- Explicit opt-in requirement, do-not-call filtering, duplicate prevention and eligibility recheck immediately before a call.
- Uses existing Telnyx WebRTC dialer, not a second SDK; never places calls until the user presses Start.
- Existing Dashboard, Customers, Invoices, manual dialer and other pages retained.

## Install (order matters)
1. Back up Supabase data and run `SUPABASE_MIGRATION_05_POWER_CRM.sql` in the Supabase SQL Editor.
2. Upload updated `Dialnytics` project files to GitHub without `.env`, database secrets or API keys.
3. In Render, deploy the latest commit after migration is successful.
4. Log in, add a CRM lead with explicit consent (E.164 phone), open Power Dialer, create a queue, choose mode and Start.

## CSV import
UTF-8 `.csv` with `name,phone,email,consent` columns; consent must be `yes`, `true` or `1` for import. Optional `do_not_call` field. Max 500 rows and 250 KB per upload. Numbers must use international E.164 format.

## Important limitations
- No live Supabase or Telnyx call tests performed in this build. Static Python, JS and Jinja syntax checks only.
- Auto Next runs only while the Power Dialer browser page is open and requires a saved call disposition before continuing.
- Call initiation uses the existing WebRTC client; it inherits any Telnyx/SDK limitations and any existing call-status sync issues.
- Queue state is saved in PostgreSQL, but after a browser refresh you must create a new queue; there is no restore-current-queue UI yet.
- There is no provider-side telemarketing compliance engine, calling-hours enforcement, automated opt-out ingestion, retry policy or concurrency scheduler. Operators must comply with applicable law and respect opt-outs.
- A single-user browser queue is supported; there is no predictive dialing or parallel calls.
- Frontend and routes are code-integrated, but production readiness requires deployed tests.
