==========================================================
  CALL "RECONNECTING" / VOICEMAIL FIX — STUN add
==========================================================

MASLA (screenshot se)
---------------------
Call Active hoti hai phir "Reconnecting..." -> media/ICE toot jaata hai ->
call voicemail par chali jaati. Sab calls par.

WAJAH
-----
Dialer bina STUN/TURN (iceServers khaali) chal raha tha. NAT ke peeche
WebRTC media connect ke baad survive nahi kar pata -> ICE disconnect ->
"Reconnecting" -> drop.

AB
--
Call ke liye STUN servers add kiye (Google STUN). ICE ab srflx candidates
gather karta hai aur media alive rehti hai.

TEST (ek user par)
------------------
Deploy -> dialer HARD-REFRESH (Ctrl+F5) -> call karo -> ab Active rehni
chahiye, Reconnecting/voicemail nahi.

AGAR PHIR BHI RECONNECTING
--------------------------
To media ConnexCS side se nahi aa rahi (one-way/no RTP). Ye check karo:
 - ConnexCS mein jo codecs/NAT/media settings local presence try karte
   waqt chhue the -> wapas theek karo (G711u/G729, media relay on).
 - TURN server chahiye ho sakta hai (strict NAT par). Agar STUN se na
   chale to batao, ConnexCS ka TURN daal dete hain.

NOTE: local presence (PAI) wala change pehle hi revert ho chuka -- ye zip
us ke upar sirf STUN add karta hai. Calls ka ANI pehle jaisa (assigned).

BADLI FILES
-----------
  frontend/static/js/dialer.js     (STUN iceServers)
  frontend/templates/base.html     (dialer.js ?v=20261126c)
