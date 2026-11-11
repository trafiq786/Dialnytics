Update EE - White-label Partner: poora (wallet + users/numbers + brand/domain)
(DD ki jagah ye lagayein - is mein DD b shamil ha.)

Files (nayi + replace):
  Dialnytics/backend/partners.py            (nayi)
  Dialnytics/backend/main.py
  Dialnytics/frontend/templates/partner_users.html, partner_user_new.html, partner_user_done.html,
      partner_brand.html, partner_wallet.html, partner_payments.html   (nayi)
  Dialnytics/frontend/templates/base.html, login.html, reseller_detail.html, dialer_rail.html
  Dialnytics/frontend/static/css/responsive.css
  Dialnytics/frontend/static/js/dialer.js
  Dialnytics/SUPABASE_MIGRATION_31_PARTNERS.sql  (optional, app khud tables bana leti ha)

Render Environment (zaroori):
  PARTNER_CNAME_TARGET = aap ki Render service ka address, jaise dialnytics.onrender.com
       (Render > service > Settings > top pe ".onrender.com" wala address)
Optional:
  RENDER_API_KEY + RENDER_SERVICE_ID  -> partner ka domain khud Render mein add/verify ho
       (na ho tou: Admin > Resellers > partner > domain ko Render Custom Domains mein add kar ke "Mark live")
  PARTNER_TELNYX_ACCOUNT = t1   (naye numbers kis Telnyx account se khareedein)

Partner kya karega:
  Users > + New user: naam, email, company, plan (USA / Canada / USA+Canada / UK), add-ons,
      country + area code > numbers list > chunay > Create. Login details copy kar ke client ko de.
      Pehle aap ke khali numbers ("Ready"), kam hon tou Telnyx se naye ("New", US/Canada) khud khareede jate hain.
  Users list: add-ons on/off, user switch off/on.
  Wallet: bank payment report.  Brand: naam, logo, rang, WhatsApp, apna domain.
Billing: user 11 Dec ko bana tou 10 Jan tak poora mahina (add-ons ke saath) kat-ta ha.
  Baad mein add-on lagaya tou sirf us user ke baqi din ka. Har user apni tareekh pe renew hota ha.
Brand: partner ke clients ko login page, logo, tab ka naam, support WhatsApp - sab partner ka.
  Billing page aur "Refer & Earn" un ko nahi dikhte.
