"""Announcements: the admin posts updates / maintenance notices, users see them as a
popup, a top banner and in the notification bell."""
import datetime as dt
import logging
import uuid

from fastapi import Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

log = logging.getLogger("dialnytics.announcements")

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS public.announcements (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    title text NOT NULL DEFAULT '',
    message text NOT NULL DEFAULT '',
    kind text NOT NULL DEFAULT 'update',          -- update | feature | maint | urgent
    audience text NOT NULL DEFAULT 'all',         -- all | owners | direct | partners | company
    account_id uuid,                              -- audience = company
    include_partners boolean NOT NULL DEFAULT true,
    show_popup boolean NOT NULL DEFAULT true,
    show_banner boolean NOT NULL DEFAULT true,
    popup_mode text NOT NULL DEFAULT 'once',      -- once | until_read | every_login
    link text NOT NULL DEFAULT '',
    status text NOT NULL DEFAULT 'live',          -- draft | live | ended
    ends_on date,
    created_at timestamptz NOT NULL DEFAULT now(),
    published_at timestamptz,
    ended_at timestamptz
);
CREATE TABLE IF NOT EXISTS public.announcement_reads (
    announcement_id uuid REFERENCES public.announcements(id) ON DELETE CASCADE,
    user_id uuid REFERENCES public.dialnytics_users(id) ON DELETE CASCADE,
    read_at timestamptz,
    popup_seen_at timestamptz,
    popup_session text NOT NULL DEFAULT '',
    remind_after timestamptz,
    banner_closed boolean NOT NULL DEFAULT false,
    PRIMARY KEY (announcement_id, user_id)
);
ALTER TABLE public.announcements ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.announcement_reads ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.announcements FROM anon, authenticated;
REVOKE ALL ON public.announcement_reads FROM anon, authenticated;
"""

KINDS = {"update": "Update", "feature": "New feature", "maint": "Maintenance", "urgent": "Urgent"}
AUDIENCES = {"all": "All users", "owners": "Company owners", "direct": "My direct customers",
             "partners": "Partners and their users", "company": "One company"}
POPUP_MODES = {"once": "Once per user", "until_read": "Every login until read",
               "every_login": "Every login until it ends"}


def register(app, d):
    db_connect = d["db_connect"]
    templates = d["templates"]
    get_current_user = d["get_current_user"]
    require_admin = d["require_admin"]
    brand_name = d.get("brand_name") or (lambda: "Dialnytics")
    session_key = d.get("session_key") or (lambda request: request.cookies.get("session_token", "")[-16:])

    # ------------------------------------------------------------------ who sees what
    AUDIENCE_SQL = """
        a.status='live' AND (a.ends_on IS NULL OR a.ends_on >= CURRENT_DATE)
        AND (
          a.audience='all' AND (a.include_partners OR NOT %(partner_side)s)
          OR a.audience='owners' AND %(is_owner)s AND (a.include_partners OR NOT %(partner_side)s)
          OR a.audience='direct' AND NOT %(partner_side)s
          OR a.audience='partners' AND %(partner_side)s
          OR a.audience='company' AND a.account_id IS NOT NULL AND a.account_id = %(account_id)s
        )"""

    def viewer(cur, user):
        """Facts about the user needed for the audience filter."""
        partner_side = user.get("user_type") == "reseller"
        account_id = user.get("account_id") or None
        if account_id and not partner_side:
            cur.execute("SELECT reseller_id FROM public.dialnytics_accounts WHERE id=%s", (account_id,))
            r = cur.fetchone()
            partner_side = bool(r and r.get("reseller_id"))
        is_owner = (user.get("account_role") == "owner") or user.get("user_type") == "reseller"
        return {"partner_side": partner_side, "is_owner": bool(is_owner), "account_id": account_id}

    def for_user(user, request):
        if not user or user.get("role") == "admin":
            return []
        sess = session_key(request)
        with db_connect() as conn:
            with conn.cursor() as cur:
                v = viewer(cur, user)
                v["uid"] = user["id"]
                cur.execute(f"""SELECT a.*, r.read_at, r.popup_seen_at, r.popup_session, r.remind_after,
                        COALESCE(r.banner_closed,false) AS banner_closed
                    FROM public.announcements a
                    LEFT JOIN public.announcement_reads r ON r.announcement_id=a.id AND r.user_id=%(uid)s
                    WHERE {AUDIENCE_SQL}
                    ORDER BY a.published_at DESC NULLS LAST LIMIT 30""", v)
                rows = cur.fetchall()
        now = dt.datetime.now(dt.timezone.utc)
        own = str(brand_name())
        out = []
        for a in rows:
            def rebrand(text):
                return text.replace("Dialnytics", own) if own and own != "Dialnytics" else text
            reminded = a["remind_after"] and a["remind_after"] > now
            if a["popup_mode"] == "every_login":
                popup = a["popup_session"] != sess
            elif a["popup_mode"] == "until_read":
                popup = not a["read_at"] and a["popup_session"] != sess
            else:
                popup = not a["popup_seen_at"]
            out.append({
                "id": str(a["id"]), "title": rebrand(a["title"]), "message": rebrand(a["message"]),
                "kind": a["kind"], "kind_label": KINDS.get(a["kind"], "Update"), "link": a["link"],
                "date": (a["published_at"] or a["created_at"]).isoformat(),
                "unread": not a["read_at"],
                "popup": bool(a["show_popup"] and popup and not reminded),
                "banner": bool(a["show_banner"] and (a["kind"] == "urgent" or not a["banner_closed"])),
                "closable": a["kind"] != "urgent",
            })
        return out

    def mark(user, ann_id, action, request):
        cols = {
            "read": "read_at=COALESCE(announcement_reads.read_at, now())",
            "popup": "popup_seen_at=now(), popup_session=%(sess)s, read_at=COALESCE(announcement_reads.read_at, now())",
            "remind": "remind_after=now() + interval '1 hour', popup_session=%(sess)s",
            "close_banner": "banner_closed=true, read_at=COALESCE(announcement_reads.read_at, now())",
        }
        if action not in cols:
            raise HTTPException(400, "Unknown action")
        params = {"aid": ann_id, "uid": user["id"], "sess": session_key(request)}
        with db_connect() as conn:
            with conn.cursor() as cur:
                cur.execute(f"""INSERT INTO public.announcement_reads(announcement_id,user_id) VALUES (%(aid)s,%(uid)s)
                    ON CONFLICT DO NOTHING""", params)
                cur.execute(f"""UPDATE public.announcement_reads SET {cols[action]}
                    WHERE announcement_id=%(aid)s AND user_id=%(uid)s""", params)

    # ------------------------------------------------------------------ user API
    @app.get("/api/announcements")
    def api_announcements(request: Request):
        user = get_current_user(request)
        if not user:
            return JSONResponse({"items": []}, status_code=401)
        items = for_user(user, request)
        return JSONResponse({"items": items, "unread": sum(1 for i in items if i["unread"])},
                            headers={"Cache-Control": "no-store"})

    @app.post("/api/announcements/{ann_id}/{action}")
    def api_announcement_mark(ann_id: uuid.UUID, action: str, request: Request):
        user = get_current_user(request)
        if not user:
            raise HTTPException(401, "Not signed in")
        mark(user, ann_id, action, request)
        return {"ok": True}

    @app.post("/api/announcements-read-all")
    def api_announcements_read_all(request: Request):
        user = get_current_user(request)
        if not user:
            raise HTTPException(401, "Not signed in")
        for a in for_user(user, request):
            if a["unread"]:
                mark(user, a["id"], "read", request)
        return {"ok": True}

    # ------------------------------------------------------------------ admin
    def audience_size(cur, a):
        """How many active users this announcement is for (for the Seen column)."""
        cur.execute("""SELECT u.id, u.user_type, u.account_role, u.account_id,
                (acc.reseller_id IS NOT NULL) AS under_partner
            FROM public.dialnytics_users u LEFT JOIN public.dialnytics_accounts acc ON acc.id=u.account_id
            WHERE u.is_active AND u.role <> 'admin'""")
        n = 0
        for u in cur.fetchall():
            partner_side = u["user_type"] == "reseller" or bool(u["under_partner"])
            owner = u["account_role"] == "owner" or u["user_type"] == "reseller"
            aud = a["audience"]
            if (aud == "all" and (a["include_partners"] or not partner_side)
                    or aud == "owners" and owner and (a["include_partners"] or not partner_side)
                    or aud == "direct" and not partner_side
                    or aud == "partners" and partner_side
                    or aud == "company" and a["account_id"] and u["account_id"] == a["account_id"]):
                n += 1
        return n

    @app.get("/announcements", response_class=HTMLResponse)
    def announcements_page(request: Request):
        require_admin(request)
        user = get_current_user(request)
        edit_id = request.query_params.get("edit", "")
        with db_connect() as conn:
            with conn.cursor() as cur:
                cur.execute("""SELECT a.*, (SELECT count(*) FROM public.announcement_reads r
                        WHERE r.announcement_id=a.id AND r.read_at IS NOT NULL) AS seen
                    FROM public.announcements a ORDER BY a.created_at DESC LIMIT 100""")
                rows = cur.fetchall()
                for a in rows:
                    a["total"] = audience_size(cur, a)
                    if a["status"] == "live" and a["ends_on"] and a["ends_on"] < dt.date.today():
                        a["status"] = "ended"
                cur.execute("SELECT id, name FROM public.dialnytics_accounts ORDER BY lower(name) LIMIT 1000")
                companies = cur.fetchall()
        edit = next((a for a in rows if str(a["id"]) == edit_id), None)
        return templates.TemplateResponse(request=request, name="announcements.html", context={
            "user": user, "rows": rows, "companies": companies, "edit": edit,
            "kinds": KINDS, "audiences": AUDIENCES, "popup_modes": POPUP_MODES,
            "msg": request.query_params.get("msg", ""), "today": dt.date.today().isoformat()})

    @app.post("/announcements")
    def announcements_save(request: Request, title: str = Form(...), message: str = Form(""),
                           kind: str = Form("update"), audience: str = Form("all"), account_id: str = Form(""),
                           popup_mode: str = Form("once"), ends_on: str = Form(""), link: str = Form(""),
                           show_popup: str = Form(""), show_banner: str = Form(""),
                           include_partners: str = Form(""), action: str = Form("publish"),
                           edit_id: str = Form("")):
        require_admin(request)
        title = title.strip()[:140]
        if not title:
            return RedirectResponse("/announcements?msg=notitle", status_code=303)
        kind = kind if kind in KINDS else "update"
        audience = audience if audience in AUDIENCES else "all"
        popup_mode = popup_mode if popup_mode in POPUP_MODES else "once"
        try:
            acc = str(uuid.UUID(account_id)) if audience == "company" and account_id else None
        except ValueError:
            acc = None
        if audience == "company" and not acc:
            return RedirectResponse("/announcements?msg=nocompany", status_code=303)
        try:
            end = dt.date.fromisoformat(ends_on) if ends_on else None
        except ValueError:
            end = None
        link = link.strip()[:500]
        if link and not link.startswith(("https://", "http://")):
            link = ""
        status = "draft" if action == "draft" else "live"
        vals = dict(title=title, message=message.strip()[:2000], kind=kind, audience=audience, account_id=acc,
                    include_partners=bool(include_partners), show_popup=bool(show_popup),
                    show_banner=bool(show_banner), popup_mode=popup_mode, link=link, ends_on=end, status=status)
        with db_connect() as conn:
            with conn.cursor() as cur:
                if edit_id:
                    cur.execute("""UPDATE public.announcements SET title=%(title)s, message=%(message)s, kind=%(kind)s,
                            audience=%(audience)s, account_id=%(account_id)s, include_partners=%(include_partners)s,
                            show_popup=%(show_popup)s, show_banner=%(show_banner)s, popup_mode=%(popup_mode)s,
                            link=%(link)s, ends_on=%(ends_on)s, status=%(status)s, ended_at=NULL,
                            published_at=CASE WHEN %(status)s='live' THEN COALESCE(published_at, now()) ELSE published_at END
                        WHERE id=%(id)s""", dict(vals, id=edit_id))
                else:
                    cur.execute("""INSERT INTO public.announcements(title,message,kind,audience,account_id,include_partners,
                            show_popup,show_banner,popup_mode,link,ends_on,status,published_at)
                        VALUES (%(title)s,%(message)s,%(kind)s,%(audience)s,%(account_id)s,%(include_partners)s,
                            %(show_popup)s,%(show_banner)s,%(popup_mode)s,%(link)s,%(ends_on)s,%(status)s,
                            CASE WHEN %(status)s='live' THEN now() END)""", vals)
        return RedirectResponse("/announcements?msg=" + ("draft" if status == "draft" else "published"), status_code=303)

    @app.post("/announcements/{ann_id}/{action}")
    def announcements_action(ann_id: uuid.UUID, action: str, request: Request):
        require_admin(request)
        with db_connect() as conn:
            with conn.cursor() as cur:
                if action == "end":
                    cur.execute("UPDATE public.announcements SET status='ended', ended_at=now() WHERE id=%s", (ann_id,))
                elif action == "repost":
                    # Show it again to everyone: a fresh popup and banner.
                    cur.execute("""UPDATE public.announcements SET status='live', ended_at=NULL, published_at=now(),
                        ends_on=CASE WHEN ends_on < CURRENT_DATE THEN NULL ELSE ends_on END WHERE id=%s""", (ann_id,))
                    cur.execute("DELETE FROM public.announcement_reads WHERE announcement_id=%s", (ann_id,))
                elif action == "delete":
                    cur.execute("DELETE FROM public.announcements WHERE id=%s", (ann_id,))
                else:
                    raise HTTPException(400, "Unknown action")
        return RedirectResponse("/announcements?msg=" + action, status_code=303)

    @app.get("/announcements/{ann_id}/seen")
    def announcements_seen(ann_id: uuid.UUID, request: Request):
        require_admin(request)
        with db_connect() as conn:
            with conn.cursor() as cur:
                cur.execute("""SELECT u.name, u.email, r.read_at FROM public.announcement_reads r
                    JOIN public.dialnytics_users u ON u.id=r.user_id
                    WHERE r.announcement_id=%s AND r.read_at IS NOT NULL ORDER BY r.read_at DESC""", (ann_id,))
                rows = cur.fetchall()
        return {"seen": [{"name": r["name"] or r["email"], "email": r["email"],
                          "at": r["read_at"].isoformat()} for r in rows]}

    return {"for_user": for_user}
