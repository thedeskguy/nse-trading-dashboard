import { useQuery, useMutation } from "@tanstack/react-query";
import { apiFetch } from "./client";
import { createClient } from "@/lib/supabase/client";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface SubscriptionStatus {
  plan: "free" | "pro";
  status: "active" | "inactive" | "cancelled";
  current_period_end: number | null; // Unix timestamp
}

export interface CreateSubscriptionResponse {
  subscription_id: string;
  short_url: string | null;
}

export function useSubscription() {
  return useQuery({
    queryKey: ["subscription"],
    queryFn: () => apiFetch<SubscriptionStatus>("/api/v1/payments/subscription-status"),
    staleTime: 5 * 60 * 1000,
    refetchInterval: 5 * 60 * 1000,
  });
}

export function useCreateSubscription() {
  return useMutation({
    mutationFn: async (plan: "monthly" | "annual") => {
      const supabase = createClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };
      if (session?.access_token) {
        headers["Authorization"] = `Bearer ${session.access_token}`;
      }
      const res = await fetch(`${API_BASE}/api/v1/payments/create-subscription`, {
        method: "POST",
        headers,
        body: JSON.stringify({ plan }),
      });
      if (!res.ok) throw new Error(`API error ${res.status}: ${await res.text()}`);
      return res.json() as Promise<CreateSubscriptionResponse>;
    },
  });
}
