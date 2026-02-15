-- =========================================================
-- EXTENSIONS
-- =========================================================
create extension if not exists "pgcrypto";

-- =========================================================
-- FIRMS
-- =========================================================
create table if not exists public.firms (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  description text null,
  is_active boolean not null default true,
  created_by uuid not null references auth.users(id),
  created_at timestamptz not null default now()
);

create index if not exists idx_firms_created_by
  on public.firms(created_by);

alter table public.firms enable row level security;

drop policy if exists firms_insert_creator on public.firms;
create policy firms_insert_creator
on public.firms for insert
to public
with check (created_by = (select auth.uid()));

drop policy if exists firms_select_own on public.firms;
create policy firms_select_own
on public.firms for select
to public
using ((id = current_firm_id()) and (is_active = true));

drop policy if exists firms_update_own on public.firms;
create policy firms_update_own
on public.firms for update
to public
using (id = current_firm_id())
with check (id = current_firm_id());


-- =========================================================
-- PROFILES
-- =========================================================
create table if not exists public.profiles (
  user_id uuid primary key references auth.users(id),
  firm_id uuid not null references public.firms(id) on delete cascade,
  role text not null default 'admin',
  is_active boolean not null default true,
  created_at timestamptz not null default now()
);

create index if not exists idx_profiles_firm_id
  on public.profiles(firm_id);

alter table public.profiles enable row level security;

drop policy if exists profiles_insert_self on public.profiles;
create policy profiles_insert_self
on public.profiles for insert
to public
with check (user_id = (select auth.uid()));

drop policy if exists profiles_select_self on public.profiles;
create policy profiles_select_self
on public.profiles for select
to public
using ((user_id = (select auth.uid())) and (is_active = true));

drop policy if exists profiles_update_self on public.profiles;
create policy profiles_update_self
on public.profiles for update
to public
using (user_id = (select auth.uid()))
with check (user_id = (select auth.uid()));


-- =========================================================
-- current_firm_id() FUNCTION
-- (matches what you pasted)
-- =========================================================
create or replace function public.current_firm_id()
returns uuid
language sql
stable
as $function$
  select p.firm_id
  from public.profiles p
  where p.user_id = (select auth.uid())
    and p.is_active = true
  limit 1
$function$;


-- =========================================================
-- COMPANY CLIENTS
-- =========================================================
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

create unique index if not exists uq_company_clients_firm_legal_id
  on public.company_clients(firm_id, legal_id);

alter table public.company_clients enable row level security;

drop policy if exists company_clients_insert on public.company_clients;
create policy company_clients_insert
on public.company_clients for insert
to public
with check (firm_id = current_firm_id());

drop policy if exists company_clients_select on public.company_clients;
create policy company_clients_select
on public.company_clients for select
to public
using (firm_id = current_firm_id());

drop policy if exists company_clients_update on public.company_clients;
create policy company_clients_update
on public.company_clients for update
to public
using (firm_id = current_firm_id())
with check (firm_id = current_firm_id());


-- =========================================================
-- WORKERS
-- (IMPORTANT: columns are company_client_id + national_id)
-- =========================================================
create table if not exists public.workers (
  id uuid primary key default gen_random_uuid(),
  firm_id uuid not null references public.firms(id) on delete cascade,
  company_client_id uuid not null references public.company_clients(id) on delete cascade,
  full_name text not null,
  national_id text not null,
  is_active boolean not null default true,
  created_at timestamptz not null default now()
);

create index if not exists idx_workers_firm_id
  on public.workers(firm_id);

create index if not exists idx_workers_company_client_id
  on public.workers(company_client_id);

create unique index if not exists uq_workers_firm_national_id
  on public.workers(firm_id, national_id);

alter table public.workers enable row level security;

drop policy if exists workers_select on public.workers;
create policy workers_select
on public.workers for select
to public
using ((firm_id = current_firm_id()) and (is_active = true));

drop policy if exists workers_insert on public.workers;
create policy workers_insert
on public.workers for insert
to public
with check (
  (firm_id = current_firm_id())
  and exists (
    select 1
    from public.company_clients cc
    where cc.id = workers.company_client_id
      and cc.firm_id = current_firm_id()
      and cc.is_active = true
  )
);

drop policy if exists workers_update on public.workers;
create policy workers_update
on public.workers for update
to public
using (firm_id = current_firm_id())
with check (firm_id = current_firm_id());


-- =========================================================
-- INCIDENT TYPES (CATALOG)
-- =========================================================
create table if not exists public.incident_types (
  id smallint primary key,
  code text not null unique,
  name text not null
);

alter table public.incident_types enable row level security;

drop policy if exists incident_types_select_all on public.incident_types;
create policy incident_types_select_all
on public.incident_types for select
to public
using (true);


-- =========================================================
-- INCIDENTS
-- =========================================================
create table if not exists public.incidents (
  id uuid primary key default gen_random_uuid(),
  firm_id uuid not null references public.firms(id) on delete cascade,
  worker_id uuid not null references public.workers(id) on delete cascade,
  incident_type_id smallint not null references public.incident_types(id),
  incident_date date not null,
  observations text null,
  manual_handling boolean not null default false,
  created_at timestamptz not null default now(),
  received_day date not null,
  code text null
);

