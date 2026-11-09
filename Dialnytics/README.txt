Update X - Empty companies delete
Files replace karein:
  Dialnytics/backend/main.py
  Dialnytics/frontend/templates/companies.html
  Dialnytics/frontend/templates/company_detail.html

1) Auto: jis company mein koi active user na ho (aur 24 ghante se purani ho) wo
   Companies page kholte hi khud delete ho jati ha. Nayi bani company ko 24 ghante milte hain users add karne ke liye.
   (Render env EMPTY_COMPANY_GRACE_HOURS se time badal sakte hain, default 24)
2) Manual: Companies list mein jis company ke Users = 0 hain wahan red "Delete" button.
   Company detail page ke neeche "Delete company" section.
   Jis company mein active users hain wo delete nahi hogi (pehle users hatayen).
Database change koi nahi.
