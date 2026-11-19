Dialnytics — Update AH  (AG ka behtar version)
CSP ab har WSS provider ko allow karti hai (bulletproof).

connect-src mein 'wss:' add kiya — iska matlab browser kisi bhi
secure WebSocket (wss://) provider se connect kar sakta hai.
Ab SIP Provider list mein ho ya na ho, DB/cache/deploy-timing
ka koi masla nahi — har WSS provider chalega.

FILES (2, backend):
  backend/voice_helpers.py   <-- CSP yahan hai, ISE deploy karna ZAROORI
  backend/main.py

>>> DEPLOY VERIFICATION <<<
Deploy ke baad sip-test.html ka CSP header dekho (Network tab).
connect-src mein 'self' ke foran baad ab:
     connect-src 'self' wss: wss://*.telnyx.com ...
Agar 'wss:' nazar aaya -> voice_helpers.py deploy ho gayi, block
khatam. Agar 'wss:' NAHI dikha -> voice_helpers.py deploy NAHI hui
(ya server restart nahi hua) -> dobara deploy karo.
