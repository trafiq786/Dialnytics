==========================================================
  LOCAL PRESENCE — ab pool CLI asli ANI banegi (SIP)
==========================================================

MASLA
-----
Local presence ON tha lekin call assigned (user ka apna) number se ja
rahi thi. Wajah: dialer sirf "From" header mein local CLI bhejta tha,
par ConnexCS global SIP par registration username (= assigned number)
ko hi asserted caller-ID (ANI) bana deta tha.

AB KYA HUA
----------
Jab local presence pool se koi ALAG CLI uthata hai, dialer ab us CLI ko
P-Asserted-Identity (aur P-Preferred-Identity) header mein bhi bhejta hai.
Tumhari ConnexCS wali P-Asserted-ID rewrite ( (.*) -> $1 ) ab usi ko
aage Infinity tak le jayegi -> ANI = pool wala local number.

(Jab pool match na ho to pehle jaisa fallback = user ka apna number,
koi PAI nahi bhejta -- behaviour safe.)

TEST (ek user par)
------------------
1) Deploy -> dialer page HARD-REFRESH (Ctrl+F5).
2) Local presence ON wale user se aisa number dial karo jiska AREA CODE
   pool mein maujood ho.
3) Call ke CDR/console mein ANI check karo -> ab pool wala local number
   hona chahiye, assigned nahi.

AGAR PHIR BHI ASSIGNED CLI JAYE
-------------------------------
Do mein se ek:
 (a) Pool mein us destination ke AREA CODE ka koi number NAHI -> fallback
     user ke number par. (Pool mein wo area code add karo.)
 (b) ConnexCS us customer par client ki PAI accept/trust nahi kar raha.
     ConnexCS customer -> CLI/Caller-ID setting ko "From header / PAI se
     lo" (fixed/registration nahi) par set karna pad sakta hai. Agar call
     FAIL ho jaye (403) to PAI reject ho rahi hai -> batao, revert kar
     denge.

BADLI FILES
-----------
  frontend/static/js/dialer.js     (PAI/PPI header jab local presence)
  frontend/templates/base.html     (dialer.js ?v=20261126)

NOTE: ye change sirf local-presence+pool-match wali calls ko chhuta hai.
Baqi calls bilkul pehle jaisi.
