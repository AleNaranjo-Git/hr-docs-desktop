-- =========================
-- EXTENSIONS
-- =========================
create extension if not exists "pgcrypto";

-- =========================
-- FIRMS
-- =========================
create table if not exists public.firms (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  legal_id text not null,
  created_by uuid not null references auth.users(id),
  is_active boolean not null default true,
  created_at timestamptz not null default now()
);

-- =========================
-- PROFILES
-- =========================
create table if not exists public.profiles (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id),
  firm_id uuid not null references public.firms(id) on delete cascade,

  full_name text not null,
  role text not null,

  is_active boolean not null default true,
  created_at timestamptz not null default now()
);

create unique index if not exists idx_profiles_user_id
  on public.profiles(user_id);

-- =========================
-- COMPANY CLIENTS
-- =========================
create table if not exists public.company_clients (
  id uuid primary key default gen_random_uuid(),
  firm_id uuid not null references public.firms(id) on delete cascade,

  name text not null,
  legal_id text not null,
  description text null,

  is_active boolean not null default true,
  created_at timestamptz not null default now()
);

create index if not exists idx_company_clients_firm_id
  on public.company_clients(firm_id);

-- =========================
-- WORKERS
-- =========================
create table if not exists public.workers (
  id uuid primary key default gen_random_uuid(),
  firm_id uuid not null references public.firms(id) on delete cascade,
  client_id uuid not null references public.company_clients(id) on delete cascade,

  full_name text not null,
  legal_id text not null,
  position text null,

  is_active boolean not null default true,
  created_at timestamptz not null default now()
);

create index if not exists idx_workers_firm_id
  on public.workers(firm_id);

-- =========================
-- INCIDENT TYPES (CATALOG)
-- =========================
create table if not exists public.incident_types (
  id smallint primary key,
  code text not null unique,
  name text not null
);

-- =========================
-- INCIDENTS
-- =========================
create table if not exists public.incidents (
  id uuid primary key default gen_random_uuid(),
  firm_id uuid not null references public.firms(id) on delete cascade,

  worker_id uuid not null references public.workers(id) on delete cascade,
  incident_type_id smallint not null references public.incident_types(id),

  incident_date date not null,
  received_day date not null,

  observations text null,
  manual_handling boolean not null default false,

  created_at timestamptz not null default now()
);

create index if not exists idx_incidents_firm_id
  on public.incidents(firm_id);

create index if not exists idx_incidents_received_day
  on public.incidents(received_day);

-- =========================
-- DOCUMENT TEMPLATES
-- =========================
create table if not exists public.document_templates (
  id uuid primary key default gen_random_uuid(),
  firm_id uuid not null references public.firms(id) on delete cascade,

  name text not null,
  template_key text not null,
  description text null,

  is_active boolean not null default true,
  created_at timestamptz not null default now()
);

create index if not exists idx_document_templates_firm_id
  on public.document_templates(firm_id);