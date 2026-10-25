-- 10: call transfer between agents + advanced (server-controlled) outgoing calls
ALTER TABLE public.dialnytics_users ADD COLUMN IF NOT EXISTS adv_calling boolean NOT NULL DEFAULT false;
CREATE TABLE IF NOT EXISTS public.live_legs (
    agent_leg text PRIMARY KEY,
    user_id uuid REFERENCES public.dialnytics_users(id) ON DELETE CASCADE,
    customer_leg text NOT NULL,
    customer_number text NOT NULL DEFAULT '',
    kind text NOT NULL DEFAULT 'in',
    ref_id uuid,
    started_at timestamptz NOT NULL DEFAULT now(),
    ended_at timestamptz
);
CREATE INDEX IF NOT EXISTS live_legs_customer_idx ON public.live_legs(customer_leg) WHERE ended_at IS NULL;
CREATE INDEX IF NOT EXISTS live_legs_user_idx ON public.live_legs(user_id) WHERE ended_at IS NULL;
CREATE TABLE IF NOT EXISTS public.call_transfers (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_leg text NOT NULL,
    customer_number text NOT NULL DEFAULT '',
    from_user uuid REFERENCES public.dialnytics_users(id) ON DELETE CASCADE,
    from_leg text NOT NULL,
    to_user uuid REFERENCES public.dialnytics_users(id) ON DELETE CASCADE,
    to_number text NOT NULL DEFAULT '',
    to_leg text NOT NULL DEFAULT '',
    status text NOT NULL DEFAULT 'queued',
    reason text NOT NULL DEFAULT '',
    group_id uuid,
    log_id uuid,
    created_at timestamptz NOT NULL DEFAULT now(),
    deadline timestamptz NOT NULL DEFAULT now() + interval '3 minutes',
    ring_started_at timestamptz,
    answered_at timestamptz,
    ended_at timestamptz
);
CREATE INDEX IF NOT EXISTS call_transfers_open_idx ON public.call_transfers(status) WHERE status IN ('queued','ringing');
CREATE INDEX IF NOT EXISTS call_transfers_to_idx ON public.call_transfers(to_user, status);
CREATE TABLE IF NOT EXISTS public.cc_calls (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid REFERENCES public.dialnytics_users(id) ON DELETE CASCADE,
    agent_leg text UNIQUE NOT NULL,
    customer_leg text NOT NULL DEFAULT '',
    number text NOT NULL DEFAULT '',
    status text NOT NULL DEFAULT 'dialing',
    reason text NOT NULL DEFAULT '',
    created_at timestamptz NOT NULL DEFAULT now(),
    answered_at timestamptz,
    ended_at timestamptz
);
CREATE INDEX IF NOT EXISTS cc_calls_customer_idx ON public.cc_calls(customer_leg);
ALTER TABLE public.live_legs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.call_transfers ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cc_calls ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.live_legs FROM anon, authenticated;
REVOKE ALL ON public.call_transfers FROM anon, authenticated;
REVOKE ALL ON public.cc_calls FROM anon, authenticated;
