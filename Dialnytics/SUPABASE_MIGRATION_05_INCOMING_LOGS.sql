-- Run once in Supabase SQL Editor before deploying this code.
-- Non-destructive link from Voice API inbound call group to its call log.
ALTER TABLE public.incoming_call_groups
    ADD COLUMN IF NOT EXISTS call_log_id uuid REFERENCES public.calls(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS incoming_call_groups_call_log_idx
    ON public.incoming_call_groups(call_log_id);
