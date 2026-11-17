# Update VV4: Test page mein Caller ID (CLI) field

Server ne bataya: "405 CLI Restriction in effect" — yani caller ID (From number) allowed nahi.
Ab test page mein Caller ID ka khaana hai, jisme wo number daalenge jo provider allow kare.

## File
- frontend/static/sip-test.html

## Deploy
sip-test.html GitHub pe replace, Render → Manual Deploy.

## Test (provider ke CLI allow karne ke baad)
1. WSS: wss://sip.echodial.ai:443/ws, username dialnytics, password, REGISTER tick, Connect.
2. "Caller ID / CLI" mein wo number daalein jo provider ne allowed kiya (jaise 17045978991).
3. "Number to call" mein destination.
4. Call. Ab From mein wo CLI jayega.
