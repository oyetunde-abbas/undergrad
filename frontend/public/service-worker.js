// Basic service worker: caches the built app shell (JS/CSS/HTML) so the
// app loads instantly on repeat visits and satisfies PWA installability
// requirements. Deliberately does NOT cache API responses (job listings,
// saved jobs, etc.) — that data needs to stay live/fresh, and caching it
// here would risk showing stale listings or, worse, stale auth state.

const CACHE_NAME = 'undergrad-shell-v2';

self.addEventListener('install', (event) => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((names) =>
      Promise.all(
        names
          .filter((name) => name !== CACHE_NAME)
          .map((name) => caches.delete(name))
      )
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Only handle same-origin GET requests for the app shell itself.
  // Everything else (API calls to the backend, cross-origin requests)
  // passes straight through untouched.
  if (event.request.method !== 'GET' || url.origin !== self.location.origin) {
    return;
  }

  // Never cache API-shaped paths, even if same-origin (covers the case of
  // a same-domain deployment where frontend and backend share an origin).
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/auth/') ||
      url.pathname.startsWith('/jobs') || url.pathname.startsWith('/saved') ||
      url.pathname.startsWith('/applications') || url.pathname.startsWith('/profile') ||
      url.pathname.startsWith('/submit') || url.pathname.startsWith('/feedback')) {
    return;
  }

  event.respondWith(
    caches.match(event.request).then((cached) => {
      const networkFetch = fetch(event.request)
        .then((response) => {
          if (response.ok) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
          }
          return response;
        })
        .catch(() => cached); // offline fallback to whatever's cached, if anything

      // Only content-hashed build files (/assets/...) are safe to serve cache-first,
      // because a new build always gets a new filename. EVERYTHING else (index.html,
      // /src/* in dev, icons, manifest) is network-first, so a redesign or redeploy
      // shows up on the very next load instead of one reload later.
      const isHashedAsset = url.pathname.startsWith('/assets/');
      if (isHashedAsset) {
        return cached || networkFetch;
      }
      return networkFetch.then((r) => r || cached).catch(() => cached);
    })
  );
});
