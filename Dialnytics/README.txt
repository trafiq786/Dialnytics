Update GG - Reseller disable/delete + users list + partner colour scheme
Replace:
  Dialnytics/backend/partners.py
  Dialnytics/backend/main.py
  Dialnytics/frontend/templates/reseller_detail.html, resellers.html, partner_brand.html, base.html, login.html
  Dialnytics/frontend/static/css/responsive.css
  Dialnytics/SUPABASE_MIGRATION_31_PARTNERS.sql (optional)
(FF ke baad. Database: partners table mein "theme" column app khud bana leti ha.)

Admin > Resellers > reseller kholein:
  - Upar "Disable reseller" (option: unke users b band) / "Enable reseller"
  - "Users of this reseller": har user, company, number, plan, add-ons, renew date, status
  - Neeche "Delete reseller": email likh ke delete. Companies aap ki direct customers ban jati hain
    (ya option se unke users b band).
Resellers list mein status: White-label / Reseller / Disabled.
Partner > Brand > "Dialer colour scheme": Classic, Ocean, Emerald, Sunset, Rose, Violet, Graphite,
  ya "My brand colour". Partner aur us ke saare clients ko yahi rang dikhte hain (login page b).
