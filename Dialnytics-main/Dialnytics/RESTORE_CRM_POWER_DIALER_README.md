# Dialnytics CRM + Power Dialer restoration

This release restores the missing CRM UI and Power Dialer UI using the existing authenticated FastAPI endpoints. Existing Telnyx, customer, invoice and incoming-call code is unchanged.

## Deploy
1. Back up your current GitHub repo and Supabase database.
2. Upload the contents of the `Dialnytics` folder to the same repository folder (do not create a second nested Dialnytics folder).
3. Ensure the CRM/Power Dialer database migration from the original project has already been run. This package does not change database schema.
4. Commit to GitHub and deploy the latest commit on Render.
5. Hard-refresh the browser and visit `/crm` and `/power-dialer`.

## Notes
- CRM CSV requires `name,phone,consent`; `email,do_not_call` optional. Only explicit opted-in leads import.
- Power Dialer rechecks consent and Do Not Call before each call, and pauses if WebRTC is unavailable.
- Automatic mode requires a completed call and manually recorded disposition before proceeding after the configured delay.
- Outbound calling, payment, and inbound routing were not modified. Live Telnyx/Supabase integration must be tested on deployment.
