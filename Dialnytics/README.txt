Update AA - Twilio number: outgoing Telnyx se, incoming Twilio se

Replace / add:
  Dialnytics/backend/main.py
  Dialnytics/backend/ring_group.py
  Dialnytics/frontend/static/js/dialer.js
  Dialnytics/frontend/templates/dialer_rail.html
  Dialnytics/frontend/templates/base.html
  Dialnytics/frontend/templates/users.html
  Dialnytics/frontend/templates/customer_detail.html
  Dialnytics/SUPABASE_MIGRATION_30_TWILIO_IN.sql  (optional - app khud column bana leti ha)
Is mein update Z (verified numbers list) aur X (companies delete) b shamil hain.
Y (responsive) pehle laga ho tou behtar - base.html mein sab files ka version ha.

Kaise use karein:
1. Twilio number ko Telnyx > Verified Numbers mein verify karein (jis Telnyx account se calls karni hain).
2. Admin > user > Change number: line = Telnyx 1/2, number = "+44... (verified · outgoing only)".
3. Save. Dialnytics khud:
   - outgoing calls Telnyx se karega (client ko Twilio wala number dikhega)
   - Twilio number ka webhook set karega, incoming calls user ke dialer mein ring hongi
4. Jo users is update se PEHLE assign kiye the, unka number aik dafa dobara save kar dein.
Telnyx account badla: naye account pe number verify karein aur user ki line Telnyx 2 kar dein.
