# Incoming fixes - deployment notes

1. Back up Supabase before changes.
2. Run SUPABASE_MIGRATION_05_INCOMING_LOGS.sql in Supabase SQL Editor.
3. Deploy all three updated files together (main.py, dialer.js, call_logs.html).
4. Hard-refresh browser and test an inbound call: answer, decline, remote hangup, missed call, and filters.
5. Inspect Render logs and Telnyx call flow for any carrier hangup failures.

## Caveats
- Code/static checks only; live Telnyx tests not performed.
- Incoming caller ID displays the original Telnyx `from` value when available. Anonymous caller ID cannot be reconstructed.
- For safety, decline requires exactly one recent pending group if the browser has not cached its group ID; ambiguous simultaneous calls are not auto-hung-up.
- Existing historical incoming groups are not backfilled into public.calls.
- Call duration for incoming calls uses webhook timing, not precise answered-at time; refine with answered_at tracking for accurate talk time.
- A failed Telnyx hangup is reported to browser, not falsely claimed successful.
- Current inbound SIP leg status tracking may need additional provider-event mapping after live tests.
