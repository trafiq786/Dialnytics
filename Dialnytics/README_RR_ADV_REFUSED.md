# Update RR: "Advanced outbound refused (Not allowed)" ka fix

## Masla 1 (code ki ghalti, KK se)
Jin users pe sirf **Live listening** on thi (Advanced calling off), un ke dialer ko call ka "pehchan tag" nahi milta tha.
Server us ki call ko pehchan nahi pata tha, "Not allowed" keh ke kaat deta tha.
Ab Live listening wale users ko bhi tag milta hai.

## Masla 2 (DATABASE_URL badalne ki wajah se, ek dafa ka)
Ye pehchan tag DATABASE_URL se bana ek secret se sign hota hai. Aap ne port 5432 se 6543 kiya, tou secret badal gaya.
Jo dialers pehle se khule thay, un ke paas purana tag hai, aur un ki Advanced calls "Not allowed" ho rahi hain.
**Hal: sab users dialer ka page ek dafa refresh karein.**

Aage aisa na ho, is ke liye Render → Environment mein ek naya variable bana dein:
- Naam: `DN_LEG_SECRET`
- Value: koi bhi lambi random line (40+ akhar), jaise do password generator ki lines jod ke.
Phir DATABASE_URL ya API key badalne se ye tag nahi tootega.
(Ye variable add karne ke baad bhi users ko ek dafa refresh karna hoga.)

## File
- frontend/templates/dialer_rail.html
