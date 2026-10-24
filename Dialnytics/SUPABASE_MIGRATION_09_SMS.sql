-- Dialnytics 09: Text messages (SMS). Safe to run more than once.
-- The app also runs this automatically on start-up.
ALTER TABLE public.dialnytics_users ADD COLUMN IF NOT EXISTS sms_enabled boolean NOT NULL DEFAULT false;
CREATE TABLE IF NOT EXISTS public.sms_messages (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid REFERENCES public.dialnytics_users(id) ON DELETE CASCADE,
    our_number text NOT NULL,
    contact_number text NOT NULL,
    direction text NOT NULL CHECK (direction IN ('in','out')),
    body text NOT NULL DEFAULT '',
    media jsonb NOT NULL DEFAULT '[]'::jsonb,
    status text NOT NULL DEFAULT '',
    error text NOT NULL DEFAULT '',
    provider text NOT NULL DEFAULT 'telnyx',
    provider_id text UNIQUE,
    is_read boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS sms_messages_thread_idx ON public.sms_messages(user_id, contact_number, created_at DESC);
CREATE INDEX IF NOT EXISTS sms_messages_unread_idx ON public.sms_messages(user_id) WHERE direction = 'in' AND is_read = false;
ALTER TABLE public.sms_messages ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.sms_messages FROM anon, authenticated;
