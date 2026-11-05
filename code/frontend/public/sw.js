/**
 * PromptShield-AI Service Worker
 * Secure PWA Implementation:
 * - Stale-while-revalidate / cache-first for static shell assets (HTML, JS, CSS, SVG, Icons).
 * - Network-only (no caching) for all /api/v1/* requests to protect sensitive prompt data & JWT tokens.
 * - Offline navigation fallback to cached index.html or offline.html.
 */

const CACHE_NAME = 'promptshield-v1.0.0';
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/offline.html',
  '/manifest.webmanifest',
  '/favicon.svg',
  '/pwa-192x192.png',
  '/pwa-512x512.png',
  '/pwa-maskable-512x512.png',
  '/apple-touch-icon.png'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS);
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
        })
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // 1. Never cache API calls (POST/GET /api/v1/*) or requests with Authorization
  // Strictly enforce network-first without caching for any backend communication to protect user confidentiality.
  if (url.pathname.includes('/api/') || request.headers.has('Authorization') || request.method !== 'GET') {
    event.respondWith(
      fetch(request).catch(() => {
        return new Response(
          JSON.stringify({
            error: 'You are currently offline. PromptShield AI requires an active internet connection to communicate with the AI engine.',
            status: 503,
            offline: true
          }),
          {
            status: 503,
            headers: { 'Content-Type': 'application/json' }
          }
        );
      })
    );
    return;
  }

  // 2. Navigation requests: try network first, fall back to cached shell or offline.html
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request).catch(async () => {
        const cache = await caches.open(CACHE_NAME);
        const cachedShell = await cache.match('/index.html');
        if (cachedShell) return cachedShell;
        const cachedOffline = await cache.match('/offline.html');
        return cachedOffline || new Response('Offline', { status: 503 });
      })
    );
    return;
  }

  // 3. Static assets: Cache-first with background revalidation
  event.respondWith(
    caches.match(request).then((cachedResponse) => {
      if (cachedResponse) {
        // Revalidate in background if not an immutable build hash asset
        fetch(request).then((networkResponse) => {
          if (networkResponse && networkResponse.status === 200) {
            caches.open(CACHE_NAME).then((cache) => cache.put(request, networkResponse));
          }
        }).catch(() => {});
        return cachedResponse;
      }

      return fetch(request).then((networkResponse) => {
        if (!networkResponse || networkResponse.status !== 200 || networkResponse.type !== 'basic') {
          return networkResponse;
        }

        // Only cache GET static files (scripts, styles, fonts, images)
        const isStaticAsset = (
          url.pathname.endsWith('.js') ||
          url.pathname.endsWith('.css') ||
          url.pathname.endsWith('.svg') ||
          url.pathname.endsWith('.png') ||
          url.pathname.endsWith('.woff2') ||
          url.pathname.endsWith('.webp')
        );

        if (isStaticAsset) {
          const responseToCache = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(request, responseToCache);
          });
        }

        return networkResponse;
      }).catch(() => {
        // Return 404 or nothing if resource unavailable
        return new Response('', { status: 404 });
      });
    })
  );
});

self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});

