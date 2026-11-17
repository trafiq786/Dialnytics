-- Announcements (app bhi khud bana deti hai start hone pe)

CREATE TABLE IF NOT EXISTS public.announcements (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    title text NOT NULL DEFAULT '',
    message text NOT NULL DEFAULT '',
    kind text NOT NULL DEFAULT 'update',          -- update | feature | maint | urgent
    audience text NOT NULL DEFAULT 'all',         -- all | owners | direct | partners | company
    account_id uuid,                              -- audience = company
    include_partners boolean NOT NULL DEFAULT true,
    show_popup boolean NOT NULL DEFAULT true,
    show_banner boolean NOT NULL DEFAULT true,
    popup_mode text NOT NULL DEFAULT 'once',      -- once | until_read | every_login
    link text NOT NULL DEFAULT '',
    status text NOT NULL DEFAULT 'live',          -- draft | live | ended
    ends_on date,
    created_at timestamptz NOT NULL DEFAULT now(),
    published_at timestamptz,
    ended_at timestamptz
);
CREATE TABLE IF NOT EXISTS public.announcement_reads (
    announcement_id uuid REFERENCES public.announcements(id) ON DELETE CASCADE,
    user_id uuid REFERENCES public.dialnytics_users(id) ON DELETE CASCADE,
    read_at timestamptz,
    popup_seen_at timestamptz,
    popup_session text NOT NULL DEFAULT '',
    remind_after timestamptz,
    banner_closed boolean NOT NULL DEFAULT false,
    PRIMARY KEY (announcement_id, user_id)
);
ALTER TABLE public.announcements ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.announcement_reads ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.announcements FROM anon, authenticated;
REVOKE ALL ON public.announcement_reads FROM anon, authenticated;
