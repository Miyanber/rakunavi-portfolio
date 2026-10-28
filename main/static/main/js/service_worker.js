/**
 * NOTE:
 * This file intentionally avoids using any Japanese characters,
 * including in comments and strings, to prevent encoding issues
 * when opened in environments such as Windows using Shift-JIS.
 * ##### DO NOT WRITE ANY JAPANESE TEXT IN THIS FILE. #####
 */
console.log("service_worker.js: loaded");

const CACHE_NAME = 'rakunavi-pwa-caches-v3';
const CACHE_EXPIRATION_MS = 1000 * 60 * 60;  // 1 hour

// Helper to check if request is cross-origin
const isExternalRequest = (request) =>
	new URL(request.url).origin !== self.location.origin;


// Extract URLs from sitemap XML
const extractUrlsFromSitemap = async () => {
	try {
		const response = await fetch('/sitemap.xml');
		if (!response.ok) return [];

		const text = await response.text();

		// Extract <loc>...</loc>
		const matches = [...text.matchAll(/<loc>(.*?)<\/loc>/g)];

		const urls = matches.map(match => {
			try {
				const url = new URL(match[1]);
				return url.pathname;
			} catch {
				return null;
			}
		}).filter(Boolean);

		return urls;

	} catch (err) {
		console.warn('Failed to load sitemap:', err);
		return [];
	}
};



// Install & cache essential assets
self.addEventListener('install', event => {
	event.waitUntil(
		(async () => {
			const cache = await caches.open(CACHE_NAME);
			await cache.add('/offline/');
			await self.skipWaiting();
		})()
	);
});

self.addEventListener('activate', event => {
	event.waitUntil(
		(async () => {
			const keys = await caches.keys();
			await Promise.all(
				keys.map(key => {
					if (key !== CACHE_NAME) {
						return caches.delete(key);
					}
				})
			);
			await self.clients.claim();
		})()
	);
});


// Fetch handler with cache expiration and external request handling
self.addEventListener('fetch', event => {
	if (isExternalRequest(event.request)) return;
	if (event.request.method !== 'GET') return;

	if (event.request.mode === 'navigate') {

		event.respondWith((async () => {

			const cache = await caches.open(CACHE_NAME);

			try {
				const response = await fetch(event.request);

				if (response.status === 200) {
					cache.put(event.request, response.clone());
				}

				return response;

			} catch (error) {

				const cached = await cache.match(event.request);
				if (cached) return cached;

				return await cache.match('/offline/');
			}

		})());

	}
});
