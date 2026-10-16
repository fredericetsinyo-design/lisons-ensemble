// Lisons Ensemble: app shell cached for offline reading. Server data (Supabase) always goes to the network.
const CACHE = 'lisons-ensemble-v3';
const SHELL = ['./', 'index.html', 'manifest.webmanifest', 'icons/icon-192.png', 'icons/icon-512.png',
  'img/etude.jpg', 'img/rayons.jpg', 'img/bibliotheque.jpg', 'img/fauteuil.jpg', 'img/canape.jpg', 'img/lecture.jpg', 'img/livre.jpg', 'img/jeune.jpg', 'img/allonge.jpg'];
self.addEventListener('install', e => { e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting())); });
self.addEventListener('activate', e => { e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim())); });
self.addEventListener('fetch', e => {
  const req = e.request; if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.hostname.endsWith('supabase.co')) return;                       // live data: never cached here
  if (req.mode === 'navigate') {                                          // pages: network first, cached copy offline
    e.respondWith(fetch(req).then(r => { const copy = r.clone(); caches.open(CACHE).then(c => c.put('index.html', copy)); return r; }).catch(() => caches.match('index.html')));
    return;
  }
  e.respondWith(caches.match(req).then(hit => hit || fetch(req).then(r => {     // libraries, fonts, images: cache first
    if (r.ok && (url.origin === location.origin || /cdnjs|jsdelivr|fonts\.(googleapis|gstatic)/.test(url.hostname))) { const copy = r.clone(); caches.open(CACHE).then(c => c.put(req, copy)); }
    return r;
  })));
});
