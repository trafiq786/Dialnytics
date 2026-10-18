ALTER TABLE public.power_queue_items ADD COLUMN IF NOT EXISTS call_notes text NOT NULL DEFAULT '';
