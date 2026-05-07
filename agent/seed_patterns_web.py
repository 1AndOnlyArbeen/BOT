"""Advanced JS, HTML5, CSS, Tailwind — production patterns for Ultron's library."""
from __future__ import annotations


WEB_SEED: list[dict] = [

# ════════ Advanced JavaScript ════════

{
    "request": "debounce and throttle utilities",
    "language": "javascript", "framework": "stdlib",
    "code": """export function debounce(fn, wait = 300) {
  let t;
  function debounced(...args) {
    clearTimeout(t);
    t = setTimeout(() => fn.apply(this, args), wait);
  }
  debounced.cancel = () => clearTimeout(t);
  return debounced;
}

export function throttle(fn, limit = 300) {
  let last = 0, t;
  return function (...args) {
    const now = Date.now();
    const diff = now - last;
    if (diff >= limit) {
      last = now;
      fn.apply(this, args);
    } else {
      clearTimeout(t);
      t = setTimeout(() => { last = Date.now(); fn.apply(this, args); }, limit - diff);
    }
  };
}""",
},
{
    "request": "fetch with timeout, abort, and retry",
    "language": "javascript", "framework": "stdlib",
    "code": """export async function smartFetch(url, {
  retries = 3, timeout = 10_000, backoff = 500, ...init
} = {}) {
  for (let i = 0; i <= retries; i++) {
    const ac = new AbortController();
    const t = setTimeout(() => ac.abort(), timeout);
    try {
      const r = await fetch(url, { ...init, signal: ac.signal });
      clearTimeout(t);
      if (r.ok) return r;
      if (r.status >= 400 && r.status < 500 && r.status !== 429) return r;  // don't retry client errors
      throw new Error(`HTTP ${r.status}`);
    } catch (e) {
      clearTimeout(t);
      if (i === retries) throw e;
      await new Promise(r => setTimeout(r, backoff * 2 ** i));
    }
  }
}""",
},
{
    "request": "Promise.allSettled / any / race usage",
    "language": "javascript", "framework": "stdlib",
    "code": """// allSettled — never rejects, gives you both successes & failures
const results = await Promise.allSettled([
  fetch('/api/a'), fetch('/api/b'), fetch('/api/c'),
]);
const ok = results.filter(r => r.status === 'fulfilled').map(r => r.value);
const failed = results.filter(r => r.status === 'rejected');

// any — first to succeed
const fastest = await Promise.any([
  fetch('https://mirror1.example.com/data'),
  fetch('https://mirror2.example.com/data'),
]);

// race — first to settle (success OR failure)
const result = await Promise.race([
  longTask(),
  new Promise((_, rej) => setTimeout(() => rej(new Error('timeout')), 5000)),
]);""",
},
{
    "request": "async iterator / generator for paginated API",
    "language": "javascript", "framework": "stdlib",
    "code": """async function* fetchPages(url) {
  let next = url;
  while (next) {
    const r = await fetch(next);
    const data = await r.json();
    for (const item of data.items) yield item;
    next = data.nextPageUrl;
  }
}

for await (const item of fetchPages('/api/items?page=1')) {
  console.log(item);
  if (item.stop) break;
}""",
},
{
    "request": "JavaScript Proxy for reactive state",
    "language": "javascript", "framework": "stdlib",
    "code": """function reactive(target, onChange) {
  return new Proxy(target, {
    get(t, k, r) {
      const v = Reflect.get(t, k, r);
      return (typeof v === 'object' && v !== null) ? reactive(v, onChange) : v;
    },
    set(t, k, v, r) {
      const old = t[k];
      const ok = Reflect.set(t, k, v, r);
      if (old !== v) onChange(k, v, old);
      return ok;
    },
  });
}

const state = reactive({ count: 0, user: { name: 'Alice' } }, (k, v, old) => {
  console.log(`${k}: ${old} → ${v}`);
});
state.count = 5;
state.user.name = 'Bob';""",
},
{
    "request": "IntersectionObserver for lazy loading and infinite scroll",
    "language": "javascript", "framework": "browser",
    "code": """// lazy images
const io = new IntersectionObserver((entries) => {
  for (const e of entries) {
    if (!e.isIntersecting) continue;
    const img = e.target;
    img.src = img.dataset.src;
    io.unobserve(img);
  }
}, { rootMargin: '100px' });
document.querySelectorAll('img[data-src]').forEach(img => io.observe(img));

// infinite scroll
const sentinel = document.querySelector('#sentinel');
const loadMore = new IntersectionObserver(async ([e]) => {
  if (!e.isIntersecting) return;
  await loadNextPage();
});
loadMore.observe(sentinel);""",
},
{
    "request": "MutationObserver for DOM changes",
    "language": "javascript", "framework": "browser",
    "code": """const target = document.querySelector('#feed');
const observer = new MutationObserver((mutations) => {
  for (const m of mutations) {
    if (m.type === 'childList') {
      m.addedNodes.forEach(n => {
        if (n.nodeType === 1) hydrate(n);
      });
    }
  }
});
observer.observe(target, { childList: true, subtree: true });
// later:
observer.disconnect();""",
},
{
    "request": "ResizeObserver for responsive components",
    "language": "javascript", "framework": "browser",
    "code": """const ro = new ResizeObserver((entries) => {
  for (const e of entries) {
    const w = e.contentRect.width;
    e.target.dataset.size = w < 480 ? 'sm' : w < 800 ? 'md' : 'lg';
  }
});
document.querySelectorAll('.responsive-card').forEach(el => ro.observe(el));""",
},
{
    "request": "Web Worker offloading heavy computation",
    "language": "javascript", "framework": "browser",
    "code": """// main.js
const worker = new Worker('/worker.js', { type: 'module' });
worker.postMessage({ cmd: 'crunch', data: bigArray });
worker.onmessage = (e) => console.log('result:', e.data);

// worker.js
self.onmessage = (e) => {
  const { cmd, data } = e.data;
  if (cmd === 'crunch') {
    const total = data.reduce((s, x) => s + Math.sqrt(x * x + 1), 0);
    self.postMessage(total);
  }
};""",
},
{
    "request": "Service Worker for offline cache (PWA)",
    "language": "javascript", "framework": "browser",
    "code": """// sw.js
const CACHE = 'v1';
const ASSETS = ['/', '/index.html', '/main.js', '/styles.css'];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)));
  self.skipWaiting();
});

self.addEventListener('activate', (e) => {
  e.waitUntil(caches.keys().then(keys =>
    Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
  ));
  clients.claim();
});

self.addEventListener('fetch', (e) => {
  if (e.request.method !== 'GET') return;
  e.respondWith(
    caches.match(e.request).then(hit => hit || fetch(e.request).then(res => {
      const copy = res.clone();
      caches.open(CACHE).then(c => c.put(e.request, copy));
      return res;
    }))
  );
});

// register in main:
if ('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js');""",
},
{
    "request": "IndexedDB simple wrapper for client-side storage",
    "language": "javascript", "framework": "browser",
    "code": """function openDB(name, version, schema) {
  return new Promise((res, rej) => {
    const req = indexedDB.open(name, version);
    req.onupgradeneeded = () => schema(req.result);
    req.onsuccess = () => res(req.result);
    req.onerror = () => rej(req.error);
  });
}

const db = await openDB('app', 1, (db) => {
  const store = db.createObjectStore('users', { keyPath: 'id' });
  store.createIndex('email', 'email', { unique: true });
});

function tx(store, mode = 'readonly') {
  return db.transaction(store, mode).objectStore(store);
}

await new Promise((res) => {
  const r = tx('users', 'readwrite').put({ id: 1, email: 'a@b.com' });
  r.onsuccess = res;
});

const user = await new Promise((res) => {
  const r = tx('users').get(1);
  r.onsuccess = () => res(r.result);
});""",
},
{
    "request": "drag-and-drop file upload zone",
    "language": "javascript", "framework": "browser",
    "code": """const zone = document.querySelector('#dropzone');
['dragenter', 'dragover'].forEach(ev =>
  zone.addEventListener(ev, e => { e.preventDefault(); zone.classList.add('over'); })
);
['dragleave', 'drop'].forEach(ev =>
  zone.addEventListener(ev, e => { e.preventDefault(); zone.classList.remove('over'); })
);
zone.addEventListener('drop', async (e) => {
  for (const file of e.dataTransfer.files) {
    if (file.size > 10 * 1024 * 1024) continue;  // 10MB
    const fd = new FormData();
    fd.append('file', file);
    await fetch('/api/upload', { method: 'POST', body: fd });
  }
});""",
},
{
    "request": "Clipboard API copy + paste handling",
    "language": "javascript", "framework": "browser",
    "code": """// copy
async function copyToClipboard(text) {
  try { await navigator.clipboard.writeText(text); return true; }
  catch { return false; }
}

// read clipboard (requires permission)
async function readClipboard() {
  try { return await navigator.clipboard.readText(); }
  catch { return ''; }
}

// listen for paste in any input
document.addEventListener('paste', (e) => {
  const text = e.clipboardData.getData('text/plain');
  if (text.startsWith('http')) /* handle URL paste */ {}
});""",
},
{
    "request": "History API SPA routing without a framework",
    "language": "javascript", "framework": "browser",
    "code": """const routes = {
  '/': () => render('<h1>Home</h1>'),
  '/about': () => render('<h1>About</h1>'),
  '/orders/:id': ({ id }) => render(`<h1>Order ${id}</h1>`),
};

function match(pathname) {
  for (const [pattern, handler] of Object.entries(routes)) {
    const keys = [];
    const re = new RegExp('^' + pattern.replace(/:(\\w+)/g, (_, k) => (keys.push(k), '([^/]+)')) + '$');
    const m = pathname.match(re);
    if (m) {
      const params = Object.fromEntries(keys.map((k, i) => [k, m[i + 1]]));
      handler(params);
      return;
    }
  }
  render('<h1>404</h1>');
}

window.addEventListener('popstate', () => match(location.pathname));
document.addEventListener('click', (e) => {
  const a = e.target.closest('a[data-link]');
  if (!a) return;
  e.preventDefault();
  history.pushState({}, '', a.href);
  match(location.pathname);
});
match(location.pathname);""",
},
{
    "request": "EventTarget custom events for component communication",
    "language": "javascript", "framework": "browser",
    "code": """// dispatch:
const evt = new CustomEvent('cart:add', { detail: { productId: 1, qty: 2 }, bubbles: true });
document.dispatchEvent(evt);

// listen:
document.addEventListener('cart:add', (e) => {
  console.log('added', e.detail);
});

// scoped event bus:
class Bus extends EventTarget {}
export const bus = new Bus();
bus.addEventListener('user:login', (e) => console.log(e.detail));
bus.dispatchEvent(new CustomEvent('user:login', { detail: { id: 1 } }));""",
},
{
    "request": "currying and partial application",
    "language": "javascript", "framework": "stdlib",
    "code": """export const curry = (fn) => {
  const arity = fn.length;
  return function curried(...args) {
    return args.length >= arity
      ? fn.apply(this, args)
      : (...rest) => curried.apply(this, [...args, ...rest]);
  };
};

export const partial = (fn, ...preset) => (...rest) => fn(...preset, ...rest);

// usage:
const add = curry((a, b, c) => a + b + c);
add(1)(2)(3);            // 6
add(1, 2)(3);            // 6

const greet = (greeting, name) => `${greeting}, ${name}`;
const hello = partial(greet, 'Hello');
hello('Alice');          // 'Hello, Alice'""",
},
{
    "request": "Web Components custom element with Shadow DOM",
    "language": "javascript", "framework": "web-components",
    "code": """class CounterButton extends HTMLElement {
  static observedAttributes = ['count'];

  constructor() {
    super();
    const sh = this.attachShadow({ mode: 'open' });
    sh.innerHTML = `
      <style>
        button { background: #c96442; color: white; padding: 8px 16px;
                 border: none; border-radius: 6px; cursor: pointer; }
        button:hover { background: #a8512f; }
      </style>
      <button><slot>Click</slot> (<span id="n">0</span>)</button>
    `;
    sh.querySelector('button').addEventListener('click', () => {
      this.setAttribute('count', +this.getAttribute('count') + 1);
      this.dispatchEvent(new CustomEvent('increment', { detail: this.count, bubbles: true }));
    });
  }

  get count() { return +this.getAttribute('count') || 0; }
  attributeChangedCallback(name, _old, val) {
    if (name === 'count') this.shadowRoot.querySelector('#n').textContent = val;
  }
}
customElements.define('counter-button', CounterButton);
// <counter-button count="0">Add to cart</counter-button>""",
},
{
    "request": "structured cloning and Map/Set patterns",
    "language": "javascript", "framework": "stdlib",
    "code": """// deep copy non-trivial data (Date, Map, Set, ArrayBuffer):
const copy = structuredClone(original);

// Map for non-string keys:
const userOrders = new Map();
userOrders.set(userObj, [orderA, orderB]);
userOrders.size;  // 1

// Set for unique values:
const uniqueIds = new Set([1, 2, 2, 3, 3]);  // {1, 2, 3}
uniqueIds.has(2);

// WeakMap — entries auto-cleaned when key object is GC'd
const cache = new WeakMap();
cache.set(userObj, expensiveData);""",
},
{
    "request": "Performance observer for measuring real user metrics",
    "language": "javascript", "framework": "browser",
    "code": """// Largest Contentful Paint
new PerformanceObserver((list) => {
  for (const entry of list.getEntries()) {
    sendBeacon('/metrics', { kind: 'lcp', value: entry.startTime, url: location.pathname });
  }
}).observe({ type: 'largest-contentful-paint', buffered: true });

// First Input Delay
new PerformanceObserver((list) => {
  for (const e of list.getEntries()) {
    sendBeacon('/metrics', { kind: 'fid', value: e.processingStart - e.startTime });
  }
}).observe({ type: 'first-input', buffered: true });

// Long tasks
new PerformanceObserver((list) => {
  for (const e of list.getEntries()) {
    if (e.duration > 50) console.warn('long task', e.duration, 'ms');
  }
}).observe({ type: 'longtask', buffered: true });

function sendBeacon(url, data) {
  navigator.sendBeacon(url, JSON.stringify(data));
}""",
},
{
    "request": "WebSocket client with auto-reconnect and heartbeat",
    "language": "javascript", "framework": "browser",
    "code": """class ReconnectingWS {
  constructor(url, { onMessage, onOpen, heartbeatMs = 30000 } = {}) {
    this.url = url; this.onMessage = onMessage; this.onOpen = onOpen;
    this.heartbeatMs = heartbeatMs; this.attempts = 0; this.connect();
  }
  connect() {
    this.ws = new WebSocket(this.url);
    this.ws.onopen = () => {
      this.attempts = 0;
      this.heartbeat = setInterval(() => this.send({ type: 'ping' }), this.heartbeatMs);
      this.onOpen?.();
    };
    this.ws.onmessage = (e) => this.onMessage?.(JSON.parse(e.data));
    this.ws.onclose = () => {
      clearInterval(this.heartbeat);
      const delay = Math.min(30_000, 1000 * 2 ** this.attempts++);
      setTimeout(() => this.connect(), delay);
    };
    this.ws.onerror = () => this.ws.close();
  }
  send(data) { this.ws?.readyState === 1 && this.ws.send(JSON.stringify(data)); }
  close() { this.ws?.close(); }
}""",
},
{
    "request": "navigator.share + clipboard fallback for share button",
    "language": "javascript", "framework": "browser",
    "code": """async function share({ title, text, url }) {
  if (navigator.share) {
    try { await navigator.share({ title, text, url }); return true; }
    catch (e) { if (e.name === 'AbortError') return false; }
  }
  await navigator.clipboard.writeText(url);
  toast('Link copied');
  return true;
}""",
},
{
    "request": "lazy ESM dynamic import for code splitting",
    "language": "javascript", "framework": "stdlib",
    "code": """// instead of static import on top of file:
async function openEditor() {
  const { default: CodeEditor } = await import('./CodeEditor.js');
  const editor = new CodeEditor(document.querySelector('#mount'));
  editor.load(content);
}

// load only when needed:
document.querySelector('#open-editor').addEventListener('click', openEditor);

// conditional polyfills:
if (!('IntersectionObserver' in window)) {
  await import('intersection-observer');
}""",
},

# ════════ HTML5 advanced ════════

{
    "request": "semantic HTML5 page structure with ARIA",
    "language": "html", "framework": "html5",
    "code": """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="description" content="..." />
  <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
  <title>Site Name</title>
</head>
<body>
  <a href="#main" class="skip-link">Skip to content</a>

  <header role="banner">
    <nav aria-label="Primary">
      <ul>
        <li><a href="/" aria-current="page">Home</a></li>
        <li><a href="/about">About</a></li>
      </ul>
    </nav>
  </header>

  <main id="main" tabindex="-1">
    <article aria-labelledby="post-title">
      <h1 id="post-title">Title</h1>
      <time datetime="2026-05-06">May 6, 2026</time>
      <section aria-label="Article body">…</section>
    </article>

    <aside aria-label="Related">…</aside>
  </main>

  <footer role="contentinfo">…</footer>
</body>
</html>""",
},
{
    "request": "HTML5 form with native validation",
    "language": "html", "framework": "html5",
    "code": """<form novalidate id="signup">
  <label>
    Email
    <input type="email" name="email" required autocomplete="email"
           placeholder="you@example.com" />
  </label>

  <label>
    Password
    <input type="password" name="password" required minlength="8"
           pattern="(?=.*[A-Z])(?=.*\\d).{8,}"
           autocomplete="new-password" />
    <small>8+ chars, 1 uppercase, 1 number</small>
  </label>

  <label>
    Age
    <input type="number" name="age" min="13" max="120" required />
  </label>

  <fieldset>
    <legend>Plan</legend>
    <label><input type="radio" name="plan" value="free" required /> Free</label>
    <label><input type="radio" name="plan" value="pro" /> Pro</label>
  </fieldset>

  <label><input type="checkbox" name="terms" required /> I agree to terms</label>

  <button type="submit">Sign up</button>
</form>

<script>
  document.querySelector('#signup').addEventListener('submit', (e) => {
    if (!e.target.checkValidity()) {
      e.preventDefault();
      e.target.reportValidity();
    }
  });
</script>""",
},
{
    "request": "PWA manifest + meta tags",
    "language": "html", "framework": "pwa",
    "code": """<!-- in <head> -->
<link rel="manifest" href="/manifest.webmanifest" />
<meta name="theme-color" content="#0b0d12" />
<link rel="apple-touch-icon" href="/icons/192.png" />
<meta name="apple-mobile-web-app-capable" content="yes" />

<!-- manifest.webmanifest -->
{
  "name": "Ultron",
  "short_name": "Ultron",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#0b0d12",
  "theme_color": "#ff3b3b",
  "icons": [
    { "src": "/icons/192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/icons/512.png", "sizes": "512x512", "type": "image/png" },
    { "src": "/icons/maskable.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable" }
  ]
}""",
},
{
    "request": "Open Graph + Twitter card meta for SEO",
    "language": "html", "framework": "html5",
    "code": """<meta property="og:title" content="Page title" />
<meta property="og:description" content="Page description (≤155 chars)" />
<meta property="og:url" content="https://example.com/page" />
<meta property="og:image" content="https://example.com/og.png" />
<meta property="og:image:width" content="1200" />
<meta property="og:image:height" content="630" />
<meta property="og:type" content="article" />
<meta property="og:site_name" content="Brand" />

<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:title" content="Page title" />
<meta name="twitter:description" content="Page description" />
<meta name="twitter:image" content="https://example.com/og.png" />
<meta name="twitter:site" content="@yourhandle" />

<link rel="canonical" href="https://example.com/page" />""",
},
{
    "request": "HTML dialog element for accessible modals",
    "language": "html", "framework": "html5",
    "code": """<button onclick="document.getElementById('confirmDlg').showModal()">Delete</button>

<dialog id="confirmDlg" aria-labelledby="dlgTitle">
  <form method="dialog">
    <h2 id="dlgTitle">Are you sure?</h2>
    <p>This cannot be undone.</p>
    <menu>
      <button value="cancel">Cancel</button>
      <button value="confirm" autofocus>Delete</button>
    </menu>
  </form>
</dialog>

<script>
  const dlg = document.getElementById('confirmDlg');
  dlg.addEventListener('close', () => {
    if (dlg.returnValue === 'confirm') doDelete();
  });
</script>

<style>
  dialog::backdrop { background: rgba(0,0,0,0.6); backdrop-filter: blur(4px); }
  dialog { border: none; border-radius: 12px; padding: 24px; }
</style>""",
},
{
    "request": "details/summary native disclosure",
    "language": "html", "framework": "html5",
    "code": """<details>
  <summary>Frequently asked questions</summary>
  <div>Hidden content here.</div>
</details>

<style>
  details summary { cursor: pointer; font-weight: 600; padding: 8px 0; }
  details summary::-webkit-details-marker { display: none; }
  details summary::before { content: '▶'; display: inline-block; margin-right: 8px;
    transition: transform .2s; }
  details[open] summary::before { transform: rotate(90deg); }
</style>""",
},

# ════════ Advanced CSS ════════

{
    "request": "CSS custom properties (variables) with fallbacks and dark mode",
    "language": "css", "framework": "css",
    "code": """:root {
  --bg: #ffffff;
  --text: #1a1a1a;
  --accent: #c96442;
  --radius: 8px;
  --space-1: 0.25rem;
  --space-2: 0.5rem;
  --space-3: 1rem;
  --space-4: 1.5rem;
  --shadow: 0 2px 8px rgba(0,0,0,0.08);
}

[data-theme="dark"] {
  --bg: #0b0d12;
  --text: #e8eaf0;
  --accent: #ff3b3b;
  --shadow: 0 2px 8px rgba(0,0,0,0.4);
}

@media (prefers-color-scheme: dark) {
  :root:not([data-theme]) {
    --bg: #0b0d12;
    --text: #e8eaf0;
  }
}

body {
  background: var(--bg, #fff);
  color: var(--text, #000);
  padding: var(--space-3);
}

.card {
  background: var(--bg);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: var(--space-3);
}""",
},
{
    "request": "CSS Grid with named areas, responsive layouts",
    "language": "css", "framework": "css",
    "code": """.layout {
  display: grid;
  min-height: 100vh;
  gap: 1rem;
  grid-template-areas:
    'header header header'
    'sidebar main aside'
    'footer footer footer';
  grid-template-columns: 220px 1fr 280px;
  grid-template-rows: 64px 1fr 48px;
}

.layout > header { grid-area: header; }
.layout > nav    { grid-area: sidebar; }
.layout > main   { grid-area: main; }
.layout > aside  { grid-area: aside; }
.layout > footer { grid-area: footer; }

@media (max-width: 900px) {
  .layout {
    grid-template-areas:
      'header'
      'main'
      'sidebar'
      'aside'
      'footer';
    grid-template-columns: 1fr;
    grid-template-rows: auto auto auto auto auto;
  }
}""",
},
{
    "request": "container queries for component-level responsiveness",
    "language": "css", "framework": "css",
    "code": """.card-grid {
  display: grid;
  gap: 1rem;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
}

.card {
  container-type: inline-size;
  container-name: card;
}

.card-content {
  display: grid;
  gap: 0.5rem;
}

@container card (min-width: 400px) {
  .card-content {
    grid-template-columns: 1fr 2fr;
    align-items: center;
  }
  .card img {
    max-width: 100%;
  }
}""",
},
{
    "request": ":has(), :is(), :where() modern selectors",
    "language": "css", "framework": "css",
    "code": """/* parent of an invalid input gets red border */
.field:has(input:invalid) {
  border-color: red;
}

/* card with badge gets a corner ribbon */
.card:has(.badge) {
  position: relative;
  padding-top: 2.5rem;
}

/* :is() — group selectors */
:is(h1, h2, h3) {
  font-family: 'Inter';
}

/* :where() — same as :is() but 0 specificity (easy to override) */
:where(.btn, button[type=submit]) {
  cursor: pointer;
}

/* combine: */
section:has(figure) :is(h2, h3) {
  margin-top: 0;
}""",
},
{
    "request": "smooth scroll, scroll-snap, sticky elements",
    "language": "css", "framework": "css",
    "code": """html {
  scroll-behavior: smooth;
  scroll-padding-top: 80px;  /* room for sticky header */
}

.gallery {
  display: flex;
  overflow-x: auto;
  scroll-snap-type: x mandatory;
  scroll-behavior: smooth;
  gap: 1rem;
}
.gallery > .card {
  flex: 0 0 80%;
  scroll-snap-align: center;
  scroll-snap-stop: always;
}

.sticky-header {
  position: sticky;
  top: 0;
  background: var(--bg);
  backdrop-filter: blur(8px);
  z-index: 10;
  transition: box-shadow .2s;
}
.sticky-header.scrolled { box-shadow: var(--shadow); }""",
},
{
    "request": "CSS aspect-ratio for images and videos",
    "language": "css", "framework": "css",
    "code": """.video-wrap {
  aspect-ratio: 16 / 9;
  background: #000;
}
.video-wrap iframe { width: 100%; height: 100%; border: 0; }

.thumb {
  aspect-ratio: 1;
  object-fit: cover;
  width: 100%;
  border-radius: 8px;
}

.product-image {
  aspect-ratio: 4 / 3;
  background: linear-gradient(135deg, #f5f5f5, #e5e5e5);
  display: grid;
  place-items: center;
}""",
},
{
    "request": "CSS keyframe animations with prefers-reduced-motion",
    "language": "css", "framework": "css",
    "code": """@keyframes fade-in-up {
  from { opacity: 0; transform: translateY(12px); }
  to   { opacity: 1; transform: translateY(0); }
}

.appear {
  animation: fade-in-up .5s ease-out forwards;
}

@media (prefers-reduced-motion: reduce) {
  .appear,
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}""",
},
{
    "request": "creative ::before / ::after pseudo-elements",
    "language": "css", "framework": "css",
    "code": """/* underline that grows on hover */
.link {
  position: relative;
  text-decoration: none;
}
.link::after {
  content: '';
  position: absolute;
  left: 0; bottom: -2px;
  width: 100%;
  height: 2px;
  background: currentColor;
  transform: scaleX(0);
  transform-origin: left;
  transition: transform .3s;
}
.link:hover::after { transform: scaleX(1); }

/* corner ribbon */
.card.featured::before {
  content: 'NEW';
  position: absolute;
  top: 12px; right: -28px;
  background: red; color: white;
  padding: 4px 32px;
  transform: rotate(45deg);
  font-weight: bold; font-size: 12px;
}""",
},
{
    "request": "backdrop-filter glassmorphism",
    "language": "css", "framework": "css",
    "code": """.glass {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(12px) saturate(150%);
  -webkit-backdrop-filter: blur(12px) saturate(150%);
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
}

@supports not (backdrop-filter: blur(12px)) {
  .glass { background: rgba(255, 255, 255, 0.85); }
}""",
},
{
    "request": "View Transitions API for smooth route changes",
    "language": "javascript", "framework": "view-transitions",
    "code": """function navigate(url) {
  if (!document.startViewTransition) {
    return location.href = url;
  }
  document.startViewTransition(async () => {
    const r = await fetch(url);
    const html = await r.text();
    document.querySelector('main').innerHTML = new DOMParser()
      .parseFromString(html, 'text/html').querySelector('main').innerHTML;
    history.pushState({}, '', url);
  });
}

// CSS:
// ::view-transition-old(root) { animation: fade-out .2s ease-out; }
// ::view-transition-new(root) { animation: fade-in .3s ease-out; }""",
},
{
    "request": "CSS clip-path for shapes",
    "language": "css", "framework": "css",
    "code": """.diagonal-section {
  clip-path: polygon(0 0, 100% 0, 100% 90%, 0 100%);
  padding: 4rem 2rem 6rem;
}

.avatar-hex {
  width: 80px; height: 80px;
  clip-path: polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%);
  object-fit: cover;
}

.reveal-on-hover {
  clip-path: inset(0 100% 0 0);
  transition: clip-path .4s;
}
.reveal-on-hover:hover { clip-path: inset(0 0 0 0); }""",
},
{
    "request": "logical properties for RTL-friendly layouts",
    "language": "css", "framework": "css",
    "code": """.card {
  /* old: margin-left + padding-right won't flip for RTL */
  margin-inline-start: 1rem;
  padding-inline: 1rem 2rem;
  border-inline-start: 4px solid var(--accent);
  text-align: start;       /* not 'left' */
}

.section + .section {
  margin-block-start: 2rem;  /* not margin-top */
}

[dir="rtl"] .card {
  /* automatically mirrors — no special rules needed */
}""",
},
{
    "request": "scroll-driven animation (parallax-style)",
    "language": "css", "framework": "css",
    "code": """@supports (animation-timeline: scroll()) {
  .progress-bar {
    position: fixed;
    top: 0; left: 0; right: 0;
    height: 4px;
    background: var(--accent);
    transform-origin: 0 50%;
    animation: progress linear;
    animation-timeline: scroll(root);
  }
  @keyframes progress {
    from { transform: scaleX(0); }
    to   { transform: scaleX(1); }
  }

  .hero-image {
    animation: parallax linear;
    animation-timeline: view();
    animation-range: entry 0% cover 100%;
  }
  @keyframes parallax {
    from { transform: translateY(0); }
    to   { transform: translateY(-100px); }
  }
}""",
},
{
    "request": "modern CSS reset",
    "language": "css", "framework": "css",
    "code": """*, *::before, *::after { box-sizing: border-box; }
* { margin: 0; padding: 0; }

html { -webkit-text-size-adjust: 100%; tab-size: 4; }
body {
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
  font-family: system-ui, -apple-system, 'Segoe UI', sans-serif;
}

img, picture, video, canvas, svg {
  display: block;
  max-width: 100%;
  height: auto;
}

input, button, textarea, select { font: inherit; color: inherit; }

p, h1, h2, h3, h4, h5, h6 { overflow-wrap: break-word; hyphens: auto; }

#root { isolation: isolate; }""",
},

# ════════ Tailwind advanced ════════

{
    "request": "Tailwind config with custom theme, fonts, plugins",
    "language": "javascript", "framework": "tailwindcss",
    "code": """// tailwind.config.js
import forms from '@tailwindcss/forms';
import typography from '@tailwindcss/typography';
import containerQueries from '@tailwindcss/container-queries';

export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx,vue}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        brand: {
          50:  '#fef2f2',
          500: '#c96442',
          900: '#7c2d12',
        },
        bg: 'var(--bg)',
        text: 'var(--text)',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      boxShadow: {
        glow: '0 0 20px rgba(255,59,59,.4)',
      },
      animation: {
        'pulse-slow': 'pulse 3s ease-in-out infinite',
        shimmer: 'shimmer 2s linear infinite',
      },
      keyframes: {
        shimmer: {
          '0%':   { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
      },
    },
  },
  plugins: [forms, typography, containerQueries],
};""",
},
{
    "request": "Tailwind reusable button component classes with @apply",
    "language": "css", "framework": "tailwindcss",
    "code": """@tailwind base;
@tailwind components;
@tailwind utilities;

@layer components {
  .btn {
    @apply inline-flex items-center justify-center gap-2 px-4 py-2 rounded-md font-medium
           transition-colors disabled:opacity-50 disabled:cursor-not-allowed
           focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-500;
  }
  .btn-primary { @apply btn bg-brand-500 text-white hover:bg-brand-700; }
  .btn-ghost   { @apply btn text-text hover:bg-slate-100 dark:hover:bg-slate-800; }
  .btn-outline { @apply btn border border-slate-300 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800; }
  .btn-danger  { @apply btn bg-red-600 text-white hover:bg-red-700; }
  .btn-sm { @apply px-3 py-1 text-sm; }
  .btn-lg { @apply px-6 py-3 text-lg; }
}""",
},
{
    "request": "Tailwind dark mode with class strategy + toggle",
    "language": "tsx", "framework": "tailwindcss",
    "code": """// tailwind.config.js: darkMode: 'class'

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    const stored = localStorage.getItem('theme');
    const prefersDark = matchMedia('(prefers-color-scheme: dark)').matches;
    const dark = stored ? stored === 'dark' : prefersDark;
    document.documentElement.classList.toggle('dark', dark);
  }, []);
  return <>{children}</>;
}

export function ThemeToggle() {
  const [dark, setDark] = useState(() =>
    document.documentElement.classList.contains('dark'));
  const toggle = () => {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle('dark', next);
    localStorage.setItem('theme', next ? 'dark' : 'light');
  };
  return (
    <button onClick={toggle} className="p-2 rounded-md hover:bg-slate-100 dark:hover:bg-slate-800">
      {dark ? '☀️' : '🌙'}
    </button>
  );
}

// Usage: bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100""",
},
{
    "request": "Tailwind card component with hover lift",
    "language": "tsx", "framework": "tailwindcss",
    "code": """export function Card({ title, body, footer }: any) {
  return (
    <article className="
      group relative bg-white dark:bg-slate-900
      border border-slate-200 dark:border-slate-800
      rounded-xl overflow-hidden
      transition-all duration-200
      hover:-translate-y-1 hover:shadow-xl
      hover:border-brand-500/40
    ">
      <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-brand-500 to-brand-700 opacity-0 group-hover:opacity-100 transition-opacity" />
      <div className="p-6">
        <h3 className="text-xl font-semibold mb-2">{title}</h3>
        <p className="text-slate-600 dark:text-slate-400">{body}</p>
      </div>
      {footer && (
        <div className="px-6 py-3 bg-slate-50 dark:bg-slate-800/50 border-t border-slate-100 dark:border-slate-800">
          {footer}
        </div>
      )}
    </article>
  );
}""",
},
{
    "request": "Tailwind modal/dialog with backdrop",
    "language": "tsx", "framework": "tailwindcss",
    "code": """export function Modal({ open, onClose, children, title }: any) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    document.addEventListener('keydown', onKey);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = '';
    };
  }, [open, onClose]);

  if (!open) return null;

  return createPortal(
    <div
      onClick={onClose}
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        className="
          w-full max-w-lg bg-white dark:bg-slate-900
          rounded-xl shadow-2xl border border-slate-200 dark:border-slate-800
          animate-in zoom-in-95 slide-in-from-bottom-2 duration-200
        "
      >
        {title && (
          <header className="px-6 py-4 border-b border-slate-200 dark:border-slate-800">
            <h2 className="text-lg font-semibold">{title}</h2>
          </header>
        )}
        <div className="p-6">{children}</div>
      </div>
    </div>,
    document.body,
  );
}""",
},
{
    "request": "Tailwind responsive navbar with mobile drawer",
    "language": "tsx", "framework": "tailwindcss",
    "code": """export function Navbar() {
  const [open, setOpen] = useState(false);
  return (
    <header className="sticky top-0 z-40 bg-white/80 dark:bg-slate-900/80 backdrop-blur border-b border-slate-200 dark:border-slate-800">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 flex items-center justify-between h-16">
        <a href="/" className="text-xl font-bold">Brand</a>

        <nav className="hidden md:flex gap-6 text-sm">
          {['Features', 'Pricing', 'Docs', 'Blog'].map((l) => (
            <a key={l} href="#" className="text-slate-600 dark:text-slate-400 hover:text-text">
              {l}
            </a>
          ))}
        </nav>

        <div className="hidden md:flex gap-2">
          <button className="btn-ghost btn-sm">Sign in</button>
          <button className="btn-primary btn-sm">Sign up</button>
        </div>

        <button
          onClick={() => setOpen(!open)}
          className="md:hidden p-2 rounded hover:bg-slate-100 dark:hover:bg-slate-800"
          aria-label="Menu"
        >
          {open ? <X /> : <Menu />}
        </button>
      </div>

      {open && (
        <div className="md:hidden border-t border-slate-200 dark:border-slate-800 px-4 py-3 space-y-2">
          {['Features', 'Pricing', 'Docs', 'Blog'].map((l) => (
            <a key={l} href="#" className="block py-2">{l}</a>
          ))}
          <div className="flex gap-2 pt-2">
            <button className="btn-ghost flex-1">Sign in</button>
            <button className="btn-primary flex-1">Sign up</button>
          </div>
        </div>
      )}
    </header>
  );
}""",
},
{
    "request": "Tailwind dropdown menu with proper a11y",
    "language": "tsx", "framework": "tailwindcss",
    "code": """export function Dropdown({ trigger, items }: { trigger: React.ReactNode, items: {label: string, onClick?: ()=>void}[] }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (!ref.current?.contains(e.target as Node)) setOpen(false);
    };
    if (open) document.addEventListener('click', onClick);
    return () => document.removeEventListener('click', onClick);
  }, [open]);

  return (
    <div ref={ref} className="relative inline-block">
      <button
        onClick={() => setOpen(!open)}
        aria-haspopup="menu" aria-expanded={open}
        className="btn-ghost"
      >
        {trigger}
      </button>
      {open && (
        <div role="menu"
          className="absolute right-0 mt-1 w-48 py-1 bg-white dark:bg-slate-900
                     border border-slate-200 dark:border-slate-800 rounded-md shadow-lg z-50
                     animate-in fade-in slide-in-from-top-1 duration-150">
          {items.map((it, i) => (
            <button
              key={i}
              role="menuitem"
              onClick={() => { it.onClick?.(); setOpen(false); }}
              className="w-full text-left px-3 py-2 text-sm hover:bg-slate-100 dark:hover:bg-slate-800"
            >
              {it.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}""",
},
{
    "request": "Tailwind toast notification system",
    "language": "tsx", "framework": "tailwindcss",
    "code": """interface Toast { id: number; message: string; kind: 'info'|'success'|'error'; }

const ToastCtx = createContext<{ push: (m: string, k?: Toast['kind']) => void }>({ push: () => {} });

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const push = (message: string, kind: Toast['kind'] = 'info') => {
    const id = Date.now();
    setToasts((t) => [...t, { id, message, kind }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 4000);
  };
  return (
    <ToastCtx.Provider value={{ push }}>
      {children}
      <div className="fixed bottom-4 right-4 z-50 space-y-2 pointer-events-none">
        {toasts.map((t) => (
          <div key={t.id} className={`pointer-events-auto px-4 py-3 rounded-lg shadow-lg
            animate-in slide-in-from-right duration-200
            ${t.kind === 'error' ? 'bg-red-600 text-white' :
              t.kind === 'success' ? 'bg-emerald-600 text-white' :
              'bg-slate-900 text-white'}`}>
            {t.message}
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  );
}
export const useToast = () => useContext(ToastCtx);""",
},
{
    "request": "Tailwind skeleton loading shimmer",
    "language": "tsx", "framework": "tailwindcss",
    "code": """export function Skeleton({ className = 'h-4 w-full' }: { className?: string }) {
  return (
    <div className={`
      ${className}
      relative overflow-hidden rounded bg-slate-200 dark:bg-slate-800
      before:absolute before:inset-0
      before:bg-gradient-to-r before:from-transparent before:via-white/40 before:to-transparent
      dark:before:via-white/10
      before:animate-[shimmer_1.5s_infinite]
      before:bg-[length:200%_100%]
    `} />
  );
}

// usage:
// {loading ? <Skeleton className="h-32 w-full rounded-lg" /> : <Image />}

// keyframes in tailwind.config.js:
// keyframes: { shimmer: { '0%': { backgroundPosition: '-200% 0' }, '100%': { backgroundPosition: '200% 0' } } }""",
},
{
    "request": "Tailwind tabs component with keyboard navigation",
    "language": "tsx", "framework": "tailwindcss",
    "code": """export function Tabs({ tabs }: { tabs: { id: string; label: string; content: React.ReactNode }[] }) {
  const [active, setActive] = useState(tabs[0].id);
  return (
    <div>
      <div role="tablist" className="flex border-b border-slate-200 dark:border-slate-800">
        {tabs.map((t) => (
          <button
            key={t.id}
            role="tab"
            aria-selected={active === t.id}
            onClick={() => setActive(t.id)}
            className={`px-4 py-2 -mb-px text-sm font-medium border-b-2 transition-colors
              ${active === t.id
                ? 'border-brand-500 text-brand-500'
                : 'border-transparent text-slate-500 hover:text-text'}`}
          >
            {t.label}
          </button>
        ))}
      </div>
      {tabs.map((t) => (
        <div
          key={t.id}
          role="tabpanel"
          hidden={active !== t.id}
          className="py-4"
        >
          {t.content}
        </div>
      ))}
    </div>
  );
}""",
},
{
    "request": "Tailwind tooltip with positioning",
    "language": "tsx", "framework": "tailwindcss",
    "code": """export function Tooltip({ text, children }: { text: string; children: React.ReactNode }) {
  return (
    <span className="group relative inline-flex">
      {children}
      <span className="
        pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-2
        whitespace-nowrap px-2 py-1 text-xs rounded-md
        bg-slate-900 text-white shadow
        opacity-0 group-hover:opacity-100 transition-opacity
        before:absolute before:top-full before:left-1/2 before:-translate-x-1/2
        before:border-4 before:border-transparent before:border-t-slate-900
      ">
        {text}
      </span>
    </span>
  );
}""",
},
{
    "request": "Tailwind avatar with status dot",
    "language": "tsx", "framework": "tailwindcss",
    "code": """export function Avatar({ src, name, size = 40, status }: any) {
  const initials = name.split(' ').map((s: string) => s[0]).slice(0,2).join('').toUpperCase();
  return (
    <span className="relative inline-flex" style={{ width: size, height: size }}>
      {src ? (
        <img src={src} alt={name}
          className="w-full h-full rounded-full object-cover" />
      ) : (
        <span className="
          w-full h-full rounded-full
          bg-gradient-to-br from-brand-500 to-brand-700
          text-white font-semibold flex items-center justify-center"
          style={{ fontSize: size * 0.4 }}>
          {initials}
        </span>
      )}
      {status && (
        <span className={`absolute bottom-0 right-0 rounded-full ring-2 ring-white dark:ring-slate-900
          ${status === 'online' ? 'bg-emerald-500' : status === 'busy' ? 'bg-red-500' : 'bg-slate-400'}`}
          style={{ width: size * 0.3, height: size * 0.3 }} />
      )}
    </span>
  );
}""",
},
{
    "request": "Tailwind data table with hover, sticky header, selection",
    "language": "tsx", "framework": "tailwindcss",
    "code": """export function DataTable({ rows, cols }: any) {
  const [selected, setSelected] = useState<Set<number>>(new Set());
  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-800">
      <table className="w-full text-sm">
        <thead className="bg-slate-50 dark:bg-slate-800/50 sticky top-0">
          <tr>
            <th className="w-10 p-3">
              <input type="checkbox"
                onChange={(e) => setSelected(e.target.checked ? new Set(rows.map((_:any,i:number) => i)) : new Set())}
              />
            </th>
            {cols.map((c: any) => (
              <th key={c.key} className="p-3 text-left font-semibold text-slate-700 dark:text-slate-300">
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
          {rows.map((row: any, i: number) => (
            <tr key={i} className={`hover:bg-slate-50 dark:hover:bg-slate-800/40
              ${selected.has(i) ? 'bg-brand-50 dark:bg-brand-500/10' : ''}`}>
              <td className="p-3">
                <input type="checkbox" checked={selected.has(i)}
                  onChange={(e) => {
                    const next = new Set(selected);
                    e.target.checked ? next.add(i) : next.delete(i);
                    setSelected(next);
                  }} />
              </td>
              {cols.map((c: any) => (
                <td key={c.key} className="p-3">{c.render ? c.render(row) : row[c.key]}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}""",
},
{
    "request": "Tailwind beautiful pricing cards",
    "language": "tsx", "framework": "tailwindcss",
    "code": """const TIERS = [
  { name: 'Hobby', price: 0, features: ['1 project', 'Community support', '5GB storage'] },
  { name: 'Pro', price: 19, popular: true, features: ['Unlimited projects', 'Email support', '100GB storage', 'Custom domain'] },
  { name: 'Team', price: 49, features: ['Everything in Pro', '10 seats', 'SSO', 'SLA'] },
];

export function Pricing() {
  return (
    <div className="grid md:grid-cols-3 gap-6 max-w-5xl mx-auto p-6">
      {TIERS.map((t) => (
        <div key={t.name} className={`relative rounded-2xl p-8 transition-all
          ${t.popular
            ? 'bg-slate-900 text-white shadow-2xl scale-105 border-2 border-brand-500'
            : 'bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:shadow-lg'}`}>
          {t.popular && (
            <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-brand-500 text-white text-xs px-3 py-1 rounded-full font-semibold">
              MOST POPULAR
            </span>
          )}
          <h3 className="text-xl font-semibold">{t.name}</h3>
          <div className="mt-4 mb-6">
            <span className="text-4xl font-bold">${t.price}</span>
            <span className="text-slate-500">/month</span>
          </div>
          <ul className="space-y-2 mb-8">
            {t.features.map((f) => (
              <li key={f} className="flex items-start gap-2">
                <Check className="w-4 h-4 text-brand-500 mt-0.5" /> {f}
              </li>
            ))}
          </ul>
          <button className={`w-full py-3 rounded-lg font-medium
            ${t.popular ? 'bg-brand-500 hover:bg-brand-700' : 'bg-slate-100 dark:bg-slate-800 hover:bg-slate-200'}`}>
            Get started
          </button>
        </div>
      ))}
    </div>
  );
}""",
},
{
    "request": "Tailwind gradient + shimmer button effect",
    "language": "html", "framework": "tailwindcss",
    "code": """<button class="
  relative overflow-hidden
  px-6 py-3 rounded-lg font-medium text-white
  bg-gradient-to-r from-violet-600 via-pink-500 to-orange-500
  hover:saturate-150 transition-all
  shadow-lg shadow-pink-500/30
">
  <span class="relative z-10">Subscribe</span>
  <span class="
    absolute inset-0
    bg-gradient-to-r from-transparent via-white/30 to-transparent
    -translate-x-full hover:translate-x-full transition-transform duration-700
  "></span>
</button>""",
},
{
    "request": "Tailwind responsive image gallery with hover zoom",
    "language": "html", "framework": "tailwindcss",
    "code": """<div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
  {photos.map(p =>
    <figure class="group relative aspect-square overflow-hidden rounded-lg cursor-pointer">
      <img src={p.url}
        class="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110" />
      <figcaption class="
        absolute inset-x-0 bottom-0 p-3
        bg-gradient-to-t from-black/80 to-transparent
        text-white text-sm
        opacity-0 group-hover:opacity-100 transition-opacity
      ">
        {p.caption}
      </figcaption>
    </figure>
  )}
</div>""",
},
{
    "request": "Tailwind chat message bubbles with tails",
    "language": "tsx", "framework": "tailwindcss",
    "code": """export function ChatBubble({ from, text, time }: { from: 'me'|'them'; text: string; time: string }) {
  const isMe = from === 'me';
  return (
    <div className={`flex ${isMe ? 'justify-end' : 'justify-start'} mb-2`}>
      <div className={`
        relative max-w-xs lg:max-w-md px-4 py-2 rounded-2xl
        ${isMe
          ? 'bg-brand-500 text-white rounded-br-sm'
          : 'bg-slate-100 dark:bg-slate-800 rounded-bl-sm'}
      `}>
        <p>{text}</p>
        <span className={`block text-xs mt-1 opacity-60 text-right`}>{time}</span>
      </div>
    </div>
  );
}""",
},
{
    "request": "Tailwind animated underline tab nav",
    "language": "tsx", "framework": "tailwindcss",
    "code": """export function UnderlineTabs({ tabs, value, onChange }: any) {
  return (
    <div className="flex items-center gap-1 border-b border-slate-200 dark:border-slate-800 relative">
      {tabs.map((t: any, i: number) => (
        <button key={t.id} onClick={() => onChange(t.id)}
          className={`px-4 py-2 text-sm font-medium relative transition-colors
            ${value === t.id ? 'text-brand-500' : 'text-slate-500 hover:text-text'}`}>
          {t.label}
          {value === t.id && (
            <span className="absolute -bottom-px left-0 right-0 h-0.5 bg-brand-500 rounded-t" />
          )}
        </button>
      ))}
    </div>
  );
}""",
},
{
    "request": "Tailwind status badge with semantic colors",
    "language": "tsx", "framework": "tailwindcss",
    "code": """const VARIANTS = {
  success: 'bg-emerald-50 text-emerald-700 ring-emerald-600/20 dark:bg-emerald-500/10 dark:text-emerald-400',
  warn:    'bg-amber-50   text-amber-700   ring-amber-600/20   dark:bg-amber-500/10   dark:text-amber-400',
  error:   'bg-red-50     text-red-700     ring-red-600/20     dark:bg-red-500/10     dark:text-red-400',
  info:    'bg-sky-50     text-sky-700     ring-sky-600/20     dark:bg-sky-500/10     dark:text-sky-400',
  neutral: 'bg-slate-50   text-slate-700   ring-slate-600/20   dark:bg-slate-500/10   dark:text-slate-400',
};

export function Badge({ children, variant = 'neutral' }: { children: React.ReactNode; variant?: keyof typeof VARIANTS }) {
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium
                       ring-1 ring-inset ${VARIANTS[variant]}`}>
      {children}
    </span>
  );
}""",
},
{
    "request": "Tailwind animated progress bar (determinate + indeterminate)",
    "language": "tsx", "framework": "tailwindcss",
    "code": """export function Progress({ value }: { value?: number }) {
  if (value === undefined) {
    // indeterminate
    return (
      <div className="w-full h-2 bg-slate-200 dark:bg-slate-800 rounded overflow-hidden">
        <div className="h-full w-1/3 bg-brand-500 rounded
          animate-[slide_1.2s_ease-in-out_infinite]" />
      </div>
    );
  }
  return (
    <div className="w-full h-2 bg-slate-200 dark:bg-slate-800 rounded overflow-hidden">
      <div
        className="h-full bg-brand-500 transition-all duration-500 ease-out rounded"
        style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
      />
    </div>
  );
}

// keyframes in tailwind config:
// keyframes: { slide: { '0%':{transform:'translateX(-100%)'}, '100%':{transform:'translateX(400%)'} } }""",
},
{
    "request": "Tailwind input + textarea fully styled with focus rings",
    "language": "tsx", "framework": "tailwindcss",
    "code": """const baseInput = `
  w-full px-3 py-2 rounded-md
  bg-white dark:bg-slate-900
  border border-slate-300 dark:border-slate-700
  text-text placeholder:text-slate-400
  focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500
  disabled:opacity-50 disabled:cursor-not-allowed
  transition-shadow
`;

export const Input = (p: React.InputHTMLAttributes<HTMLInputElement>) =>
  <input {...p} className={baseInput} />;

export const Textarea = (p: React.TextareaHTMLAttributes<HTMLTextAreaElement>) =>
  <textarea {...p} className={`${baseInput} min-h-[100px] resize-y`} />;

// validation state:
// <input className={`${baseInput} ${errors.email ? 'border-red-500 focus:ring-red-500' : ''}`} />""",
},
]
