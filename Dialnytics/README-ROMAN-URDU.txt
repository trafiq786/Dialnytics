==========================================================
  REVERT — PAI header hata diya (calls phir connect)
==========================================================

KYA HUA
-------
Pichle fix (P-Asserted-Identity header) se calls ring to ho rahi thi par
connect nahi ho rahi thi -- ConnexCS/Infinity us PAI ko reject/mishandle
kar raha tha. Isliye PAI/PPI header HATA diya.

AB
--
Local presence wapas pehle jaisa: dialer local CLI sirf "From" header mein
bhejta hai. Calls normal connect hongi.

ANI (LOCAL PRESENCE) KA ASLI HAL -- ConnexCS side
--------------------------------------------------
Pool wala local number ANI banane ke liye masla DIALER ka nahi, ConnexCS
ka hai: wo registration username ko ANI bana deta hai. Browser se PAI
force karna calls tod deta hai. Isliye ye ConnexCS par set karna hoga:

  ConnexCS -> us SIP customer/trunk ki CLI/Caller-ID handling ko aisa
  karo ke wo INVITE ke "From" header se CLI le (fixed/registration nahi).
  (ConnexCS support se "use From header as CLI / trust endpoint CLI"
   poochho -- parameter rewrite CLI = From user.)

Jab ConnexCS From se CLI lega, to local presence (jo From mein already
sahi number bhejta hai) khud chal jayegा -- dialer mein kuch nahi chahiye.

BADLI FILES
-----------
  frontend/static/js/dialer.js     (PAI/PPI header removed)
  frontend/templates/base.html     (dialer.js ?v=20261126b)

DEPLOY -> dialer HARD-REFRESH (Ctrl+F5) -> call connect check karo.
