-- Purane leads jin ke UK number "+440..." format mein hain (jaise +4407980680192) unhein sahi karein.
-- Supabase > SQL Editor mein aik dafa chalayein.
UPDATE public.crm_leads l
SET phone = '+44' || substr(l.phone, 5), updated_at = now()
WHERE l.phone ~ '^\+440[1-9][0-9]{8,9}$'
  AND NOT EXISTS (SELECT 1 FROM public.crm_leads d
                  WHERE d.user_id = l.user_id AND d.phone = '+44' || substr(l.phone, 5));
