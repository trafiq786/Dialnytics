===========================================================
  ROUTING  —  1-click provider switch  +  hybrid calling
===========================================================

KYA BANA
--------
Admin sidebar mein naya page: Calling -> "Routing" (🔀).

1) SWITCH PROVIDER (1 click failover)
   Sab active EchoDial users ko ek SIP provider se doosre par ek click mein
   move karo. Har user apna number (CLI) aur hybrid inbound barqarar rakhta
   hai. Telnyx/Twilio users ko haath nahi lagta.
   >> Jab kisi provider ka issue aaye: From = kharab provider, To = theek
      provider, "Switch all users". Users agli call par naye provider se
      register ho jate hain.

2) HYBRID CALLING (out = SIP, in = Twilio DID)
   Ye core pehle se app mein tha (jab EchoDial user ka number Twilio number
   ho to outbound SIP se jati hai CLI = wahi Twilio number, aur inbound
   Twilio par aati hai). Ab uska saaf control + status mil gaya:
   - Har EchoDial user ke saamne "Inbound: Twilio (hybrid)" ya "SIP only".
   - "Re-sync hybrid" button: sab EchoDial users ka twilio_in dobara set
     karta hai aur har Twilio number ka voice webhook is app par point karta
     hai. Naye users/numbers add karne ke baad ya inbound kaam na kare to
     ye dabao.


ZAROORI — main.py aur base.html CUMULATIVE hain
-----------------------------------------------
Is zip ki  backend/main.py  aur  frontend/templates/base.html  mein pehli
wali AUTO-INVOICE (Renewals) changes BHI shamil hain. Yani ye LATEST hain —
inhi ko rakho. Agar tum ne pehle AUTO-INVOICE.zip apply ki thi, to ye naye
main.py/base.html us ke upar aa jayenge (kuch khoega nahi, dono features
andar hain).


NAYE / BADLE FILES
------------------
  backend/main.py                          (BADLA — /routing routes [+ auto-invoice])
  frontend/templates/base.html             (BADLA — nav: Routing [+ Renewals])
  frontend/templates/routing.html          (NAYA — admin page)

Note: is zip mein mailer.py / auto_invoice.py / renewals.html NAHI hain —
wo AUTO-INVOICE.zip mein hain. Agar wo abhi tak apply nahi ki, to pehle wo
3 files bhi daal do (warna app import error de ga, kyunke main.py unhe
import karti hai).


DATABASE
--------
Koi nayi table nahi. Sab existing columns (sip_provider_id, twilio_in,
provider) use hoti hain.


ISTEMAAL
--------
1) Deploy karo (Render push).
2) Sidebar -> Calling -> "Routing" (🔀) kholo.
3) Upar 3 stat: total EchoDial users, kitne hybrid, kitne providers.
4) SWITCH: From/To chuno -> "Switch all users". Confirm. Count dikhega.
   (Target provider pehle SIP Providers mein ACTIVE hona chahiye — warna
    CSP us ka WSS block kar deta hai aur calling nahi chalti; page tumhe
    rok dega aur bata dega.)
5) HYBRID: Twilio configured ho to "Re-sync hybrid" dabao — sab ka inbound
   Twilio par set ho jayega.


TEST (test-on-one-first)
------------------------
- Pehle ek SIP provider aur daal lo (SIP Providers page) ya env EchoDial ko
  target rakho.
- Switch karne se pehle 1 test user ko dekho (wo ab bhi call kar pa raha ho).
- Switch ke baad us test user se ek call karke confirm karo.
- Hybrid: ek test user jiska number Twilio ka ho, us par ek baahar se call
  karo -> uske dialer par ring aani chahiye (inbound Twilio).


ROLLBACK
--------
Routing sirf UI/action hai — koi schema/background change nahi. Hatana ho to
purani main.py + base.html wapas daal do, routing.html ignore ho jayega.
Jo switch pehle ho chuka wo users ke sip_provider_id mein mehfooz rehta hai.

Sawal ho to batao.