create index if not exists idx_incidents_firm_id
  on public.incidents(firm_id);

create index if not exists idx_incidents_worker_id
  on public.incidents(worker_id);

create index if not exists idx_incidents_date
  on public.incidents(incident_date);

create index if not exists idx_incidents_type
  on public.incidents(incident_type_id);

create index if not exists idx_incidents_received_day
  on public.incidents(received_day);

-- unique per firm + code
create unique index if not exists uq_incidents_firm_code
  on public.incidents(firm_id, code);

alter table public.incidents enable row level security;

drop policy if exists incidents_select on public.incidents;
create policy incidents_select
on public.incidents for select
to public
using (firm_id = current_firm_id());

drop policy if exists incidents_insert on public.incidents;
create policy incidents_insert
on public.incidents for insert
to public
with check (firm_id = current_firm_id());

drop policy if exists incidents_update on public.incidents;
create policy incidents_update
on public.incidents for update
to public
using (firm_id = current_firm_id())
with check (firm_id = current_firm_id());

drop policy if exists incidents_delete on public.incidents;
create policy incidents_delete
on public.incidents for delete
to public
using (firm_id = current_firm_id());


-- =========================================================
-- INCIDENT CODE COUNTER TABLE
-- =========================================================
create table if not exists public.firm_incident_counters (
  firm_id uuid not null references public.firms(id) on delete cascade,
  year int not null,
  last_number int not null default 0,
  updated_at timestamptz not null default now(),
  primary key (firm_id, year)
);

alter table public.firm_incident_counters enable row level security;

drop policy if exists firm_incident_counters_select on public.firm_incident_counters;
create policy firm_incident_counters_select
on public.firm_incident_counters for select
to public
using (firm_id = current_firm_id());

drop policy if exists firm_incident_counters_insert on public.firm_incident_counters;
create policy firm_incident_counters_insert
on public.firm_incident_counters for insert
to public
with check (firm_id = current_firm_id());

drop policy if exists firm_incident_counters_update on public.firm_incident_counters;
create policy firm_incident_counters_update
on public.firm_incident_counters for update
to public
using (firm_id = current_firm_id())
with check (firm_id = current_firm_id());


-- =========================================================
-- INCIDENT CODE GENERATION FUNCTIONS + TRIGGER
-- (matches what you already ran conceptually)
-- =========================================================
create or replace function public.generate_incident_code_per_firm(p_firm_id uuid)
returns text
language plpgsql
as $$
declare
  v_year int;
  v_next int;
begin
  v_year := extract(year from now())::int;

  insert into public.firm_incident_counters (firm_id, year, last_number)
  values (p_firm_id, v_year, 1)
  on conflict (firm_id, year)
  do update set
    last_number = public.firm_incident_counters.last_number + 1,
    updated_at = now()
  returning last_number into v_next;

  return v_year::text || '-' || lpad(v_next::text, 3, '0');
end;
$$;

create or replace function public.incidents_set_code_per_firm()
returns trigger
language plpgsql
as $$
begin
  if new.code is null or length(trim(new.code)) = 0 then
    if new.firm_id is null then
      raise exception 'incidents.firm_id is required to generate code';
    end if;

    new.code := public.generate_incident_code_per_firm(new.firm_id);
  end if;

  return new;
end;
$$;

drop trigger if exists trg_incidents_set_code on public.incidents;

create trigger trg_incidents_set_code
before insert on public.incidents
for each row
execute function public.incidents_set_code_per_firm();


-- =========================================================
-- DOCUMENT TEMPLATES
-- (IMPORTANT: has company_client_id + storage_path + version)
-- =========================================================
create table if not exists public.document_templates (
  id uuid primary key default gen_random_uuid(),
  firm_id uuid not null references public.firms(id) on delete cascade,
  company_client_id uuid not null references public.company_clients(id) on delete cascade,
  template_key text not null,
  storage_path text not null,
  version integer not null default 1,
  is_active boolean not null default true,
  created_at timestamptz not null default now()
);

create index if not exists idx_templates_firm_id
  on public.document_templates(firm_id);

create index if not exists idx_templates_company_client_id
  on public.document_templates(company_client_id);

-- unique only for active rows
create unique index if not exists uq_templates_firm_client_key_active
  on public.document_templates(firm_id, company_client_id, template_key, is_active)
  where is_active = true;

alter table public.document_templates enable row level security;

drop policy if exists document_templates_insert on public.document_templates;
create policy document_templates_insert
on public.document_templates for insert
to public
with check (firm_id = current_firm_id());

drop policy if exists document_templates_select on public.document_templates;
create policy document_templates_select
on public.document_templates for select
to public
using ((firm_id = current_firm_id()) and (is_active = true));

drop policy if exists document_templates_update on public.document_templates;
create policy document_templates_update
on public.document_templates for update
to public
using (firm_id = current_firm_id())
with check (firm_id = current_firm_id());