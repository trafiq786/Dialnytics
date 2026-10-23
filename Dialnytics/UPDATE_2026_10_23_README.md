# Dialnytics Dialer — Update 23 Oct 2026

## Is update mein kya naya hai

1. **Logo** — official Dialnytics logo header, login/signup page aur favicon par (dark theme mein white "Dial").
2. **Voicemails** — call miss ho, decline ho ya Do Not Disturb on ho to caller message chhor sakta hai (Telnyx aur Twilio dono). Har user ko sirf apne voicemails dikhte hain. Unread/Today count, delete, call back.
3. **Call Logs** — kisi bhi call par click karein to details panel khulta hai: number, contact name, direction, status, date/time, duration, recording/voicemail player, Call back, Save contact, Copy number, Delete log.
4. **Contacts** — delete button aur search. Same number dobara save karne par naya contact nahi banta, naam update hota hai.
5. **Recordings** — Supabase mein save hoti hain (redeploy par ghayab nahi hongi). `/media` khatam: recording sirf login wale owner ko hi chalti hai. Ab dono taraf ki awaaz record hoti hai (pehle sirf saamne wale ki). Download aur delete bhi.
6. **Twilio backup provider** — user create karte waqt Provider (Telnyx/Twilio) select karein; Caller ID list usi provider ke numbers dikhati hai. Customer page se provider/number badla ja sakta hai.
7. **Estimated cost** — Customer page par provider ke hisaab se Today/Week/Month cost (incoming/outgoing minutes alag). Dashboard (admin) par sab customers ka total cost box. Rates Settings mein edit hote hain.
8. **Security** — purana "Simulation mode" `/api/call` hata diya, security headers (CSP, X-Frame-Options waghera) aur CSRF protection har form/fetch par.

## Deploy steps (ek ek kar ke)

1. GitHub par is ZIP ki files upload karein (ek commit). Render Root Directory `Dialnytics` hi rahe.
2. Render → Environment mein yeh add karein:
   - `PUBLIC_BASE_URL` = `https://dialnytics.co.uk`
   - Twilio ke liye (sirf jab Twilio use karna ho): `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`
     (API key aur TwiML App pehli dafa khud ban jate hain. Chahein to `TWILIO_API_KEY_SID`, `TWILIO_API_KEY_SECRET`, `TWILIO_TWIML_APP_SID` khud bhi de sakte hain.)
   - Optional (behtar storage): `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` — recordings private Storage bucket mein jayengi. In ke baghair recordings Supabase database mein save hoti hain.
3. Database: app start hote hi naye tables/columns khud bana leti hai. Agar Render logs mein "Automatic schema update failed" aaye to `SUPABASE_MIGRATION_07_PROVIDERS_RECORDINGS.sql` Supabase SQL Editor mein run karein (dobara run karna safe hai).
4. Manual Deploy karein.
5. Sab users ek dafa logout/login karein.

## Apna logo lagana

Official logo lag chuka hai. Badalna ho to `frontend/static/img/` mein yeh files replace karein:
- `dialnytics-logo.png` (light theme) aur `dialnytics-logo-dark.png` (dark theme, white "Dial")
- `dialnytics-favlogo.png` (sirf icon, favicon ke liye)



## Emergency switch

Agar deploy ke baad koi page ya dialer CSP ki wajah se na chale: Render mein `CSP_REPORT_ONLY=1` set karke redeploy karein, aur browser console ka screenshot bhejein.

## Abhi ki limitations

- Telnyx, Twilio aur Supabase ke live accounts par test nahi hua — Render par deploy ke baad ek test call, ek voicemail aur ek recording zaroor check karein.
- Twilio line par Hold, Transfer aur Add Call abhi nahi hain (Telnyx par pehle jaise chalte hain).
- Cost estimate har provider ke ek rate par hai (country ke hisaab se alag rate nahi). Har call poore minute mein round up hoti hai.
- Purani recordings jo disk par thi, woh pehle hi redeploy par mit chuki hain; wapas nahi aa sakti.
- CSP mein inline scripts abhi allowed hain (purane templates ki wajah se).

## Bina reload ke navigation (in-app navigation)

