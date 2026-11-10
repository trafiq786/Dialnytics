-- Twilio number verified on Telnyx: outgoing via Telnyx, incoming rings through Twilio.
-- The app also adds this column by itself on start; running it here is optional.
ALTER TABLE public.dialnytics_users ADD COLUMN IF NOT EXISTS twilio_in boolean NOT NULL DEFAULT false;
