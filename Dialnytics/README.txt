DIALNYTICS UPDATE S  -  Super admin bhi Live call sun sake (2026-11-08)
======================================================================
P, Q, R ke upar lagao. 2 files:
  frontend/templates/team.html
  frontend/static/js/monitor-phone.js   (NAYI file)

MASLA: super admin ke pages par dialer load nahi hota, is liye "Open the dialer" error.
FIX:   jahan dialer nahi (super admin), Team page khud ek chhota "sunne wala phone" load
       karta hai (sirf Live call sunne ke liye; koi aur call nahi leta).
       Pehli dafa Listen dabane par "Connecting your listening phone..." 2-5 second.

Company owners (jin ke paas dialer hai) ke liye kuch nahi badla: un ka dialer hi sunta hai.

TEST: super admin -> Companies -> company -> Open Team view -> Live call -> Listen.
Browser microphone permission maange to Allow karo (Listen mein mic band hi rehta hai,
Whisper/Join ke liye chahiye).
