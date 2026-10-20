-- Safe additive migration. Run in Supabase SQL Editor before deploying code.
ALTER TABLE public.dialnytics_users ADD COLUMN IF NOT EXISTS contact_name TEXT NOT NULL DEFAULT '';
ALTER TABLE public.dialnytics_users ADD COLUMN IF NOT EXISTS contact_phone TEXT NOT NULL DEFAULT '';
ALTER TABLE public.dialnytics_users ADD COLUMN IF NOT EXISTS contact_address TEXT NOT NULL DEFAULT '';
ALTER TABLE public.dialnytics_users ADD COLUMN IF NOT EXISTS customer_notes TEXT NOT NULL DEFAULT '';
CREATE SEQUENCE IF NOT EXISTS public.dialnytics_invoice_seq;
CREATE TABLE IF NOT EXISTS public.dialnytics_invoices (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(), invoice_number TEXT NOT NULL UNIQUE,
 customer_id UUID NOT NULL REFERENCES public.dialnytics_users(id),
 customer_name TEXT NOT NULL,customer_email TEXT NOT NULL,contact_phone TEXT NOT NULL DEFAULT '',
 contact_address TEXT NOT NULL DEFAULT '',issue_date DATE NOT NULL,due_date DATE NOT NULL,
 notes TEXT NOT NULL DEFAULT '',terms TEXT NOT NULL DEFAULT '',
 subtotal_pkr NUMERIC(14,2) NOT NULL DEFAULT 0,discount_pkr NUMERIC(14,2) NOT NULL DEFAULT 0,
 tax_percent NUMERIC(5,2) NOT NULL DEFAULT 0,tax_pkr NUMERIC(14,2) NOT NULL DEFAULT 0,
 total_pkr NUMERIC(14,2) NOT NULL DEFAULT 0,
 status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','sent','paid','void')),
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW());
CREATE TABLE IF NOT EXISTS public.dialnytics_invoice_items (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),invoice_id UUID NOT NULL REFERENCES public.dialnytics_invoices(id) ON DELETE CASCADE,
 position INT NOT NULL,description TEXT NOT NULL,qty INT NOT NULL CHECK(qty>0),
 unit_price_pkr NUMERIC(14,2) NOT NULL CHECK(unit_price_pkr>=0),amount_pkr NUMERIC(14,2) NOT NULL CHECK(amount_pkr>=0));
CREATE INDEX IF NOT EXISTS dialnytics_invoice_customer_idx ON public.dialnytics_invoices(customer_id);
ALTER TABLE public.dialnytics_invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.dialnytics_invoice_items ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.dialnytics_invoices,public.dialnytics_invoice_items FROM anon,authenticated;
