-- Optional: the app runs this by itself on start.
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
