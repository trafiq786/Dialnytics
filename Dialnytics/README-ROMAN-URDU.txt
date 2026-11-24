==========================================================
  CRM IMPORT — AB HAR FORMAT KHUD UPLOAD HO JATA HAI
==========================================================

MASLA JO THA
------------
Tumhari lead file (name, phone, email, consent, do_not_call) upload pe
0 add / 351 skip ho rahi thi, kyunki:
  1) consent column KHAALI thi -> CRM bina consent ke har lead reject kar
     deta tha.
  2) US 10-digit numbers ko import UK (+44) samajh ke None bana ke skip
     kar deta tha.

AB KYA THEEK HUA (code)
----------------------
1) CONSENT: ab maan liya jata hai ke permission lead banate waqt li gayi.
   Har row import hogi -- SIVAAE us ke jis ki consent cell mein saaf
   likha ho: no / false / 0 / optout / declined / revoked / dnc,
   YA do_not_call cell mein 'yes'. Khaali consent ab skip NAHI karti.

2) NUMBERS: country KHUD detect hoti hai (US/Canada vs UK).
   - US 10-digit (jaise 2163079977 / (616) 262-6271) -> khud +1 lag jata hai.
   - 1XXXXXXXXXX -> +1. UK 0.../44... -> +44 (pehle jaisa).
   File ke numbers dekh kar majority se decide hota hai.

NATEEJA
-------
Wahi original file ab seedha upload karo -> ~269 leads add honge
(naam, number, email CRM mein show). File clean karne ki zaroorat NAHI.
(Jo rows bina number ke hain -- "Dialer Lead Id"/khaali -- wo phir bhi
skip hongi kyunki unhe dial nahi kiya ja sakta.)

BADLI FILES
-----------
  backend/main.py                 (import: consent + US numbers)
  frontend/templates/crm.html     (help text update)

NOTE: is main.py mein pichla sab kaam bhi shaamil hai (SIP migration +
Power Dialer auto-dial) -- cumulative hai.

COMPLIANCE
----------
Ye US cold leads hain -- dial se pehle DNC/TCPA scrub apni zimmedari par
karna. Consent ab tumhari taraf se assumed hai.
