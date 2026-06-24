/* TradeDash service worker — app-shell offline support.
 * Strategy:
 *   - API / cross-origin GETs  -> network only (never serve stale market data)
 *   - same-origin navigations  -> network first, fall back to cached /offline.html
 *   - same-origin static assets -> stale-while-revalidate (hashed _next chunks, icons)
 * Bump CACHE_VERSION to invalidate old caches on deploy.
 */
const CACHE_VERSION = "tradedash-v1";
const PRECACHE = [
  "/offline.html",
  "/icon-192.png",
  "/icon-512.png",
  "/apple-icon.png",
  "/manifest.webmanifest",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE_VERSION)
      .then((cache) => cache.addAll(PRECACHE))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(keys.filter((k) => k !== CACHE_VERSION).map((k) => caches.delete(k)))
      )
      .then(() => self.clients.claim())
  );
});

function isStaticAsset(url) {
  return (
    url.pathname.startsWith("/_next/static/") ||
    url.pathname.startsWith("/icon") ||
    url.pathname.startsWith("/apple-icon") ||
    /\.(?:png|jpg|jpeg|svg|webp|gif|ico|woff2?|css|js)$/.test(url.pathname)
  );
}

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  const sameOrigin = url.origin === self.location.origin;

  // Never cache API calls or any cross-origin request (backend lives elsewhere).
  if (!sameOrigin || url.pathname.startsWith("/api/")) return;

  // Navigations: network first, offline fallback.
  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request).catch(() =>
        caches.match("/offline.html", { ignoreSearch: true }).then(
          (cached) => cached || new Response("Offline", { status: 503 })
        )
      )
    );
    return;
  }

  // Static assets: stale-while-revalidate.
  if (isStaticAsset(url)) {
    event.respondWith(
      caches.open(CACHE_VERSION).then(async (cache) => {
        const cached = await cache.match(request);
        const network = fetch(request)
          .then((res) => {
            if (res && res.status === 200) cache.put(request, res.clone());
            return res;
          })
          .catch(() => cached);
        return cached || network;
      })
    );
  }
});
