from fastapi import FastAPI, Request, Form, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from datetime import datetime, timedelta, date
from typing import Optional, List
import secrets
import hashlib
import os
import json
import urllib.request
import urllib.error
import bleach
import base64
import time
import psycopg
import uuid
from decimal import Decimal
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, KeepTogether
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT
from psycopg.rows import dict_row
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.exceptions import InvalidSignature

app = FastAPI(title="Dialnytics", version="1.1.0")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

app.mount("/static", StaticFiles(directory=os.path.join(FRONTEND_DIR, "static")), name="static")
MEDIA_DIR = os.path.join(BASE_DIR, "data", "media")
os.makedirs(MEDIA_DIR, exist_ok=True)
app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")
templates = Jinja2Templates(directory=os.path.join(FRONTEND_DIR, "templates"))

# ==================== CONFIG (Telnyx) ====================
def _load_env_file():
    env_path = os.path.join(BASE_DIR, ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

_load_env_file()

TELNYX_API_KEY = os.getenv("TELNYX_API_KEY", "")
TELNYX_CONNECTION_ID = os.getenv("TELNYX_CONNECTION_ID", "")
TELNYX_FROM_NUMBER = os.getenv("TELNYX_FROM_NUMBER", "")

# user email -> telephony credential id
telephony_creds = {}

# ==================== IN-MEMORY DB ====================
users_db = {}
sessions = {}
call_logs = []
contacts_db = {}
recordings_db = {}
voicemails_db = {}
campaigns_db = {}

def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 600000)
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, digest_hex = stored.split("$", 1)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
        if len(salt) != 16 or len(expected) != 32:
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 600000)
        return secrets.compare_digest(actual, expected)
    except (ValueError, TypeError, AttributeError):
        return False

users_db["admin@dialnytics.com"] = {
    "id": 1,
    "email": "admin@dialnytics.com",
    "name": "Admin",
    "password": hash_password(os.environ["ADMIN_PASSWORD"]),
    "role": "admin",
    "phone_number": "",
    "sip_username": "",
    "credential_id": "",
    "created_at": datetime.now().isoformat()
}
users_db["agent@dialnytics.com"] = {
    "id": 2,
    "email": "agent@dialnytics.com",
    "name": "Agent One",
    "password": hash_password(os.environ["AGENT_PASSWORD"]),
    "role": "user",
    "phone_number": "",
    "sip_username": "",
    "credential_id": "",
    "created_at": datetime.now().isoformat()
}

# Supabase PostgreSQL is the source of truth for users and sessions.
# Fail closed: never silently fall back to local JSON for production accounts.
DATABASE_URL = os.environ.get("DATABASE_URL", "")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is required for the database build")

def db_connect():
    return psycopg.connect(DATABASE_URL, row_factory=dict_row, connect_timeout=10)

def _db_user(row):
    return {
        "id": str(row["id"]), "email": row["email"], "name": row["name"],
        "password": row["password_hash"],
        "role": "admin" if row["role"] == "admin" else "user",
        "phone_number": row["phone_number"] or "",
        "sip_username": row["sip_username"] or "",
        "credential_id": row["credential_id"] or "",
        "plan_name": row["plan_name"] or "",
        "plan_start": row["plan_start"].isoformat() if row["plan_start"] else "",
        "plan_renewal": row["plan_renewal"].isoformat() if row["plan_renewal"] else "",
        "recording_premium": row["recording_premium"],
        "dnd_enabled": row["dnd_enabled"],
        "is_demo": bool(row.get("is_demo", False)),
        "trial_started_at": row["trial_started_at"].isoformat() if row.get("trial_started_at") else None,
        "trial_expires_at": row["trial_expires_at"].isoformat() if row.get("trial_expires_at") else None,
        "created_at": row["created_at"].isoformat() if row["created_at"] else "",
        "amount_paid": float(row["last_paid_amount"] or 0),
        "last_paid_amount": float(row["last_paid_amount"] or 0),
    }

def refresh_users():
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM public.dialnytics_users WHERE is_active = TRUE")
            data = {row["email"]: _db_user(row) for row in cur.fetchall()}
    users_db.clear()
    users_db.update(data)

def save_users():
    # All existing routes that modify user data call this function.
    # Use upserts in a transaction; do not delete users absent from memory.
    with db_connect() as conn:
        with conn.cursor() as cur:
            for email, u in users_db.items():
                cur.execute("""INSERT INTO public.dialnytics_users
                    (name,email,password_hash,role,phone_number,credential_id,sip_username,
                     plan_name,plan_start,plan_renewal,last_paid_amount,recording_premium,dnd_enabled,is_demo)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s::date,%s::date,%s,%s,%s,%s)
                    ON CONFLICT (email) DO UPDATE SET
                      name=EXCLUDED.name, password_hash=EXCLUDED.password_hash,
                      role=EXCLUDED.role, phone_number=EXCLUDED.phone_number,
                      credential_id=EXCLUDED.credential_id,sip_username=EXCLUDED.sip_username,
                      plan_name=EXCLUDED.plan_name,plan_start=EXCLUDED.plan_start,
                      plan_renewal=EXCLUDED.plan_renewal,
                      last_paid_amount=EXCLUDED.last_paid_amount,
                      recording_premium=EXCLUDED.recording_premium,dnd_enabled=EXCLUDED.dnd_enabled,
                      is_demo=EXCLUDED.is_demo
                    RETURNING id""", (
                        u.get("name", ""),email,u["password"],
                        "admin" if u.get("role")=="admin" else "agent",
                        u.get("phone_number"),u.get("credential_id"),u.get("sip_username"),
                        u.get("plan_name"),u.get("plan_start") or None,
                        u.get("plan_renewal") or None,u.get("last_paid_amount",u.get("amount_paid",0)),
                        bool(u.get("recording_premium",False)),bool(u.get("dnd_enabled",False)),bool(u.get("is_demo",False))))
                uid=cur.fetchone()["id"]
                u["id"]=str(uid)
                # Replace rather than accumulate stale caller-ID assignments.
                cur.execute("DELETE FROM public.caller_id_assignments WHERE user_id=%s AND phone_number IS DISTINCT FROM %s", (uid, u.get("phone_number") or None))
                if u.get("phone_number"):
                    cur.execute("""INSERT INTO public.caller_id_assignments(user_id,phone_number)
                        VALUES (%s,%s) ON CONFLICT(user_id,phone_number) DO NOTHING""",(uid,u["phone_number"]))

def load_users():
    refresh_users()
    # Seed only missing defaults; do not overwrite previously saved passwords.
    missing = [email for email in ("admin@dialnytics.com","agent@dialnytics.com") if email not in users_db]
    if missing:
        for email in missing:
            if email == "admin@dialnytics.com":
                users_db[email] = dict(DEFAULT_ADMIN)
            else:
                users_db[email] = dict(DEFAULT_AGENT)
        save_users()
        refresh_users()

DEFAULT_ADMIN = dict(users_db["admin@dialnytics.com"])
DEFAULT_AGENT = dict(users_db["agent@dialnytics.com"])
load_users()

class CallRequest(BaseModel):
    to_number: str

class CampaignCreate(BaseModel):
    name: str
    numbers: List[str]

