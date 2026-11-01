# Update 2026-11-01 (B)

Dialer
- Dashboard: Lifetime earnings (PKR) + Lifetime earnings in USD box + existing This Month box.
- Provider costs: Today / Last 7 days / Last 30 days / Lifetime (replaces this week / this month).
- Card (USD) payments no longer show PKR 0: converted with Settings > "1 USD = PKR" (default 280); old zero rows are repaired once at startup.
- Users page: "Disabled Users" list (Enable / Delete permanently), and "Delete permanently (all data)" in the Edit drawer. Type the email to confirm. Cannot be undone.
- A disabled user who orders on the website is re-activated in place (history kept, new password from the order). If the order expires, the account goes back to disabled.
- SMS credits: Edit user > Calling > "SMS allowance" in multiples of 100 (blank = unlimited, existing users stay unlimited). 1 credit per message segment; failed sends are refunded. Website "SMS 100 pack" x N gives the owner N*100 credits automatically.
- Customer page: USD paid shown with PKR equivalent, SMS left.
- Invoices: payment method (Bank / Card / USDT / Other). Bank shows the UBL account only; Card shows "Card" name + renewal date. PAID stamp when the invoice is marked paid. PDF now uses the Dialnytics letterhead (customer name in the header, phone +44 7476 629105, address removed).
- New files: frontend/static/img/letterhead.png, frontend/static/fonts/Poppins-*.ttf (needed for the invoice PDF).
- DB: columns are added automatically at startup (sms_credits, signup_reactivate, signup_prev_account, website_orders.sms_packs, invoices.payment_method/card_name/renewal_date).

Marketing
- Add-ons: "SMS 100 pack" $5 with a - / + quantity (one-time, per pack). Price editable in admin pricing.
- Terms, Billing/Refund, Suspension, Call recording pages and FAQ: no refunds, plan cannot be changed, all calls recorded, illegal/scam calls = termination without refund.
