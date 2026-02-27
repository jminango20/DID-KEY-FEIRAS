// FeirasWallet Service Worker
// Caches static assets and wallet pages for offline use.
// Credentials are stored in localStorage — offline-first by design.

const CACHE_NAME = 'feiras-wallet-v1';

const PRECACHE_URLS = [
    '/wallet/',
    '/static/js/wallet.js',
    '/static/manifest.json',
];

// ── Install: pre-cache static assets ─────────────────────────────────────────

self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => cache.addAll(PRECACHE_URLS))
    );
    self.skipWaiting();
});

// ── Activate: remove old caches ───────────────────────────────────────────────

self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(keys =>
            Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
        )
    );
    self.clients.claim();
});

// ── Fetch: cache-first for static, network-first for API ─────────────────────

self.addEventListener('fetch', event => {
    const url = new URL(event.request.url);

    // Skip non-GET and cross-origin
    if (event.request.method !== 'GET') return;
    if (url.origin !== self.location.origin) return;

    // Network-first for API calls (need fresh credentials)
    if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/verify/')) {
        event.respondWith(
            fetch(event.request).catch(() => caches.match(event.request))
        );
        return;
    }

    // Cache-first for static assets and wallet pages
    event.respondWith(
        caches.match(event.request).then(cached => {
            if (cached) return cached;
            return fetch(event.request).then(response => {
                if (!response || response.status !== 200 || response.type !== 'basic') {
                    return response;
                }
                const toCache = response.clone();
                caches.open(CACHE_NAME).then(cache => cache.put(event.request, toCache));
                return response;
            });
        })
    );
});
