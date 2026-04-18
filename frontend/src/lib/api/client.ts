import { createClient } from "@/lib/supabase/client";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// Warn once if deployed to production with the localhost default still set.
if (
  typeof window !== "undefined" &&
  process.env.NODE_ENV === "production" &&
  API_BASE.includes("localhost")
) {
  console.warn(
    "[TradeDash] NEXT_PUBLIC_API_URL is pointing to localhost in production. " +
    "Set it to your Railway backend URL in Vercel environment variables.",
  );
}

async function getToken(forceRefresh = false): Promise<string | null> {
  const supabase = createClient();
  if (forceRefresh) {
    const { data } = await supabase.auth.refreshSession();
    return data.session?.access_token ?? null;
  }
  const { data: { session } } = await supabase.auth.getSession();
  // Access tokens live 1h. If it's within 60s of expiry, refresh preemptively
  // so the browser doesn't race the server with an already-dead token.
  if (session?.expires_at) {
    const secondsLeft = session.expires_at - Math.floor(Date.now() / 1000);
    if (secondsLeft < 60) {
      const { data } = await supabase.auth.refreshSession();
      return data.session?.access_token ?? null;
    }
  }
  return session?.access_token ?? null;
}

export async function apiFetch<T>(path: string, params?: Record<string, string>): Promise<T> {
  const url = new URL(`${API_BASE}${path}`);
  if (params) Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v));

  const doFetch = async (token: string | null) => {
    const headers: Record<string, string> = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;
    return fetch(url.toString(), { cache: "no-store", headers });
  };

  let token = await getToken();
  let res = await doFetch(token);

  // If the server rejected the JWT, refresh once and retry.
  if (res.status === 401) {
    token = await getToken(true);
    res = await doFetch(token);
  }

  if (!res.ok) throw new Error(`API error ${res.status}: ${await res.text()}`);
  return res.json();
}
