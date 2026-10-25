# Second Telnyx account (Telnyx 2)

Each user calls through the Telnyx account that owns their number. When an admin
assigns a number, the dialer finds which account owns it and moves the user
there automatically (a new calling login is made on that account).

Render environment variables for account 2 (account 1 keeps the old TELNYX_* ones):

| Variable | Where in Telnyx |
|---|---|
| TELNYX2_API_KEY | Account Settings → Keys & Credentials → API Keys |
| TELNYX2_PUBLIC_KEY | Account Settings → Keys & Credentials → Public Key |
| TELNYX2_CONNECTION_ID | Voice → SIP Connections → (Credentials type) → ID |
| TELNYX2_VOICE_APP_ID | Voice → Voice API Applications → ID (webhook: https://dialnytics.co.uk/webhooks/telnyx) |
| TELNYX2_SMS_PROFILE_ID | optional, Messaging → profile ID (webhook: https://dialnytics.co.uk/webhooks/telnyx/sms) |
| TELNYX2_ADV_CONNECTION_ID | optional, Advanced calling connection |

Notes
- Transfers work only between agents on the same Telnyx account.
- Without TELNYX2_API_KEY everything works exactly as before.
