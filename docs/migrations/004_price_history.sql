-- 004_price_history.sql — persistent EOD OHLCV store + precomputed scanner results.
-- Written by the nightly GitHub Actions pipeline (service-role key); read by the backend.
-- RLS enabled with NO policies: only the service-role key (which bypasses RLS) can access.

create table if not exists price_history (
  ticker  text not null,
  date    date not null,
  open    double precision not null,
  high    double precision not null,
  low     double precision not null,
  close   double precision not null,
  volume  bigint not null,
  primary key (ticker, date)
);

create index if not exists idx_price_history_ticker_date
  on price_history (ticker, date desc);

create table if not exists scan_results (
  index_name  text primary key,
  computed_at timestamptz not null default now(),
  payload     jsonb not null
);

alter table price_history enable row level security;
alter table scan_results enable row level security;
