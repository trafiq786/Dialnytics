# Dialnytics — Smart Cloud Dialer

Dark-themed multi-user dialer (Dialsyx-style) built with FastAPI + HTML/CSS/JS.

## Features (MVP)

- Login / Signup (multi-user)
- Dashboard with stats
- Dial Pad (manual outbound calling)
- Call Logs
- Contacts management
- Dark modern UI

## Quick Start

```bash
cd dialnytics

# Create virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Open: http://localhost:8000

### Default Admin Login
- Email: `admin@dialnytics.com`
- Password: `admin123`

## Project Structure

```
dialnytics/
├── backend/
│   └── main.py          # FastAPI app
├── frontend/
│   ├── static/css/style.css
│   └── templates/       # Jinja2 HTML
├── requirements.txt
└── README.md
```

## Telnyx WebRTC

Keys `.env` file mein hain. Server start karo, login karo, Dialer page kholo.

- Admin: `admin@dialnytics.com` / `admin123`
- Har user apne website login se dial karega
- Browser Telnyx password nahi dekhta — backend JWT banata hai
- Number E.164 mein dial karo, jaise `+12025550123`
- Mic permission allow karna zaroori hai
- HTTPS ya localhost pe chalana (mic ke liye)

```bash
cd dialnytics
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Open: http://localhost:8000


## Multi-user

- Each signup creates a new user
- Users are isolated (own call logs & contacts)
- Admin can later manage users from backend