- Sidebar, Today/This Week/This Month aur andar ke page links ab sirf beech ka content badalte hain. Dialer rail, Telnyx/Twilio connection aur chalti call nahi rukti.
- Browser ke Back/Forward button kaam karte hain, aur address bar ka URL bhi badalta hai.
- Contacts, Call Logs, CRM aur Voicemails ke "Call" buttons ab rail se seedha call milate hain, page nahi badalta. Agar pehle se call chal rahi ho to doosri call nahi milti.
- Har page ke scripts (CRM, Power Dialer, Contacts, Scripts, Users, Invoice) naye content par dobara chalte hain. Purane page ke listeners aur Power Dialer ka timer page chhorte hi band ho jate hain.
- Fetch fail ho, login expire ho, ya PDF/download link ho to normal page load hota hai.
- Files: `frontend/static/js/page-nav.js` (naya), `base.html`, `invoice_form.html`, `power-dialer.js`, `style.css`.
- Limitation: Save, Create User, Record Payment jaise forms submit karne par ab bhi poora page reload hota hai.

## Speed fix (pages 3-4 second mein khul rahe the)

- Wajah: har page par Supabase se 4-8 naye connections bante the (har ek ~300-500ms). Ab connections dobara istemal hote hain (connection pool, `backend/voice_helpers.py`). Kharab/purana connection khud badal jata hai.
- Link par mouse aate hi page pehle se load hona shuru ho jata hai, click par menu foran highlight hota hai aur upar patli loading line dikhti hai.
- Optional: Render mein `DB_POOL_SIZE` (default 8) se khule connections ki tadaad badal sakte hain.

## Mobile / tablet layout

- 1100px se chhoti screen (phone, tablet) par sidebar ki jagah neeche tab bar: Home, Calls, Dial (beech mein), Contacts, More.
- Dial button se dialer neeche se poori screen par khulta hai; call ke dauran chhupa kar doosre pages dekh sakte hain ("On call" hara button). Incoming call par dialer khud khulta hai.
- Phone ka custom system font ab buttons/inputs par nahi lagta (keypad ke number saaf).
- Chhoti screen (iPhone SE), tircha phone (keypad side mein), tablet, notch/home-bar wale phones (safe area) sab ke liye adjust hota hai. Computer par layout pehle jaisa.
- Files: `static/js/mobile-nav.js` (naya), `base.html`, `dialer_rail.html`, `login.html`, `page-nav.js`, `style.css`.

## White-label: customers ko provider ka naam nahi dikhta

- Messages page, Power Dialer aur dialer ke error messages se "Telnyx/Twilio" hata diya.
- Calling token ke errors customers ko sirf "Calling line is temporarily unavailable. Please contact support." dikhate hain; asal detail Render logs mein jati hai. Admin ko poori detail milti hai.
- Admin pages (Settings rates, cost box, Users/Customers) mein provider ke naam pehle jaise hain.

## Dialer: premium number box, Calling Preferences, Take the Tour
- Number box: gradient border, bara saaf font, country code ka nishan (GB, US, PK...), andar Paste aur × (clear) button.
- Dialer ki lambai content jitni (neeche khali jagah khatam), premium gradient border (computer par).
- Profile menu → Calling Preferences (`/settings/calling`): 6 ringtones (preview ke saath), volume, "Record every call automatically" (sirf recording-upgrade wale accounts).
- Profile menu → Take the Tour: 14 steps, Back / Next / Cancel, phone par bhi.

## Management system: Companies, Owner Team dashboard, Resellers
- **Companies** (admin sidebar): har customer ab ek company ka hissa hai. Purana har customer khud apni company ka Owner ban gaya (kuch nahi toota).
- **Users page**: User type (Customer / Reseller), Company (nayi ya mojooda), Role (Owner / Agent). Owner bina number ke ban sakta hai (sirf team dekhta hai); Agent ko number chahiye.
- **Owner ka Team page** (`/team`): har member ka live status (Online / On call + number + timer / Ringing / Offline), aaj ki calls, answered, talk time, last call; har 5 second update. Member kholne par uski call logs aur recordings.
- **Resellers** (admin sidebar): reseller ki companies assign/remove. Reseller login karke sirf "My Clients" dekhta hai: companies, users, online, calls (view only). Telnyx/Twilio ka naam, cost, recordings ya call details nahi.
- Database: app start par khud update hota hai (`SUPABASE_MIGRATION_08_COMPANIES_RESELLERS.sql` manual backup ke liye).
