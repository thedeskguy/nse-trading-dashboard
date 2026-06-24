"use client";
import { useEffect } from "react";

// Registers the app-shell service worker (public/sw.js) in production only,
// so it never interferes with dev HMR.
export function ServiceWorkerRegistrar() {
  useEffect(() => {
    if (process.env.NODE_ENV !== "production") return;
    if (!("serviceWorker" in navigator)) return;
    navigator.serviceWorker.register("/sw.js").catch(() => {
      /* registration is best-effort; app works without it */
    });
  }, []);
  return null;
}
