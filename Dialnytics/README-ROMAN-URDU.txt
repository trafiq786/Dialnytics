==========================================================
  CRM IMPORT — "Customer Name" format support
==========================================================

NAYA
----
Is format ki sheet ab seedha upload hogi:
   Phone number | state | Customer Name | zip code

- "Customer Name" (ya Customer / Client Name) -> lead ka NAAM.
- "Phone number" -> number (US 10-digit -> +1 auto).
- state + zip code -> lead ke NOTES mein (zaaya nahi hota).

(Pehle "Customer Name" map nahi hota tha -> naam khaali -> rows skip.)

BADLI FILE
----------
  backend/main.py   (name keys + known headers + zipcode)

DEPLOY -> CRM page Ctrl+F5 -> sheet upload karo.
NOTE: jo sample bheja usme sirf header tha (data nahi). Apni asli data
wali file isi format mein upload karo.
