-- Migration 002: user_sessions table for single-session enforcement
-- Run this in Supabase Dashboard → SQL Editor. Idempotent and safe to re-run.

CREATE TABLE IF NOT EXISTS public.user_sessions (
  user_id    uuid        PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  session_id text        NOT NULL,
  updated_at timestamptz DEFAULT now()
);

-- If an older version of this table used session_nonce, rename it
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name   = 'user_sessions'
      AND column_name  = 'session_nonce'
  ) AND NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name   = 'user_sessions'
      AND column_name  = 'session_id'
  ) THEN
    EXECUTE 'ALTER TABLE public.user_sessions RENAME COLUMN session_nonce TO session_id';
  END IF;
END $$;

-- Row-level security: users can read + upsert their own row only
ALTER TABLE public.user_sessions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view their own session"   ON public.user_sessions;
DROP POLICY IF EXISTS "Users can insert their own session" ON public.user_sessions;
DROP POLICY IF EXISTS "Users can update their own session" ON public.user_sessions;

CREATE POLICY "Users can view their own session"
  ON public.user_sessions
  FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own session"
  ON public.user_sessions
  FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own session"
  ON public.user_sessions
  FOR UPDATE
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- Auto-update updated_at on every row change
CREATE OR REPLACE FUNCTION public.user_sessions_touch_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS user_sessions_touch_updated_at ON public.user_sessions;
CREATE TRIGGER user_sessions_touch_updated_at
  BEFORE UPDATE ON public.user_sessions
  FOR EACH ROW EXECUTE FUNCTION public.user_sessions_touch_updated_at();

-- Enable Realtime so other tabs/devices see updates (no-op if already added)
DO $$ BEGIN
  ALTER PUBLICATION supabase_realtime ADD TABLE public.user_sessions;
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

NOTIFY pgrst, 'reload schema';
