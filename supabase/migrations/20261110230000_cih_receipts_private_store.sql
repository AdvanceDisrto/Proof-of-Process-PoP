-- iNNOVULIS CIH v0.1 evidence-integrity receipts
-- Applied to Supabase BUDDY project tkrxmdonmxpeockpbazl.
-- App authenticates users via Auth0 server-side; only server-side service_role writes.
-- A database acknowledgment is not independent evidence of truth or hardware execution.
create table if not exists public.cih_receipts (
  receipt_hash text primary key
    constraint cih_receipt_hash_hex check (receipt_hash ~ '^[0-9a-f]{64}$'),
  auth0_subject text not null
    constraint cih_subject_nonempty check (length(auth0_subject) between 1 and 255),
  receipt_body jsonb not null
    constraint cih_body_schema check (receipt_body->>'schema' = 'innovulis.cih.receipt.v0.1')
    constraint cih_body_subject check (receipt_body->>'requester_subject' = auth0_subject),
  signature_b64 text not null
    constraint cih_signature_nonempty check (length(signature_b64) between 80 and 128),
  key_id text not null
    constraint cih_key_id_format check (key_id ~ '^ed25519-sha256:[0-9a-f]{24}$'),
  created_at timestamptz not null default now()
);
create index if not exists idx_cih_receipts_subject_created
  on public.cih_receipts (auth0_subject, created_at desc);
alter table public.cih_receipts enable row level security;
revoke all privileges on public.cih_receipts from public, anon, authenticated, service_role;
grant select, insert on public.cih_receipts to service_role;
comment on table public.cih_receipts is
  'CIH signed evidence-integrity receipts. RLS denies direct browser access; service_role only for server-side read/append. Hashes do not prove truth.';
