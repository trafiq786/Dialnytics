"""Live call listening for supervisors (Telnyx lines).

Who may listen:
  * the super admin (role = admin): every company
  * a company owner: only their own company, and only when the super admin has
    turned "Live call listening" on for that company (dialnytics_accounts.live_listen)

How it works:
  1. The agent's call (customer leg + agent leg, both server controlled) is moved
     into a Telnyx conference the first time someone listens.
  2. The server dials the listener's browser (their Dialnytics calling login) with
     the X-DN-Monitor header; the dialer answers it silently.
  3. When that leg answers it joins the conference as a supervisor:
       listen  -> supervisor_role "monitor"  (hears both, nobody hears them)
       whisper -> supervisor_role "whisper"  (only the agent hears them)
       join    -> supervisor_role "barge"    (everyone hears them)
  4. The listener leg ends when the listener presses Stop or the call ends.
"""
import logging
import time
import uuid

import call_transfer as ct

log = logging.getLogger("dialnytics.live")

SCHEMA_SQL = """
ALTER TABLE public.dialnytics_accounts ADD COLUMN IF NOT EXISTS live_listen boolean NOT NULL DEFAULT false;
ALTER TABLE public.live_legs ADD COLUMN IF NOT EXISTS conference_id text;
ALTER TABLE public.dialnytics_users ADD COLUMN IF NOT EXISTS live_route boolean NOT NULL DEFAULT false;
CREATE TABLE IF NOT EXISTS public.live_monitors (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    listener_id uuid REFERENCES public.dialnytics_users(id) ON DELETE CASCADE,
    agent_id uuid REFERENCES public.dialnytics_users(id) ON DELETE CASCADE,
    customer_leg text NOT NULL,
    agent_leg text NOT NULL,
    conference_id text NOT NULL,
    listener_leg text,
    mode text NOT NULL DEFAULT 'listen',
    status text NOT NULL DEFAULT 'dialing',
    tx_account text NOT NULL DEFAULT 't1',
    error text NOT NULL DEFAULT '',
    created_at timestamptz NOT NULL DEFAULT now(),
    ended_at timestamptz
);
CREATE INDEX IF NOT EXISTS live_monitors_open_idx ON public.live_monitors(customer_leg) WHERE ended_at IS NULL;
CREATE INDEX IF NOT EXISTS live_monitors_listener_idx ON public.live_monitors(listener_id) WHERE ended_at IS NULL;
ALTER TABLE public.live_monitors ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.live_monitors FROM anon, authenticated;
"""

ROLES = {"listen": "monitor", "whisper": "whisper", "join": "barge"}
D = {}


class LiveError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def setup(**deps):
    """deps: account_live_listen(account_id) -> bool"""
    D.update(deps)
    if end_for_customer not in ct.GONE_HOOKS:
        ct.GONE_HOOKS.append(end_for_customer)
    ct.PREFIX_HOOKS["mon:"] = _hook


def _hook(event, mid, payload):
    try:
        uuid.UUID(mid)
    except ValueError:
        return
    on_event(event, mid, payload)


# ---------------------------------------------------------------- permission
def can_listen(viewer, agent):
    if not viewer or not agent:
        return False
    if viewer.get("role") == "admin":
        return True
    if viewer.get("user_type") != "customer" or viewer.get("account_role") != "owner":
        return False
    aid = str(viewer.get("account_id") or "")
    if not aid or aid != str(agent.get("account_id") or ""):
        return False
    return bool(D["account_live_listen"](aid))


def _live_leg(agent_id):
    with ct._db() as conn:
        with conn.cursor() as cur:
            cur.execute("""SELECT l.*, GREATEST(0, EXTRACT(EPOCH FROM (now()-l.started_at)))::int AS secs
                FROM public.live_legs l WHERE l.user_id=%s AND l.ended_at IS NULL AND l.kind<>'ext'
                ORDER BY l.started_at DESC LIMIT 1""", (agent_id,))
            return cur.fetchone()


def details(viewer, agent):
    """What the Team page popup shows for one agent."""
    if not can_listen(viewer, agent):
        raise LiveError("Live call listening is not turned on for your company", 403)
    leg = _live_leg(agent["id"])
    out = {"agent": {"id": agent["id"], "name": agent.get("name") or "", "phone_number": agent.get("phone_number") or ""},
           "live": bool(leg), "can_listen": False, "reason": ""}
    if (agent.get("provider") or "telnyx") != "telnyx":
        out["reason"] = "Live listening works on Telnyx lines only"
        return out
    if not leg:
        out["reason"] = ("Outgoing calls of this agent cannot be heard yet. Turn on Live listening for this agent "
                         "(Users → Edit), then the agent refreshes the dialer once."
                         if not (agent.get("adv_calling") or agent.get("live_route")) else "No live call right now")
        return out
    out.update(number=leg["customer_number"] or "", seconds=int(leg["secs"] or 0),
               direction="outgoing" if leg["kind"] == "out" else "incoming", can_listen=True)
    mine = _open_monitor(viewer["id"])
    if mine and mine["customer_leg"] == leg["customer_leg"]:
        out["monitor"] = _mon_json(mine)
    return out