def _terminate_user_inbound_calls(user_id):
    """End tracked Voice API inbound calls for a revoked user.

    Only server-verified Telnyx call_control_ids stored by the webhook are used.
    Failed provider requests are reported, not silently claimed successful.
    """
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""SELECT g.id, g.telnyx_call_id
                FROM public.incoming_call_groups g
                JOIN public.call_participants p ON p.group_id=g.id
                WHERE p.user_id=%s AND g.status IN ('ringing','answered')
                FOR UPDATE OF g""", (user_id,))
            active = cur.fetchall()
            if active:
                cur.execute("""UPDATE public.incoming_call_groups
                    SET status='ended', ended_at=NOW()
                    WHERE id=ANY(%s)""", ([r['id'] for r in active],))
                cur.execute("""UPDATE public.call_participants
                    SET status='cancelled' WHERE user_id=%s AND group_id=ANY(%s)""",
                    (user_id, [r['id'] for r in active]))
    results = {'tracked': len(active), 'hangup_sent': 0, 'hangup_failed': 0}
    for row in active:
        try:
            _telnyx_request('POST',
                f"/v2/calls/{row['telnyx_call_id']}/actions/hangup", {})
            results['hangup_sent'] += 1
        except Exception:
            import logging
            logging.exception('Carrier hangup failed for revoked user')
            results['hangup_failed'] += 1
    return results

def create_session(email: str) -> str:
    token = secrets.token_hex(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM public.dialnytics_users WHERE email=%s AND is_active=TRUE", (email,))
            row=cur.fetchone()
            if not row:
                raise HTTPException(status_code=401,detail="Account disabled")
            cur.execute("UPDATE public.user_sessions SET revoked_at=NOW() WHERE user_id=%s AND revoked_at IS NULL",(row["id"],))
            cur.execute("INSERT INTO public.user_sessions(user_id,token_hash,expires_at) VALUES(%s,%s,NOW()+INTERVAL '24 hours')",(row["id"],token_hash))
    # Browser session guard tears down local WebRTC calls. Voice API calls
    # tracked by incoming_call_groups are also terminated carrier-side.
    _terminate_user_inbound_calls(row['id'])
    return token

def revoke_session(token):
    if not token:
        return
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE public.user_sessions SET revoked_at=NOW() WHERE token_hash=%s",(hashlib.sha256(token.encode()).hexdigest(),))

def get_current_user(request: Request):
    token = request.cookies.get("session_token")
    if not token:
        return None
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""SELECT u.* FROM public.user_sessions s
                JOIN public.dialnytics_users u ON u.id=s.user_id
                WHERE s.token_hash=%s AND s.revoked_at IS NULL
                AND s.expires_at>NOW() AND u.is_active=TRUE""",(hashlib.sha256(token.encode()).hexdigest(),))
            row=cur.fetchone()
    if not row:
        return None
    user=_db_user(row)
    if user.get("is_demo") and (not user.get("trial_expires_at") or datetime.fromisoformat(user["trial_expires_at"]) <= datetime.now().astimezone()):
        revoke_session(token)
        return None
    users_db[user["email"]]=user
    return user

# Session heartbeat for browser-side immediate logout and WebRTC teardown.
# Database remains authoritative across workers and devices.
@app.get("/api/session/status")
async def session_status(request: Request):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"active": False}, status_code=401,
                            headers={"Cache-Control": "no-store"})
    return JSONResponse({"active": True, "user_id": user["id"]},
                        headers={"Cache-Control": "no-store"})

# ==================== ROUTES ====================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    user = get_current_user(request)
    if user:
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse(request=request, name="login.html")

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html")

@app.post("/login")
async def login(request: Request, email: str = Form(...), password: str = Form(...)):
    refresh_users()
    user = users_db.get(email.strip().lower())
    if not user or not verify_password(password, user["password"]):
        return templates.TemplateResponse(request=request, name="login.html", context={"error": "Invalid email or password"})
    if user.get("is_demo"):
        with db_connect() as conn:
            with conn.cursor() as cur:
                cur.execute("""UPDATE public.dialnytics_users
                    SET trial_started_at=COALESCE(trial_started_at,NOW()),
                        trial_expires_at=COALESCE(trial_expires_at,NOW()+INTERVAL '1 hour')
                    WHERE email=%s AND is_demo=TRUE RETURNING trial_expires_at""", (user["email"],))
                expires = cur.fetchone()["trial_expires_at"]
        if expires <= datetime.now().astimezone():
            return templates.TemplateResponse(request=request, name="login.html", context={"error": "Demo trial expired. Contact admin to upgrade."})
    token = create_session(user["email"])
    response = RedirectResponse(url="/dashboard", status_code=302)
    response.set_cookie(key="session_token", value=token, httponly=True, secure=True, samesite="lax", max_age=86400)
    return response

@app.get("/signup")
@app.post("/signup")
async def signup_disabled():
    return RedirectResponse(url="/login", status_code=302)

def get_telnyx_numbers():
    """Fetch all account-owned numbers, including paginated results."""
    if not TELNYX_API_KEY:
        raise HTTPException(status_code=503, detail="Telnyx API key not configured")
    numbers = []
    page = 1
    while page <= 30:
        response = _telnyx_request("GET", f"/v2/phone_numbers?page[number]={page}&page[size]=100")
        batch = response.get("data") or []
        if not isinstance(batch, list):
            raise HTTPException(status_code=502, detail="Invalid Telnyx numbers response")
        for item in batch:
            number = item.get("phone_number")
            if number:
                numbers.append(number)
        meta = response.get("meta") or {}
        total_pages = meta.get("total_pages")
        if total_pages is not None:
            if page >= int(total_pages):
                break
        elif len(batch) < 100:
            break
        page += 1
    return sorted(set(numbers))


def number_assignments(number):
    return [u for u in users_db.values() if u.get("phone_number") == number]


@app.get("/api/admin/caller-ids")
async def admin_caller_ids(request: Request):
    admin = get_current_user(request)
    if not admin or admin.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    numbers = get_telnyx_numbers()
    return JSONResponse({"numbers": [
        {"number": n, "assigned_to": [
            {"email": u.get("email", ""), "last_name": (u.get("name") or "").strip().split()[-1] if (u.get("name") or "").strip() else "Unknown"}
            for u in number_assignments(n)]}
        for n in numbers]})



# Admin-only customer management and invoice features.
def require_admin(request):
    actor = get_current_user(request)
    if not actor or actor.get('role') != 'admin':
        raise HTTPException(status_code=403, detail='Admin access required')
    return actor


def _customer_data(email):
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""SELECT u.id,u.name,u.email,u.phone_number,u.plan_name,
                u.plan_start,u.plan_renewal,u.created_at,u.is_active,u.is_demo,
                u.last_paid_amount,u.recording_premium,u.contact_name,u.contact_phone,
                u.contact_address,u.customer_notes,
                (SELECT count(*) FROM public.calls c WHERE c.user_id=u.id AND c.created_at >= date_trunc('month',now())) AS calls_month,
                (SELECT COALESCE(sum(c.duration_seconds),0) FROM public.calls c WHERE c.user_id=u.id AND c.created_at >= date_trunc('month',now())) AS talk_seconds,
                (SELECT COALESCE(sum(p.amount_pkr),0) FROM public.payments p WHERE p.user_id=u.id AND p.status='paid') AS collected,
                (SELECT max(p.paid_at) FROM public.payments p WHERE p.user_id=u.id AND p.status='paid') AS last_payment_at
                FROM public.dialnytics_users u WHERE lower(u.email)=lower(%s)""", (email,))
            row=cur.fetchone()
            if not row: raise HTTPException(404, 'Customer not found')
            return dict(row)


@app.get('/customers', response_class=HTMLResponse)
async def customers_page(request: Request):
    admin=require_admin(request)
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""SELECT u.name,u.email,u.plan_name,u.phone_number,u.last_paid_amount,
                u.plan_renewal,u.is_active,u.is_demo,u.created_at,
                (SELECT count(*) FROM public.caller_id_assignments a WHERE a.user_id=u.id) AS numbers
                FROM public.dialnytics_users u WHERE u.role <> 'admin' ORDER BY u.created_at DESC""")
            customers=cur.fetchall()
    return templates.TemplateResponse(request=request,name='customers.html',context={'user':admin,'customers':customers,'today':date.today()})


@app.get('/customers/{email}', response_class=HTMLResponse)
async def customer_detail(request:Request,email:str):
    admin=require_admin(request)
    c=_customer_data(email)
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT amount_pkr,status,paid_at,renewal_date FROM public.payments WHERE user_id=%s ORDER BY paid_at DESC NULLS LAST LIMIT 100',(c['id'],))
            payments=cur.fetchall()
    return templates.TemplateResponse(request=request,name='customer_detail.html',context={'user':admin,'customer':c,'payments':payments})


