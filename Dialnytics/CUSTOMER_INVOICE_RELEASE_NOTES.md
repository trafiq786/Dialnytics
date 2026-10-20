# Dialnytics Customer + Invoice Integration (code build)

## Included
- Premium Customers table, customer drawer, full customer detail editor, subscription status, monthly call metrics, payment history, account disable and password reset.
- Invoice creation with multiple line items, quantity, discount, tax, due date, notes, terms; draft/sent/paid/void, duplicate, delete (draft/void only), PDF download. Payment instruction: Contact us for payment.
- Database migration 04 with additive customer fields and invoice tables; invoice numbering sequence.
- Dashboard totals now query public.calls rather than in-memory call_logs; contact count from PostgreSQL.
- Preserved Telnyx routes, existing user creation, demo, recordings, scripts, and frontend dialer logic from prior build; newest supplied dialer.js included.

## Before deployment
1. Back up Supabase database.
2. Run SUPABASE_MIGRATION_04_CUSTOMERS_INVOICES.sql in Supabase SQL Editor.
3. Upload project files to GitHub and deploy Render with reportlab dependency.
4. Verify routes /customers, /invoices, PDF download, customer changes, payment entry, and existing calling.

## Known limitations / important
- This code was syntax/template-checked locally, NOT tested against live Supabase/Telnyx.
- Invoices are immutable after creation (edit invoice is not yet implemented). Duplicate and create a corrected invoice instead.
- Invoice Mark as Paid updates invoice status only, not the payments ledger, to avoid double-counting; use Record Payment for actual receipts.
- Payment method/reference are accepted in form but the existing payments schema has no fields to persist them; do not treat those values as stored.
- The current Users screen remains available for creation, number assignment, and recording entitlement. Customer management is a separate admin page.
- Existing application has no CSRF protection on admin forms; implement before wider production rollout.
- Existing session, Telnyx, recordings, and hosting limitations remain unchanged.
- New customer editing does not change login email or Caller ID; use existing Users number assignment flow.
