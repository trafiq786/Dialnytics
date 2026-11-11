-- Live listening per user (app bhi khud bana deti hai start hone pe)
ALTER TABLE public.dialnytics_users ADD COLUMN IF NOT EXISTS live_route boolean NOT NULL DEFAULT false;
