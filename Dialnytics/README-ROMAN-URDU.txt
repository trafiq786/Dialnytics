==========================================================
  DTMF FIX — IVR bots mein number press ab kaam kare (SIP)
==========================================================

MASLA
-----
Jab koi bot/IVR kehta hai "press 1 for sales..." to number dabane par
tone aage nahi jati thi (SIP/EchoDial lines par).

WAJAH
-----
SIP call par DTMF sirf RFC2833 (RTP) se bhej raha tha. ConnexCS WebRTC leg
par agar telephone-event negotiate na ho to tone kahin nahi pohnchti.

AB KYA HUA
----------
In-call keypad ab SIP par DTMF aise bhejta hai:
  1) Pehle RFC2833 (agar RTP sender support kare) — stronger 200ms tone.
  2) Warna SIP INFO (application/dtmf-relay) — carrier-agnostic.
Double digit ka risk nahi (ek hi method chalta hai).

BADLI FILES
-----------
  frontend/static/js/dialer.js     (SIP dtmf: RFC2833 -> SIP INFO fallback)
  frontend/templates/base.html     (dialer.js ?v=20261125 cache-bust)

TEST
----
Deploy -> dialer page HARD-REFRESH (Ctrl+F5) -> kisi IVR/bot number par
EchoDial(SIP) line se call -> keypad khol kar number dabao.

NOTE
----
- Ye fix SIP/EchoDial lines ke liye hai.
- Twilio lines par DTMF alag SDK se jata hai (tw.sendDigits) — agar Twilio
  line par masla hai to batao, usay alag dekhenge.
- Agar SIP par phir bhi na chale: ConnexCS mein Infinity carrier par DTMF
  relay mode (RFC2833) set karna pad sakta hai — wo switch-side setting hai.
