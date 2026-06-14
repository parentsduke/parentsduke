// chetan-sw.js
// 极简离线缓存：缓存外壳页面，AI接口请求直接走网络（不缓存）
const CACHE_NAME = 'chetan-gpt-v1';
const CORE_ASSETS = [
  '/chetan-gpt.html',
  '/manifest.json',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(CORE_ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Supabase接口、API请求：不缓存，直接走网络
  if (url.hostname.includes('supabase.co') || url.pathname.includes('/functions/')) {
    return;
  }

  // 其他资源：缓存优先，网络兜底
  event.respondWith(
    caches.match(event.request).then((cached) => {
      return cached || fetch(event.request).then((res) => {
        if (res.ok && event.request.method === 'GET') {
          const resClone = res.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, resClone));
        }
        return res;
      }).catch(() => cached);
    })
  );
});
