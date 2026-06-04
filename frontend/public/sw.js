/**
 * Service Worker — caches app shell for offline access.
 * Strategy: network-first for API, cache-first for static assets.
 */
const CACHE = "wellness-os-v1";
const STATIC = ["index.html", "assets/index-DPVTLOha.js", "assets/index-ujnm4VAg.css"];

self.addEventListener("install", (ev) => {
  ev.waitUntil(
    caches.open(CACHE).then(c => c.addAll(STATIC)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (ev) => {
  ev.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (ev) => {
  const { request } = ev;
  const url = new URL(request.url);

  // Network-first for API calls
  if (url.pathname.startsWith("/api/")) {
    ev.respondWith(
      fetch(request).catch(() => new Response(JSON.stringify({ error: "offline" }), {
        status: 503, headers: { "Content-Type": "application/json" }
      }))
    );
    return;
  }

  // Cache-first for static assets
  ev.respondWith(
    caches.match(request).then(cached => cached || fetch(request).then(r => {
      if (r.ok) {
        const clone = r.clone();
        caches.open(CACHE).then(c => c.put(request, clone));
      }
      return r;
    }))
  );
});

// Listen for sync messages from the app
self.addEventListener("message", (ev) => {
  if (ev.data?.type === "SKIP_WAITING") self.skipWaiting();
});