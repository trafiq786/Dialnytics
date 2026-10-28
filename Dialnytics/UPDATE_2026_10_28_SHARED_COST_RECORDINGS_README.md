# Shared numbers + dashboard margin + admin call recordings (2026-10-28)

Three features in one update. Nothing is removed; existing users and data are safe.
New database columns/tables are created automatically on start (migrations 14 & 15).

## 1. Shared number (ring group) — Telnyx 1/2 and Twilio 1/2
- A number can now be given to several users of the SAME company. Assign it from
  Create User (pick an existing company + the number) or Customer Details → the number
  list shows "share with … (same company)". Confirm and all of them keep the number.
- Incoming call: every member who is online and free rings at the same time (30 s).
  The first to answer gets the call; everyone else stops ringing.
- A member already on a call does not ring. The next call goes to the other free members.
- If everybody is busy: the caller hears hold music and the first member to become
  free is rung (up to 3 minutes), then voicemail.
- If everybody is offline: straight to voicemail.
- Call logs: a missed call and a voicemail show in every member's log; an answered
  call shows only in the log of the member who took it.
- Outgoing calls still use the shared number as caller ID.
- SMS to a shared number is one inbox that every member of that company sees.
- Single-user numbers keep working exactly as before.
- New hold-music files: frontend/static/audio/hold-part1.mp3 and hold-part2.mp3.

## 2. Admin dashboard — cost, revenue and margin
- The admin dashboard now shows, for Today / This Week / This Month:
  Revenue (recorded payments), Cost (estimated), and Margin (revenue − cost, red when negative).
- Plus a breakdown per calling account: Telnyx 1, Telnyx 2, Twilio 1, Twilio 2.

## 3. Admin call recordings (fraud monitoring)
- Every call (incoming and outgoing, Telnyx and Twilio) is recorded by the dialer and
  uploaded for the admin only. This is separate from the customer's own REC button and
  does not need the $25 upgrade.
- Customer Details → "🎙 Recordings" opens a page with every call recording, with
  filters (direction, number, date) and play/download.
- Recordings auto-delete after 14 days (set MONITOR_RECORDING_DAYS to change).
- Storage: Supabase Storage bucket when configured, else the database. ~120 KB per minute.
- Disclose call recording in your website terms & conditions (legal requirement in the UK
  and many countries). No in-dialer notice is shown.

## Files changed
- backend/main.py
- backend/ring_group.py  (NEW)
- backend/voice_helpers.py
- frontend/static/js/dialer.js
- frontend/static/audio/hold-part1.mp3, hold-part2.mp3  (NEW)
- frontend/templates/dashboard.html
- frontend/templates/customer_detail.html
- frontend/templates/users.html
- frontend/templates/admin_recordings.html  (NEW)

## Optional environment variables (all have defaults)
- RING_GROUP_RING_SECONDS (30), RING_GROUP_QUEUE_SECONDS (180)
- MONITOR_RECORDING_DAYS (14)

## Fix (2026-10-28, later): shared number sent calls to voicemail
- The ring group uses a new participant status 'waiting'. An old database CHECK
  constraint rejected it, so shared-number calls crashed and fell to voicemail.
- Migration 14 now replaces that constraint automatically (and drops any status
  CHECK on incoming_call_groups). No data is changed. Just redeploy this build.
