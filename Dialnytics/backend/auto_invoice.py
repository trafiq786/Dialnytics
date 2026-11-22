"""Auto-invoice: renewal se N din pehle customer ko invoice + PDF khud mail.

Design
------
* Admin page /renewals par ON/OFF + "N days before" + "Run now / Test on one".
* Har roz ek daily background thread check karta hai; ON ho to run() chalata hai.
* Idempotent: dialnytics_auto_invoice_log (customer_id, renewal_date) UNIQUE —
  ek customer ko ek renewal cycle mein ek hi invoice/mail jati hai, chahe app
  ke kitne hi worker/restart hon.
* SMTP na ho to invoice phir bhi ban jati hai (status 'sent') aur log mein
  emailed=false — admin baad mein manually bhej sakta hai.

main.py ye module `init(...)` se wire karta hai (circular import se bachne ke
liye dependencies inject hoti hain).
"""
import os
import time
import uuid
import logging
import threading
from datetime import date, timedelta

log = logging.getLogger("dialnytics.auto_invoice")

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS public.dialnytics_auto_invoice_log (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id uuid NOT NULL,
    renewal_date date NOT NULL,
    invoice_id uuid,
    emailed boolean NOT NULL DEFAULT false,
    detail text,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (customer_id, renewal_date)
);
CREATE INDEX IF NOT EXISTS idx_auto_invoice_log_date
    ON public.dialnytics_auto_invoice_log (renewal_date DESC);
REVOKE ALL ON public.dialnytics_auto_invoice_log FROM anon, authenticated;
"""

# ---- injected dependencies (set by main.init) ----
_db = None            # db_connect context manager
_get_setting = None   # get_setting(key, default)
_set_setting = None   # set_setting(key, value)
_build_pdf = None      # build_pdf(inv_dict, items_list) -> bytes
_mailer = None         # mailer module (send_email)
_base_url = ""


def init(db_connect, get_setting, set_setting, build_pdf, mailer, public_base_url=""):
    global _db, _get_setting, _set_setting, _build_pdf, _mailer, _base_url
    _db = db_connect
    _get_setting = get_setting
    _set_setting = set_setting
    _build_pdf = build_pdf
    _mailer = mailer
    _base_url = (public_base_url or "").rstrip("/")


# ---------------- settings helpers ----------------
def enabled() -> bool:
    try:
        return str(_get_setting("auto_invoice_enabled", "0")) == "1"
    except Exception:
        return False


def days_before() -> int:
    try:
        n = int(_get_setting("auto_invoice_days", "3"))
    except Exception:
        n = 3
    return min(max(n, 1), 30)


def cc_admin() -> str:
    try:
        return (_get_setting("auto_invoice_cc", "") or "").strip()
    except Exception:
        return ""


def last_run() -> str:
    try:
        return _get_setting("auto_invoice_last_run", "") or ""
    except Exception:
        return ""


# ---------------- core ----------------
def _due_customers(cur, target):
    cur.execute("""
        SELECT u.id, u.name, u.email, u.plan_name, u.plan_renewal,
               u.last_paid_amount, u.contact_phone, u.contact_address
          FROM public.dialnytics_users u
         WHERE u.role <> 'admin'
           AND u.is_active = TRUE
           AND COALESCE(u.is_demo, FALSE) = FALSE
           AND u.email IS NOT NULL AND u.email <> ''
           AND u.plan_renewal = %s
         ORDER BY u.name
    """, (target,))
    return cur.fetchall()


def _make_invoice(cur, c, target):
    """Create a 'sent' invoice for customer c for the renewal `target`.
    Returns (invoice_dict, items_list)."""
    amount = int(round(float(c.get("last_paid_amount") or 0)))
    if amount <= 0:
        raise ValueError("no monthly amount set on customer")
    plan = (c.get("plan_name") or "Dialnytics").strip()
    desc = "%s plan - monthly subscription (renews %s)" % (plan, target.isoformat())
    cur.execute("SELECT nextval('public.dialnytics_invoice_seq') AS n")
    number = "INV-%d-%04d" % (target.year, cur.fetchone()["n"])
    issue = date.today()
    cur.execute("""
        INSERT INTO public.dialnytics_invoices
            (invoice_number, customer_id, customer_name, customer_email, contact_phone, contact_address,
             issue_date, due_date, notes, terms, subtotal_pkr, discount_pkr, tax_percent, tax_pkr,
             total_pkr, status, payment_method, card_name, renewal_date, paid_pkr)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,0,0,0,%s,'sent','bank','',%s,0)
        RETURNING id, invoice_number, customer_name, customer_email, contact_phone,
                  contact_address, issue_date, due_date, notes, terms, subtotal_pkr,
                  discount_pkr, tax_percent, tax_pkr, total_pkr, status, payment_method,
                  card_name, renewal_date, paid_pkr
    """, (number, c["id"], c["name"], c["email"], c.get("contact_phone") or "",
          c.get("contact_address") or "", issue, target,
          "Auto-generated renewal invoice.", "Payment is due by the due date shown.",
          amount, amount, target))
    inv = dict(cur.fetchone())
    cur.execute("""
        INSERT INTO public.dialnytics_invoice_items
            (invoice_id, position, description, qty, unit_price_pkr, amount_pkr)
        VALUES (%s,0,%s,1,%s,%s)
    """, (inv["id"], desc[:500], amount, amount))
    items = [{"description": desc, "qty": 1, "unit_price_pkr": amount, "amount_pkr": amount, "position": 0}]
    return inv, items


def _email_invoice(inv, items, customer):
    """Render PDF + email it. Returns (ok, detail)."""
    if _mailer is None or not _mailer.configured():
        return False, "SMTP not configured"
    try:
        pdf = _build_pdf(inv, items)
    except Exception as e:  # noqa: BLE001
        log.exception("PDF build failed")
        return False, "pdf: %s" % e
    total = inv.get("total_pkr") or 0
    due = inv.get("due_date")
    due_s = due.isoformat() if hasattr(due, "isoformat") else str(due)
    name = (customer.get("name") or "there").split()[0]
    portal = _base_url or "https://dialnytics.co.uk"
    subject = "Your Dialnytics invoice %s - renewal due %s" % (inv.get("invoice_number"), due_s)
    html = """\
