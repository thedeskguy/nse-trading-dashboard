"use client";
import { useEffect, useRef, useState } from "react";
import { createClient } from "@/lib/supabase/client";

interface QuoteMessage {
  ticker: string;
  price: number;
  change_pct: number;
}

function getWsBase(): string {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  return apiUrl.replace(/^http:\/\//, "ws://").replace(/^https:\/\//, "wss://");
}

/**
 * Connects to /api/v1/ws/quote/{ticker} and pushes live price + change_pct.
 * Reconnects automatically on disconnect with exponential back-off.
 * Falls back to null values if the socket is not yet connected or fails.
 */
export function useWebSocketQuote(ticker: string): QuoteMessage | null {
  const [quote, setQuote] = useState<QuoteMessage | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const cancelledRef = useRef(false);
  const retryDelay = useRef(2000);

  useEffect(() => {
    cancelledRef.current = false;
    retryDelay.current = 2000;

    async function connect() {
      if (cancelledRef.current) return;

      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();
      if (!session || cancelledRef.current) return;

      const url = `${getWsBase()}/api/v1/ws/quote/${encodeURIComponent(ticker)}?token=${session.access_token}`;
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onmessage = (e) => {
        try {
          setQuote(JSON.parse(e.data) as QuoteMessage);
          retryDelay.current = 2000; // reset on success
        } catch { /* ignore malformed frames */ }
      };

      ws.onclose = (ev) => {
        if (cancelledRef.current) return;
        // 4401 = auth rejected — don't retry
        if (ev.code === 4401) return;
        const delay = Math.min(retryDelay.current, 30_000);
        retryDelay.current = delay * 2;
        setTimeout(connect, delay);
      };
    }

    connect();

    return () => {
      cancelledRef.current = true;
      wsRef.current?.close();
    };
  }, [ticker]);

  return quote;
}
