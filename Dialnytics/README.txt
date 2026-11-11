Update DD - White-label Partner: Hissa 1 (wallet + billing)

Nayi files:
  Dialnytics/backend/partners.py
  Dialnytics/frontend/templates/partner_wallet.html
  Dialnytics/frontend/templates/partner_payments.html
  Dialnytics/SUPABASE_MIGRATION_31_PARTNERS.sql   (optional, app khud tables bana leti ha)
Replace:
  Dialnytics/backend/main.py
  Dialnytics/frontend/templates/reseller_detail.html
  Dialnytics/frontend/templates/base.html
  Dialnytics/frontend/templates/dialer_rail.html
  Dialnytics/frontend/static/css/responsive.css
  Dialnytics/frontend/static/js/dialer.js
(Y, AA, BB, CC ke baad lagayein - ye un sab ke upar bani ha.)

Kaise chalayein:
1. Admin > Resellers > reseller kholein > "Make partner".
2. Wahan prices (default aap ke rates), credit limit aur apni bank details save karein.
3. Partner login kare: menu mein "Wallet". Bank transfer kar ke amount + reference + screenshot bheje.
4. Aap: menu "Partner payments" (waiting count dikhta ha) > amount check kar ke Confirm.
Billing: naya user/add-on = mahine ke baqi din ka; har 1 tareekh ko poora mahina khud kat-ta ha.
US/Canada discount har company ke users pe (1=$22, 2=$20, 3+=$18).
Balance + credit khatam: purane users chalte rahein, naye users/add-ons nahi.
Partner users: US plan sirf USA call, Canada plan sirf Canada, US+CAN dono, UK sirf UK.
3-way/Leave add-on na ho tou "Add Call" band.
Hissa 2 (partner khud user + number banaye) is ke baad.
