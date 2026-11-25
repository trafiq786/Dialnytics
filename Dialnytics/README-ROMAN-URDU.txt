==========================================================
  CRM IMPORT v4 — 50k se zyada ho to baqi SKIP (reject nahi)
==========================================================

TABDEELI
--------
- Ab agar file mein 50,000 se ZYADA leads hon to error nahi aata.
  Pehle 50,000 import ho jate hain, baqi (extra) SKIP count mein chale
  jate hain.
  (Pehle poori file reject hoti thi "Maximum 50,000 rows".)

- Misal: 2.44 lakh wali file -> pehle 50,000 add (unique), baaki ~1.94
  lakh "skipped" mein. Dubara upload karne par agle naye numbers add
  honge (duplicate khud skip, is liye repeat nahi honge).

Baqi sab waise hi:
  - COPY se fast insert (seconds mein)
  - FN/LN naam, address->notes, US +1 auto, khaali consent allow
  - Limit badalni ho: Render env CRM_IMPORT_MAX (default 50000)

BADLI FILE
----------
  backend/main.py
