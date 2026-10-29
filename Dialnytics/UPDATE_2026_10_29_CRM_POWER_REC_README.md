# CRM import format + faster power-dialer outcome + Twilio recording (2026-10-29)

1. CRM CSV import now accepts a plain lead list like:
   Name, Company, Website, Phone Number, Notes
   - Headers are matched loosely (case/space-insensitive; "Phone Number " works).
   - Company, Website and Notes are saved and shown in the CRM.
   - If the CSV has NO consent column, leads import with consent = yes (you are
     importing your own list). If a consent column exists, it is still honoured.
   - Duplicate phone numbers already in your CRM are skipped.
   - New columns company/website are added automatically (migration 18).

2. Power Dialer: saving a call outcome is now instant. It used to reload the
   whole queue from the server on every click (one slow round trip); now it
   updates in place, so the next lead comes up immediately.
   NOTE: for the biggest speed gain also deploy the SPEED build and set Render
   `--workers 4` + Supabase transaction pooler (see the SPEED readme).

3. Twilio call recording now works for admin monitoring (the recorder reads the
   call's audio from the peer-connection, which Twilio needs). Only ANSWERED
   calls are recorded — "No answer"/busy calls have no audio to record.

## Files
- backend/main.py
- frontend/static/js/dialer.js        (Twilio recording capture)
- frontend/static/js/crm.js           (show company/website)
- frontend/static/js/power-dialer.js  (instant outcome)

After deploying, hard-refresh the dialer (Ctrl+Shift+R). If Cloudflare proxy is
on, also Purge Everything so the new JS loads.
