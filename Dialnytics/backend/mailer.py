"""Tiny SMTP mailer (stdlib only). Safe no-op if not configured.

Dialnytics ki mail already Zoho par chalti hai (dialnytics.com), is liye
defaults Zoho ke hain. Render par ye env vars set karo:

  SMTP_USER   e.g. billing@dialnytics.com   (ya support@dialnytics.com)
  SMTP_PASS   Zoho **app-specific password** (normal login password NAHI)
  SMTP_HOST   default smtp.zoho.com
  SMTP_PORT   default 465  (SSL).  587 = STARTTLS
  SMTP_FROM   optional, default: "Dialnytics <SMTP_USER>"

Agar SMTP_USER / SMTP_PASS set na hon to send_email() crash nahi karta —
bas (False, reason) return karta hai, taake baqi app chalti rahe.
"""
import os
import ssl
import smtplib
import logging
from email.message import EmailMessage

log = logging.getLogger("dialnytics.mailer")


def configured() -> bool:
    return bool(os.getenv("SMTP_USER", "").strip() and os.getenv("SMTP_PASS", "").strip())


def from_address() -> str:
    user = os.getenv("SMTP_USER", "").strip()
    frm = os.getenv("SMTP_FROM", "").strip()
    return frm or ("Dialnytics <%s>" % user)


def send_email(to, subject, html_body, text_body=None, attachments=None,
               cc=None, reply_to=None):
    """Send one email.

    to          : str or list[str]
    attachments : list of (filename, bytes, mimetype)
    Returns (ok: bool, detail: str).
    """
    if not configured():
        return False, "SMTP not configured (set SMTP_USER / SMTP_PASS in Render)"

    user = os.getenv("SMTP_USER", "").strip()
    pw = os.getenv("SMTP_PASS", "")
    host = os.getenv("SMTP_HOST", "smtp.zoho.com").strip()
    try:
        port = int(os.getenv("SMTP_PORT", "465"))
    except ValueError:
        port = 465

    msg = EmailMessage()
    msg["From"] = from_address()
    msg["To"] = to if isinstance(to, str) else ", ".join(to)
    if cc:
        msg["Cc"] = cc if isinstance(cc, str) else ", ".join(cc)
    msg["Subject"] = subject
    if reply_to:
        msg["Reply-To"] = reply_to
    msg.set_content(text_body or "Please open this message in an HTML email client.")
    if html_body:
        msg.add_alternative(html_body, subtype="html")

    for fn, data, mt in (attachments or []):
        maintype, _, subtype = (mt or "application/octet-stream").partition("/")
        msg.add_attachment(data, maintype=maintype or "application",
                           subtype=subtype or "octet-stream", filename=fn)

    try:
        if port == 465:
            ctx = ssl.create_default_context()
            with smtplib.SMTP_SSL(host, port, context=ctx, timeout=30) as s:
                s.login(user, pw)
                s.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=30) as s:
                s.ehlo()
                s.starttls(context=ssl.create_default_context())
                s.ehlo()
                s.login(user, pw)
                s.send_message(msg)
        return True, "sent"
    except Exception as e:  # noqa: BLE001
        log.exception("Email send failed")
        return False, "%s: %s" % (type(e).__name__, e)
