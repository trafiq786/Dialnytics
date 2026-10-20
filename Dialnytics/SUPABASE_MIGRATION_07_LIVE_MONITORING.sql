-- Run once in Supabase SQL Editor before deploying the live monitoring build.
CREATE TABLE IF NOT EXISTS public.live_agent_presence (
  user_id uuid PRIMARY KEY REFERENCES public.dialnytics_users(id) ON DELETE CASCADE,
  state text NOT NULL DEFAULT 'available' CHECK (state IN ('available','ringing','on_call')),
  direction text NOT NULL DEFAULT '',
  phone_number text NOT NULL DEFAULT '',
  call_started_at timestamptz,
  last_seen timestamptz NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS live_agent_presence_seen_idx ON public.live_agent_presence(last_seen);