@app.post('/customers/{email}/update')
async def customer_update(request:Request,email:str,name:str=Form(...),plan_name:str=Form(''),
    plan_renewal:str=Form(''),contact_name:str=Form(''),contact_phone:str=Form(''),
    contact_address:str=Form(''),customer_notes:str=Form(''),is_active:str=Form('true'),
    new_password:str=Form(''),monthly_amount:int=Form(0)):
    require_admin(request)
    if monthly_amount<0: raise HTTPException(422,'Amount must not be negative')
    if plan_renewal:
        try: date.fromisoformat(plan_renewal)
        except ValueError: raise HTTPException(422,'Invalid renewal date')
    if new_password and len(new_password)<12: raise HTTPException(422,'Password must be at least 12 characters')
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""UPDATE public.dialnytics_users SET name=%s,plan_name=%s,
                plan_renewal=%s::date,contact_name=%s,contact_phone=%s,contact_address=%s,
                customer_notes=%s,is_active=%s,last_paid_amount=%s
                WHERE lower(email)=lower(%s) AND role<>'admin' RETURNING id""",
                (name.strip()[:200],plan_name.strip()[:120],plan_renewal or None,contact_name.strip()[:200],
                contact_phone.strip()[:60],contact_address.strip()[:500],customer_notes.strip()[:3000],
                is_active=='true',monthly_amount,email))
            row=cur.fetchone()
            if not row: raise HTTPException(404,'Customer not found')
            if new_password:
                cur.execute('UPDATE public.dialnytics_users SET password_hash=%s WHERE id=%s',(hash_password(new_password),row['id']))
            if is_active!='true':
                cur.execute('UPDATE public.user_sessions SET revoked_at=NOW() WHERE user_id=%s AND revoked_at IS NULL',(row['id'],))
    refresh_users()
    return RedirectResponse('/customers/'+email+'?saved=1',status_code=303)


@app.post('/customers/{email}/payment')
async def customer_payment(request:Request,email:str,amount:int=Form(...),method:str=Form('Manual'),reference:str=Form('')):
    require_admin(request)
    if amount<=0: raise HTTPException(422,'Amount must be positive')
    c=_customer_data(email)
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""INSERT INTO public.payments(user_id,amount_pkr,status,paid_at,renewal_date)
                VALUES(%s,%s,'paid',NOW(),%s)""",(c['id'],amount,c['plan_renewal']))
            cur.execute('UPDATE public.dialnytics_users SET last_paid_amount=%s WHERE id=%s',(amount,c['id']))
    refresh_users()
    return RedirectResponse('/customers/'+email+'?payment=1',status_code=303)


def _invoice_row(invoice_id):
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT * FROM public.dialnytics_invoices WHERE id=%s',(invoice_id,))
            row=cur.fetchone()
            if not row: raise HTTPException(404,'Invoice not found')
            cur.execute('SELECT * FROM public.dialnytics_invoice_items WHERE invoice_id=%s ORDER BY position',(invoice_id,))
            return dict(row),cur.fetchall()


@app.get('/invoices',response_class=HTMLResponse)
async def invoices_page(request:Request):
    admin=require_admin(request)
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT * FROM public.dialnytics_invoices ORDER BY created_at DESC LIMIT 300')
            invoices=cur.fetchall()
    return templates.TemplateResponse(request=request,name='invoices.html',context={'user':admin,'invoices':invoices})


@app.get('/invoices/new',response_class=HTMLResponse)
async def invoice_new(request:Request,customer:str=''):
    admin=require_admin(request)
    c=_customer_data(customer) if customer else None
    return templates.TemplateResponse(request=request,name='invoice_form.html',context={'user':admin,'customer':c,'invoice':None,'items':[]})


@app.post('/invoices/new')
async def invoice_create(request:Request,customer_email:str=Form(...),issue_date:str=Form(...),due_date:str=Form(...),
    description:List[str]=Form(...),qty:List[int]=Form(...),unit_price:List[int]=Form(...),
    discount:int=Form(0),tax_percent:int=Form(0),notes:str=Form(''),terms:str=Form('Payment is due by the due date shown.'),
    action:str=Form('save')):
    require_admin(request)
    c=_customer_data(customer_email)
    if not description or len(description)>30 or len(description)!=len(qty) or len(qty)!=len(unit_price):
        raise HTTPException(422,'Invalid invoice items')
    try:
        issued=date.fromisoformat(issue_date); due=date.fromisoformat(due_date)
    except ValueError: raise HTTPException(422,'Invalid dates')
    if any(q<=0 or q>100000 or price<0 or price>100000000 for q,price in zip(qty,unit_price)) or discount<0 or not 0<=tax_percent<=100:
        raise HTTPException(422,'Invalid quantities, discount or tax')
    subtotal=sum(q*p for q,p in zip(qty,unit_price))
    taxable=max(0,subtotal-discount)
    tax_amount=round(taxable*tax_percent/100)
    total=taxable+tax_amount
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT nextval('public.dialnytics_invoice_seq') AS n")
            number=f'INV-{issued.year}-{cur.fetchone()["n"]:04d}'
            cur.execute("""INSERT INTO public.dialnytics_invoices
                (invoice_number,customer_id,customer_name,customer_email,contact_phone,contact_address,
                 issue_date,due_date,notes,terms,subtotal_pkr,discount_pkr,tax_percent,tax_pkr,total_pkr,status)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'draft') RETURNING id""",
                (number,c['id'],c['name'],c['email'],c.get('contact_phone') or '',c.get('contact_address') or '',
                issued,due,notes[:3000],terms[:3000],subtotal,discount,tax_percent,tax_amount,total))
            invoice_id=cur.fetchone()['id']
            for i,(d,q,price) in enumerate(zip(description,qty,unit_price)):
                cur.execute("""INSERT INTO public.dialnytics_invoice_items(invoice_id,position,description,qty,unit_price_pkr,amount_pkr)
                    VALUES(%s,%s,%s,%s,%s,%s)""",(invoice_id,i,d.strip()[:500],q,price,q*price))
    return RedirectResponse('/invoices/'+str(invoice_id),status_code=303)


@app.get('/invoices/{invoice_id}',response_class=HTMLResponse)
async def invoice_detail(request:Request,invoice_id:uuid.UUID):
    admin=require_admin(request)
    invoice,items=_invoice_row(invoice_id)
    return templates.TemplateResponse(request=request,name='invoice_detail.html',context={'user':admin,'invoice':invoice,'items':items})


@app.post('/invoices/{invoice_id}/status')
async def invoice_status(request:Request,invoice_id:uuid.UUID,status:str=Form(...)):
    require_admin(request)
    if status not in ('draft','sent','paid','void'): raise HTTPException(422,'Invalid invoice status')
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute('UPDATE public.dialnytics_invoices SET status=%s,updated_at=NOW() WHERE id=%s RETURNING id',(status,invoice_id))
            if not cur.fetchone(): raise HTTPException(404,'Invoice not found')
    # Invoice status is not itself a cash receipt: avoid double counting payments.
    return RedirectResponse('/invoices/'+str(invoice_id),status_code=303)


@app.post('/invoices/{invoice_id}/delete')
async def invoice_delete(request:Request,invoice_id:uuid.UUID):
    require_admin(request)
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM public.dialnytics_invoices WHERE id=%s AND status IN ('draft','void')",(invoice_id,))
            if cur.rowcount==0: raise HTTPException(409,'Only draft or void invoices can be deleted')
    return RedirectResponse('/invoices',status_code=303)


@app.post('/invoices/{invoice_id}/duplicate')
async def invoice_duplicate(request:Request,invoice_id:uuid.UUID):
    require_admin(request)
    inv,items=_invoice_row(invoice_id)
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT nextval('public.dialnytics_invoice_seq') AS n")
            number=f'INV-{date.today().year}-{cur.fetchone()["n"]:04d}'
            cur.execute("""INSERT INTO public.dialnytics_invoices
                (invoice_number,customer_id,customer_name,customer_email,contact_phone,contact_address,issue_date,due_date,
                 notes,terms,subtotal_pkr,discount_pkr,tax_percent,tax_pkr,total_pkr,status)
                VALUES(%s,%s,%s,%s,%s,%s,CURRENT_DATE,CURRENT_DATE+INTERVAL '3 days',%s,%s,%s,%s,%s,%s,%s,'draft') RETURNING id""",
                (number,inv['customer_id'],inv['customer_name'],inv['customer_email'],inv['contact_phone'],inv['contact_address'],
                inv['notes'],inv['terms'],inv['subtotal_pkr'],inv['discount_pkr'],inv['tax_percent'],inv['tax_pkr'],inv['total_pkr']))
            new_id=cur.fetchone()['id']
            for item in items:
                cur.execute("""INSERT INTO public.dialnytics_invoice_items(invoice_id,position,description,qty,unit_price_pkr,amount_pkr)
                    VALUES(%s,%s,%s,%s,%s,%s)""",(new_id,item['position'],item['description'],item['qty'],item['unit_price_pkr'],item['amount_pkr']))
    return RedirectResponse('/invoices/'+str(new_id),status_code=303)


