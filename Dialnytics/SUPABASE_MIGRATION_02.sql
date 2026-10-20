-- Run in Supabase SQL editor BEFORE deploying this build.
CREATE TABLE IF NOT EXISTS public.dialnytics_contacts (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 user_id uuid NOT NULL REFERENCES public.dialnytics_users(id) ON DELETE CASCADE,
 name text NOT NULL, number text NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS dialnytics_contacts_user_idx ON public.dialnytics_contacts(user_id);
ALTER TABLE public.dialnytics_contacts ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.dialnytics_contacts FROM anon, authenticated;
