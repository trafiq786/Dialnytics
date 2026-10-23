-- Dialnytics update (Oct 2026): Twilio provider, private recordings/voicemails, cost settings.
-- The app also runs this automatically on startup. Running it manually in the
-- Supabase SQL Editor is safe and can be repeated (everything is IF NOT EXISTS).
ALTER TABLE public.dialnytics_users ADD COLUMN IF NOT EXISTS provider text NOT NULL DEFAULT 'telnyx';
ALTER TABLE public.calls ADD COLUMN IF NOT EXISTS provider text NOT NULL DEFAULT 'telnyx';
ALTER TABLE public.calls ADD COLUMN IF NOT EXISTS provider_call_id text;
CREATE INDEX IF NOT EXISTS calls_created_at_idx ON public.calls(created_at);
CREATE TABLE IF NOT EXISTS public.dialnytics_settings (
    key text PRIMARY KEY,
    value text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS public.dialnytics_recordings (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES public.dialnytics_users(id) ON DELETE CASCADE,
    call_id uuid REFERENCES public.calls(id) ON DELETE SET NULL,
    kind text NOT NULL DEFAULT 'call' CHECK (kind IN ('call','voicemail')),
    provider text NOT NULL DEFAULT 'telnyx',
    from_number text NOT NULL DEFAULT '',
    to_number text NOT NULL DEFAULT '',
    duration_seconds integer NOT NULL DEFAULT 0,
    content_type text NOT NULL DEFAULT 'audio/webm',
    size_bytes integer NOT NULL DEFAULT 0,
    storage text NOT NULL DEFAULT 'db' CHECK (storage IN ('db','supabase')),
    storage_path text,
    audio bytea,
    is_read boolean NOT NULL DEFAULT false,
    provider_ref text UNIQUE,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS dialnytics_recordings_user_idx
    ON public.dialnytics_recordings(user_id, kind, created_at DESC);
CREATE INDEX IF NOT EXISTS dialnytics_recordings_call_idx ON public.dialnytics_recordings(call_id);
ALTER TABLE public.dialnytics_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.dialnytics_recordings ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.dialnytics_settings FROM anon, authenticated;
REVOKE ALL ON public.dialnytics_recordings FROM anon, authenticated;
