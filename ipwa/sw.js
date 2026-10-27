// Offline-first. On a controlled client, NEVER fall back to the network.
const CACHE = 'itm-ipop-verifier-static-v2';
const ASSETS = ['./', './index.html', './verifier.mjs', './wasm-sha256.mjs', './archive.mjs', './verifier_bg.wasm', './manifest.webmanifest', './icon.svg', './icon-192.png', './icon-512.png'];
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(ASSETS)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key.startsWith('itm-ipop-verifier-static-') && key !== CACHE).map(key => caches.delete(key)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  if (url.origin !== self.location.origin) return;
  event.respondWith((async () => {
    if (event.request.method !== 'GET') return new Response('Method not allowed', {status:405});
    const hit = await caches.match(event.request, {ignoreSearch:true});
    return hit || new Response('Offline asset not cached', {status:503});
  })());
});
