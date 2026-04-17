import type { SupabaseClient } from "@supabase/supabase-js";

const STORAGE_KEY = "tradedash.session_id";

function newSessionId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

export function getLocalSessionId(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(STORAGE_KEY);
}

export function setLocalSessionId(id: string): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(STORAGE_KEY, id);
}

export function clearLocalSessionId(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(STORAGE_KEY);
}

export async function claimSession(
  supabase: SupabaseClient,
  userId: string
): Promise<string> {
  const sessionId = newSessionId();
  setLocalSessionId(sessionId);
  const { error } = await supabase
    .from("user_sessions")
    .upsert({ user_id: userId, session_id: sessionId }, { onConflict: "user_id" });
  if (error) {
    console.warn("[session] claim upsert failed", error.message);
  }
  return sessionId;
}
