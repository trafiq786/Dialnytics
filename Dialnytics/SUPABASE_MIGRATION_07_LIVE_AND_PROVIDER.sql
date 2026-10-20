CREATE TABLE IF NOT EXISTS public.live_agent_presence (
 user_id uuid PRIMARY KEY REFERENCES public.dialnytics_users(id) ON DELETE CASCADE,
 status text NOT NULL DEFAULT 'available', number text NOT NULL DEFAULT '',
 direction text NOT NULL DEFAULT '', started_at timestamptz,
 last_seen timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS public.user_provider_settings (
 user_id uuid PRIMARY KEY REFERENCES public.dialnytics_users(id) ON DELETE CASCADE,
 provider text NOT NULL DEFAULT 'telnyx' CHECK(provider IN ('telnyx','twilio')),
 twilio_number text
);
REVOKE ALL ON public.live_agent_presence FROM anon, authenticated;
REVOKE ALL ON public.user_provider_settings FROM anon, authenticated;
