-- iNNOVULIS CIH / BUDDY Supabase optional .krdid receipt replica
-- Applied live to Supabase project tkrxmdonmxpeockpbazl on 2026-11-11 UTC.
-- Durable source of truth for issuance remains local SQLite + Ed25519 signature.
-- This table is a SECONDARY COPY and is not immutable against DB administrators.
-- This script updates the earlier auth0_subject-based cih_receipts schema.
BEGIN;

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'cih_receipts'
          AND column_name = 'auth0_subject'
  ) THEN
    EXECUTE 'ALTER TABLE public.cih_receipts RENAME COLUMN auth0_subject TO requester_subject';
  END IF;

  IF EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid='public.cih_receipts'::regclass AND conname='cih_subject_nonempty'
  ) THEN
    EXECUTE 'ALTER TABLE public.cih_receipts RENAME CONSTRAINT cih_subject_nonempty TO cih_requester_subject_nonempty';
  END IF;

  IF EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid='public.cih_receipts'::regclass AND conname='cih_body_subject'
  ) THEN
    EXECUTE 'ALTER TABLE public.cih_receipts RENAME CONSTRAINT cih_body_subject TO cih_body_requester_subject';
  END IF;
END $$;

ALTER INDEX IF EXISTS public.idx_cih_receipts_subject_created RENAME TO idx_cih_receipts_requester_created;
ALTER TABLE public.cih_receipts ENABLE ROW LEVEL SECURITY;
REVOKE ALL PRIVILEGES ON public.cih_receipts FROM PUBLIC, anon, authenticated, service_role;
GRANT SELECT, INSERT ON public.cih_receipts TO service_role;

COMMENT ON TABLE public.cih_receipts IS
'Optional CIH Ed25519 signed-receipt replica. Source identity is an enrolled local .krdid key, not Supabase Auth. Server-side only. Not an immutable ledger or hardware trust anchor.';

COMMIT;
