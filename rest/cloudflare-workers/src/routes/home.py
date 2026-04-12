"""Home page for the UCP demo server."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter()

HOME_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>UCP Demo Server</title>
<style>
  :root { --bg: #0a0a0a; --fg: #e4e4e7; --muted: #a1a1aa; --accent: #3b82f6; --surface: #18181b; --border: #27272a; --green: #22c55e; --orange: #f59e0b; --red: #ef4444; }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: var(--bg); color: var(--fg); line-height: 1.6; }
  .container { max-width: 860px; margin: 0 auto; padding: 2rem 1.5rem; }
  h1 { font-size: 2rem; font-weight: 700; margin-bottom: 0.25rem; }
  .subtitle { color: var(--muted); font-size: 1.1rem; margin-bottom: 2rem; }
  .badge { display: inline-block; font-size: 0.75rem; font-weight: 600; padding: 0.2rem 0.6rem; border-radius: 9999px; background: #1e3a5f; color: var(--accent); margin-left: 0.5rem; vertical-align: middle; }
  .badge.green { background: #14532d; color: var(--green); }
  .badge.sm { font-size: 0.65rem; padding: 0.1rem 0.45rem; margin-left: 0; }
  .badge.stock { background: #14532d; color: var(--green); }
  .badge.oos { background: #3b0d0d; color: var(--red); }
  h2 { font-size: 1.25rem; font-weight: 600; margin: 2rem 0 0.75rem; padding-top: 1.5rem; border-top: 1px solid var(--border); }
  h2:first-of-type { border-top: none; padding-top: 0; }
  p, li { color: var(--muted); }
  a { color: var(--accent); text-decoration: none; }
  a:hover { text-decoration: underline; }
  code { font-family: "SF Mono", "Fira Code", monospace; font-size: 0.85em; background: var(--surface); padding: 0.15rem 0.4rem; border-radius: 4px; border: 1px solid var(--border); }
  pre { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 1rem 1.25rem; overflow-x: auto; margin: 0.75rem 0; }
  pre code { background: none; border: none; padding: 0; font-size: 0.8rem; line-height: 1.7; }
  .string { color: #34d399; }
  table { width: 100%; border-collapse: collapse; margin: 0.75rem 0; font-size: 0.9rem; }
  th, td { text-align: left; padding: 0.5rem 0.75rem; border-bottom: 1px solid var(--border); }
  th { color: var(--fg); font-weight: 600; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.05em; }
  td code { font-size: 0.8rem; }

  /* Search bar */
  .search-bar { display: flex; gap: 0.5rem; margin-bottom: 1rem; }
  .search-bar input { flex: 1; padding: 0.5rem 0.75rem; background: var(--surface); border: 1px solid var(--border); border-radius: 6px; color: var(--fg); font-size: 0.9rem; outline: none; }
  .search-bar input:focus { border-color: var(--accent); }
  .search-bar button { padding: 0.5rem 1.25rem; background: var(--accent); color: white; border: none; border-radius: 6px; font-size: 0.9rem; font-weight: 500; cursor: pointer; }
  .search-bar button:hover { background: #2563eb; }

  /* Product cards */
  .product-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 0.75rem; margin: 0.75rem 0; }
  .product { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 1rem; transition: border-color 0.15s; cursor: pointer; }
  .product:hover { border-color: var(--accent); }
  .product .name { font-weight: 600; color: var(--fg); margin-bottom: 0.25rem; }
  .product .desc { color: var(--muted); font-size: 0.8rem; margin-bottom: 0.5rem; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
  .product .meta { display: flex; align-items: center; justify-content: space-between; gap: 0.5rem; }
  .product .price { color: var(--green); font-weight: 700; font-size: 1.1rem; }
  .product .id-label { color: var(--muted); font-size: 0.75rem; font-family: monospace; }
  .product .cats { margin-top: 0.5rem; display: flex; flex-wrap: wrap; gap: 0.3rem; }
  .product .cat { font-size: 0.65rem; padding: 0.1rem 0.4rem; border-radius: 4px; background: var(--bg); border: 1px solid var(--border); color: var(--muted); }
  .product-loading { color: var(--muted); text-align: center; padding: 2rem; }
  .pagination { display: flex; justify-content: center; gap: 0.5rem; margin-top: 0.75rem; }
  .pagination button { padding: 0.35rem 0.75rem; background: var(--surface); border: 1px solid var(--border); border-radius: 4px; color: var(--fg); font-size: 0.8rem; cursor: pointer; }
  .pagination button:hover { border-color: var(--accent); }
  .pagination button:disabled { opacity: 0.3; cursor: default; }
  .result-count { color: var(--muted); font-size: 0.8rem; margin-bottom: 0.5rem; }

  /* Product detail panel */
  .detail-panel { background: var(--surface); border: 1px solid var(--accent); border-radius: 8px; padding: 1.5rem; margin: 1rem 0; display: none; }
  .detail-panel h3 { font-size: 1.2rem; margin-bottom: 0.5rem; }
  .detail-panel .detail-desc { color: var(--muted); margin-bottom: 0.75rem; }
  .detail-panel .detail-meta { display: flex; gap: 1.5rem; flex-wrap: wrap; font-size: 0.9rem; }
  .detail-panel .detail-meta div { display: flex; flex-direction: column; gap: 0.15rem; }
  .detail-panel .detail-meta .label { color: var(--muted); font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; }
  .detail-close { float: right; background: none; border: none; color: var(--muted); font-size: 1.2rem; cursor: pointer; }
  .detail-close:hover { color: var(--fg); }
  .detail-json { margin-top: 1rem; }
  .detail-json summary { color: var(--accent); cursor: pointer; font-size: 0.85rem; }
  .detail-json pre { max-height: 250px; overflow-y: auto; margin-top: 0.5rem; }

  /* Option picker */
  .option-picker { margin: 1rem 0; display: flex; flex-wrap: wrap; gap: 1rem; }
  .option-group { display: flex; flex-direction: column; gap: 0.4rem; }
  .option-group .option-label { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted); font-weight: 600; }
  .option-values { display: flex; flex-wrap: wrap; gap: 0.35rem; }
  .option-chip { padding: 0.35rem 0.75rem; border: 1px solid var(--border); border-radius: 6px; font-size: 0.8rem; cursor: pointer; background: var(--bg); color: var(--fg); transition: all 0.15s; }
  .option-chip:hover { border-color: var(--accent); }
  .option-chip.selected { background: var(--accent); border-color: var(--accent); color: white; font-weight: 600; }
  .option-chip.unavailable { opacity: 0.4; text-decoration: line-through; }
  .option-chip.unavailable.selected { opacity: 0.7; }
  .option-chip.no-exist { opacity: 0.2; cursor: not-allowed; }
  .detail-variant-info { margin-top: 0.75rem; padding: 0.75rem; background: var(--bg); border: 1px solid var(--border); border-radius: 6px; font-size: 0.85rem; }
  .detail-variant-info .variant-title { font-weight: 600; color: var(--fg); }
  .detail-variant-info .variant-id { font-family: monospace; font-size: 0.75rem; color: var(--muted); }

  /* Fulfillment toggle */
  .fulfillment-toggle { display: flex; gap: 0; border: 1px solid var(--border); border-radius: 6px; overflow: hidden; margin: 0.5rem 0; }
  .fulfillment-toggle button { flex: 1; padding: 0.5rem 1rem; background: var(--bg); border: none; color: var(--muted); font-size: 0.85rem; cursor: pointer; transition: all 0.15s; }
  .fulfillment-toggle button.active { background: var(--accent); color: white; font-weight: 600; }
  .fulfillment-toggle button:hover:not(.active) { color: var(--fg); }

  /* Checkout tabs */
  .checkout-tabs { margin: 1rem 0; }
  .tab-bar { display: flex; justify-content: center; gap: 0; border-bottom: 1px solid var(--border); margin-bottom: 0; }
  .tab-btn { padding: 0.6rem 1.25rem; background: none; border: none; border-bottom: 2px solid transparent; color: var(--muted); font-size: 0.9rem; font-weight: 500; cursor: pointer; transition: color 0.15s, border-color 0.15s; }
  .tab-btn:hover { color: var(--fg); }
  .tab-btn.active { color: var(--accent); border-bottom-color: var(--accent); }
  .tab-panel { display: none; padding: 0.5rem 0 0; }
  .tab-panel.active { display: block; }

  /* Steps */
  .step { display: flex; gap: 0.75rem; margin: 1rem 0; }
  .step-num { flex-shrink: 0; min-width: 1.75rem; height: 1.75rem; padding: 0 0.4rem; border-radius: 9999px; background: var(--accent); color: white; font-weight: 700; font-size: 0.8rem; display: flex; align-items: center; justify-content: center; margin-top: 0.1rem; }
  .step-content { flex: 1; }
  .step-content strong { color: var(--fg); }
  .try-btn { display: inline-block; margin-top: 0.5rem; padding: 0.4rem 1rem; background: var(--accent); color: white; border-radius: 6px; font-size: 0.85rem; font-weight: 500; cursor: pointer; border: none; }
  .try-btn:hover { background: #2563eb; }
  .response-box { background: #0f1729; border: 1px solid #1e3a5f; border-radius: 8px; padding: 1rem; margin-top: 0.5rem; display: none; max-height: 300px; overflow-y: auto; }
  .response-box pre { background: none; border: none; padding: 0; margin: 0; }
  footer { margin-top: 3rem; padding-top: 1.5rem; border-top: 1px solid var(--border); color: var(--muted); font-size: 0.85rem; text-align: center; }
</style>
</head>
<body>
<div class="container">
  <h1>UCP Demo Server <span class="badge green">v2026-04-08</span></h1>
  <p class="subtitle">A reference implementation of the <a href="https://ucp.dev">Universal Commerce Protocol</a> specification. Meant to be a helpful aid to those building UCP clients.</p>
  <p class="subtitle">The endpoints listed below are all live on this server, making it easy to test your UCP client using the reference flower shop data.</p>
  <h2>Catalog</h2>
  <div class="search-bar">
    <input type="text" id="searchInput" placeholder="Search products (e.g. roses, orchid, pot...)" />
    <button onclick="searchCatalog()">Search</button>
  </div>
  <div class="result-count" id="resultCount"></div>
  <div class="product-grid" id="productGrid">
    <div class="product-loading">Loading catalog...</div>
  </div>
  <div class="pagination" id="pagination"></div>
  <div class="detail-panel" id="detailPanel"></div>

  <h2>Quick Start</h2>

  <div class="step">
    <div class="step-num">1</div>
    <div class="step-content">
      <strong>Discover capabilities</strong>
      <p>Fetch the merchant profile to see supported services, capabilities, and payment handlers.</p>
      <pre><code>curl {{BASE}}/.well-known/ucp</code></pre>
      <button class="try-btn" onclick="tryIt(this, '/.well-known/ucp', 'GET')">Try it</button>
      <div class="response-box"><pre><code></code></pre></div>
    </div>
  </div>

  <div class="step">
    <div class="step-num">2</div>
    <div class="step-content">
      <strong>Search the catalog</strong>
      <p>Use the catalog search endpoint to discover products.</p>
      <pre><code>curl -X POST {{BASE}}/catalog/search \\
  -H <span class="string">"Content-Type: application/json"</span> \\
  -H <span class="string">'UCP-Agent: profile="https://agent.example/profile"'</span> \\
  -H <span class="string">"request-signature: test"</span> \\
  -H <span class="string">"request-id: &lt;unique-id&gt;"</span> \\
  -d <span class="string">'{"query": "roses", "pagination": {"limit": 5}}'</span></code></pre>
      <button class="try-btn" onclick="trySearch(this)">Try it</button>
      <div class="response-box"><pre><code></code></pre></div>
    </div>
  </div>

  <div class="checkout-tabs">
    <div class="tab-bar">
      <button class="tab-btn active" onclick="switchTab('direct')">Direct checkout</button>
      <button class="tab-btn" onclick="switchTab('cart')">Via cart</button>
    </div>
    <div class="tab-panel active" id="tab-direct">
      <div class="step" style="margin-top:0">
        <div class="step-num">3</div>
        <div class="step-content">
          <strong>Create a checkout</strong>
          <p>Go straight to checkout with line items. Choose a fulfillment method:</p>
          <div class="fulfillment-toggle">
            <button class="active" onclick="setFulfillment('shipping', this)">Shipping</button>
            <button onclick="setFulfillment('pickup', this)">Pickup</button>
          </div>
          <pre><code id="checkoutCurl">curl -X POST {{BASE}}/checkout-sessions \\
  -H <span class="string">"Content-Type: application/json"</span> \\
  -H <span class="string">'UCP-Agent: profile="https://agent.example/profile"'</span> \\
  -H <span class="string">"request-signature: test"</span> \\
  -H <span class="string">"idempotency-key: &lt;unique-key&gt;"</span> \\
  -H <span class="string">"request-id: &lt;unique-id&gt;"</span> \\
  -d <span class="string">'{
  "line_items": [
    {"item": {"id": "bouquet_roses", "title": "Roses"}, "quantity": 1}
  ],
  "buyer": {"full_name": "Jane Doe", "email": "jane@example.com"},
  "fulfillment": {"methods": [{"type": "shipping", "destinations": [{"address_country": "US", "postal_code": "97201"}]}]},
  "payment": {"instruments": []}
}'</span></code></pre>
          <button class="try-btn" onclick="tryCheckout(this)">Try it</button>
          <div class="response-box"><pre><code></code></pre></div>
        </div>
      </div>
    </div>
    <div class="tab-panel" id="tab-cart">
      <div class="step" style="margin-top:0">
        <div class="step-num">3a</div>
        <div class="step-content">
          <strong>Create a cart</strong>
          <p>Add items to a lightweight cart for exploration.</p>
          <pre><code>curl -X POST {{BASE}}/carts \\
  -H <span class="string">"Content-Type: application/json"</span> \\
  -H <span class="string">'UCP-Agent: profile="https://agent.example/profile"'</span> \\
  -H <span class="string">"request-signature: test"</span> \\
  -H <span class="string">"idempotency-key: &lt;unique-key&gt;"</span> \\
  -H <span class="string">"request-id: &lt;unique-id&gt;"</span> \\
  -d <span class="string">'{
  "line_items": [
    {"item": {"id": "bouquet_roses"}, "quantity": 2},
    {"item": {"id": "pot_ceramic"}, "quantity": 1}
  ]
}'</span></code></pre>
          <button class="try-btn" onclick="tryCart(this)">Try it</button>
          <div class="response-box"><pre><code></code></pre></div>
        </div>
      </div>
      <div class="step">
        <div class="step-num">3b</div>
        <div class="step-content">
          <strong>Convert cart to checkout</strong>
          <p>Pass <code>cart_id</code> to create a checkout from the cart.</p>
          <pre><code>curl -X POST {{BASE}}/checkout-sessions \\
  -H <span class="string">"Content-Type: application/json"</span> \\
  -H <span class="string">'UCP-Agent: profile="https://agent.example/profile"'</span> \\
  -H <span class="string">"request-signature: test"</span> \\
  -H <span class="string">"idempotency-key: &lt;unique-key&gt;"</span> \\
  -H <span class="string">"request-id: &lt;unique-id&gt;"</span> \\
  -d <span class="string">'{"cart_id": "&lt;cart-id&gt;"}'</span></code></pre>
          <button class="try-btn" onclick="tryCartCheckout(this)">Try it</button>
          <div class="response-box"><pre><code></code></pre></div>
        </div>
      </div>
    </div>
  </div>

  <div class="step">
    <div class="step-num">4</div>
    <div class="step-content">
      <strong>Apply a discount</strong>
      <p>Update the checkout with a discount code. Available codes:</p>
      <table>
        <tr><th>Code</th><th>Type</th><th>Value</th></tr>
        <tr><td><code>10OFF</code></td><td>Percentage</td><td>10% off</td></tr>
        <tr><td><code>WELCOME20</code></td><td>Percentage</td><td>20% off</td></tr>
        <tr><td><code>FIXED500</code></td><td>Fixed</td><td>$5.00 off</td></tr>
      </table>
    </div>
  </div>

  <h2>Endpoints</h2>
  <table>
    <tr><th>Method</th><th>Path</th><th>Description</th></tr>
    <tr><td><code>GET</code></td><td><code>/.well-known/ucp</code></td><td>Discovery profile</td></tr>
    <tr><td colspan="3" style="color:var(--accent);font-weight:600;font-size:0.8rem;padding-top:0.75rem;">CATALOG</td></tr>
    <tr><td><code>POST</code></td><td><code>/catalog/search</code></td><td>Search products</td></tr>
    <tr><td><code>POST</code></td><td><code>/catalog/lookup</code></td><td>Batch lookup by IDs</td></tr>
    <tr><td><code>POST</code></td><td><code>/catalog/product</code></td><td>Get product detail</td></tr>
    <tr><td colspan="3" style="color:var(--accent);font-weight:600;font-size:0.8rem;padding-top:0.75rem;">CART</td></tr>
    <tr><td><code>POST</code></td><td><code>/carts</code></td><td>Create cart</td></tr>
    <tr><td><code>GET</code></td><td><code>/carts/{id}</code></td><td>Get cart</td></tr>
    <tr><td><code>PUT</code></td><td><code>/carts/{id}</code></td><td>Update cart</td></tr>
    <tr><td><code>POST</code></td><td><code>/carts/{id}/cancel</code></td><td>Cancel cart</td></tr>
    <tr><td colspan="3" style="color:var(--accent);font-weight:600;font-size:0.8rem;padding-top:0.75rem;">CHECKOUT</td></tr>
    <tr><td><code>POST</code></td><td><code>/checkout-sessions</code></td><td>Create checkout</td></tr>
    <tr><td><code>GET</code></td><td><code>/checkout-sessions/{id}</code></td><td>Get checkout</td></tr>
    <tr><td><code>PUT</code></td><td><code>/checkout-sessions/{id}</code></td><td>Update checkout</td></tr>
    <tr><td><code>POST</code></td><td><code>/checkout-sessions/{id}/complete</code></td><td>Complete checkout</td></tr>
    <tr><td><code>POST</code></td><td><code>/checkout-sessions/{id}/cancel</code></td><td>Cancel checkout</td></tr>
    <tr><td colspan="3" style="color:var(--accent);font-weight:600;font-size:0.8rem;padding-top:0.75rem;">ORDERS</td></tr>
    <tr><td><code>GET</code></td><td><code>/orders/{id}</code></td><td>Get order</td></tr>
    <tr><td><code>PUT</code></td><td><code>/orders/{id}</code></td><td>Update order</td></tr>
  </table>

  <h2>Required Headers</h2>
  <table>
    <tr><th>Header</th><th>Value</th><th>Required</th></tr>
    <tr><td><code>UCP-Agent</code></td><td><code>profile="https://agent.example/profile"</code></td><td>All requests</td></tr>
    <tr><td><code>request-signature</code></td><td><code>test</code> (bypasses validation)</td><td>All requests</td></tr>
    <tr><td><code>request-id</code></td><td>Any unique string</td><td>All requests</td></tr>
    <tr><td><code>idempotency-key</code></td><td>Any unique string</td><td>POST / PUT (checkout)</td></tr>
  </table>

  <h2>Links</h2>
  <p>
    <a href="https://ucp.dev">UCP Specification</a> &middot;
    <a href="https://github.com/Universal-Commerce-Protocol/ucp/releases/tag/v2026-04-08">v2026-04-08 Release</a> &middot;
    <a href="https://github.com/Universal-Commerce-Protocol/samples">Samples Repo</a> &middot;
    <a href="https://developers.googleblog.com/under-the-hood-universal-commerce-protocol-ucp/">Blog Post</a> &middot;
    <a href="/docs">OpenAPI Docs</a>
  </p>

  <footer>
    Shipped with <svg style="display:inline-block;vertical-align:middle;margin:0 0.15rem" width="16" height="16" viewBox="0 0 24 24" fill="#ef4444" xmlns="http://www.w3.org/2000/svg"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/></svg> by <a href="https://runtype.com" target="_blank" rel="noopener"><img src="https://www.runtype.com/runtype-text-only.svg" alt="Runtype" style="display:inline-block;vertical-align:middle;height:1em;filter:invert(1);margin-left:0.2rem;margin-top: 2px" /></a>
  </footer>
</div>

<script>
const BASE = window.location.origin;
const UCP_HEADERS = {
  'Content-Type': 'application/json',
  'UCP-Agent': 'profile="https://agent.example/profile"',
  'Signature': 'sig=:test:',
  'Request-Id': 'homepage-' + Date.now(),
};

document.querySelectorAll('code').forEach(el => {
  el.innerHTML = el.innerHTML.replace(/{{BASE}}/g, BASE);
});

// --- Catalog search ---
let currentCursor = null;
let currentQuery = '';

document.getElementById('searchInput').addEventListener('keydown', e => {
  if (e.key === 'Enter') searchCatalog();
});

async function searchCatalog(cursor) {
  const grid = document.getElementById('productGrid');
  const countEl = document.getElementById('resultCount');
  const query = document.getElementById('searchInput').value.trim();
  currentQuery = query;

  grid.innerHTML = '<div class="product-loading">Searching...</div>';
  countEl.textContent = '';

  const body = { query, pagination: { limit: 6 } };
  if (cursor) body.pagination.cursor = cursor;

  try {
    const res = await fetch(BASE + '/catalog/search', {
      method: 'POST', headers: UCP_HEADERS,
      body: JSON.stringify(body),
    });
    const data = await res.json();
    renderProducts(data.products);
    renderPagination(data.pagination);
    const total = data.pagination.total_count;
    if (total !== undefined) {
      countEl.textContent = total + ' product' + (total !== 1 ? 's' : '') + (query ? ' matching "' + query + '"' : '');
    }
  } catch(e) {
    grid.innerHTML = '<div class="product-loading">Error: ' + e.message + '</div>';
  }
}

function renderProducts(products) {
  const grid = document.getElementById('productGrid');
  if (!products || products.length === 0) {
    grid.innerHTML = '<div class="product-loading">No products found</div>';
    return;
  }
  grid.innerHTML = products.map(p => {
    const variant = p.variants && p.variants[0];
    const price = variant && variant.price ? '$' + (variant.price.amount / 100).toFixed(2) : '';
    const available = variant && variant.availability ? variant.availability.available : true;
    const status = available ? 'In stock' : 'Out of stock';
    const statusClass = available ? 'stock' : 'oos';
    const desc = p.description && p.description.plain ? p.description.plain : '';
    const cats = (p.categories || []).map(c => '<span class="cat">' + c.value + '</span>').join('');
    return '<div class="product" onclick="showDetail(\\''+p.id+'\\')">' +
      '<div class="name">' + p.title + '</div>' +
      (desc ? '<div class="desc">' + desc + '</div>' : '') +
      '<div class="meta">' +
        '<span class="price">' + price + '</span>' +
        '<span class="badge sm ' + statusClass + '">' + status + '</span>' +
      '</div>' +
      '<div class="id-label">' + p.id + '</div>' +
      (cats ? '<div class="cats">' + cats + '</div>' : '') +
    '</div>';
  }).join('');
}

function renderPagination(pg) {
  const el = document.getElementById('pagination');
  if (!pg) { el.innerHTML = ''; return; }
  currentCursor = pg.cursor;
  el.innerHTML = pg.has_next_page
    ? '<button onclick="searchCatalog(\\''+pg.cursor+'\\')">Load more</button>'
    : '';
}

let currentDetailProductId = null;
let currentSelections = [];

async function showDetail(productId, selected) {
  currentDetailProductId = productId;
  const panel = document.getElementById('detailPanel');
  panel.style.display = 'block';
  panel.innerHTML = '<div class="product-loading">Loading...</div>';
  panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

  const reqBody = { id: productId };
  if (selected && selected.length > 0) {
    reqBody.selected = selected;
    reqBody.preferences = selected.map(s => s.name);
  }

  try {
    const res = await fetch(BASE + '/catalog/product', {
      method: 'POST', headers: UCP_HEADERS,
      body: JSON.stringify(reqBody),
    });
    const data = await res.json();
    const p = data.product;
    if (!p) {
      panel.innerHTML = '<button class="detail-close" onclick="this.parentElement.style.display=\\'none\\'">&times;</button><p>Product not found</p>';
      return;
    }

    // Track effective selections from response
    currentSelections = p.selected || [];

    const variant = p.variants && p.variants[0];
    const price = variant && variant.price ? '$' + (variant.price.amount / 100).toFixed(2) : 'N/A';
    const avail = variant && variant.availability;
    const status = avail ? (avail.available ? 'In stock' : avail.status.replace(/_/g,' ')) : 'Unknown';
    const statusClass = avail && avail.available ? 'stock' : 'oos';
    const desc = p.description && p.description.plain ? p.description.plain : '';

    // Build option picker UI
    let optionHtml = '';
    if (p.options && p.options.length > 0) {
      optionHtml = '<div class="option-picker">';
      for (const opt of p.options) {
        const selectedVal = currentSelections.find(s => s.name === opt.name);
        optionHtml += '<div class="option-group"><span class="option-label">' + opt.name + '</span><div class="option-values">';
        for (const val of opt.values) {
          let cls = 'option-chip';
          if (selectedVal && selectedVal.label === val.label) cls += ' selected';
          if (val.exists === false) cls += ' no-exist';
          else if (val.available === false) cls += ' unavailable';
          const disabled = val.exists === false ? ' disabled' : '';
          optionHtml += '<button class="' + cls + '"' + disabled + ' onclick="selectOption(\\'' + p.id + '\\', \\'' + opt.name + '\\', \\'' + val.label + '\\')">' + val.label + '</button>';
        }
        optionHtml += '</div></div>';
      }
      optionHtml += '</div>';
    }

    // Variant info
    let variantHtml = '';
    if (variant) {
      variantHtml = '<div class="detail-variant-info">' +
        '<span class="variant-title">' + (variant.title || variant.id) + '</span>' +
        ' <span class="badge sm ' + statusClass + '">' + status + '</span>' +
        '<div class="variant-id">variant: ' + variant.id + (variant.sku ? ' &middot; SKU: ' + variant.sku : '') + '</div>' +
      '</div>';
    }

    panel.innerHTML =
      '<button class="detail-close" onclick="this.parentElement.style.display=\\'none\\'">&times;</button>' +
      '<h3>' + p.title + ' <span style="color:var(--green);font-weight:700;font-size:1.1rem">' + price + '</span></h3>' +
      (desc ? '<div class="detail-desc">' + desc + '</div>' : '') +
      optionHtml +
      variantHtml +
      '<details class="detail-json"><summary>Raw UCP response</summary><pre><code>' + JSON.stringify(data, null, 2) + '</code></pre></details>';
  } catch(e) {
    panel.innerHTML = '<button class="detail-close" onclick="this.parentElement.style.display=\\'none\\'">&times;</button><p>Error: ' + e.message + '</p>';
  }
}

function selectOption(productId, optName, optLabel) {
  // Update selections: replace existing selection for this option name, or add new one
  let newSelections = currentSelections.filter(s => s.name !== optName);
  newSelections.push({ name: optName, label: optLabel });
  showDetail(productId, newSelections);
}

// --- Try-it buttons ---
async function tryIt(btn, path, method) {
  const box = btn.nextElementSibling;
  const code = box.querySelector('code');
  box.style.display = 'block';
  code.textContent = 'Loading...';
  try {
    const res = await fetch(BASE + path, {method});
    const data = await res.json();
    code.textContent = JSON.stringify(data, null, 2);
  } catch(e) { code.textContent = 'Error: ' + e.message; }
}

async function trySearch(btn) {
  const box = btn.nextElementSibling;
  const code = box.querySelector('code');
  box.style.display = 'block';
  code.textContent = 'Loading...';
  try {
    const res = await fetch(BASE + '/catalog/search', {
      method: 'POST', headers: UCP_HEADERS,
      body: JSON.stringify({ query: 'roses', pagination: { limit: 5 } }),
    });
    const data = await res.json();
    code.textContent = JSON.stringify(data, null, 2);
  } catch(e) { code.textContent = 'Error: ' + e.message; }
}

async function tryCart(btn) {
  const box = btn.nextElementSibling;
  const code = box.querySelector('code');
  box.style.display = 'block';
  code.textContent = 'Loading...';
  const key = 'demo-cart-' + Date.now() + '-' + Math.random().toString(36).slice(2,8);
  try {
    const res = await fetch(BASE + '/carts', {
      method: 'POST',
      headers: { ...UCP_HEADERS, 'idempotency-key': key },
      body: JSON.stringify({
        line_items: [
          {item: {id: 'bouquet_roses'}, quantity: 2},
          {item: {id: 'pot_ceramic'}, quantity: 1},
        ],
      }),
    });
    const data = await res.json();
    if (data.id) lastCartId = data.id;
    code.textContent = JSON.stringify(data, null, 2);
  } catch(e) { code.textContent = 'Error: ' + e.message; }
}

function switchTab(tab) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.querySelector('.tab-btn[onclick*="' + tab + '"]').classList.add('active');
  document.getElementById('tab-' + tab).classList.add('active');
}

let lastCartId = null;

async function tryCartCheckout(btn) {
  const box = btn.nextElementSibling;
  const code = box.querySelector('code');
  box.style.display = 'block';

  if (!lastCartId) {
    code.textContent = 'No cart created yet. Click "Try it" on step 3a first.';
    return;
  }

  code.textContent = 'Converting cart ' + lastCartId.slice(0,12) + '... to checkout...';
  const key = 'demo-c2c-' + Date.now() + '-' + Math.random().toString(36).slice(2,8);
  try {
    const res = await fetch(BASE + '/checkout-sessions', {
      method: 'POST',
      headers: { ...UCP_HEADERS, 'idempotency-key': key },
      body: JSON.stringify({ cart_id: lastCartId, line_items: [] }),
    });
    const data = await res.json();
    code.textContent = JSON.stringify(data, null, 2);
  } catch(e) { code.textContent = 'Error: ' + e.message; }
}

let selectedFulfillment = 'shipping';

function setFulfillment(mode, btn) {
  selectedFulfillment = mode;
  btn.parentElement.querySelectorAll('button').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
}

async function tryCheckout(btn) {
  const box = btn.nextElementSibling;
  const code = box.querySelector('code');
  box.style.display = 'block';
  code.textContent = 'Loading...';
  const key = 'demo-' + Date.now() + '-' + Math.random().toString(36).slice(2,8);

  const body = {
    line_items: [{item: {id: 'bouquet_roses', title: 'Roses'}, quantity: 1}],
    buyer: {full_name: 'Jane Doe', email: 'jane@example.com'},
    payment: {instruments: []},
  };

  if (selectedFulfillment === 'pickup') {
    body.fulfillment = {
      methods: [{
        type: 'pickup',
        destinations: [{name: 'Downtown Flower Shop'}],
      }],
    };
  } else {
    body.fulfillment = {
      methods: [{
        type: 'shipping',
        destinations: [{address_country: 'US', postal_code: '97201', address_region: 'OR', address_locality: 'Portland', street_address: '123 Main St'}],
      }],
    };
  }

  try {
    const res = await fetch(BASE + '/checkout-sessions', {
      method: 'POST',
      headers: { ...UCP_HEADERS, 'idempotency-key': key },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    code.textContent = JSON.stringify(data, null, 2);
  } catch(e) { code.textContent = 'Error: ' + e.message; }
}

// Load catalog on page load
searchCatalog();
</script>
</body>
</html>"""


@router.get("/", response_class=HTMLResponse)
async def home():
  return HOME_HTML
