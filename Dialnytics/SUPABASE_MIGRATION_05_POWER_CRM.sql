-- Run after previous Dialnytics migrations. Does not remove existing records.
CREATE TABLE IF NOT EXISTS public.crm_leads (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
 user_id UUID NOT NULL REFERENCES public.dialnytics_users(id) ON DELETE CASCADE,
 name TEXT NOT NULL, phone TEXT NOT NULL, email TEXT NOT NULL DEFAULT '',
 status TEXT NOT NULL DEFAULT 'new' CHECK(status IN ('new','interested','callback','converted','not_interested')),
 notes TEXT NOT NULL DEFAULT '', followup_at TIMESTAMPTZ,
 consent BOOLEAN NOT NULL DEFAULT FALSE, do_not_call BOOLEAN NOT NULL DEFAULT FALSE,
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
 UNIQUE(user_id,phone)
);
CREATE TABLE IF NOT EXISTS public.power_queues (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
 user_id UUID NOT NULL REFERENCES public.dialnytics_users(id) ON DELETE CASCADE,
 mode TEXT NOT NULL CHECK(mode IN ('auto','manual')),
 delay_seconds INT NOT NULL DEFAULT 5 CHECK(delay_seconds BETWEEN 3 AND 30),
 status TEXT NOT NULL DEFAULT 'paused' CHECK(status IN ('paused','running','stopped')),
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS public.power_queue_items (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
 queue_id UUID NOT NULL REFERENCES public.power_queues(id) ON DELETE CASCADE,
 lead_id UUID NOT NULL REFERENCES public.crm_leads(id) ON DELETE CASCADE,
 position INT NOT NULL, result TEXT, finished_at TIMESTAMPTZ,
 UNIQUE(queue_id,lead_id), UNIQUE(queue_id,position)
);
CREATE INDEX IF NOT EXISTS crm_leads_owner_idx ON public.crm_leads(user_id,status);
CREATE INDEX IF NOT EXISTS power_queues_owner_idx ON public.power_queues(user_id);
CREATE INDEX IF NOT EXISTS power_items_queue_idx ON public.power_queue_items(queue_id,position);
ALTER TABLE public.crm_leads ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.power_queues ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.power_queue_items ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.crm_leads,public.power_queues,public.power_queue_items FROM anon,authenticated;
