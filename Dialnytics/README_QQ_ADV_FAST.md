# Update QQ: Advanced calling tez (ring jaldi + "hello" ke baad awaz jaldi)

## Kya badla
1. **Ring jaldi shuru:** Customer ka number ab database mein likhne SE PEHLE milaya jata hai.
   Pehle: webhook → database → number milao. Ab: webhook → number milao → database.
2. **"Hello" ke baad awaz jaldi:** Customer uthaye tou server dono lines foran jod deta hai, aur database baad mein update hota hai.
   Pehle: database update → answer → database → jodo.
3. Hifazat ke intezamaat:
   - Agent dialing ke dauran hi call kaat de tou customer ka phone foran band hota hai.
   - Telnyx ek hi webhook dobara bheje tou call do dafa nahi lagti.
   - Dono lines do dafa nahi judtin.
   - Ek pal ki der ho jaye tou dono lines ko jodna chhoot nahi jata.

## Andazan waqt (Advanced calling)

| Hissa | Pehle (Oregon, purana code) | PP ke baad | QQ ke baad | QQ + Frankfurt |
|---|---|---|---|---|
| Call dabane se ring shuru hone tak | 1–3 sec (rush mein 10+ sec) | 0.6–1 sec | 0.4–0.7 sec | 0.3–0.5 sec |
| Customer "hello" bole, agent tak awaz pohnche | 1–1.5 sec | 0.8–1.2 sec | 0.3–0.6 sec | 0.3–0.5 sec |

Muqable ke liye: baghair Advanced calling ke ring 0.2–0.4 sec mein shuru hoti hai, aur "hello" ke baad koi gap nahi hota.

Ye andaze hain. Asal waqt Render Logs mein dekhein:
- `customer dialled ... ms after the webhook arrived`: ring se pehle server pe kitni der lagi.
- `connected ... ms after the customer answered`: "hello" ke baad jodne mein kitni der lagi.

## File
- backend/call_transfer.py (pichhli saari tabdeeliyan bhi shamil hain)
