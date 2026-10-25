# Update 2026-10-25: Call transfer, Add Call and Conference

## What is new

1. **Transfer to a teammate.** Use the Transfer button during a call. It lists the agents of the same company with live status: Available, On a call, or Offline.
   - **Available teammate.** Their dialer rings and shows "Transferred call · from <name>". The caller hears hold music.
   - **Teammate on another call.** The transfer waits. The caller hears hold music, and the call rings the teammate as soon as their call ends. The wait is at most 3 minutes (`TRANSFER_WAIT_SECONDS`, default 180).
   - **No answer, Decline, or 3 minutes up.** The caller comes back to the first agent automatically. The customer is never dropped.
   - **Transfer to a phone number** is also possible from the same screen.
2. **Add Call.** You can have up to 4 calls at once. The other calls stay on hold, and you can Swap between them or end each one from the Call List.
3. **Merge (conference).** Everyone on the call list hears everyone. If one person leaves, the others stay connected. The red button ends the whole conference.
4. **Advanced calling** is an optional per-user admin toggle. It is only needed to transfer OUTGOING calls, and it needs the Telnyx setup below.

Incoming calls can be transferred for every Telnyx user without any Telnyx change. Add Call and Conference also work for every Telnyx user.

## Files

| GitHub path | Status |
|---|---|
| `Dialnytics/backend/call_transfer.py` | NEW |
| `Dialnytics/backend/main.py` | changed |
| `Dialnytics/frontend/static/js/dialer.js` | changed |
| `Dialnytics/frontend/templates/dialer_rail.html` | changed |
| `Dialnytics/frontend/templates/users.html` | changed (Advanced calling toggle) |
| `Dialnytics/frontend/static/audio/hold-music.mp3` | NEW (hold music) |
| `Dialnytics/SUPABASE_MIGRATION_10_TRANSFER.sql` | NEW (runs automatically on start) |

The new tables are `live_legs`, `call_transfers` and `cc_calls`, plus the column `dialnytics_users.adv_calling`. They are created automatically when the app starts.

## Telnyx setup for Advanced calling (outgoing transfers only)

1. In Telnyx, go to Voice → SIP Connections → Add SIP Connection and choose the **Credentials** type. Name it `Dialnytics Advanced`.
2. On the new connection, set these options:
   - **Webhook URL:** `https://dialnytics.co.uk/webhooks/telnyx`
   - **Park outbound calls:** ON
   - **Outbound Voice Profile:** the same one the current Dialnytics connection uses
3. Copy the connection ID.
4. In Render, add the environment variable `TELNYX_ADV_CONNECTION_ID=<id>`.
5. In Users → Edit → Calling, press **Toggle Advanced** for one user. That user must refresh the dialer.

To roll back, toggle the user off. They go back to the normal connection.

## Optional environment variables

| Variable | Default | What it does |
|---|---|---|
| `TRANSFER_WAIT_SECONDS` | 180 | How long a transfer waits for a busy agent |
| `TRANSFER_RING_SECONDS` | 30 | How long the teammate's dialer rings |
| `HOLD_MUSIC_URL` | `/static/audio/hold-music.mp3` | Your own hold music |
| `TRANSFER_WORKER` | on | Set it to `0` to turn off the queue worker (debug only) |
