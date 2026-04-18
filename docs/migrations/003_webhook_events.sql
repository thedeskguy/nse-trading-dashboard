-- Migration 003: webhook_events — idempotency table for Razorpay webhooks
-- Run in Supabase SQL editor (service role).

create table if not exists public.webhook_events (
    id          text        primary key,   -- SHA-256 of raw request body
    event_type  text        not null,
    processed_at timestamptz not null default now()
);

-- Disable RLS — only the service role writes here (no user-facing rows)
alter table public.webhook_events disable row level security;
