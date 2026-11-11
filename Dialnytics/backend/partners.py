"""White-label partners: prepaid wallet, seat billing and add-ons.

A partner is a reseller login (user_type='reseller') with a row in public.partners.
Money model (all USD):
  * The partner pays by bank transfer and reports it (amount, reference, screenshot).
    It stays 'pending' until the super admin confirms it.
  * Every seat (user) and add-on is charged from the wallet: the remaining days of the
    current month when it is created, then the full month on the 1st (UTC).
  * available = confirmed balance + credit limit. When available is not enough, NEW users
    and NEW add-ons are refused; existing users keep working (renewals still post, so the
    balance can go negative and the partner sees what is owed).
Ledger amounts: deposits/credits positive, charges negative. Only 'confirmed' and
'posted' rows count toward the balance.
"""
import calendar
import logging
import secrets
import threading
import time
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP

from fastapi import Request, Form, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, Response

log = logging.getLogger("dialnytics.partners")

SCHEMA_SQL = """
-- 31: white-label partners (wallet, seats, add-ons)
CREATE TABLE IF NOT EXISTS public.partners (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL UNIQUE REFERENCES public.dialnytics_users(id) ON DELETE CASCADE,
    status text NOT NULL DEFAULT 'active' CHECK (status IN ('active','suspended')),
    credit_limit numeric(12,2) NOT NULL DEFAULT 200,
    prices jsonb NOT NULL DEFAULT '{}'::jsonb,
    bank_details text NOT NULL DEFAULT '',
    notes text NOT NULL DEFAULT '',
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS public.partner_ledger (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    partner_id uuid NOT NULL REFERENCES public.partners(id) ON DELETE CASCADE,
    kind text NOT NULL CHECK (kind IN ('deposit','charge','adjust')),
    status text NOT NULL CHECK (status IN ('pending','confirmed','rejected','posted')),
    amount numeric(12,2) NOT NULL,
    description text NOT NULL DEFAULT '',
    reference text NOT NULL DEFAULT '',
    proof bytea,
    proof_type text NOT NULL DEFAULT '',
    user_id uuid,
    charge_key text UNIQUE,
    decided_by uuid,
    decided_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS partner_ledger_partner_idx ON public.partner_ledger(partner_id, created_at DESC);
CREATE INDEX IF NOT EXISTS partner_ledger_pending_idx ON public.partner_ledger(status) WHERE status='pending';
CREATE TABLE IF NOT EXISTS public.partner_seats (
    user_id uuid PRIMARY KEY REFERENCES public.dialnytics_users(id) ON DELETE CASCADE,
    partner_id uuid NOT NULL REFERENCES public.partners(id) ON DELETE CASCADE,
    account_id uuid,
    plan text NOT NULL CHECK (plan IN ('us','ca','usca','uk')),
    addons text[] NOT NULL DEFAULT '{}',
    paid_until date NOT NULL,
    active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    cancelled_at timestamptz
);
CREATE INDEX IF NOT EXISTS partner_seats_partner_idx ON public.partner_seats(partner_id) WHERE active;
-- Which calls a partner seat may make: us = US only, ca = Canada only, usca = both, uk = UK.
ALTER TABLE public.dialnytics_users ADD COLUMN IF NOT EXISTS partner_plan text NOT NULL DEFAULT '';
-- 32: partner brand + own domain
ALTER TABLE public.partners ADD COLUMN IF NOT EXISTS brand_name text NOT NULL DEFAULT '';
ALTER TABLE public.partners ADD COLUMN IF NOT EXISTS brand_color text NOT NULL DEFAULT '';
ALTER TABLE public.partners ADD COLUMN IF NOT EXISTS support_whatsapp text NOT NULL DEFAULT '';
ALTER TABLE public.partners ADD COLUMN IF NOT EXISTS logo bytea;
ALTER TABLE public.partners ADD COLUMN IF NOT EXISTS logo_type text NOT NULL DEFAULT '';
ALTER TABLE public.partners ADD COLUMN IF NOT EXISTS logo_version integer NOT NULL DEFAULT 0;
ALTER TABLE public.partners ADD COLUMN IF NOT EXISTS domain text;
ALTER TABLE public.partners ADD COLUMN IF NOT EXISTS domain_status text NOT NULL DEFAULT '';
ALTER TABLE public.partners ADD COLUMN IF NOT EXISTS theme text NOT NULL DEFAULT '';
CREATE UNIQUE INDEX IF NOT EXISTS partners_domain_idx ON public.partners(lower(domain)) WHERE domain IS NOT NULL;
ALTER TABLE public.partners ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.partner_ledger ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.partner_seats ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.partners FROM anon, authenticated;
REVOKE ALL ON public.partner_ledger FROM anon, authenticated;
REVOKE ALL ON public.partner_seats FROM anon, authenticated;
"""

PLANS = {"us": "USA", "ca": "Canada", "usca": "USA + Canada", "uk": "United Kingdom"}
ADDONS = {"power": "Power Dialer + CRM", "rec": "Call recording", "conf": "3-way call + Leave call"}
DEFAULT_PRICES = {
    "uk": "34", "us1": "22", "us2": "20", "us3": "18", "usca1": "27", "usca3": "22",
    "power": "8", "rec": "5", "conf": "10",
}
PRICE_LABELS = [
    ("uk", "UK / user"), ("us1", "USA or Canada · 1 user"), ("us2", "USA or Canada · 2 users (each)"),
    ("us3", "USA or Canada · 3+ users (each)"), ("usca1", "USA + Canada · 1–2 users (each)"),
    ("usca3", "USA + Canada · 3+ users (each)"),
    ("power", "Add-on: Power Dialer + CRM"), ("rec", "Add-on: Call recording"), ("conf", "Add-on: 3-way + Leave call"),
]
MAX_PROOF = 5 * 1024 * 1024
PROOF_TYPES = {"image/png", "image/jpeg", "image/webp", "application/pdf"}

# NANP area codes that belong to Canada (everything else on +1 is treated as USA).
CANADA_AREA_CODES = {
    "204", "226", "236", "249", "250", "257", "263", "289", "306", "343", "354", "365", "367", "368", "382",
    "387", "403", "416", "418", "428", "431", "437", "438", "450", "460", "468", "474", "506", "514", "519",
    "548", "579", "581", "584", "587", "600", "604", "613", "622", "639", "647", "672", "683", "705", "709",
    "742", "753", "778", "780", "782", "807", "819", "825", "867", "873", "879", "902", "905", "942",
}

CENT = Decimal("0.01")


def money(v):
    return Decimal(str(v or 0)).quantize(CENT, rounding=ROUND_HALF_UP)


def fmt(v):
    v = money(v)
    sign = "−" if v < 0 else ""
    return f"{sign}${abs(v):,.2f}"


def nanp_country(digits):
    """'US' or 'CA' for a +1 number (digits only, starting with 1), else ''."""
    if not digits.startswith("1") or len(digits) < 4:
        return ""
    return "CA" if digits[1:4] in CANADA_AREA_CODES else "US"


def plan_allows(plan, digits):
    """Extra check for partner seats on top of the normal UK / +1 zones."""
    if plan in ("us", "ca") and digits.startswith("1"):
        return nanp_country(digits) == plan.upper()
    return True


def prices_of(partner):
    p = dict(DEFAULT_PRICES)
    for k, v in (partner.get("prices") or {}).items():
        if k in p:
            try:
                p[k] = str(money(v))
            except Exception:
                pass
    return {k: money(v) for k, v in p.items()}


