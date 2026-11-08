DIALNYTICS UPDATE O  -  Advanced calling ko tez karna (2026-11-08)
=================================================================
Update N2 ke upar lagao. Sirf 2 files: backend/call_transfer.py, backend/main.py

KYA TEZ HUA
-----------
1. Client uthane ke baad (khamoshi wala hissa):
   Pehle: answer -> Telnyx ke webhook ka intezar -> phir jodna.
   Ab:    answer -> foran jodna. Webhook sirf backup ke taur par.
   Is se ek poora internet chakkar (Telnyx -> Render -> wapas) bach jata hai.
2. Ghanti bajne se pehle:
   User ab server ki memory se pehchana jata hai, database ka ek chakkar kam.

Database khud update hota hai (cc_calls.bridged_at), kuch manually nahi chalana.

TEST
----
Deploy -> dialer Ctrl+F5 -> Advanced user se call.
Render logs mein "Advanced outbound ... connected (fast)" dikhe to naya tez raasta chal raha hai.

AUR TEZI KE LIYE (aap ki taraf se)
---------------------------------
- Render service aur Supabase database ka REGION ek hi ho (dono US East / dono Frankfurt).
  Alag region = har database chakkar par 100-200 ms extra.
- Render plan: Free/Starter instance par CPU kam hota hai; Standard par webhooks tez chalti hain.
- Advanced calling sirf un users ke liye ON rakho jinhe Leave call / Transfer chahiye.
  Baqi users seedhi calling par sab se tez rehte hain.