@app.get('/invoices/{invoice_id}/pdf')
async def invoice_pdf(request:Request,invoice_id:uuid.UUID):
    require_admin(request)
    inv,items=_invoice_row(invoice_id)
    buffer=BytesIO()
    doc=SimpleDocTemplate(buffer,pagesize=(595,842),rightMargin=42,leftMargin=42,topMargin=40,bottomMargin=40)
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='DialTitle',parent=styles['Title'],fontSize=22,textColor=colors.HexColor('#111b37'),spaceAfter=16))
    styles.add(ParagraphStyle(name='DialSmall',parent=styles['Normal'],fontSize=9,leading=14))
    def esc(v):
        import html
        return html.escape(str(v or ''))
    story=[Paragraph('DIALNYTICS  |  INVOICE',styles['DialTitle']),
        Paragraph('Invoice: '+esc(inv['invoice_number'])+'  |  Status: '+esc(inv['status']).upper(),styles['DialSmall']),Spacer(1,18),
        Paragraph('<b>BILL TO</b><br/>'+esc(inv['customer_name'])+'<br/>'+esc(inv['customer_email'])+'<br/>'+esc(inv['contact_phone']),styles['DialSmall']),Spacer(1,14),
        Paragraph('Issued: '+str(inv['issue_date'])+'    Due: '+str(inv['due_date']),styles['DialSmall']),Spacer(1,18)]
    rows=[['DESCRIPTION','QTY','UNIT PRICE','AMOUNT']]
    for item in items:
        rows.append([Paragraph(esc(item['description']),styles['DialSmall']),str(item['qty']),f"PKR {item['unit_price_pkr']:,.0f}",f"PKR {item['amount_pkr']:,.0f}"])
    table=Table(rows,colWidths=[275,45,95,95],repeatRows=1,hAlign='LEFT')
    table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#111b37')),
        ('TEXTCOLOR',(0,0),(-1,0),colors.white),('BOTTOMPADDING',(0,0),(-1,0),11),('TOPPADDING',(0,0),(-1,0),11),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f2f6fa')]),
        ('VALIGN',(0,0),(-1,-1),'TOP'),('BOTTOMPADDING',(0,1),(-1,-1),10),('TOPPADDING',(0,1),(-1,-1),10)]))
    story.extend([table,Spacer(1,20),Paragraph(f"Subtotal: PKR {inv['subtotal_pkr']:,.0f}",styles['DialSmall']),
        Paragraph(f"Discount: PKR {inv['discount_pkr']:,.0f} | Tax ({inv['tax_percent']}%): PKR {inv['tax_pkr']:,.0f}",styles['DialSmall']),
        Spacer(1,10),Paragraph(f"<b>AMOUNT DUE: PKR {inv['total_pkr']:,.0f}</b>",styles['Heading2']),Spacer(1,20),
        Paragraph('<b>HOW TO PAY</b><br/>Contact us for payment.',styles['DialSmall']),Spacer(1,14),
        Paragraph('<b>NOTES</b><br/>'+esc(inv['notes']),styles['DialSmall']),Spacer(1,10),
        Paragraph('<b>TERMS</b><br/>'+esc(inv['terms']),styles['DialSmall'])])
    doc.build(story)
    return Response(buffer.getvalue(),media_type='application/pdf',headers={'Content-Disposition':f'attachment; filename="{inv["invoice_number"]}.pdf"','Cache-Control':'private, no-store'})

@app.get("/users", response_class=HTMLResponse)
async def users_page(request: Request):
    user = get_current_user(request)
    if not user or user.get("role") != "admin":
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse(request=request, name="users.html", context={
        "user": user,
        "users": list(users_db.values()),
        "error": request.query_params.get("error"),
        "created": request.query_params.get("created"),
        "deleted": request.query_params.get("deleted"),
    })

@app.post("/users")
async def create_user(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    phone_number: str = Form(...),
    plan_name: str = Form("1 USER ACCOUNT"),
    plan_start: str = Form(""),
    plan_renewal: str = Form(""),
    is_demo: bool = Form(False),
):
    user = get_current_user(request)
    if not user or user.get("role") != "admin":
        return RedirectResponse(url="/login", status_code=302)
    email = email.strip().lower()
    phone_number = phone_number.strip()
    refresh_users()
    if email in users_db:
        return RedirectResponse(url="/users?error=Email+already+exists", status_code=302)
    if not phone_number.startswith("+"):
        return RedirectResponse(url="/users?error=Number+must+start+with+%2B", status_code=302)
    # Server-side validation: the chosen caller ID must be owned by this Telnyx account.
    try:
        owned_numbers = get_telnyx_numbers()
    except HTTPException:
        return RedirectResponse(url="/users?error=Unable+to+verify+Telnyx+numbers", status_code=302)
    if phone_number not in owned_numbers:
        return RedirectResponse(url="/users?error=Caller+ID+not+in+Telnyx+account", status_code=302)
    assigned = number_assignments(phone_number)
    form_data = await request.form()
    if assigned and form_data.get("confirm_shared_number") != "yes":
        return RedirectResponse(url="/users?error=Confirm+Caller+ID+transfer", status_code=302)
    # Transfer ownership, never share a caller ID. Lock the number's existing
    # assignment inside PostgreSQL to avoid races with other admin requests.
    if assigned:
        with db_connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (phone_number,))
                cur.execute("""UPDATE public.dialnytics_users SET phone_number=NULL
                    WHERE id IN (SELECT user_id FROM public.caller_id_assignments WHERE phone_number=%s)""", (phone_number,))
                cur.execute("DELETE FROM public.caller_id_assignments WHERE phone_number=%s", (phone_number,))
        refresh_users()
    try:
        amount_paid = int((await request.form()).get("amount_paid", "0") or 0)
        if amount_paid < 0: raise ValueError()
    except ValueError:
        return RedirectResponse(url="/users?error=Invalid+PKR+amount", status_code=302)
    payment_status = str((await request.form()).get("payment_status", "paid"))
    if payment_status not in ("paid", "partial", "unpaid"):
        payment_status = "unpaid"
    if is_demo:
        amount_paid = 0
        payment_status = "unpaid"
    if payment_status == "unpaid": amount_paid = 0
    users_db[email] = {
        "id": len(users_db) + 1,
        "email": email,
        "name": name.strip(),
        "password": hash_password(password),
        "role": "user",
        "phone_number": phone_number,
        "sip_username": "",
        "credential_id": "",
        "plan_name": (plan_name or "1 USER ACCOUNT").strip(),
        "plan_start": plan_start or datetime.now().date().isoformat(),
        "plan_renewal": plan_renewal or (datetime.now() + timedelta(days=30)).date().isoformat(),
        "recording_premium": False,
        "is_demo": is_demo,
        "last_paid_amount": amount_paid if amount_paid else 0,
        "payment_status": payment_status,
        "payments": ([{"amount": amount_paid, "date": datetime.now().date().isoformat(), "type": "initial"}] if amount_paid else []),
        "created_at": datetime.now().isoformat(),
    }
    save_users()
    if amount_paid:
        with db_connect() as conn:
            with conn.cursor() as cur:
                cur.execute("""INSERT INTO public.payments(user_id,amount_pkr,status,paid_at,renewal_date)
                    SELECT id,%s,%s,CASE WHEN %s='paid' THEN NOW() ELSE NULL END,%s::date
                    FROM public.dialnytics_users WHERE email=%s""",(
                    amount_paid, "pending" if payment_status == "unpaid" else payment_status,
                    payment_status,users_db[email]["plan_renewal"],email))
    try:
        _ensure_credential(email)
    except Exception:
        pass
    return RedirectResponse(url="/users?created=1", status_code=302)


@app.post("/users/delete")
async def delete_user(request: Request, email: str = Form(...)):
    admin = get_current_user(request)
    if not admin or admin.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    email = email.strip().lower()
    if email == admin["email"]:
        return RedirectResponse(url="/users?error=Cannot+delete+your+own+account", status_code=303)
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id,role FROM public.dialnytics_users WHERE email=%s AND is_active=TRUE FOR UPDATE", (email,))
            target = cur.fetchone()
            if not target or target["role"] == "admin":
                return RedirectResponse(url="/users?error=User+not+found+or+protected", status_code=303)
            cur.execute("UPDATE public.dialnytics_users SET is_active=FALSE,phone_number=NULL WHERE id=%s", (target["id"],))
            cur.execute("DELETE FROM public.caller_id_assignments WHERE user_id=%s", (target["id"],))
            cur.execute("UPDATE public.user_sessions SET revoked_at=NOW() WHERE user_id=%s AND revoked_at IS NULL", (target["id"],))
    try:
        _terminate_user_inbound_calls(target["id"])
    except Exception:
        import logging
        logging.exception("Unable to terminate all active incoming calls on user deletion")
    refresh_users()
    return RedirectResponse(url="/users?deleted=1", status_code=303)