def seat_price(prices, plan, company_count):
    """Monthly price of one seat when its company has `company_count` seats of the same family."""
    n = max(1, int(company_count or 1))
    if plan == "uk":
        return prices["uk"]
    if plan in ("us", "ca"):
        return prices["us1"] if n == 1 else prices["us2"] if n == 2 else prices["us3"]
    return prices["usca1"] if n < 3 else prices["usca3"]


def addons_price(prices, addons):
    return sum((prices[a] for a in addons if a in ADDONS), Decimal("0"))


def family(plan):
    return "nanp" if plan in ("us", "ca") else plan


def month_end(d):
    return d.replace(day=calendar.monthrange(d.year, d.month)[1])


def add_months(d, n):
    y, m = divmod(d.month - 1 + n, 12)
    y, m = d.year + y, m + 1
    return d.replace(year=y, month=m, day=min(d.day, calendar.monthrange(y, m)[1]))


def period_end(start):
    """A seat that starts on 11 Dec is paid until 10 Jan."""
    return add_months(start, 1) - timedelta(days=1)


def prorate(monthly, paid_until, today=None):
    """Part of a monthly price for the days left in the seat's current period (today included)."""
    today = today or datetime.now(timezone.utc).date()
    start = add_months(paid_until + timedelta(days=1), -1)
    total = max(1, (paid_until - start).days + 1)
    left = max(0, min(total, (paid_until - today).days + 1))
    return money(Decimal(monthly) * left / total), left


