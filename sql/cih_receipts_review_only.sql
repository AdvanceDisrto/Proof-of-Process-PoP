-- REVIEW ONLY. Not applied to the existing BUDDY Supabase project.
-- Auth0 identities are not Supabase auth.uid(); backend owns access checks.
create table if not exists public.cih_receipts (
  receipt_hash text primary key check (receipt_hash ~ '^[0-9a-f]{64}$'),
  auth0_subject text not null,
  receipt_body jsonb not null,
  signature_b64 text not null,
  key_id text not null,
  created_at timestamptz not null default now()
);
alter table public.cih_receipts enable row level security;
-- No anon/authenticated policies: the Data API must not expose private data.
revoke all on public.cih_receipts from anon, authenticated;
comment on table public.cih_receipts is 'Signed application records; NOT cryptographically immutable storage and NOT legal certification.';
