# Update KK: Live listening (Advanced calling se alag)

## Kya badla
- Users > Edit mein naya option **Live listening**.
  - On ho tou admin us user ki outgoing calls sun sakta hai, whisper kar sakta hai aur join kar sakta hai.
  - Agent ko outgoing transfer NAHI milta. Transfer sirf Advanced calling se milta hai.
- **Advanced calling** pehle ki tarah chalta hai: outgoing transfer aur listening dono.
- Incoming calls pehle bhi sun sakte thay, aur ab bhi sun sakte hain.
- Partner users ke liye "3-way / Leave call" add-on lene pe outgoing calls ab sahi tarah server se guzarti hain. Pehle ye add-on outgoing calls pe kaam nahi karta tha.
- Kisi user ka Telnyx account badlein tou ab Advanced calling aur Live listening band nahi hote.

## Files
- backend/main.py
- backend/partners.py
- backend/call_transfer.py
- backend/live_listen.py
- frontend/templates/users.html
- frontend/templates/dialer_rail.html
- frontend/templates/base.html
- frontend/static/js/dialer.js
- SUPABASE_MIGRATION_32_LIVE_LISTEN.sql (optional, app column khud bana leti hai)

## Deploy ke baad
1. Users > Edit user > **Live listening** tick > Save.
2. Agent ek dafa dialer refresh kare. Us ka calling login naye connection pe chala jata hai.
3. Agent call kare, phir Companies > company > agent card pe click karein > **Listen**.

## Yaad rakhein
- Har outgoing minute pe takreeban $0.002 extra lagta hai.
- Sirf Telnyx lines ke liye hai.
- Admin ki apni login pe bhi Telnyx calling line honi chahiye aur dialer khula hona chahiye, kyun ke sunne wali call admin ke dialer pe aati hai.
