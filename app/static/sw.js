const CACHE_NAME = 'iperc-v2';
const urlsToCache = [
    '/',
    '/dashboard',
    '/iperc/nuevo',
    '/static/manifest.json',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
    'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css'
];

// ── IndexedDB: guardar formularios offline ─────────────────
const DB_NAME = 'iperc-offline';
const DB_VERSION = 1;
const STORE_NAME = 'registros-pendientes';

function abrirDB() {
    return new Promise((resolve, reject) => {
        const req = indexedDB.open(DB_NAME, DB_VERSION);
        req.onupgradeneeded = e => {
            const db = e.target.result;
            if (!db.objectStoreNames.contains(STORE_NAME)) {
                db.createObjectStore(STORE_NAME, {
                    keyPath: 'id',
                    autoIncrement: true
                });
            }
        };
        req.onsuccess = e => resolve(e.target.result);
        req.onerror   = e => reject(e.target.error);
    });
}

function guardarPendiente(datos) {
    return abrirDB().then(db => {
        return new Promise((resolve, reject) => {
            const tx    = db.transaction(STORE_NAME, 'readwrite');
            const store = tx.objectStore(STORE_NAME);
            const req   = store.add({
                datos,
                timestamp: Date.now(),
                intentos: 0
            });
            req.onsuccess = () => resolve(req.result);
            req.onerror   = () => reject(req.error);
        });
    });
}

function obtenerPendientes() {
    return abrirDB().then(db => {
        return new Promise((resolve, reject) => {
            const tx    = db.transaction(STORE_NAME, 'readonly');
            const store = tx.objectStore(STORE_NAME);
            const req   = store.getAll();
            req.onsuccess = () => resolve(req.result);
            req.onerror   = () => reject(req.error);
        });
    });
}

function eliminarPendiente(id) {
    return abrirDB().then(db => {
        return new Promise((resolve, reject) => {
            const tx    = db.transaction(STORE_NAME, 'readwrite');
            const store = tx.objectStore(STORE_NAME);
            const req   = store.delete(id);
            req.onsuccess = () => resolve();
            req.onerror   = () => reject(req.error);
        });
    });
}

// ── Install ────────────────────────────────────────────────
self.addEventListener('install', event => {
    self.skipWaiting();
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => cache.addAll(urlsToCache))
    );
});

// ── Activate ───────────────────────────────────────────────
self.addEventListener('activate', event => {
    event.waitUntil(
        Promise.all([
            self.clients.claim(),
            caches.keys().then(keys =>
                Promise.all(
                    keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))
                )
            )
        ])
    );
});

// ── Fetch: caché para GET, interceptar POST /iperc/guardar ─
self.addEventListener('fetch', event => {
    const url = new URL(event.request.url);

    // Interceptar POST al guardar IPERC
    if (event.request.method === 'POST' && url.pathname === '/iperc/guardar') {
        event.respondWith(
            fetch(event.request.clone()).catch(async () => {
                // Sin internet → guardar en IndexedDB
                const formData = await event.request.formData();
                const datos = {};
                for (const [key, val] of formData.entries()) {
                    datos[key] = val;
                }
                await guardarPendiente(datos);

                // Registrar sync para cuando recupere conexión
                await self.registration.sync.register('sync-iperc');

                // Devolver respuesta simulada para que el usuario
                // vea el mensaje de guardado offline
                return new Response(
                    JSON.stringify({
                        status: 'offline',
                        mensaje: 'IPERC guardado localmente. Se enviará automáticamente cuando recuperes conexión.'
                    }),
                    {
                        status: 200,
                        headers: { 'Content-Type': 'application/json' }
                    }
                );
            })
        );
        return;
    }

    // Para el resto: estrategia cache-first
    event.respondWith(
        caches.match(event.request).then(response => {
            if (response) return response;
            return fetch(event.request).catch(() => {
                if (event.request.destination === 'document') {
                    return caches.match('/dashboard');
                }
            });
        })
    );
});

// ── Background Sync: enviar registros pendientes ───────────
self.addEventListener('sync', event => {
    if (event.tag === 'sync-iperc') {
        event.waitUntil(sincronizarPendientes());
    }
});

async function sincronizarPendientes() {
    const pendientes = await obtenerPendientes();

    for (const registro of pendientes) {
        try {
            const formData = new FormData();
            for (const [key, val] of Object.entries(registro.datos)) {
                formData.append(key, val);
            }

            const response = await fetch('/iperc/guardar', {
                method: 'POST',
                body: formData
            });

            if (response.ok || response.redirected) {
                await eliminarPendiente(registro.id);

                // Notificar al trabajador que se sincronizó
                const clients = await self.clients.matchAll();
                clients.forEach(client => {
                    client.postMessage({
                        tipo: 'sync-exitoso',
                        mensaje: '✓ IPERC enviado correctamente al servidor.'
                    });
                });
            }
        } catch (err) {
            // Si falla el intento, se reintentará en el próximo sync
            console.log('Reintentando sync:', err);
        }
    }
}

// ── Mensaje desde la app: verificar pendientes ─────────────
self.addEventListener('message', event => {
    if (event.data === 'verificar-pendientes') {
        obtenerPendientes().then(pendientes => {
            event.source.postMessage({
                tipo: 'pendientes-count',
                cantidad: pendientes.length
            });
        });
    }
});