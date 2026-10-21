-- Run in Supabase SQL Editor BEFORE deploying this code.
ALTER TABLE public.dialnytics_users
    ADD COLUMN IF NOT EXISTS is_demo BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS trial_started_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS trial_expires_at TIMESTAMPTZ;
CREATE INDEX IF NOT EXISTS idx_dialnytics_demo_expiry
    ON public.dialnytics_users(trial_expires_at) WHERE is_demo = TRUE;
