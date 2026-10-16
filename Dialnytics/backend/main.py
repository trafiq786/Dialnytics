from fastapi import FastAPI, Request, Form, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
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
TELNYX_FROM_NUMBER = os.getenv("TELNYX_FROM_NUMBER", "+12033039364")

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
    "phone_number": "+12033039364",
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
    "phone_number": "+12033039364",
    "sip_username": "",
    "credential_id": "",
    "created_at": datetime.now().isoformat()
}

USERS_FILE = os.path.join(BASE_DIR, "users.json")

def save_users():
    with open(USERS_FILE, "w") as f:
        json.dump(users_db, f, indent=2)

def load_users():
    if not os.path.exists(USERS_FILE):
        save_users()
        return
    with open(USERS_FILE) as f:
        stored = json.load(f)
    if stored:
        users_db.clear()
        users_db.update(stored)

load_users()

class CallRequest(BaseModel):
    to_number: str

class CampaignCreate(BaseModel):
    name: str
    numbers: List[str]

def create_session(email: str) -> str:
    token = secrets.token_hex(32)
    sessions[token] = {"email": email, "expires": datetime.now() + timedelta(hours=24)}
    return token

def get_current_user(request: Request):
    token = request.cookies.get("session_token")
    if not token or token not in sessions:
        return None
    session = sessions[token]
    if session["expires"] < datetime.now():
        del sessions[token]
        return None
    return users_db.get(session["email"])

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
    user = users_db.get(email)
    if not user or not verify_password(password, user["password"]):
        return templates.TemplateResponse(request=request, name="login.html", context={"error": "Invalid email or password"})
    token = create_session(email)
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
):
    user = get_current_user(request)
    if not user or user.get("role") != "admin":
        return RedirectResponse(url="/login", status_code=302)
    email = email.strip().lower()
    phone_number = phone_number.strip()
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
        return RedirectResponse(url="/users?error=Please+confirm+shared+Caller+ID", status_code=302)
    try:
        amount_paid = int((await request.form()).get("amount_paid", "0") or 0)
        if amount_paid < 0: raise ValueError()
    except ValueError:
        return RedirectResponse(url="/users?error=Invalid+PKR+amount", status_code=302)
    payment_status = str((await request.form()).get("payment_status", "paid"))
    if payment_status not in ("paid", "partial", "unpaid"):
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
        "last_paid_amount": amount_paid if amount_paid else 0,
        "payment_status": payment_status,
        "payments": ([{"amount": amount_paid, "date": datetime.now().date().isoformat(), "type": "initial"}] if amount_paid else []),
        "created_at": datetime.now().isoformat(),
    }
    save_users()
    try:
        _ensure_credential(email)
    except Exception:
        pass
    return RedirectResponse(url="/users?created=1", status_code=302)

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
    if token and token in sessions:
        del sessions[token]
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("session_token")
    return response

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    period = request.query_params.get("period", "today")
    if period not in ("today", "week", "month"): period = "today"
    today = date.today()
    beginning = today if period == "today" else (today - timedelta(days=today.weekday()) if period == "week" else today.replace(day=1))
    user_calls = [c for c in call_logs if c.get("user_email") == user["email"] and str(c.get("created_at", ""))[:10] >= beginning.isoformat()]
    total_calls = len(user_calls)
    answered = len([c for c in user_calls if c.get("status") in ("answered", "completed", "active")])
    failed = len([c for c in user_calls if c.get("status") not in ("answered", "completed", "active")])
    answer_rate = f"{int((answered/total_calls)*100)}%" if total_calls else "0%"
    talk = [int(c.get("duration") or 0) for c in user_calls]
    avg = int(sum(talk) / len(talk)) if talk else 0
    avg_talk = f"{avg // 60}:{avg % 60:02d}"
    revenue = 0
    renewals = []
    if user.get("role") == "admin":
        for account in users_db.values():
            if account.get("role") == "admin": continue
            for payment in account.get("payments", []):
                if str(payment.get("date", ""))[:7] == today.strftime("%Y-%m"):
                    revenue += int(payment.get("amount", 0))
            try:
                remaining = (date.fromisoformat(account.get("plan_renewal", "")) - today).days
            except ValueError:
                continue
            if 0 <= remaining <= 7:
                renewals.append({"name": account.get("name"), "email": account.get("email"), "renewal": account.get("plan_renewal"), "amount": account.get("last_paid_amount", 0), "days": remaining})
        renewals.sort(key=lambda r: r["days"])
    return templates.TemplateResponse(request=request, name="dashboard.html", context={
        "period": period, "revenue": revenue, "renewals": renewals,
        "user": user, "total_calls": total_calls, "answer_rate": answer_rate,
        "avg_talk_time": avg_talk, "contacts_count": len(contacts_db.get(user["email"], [])),
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
        "from_number": TELNYX_FROM_NUMBER,
        "to_number": data.get("to_number"),
        "status": data.get("status", "initiated"),
        "duration": 0,
        "created_at": datetime.now().isoformat(),
        "recording_url": None,
    }
    call_logs.append(call_entry)
    return JSONResponse({"success": True, "call": call_entry, "id": call_entry["id"]})

@app.post("/api/call-log/{call_id}")
async def update_call_log(call_id: str, request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    data = await request.json()
    for entry in call_logs:
        if entry["id"] == call_id and entry["user_email"] == user["email"]:
            entry["duration"] = int(data.get("duration") or 0)
            if data.get("status"):
                entry["status"] = data["status"]
            return JSONResponse({"success": True})
    raise HTTPException(status_code=404, detail="Call not found")

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
    user_calls = [c for c in call_logs if c.get("user_email") == user["email"]]
    return templates.TemplateResponse(request=request, name="call_logs.html", context={
        "user": user, "logs": user_calls[::-1]
    })

@app.get("/contacts", response_class=HTMLResponse)
async def contacts_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse(request=request, name="contacts.html", context={
        "user": user, "contacts": contacts_db.get(user["email"], [])
    })

@app.post("/api/contacts")
async def add_contact(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    data = await request.json()
    if user["email"] not in contacts_db:
        contacts_db[user["email"]] = []
    contact = {
        "id": len(contacts_db[user["email"]]) + 1,
        "name": data.get("name"), "number": data.get("number"),
        "created_at": datetime.now().isoformat()
    }
    contacts_db[user["email"]].append(contact)
    return JSONResponse({"success": True, "contact": contact})

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

@app.post("/webhooks/telnyx")
async def telnyx_webhook(request: Request):
    body = await request.json()
    data = body.get("data") or {}
    payload = data.get("payload") or {}
    event = data.get("event_type") or ""
    urls = payload.get("recording_urls") or {}
    mp3 = urls.get("mp3") or payload.get("public_recording_urls", {}).get("mp3")
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

# Scripts are saved locally for testing; use a persistent database before production.
SCRIPTS_FILE = os.path.join(BASE_DIR, "scripts.json")

def _load_scripts():
    try:
        with open(SCRIPTS_FILE, encoding="utf-8") as fh:
            result = json.load(fh)
            return result if isinstance(result, dict) else {}
    except (OSError, ValueError):
        return {}

def _save_scripts(data):
    with open(SCRIPTS_FILE, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)

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
        script_id = secrets.token_hex(10)
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
