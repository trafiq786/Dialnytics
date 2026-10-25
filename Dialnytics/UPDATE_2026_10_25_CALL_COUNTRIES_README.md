# Calling countries per user (2026-10-25)

- A UK number (+44) can call only the UK; a US number (+1) only US/Canada.
- Admin can allow more: Users → Edit → Calling tab → "Countries this user can call" → tick US / Canada and/or United Kingdom → Save countries.
- Nothing ticked = only the country of the user's own number. Admin accounts have no limit.
- Checked in the dialer, call log, Twilio outgoing calls, Power Dialer, advanced calling and transfers to outside numbers.
- Database: column `dialnytics_users.call_countries` is added automatically on start (migration 12).
- This update also contains the Telnyx 2 changes (main.py, call_transfer.py, users.html).
- Telnyx Outbound Voice Profile must still allow every country you sell (UK, US, Canada).
- Emergency and short numbers (999, 112, 911, 933, N11 and anything too short) are always blocked, also for admin, in the dialer, call log, Twilio, Power Dialer, advanced calling and transfers.
