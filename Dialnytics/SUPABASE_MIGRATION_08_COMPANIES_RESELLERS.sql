-- Dialnytics: companies (multi-user accounts), owners/agents, resellers, live presence.
-- The app runs this automatically on startup; running it manually is safe and repeatable.
-- Run SUPABASE_MIGRATION_07 first if it was never applied.
-- 08: companies (accounts), owners/agents, resellers, live presence
CREATE TABLE IF NOT EXISTS public.dialnytics_accounts (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL,
    reseller_id uuid REFERENCES public.dialnytics_users(id) ON DELETE SET NULL,
    notes text NOT NULL DEFAULT '',
    created_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE public.dialnytics_users ADD COLUMN IF NOT EXISTS account_id uuid REFERENCES public.dialnytics_accounts(id) ON DELETE SET NULL;
ALTER TABLE public.dialnytics_users ADD COLUMN IF NOT EXISTS account_role text NOT NULL DEFAULT 'agent';
ALTER TABLE public.dialnytics_users ADD COLUMN IF NOT EXISTS user_type text NOT NULL DEFAULT 'customer';
CREATE INDEX IF NOT EXISTS dialnytics_users_account_idx ON public.dialnytics_users(account_id);
CREATE INDEX IF NOT EXISTS dialnytics_accounts_reseller_idx ON public.dialnytics_accounts(reseller_id);
CREATE TABLE IF NOT EXISTS public.user_presence (
    user_id uuid PRIMARY KEY REFERENCES public.dialnytics_users(id) ON DELETE CASCADE,
    status text NOT NULL DEFAULT 'online',
    call_number text NOT NULL DEFAULT '',
    call_direction text NOT NULL DEFAULT '',
    call_started_at timestamptz,
    updated_at timestamptz NOT NULL DEFAULT now()
);
-- Every existing customer becomes the owner of its own company (company id = user id).
INSERT INTO public.dialnytics_accounts(id, name)
    SELECT u.id, COALESCE(NULLIF(u.name, ''), u.email) FROM public.dialnytics_users u
    WHERE u.account_id IS NULL AND u.role <> 'admin' AND u.user_type = 'customer'
    ON CONFLICT (id) DO NOTHING;
UPDATE public.dialnytics_users u SET account_id = u.id, account_role = 'owner'
    WHERE u.account_id IS NULL AND u.role <> 'admin' AND u.user_type = 'customer'
      AND EXISTS (SELECT 1 FROM public.dialnytics_accounts a WHERE a.id = u.id);
ALTER TABLE public.dialnytics_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_presence ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.dialnytics_accounts FROM anon, authenticated;
REVOKE ALL ON public.user_presence FROM anon, authenticated;
