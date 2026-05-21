"use client";

import { useEffect, useMemo, useRef } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import {
  claimSession,
  clearLocalSessionId,
  getLocalSessionId,
} from "@/lib/session/sessionClaim";

const POLL_INTERVAL_MS = 60_000;

export function SessionWatcher({ userId }: { userId: string }) {
  const supabase = useMemo(() => createClient(), []);
  const router = useRouter();
  const kickedRef = useRef(false);

  useEffect(() => {
    let cancelled = false;

    const kick = async () => {
      if (kickedRef.current || cancelled) return;
      kickedRef.current = true;
      clearLocalSessionId();
      await supabase.auth.signOut();
      router.replace("/login?reason=signed-in-elsewhere");
    };

    const verifyOrClaim = async () => {
      if (cancelled || kickedRef.current) return;
      const local = getLocalSessionId();
      const { data, error } = await supabase
        .from("user_sessions")
        .select("session_id")
        .eq("user_id", userId)
        .maybeSingle();

      if (error) {
        console.warn("[session] verify failed", error.message);
        return;
      }

      if (!data) {
        await claimSession(supabase, userId);
        return;
      }

      if (!local) {
        await claimSession(supabase, userId);
        return;
      }

      if (data.session_id !== local) {
        await kick();
      }
    };

    verifyOrClaim();

    const channel = supabase
      .channel(`user_sessions:${userId}`)
      .on(
        "postgres_changes",
        {
          event: "*",
          schema: "public",
          table: "user_sessions",
          filter: `user_id=eq.${userId}`,
        },
        (payload) => {
          const next = (payload.new ?? {}) as { session_id?: string };
          const local = getLocalSessionId();
          if (next.session_id && local && next.session_id !== local) {
            kick();
          }
        }
      )
      .subscribe();

    const intervalId = window.setInterval(verifyOrClaim, POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
      supabase.removeChannel(channel);
    };
  }, [supabase, router, userId]);

  return null;
}
