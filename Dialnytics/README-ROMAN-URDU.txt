==========================================================
  AUDIO FIX — G711 prefer (one-way / no awaz)
==========================================================

MAINE PURA CODE CHECK KIYA
--------------------------
Media path (remote audio attach + play) SAHI hai:
 - Remote audio do jagah attach hota hai: 'track' event aur 'accepted'.
 - <audio id=remoteAudio autoplay playsinline> maujood hai.
 - echoRemoteStream receivers se audio track theek uthata hai.
Yani "kabhi awaz, kabhi nahi" ek DETERMINISTIC code bug nahi -- warna
hamesha no-audio hota. Ye media-plane (ConnexCS/Infinity) ka masla hai.

JO EK CHEEZ CODE-SIDE THEEK KI
------------------------------
Browser pehle OPUS codec offer karta tha -> ConnexCS ko Opus<->G711
transcode karna padta tha -> yahi aksar ONE-WAY / NO AUDIO deta hai.
Ab browser SDP mein G711 (PCMU/PCMA) pehle offer karega (koi codec hataya
nahi, sirf order badla). Infinity/ConnexCS G711 natively carry karte hain
-> transcoding nahi -> audio reliable.

+ pichla STUN fix bhi isme hai (ICE stability).

TEST (ek user par)
------------------
Deploy -> dialer HARD-REFRESH (Ctrl+F5) -> 2-3 calls karo.
Awaz dono taraf aani chahiye, Reconnecting nahi.

AGAR PHIR BHI (no audio / 5s PDD / voicemail)
---------------------------------------------
Ab ye pakka ConnexCS/Infinity media-side hai. Ye check/karao:
 1) ConnexCS carrier (Infinity) CODECS: G711u (PCMU) + G729 allow hon,
    aur "transcode/NAT media" ON ho.
 2) 5 sec PDD (active hone mein der) = Infinity route ki post-dial delay
    -- Infinity se poochho, ya doosra route test karo.
 3) One-way audio aksar NAT/media-IP ka masla -- ConnexCS media relay/
    RTP proxy ON karo us customer par.
 4) Strict NAT par TURN chahiye -- bolo to ConnexCS ka TURN daal dun.

BADLI FILES
-----------
  frontend/static/js/dialer.js     (preferG711 SDP + STUN)
  frontend/templates/base.html     (dialer.js ?v=20261126d)

NOTE: Agar G711 ke baad calls kharab hon (na chalein) to batao -- turant
revert kar denge. Sirf codec ORDER badla hai, risk kam hai.
