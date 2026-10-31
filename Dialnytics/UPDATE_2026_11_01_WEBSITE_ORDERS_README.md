# Website orders (2026-11-01)

New file: `backend/website_orders.py`. Changed: `backend/main.py`, `frontend/templates/{base,users,customer_detail,dashboard}.html`.
New templates: `pending_orders.html`, `feature_locked.html`.

## Environment (Render)
- `MARKETING_API_KEY` - shared secret, identical to `DIALER_API_KEY` on the marketing site.
- `MARKETING_URL` - `https://dialnytics-web.onrender.com`.
- `SUPPORT_WHATSAPP` - optional.
The database changes run automatically on start (idempotent). No manual SQL needed.

## What it adds
- `/webhooks/marketing/*` secured endpoints (numbers, hold, create order, paid, renew, cancel, status).
- **Pending Orders** page (`/users/pending`): bank/crypto orders, time left, **Mark as paid** (USD amount, method, reference) and cancel. Also lists website accounts that have no number.
- Users created from the website show **Self-signup (website order)** in User Accounts.
- Number holds: held numbers are hidden from the Create User list and refused by Create User.
- Expiry sweeper (every 45 s): pending users, the order and the hold are deleted when the timer ends.
- Add-on flags: Recording -> `recording_premium`, SMS -> `sms_enabled`, Campaigns & Power Dialer -> new `power_enabled`.
  `power_enabled` now gates Power Dialer, Campaigns, **CRM** and Follow-ups (pages, APIs and sidebar links). Existing users keep access (column default TRUE); website users get it only with the add-on. Admin switch: Users -> Edit -> Calling tab -> "Power Dialer, CRM, Campaigns & Follow-ups" (`POST /users/power`). SMS pages still need a Telnyx number until Twilio SMS code is added (`has_sms`).
- Payments: new **USD** box (create user, record payment, dashboard repayment) and `amount_usd`, `method`, `reference` columns; USD shows in Payment History.
  Optional setting `usd_pkr_rate` (dialnytics_settings) converts website payments into the PKR revenue totals; without it PKR is 0 for those rows.