<div style="font-family:Arial,Helvetica,sans-serif;color:#111827;max-width:560px">
  <p>Hi %s,</p>
  <p>Your Dialnytics plan renews on <b>%s</b>. Please find your invoice
     <b>%s</b> attached (PDF).</p>
  <table style="border-collapse:collapse;margin:14px 0">
    <tr><td style="padding:4px 14px 4px 0;color:#6b7280">Amount due</td>
        <td style="padding:4px 0;font-weight:700">PKR %s</td></tr>
    <tr><td style="padding:4px 14px 4px 0;color:#6b7280">Due date</td>
        <td style="padding:4px 0">%s</td></tr>
  </table>
  <p>Payment ke baad invoice paid ho jati hai aur aap ka service bina rukawat
     chalta rehta hai. Bank/payment details invoice PDF mein hain.</p>
  <p>Shukriya,<br>Dialnytics Billing<br>
     <a href="%s" style="color:#2563eb">%s</a></p>
</div>""" % (name, due_s, inv.get("invoice_number"), "{:,}".format(int(total)),
            due_s, portal, portal)
    text = ("Hi %s,\n\nYour Dialnytics plan renews on %s. Invoice %s is attached.\n"
            "Amount due: PKR %s. Due date: %s.\n\nThank you,\nDialnytics Billing\n%s\n"
            % (name, due_s, inv.get("invoice_number"), "{:,}".format(int(total)), due_s, portal))
    fn = "%s.pdf" % inv.get("invoice_number")
    return _mailer.send_email(customer["email"], subject, html, text_body=text,
                              attachments=[(fn, pdf, "application/pdf")],
                              cc=(cc_admin() or None))


def run(days=None, only_email=None, dry=False):
    """Generate+send renewal invoices for customers due in `days` days.

    only_email : restrict to one customer (test-on-one-first).
    dry        : preview only, nothing created or sent.
    Returns a summary dict.
    """
    if _db is None:
        return {"error": "auto_invoice not initialised"}
    n = int(days) if days else days_before()
    n = min(max(n, 1), 30)
    target = date.today() + timedelta(days=n)
    out = {"target": target.isoformat(), "days": n, "dry": bool(dry),
           "found": 0, "invoiced": [], "emailed": 0, "skipped": [], "errors": []}
    only = (only_email or "").strip().lower()

    with _db() as conn:
        with conn.cursor() as cur:
            rows = _due_customers(cur, target)
    if only:
        rows = [r for r in rows if (r["email"] or "").lower() == only]
    out["found"] = len(rows)

    for c in rows:
        label = c.get("email") or str(c.get("id"))
        if dry:
            amt = int(round(float(c.get("last_paid_amount") or 0)))
            out["invoiced"].append({"email": label, "name": c.get("name"),
                                     "amount": amt, "preview": True,
                                     "note": "" if amt > 0 else "no amount set"})
            continue
        try:
            with _db() as conn:
                with conn.cursor() as cur:
                    # Claim this (customer, renewal) slot first — stops double-send
                    # across workers/restarts.
                    cur.execute("""
                        INSERT INTO public.dialnytics_auto_invoice_log (customer_id, renewal_date)
                        VALUES (%s,%s)
                        ON CONFLICT (customer_id, renewal_date) DO NOTHING
                        RETURNING id
                    """, (c["id"], target))
                    claim = cur.fetchone()
                    if not claim:
                        out["skipped"].append({"email": label, "reason": "already invoiced this cycle"})
                        continue
                    log_id = claim["id"]
                    try:
                        inv, items = _make_invoice(cur, c, target)
                    except ValueError as e:
                        # No amount etc. — drop the claim so it can be fixed+retried.
                        cur.execute("DELETE FROM public.dialnytics_auto_invoice_log WHERE id=%s", (log_id,))
                        out["skipped"].append({"email": label, "reason": str(e)})
                        continue
                    ok, detail = _email_invoice(inv, items, c)
                    cur.execute("""UPDATE public.dialnytics_auto_invoice_log
                                   SET invoice_id=%s, emailed=%s, detail=%s WHERE id=%s""",
                                (inv["id"], bool(ok), detail[:400], log_id))
            out["invoiced"].append({"email": label, "name": c.get("name"),
                                     "invoice": inv["invoice_number"],
                                     "amount": int(inv["total_pkr"]), "emailed": bool(ok),
                                     "detail": detail})
            if ok:
                out["emailed"] += 1
        except Exception as e:  # noqa: BLE001
            log.exception("auto-invoice for %s failed", label)
            out["errors"].append({"email": label, "error": "%s: %s" % (type(e).__name__, e)})
    return out


# ---------------- daily scheduler ----------------
def _claim_today():
    """Return True at most once per calendar day across all workers."""
    today = date.today().isoformat()
    try:
        with _db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT pg_advisory_xact_lock(hashtext('dialnytics-auto-invoice-day'))")
                cur.execute("SELECT value FROM public.dialnytics_settings WHERE key='auto_invoice_last_run'")
                row = cur.fetchone()
                if row and str(row["value"]) == today:
                    return False
                cur.execute("""INSERT INTO public.dialnytics_settings(key,value,updated_at)
                               VALUES('auto_invoice_last_run',%s,NOW())
                               ON CONFLICT(key) DO UPDATE SET value=EXCLUDED.value,updated_at=NOW()""",
                            (today,))
        return True
    except Exception:
        log.exception("auto-invoice claim_today failed")
        return False


def _loop():
    time.sleep(25)  # let the app settle after boot
    while True:
        try:
            if enabled() and _claim_today():
                log.info("auto-invoice daily run starting")
                summary = run()
                log.info("auto-invoice daily run: %s invoiced, %s emailed, %s skipped, %s errors",
                         len(summary.get("invoiced", [])), summary.get("emailed"),
                         len(summary.get("skipped", [])), len(summary.get("errors", [])))
        except Exception:
            log.exception("auto-invoice loop iteration failed")
        time.sleep(3600)  # hourly wake; _claim_today keeps it to once/day


def start_scheduler():
    if _db is None:
        log.warning("auto-invoice scheduler not started (not initialised)")
        return
    if os.getenv("AUTO_INVOICE_SCHEDULER", "1").strip() == "0":
        log.info("auto-invoice scheduler disabled by AUTO_INVOICE_SCHEDULER=0")
        return
    threading.Thread(target=_loop, name="auto-invoice", daemon=True).start()
    log.info("auto-invoice daily scheduler started")
