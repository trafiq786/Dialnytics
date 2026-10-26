# Two Twilio accounts (2026-10-26)

Provider choices in admin: Telnyx 1, Telnyx 2, Twilio 1, Twilio 2. Each shows only its own numbers.
The user's account is chosen automatically from the number assigned to them.

- Twilio 1 = existing `TWILIO_*` variables (unchanged, existing Twilio users keep working)
- Twilio 2 = new account, Render variables:
  - `TWILIO2_ACCOUNT_SID` (required)
  - `TWILIO2_AUTH_TOKEN` (required)
  - `TWILIO2_API_KEY_SID`, `TWILIO2_API_KEY_SECRET`, `TWILIO2_TWIML_APP_SID` (optional; created automatically on first use and stored per account)
- Create User page shows the status of every account (connected / not set up / error), no keys shown.
- Database: column `dialnytics_users.twilio_account` (default 'w1') added automatically on start (migration 13). No data is changed or removed.
- Saved Twilio API key / TwiML app are now kept per account SID, so a new account never reuses keys of another account.
