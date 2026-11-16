# Update SS: internet ke chhote jhatkon se call na kate

## Masla
Dialer har 0.7 second baad call ki sehat check karta hai. Pehle:
- internet sirf **2 second** ke liye ruka, ya
- 2 second tak awaz ke packets nahi aaye,
tou dialer call ko "khatam" maan leta tha. Awaz band ho jati thi aur screen pe "Call ended" aa jata tha, halaanke asal call aksar zinda hoti thi aur internet 1–2 second mein wapas aa jata.

## Ab
- Internet ruke tou call **nahi katti**. Screen pe likha aata hai: **"Internet weak · reconnecting… (call is still on)"**.
- Internet wapas aate hi awaz khud wapas aa jati hai aur message hat jata hai.
- **25 second** tak internet bilkul na aaye, tabhi call band hoti hai. Us waqt dialer call ko theek se kaat deta hai, taake saamne wala khamoshi mein na rahe aur bill na chalta rahe.
- Telnyx ka signal wala connection ek pal ke liye toote tou bhi call chalti rehti hai (naye Telnyx SDK mein; purane mein ye setting khud ignore ho jati hai).

## Files
- frontend/static/js/dialer.js
- frontend/templates/base.html (naya version number)

Deploy ke baad sab users ek dafa page refresh karein.