def register(app, d):
    db_connect = d["db_connect"]
    templates = d["templates"]
    get_current_user = d["get_current_user"]
    require_admin = d["require_admin"]
    refresh_users = d["refresh_users"]
    worker_should_run = d.get("worker_should_run") or (lambda: True)

    # ------------------------------------------------------------------ data
    def partner_by_user(cur, user_id):
        cur.execute("SELECT * FROM public.partners WHERE user_id=%s", (user_id,))
        return cur.fetchone()

    def partner_of(user):
        if not user or user.get("user_type") != "reseller":
            return None
        with db_connect() as conn:
            with conn.cursor() as cur:
                return partner_by_user(cur, user["id"])

    def balance(cur, pid):
        cur.execute("""SELECT COALESCE(sum(amount),0) AS b FROM public.partner_ledger
            WHERE partner_id=%s AND status IN ('confirmed','posted')""", (pid,))
        return money(cur.fetchone()["b"])

    def summary(cur, partner):
        bal = balance(cur, partner["id"])
        credit = money(partner["credit_limit"])
        cur.execute("""SELECT COALESCE(sum(amount),0) AS p, count(*) AS n FROM public.partner_ledger
            WHERE partner_id=%s AND status='pending'""", (partner["id"],))
        pend = cur.fetchone()
        return {"balance": bal, "credit": credit, "available": bal + credit,
                "pending": money(pend["p"]), "pending_count": pend["n"],
                "renewal": next_renewal(cur, partner)}

    def seats(cur, pid, active_only=True):
        cur.execute("""SELECT s.*, u.name, u.email, u.phone_number, u.is_active AS user_active, a.name AS company
            FROM public.partner_seats s JOIN public.dialnytics_users u ON u.id=s.user_id
            LEFT JOIN public.dialnytics_accounts a ON a.id=s.account_id
            WHERE s.partner_id=%s """ + ("AND s.active " if active_only else "") +
            "ORDER BY a.name NULLS LAST, s.created_at", (pid,))
        return cur.fetchall()

    def company_counts(rows):
        counts = {}
        for s in rows:
            if s["active"]:
                key = (str(s["account_id"] or s["user_id"]), family(s["plan"]))
                counts[key] = counts.get(key, 0) + 1
        return counts

    def seat_monthly(prices, s, counts):
        n = counts.get((str(s["account_id"] or s["user_id"]), family(s["plan"])), 1)
        return seat_price(prices, s["plan"], n) + addons_price(prices, s["addons"] or [])

    def next_renewal(cur, partner):
        prices = prices_of(partner)
        rows = seats(cur, partner["id"])
        counts = company_counts(rows)
        return money(sum((seat_monthly(prices, s, counts) for s in rows), Decimal("0")))

    def post(cur, pid, amount, description, user_id=None, key=None, kind="charge", status="posted"):
        cur.execute("""INSERT INTO public.partner_ledger(partner_id,kind,status,amount,description,user_id,charge_key)
            VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (charge_key) DO NOTHING RETURNING id""",
            (pid, kind, status, money(amount), description[:300], user_id, key))
        return cur.fetchone() is not None

    def apply_features(cur, user_id, plan, addons):
        """Turn the paid plan + add-ons into the user's dialer switches."""
        conf = "conf" in addons
        cur.execute("""UPDATE public.dialnytics_users SET partner_plan=%s, power_enabled=%s,
                recording_premium=%s, conf_leave=%s, adv_calling=%s, call_countries=%s WHERE id=%s""",
            (plan, "power" in addons, "rec" in addons, conf, conf, "UK" if plan == "uk" else "US", user_id))

    # ------------------------------------------------------------------ actions used by user creation (phase 2)
    def quote_new_seat(cur, partner, account_id, plan, addons):
        prices = prices_of(partner)
        rows = seats(cur, partner["id"])
        n = 1 + sum(1 for s in rows if str(s["account_id"] or "") == str(account_id or "-")
                    and family(s["plan"]) == family(plan))
        monthly = seat_price(prices, plan, n) + addons_price(prices, addons)
        today = datetime.now(timezone.utc).date()
        return {"monthly": monthly, "today": monthly, "paid_until": period_end(today), "company_count": n}

    def sync_renewal(cur, user_id, paid_until):
        """The dialer blocks calls after plan_renewal: keep it one day after the paid period."""
        cur.execute("UPDATE public.dialnytics_users SET plan_renewal=%s WHERE id=%s",
                    (paid_until + timedelta(days=1), user_id))

    def add_seat(cur, partner, user_id, account_id, plan, addons):
        """Charge and register a new seat. Raises 402 when the wallet cannot pay for it."""
        if plan not in PLANS:
            raise HTTPException(status_code=422, detail="Choose a plan")
        addons = sorted({a for a in addons if a in ADDONS})
        if partner["status"] != "active":
            raise HTTPException(status_code=403, detail="Your partner account is suspended")
        q = quote_new_seat(cur, partner, account_id, plan, addons)
        s = summary(cur, partner)
        if s["available"] < q["today"]:
            raise HTTPException(status_code=402, detail=f"Not enough balance: this user costs {fmt(q['today'])} today, "
                                                        f"available is {fmt(s['available'])}. Add a payment first.")
        today = datetime.now(timezone.utc).date()
        cur.execute("""INSERT INTO public.partner_seats(user_id,partner_id,account_id,plan,addons,paid_until)
            VALUES (%s,%s,%s,%s,%s,%s)
            ON CONFLICT (user_id) DO UPDATE SET partner_id=EXCLUDED.partner_id, account_id=EXCLUDED.account_id,
                plan=EXCLUDED.plan, addons=EXCLUDED.addons, paid_until=EXCLUDED.paid_until, active=true, cancelled_at=NULL""",
            (user_id, partner["id"], account_id, plan, addons, q["paid_until"]))
        label = PLANS[plan] + (" + " + ", ".join(ADDONS[a] for a in addons) if addons else "")
        post(cur, partner["id"], -q["today"], f"New user · {label} · until {q['paid_until']:%d %b %Y}",
             user_id, f"seat:{user_id}:{today.isoformat()}")
        apply_features(cur, user_id, plan, addons)
        sync_renewal(cur, user_id, q["paid_until"])
        return q

    def change_addons(cur, partner, user_id, new_addons):
        cur.execute("SELECT * FROM public.partner_seats WHERE user_id=%s AND partner_id=%s AND active",
                    (user_id, partner["id"]))
        seat = cur.fetchone()
        if not seat:
            raise HTTPException(status_code=404, detail="User not found")
        new_addons = sorted({a for a in new_addons if a in ADDONS})
        added = [a for a in new_addons if a not in (seat["addons"] or [])]
        prices = prices_of(partner)
        cost, days_left = prorate(addons_price(prices, added), seat["paid_until"]) if added else (Decimal("0"), 0)
        if cost:
            s = summary(cur, partner)
            if s["available"] < cost:
                raise HTTPException(status_code=402, detail=f"Not enough balance for these add-ons ({fmt(cost)} today).")
            today = datetime.now(timezone.utc).date()
            post(cur, partner["id"], -cost, "Add-on · " + ", ".join(ADDONS[a] for a in added)
                 + f" · {days_left} days until {seat['paid_until']:%d %b %Y}",
                 user_id, f"addon:{user_id}:{today.isoformat()}:{'-'.join(added)}:{secrets.token_hex(3)}")
        cur.execute("UPDATE public.partner_seats SET addons=%s WHERE user_id=%s", (new_addons, user_id))
        apply_features(cur, user_id, seat["plan"], new_addons)
        return cost

    def cancel_seat(cur, partner, user_id):
        cur.execute("""UPDATE public.partner_seats SET active=false, cancelled_at=now()
            WHERE user_id=%s AND partner_id=%s AND active RETURNING user_id""", (user_id, partner["id"]))
        return cur.fetchone() is not None

    # ------------------------------------------------------------------ monthly renewal
    def renew_all(today=None):
        """Charge every active seat whose paid month has ended (each seat renews on its own
        start date: started 11 Dec -> renews 11 Jan). Idempotent."""
        today = today or datetime.now(timezone.utc).date()
        done = 0
        with db_connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT pg_advisory_xact_lock(hashtext('dialnytics-partner-renewal'))")
                cur.execute("SELECT * FROM public.partners")
                for partner in cur.fetchall():
                    prices = prices_of(partner)
                    rows = seats(cur, partner["id"])
                    counts = company_counts(rows)
                    for s in rows:
                        if s["paid_until"] >= today:
                            continue
                        if not s["user_active"]:
                            cur.execute("UPDATE public.partner_seats SET active=false, cancelled_at=now() WHERE user_id=%s",
                                        (s["user_id"],))
                            continue
                        monthly = seat_monthly(prices, s, counts)
                        start = s["paid_until"] + timedelta(days=1)
                        until = period_end(start)
                        label = PLANS[s["plan"]] + (" + add-ons" if s["addons"] else "")
                        post(cur, partner["id"], -monthly,
                             f"Renewal · {s['name']} · {label} · {start:%d %b} – {until:%d %b %Y}",
                             s["user_id"], f"seat:{s['user_id']}:{start.isoformat()}")
                        cur.execute("UPDATE public.partner_seats SET paid_until=%s WHERE user_id=%s",
                                    (until, s["user_id"]))
                        sync_renewal(cur, s["user_id"], until)
                        done += 1
        if done:
            log.info("Partner renewal: %d seats charged", done)
            try:
                refresh_users()
            except Exception:
                log.exception("refresh after renewal failed")
        return done

    def renewal_loop():
        while True:
            try:
                if worker_should_run():
                    renew_all()
            except Exception:
                log.exception("Partner renewal failed")
            time.sleep(3600)

    if not d.get("no_worker"):
        threading.Thread(target=renewal_loop, daemon=True, name="partner-renewal").start()

    # ------------------------------------------------------------------ partner pages
    def need_partner(request):
        user = get_current_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Sign in")
        partner = partner_of(user)
        if not partner:
            raise HTTPException(status_code=403, detail="Partner access required")
        return user, partner

    @app.get("/partner/wallet", response_class=HTMLResponse)
    async def partner_wallet(request: Request):
        user = get_current_user(request)
        if not user:
            return RedirectResponse("/login", status_code=302)
        partner = partner_of(user)
        if not partner:
            return RedirectResponse("/clients", status_code=302)
        with db_connect() as conn:
            with conn.cursor() as cur:
                s = summary(cur, partner)
                cur.execute("""SELECT id,kind,status,amount,description,reference,created_at,proof_type
                    FROM public.partner_ledger WHERE partner_id=%s ORDER BY created_at DESC LIMIT 200""", (partner["id"],))
                ledger = cur.fetchall()
                rows = seats(cur, partner["id"])
        prices = prices_of(partner)
        counts = company_counts(rows)
        seat_rows = [dict(r, monthly=seat_monthly(prices, r, counts)) for r in rows]
        return templates.TemplateResponse(request=request, name="partner_wallet.html", context={
            "user": user, "partner": partner, "s": s, "ledger": ledger, "seats": seat_rows, "fmt": fmt, "day": timedelta(days=1),
            "plans": PLANS, "addons": ADDONS, "prices": prices, "price_labels": PRICE_LABELS,
            "msg": request.query_params.get("msg"), "err": request.query_params.get("err")})

    @app.post("/partner/wallet/deposit")
    async def partner_deposit(request: Request, amount: str = Form(...), reference: str = Form(""),
                              proof: UploadFile = File(None)):
        user, partner = need_partner(request)
        try:
            amt = money(amount.replace("$", "").replace(",", "").strip())
        except Exception:
            amt = Decimal("0")
        if amt <= 0 or amt > Decimal("100000"):
            return RedirectResponse("/partner/wallet?err=amount", status_code=303)
        data, ctype = None, ""
        if proof is not None and proof.filename:
            data = await proof.read(MAX_PROOF + 1)
            ctype = (proof.content_type or "").lower()
            if len(data) > MAX_PROOF or ctype not in PROOF_TYPES:
                return RedirectResponse("/partner/wallet?err=proof", status_code=303)
        with db_connect() as conn:
            with conn.cursor() as cur:
                cur.execute("""INSERT INTO public.partner_ledger(partner_id,kind,status,amount,description,reference,proof,proof_type)
                    VALUES (%s,'deposit','pending',%s,'Bank transfer',%s,%s,%s)""",
                    (partner["id"], amt, reference.strip()[:120], data, ctype))
        log.info("Partner %s reported a payment of %s", user["email"], amt)
        return RedirectResponse("/partner/wallet?msg=sent", status_code=303)

    @app.get("/partner/proof/{entry_id}")
    async def partner_proof(entry_id: uuid.UUID, request: Request):
        user = get_current_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Sign in")
        with db_connect() as conn:
            with conn.cursor() as cur:
                cur.execute("""SELECT l.proof, l.proof_type, p.user_id FROM public.partner_ledger l
                    JOIN public.partners p ON p.id=l.partner_id WHERE l.id=%s""", (entry_id,))
                row = cur.fetchone()
        if not row or not row["proof"] or (user.get("role") != "admin" and str(row["user_id"]) != user["id"]):
            raise HTTPException(status_code=404, detail="Not found")
        return Response(bytes(row["proof"]), media_type=row["proof_type"] or "application/octet-stream",
                        headers={"Cache-Control": "private, no-store", "Content-Disposition": "inline"})

    # ------------------------------------------------------------------ admin
    def admin_partner_context(cur, reseller_id):
        partner = partner_by_user(cur, reseller_id)
        if not partner:
            return None
        s = summary(cur, partner)
        cur.execute("""SELECT id,kind,status,amount,description,reference,created_at,proof_type
            FROM public.partner_ledger WHERE partner_id=%s ORDER BY created_at DESC LIMIT 100""", (partner["id"],))
        ledger = cur.fetchall()
        prices = prices_of(partner)
        rows = seats(cur, partner["id"])
        counts = company_counts(rows)
        return {"partner": partner, "s": s, "ledger": ledger, "prices": prices, "price_labels": PRICE_LABELS,
                "seats": [dict(r, monthly=seat_monthly(prices, r, counts)) for r in rows],
                "plans": PLANS, "addons": ADDONS, "fmt": fmt}

    def partner_info_for_admin(reseller_id):
        with db_connect() as conn:
            with conn.cursor() as cur:
                return admin_partner_context(cur, reseller_id)

    @app.post("/resellers/{reseller_id}/partner")
    async def admin_partner_save(reseller_id: uuid.UUID, request: Request):
        require_admin(request)
        form = await request.form()
        action = form.get("action") or "save"
        with db_connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM public.dialnytics_users WHERE id=%s AND user_type='reseller'", (reseller_id,))
                if not cur.fetchone():
                    raise HTTPException(status_code=404, detail="Reseller not found")
                if action == "enable":
                    cur.execute("INSERT INTO public.partners(user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING",
                                (reseller_id,))
                else:
                    prices = {}
                    for key, _label in PRICE_LABELS:
                        raw = str(form.get("price_" + key) or "").replace("$", "").strip()
                        if raw:
                            try:
                                v = money(raw)
                                if Decimal("0") <= v <= Decimal("10000"):
                                    prices[key] = str(v)
                            except Exception:
                                pass
                    try:
                        credit = money(str(form.get("credit_limit") or "0").replace("$", "").replace(",", ""))
                    except Exception:
                        credit = Decimal("0")
                    status = "suspended" if form.get("status") == "suspended" else "active"
                    from psycopg.types.json import Jsonb
                    cur.execute("""UPDATE public.partners SET prices=%s, credit_limit=%s, status=%s,
                        bank_details=%s WHERE user_id=%s""",
                        (Jsonb(prices), max(Decimal("0"), credit), status,
                         str(form.get("bank_details") or "")[:1000], reseller_id))
        return RedirectResponse(f"/resellers/{reseller_id}?msg=saved#partner", status_code=303)

    @app.post("/resellers/{reseller_id}/partner/adjust")
    async def admin_partner_adjust(reseller_id: uuid.UUID, request: Request, amount: str = Form(...), note: str = Form("")):
        admin = require_admin(request)
        try:
            amt = money(amount.replace("$", "").replace(",", ""))
        except Exception:
            raise HTTPException(status_code=422, detail="Enter an amount like 50 or -20")
        if not amt:
            return RedirectResponse(f"/resellers/{reseller_id}#partner", status_code=303)
        with db_connect() as conn:
            with conn.cursor() as cur:
                partner = partner_by_user(cur, reseller_id)
                if not partner:
                    raise HTTPException(status_code=404, detail="Not a partner")
                cur.execute("""INSERT INTO public.partner_ledger(partner_id,kind,status,amount,description,decided_by,decided_at)
                    VALUES (%s,'adjust','posted',%s,%s,%s,now())""",
                    (partner["id"], amt, ("Adjustment · " + note.strip())[:300] if note.strip() else "Adjustment", admin["id"]))
        return RedirectResponse(f"/resellers/{reseller_id}?msg=saved#partner", status_code=303)

    @app.post("/partners/payments/{entry_id}/{decision}")
    async def admin_payment_decide(entry_id: uuid.UUID, decision: str, request: Request):
        admin = require_admin(request)
        if decision not in ("confirm", "reject"):
            raise HTTPException(status_code=404, detail="Not found")
        form = await request.form()
        with db_connect() as conn:
            with conn.cursor() as cur:
                amount = form.get("amount")
                params = ["confirmed" if decision == "confirm" else "rejected", admin["id"]]
                extra = ""
                if decision == "confirm" and amount:
                    try:
                        params.append(money(str(amount).replace("$", "").replace(",", "")))
                        extra = ", amount=%s"
                    except Exception:
                        pass
                params.append(entry_id)
                cur.execute(f"""UPDATE public.partner_ledger SET status=%s, decided_by=%s, decided_at=now(){extra}
                    WHERE id=%s AND kind='deposit' AND status='pending' RETURNING partner_id""", params)
                row = cur.fetchone()
                rid = None
                if row:
                    cur.execute("SELECT user_id FROM public.partners WHERE id=%s", (row["partner_id"],))
                    rid = cur.fetchone()["user_id"]
        back = form.get("back") or (f"/resellers/{rid}#partner" if rid else "/partners/payments")
        if not str(back).startswith("/"):
            back = "/partners/payments"
        return RedirectResponse(back, status_code=303)

    @app.get("/partners/payments", response_class=HTMLResponse)
    async def admin_payments(request: Request):
        admin = require_admin(request)
        with db_connect() as conn:
            with conn.cursor() as cur:
                cur.execute("""SELECT l.id,l.amount,l.reference,l.created_at,l.proof_type,l.status,l.decided_at,
                        u.name AS partner_name, u.id AS reseller_id
                    FROM public.partner_ledger l JOIN public.partners p ON p.id=l.partner_id
                    JOIN public.dialnytics_users u ON u.id=p.user_id
                    WHERE l.kind='deposit' ORDER BY (l.status='pending') DESC, l.created_at DESC LIMIT 200""")
                rows = cur.fetchall()
        return templates.TemplateResponse(request=request, name="partner_payments.html", context={
            "user": admin, "rows": rows, "fmt": fmt})

    _pp = {"at": 0, "n": 0}

    def pending_payments_count():
        if time.time() - _pp["at"] < 20:
            return _pp["n"]
        _pp["at"] = time.time()
        try:
            with db_connect() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT count(*) AS n FROM public.partner_ledger WHERE kind='deposit' AND status='pending'")
                    _pp["n"] = cur.fetchone()["n"]
                    return _pp["n"]
        except Exception:
            return 0

    templates.env.globals["partner_pending_payments"] = pending_payments_count

    _pcache = {}

    def is_partner(user):
        if not user or user.get("user_type") != "reseller":
            return False
        hit = _pcache.get(user["id"])
        if hit and time.time() - hit[0] < 30:
            return hit[1]
        val = bool(partner_of(user))
        _pcache[user["id"]] = (time.time(), val)
        return val

    templates.env.globals["is_partner"] = is_partner

    # ================================================================== phase 2: partner creates users
    telnyx_number_accounts = d.get("telnyx_number_accounts")
    tx_verified = d.get("tx_verified") or set()
    telnyx_request = d.get("telnyx_request")
    tx_ctx = d.get("tx_ctx")
    set_user_telnyx_account = d.get("set_user_telnyx_account")
    ensure_credential = d.get("ensure_credential")
    hash_password = d.get("hash_password")
    hold_info = d.get("hold_info") or (lambda numbers: {})
    public_url = d.get("public_url") or ""
    buy_account = d.get("buy_account") or "t1"
    _conn_cache = {"id": None, "at": 0}

    TOLL_FREE = ("+1800", "+1833", "+1844", "+1855", "+1866", "+1877", "+1888", "+44800", "+44808")
    PLAN_COUNTRIES = {"us": ["US"], "ca": ["CA"], "usca": ["US", "CA"], "uk": ["GB"]}

    def number_country(n):
        if n.startswith("+44"):
            return "GB"
        if n.startswith("+1"):
            return nanp_country(n[1:])
        return ""

    def taken_numbers(cur):
        cur.execute("""SELECT phone_number AS n FROM public.caller_id_assignments WHERE phone_number IS NOT NULL
            UNION SELECT phone_number FROM public.dialnytics_users WHERE COALESCE(phone_number,'')<>''
            UNION SELECT signup_number FROM public.dialnytics_users
                  WHERE signup_status='pending' AND COALESCE(signup_number,'')<>''""")
        return {r["n"] for r in cur.fetchall()}

    def pool_numbers(country, area=""):
        """Numbers you already own that nobody uses: offered first, no purchase needed."""
        owned = [n for n in telnyx_number_accounts() if n not in tx_verified]
        with db_connect() as conn:
            with conn.cursor() as cur:
                taken = taken_numbers(cur)
        held = hold_info(owned) or {}
        area = "".join(ch for ch in str(area or "") if ch.isdigit())
        out = []
        for n in sorted(owned):
            if n in taken or n in held or n.startswith(TOLL_FREE) or number_country(n) != country:
                continue
            national = n[2:] if n.startswith("+1") else n[3:]
            if area and not national.startswith(area):
                continue
            out.append(n)
        return out[:30]

    import os as _os2
    MAX_NUMBER_COST = Decimal(_os2.getenv("PARTNER_MAX_NUMBER_COST", "1"))

    def cheap_enough(item):
        """Only numbers costing at most $1 upfront and $1 a month may be bought."""
        info = item.get("cost_information") or {}
        try:
            upfront = Decimal(str(info.get("upfront_cost")))
            monthly = Decimal(str(info.get("monthly_cost")))
        except Exception:
            return False                      # no price shown: never buy blind
        if (info.get("currency") or "USD").upper() != "USD":
            return False
        return upfront <= MAX_NUMBER_COST and monthly <= MAX_NUMBER_COST

    def search_numbers(country, area="", contains=""):
        """New numbers that can be bought right now (USA and Canada), $1 or less."""
        if country not in ("US", "CA") or not telnyx_request:
            return []
        import urllib.parse as up
        q = [("filter[country_code]", country), ("filter[features][]", "voice"),
             ("filter[phone_number_type]", "local"), ("filter[limit]", "12" if not contains else "5")]
        area = "".join(ch for ch in str(area or "") if ch.isdigit())[:3]
        if len(area) == 3:
            q.append(("filter[national_destination_code]", area))
        if contains:
            q.append(("filter[phone_number][contains]", contains))
        try:
            with tx_ctx(buy_account):
                res = telnyx_request("GET", "/v2/available_phone_numbers?" + up.urlencode(q))
        except HTTPException as exc:
            log.warning("Number search failed: %s", exc.detail)
            return []
        out = []
        for item in res.get("data") or []:
            n = item.get("phone_number") or ""
            if n and number_country(n) == country and cheap_enough(item):
                out.append(n)
        return out

    def number_connection():
        """Connection new numbers go on: the same one as a number you already own."""
        import os
        env = os.getenv("PARTNER_NUMBER_CONNECTION_ID", "").strip()
        if env:
            return env
        if _conn_cache["id"] and time.time() - _conn_cache["at"] < 3600:
            return _conn_cache["id"]
        with tx_ctx(buy_account):
            res = telnyx_request("GET", "/v2/phone_numbers?page[size]=100")
        counts = {}
        for item in res.get("data") or []:
            if item.get("connection_id"):
                counts[item["connection_id"]] = counts.get(item["connection_id"], 0) + 1
        if not counts:
            return None
        best = max(counts, key=counts.get)        # where most of your numbers already are
        _conn_cache.update(id=best, at=time.time())
        return best

    def buy_number(number):
        conn_id = number_connection()
        body = {"phone_numbers": [{"phone_number": number}]}
        if conn_id:
            body["connection_id"] = conn_id
        with tx_ctx(buy_account):
            res = telnyx_request("POST", "/v2/number_orders", body)
            order = res.get("data") or {}
            for _ in range(10):
                if order.get("status") == "success":
                    break
                if order.get("status") in ("failure", "cancelled"):
                    raise HTTPException(status_code=409, detail="That number could not be bought. Pick another one.")
                time.sleep(1.5)
                order = (telnyx_request("GET", f"/v2/number_orders/{order.get('id')}") or {}).get("data") or {}
        if order.get("status") != "success":
            raise HTTPException(status_code=409, detail="The number is still being set up. Try again in a minute or pick another.")
        try:
            telnyx_number_accounts(fresh=True)
        except Exception:
            pass
        log.info("Partner bought number %s", number)
        return number

    def partner_companies(cur, partner_user_id):
        cur.execute("""SELECT a.id, a.name, count(u.id) FILTER (WHERE u.is_active) AS users
            FROM public.dialnytics_accounts a LEFT JOIN public.dialnytics_users u ON u.account_id=a.id
            WHERE a.reseller_id=%s GROUP BY a.id ORDER BY a.name""", (partner_user_id,))
        return cur.fetchall()

    def page_guard(request):
        user = get_current_user(request)
        if not user:
            return None, None, RedirectResponse("/login", status_code=302)
        partner = partner_of(user)
        if not partner:
            return user, None, RedirectResponse("/clients", status_code=302)
        return user, partner, None

    @app.get("/partner/users", response_class=HTMLResponse)
    async def partner_users(request: Request):
        user, partner, redirect = page_guard(request)
        if redirect:
            return redirect
        with db_connect() as conn:
            with conn.cursor() as cur:
                rows = seats(cur, partner["id"], active_only=False)
                s = summary(cur, partner)
        prices = prices_of(partner)
        counts = company_counts(rows)
        return templates.TemplateResponse(request=request, name="partner_users.html", context={
            "user": user, "partner": partner, "s": s, "fmt": fmt, "plans": PLANS, "addons": ADDONS, "prices": prices,
            "rows": [dict(r, monthly=seat_monthly(prices, r, counts)) for r in rows], "day": timedelta(days=1),
            "msg": request.query_params.get("msg"), "err": request.query_params.get("err")})

    @app.get("/partner/users/new", response_class=HTMLResponse)
    async def partner_user_new(request: Request):
        user, partner, redirect = page_guard(request)
        if redirect:
            return redirect
        with db_connect() as conn:
            with conn.cursor() as cur:
                companies = partner_companies(cur, user["id"])
                s = summary(cur, partner)
        return templates.TemplateResponse(request=request, name="partner_user_new.html", context={
            "user": user, "partner": partner, "s": s, "fmt": fmt, "plans": PLANS, "addons": ADDONS,
            "prices": {k: float(v) for k, v in prices_of(partner).items()}, "companies": companies,
            "error": request.query_params.get("error")})

    @app.get("/partner/api/numbers")
    async def partner_api_numbers(request: Request, country: str = "US", area: str = ""):
        need_partner(request)
        country = country.upper()
        if country not in ("US", "CA", "GB"):
            raise HTTPException(status_code=422, detail="Choose USA, Canada or UK")
        from starlette.concurrency import run_in_threadpool
        pool = await run_in_threadpool(pool_numbers, country, area)
        fresh = await run_in_threadpool(search_numbers, country, area) if len(pool) < 6 else []
        return {"pool": pool, "buy": [n for n in fresh if n not in pool]}

    @app.get("/partner/api/quote")
    async def partner_api_quote(request: Request, plan: str = "us", addons: str = "", account_id: str = ""):
        _user, partner = need_partner(request)
        if plan not in PLANS:
            raise HTTPException(status_code=422, detail="Choose a plan")
        chosen = [a for a in addons.split(",") if a in ADDONS]
        acc = None
        if account_id:
            try:
                acc = uuid.UUID(account_id)
            except ValueError:
                acc = None
        with db_connect() as conn:
            with conn.cursor() as cur:
                q = quote_new_seat(cur, partner, acc, plan, chosen)
                s = summary(cur, partner)
        return {"monthly": fmt(q["monthly"]), "today": fmt(q["today"]), "until": q["paid_until"].strftime("%d %b %Y"),
                "available": fmt(s["available"]), "enough": s["available"] >= q["today"],
                "company_count": q["company_count"]}

    @app.post("/partner/users", response_class=HTMLResponse)
    async def partner_user_create(request: Request):
        user, partner = need_partner(request)
        form = await request.form()
        from urllib.parse import urlencode
        import re as _re
        from starlette.concurrency import run_in_threadpool
        from psycopg.errors import UniqueViolation

        def fail(message):
            return RedirectResponse("/partner/users/new?" + urlencode({"error": message}), status_code=303)

        name = str(form.get("name") or "").strip()[:120]
        email = str(form.get("email") or "").strip().lower()[:200]
        password = str(form.get("password") or "")
        plan = str(form.get("plan") or "")
        chosen = [a for a in form.getlist("addons") if a in ADDONS]
        number = str(form.get("number") or "").strip()
        source = "buy" if form.get("number_source") == "buy" else "pool"
        company_mode = "existing" if form.get("company_mode") == "existing" else "new"
        company_name = str(form.get("company_name") or "").strip()[:200]
        account_role = "owner" if form.get("account_role") == "owner" else "agent"
        if partner["status"] != "active":
            return fail("Your partner account is paused. Contact support.")
        if not name or not _re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            return fail("Enter the user's name and a valid email.")
        generated = False
        if not password:
            password = secrets.token_urlsafe(12)[:14]
            generated = True
        if len(password) < 12:
            return fail("The password must be at least 12 characters, or leave it empty to create one.")
        if plan not in PLANS:
            return fail("Choose a plan.")
        if not _re.fullmatch(r"\+[1-9][0-9]{7,14}", number) or number_country(number) not in PLAN_COUNTRIES[plan]:
            return fail("Pick a phone number that matches the plan.")
        account_id = None
        with db_connect() as conn:
            with conn.cursor() as cur:
                if company_mode == "existing":
                    try:
                        account_id = uuid.UUID(str(form.get("account_id") or ""))
                    except ValueError:
                        return fail("Choose a company.")
                    cur.execute("SELECT 1 FROM public.dialnytics_accounts WHERE id=%s AND reseller_id=%s",
                                (account_id, user["id"]))
                    if not cur.fetchone():
                        return fail("Choose one of your companies.")
                elif not company_name:
                    return fail("Enter the company name.")
                cur.execute("SELECT 1 FROM public.dialnytics_users WHERE lower(email)=lower(%s)", (email,))
                if cur.fetchone():
                    return fail("A user with this email already exists.")
                q = quote_new_seat(cur, partner, account_id, plan, chosen)
                if summary(cur, partner)["available"] < q["today"]:
                    return fail(f"Not enough balance: this user costs {fmt(q['today'])}. Add a payment in Wallet first.")
        try:
            country = number_country(number)
            if source == "buy":
                # check the price again right before buying
                if number not in await run_in_threadpool(search_numbers, country, "", number[-10:]):
                    return fail("That number costs more than $1 or is no longer available. Pick another one.")
                await run_in_threadpool(buy_number, number)
            elif number not in await run_in_threadpool(pool_numbers, country, ""):
                return fail("That number was just taken. Pick another one.")
        except HTTPException as exc:
            return fail(str(exc.detail))
        try:
            with db_connect() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", ("caller-id:" + number,))
                    if number in taken_numbers(cur):
                        return fail("That number was just taken. Pick another one.")
                    if account_id is None:
                        cur.execute("INSERT INTO public.dialnytics_accounts(name, reseller_id) VALUES (%s,%s) RETURNING id",
                                    (company_name, user["id"]))
                        account_id = cur.fetchone()["id"]
                        account_role = "owner"
                    today = datetime.now(timezone.utc).date()
                    cur.execute("""INSERT INTO public.dialnytics_users
                        (name,email,password_hash,role,phone_number,plan_name,plan_start,plan_renewal,last_paid_amount,
                         recording_premium,dnd_enabled,is_demo,provider,account_id,account_role,user_type)
                        VALUES (%s,%s,%s,'agent',%s,%s,%s,%s,0,FALSE,FALSE,FALSE,'telnyx',%s,%s,'customer')
                        RETURNING id""", (name, email, hash_password(password), number, PLANS[plan].upper(),
                                         today, period_end(today) + timedelta(days=1), account_id, account_role))
                    new_id = cur.fetchone()["id"]
                    cur.execute("INSERT INTO public.caller_id_assignments(user_id,phone_number) VALUES (%s,%s)",
                                (new_id, number))
                    seat = add_seat(cur, partner, new_id, account_id, plan, chosen)
        except UniqueViolation:
            return fail("This email or number was just used. Refresh and try again.")
        except HTTPException as exc:
            return fail(str(exc.detail))
        acct = buy_account
        try:
            acct = telnyx_number_accounts().get(number, buy_account)
            set_user_telnyx_account(new_id, acct)
        except Exception:
            log.exception("Could not set the Telnyx account for a partner user")
        refresh_users()
        try:
            with tx_ctx(acct):
                ensure_credential(email)
        except Exception:
            log.exception("Telnyx credential creation failed for partner user")
        log.info("Partner %s created user %s (%s) on %s", user["email"], email, plan, number)
        return templates.TemplateResponse(request=request, name="partner_user_done.html", context={
            "user": user, "name": name, "email": email, "password": password, "generated": generated,
            "number": number, "plan": PLANS[plan], "addons": [ADDONS[a] for a in sorted(chosen)],
            "charged": fmt(seat["today"]), "until": seat["paid_until"].strftime("%d %b %Y"),
            "login_url": partner_login_url(partner)})

    @app.post("/partner/users/{user_id}/addons")
    async def partner_user_addons(user_id: uuid.UUID, request: Request):
        _user, partner = need_partner(request)
        form = await request.form()
        try:
            with db_connect() as conn:
                with conn.cursor() as cur:
                    change_addons(cur, partner, user_id, form.getlist("addons"))
        except HTTPException as exc:
            from urllib.parse import quote
            return RedirectResponse("/partner/users?err=" + quote(str(exc.detail)), status_code=303)
        refresh_users()
        return RedirectResponse("/partner/users?msg=saved", status_code=303)

    @app.post("/partner/users/{user_id}/{action}")
    async def partner_user_toggle(user_id: uuid.UUID, action: str, request: Request):
        _user, partner = need_partner(request)
        if action not in ("disable", "enable"):
            raise HTTPException(status_code=404, detail="Not found")
        try:
            with db_connect() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM public.partner_seats WHERE user_id=%s AND partner_id=%s",
                                (user_id, partner["id"]))
                    seat = cur.fetchone()
                    if not seat:
                        raise HTTPException(status_code=404, detail="User not found")
                    if action == "disable":
                        cancel_seat(cur, partner, user_id)
                        cur.execute("UPDATE public.dialnytics_users SET is_active=false WHERE id=%s", (user_id,))
                    elif not seat["active"]:
                        cur.execute("UPDATE public.dialnytics_users SET is_active=true WHERE id=%s", (user_id,))
                        add_seat(cur, partner, user_id, seat["account_id"], seat["plan"], seat["addons"] or [])
        except HTTPException as exc:
            from urllib.parse import quote
            return RedirectResponse("/partner/users?err=" + quote(str(exc.detail)), status_code=303)
        refresh_users()
        return RedirectResponse("/partner/users?msg=" + ("disabled" if action == "disable" else "enabled"), status_code=303)

    # ================================================================== phase 3: partner brand + own domain
    import contextvars
    import os as _os
    import re as _re3
    import json as _json
    import urllib.request as _ur
    import urllib.error as _ue
    from starlette.requests import Request as _Req

    _scope = contextvars.ContextVar("dn_brand_scope", default=None)
    _brand_cache = {}
    LOGO_TYPES = {"image/png", "image/jpeg", "image/webp"}
    MAX_LOGO = 600 * 1024
    DOMAIN_RE = _re3.compile(r"^(?=.{4,190}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,24}$")
    COLOR_RE = _re3.compile(r"^#[0-9a-fA-F]{6}$")
    THEMES = {"ocean": "Ocean", "emerald": "Emerald", "sunset": "Sunset", "rose": "Rose", "violet": "Violet",
              "graphite": "Graphite", "custom": "My brand colour"}
    RENDER_KEY = _os.getenv("RENDER_API_KEY", "").strip()
    RENDER_SERVICE = _os.getenv("RENDER_SERVICE_ID", "").strip()
    CNAME_TARGET = _os.getenv("PARTNER_CNAME_TARGET", "").strip()
    MAIN_HOST = (public_url.split("//", 1)[-1].split("/", 1)[0] or "").lower()

    class BrandScope:
        """Pure ASGI: remembers the request so templates can show the right brand."""
        def __init__(self, app_):
            self.app = app_

        async def __call__(self, scope, receive, send):
            if scope.get("type") != "http":
                return await self.app(scope, receive, send)
            token = _scope.set({"scope": scope, "brand": None, "done": False})
            try:
                await self.app(scope, receive, send)
            finally:
                _scope.reset(token)

    app.add_middleware(BrandScope)

    def _cached(key, loader, ttl=60):
        hit = _brand_cache.get(key)
        if hit and time.time() - hit[0] < ttl:
            return hit[1]
        val = loader()
        _brand_cache[key] = (time.time(), val)
        return val

    def brand_row_by_domain(host):
        def load():
            with db_connect() as conn:
                with conn.cursor() as cur:
                    cur.execute("""SELECT id,brand_name,brand_color,support_whatsapp,domain,domain_status,theme,
                        (logo IS NOT NULL) AS has_logo, logo_version FROM public.partners
                        WHERE lower(domain)=%s AND domain_status='live' AND status='active'""", (host,))
                    return cur.fetchone()
        return _cached("host:" + host, load)

    def brand_row_for_user(user):
        def load():
            with db_connect() as conn:
                with conn.cursor() as cur:
                    cur.execute("""SELECT p.id,p.brand_name,p.brand_color,p.support_whatsapp,p.domain,p.domain_status,p.theme,
                            (p.logo IS NOT NULL) AS has_logo, p.logo_version
                        FROM public.partners p
                        WHERE p.user_id=%s OR p.user_id=(SELECT a.reseller_id FROM public.dialnytics_accounts a
                                                          JOIN public.dialnytics_users u ON u.account_id=a.id WHERE u.id=%s)
                        LIMIT 1""", (user["id"], user["id"]))
                    return cur.fetchone()
        return _cached("user:" + user["id"], load)

    def current_brand():
        st = _scope.get()
        if not st:
            return None
        if st["done"]:
            return st["brand"]
        st["done"] = True
        brand = None
        try:
            scope = st["scope"]
            host = ""
            for k, v in scope.get("headers") or []:
                if k == b"host":
                    host = v.decode("latin-1").split(":")[0].strip().lower()
                    break
            if host and host != MAIN_HOST:
                brand = brand_row_by_domain(host)
            if not brand:
                user = get_current_user(_Req(scope))
                if user and user.get("role") != "admin":
                    brand = brand_row_for_user(user)
            if brand and not (brand.get("brand_name") or "").strip():
                brand = None
        except Exception:
            log.exception("Brand lookup failed")
            brand = None
        st["brand"] = brand
        return brand

    class Lazy:
        """Template value that follows the current request's brand."""
        def __init__(self, fn):
            self.fn = fn

        def __str__(self):
            return str(self.fn())

        def __html__(self):
            from markupsafe import escape
            return str(escape(str(self.fn())))

        def __bool__(self):
            return bool(self.fn())

        def __eq__(self, other):
            return str(self) == other

        def __hash__(self):
            return hash(str(self))

    g = templates.env.globals
    orig = {k: g.get(k) for k in ("brand_logo", "brand_logo_dark", "brand_icon", "support_whatsapp", "tour_url")}

    def logo_url(b):
        return f"/brand/logo/{b['id']}?v={b.get('logo_version') or 0}" if b and b.get("has_logo") else None

    def pick(key):
        def fn():
            b = current_brand()
            if not b:
                return orig[key] or ""
            if key in ("brand_logo", "brand_logo_dark", "brand_icon"):
                if logo_url(b):
                    return logo_url(b)
                if key == "brand_icon":       # no logo yet: a plain letter, never our icon
                    import urllib.parse as _up
                    letter = (b.get("brand_name") or "B")[:1].upper()
                    color = b.get("brand_color") or "#3565ec"
                    svg = (f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'><rect width='64' height='64' rx='14' "
                           f"fill='{color}'/><text x='32' y='44' font-size='34' font-family='Arial' font-weight='700' "
                           f"text-anchor='middle' fill='white'>{letter if letter.isalnum() else 'B'}</text></svg>")
                    return "data:image/svg+xml," + _up.quote(svg)
                return ""
            if key == "support_whatsapp":
                return (b.get("support_whatsapp") or "").strip().lstrip("+") or orig[key]
            if key == "tour_url":
                return ""
            return orig[key]
        return fn

    for key in orig:
        g[key] = Lazy(pick(key))
    g["brand_active"] = Lazy(lambda: bool(current_brand()))
    g["brand_name"] = Lazy(lambda: (current_brand() or {}).get("brand_name") or "Dialnytics")
    g["brand_color"] = Lazy(lambda: (current_brand() or {}).get("brand_color") or "")
    g["brand_theme"] = Lazy(lambda: (current_brand() or {}).get("theme") or "")
    g["brand_has_logo"] = Lazy(lambda: bool(logo_url(current_brand())))
    from jinja2 import pass_context

    @pass_context      # never folded at compile time: the brand depends on the request
    def brand_title(_ctx, text):
        return str(text).replace("Dialnytics", (current_brand() or {}).get("brand_name") or "Dialnytics")

    templates.env.filters["brand_title"] = brand_title

    def drop_brand_cache():
        _brand_cache.clear()

    @app.get("/brand/logo/{partner_id}")
    async def brand_logo(partner_id: uuid.UUID):
        with db_connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT logo, logo_type FROM public.partners WHERE id=%s", (partner_id,))
                row = cur.fetchone()
        if not row or not row["logo"]:
            raise HTTPException(status_code=404, detail="Not found")
        return Response(bytes(row["logo"]), media_type=row["logo_type"] or "image/png",
                        headers={"Cache-Control": "public, max-age=86400", "X-Content-Type-Options": "nosniff"})

    def render_api(method, path, body=None):
        if not (RENDER_KEY and RENDER_SERVICE):
            return None
        req = _ur.Request("https://api.render.com/v1/services/" + RENDER_SERVICE + path,
                          data=None if body is None else _json.dumps(body).encode(), method=method,
                          headers={"Authorization": "Bearer " + RENDER_KEY, "Accept": "application/json",
                                   "Content-Type": "application/json"})
        try:
            with _ur.urlopen(req, timeout=20) as r:
                raw = r.read().decode() or "{}"
                return _json.loads(raw) if raw.strip()[:1] in "{[" else {}
        except _ue.HTTPError as e:
            detail = e.read().decode()[:300]
            log.warning("Render API %s %s -> %s %s", method, path, e.code, detail)
            return {"_error": e.code, "_detail": detail}
        except Exception as exc:
            log.warning("Render API failed: %s", exc)
            return {"_error": 0, "_detail": str(exc)}

    def check_domain(domain):
        """Ask Render to verify the domain. Returns 'live', 'waiting' or 'manual'."""
        if not (RENDER_KEY and RENDER_SERVICE):
            return "manual"
        res = render_api("POST", f"/custom-domains/{domain}/verify")
        res = render_api("GET", f"/custom-domains/{domain}") or {}
        status = str(res.get("verificationStatus") or "").lower()
        return "live" if status == "verified" else "waiting"

    @app.get("/partner/brand", response_class=HTMLResponse)
    async def partner_brand_page(request: Request):
        user, partner, redirect = page_guard(request)
        if redirect:
            return redirect
        return templates.TemplateResponse(request=request, name="partner_brand.html", context={
            "user": user, "partner": partner, "cname": CNAME_TARGET, "auto": bool(RENDER_KEY and RENDER_SERVICE),
            "themes": THEMES,
            "msg": request.query_params.get("msg"), "err": request.query_params.get("err")})

    @app.post("/partner/brand")
    async def partner_brand_save(request: Request, brand_name: str = Form(""), brand_color: str = Form(""),
                                 theme: str = Form(""),
                                 support_whatsapp: str = Form(""), domain: str = Form(""),
                                 logo: UploadFile = File(None), remove_logo: str = Form("")):
        user, partner = need_partner(request)
        brand_name = brand_name.strip()[:60]
        color = brand_color.strip() if COLOR_RE.match(brand_color.strip()) else ""
        wa = "".join(ch for ch in support_whatsapp if ch.isdigit())[:16]
        domain = domain.strip().lower().removeprefix("https://").removeprefix("http://").split("/")[0]
        if domain and not DOMAIN_RE.match(domain):
            return RedirectResponse("/partner/brand?err=domain", status_code=303)
        if domain and (domain == MAIN_HOST or domain.endswith("." + MAIN_HOST)):
            return RedirectResponse("/partner/brand?err=domain", status_code=303)
        data, ctype = None, ""
        if logo is not None and logo.filename:
            data = await logo.read(MAX_LOGO + 1)
            ctype = (logo.content_type or "").lower()
            if len(data) > MAX_LOGO or ctype not in LOGO_TYPES:
                return RedirectResponse("/partner/brand?err=logo", status_code=303)
        from psycopg.errors import UniqueViolation
        try:
            with db_connect() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT domain FROM public.partners WHERE id=%s", (partner["id"],))
                    old_domain = (cur.fetchone()["domain"] or "").lower()
                    status_sql = ""
                    if domain != old_domain:
                        status_sql = ", domain_status=%s"
                    theme = theme if theme in THEMES else ""
                    params = [brand_name, color, wa, domain or None, theme]
                    if status_sql:
                        params.append("waiting" if domain else "")
                    # (status param comes after theme in the SQL above)
                    sql = ("UPDATE public.partners SET brand_name=%s, brand_color=%s, support_whatsapp=%s, domain=%s, theme=%s"
                           + status_sql)
                    if data is not None:
                        sql += ", logo=%s, logo_type=%s, logo_version=logo_version+1"
                        params += [data, ctype]
                    elif remove_logo == "1":
                        sql += ", logo=NULL, logo_type='', logo_version=logo_version+1"
                    cur.execute(sql + " WHERE id=%s", params + [partner["id"]])
        except UniqueViolation:
            return RedirectResponse("/partner/brand?err=taken", status_code=303)
        if domain and domain != old_domain:
            if RENDER_KEY and RENDER_SERVICE:
                if old_domain:
                    render_api("DELETE", f"/custom-domains/{old_domain}")
                res = render_api("POST", "/custom-domains", {"name": domain}) or {}
                if res.get("_error") and res.get("_error") != 409:
                    log.warning("Render could not add %s: %s", domain, res.get("_detail"))
            log.info("Partner %s set domain %s", user["email"], domain)
        drop_brand_cache()
        return RedirectResponse("/partner/brand?msg=saved", status_code=303)

    @app.post("/partner/brand/check")
    async def partner_brand_check(request: Request):
        _user, partner = need_partner(request)
        if not partner.get("domain"):
            return RedirectResponse("/partner/brand", status_code=303)
        from starlette.concurrency import run_in_threadpool
        state = await run_in_threadpool(check_domain, partner["domain"])
        if state == "live":
            with db_connect() as conn:
                with conn.cursor() as cur:
                    cur.execute("UPDATE public.partners SET domain_status='live' WHERE id=%s", (partner["id"],))
            drop_brand_cache()
        return RedirectResponse("/partner/brand?msg=" + ("live" if state == "live" else state), status_code=303)

    @app.post("/resellers/{reseller_id}/partner/domain")
    async def admin_partner_domain(reseller_id: uuid.UUID, request: Request, state: str = Form("live")):
        require_admin(request)
        with db_connect() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE public.partners SET domain_status=%s WHERE user_id=%s AND domain IS NOT NULL",
                            ("live" if state == "live" else "waiting", reseller_id))
        drop_brand_cache()
        return RedirectResponse(f"/resellers/{reseller_id}?msg=saved#partner", status_code=303)

    def partner_login_url(partner):
        if partner and partner.get("domain") and partner.get("domain_status") == "live":
            return "https://" + partner["domain"] + "/login"
        return public_url.rstrip("/") + "/login"

    return {
        "partner_of": partner_of, "partner_info_for_admin": partner_info_for_admin, "summary": summary,
        "quote_new_seat": quote_new_seat, "add_seat": add_seat, "change_addons": change_addons,
        "cancel_seat": cancel_seat, "renew_all": renew_all, "seats": seats, "prices_of": prices_of,
    }