@app.post("/users/repayment")
async def record_repayment(request: Request, email: str = Form(...), amount: int = Form(...), renewal_date: str = Form("")):
    admin = get_current_user(request)
    if not admin or admin.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    target = users_db.get(email.strip().lower())
    if not target: raise HTTPException(status_code=404, detail="User not found")
    if amount <= 0: raise HTTPException(status_code=400, detail="Amount must be positive")
    if renewal_date:
        try: date.fromisoformat(renewal_date)
        except ValueError: raise HTTPException(status_code=400, detail="Invalid renewal date")
        target["plan_renewal"] = renewal_date
    else:
        old = date.fromisoformat(target.get("plan_renewal") or date.today().isoformat())
        target["plan_renewal"] = (max(old, date.today()) + timedelta(days=30)).isoformat()
    target.setdefault("payments", []).append({"amount": amount, "date": date.today().isoformat(), "type": "renewal"})
    target["last_paid_amount"] = amount
    target["payment_status"] = "paid"
    save_users()
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""INSERT INTO public.payments(user_id,amount_pkr,status,paid_at,renewal_date)
                SELECT id,%s,'paid',NOW(),%s::date FROM public.dialnytics_users WHERE email=%s""",
                (amount,target["plan_renewal"],email.strip().lower()))
    return RedirectResponse(url="/dashboard?period=month", status_code=303)

@app.post("/users/plan")
async def update_user_plan(
    request: Request,
    email: str = Form(...),
    plan_name: str = Form(...),
    plan_start: str = Form(...),
    plan_renewal: str = Form(...),
):
    admin = get_current_user(request)
    if not admin or admin.get("role") != "admin":
        return RedirectResponse(url="/login", status_code=302)
    target = users_db.get(email.strip().lower())
    if not target:
        return RedirectResponse(url="/users?error=User+not+found", status_code=302)
    target["plan_name"] = plan_name.strip() or "1 USER ACCOUNT"
    target["plan_start"] = plan_start
    target["plan_renewal"] = plan_renewal
    save_users()
    return RedirectResponse(url="/users?created=1", status_code=302)

@app.post("/users/extend")
async def extend_user_plan(request: Request, email: str = Form(...), days: int = Form(30)):
    admin = get_current_user(request)
    if not admin or admin.get("role") != "admin":
        return RedirectResponse(url="/login", status_code=302)
    target = users_db.get(email.strip().lower())
    if not target:
        return RedirectResponse(url="/users?error=User+not+found", status_code=302)
    today = datetime.now().date()
    raw = target.get("plan_renewal") or today.isoformat()
    try:
        current = datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        current = today
    base = current if current > today else today
    target["plan_renewal"] = (base + timedelta(days=max(1, int(days)))).isoformat()
    if not target.get("plan_start"):
        target["plan_start"] = today.isoformat()
    if not target.get("plan_name"):
        target["plan_name"] = "1 USER ACCOUNT"
    save_users()
    return RedirectResponse(url="/users?created=1", status_code=302)

@app.post("/users/recording")
async def toggle_recording(request: Request, email: str = Form(...)):
    admin = get_current_user(request)
    if not admin or admin.get("role") != "admin":
        return RedirectResponse(url="/login", status_code=302)
    target = users_db.get(email.strip().lower())
    if not target:
        return RedirectResponse(url="/users?error=User+not+found", status_code=302)
    target["recording_premium"] = not bool(target.get("recording_premium"))
    save_users()
    return RedirectResponse(url="/users?created=1", status_code=302)

def has_recording(user):
    return user.get("role") == "admin" or bool(user.get("recording_premium"))

def plan_status(user):
    if user.get("is_demo"):
        expires = user.get("trial_expires_at")
        remaining = max(0, int((datetime.fromisoformat(expires) - datetime.now().astimezone()).total_seconds())) if expires else 3600
        return {"plan_name":"1 HOUR DEMO", "plan_start":user.get("trial_started_at") or "First login", "plan_renewal":expires or "Not started", "days_left":0 if remaining > 0 else -1, "payment_open":False, "trial_seconds_left":remaining}
    start = user.get("plan_start") or (user.get("created_at") or "")[:10] or datetime.now().date().isoformat()
    renewal = user.get("plan_renewal") or (datetime.now() + timedelta(days=30)).date().isoformat()
    try:
        days = (datetime.strptime(renewal, "%Y-%m-%d").date() - datetime.now().date()).days
    except ValueError:
        days = 0
    return {
        "plan_name": user.get("plan_name") or "1 USER ACCOUNT",
        "plan_start": start,
        "plan_renewal": renewal,
        "days_left": days,
        "payment_open": days <= 3,
    }

templates.env.globals["has_recording"] = has_recording
templates.env.globals["plan_status"] = plan_status

@app.get("/logout")
async def logout(request: Request):
    token = request.cookies.get("session_token")
    revoke_session(token)
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("session_token")
    return response

def _count_contacts(user_id):
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT COUNT(*) AS n FROM public.dialnytics_contacts WHERE user_id=%s',(user_id,))
            return cur.fetchone()['n']

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    period = request.query_params.get("period", "today")
    if period not in ("today", "week", "month"): period = "today"
    today = date.today()
    beginning = today if period == "today" else (today - timedelta(days=today.weekday()) if period == "week" else today.replace(day=1))
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""SELECT c.status,c.duration_seconds AS duration,c.created_at
                FROM public.calls c WHERE c.user_id=%s AND c.created_at >= %s
                ORDER BY c.created_at DESC""", (user["id"], beginning))
            user_calls = cur.fetchall()
    total_calls = len(user_calls)
    answered = len([c for c in user_calls if c.get("status") in ("answered", "completed", "active")])
    failed = len([c for c in user_calls if c.get("status") not in ("answered", "completed", "active")])
    answer_rate = f"{int((answered/total_calls)*100)}%" if total_calls else "0%"
    talk = [int(c.get("duration") or 0) for c in user_calls]
    avg = int(sum(talk) / len(talk)) if talk else 0
    avg_talk = f"{avg // 60}:{avg % 60:02d}"
    revenue = 0
    renewals = []
    refresh_users()
    if user.get("role") == "admin":
        for account in users_db.values():
            if account.get("role") == "admin": continue
            try:
                remaining = (date.fromisoformat(account.get("plan_renewal", "")) - today).days
            except ValueError:
                continue
            if 0 <= remaining <= 7:
                renewals.append({"name": account.get("name"), "email": account.get("email"), "renewal": account.get("plan_renewal"), "amount": account.get("last_paid_amount", 0), "days": remaining})
        renewals.sort(key=lambda r: r["days"])
        with db_connect() as conn:
            with conn.cursor() as cur:
                cur.execute("""SELECT COALESCE(SUM(amount_pkr),0) AS total FROM public.payments
                    WHERE status='paid' AND paid_at >= date_trunc('month',NOW())""")
                revenue = float(cur.fetchone()["total"])
    return templates.TemplateResponse(request=request, name="dashboard.html", context={
        "period": period, "revenue": revenue, "renewals": renewals,
        "user": user, "total_calls": total_calls, "answer_rate": answer_rate,
        "avg_talk_time": avg_talk, "contacts_count": _count_contacts(user["id"]),
        "followups": 0, "failed_calls": failed, "answered_calls": answered,
        "recordings_count": len(recordings_db.get(user["email"], [])),
        "campaigns_count": len(campaigns_db.get(user["email"], []))
    })

@app.get("/dialer", response_class=HTMLResponse)
async def dialer_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    return RedirectResponse(url="/dashboard", status_code=302)

