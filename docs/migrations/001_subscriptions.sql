-- Migration 001: subscriptions table
-- Run this in Supabase Dashboard → SQL Editor

CREATE TABLE IF NOT EXISTS public.subscriptions (
  id                   uuid        DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id              uuid        REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  subscription_id      text        UNIQUE NOT NULL,
  customer_id          text,
  plan_id              text,
  status               text        NOT NULL DEFAULT 'inactive',
  current_period_start bigint,
  current_period_end   bigint,
  created_at           timestamptz DEFAULT now(),
  updated_at           timestamptz DEFAULT now()
);

-- Index for fast per-user lookups
CREATE INDEX IF NOT EXISTS subscriptions_user_id_idx ON public.subscriptions (user_id);

-- Row-level security: users can only read their own row
ALTER TABLE public.subscriptions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own subscription"
  ON public.subscriptions
  FOR SELECT
  USING (auth.uid() = user_id);

-- Only the service role (backend webhook) can insert / update
-- (no INSERT/UPDATE policy for authenticated role — done via service role key)
