const CACHE_NAME = 'hunt-fish-cache-v1';
const urlsToCache = [
  '/',
  '/index.html',
  '/catalog.html',
  '/cart.html',
  '/wishlist.html',
  '/style.css',
  '/script.js',
  '/product_data.js',
  '/assets/icon-512.png' 
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Opened cache');
        return cache.addAll(urlsToCache);
      })
  );
});

self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        if (response) {
          return response; // Возвращаем из кэша
        }
        return fetch(event.request); // Если в кэше нет, идем в интернет
      }
    )
  );
});