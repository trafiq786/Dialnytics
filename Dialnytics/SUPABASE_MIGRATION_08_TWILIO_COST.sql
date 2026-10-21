-- Run on Supabase before deploying Update 08. Back up database first.
ALTER TABLE public.dialnytics_users ADD COLUMN IF NOT EXISTS provider text NOT NULL DEFAULT 'telnyx';
ALTER TABLE public.dialnytics_users ADD COLUMN IF NOT EXISTS twilio_number text;
ALTER TABLE public.calls ADD COLUMN IF NOT EXISTS provider text NOT NULL DEFAULT 'telnyx';
ALTER TABLE public.calls ADD COLUMN IF NOT EXISTS provider_call_sid text;
CREATE UNIQUE INDEX IF NOT EXISTS dialnytics_twilio_number_unique ON public.dialnytics_users(twilio_number) WHERE twilio_number IS NOT NULL AND provider='twilio';
CREATE UNIQUE INDEX IF NOT EXISTS dialnytics_provider_call_sid_unique ON public.calls(provider_call_sid) WHERE provider_call_sid IS NOT NULL;
CREATE TABLE IF NOT EXISTS public.provider_switch_history (
 id bigserial PRIMARY KEY, user_id uuid NOT NULL REFERENCES public.dialnytics_users(id),
 old_provider text NOT NULL, new_provider text NOT NULL, phone_number text,
 switched_at timestamptz NOT NULL DEFAULT now()
);