def _open_monitor(listener_id):
    with ct._db() as conn:
        with conn.cursor() as cur:
            cur.execute("""SELECT * FROM public.live_monitors WHERE listener_id=%s AND ended_at IS NULL
                ORDER BY created_at DESC LIMIT 1""", (listener_id,))
            return cur.fetchone()


def _mon_json(m):
    return {"id": str(m["id"]), "mode": m["mode"], "status": m["status"], "error": m.get("error") or ""}


# ---------------------------------------------------------------- start / change / stop
def _ensure_conference(leg):
    if leg.get("conference_id"):
        return leg["conference_id"]
    name = "dn-" + uuid.uuid4().hex[:16]
    try:
        resp = ct._tx("POST", "/v2/conferences", {
            "call_control_id": leg["customer_leg"], "name": name, "beep_enabled": "never"})
        conf = ((resp or {}).get("data") or {}).get("id") or ""
    except Exception as exc:
        log.warning("Live listen: could not create conference for %s: %s", leg["customer_leg"],
                    str(getattr(exc, "detail", exc)).replace("\n", " ")[:300])
        raise LiveError("Could not open this call for listening. Try again in a moment.", 502)
    if not conf:
        raise LiveError("Could not open this call for listening.", 502)
    # The caller is in the conference now; bring the agent in (Telnyx may need a moment).
    last = None
    for attempt in range(4):
        try:
            ct._tx("POST", f"/v2/conferences/{conf}/actions/join", {
                "call_control_id": leg["agent_leg"], "beep_enabled": "never"})
            last = None
            break
        except Exception as exc:
            last = str(getattr(exc, "detail", exc)).replace("\n", " ")[:300]
            if "90018" in last:          # the agent leg is gone: retrying will not help
                break
            time.sleep(0.4)
    if last:
        log.warning("Live listen: agent could not join conference %s: %s", conf, last)
        # Put the call back the way it was, so it is not dropped.
        try:
            ct._tx("POST", f"/v2/conferences/{conf}/actions/leave", {"call_control_id": leg["customer_leg"]})
        except Exception:
            pass
        try:
            ct._tx("POST", f"/v2/calls/{leg['agent_leg']}/actions/bridge",
                   {"call_control_id": leg["customer_leg"], "park_after_unbridge": "self"})
            log.info("Live listen: call %s put back to normal", leg["customer_leg"])
            raise LiveError("Could not open this call for listening. The call was put back to normal.", 502)
        except LiveError:
            raise
        except Exception as exc:
            log.warning("Live listen: could not restore call %s: %s", leg["customer_leg"], getattr(exc, "detail", exc))
            raise LiveError("Could not open this call for listening, and the call may have dropped. "
                            "Calls that started before this update cannot be heard.", 502)
    with ct._db() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE public.live_legs SET conference_id=%s WHERE customer_leg=%s AND ended_at IS NULL",
                        (conf, leg["customer_leg"]))
    log.info("Live listen: call %s moved into conference %s", leg["customer_leg"], conf)
    return conf


def start(viewer, agent, mode="listen"):
    if mode not in ROLES:
        mode = "listen"
    if not can_listen(viewer, agent):
        raise LiveError("Live call listening is not turned on for your company", 403)
    if str(viewer["id"]) == str(agent["id"]):
        raise LiveError("You cannot listen to your own call")
    if (viewer.get("provider") or "telnyx") != "telnyx" or not viewer.get("sip_username"):
        raise LiveError("Listening needs a Telnyx calling line on your login (the call comes to your dialer)")
    if not ct.voice_app():
        raise LiveError("TELNYX_VOICE_APP_ID is missing in Render", 500)
    leg = _live_leg(agent["id"])
    if not leg:
        raise LiveError("This call has ended or cannot be heard", 404)
    old = _open_monitor(viewer["id"])
    if old:
        stop(viewer, str(old["id"]))
    conf = _ensure_conference(leg)
    with ct._db() as conn:
        with conn.cursor() as cur:
            cur.execute("""INSERT INTO public.live_monitors(listener_id,agent_id,customer_leg,agent_leg,conference_id,mode,tx_account)
                VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING *""",
                (viewer["id"], agent["id"], leg["customer_leg"], leg["agent_leg"], conf, mode, ct._acct()))
            m = cur.fetchone()
    mid = str(m["id"])
    try:
        resp = ct._tx("POST", "/v2/calls", {
            "connection_id": ct.voice_app(),
            "to": f"sip:{viewer['sip_username']}@sip.telnyx.com",
            "from": agent.get("phone_number") or viewer.get("phone_number") or "",
            "timeout_secs": 30,
            "custom_headers": [{"name": "X-DN-Monitor", "value": mid}],
            "client_state": ct.D["cs_encode"]("mon:" + mid),
            "command_id": "mon-" + mid})
        lleg = ((resp or {}).get("data") or {}).get("call_control_id") or ""
    except Exception as exc:
        log.warning("Live listen: could not ring listener %s: %s", viewer["id"], getattr(exc, "detail", exc))
        lleg = ""
    with ct._db() as conn:
        with conn.cursor() as cur:
            if lleg:
                cur.execute("UPDATE public.live_monitors SET listener_leg=%s WHERE id=%s RETURNING *", (lleg, mid))
            else:
                cur.execute("""UPDATE public.live_monitors SET status='failed', error='Could not reach your dialer',
                    ended_at=now() WHERE id=%s RETURNING *""", (mid,))
            m = cur.fetchone()
    if not lleg:
        raise LiveError("Could not reach your dialer. Keep the dialer open and signed in.", 502)
    return _mon_json(m)


