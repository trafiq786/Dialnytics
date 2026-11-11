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


def prorate(monthly, today=None):
    """Price for the rest of this month, today included."""
    today = today or datetime.now(timezone.utc).date()
    days = calendar.monthrange(today.year, today.month)[1]
    left = (month_end(today) - today).days + 1
    return money(Decimal(monthly) * left / days), left


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
        today_cost, days_left = prorate(monthly)
        return {"monthly": monthly, "today": today_cost, "days_left": days_left, "company_count": n}

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
            (user_id, partner["id"], account_id, plan, addons, month_end(today)))
        label = PLANS[plan] + (" + " + ", ".join(ADDONS[a] for a in addons) if addons else "")
        post(cur, partner["id"], -q["today"], f"New user · {label} · {q['days_left']} days",
             user_id, f"seat:{user_id}:{today:%Y-%m}")
        apply_features(cur, user_id, plan, addons)
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
        cost, days_left = prorate(addons_price(prices, added)) if added else (Decimal("0"), 0)
        if cost:
            s = summary(cur, partner)
            if s["available"] < cost:
                raise HTTPException(status_code=402, detail=f"Not enough balance for these add-ons ({fmt(cost)} today).")
            today = datetime.now(timezone.utc).date()
            post(cur, partner["id"], -cost, "Add-on · " + ", ".join(ADDONS[a] for a in added) + f" · {days_left} days",
                 user_id, f"addon:{user_id}:{today:%Y-%m}:{'-'.join(added)}:{secrets.token_hex(3)}")
        cur.execute("UPDATE public.partner_seats SET addons=%s WHERE user_id=%s", (new_addons, user_id))
        apply_features(cur, user_id, seat["plan"], new_addons)
        return cost

    def cancel_seat(cur, partner, user_id):
        cur.execute("""UPDATE public.partner_seats SET active=false, cancelled_at=now()
            WHERE user_id=%s AND partner_id=%s AND active RETURNING user_id""", (user_id, partner["id"]))
        return cur.fetchone() is not None

    # ------------------------------------------------------------------ monthly renewal
    def renew_all(today=None):
        """On/after the 1st: charge every active seat whose paid period ended. Idempotent."""
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
                        label = PLANS[s["plan"]] + (" + add-ons" if s["addons"] else "")
                        post(cur, partner["id"], -monthly, f"Monthly · {s['name']} · {label} · {today:%b %Y}",
                             s["user_id"], f"seat:{s['user_id']}:{today:%Y-%m}")
                        cur.execute("UPDATE public.partner_seats SET paid_until=%s WHERE user_id=%s",
                                    (month_end(today), s["user_id"]))
                        done += 1
        if done:
            log.info("Partner renewal: %d seats charged", done)
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
            "user": user, "partner": partner, "s": s, "ledger": ledger, "seats": seat_rows, "fmt": fmt,
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

    return {
        "partner_of": partner_of, "partner_info_for_admin": partner_info_for_admin, "summary": summary,
        "quote_new_seat": quote_new_seat, "add_seat": add_seat, "change_addons": change_addons,
        "cancel_seat": cancel_seat, "renew_all": renew_all, "seats": seats, "prices_of": prices_of,
    }
