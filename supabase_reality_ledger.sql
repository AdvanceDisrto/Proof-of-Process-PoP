create extension if not exists pgcrypto;

create table if not exists public.reality_ledger (
    id uuid primary key default gen_random_uuid(),
    created_at timestamptz not null default timezone('utc', now()),
    receipt_id text unique not null,
    instance_id text not null,
    provider_name text,
    hardware_type text not null,
    workload_hash text not null check (workload_hash ~ '^[0-9a-fA-F]{64}$'),
    evidence_sha256 text not null check (evidence_sha256 ~ '^[0-9a-fA-F]{64}$'),
    attestation_verification text not null check (attestation_verification in ('VERIFIED','UNVERIFIED','REJECTED')),
    physical_gate_status text not null check (physical_gate_status in ('ACTION_REQUIRED','MEASURED_PASS')),
    evidence_origin text not null check (evidence_origin not in ('SIMULATED','MOCK','SYNTHETIC')),
    verifier_receipt_id text,
    identity_root_id text,
    identity_epoch text,
    receipt_signature text,
    delegation_certificate jsonb,
    metadata jsonb not null default '{}'::jsonb
);

alter table public.reality_ledger enable row level security;
revoke all on public.reality_ledger from anon, authenticated;
comment on table public.reality_ledger is 'i™ evidence ledger; provider credentials are separate from cryptographic identity.';
do $
begin
    if not exists (
        select 1
        from pg_publication_rel pr
        join pg_class c on c.oid = pr.prrelid
        join pg_namespace n on n.oid = c.relnamespace
        join pg_publication p on p.oid = pr.prpubid
        where p.pubname = 'supabase_realtime'
          and n.nspname = 'public'
          and c.relname = 'reality_ledger'
    ) then
        alter publication supabase_realtime add table public.reality_ledger;
    end if;
end $;