def set_mode(viewer, mid, mode):
    if mode not in ROLES:
        raise LiveError("Unknown mode", 422)
    m = _mine(viewer, mid)
    if m["status"] == "active" and m["listener_leg"]:
        body = {"call_control_id": m["listener_leg"], "supervisor_role": ROLES[mode]}
        if mode == "whisper":
            body["whisper_call_control_ids"] = [m["agent_leg"]]
        try:
            with ct._in_acct(m.get("tx_account")):
                ct._tx("POST", f"/v2/conferences/{m['conference_id']}/actions/update", body)
        except Exception as exc:
            log.warning("Live listen: mode change failed for %s: %s", mid, getattr(exc, "detail", exc))
            raise LiveError("Could not switch. You are still in the previous mode.", 502)
    with ct._db() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE public.live_monitors SET mode=%s WHERE id=%s RETURNING *", (mode, mid))
            m = cur.fetchone()
    return _mon_json(m)


def stop(viewer, mid):
    m = _mine(viewer, mid, open_only=False)
    _end(m, "stopped")
    return {"ended": True}


def status(viewer, mid):
    return _mon_json(_mine(viewer, mid, open_only=False))


def _mine(viewer, mid, open_only=True):
    try:
        uuid.UUID(str(mid))
    except ValueError:
        raise LiveError("Not found", 404)
    with ct._db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM public.live_monitors WHERE id=%s AND listener_id=%s", (mid, viewer["id"]))
            m = cur.fetchone()
    if not m or (open_only and m["ended_at"]):
        raise LiveError("Listening has ended", 404)
    return m


def _end(m, reason):
    with ct._db() as conn:
        with conn.cursor() as cur:
            cur.execute("""UPDATE public.live_monitors SET status='ended', ended_at=now(),
                error=CASE WHEN error='' THEN %s ELSE error END WHERE id=%s AND ended_at IS NULL""", (reason, m["id"]))
    if m.get("listener_leg"):
        with ct._in_acct(m.get("tx_account")):
            ct._hangup(m["listener_leg"])


def end_for_customer(customer_leg):
    """The listened call ended: hang up every listener on it."""
    with ct._db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM public.live_monitors WHERE customer_leg=%s AND ended_at IS NULL", (customer_leg,))
            rows = cur.fetchall()
    for m in rows:
        _end(m, "call ended")


# ---------------------------------------------------------------- webhooks (client_state "mon:<id>")
def on_event(event, mid, payload):
    with ct._db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM public.live_monitors WHERE id=%s", (mid,))
            m = cur.fetchone()
    if not m:
        return
    leg = payload.get("call_control_id") or m["listener_leg"]
    if event == "call.answered":
        if m["ended_at"]:
            ct._hangup(leg)
            return
        body = {"call_control_id": leg, "supervisor_role": ROLES.get(m["mode"], "monitor"), "beep_enabled": "never"}
        if m["mode"] == "whisper":
            body["whisper_call_control_ids"] = [m["agent_leg"]]
        try:
            ct._tx("POST", f"/v2/conferences/{m['conference_id']}/actions/join", body)
            new_status, err = "active", ""
            log.info("Live listen %s: listener joined (%s)", mid, m["mode"])
        except Exception as exc:
            log.warning("Live listen %s: join failed: %s", mid, getattr(exc, "detail", exc))
            new_status, err = "failed", "The call already ended"
            ct._hangup(leg)
        with ct._db() as conn:
            with conn.cursor() as cur:
                cur.execute("""UPDATE public.live_monitors SET status=%s, error=%s, listener_leg=%s,
                    ended_at=CASE WHEN %s='failed' THEN now() ELSE ended_at END WHERE id=%s""",
                    (new_status, err, leg, new_status, mid))
    elif event == "call.hangup":
        cause = str(payload.get("hangup_cause") or "")
        with ct._db() as conn:
            with conn.cursor() as cur:
                cur.execute("""UPDATE public.live_monitors SET status=CASE WHEN status='dialing' THEN 'failed' ELSE 'ended' END,
                    error=CASE WHEN error='' AND status='dialing' THEN 'Your dialer did not pick up' ELSE error END,
                    ended_at=now() WHERE id=%s AND ended_at IS NULL""", (mid,))
        log.info("Live listen %s: listener leg ended (%s)", mid, cause)
