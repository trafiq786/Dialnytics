# Update UU: Announcements (popup, banner, bell)

## Admin
- Sidebar → Overview → **Announcements** (naya tab).
- **New announcement:**
  - Title, message, type (Update / New feature / Maintenance / Urgent).
  - Audience: All users, Company owners, My direct customers, Partners and their users, ya ek company.
  - Show as: Popup, Top banner (bell hamesha on).
  - Popup shows: Once per user / Every login until read / Every login until it ends.
  - Show until (date), Link (optional).
  - "Also show to partners' users": partner ke users ko "Dialnytics" ki jagah partner ka apna brand naam dikhta hai.
- **Save draft** ya **Publish**.
- **Sent announcements:**
  - Seen (jaise 12 / 40). Number pe click karein tou naam dikhenge.
  - Edit, End, Repost (sab ko dobara popup), Delete.

## Users
- Upar 🔔 bell, na parhi announcements ki ginti ke saath.
- Page ke upar banner. ✕ se band hota hai; Urgent wala band nahi hota jab tak admin End na kare.
- Popup: "Got it" ya "Remind me later" (1 ghante baad dobara).
- **Call ke dauran popup nahi aata.** Call khatam hone ke baad aata hai.

## Files
- backend/announcements.py (naya)
- backend/main.py (register + pichhli saari tabdeeliyan)
- frontend/templates/announcements.html (naya)
- frontend/templates/base.html
- frontend/static/css/announcements.css (naya)
- frontend/static/js/announcements.js (naya)
- frontend/static/js/dialer.js
- SUPABASE_MIGRATION_33_ANNOUNCEMENTS.sql (optional, app tables khud bana leti hai)
