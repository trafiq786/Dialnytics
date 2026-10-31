# Dialnytics owned-number synchronization — staging patch

## Files
- Marketing website: `Dialnytics-Marketing/app/main.py`, `app/number_sync.py`, `templates/admin_numbers.html`
- Dialer: `Dialnytics/backend/main.py`, `backend/inventory_feed.py`

## Setup, staging only
1. Upload **each extracted patch** to the corresponding GitHub `staging` branch, preserving paths. Do not change `main`.
2. Generate a new random 48+ character shared token. Set `DIALER_INTERNAL_TOKEN` to the **same value** in BOTH staging Render services. Do not send the token to ChatGPT.
3. Marketing staging: set `DIALER_INTERNAL_URL=https://dialnytics-staging.onrender.com`.
4. Dialer staging: number sync needs **staging-only** Telnyx and Twilio test account credentials with purchased test numbers. If not configured, sync fails closed and inventory is not altered. Do NOT copy production API keys or purchased live numbers into staging.
5. Deploy Dialer staging first, then Marketing staging. Check `/admin/numbers` and click `Sync Numbers Now`. A failed sync returns HTTP 503 and leaves inventory intact.
6. The website `/api/numbers/available` refreshes inventory no more often than once per process per 60 seconds, and returns HTTP 503 when the configured dialer feed is unavailable. This avoids selling stale numbers.

## Important limitations
- Telnyx number country must be present in provider metadata (`country_iso_alpha2`, `country_iso`, or `country`); missing country numbers are deliberately excluded rather than guessing US vs Canada.
- The sync reads purchased numbers; it does not buy, configure, or release provider numbers.
- Only numbers not assigned in `dialnytics_users.phone_number`, `dialnytics_users.twilio_number`, or `caller_id_assignments.phone_number` appear. Other provider-level allocations not reflected in the dialer database are not detected.
- The marketing database remains the authority for checkout reservations. This patch does not implement a distributed lock shared with Dialer Admin. **Do not enable real automatic number assignment or live checkout before an atomic cross-service assignment check is implemented and verified.**
- Both providers must be configured or the endpoint fails closed to avoid erroneously retiring numbers from an unconfigured provider.
- Staging provider integration and full checkout tests have not been performed.
