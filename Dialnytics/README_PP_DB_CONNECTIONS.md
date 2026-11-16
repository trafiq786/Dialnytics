# Update PP: "max clients reached" wala deploy error

## Masla
Supabase ka pooler (port 5432, "session mode") ek waqt mein sirf 15 connections deta hai.
NN ke baad requests alag threads mein chalti hain aur har ek apna database connection kholti thi.
Deploy ke waqt purana aur naya server dono connections khol rahe thay, 15 ki limit poori ho gayi, aur naya server start nahi ho saka.

## Code mein kya badla
- Server ek waqt mein ab zyada se zyada 10 database connections kholta hai.
- Agar 10 busy hon tou nayi request thoda intezar karti hai, error nahi deti.
- Render pe `DB_MAX_CONNECTIONS` variable se ye number badla ja sakta hai.

## Render pe ek setting zaroor badlein (DATABASE_URL)
1. Render → dialnytics → Environment → `DATABASE_URL` ki value kholein.
2. Is mein `pooler.supabase.com:5432` likha hoga. Sirf **5432 ko 6543** kar dein, baqi sab waisa hi rehne dein.
3. Save karein.

6543 "transaction mode" hai: is mein saikron clients ek saath chal sakte hain, aur dialer ka code is ke liye pehle se tayyar hai.

## Files (is mein NN aur OO dono shamil hain)
- backend/main.py
- backend/voice_helpers.py
- backend/call_transfer.py
- backend/partners.py
- frontend/static/js/dialer.js
- frontend/templates/base.html