def _telnyx_request(method: str, path: str, body: dict = None):
    if not TELNYX_API_KEY:
        raise HTTPException(status_code=500, detail="TELNYX_API_KEY missing")
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        "https://api.telnyx.com" + path,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {TELNYX_API_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode().strip()
            if not raw:
                return {}
            if raw.startswith("{") or raw.startswith("["):
                return json.loads(raw)
            return {"raw": raw.strip('"')}
    except urllib.error.HTTPError as e:
        detail = e.read().decode()
        raise HTTPException(status_code=502, detail=f"Telnyx error: {detail}")

def _ensure_credential(email: str) -> str:
    user = users_db.get(email) or {}
    if user.get("credential_id"):
        return user["credential_id"]
    created = _telnyx_request("POST", "/v2/telephony_credentials", {
        "connection_id": TELNYX_CONNECTION_ID,
        "name": f"dialnytics-{email}"[:60],
        "tag": "dialnytics",
    })
    data = created.get("data", {})
    cred_id = data.get("id")
    if not cred_id:
        raise HTTPException(status_code=502, detail="Could not create telephony credential")
    if email in users_db:
        users_db[email]["credential_id"] = cred_id
        users_db[email]["sip_username"] = data.get("sip_username", "")
        save_users()
    return cred_id

@app.get("/api/webrtc-token")
async def webrtc_token(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if user.get("role") != "admin" and plan_status(user)["days_left"] < 0:
        raise HTTPException(status_code=402, detail="Subscription expired")
    cred_id = _ensure_credential(user["email"])
    token_resp = _telnyx_request("POST", f"/v2/telephony_credentials/{cred_id}/token")
    token = None
    if isinstance(token_resp, dict):
        token = token_resp.get("raw") or token_resp.get("data")
        if isinstance(token, dict):
            token = token.get("token")
    if not token or not isinstance(token, str):
        raise HTTPException(status_code=502, detail="Token generation failed")
    return JSONResponse({
        "token": token,
        "from_number": user.get("phone_number") or TELNYX_FROM_NUMBER,
    })

@app.get("/api/call-state")
async def call_state(request: Request, id: str = ""):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    call_id = id.strip()
    if not call_id or len(call_id) > 80:
        return JSONResponse({"ended": False})
    try:
        payload = _telnyx_request("GET", "/v2/calls/" + call_id)
    except HTTPException as exc:
        missing = "404" in str(exc.detail) or "not found" in str(exc.detail).lower() or "90015" in str(exc.detail)
        return JSONResponse({"ended": False, "missing": missing})
    info = payload.get("data") or {}
    if info.get("is_alive") is False:
        cause = str(info.get("hangup_cause") or "").lower()
        reason = "Call ended"
        if "busy" in cause:
            reason = "Busy"
        elif "reject" in cause or "decline" in cause:
            reason = "Call declined"
        elif "timeout" in cause or "no_answer" in cause or "unallocated" in cause:
            reason = "No answer"
        return JSONResponse({"ended": True, "reason": reason})
    return JSONResponse({"ended": False, "alive": True})

@app.post("/api/call-log")
async def log_webrtc_call(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    data = await request.json()
    call_entry = {
        "id": secrets.token_hex(8),
        "user_email": user["email"],
        "from_number": user.get("phone_number") or TELNYX_FROM_NUMBER,
        "to_number": data.get("to_number"),
        "status": data.get("status", "initiated"),
        "duration": 0,
        "created_at": datetime.now().isoformat(),
        "recording_url": None,
    }
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""INSERT INTO public.calls
                (user_id,from_number,to_number,direction,status,created_at)
                VALUES (%s,%s,%s,'outgoing',%s,NOW()) RETURNING id""",
                (user["id"],call_entry["from_number"],call_entry["to_number"],call_entry["status"]))
            call_entry["id"] = str(cur.fetchone()["id"])
    return JSONResponse({"success": True, "call": call_entry, "id": call_entry["id"]})

@app.post("/api/call-log/{call_id}")
async def update_call_log(call_id: str, request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    data = await request.json()
    try:
        call_uuid = uuid.UUID(call_id)
    except ValueError:
        raise HTTPException(status_code=404,detail="Call not found")
    duration = max(0,int(data.get("duration") or 0))
    status = str(data.get("status") or "initiated")[:60]
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""UPDATE public.calls SET duration_seconds=%s,status=%s
                WHERE id=%s AND user_id=%s RETURNING id""",
                (duration,status,call_uuid,user["id"]))
            if not cur.fetchone():
                raise HTTPException(status_code=404,detail="Call not found")
    return JSONResponse({"success":True})

@app.post("/api/call")
async def make_call(request: Request, data: CallRequest):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    call_id = secrets.token_hex(8)
    status = "initiated"
    note = "Simulation mode"

    # ========== TELNYX REAL CALL (uncomment when keys ready) ==========
    # if TELNYX_API_KEY and TELNYX_CONNECTION_ID:
    #     try:
    #         import telnyx
    #         telnyx.api_key = TELNYX_API_KEY
    #         call = telnyx.Call.create(
    #             connection_id=TELNYX_CONNECTION_ID,
    #             to=data.to_number,
    #             from_=TELNYX_FROM_NUMBER or user["phone_number"],
    #             # answering_machine_detection="detect",
    #         )
    #         call_id = call.call_control_id
    #         status = "initiated"
    #         note = "Real Telnyx call"
    #     except Exception as e:
    #         return JSONResponse({"success": False, "message": str(e)})
    # ================================================================

    call_entry = {
        "id": call_id, "user_email": user["email"],
        "from_number": user["phone_number"], "to_number": data.to_number,
        "status": status, "duration": 0,
        "created_at": datetime.now().isoformat(),
        "recording_url": None
    }
    call_logs.append(call_entry)

    # Simulate a recording entry
    if user["email"] not in recordings_db:
        recordings_db[user["email"]] = []
    recordings_db[user["email"]].append({
        "id": secrets.token_hex(6),
        "call_id": call_id,
        "to_number": data.to_number,
        "duration": 0,
        "created_at": datetime.now().isoformat(),
        "url": "#"
    })

    return JSONResponse({
        "success": True,
        "message": f"Call initiated to {data.to_number}",
        "call_id": call_id,
        "note": note
    })

@app.get("/call-logs", response_class=HTMLResponse)
async def call_logs_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""SELECT id,from_number,to_number,status,duration_seconds,created_at,
                recording_url FROM public.calls WHERE user_id=%s
                ORDER BY created_at DESC LIMIT 500""",(user["id"],))
            user_calls = [dict(id=str(r["id"]),from_number=r["from_number"],
                to_number=r["to_number"],status=r["status"],duration=r["duration_seconds"],
                created_at=r["created_at"].isoformat(),recording_url=r["recording_url"])
                for r in cur.fetchall()]
    return templates.TemplateResponse(request=request, name="call_logs.html", context={
        "user":user,"logs":user_calls})

@app.get("/contacts", response_class=HTMLResponse)
async def contacts_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""SELECT id,name,number,created_at FROM public.dialnytics_contacts
                WHERE user_id=%s ORDER BY created_at DESC""",(user["id"],))
            contacts = [dict(id=str(r["id"]),name=r["name"],number=r["number"],
                created_at=r["created_at"].isoformat()) for r in cur.fetchall()]
    return templates.TemplateResponse(request=request, name="contacts.html", context={
        "user":user,"contacts":contacts})

@app.post("/api/contacts")
async def add_contact(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    data = await request.json()
    name = str(data.get("name") or "").strip()[:200]
    number = str(data.get("number") or "").strip()[:40]
    if not name or not number:
        raise HTTPException(status_code=422,detail="Name and number required")
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""INSERT INTO public.dialnytics_contacts(user_id,name,number)
                VALUES(%s,%s,%s) RETURNING id,created_at""",(user["id"],name,number))
            r=cur.fetchone()
    contact=dict(id=str(r["id"]),name=name,number=number,created_at=r["created_at"].isoformat())
    return JSONResponse({"success":True,"contact":contact})

# ========== NEW PAGES ==========

@app.get("/recordings", response_class=HTMLResponse)
async def recordings_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse(request=request, name="recordings.html", context={
        "user": user,
        "recordings": recordings_db.get(user["email"], [])[::-1],
        "recording_ok": has_recording(user),
    })

@app.post("/api/recordings")
async def save_recording(
    request: Request,
    file: UploadFile = File(...),
    to_number: str = Form(""),
    duration: int = Form(0),
    kind: str = Form("call"),
):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if kind != "voicemail" and not has_recording(user):
        raise HTTPException(status_code=402, detail="Recording is a $25 upgrade")
    rec_id = secrets.token_hex(8)
    ext = ".webm"
    path = os.path.join(MEDIA_DIR, rec_id + ext)
    with open(path, "wb") as f:
        f.write(await file.read())
    entry = {
        "id": rec_id,
        "to_number": to_number,
        "from_number": "",
        "duration": duration,
        "created_at": datetime.now().isoformat(),
        "url": f"/media/{rec_id}{ext}",
    }
    bucket = voicemails_db if kind == "voicemail" else recordings_db
    bucket.setdefault(user["email"], []).append(entry)
    return JSONResponse({"success": True, "recording": entry})

def verify_telnyx_webhook(raw: bytes, signature: str, timestamp: str) -> bool:
    """Validate Telnyx API v2 Ed25519 signature with a 5-minute replay window."""
    public_key = os.getenv("TELNYX_PUBLIC_KEY", "").strip()
    if not public_key or not signature or not timestamp:
        return False
    try:
        ts = int(timestamp)
        if abs(time.time() - ts) > 300:
            return False
        key = Ed25519PublicKey.from_public_bytes(base64.b64decode(public_key, validate=True))
        signed_message = timestamp.encode("ascii") + b"|" + raw
        key.verify(base64.b64decode(signature, validate=True), signed_message)
        return True
    except (ValueError, TypeError, InvalidSignature):
        return False


@app.post("/webhooks/telnyx")
async def telnyx_webhook(request: Request):
    raw = await request.body()
    if not verify_telnyx_webhook(
        raw,
        request.headers.get("telnyx-signature-ed25519", ""),
        request.headers.get("telnyx-timestamp", ""),
    ):
        raise HTTPException(status_code=401, detail="Invalid Telnyx webhook signature")
    try:
        body = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(status_code=400, detail="Invalid JSON")
    data = body.get("data") or {}
    payload = data.get("payload") or {}
    event = data.get("event_type") or ""
    # Single-number/single-user Voice API routing.
    # Telnyx Voice API originates a SIP leg to the assigned WebRTC credential,
    # automatically bridging it to the inbound leg once answered.
    # Only the first, idempotently inserted call.initiated event originates a leg.
    if event in ("call.initiated", "call.answered", "call.bridge", "call.hangup"):
        call_id = payload.get("call_control_id")
        destination = payload.get("to") or ""
        origin = payload.get("from") or ""
        direction = str(payload.get("direction") or "").lower()
        if call_id and event == "call.initiated" and direction == "incoming" and destination:
            recipient = None
            group_id = None
            with db_connect() as conn:
                with conn.cursor() as cur:
                    cur.execute("""INSERT INTO public.incoming_call_groups
                        (telnyx_call_id,caller_number,destination_number,status)
                        VALUES (%s,%s,%s,'ringing')
                        ON CONFLICT(telnyx_call_id) DO NOTHING RETURNING id""",
                        (call_id, origin, destination))
                    inserted = cur.fetchone()
                    if inserted:
                        group_id = inserted["id"]
                        cur.execute("""SELECT u.id,u.email,u.sip_username,u.credential_id,
                            u.dnd_enabled,u.plan_renewal FROM public.caller_id_assignments a
                            JOIN public.dialnytics_users u ON u.id=a.user_id
                            WHERE a.phone_number=%s AND u.is_active=TRUE
                            LIMIT 1""", (destination,))
                        recipient = cur.fetchone()
                        if recipient and not recipient["dnd_enabled"] and (
                            not recipient["plan_renewal"] or recipient["plan_renewal"] >= datetime.now().date()
                        ):
                            cur.execute("""INSERT INTO public.call_participants
                                (group_id,user_id,status) VALUES (%s,%s,'ringing')
                                ON CONFLICT(group_id,user_id) DO NOTHING""",
                                (group_id,recipient["id"]))
                        else:
                            recipient = None
            if group_id:
                # Do not create new SIP credentials in a webhook: the user must
                # have logged in once and obtained a WebRTC credential already.
                sip_username = (recipient or {}).get("sip_username", "")
                if sip_username and TELNYX_API_KEY and os.getenv("TELNYX_VOICE_APP_ID"):
                    try:
                        _telnyx_request("POST", "/v2/calls", {
                            "connection_id": os.environ["TELNYX_VOICE_APP_ID"],
                            "to": f"sip:{sip_username}@sip.telnyx.com",
                            "from": origin or destination,
                            "link_to": call_id,
                            "bridge_intent": True,
                            "bridge_on_answer": True,
                            "prevent_double_bridge": True,
                            "timeout_secs": 30,
                            "command_id": str(group_id),
                        })
                    except Exception:
                        # Do not expose provider credentials or error bodies in responses.
                        import logging
                        logging.exception("Inbound SIP dial failed for call group %s", group_id)
                        with db_connect() as conn:
                            with conn.cursor() as cur:
                                cur.execute("""UPDATE public.incoming_call_groups
                                    SET status='failed',ended_at=NOW() WHERE id=%s""", (group_id,))
                        try:
                            _telnyx_request("POST", f"/v2/calls/{call_id}/actions/hangup", {})
                        except Exception:
                            logging.exception("Inbound hangup after routing failure")
                else:
                    # No eligible logged-in/registered agent. Do not leave a
                    # caller ringing indefinitely.
                    with db_connect() as conn:
                        with conn.cursor() as cur:
                            cur.execute("""UPDATE public.incoming_call_groups
                                SET status='missed',ended_at=NOW() WHERE id=%s""", (group_id,))
                    try:
                        _telnyx_request("POST", f"/v2/calls/{call_id}/actions/hangup", {})
                    except Exception:
                        import logging
                        logging.exception("Unable to terminate unroutable incoming call")
        if call_id and event in ("call.answered", "call.bridge", "call.hangup"):
            with db_connect() as conn:
                with conn.cursor() as cur:
                    # Linked SIP leg webhooks can have their own call control id.
                    # For now, only update the inbound leg's stored id.
                    if event in ("call.answered", "call.bridge"):
                        cur.execute("""UPDATE public.incoming_call_groups SET status='answered'
                            WHERE telnyx_call_id=%s AND status='ringing'""", (call_id,))
                    else:
                        cur.execute("""UPDATE public.incoming_call_groups
                            SET status=CASE WHEN status='ringing' THEN 'missed'
                                WHEN status='answered' THEN 'ended' ELSE status END,
                                ended_at=NOW()
                            WHERE telnyx_call_id=%s AND status IN ('ringing','answered')""", (call_id,))
    urls = payload.get("recording_urls") or {}
    mp3 = urls.get("mp3") or (payload.get("public_recording_urls") or {}).get("mp3")
    if mp3 or "voicemail" in event or "recording" in event:
        entry = {
            "id": secrets.token_hex(6),
            "to_number": payload.get("to") or payload.get("to_number") or "",
            "from_number": payload.get("from") or payload.get("from_number") or "",
            "duration": payload.get("duration_millis", 0) // 1000 if isinstance(payload.get("duration_millis"), int) else 0,
            "created_at": datetime.now().isoformat(),
            "url": mp3 or "#",
        }
        voicemails_db.setdefault("_shared", []).append(entry)
    return JSONResponse({"ok": True})

@app.get("/voicemails", response_class=HTMLResponse)
async def voicemails_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    mine = voicemails_db.get(user["email"], [])
    shared = voicemails_db.get("_shared", [])
    return templates.TemplateResponse(request=request, name="voicemails.html", context={
        "user": user, "voicemails": (shared + mine)[::-1]
    })

@app.get("/campaigns", response_class=HTMLResponse)
async def campaigns_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse(request=request, name="campaigns.html", context={
        "user": user,
        "campaigns": campaigns_db.get(user["email"], []),
        "premium": has_recording(user),
    })

@app.post("/api/campaigns")
async def create_campaign(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if not has_recording(user):
        raise HTTPException(status_code=402, detail="Campaigns are part of the $25 upgrade")
    data = await request.json()
    if user["email"] not in campaigns_db:
        campaigns_db[user["email"]] = []
    campaign = {
        "id": secrets.token_hex(6),
        "name": data.get("name", "Untitled"),
        "numbers": data.get("numbers", []),
        "status": "draft",
        "created_at": datetime.now().isoformat(),
        "dialed": 0
    }
    campaigns_db[user["email"]].append(campaign)
    return JSONResponse({"success": True, "campaign": campaign})

# Scripts are stored in PostgreSQL, not the Render ephemeral filesystem.
def _load_scripts():
    result = {}
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""SELECT u.email,s.id,s.title,s.category,s.content,s.is_default
                FROM public.scripts s JOIN public.dialnytics_users u ON u.id=s.user_id""")
            for row in cur.fetchall():
                result.setdefault(row["email"],[]).append({
                    "id":str(row["id"]),"title":row["title"],
                    "category":row["category"] or "","content":row["content"],
                    "default":row["is_default"]})
    return result

def _save_scripts(data):
    # This method is used only by the scripts routes below. Apply user-scoped changes.
    with db_connect() as conn:
        with conn.cursor() as cur:
            for email,items in data.items():
                cur.execute("SELECT id FROM public.dialnytics_users WHERE email=%s",(email,))
                row=cur.fetchone()
                if not row:
                    continue
                uid=row["id"]
                ids=[uuid.UUID(item["id"]) for item in items]
                cur.execute("DELETE FROM public.scripts WHERE user_id=%s AND NOT(id = ANY(%s::uuid[]))",(uid,ids))
                for item in items:
                    cur.execute("""INSERT INTO public.scripts(id,user_id,title,category,content,is_default)
                        VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT(id) DO UPDATE SET
                        title=EXCLUDED.title,category=EXCLUDED.category,content=EXCLUDED.content,
                        is_default=EXCLUDED.is_default,updated_at=NOW()""",(
                        uuid.UUID(item["id"]),uid,item["title"],item["category"],item["content"],bool(item.get("default"))))

@app.get("/scripts", response_class=HTMLResponse)
async def scripts_page(request: Request, edit: str = ""):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    all_scripts = _load_scripts().get(user["email"], [])
    current = next((item for item in all_scripts if item["id"] == edit), None)
    return templates.TemplateResponse(request=request, name="scripts.html", context={"user": user, "saved_scripts": all_scripts, "current_script": current})

@app.post("/scripts/save")
async def save_script(request: Request, title: str = Form(...), category: str = Form(""), content: str = Form(""), script_id: str = Form(""), is_default: Optional[str] = Form(None)):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    title = title.strip()[:150]
    if not title:
        raise HTTPException(status_code=400, detail="Script title required")
    content = bleach.clean(content, tags=["p", "br", "div", "b", "strong", "i", "em", "u", "ul", "ol", "li", "a", "blockquote"], attributes={"a": ["href", "title"]}, protocols=["https"], strip=True)
    data = _load_scripts()
    items = data.setdefault(user["email"], [])
    existing = next((item for item in items if item["id"] == script_id), None)
    if is_default:
        for item in items:
            item["default"] = False
    if existing:
        existing.update(title=title, category=category.strip()[:80], content=content[:50000], default=bool(is_default))
    else:
        script_id = str(uuid.uuid4())
        items.append({"id": script_id, "title": title, "category": category.strip()[:80], "content": content[:50000], "default": bool(is_default)})
    _save_scripts(data)
    return RedirectResponse(url="/scripts?edit=" + script_id, status_code=303)

@app.post("/scripts/delete")
async def delete_script(request: Request, script_id: str = Form(...)):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    data = _load_scripts()
    data[user["email"]] = [item for item in data.get(user["email"], []) if item["id"] != script_id]
    _save_scripts(data)
    return RedirectResponse(url="/scripts", status_code=303)

@app.get("/messages", response_class=HTMLResponse)
async def messages_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse(request=request, name="messages.html", context={"user": user})

@app.get("/crm", response_class=HTMLResponse)
async def crm_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse(request=request, name="crm.html", context={
        "user": user, "contacts": contacts_db.get(user["email"], [])
    })

@app.get("/follow-ups", response_class=HTMLResponse)
async def followups_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse(request=request, name="followups.html", context={"user": user, "items": []})

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse(request=request, name="settings.html", context={
        "user": user, "plan": plan_status(user)
    })

@app.get("/billing", response_class=HTMLResponse)
async def billing_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse(request=request, name="billing.html", context={
        "user": user,
        "plan": plan_status(user),
    })


# Atomic group-call coordination; the telephony leg orchestration must be
# configured separately through Telnyx Voice API before enabling live routing.
@app.post("/api/incoming-groups/{group_id}/answer")
async def claim_incoming_group(group_id: uuid.UUID, request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM public.dialnytics_users WHERE email=%s", (user["email"],))
            actor = cur.fetchone()
            if not actor:
                raise HTTPException(status_code=403, detail="Unknown user")
            uid = actor["id"]
            cur.execute("SELECT status FROM public.call_participants WHERE group_id=%s AND user_id=%s", (group_id,uid))
            participant = cur.fetchone()
            if not participant:
                raise HTTPException(status_code=403, detail="Not a participant")
            cur.execute("""UPDATE public.incoming_call_groups SET status='answered',answered_by=%s
                WHERE id=%s AND status='ringing' RETURNING id""", (uid,group_id))
            claimed = cur.fetchone()
            if claimed:
                cur.execute("""UPDATE public.call_participants SET status=CASE
                    WHEN user_id=%s THEN 'answered' ELSE 'cancelled' END WHERE group_id=%s""", (uid,group_id))
                return {"claimed":True,"status":"answered"}
            cur.execute("SELECT status FROM public.incoming_call_groups WHERE id=%s", (group_id,))
            current=cur.fetchone()
            return {"claimed":False,"status":current["status"] if current else "missing"}

@app.post("/api/incoming-groups/{group_id}/decline")
async def decline_incoming_group(group_id: uuid.UUID, request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""SELECT p.user_id FROM public.call_participants p
                JOIN public.dialnytics_users u ON u.id=p.user_id
                WHERE p.group_id=%s AND u.email=%s""", (group_id,user["email"]))
            if not cur.fetchone():
                raise HTTPException(status_code=403,detail="Not a participant")
            cur.execute("""UPDATE public.incoming_call_groups SET status='declined',ended_at=NOW()
                WHERE id=%s AND status='ringing' RETURNING telnyx_call_id""",(group_id,))
            updated=cur.fetchone()
            if updated:
                cur.execute("UPDATE public.call_participants SET status='declined' WHERE group_id=%s",(group_id,))
    carrier_hangup = False
    carrier_error = None
    if updated and updated.get("telnyx_call_id"):
        try:
            _telnyx_request("POST", f"/v2/calls/{updated['telnyx_call_id']}/actions/hangup", {})
            carrier_hangup = True
        except Exception as exc:
            carrier_error = str(exc)[:250]
    return {"group_declined":bool(updated),"carrier_hangup_sent":carrier_hangup,
            "carrier_error":carrier_error}

@app.get("/api/incoming/pending")
async def pending_incoming_for_user(request: Request):
    """Read-only diagnostic: pending inbound Voice API events for this user.

    This does NOT create a SIP/WebRTC call leg or permit answering the carrier.
    """
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""SELECT g.id,g.caller_number,g.destination_number,g.created_at
                FROM public.incoming_call_groups g
                JOIN public.call_participants p ON p.group_id=g.id
                JOIN public.dialnytics_users u ON u.id=p.user_id
                WHERE u.email=%s AND g.status='ringing'
                  AND g.created_at > NOW() - INTERVAL '3 minutes'
                ORDER BY g.created_at DESC LIMIT 5""", (user["email"],))
            rows = cur.fetchall()
    return {"pending": [{"id":str(r["id"]),"from":r["caller_number"],
                         "to":r["destination_number"],"created_at":r["created_at"].isoformat()}
                        for r in rows]}


@app.get("/api/incoming-groups/{group_id}/status")
async def incoming_group_status(group_id: uuid.UUID, request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401,detail="Unauthorized")
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""SELECT g.status,g.answered_by FROM public.incoming_call_groups g
                JOIN public.call_participants p ON p.group_id=g.id
                JOIN public.dialnytics_users u ON u.id=p.user_id
                WHERE g.id=%s AND u.email=%s""",(group_id,user["email"]))
            row=cur.fetchone()
    if not row:
        raise HTTPException(status_code=404,detail="Group not found")
    return {"status":row["status"],"answered_by":str(row["answered_by"]) if row["answered_by"] else None}

@app.post("/api/admin/users/{user_id}/force-logout")
async def admin_force_logout(user_id: uuid.UUID, request: Request):
    admin=get_current_user(request)
    if not admin or admin.get("role")!="admin":
        raise HTTPException(status_code=403,detail="Admin only")
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE public.user_sessions SET revoked_at=NOW() WHERE user_id=%s AND revoked_at IS NULL",(user_id,))
            count=cur.rowcount
    terminated = _terminate_user_inbound_calls(user_id)
    return {"revoked_sessions": count,
            "tracked_incoming_calls": terminated['tracked'],
            "carrier_hangups_sent": terminated['hangup_sent'],
            "carrier_hangups_failed": terminated['hangup_failed'],
            "active_calls_terminated": terminated['tracked'] > 0 and terminated['hangup_failed'] == 0,
            "note": "Untracked outbound WebRTC carrier legs cannot be terminated by this API."}
