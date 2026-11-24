==========================================================
  POWER DIALER — SKIP DISPOSITION (FULLY AUTO)
==========================================================

KYA BANA
--------
Power Dialer mein naya option: "Skip disposition — fully automatic".
ON karo to:
  - Mode khud "Auto" ho jata hai.
  - Jaise hi ek call KHATAM ho, set delay (3-30s) ke baad AGLA lead
    KHUD dial ho jata hai. Koi outcome/disposition button click NAHI
    karna padta. Bas 1-by-1 auto calls chalti rahengi.
  - Call khatam karne ke liye dialer par HANG-UP dabao (ya saamne wala
    rakh de) -> phir timer chal kar agla number dial karega.

KAISE CHALAO
------------
1) /power-dialer kholo.
2) Mode = Auto, "Delay between calls" set karo (jaise 8 sec).
3) "Skip disposition — fully automatic" wala box TICK karo.
4) Create Queue -> leads select -> Start.
5) Ab bas baat karo aur hang-up dabate jao -> agla number khud lagta
   rahega. Pause/Stop se rok sakte ho.

NOTE
----
- Ye sirf Auto mode mein chalta hai (box tick karte hi mode auto ho jata).
- Har auto call "dialed" result ke saath history mein save hoti hai
  (lead ka CRM status nahi badalta). Baad mein chaho to manually
  disposition set kar sakte ho.
- Delay = ek call khatam hone aur agla shuru hone ke BEECH ka gap.
  (Calls stack nahi hoti — pehle call khatam, phir delay, phir agli.)

BADLI FILES
-----------
  backend/main.py                        (skip_disposition column + create + 'dialed' result)
  frontend/templates/power_dialer.html   (checkbox)
  frontend/static/js/power-dialer.js     (auto-advance on call end)

DATABASE: koi manual SQL nahi — power_queues.skip_disposition column
khud ban jata hai (agar table maujood ho).

Deploy ke baad power dialer page ek dafa HARD-REFRESH (Ctrl+F5) —
JS ?v=5 ho gaya hai.
