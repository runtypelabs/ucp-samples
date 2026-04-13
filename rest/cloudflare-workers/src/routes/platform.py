"""Platform demo page — live UCP agent + session inspector."""

from fastapi import APIRouter, Path, Request
from fastapi.responses import HTMLResponse, JSONResponse

import db

router = APIRouter()


# --- Session inspector API ---

@router.get("/platform/api/session/{id}")
async def get_session(request: Request, session_id: str = Path(..., alias="id")):
  d1 = request.app.state.db
  result = await db.get_session_by_id(d1, session_id)
  if not result:
    return JSONResponse({"error": "Not found"}, status_code=404)
  return result


@router.get("/platform/api/logs/{id}")
async def get_logs(request: Request, checkout_id: str = Path(..., alias="id")):
  d1 = request.app.state.db
  logs = await db.get_request_logs_for_session(d1, checkout_id)
  return {"logs": logs}


# --- Platform page ---

PLATFORM_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>UCP Platform Demo</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=Fira+Code:wght@400;500&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #FAFAF9;
    --surface: #FFFFFF;
    --surface-alt: #F5F5F4;
    --fg: #1C1917;
    --muted: #78716C;
    --muted-light: #A8A29E;
    --accent: #0F766E;
    --accent-subtle: #F0FDFA;
    --border: #E7E5E4;
    --code-bg: #1C1917;
    --code-fg: #D6D3D1;
    --green: #059669;
    --green-bg: #ECFDF5;
    --red: #DC2626;
    --red-bg: #FEF2F2;
    --radius: 6px;
  }
  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
      --bg: #141413;
      --surface: #1C1C1A;
      --surface-alt: #232321;
      --fg: #E8E6E3;
      --muted: #9C9891;
      --muted-light: #6B6860;
      --accent: #2DD4BF;
      --accent-subtle: #0F2B27;
      --border: #2E2E2B;
      --code-bg: #0E0E0D;
      --code-fg: #D6D3D1;
      --green: #34D399;
      --green-bg: #0B2618;
      --red: #F87171;
      --red-bg: #2D1111;
    }
  }
  [data-theme="dark"] {
    --bg: #141413;
    --surface: #1C1C1A;
    --surface-alt: #232321;
    --fg: #E8E6E3;
    --muted: #9C9891;
    --muted-light: #6B6860;
    --accent: #2DD4BF;
    --accent-subtle: #0F2B27;
    --border: #2E2E2B;
    --code-bg: #0E0E0D;
    --code-fg: #D6D3D1;
    --green: #34D399;
    --green-bg: #0B2618;
    --red: #F87171;
    --red-bg: #2D1111;
  }

  *, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }
  html { scroll-behavior: smooth; }
  body {
    font-family: 'Manrope', system-ui, sans-serif;
    background: var(--bg);
    color: var(--fg);
    line-height: 1.6;
    min-height: 100vh;
  }

  .container {
    max-width: 760px;
    margin: 0 auto;
    padding: 48px 24px 120px;
  }

  /* Header */
  header {
    margin-bottom: 40px;
  }
  .header-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;
  }
  .version-tag {
    font-family: 'Fira Code', monospace;
    font-size: 0.7rem;
    color: var(--muted);
    background: var(--surface-alt);
    padding: 3px 8px;
    border-radius: var(--radius);
    border: 1px solid var(--border);
  }
  .theme-toggle {
    display: flex;
    gap: 2px;
    background: var(--surface-alt);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 2px;
  }
  .theme-toggle button {
    font-family: inherit;
    font-size: 0.7rem;
    padding: 3px 8px;
    border: none;
    border-radius: 4px;
    background: transparent;
    color: var(--muted);
    cursor: pointer;
    transition: all 0.15s;
  }
  .theme-toggle button.active {
    background: var(--surface);
    color: var(--fg);
    box-shadow: 0 1px 2px rgba(0,0,0,0.06);
  }
  h1 {
    font-size: 1.6rem;
    font-weight: 800;
    letter-spacing: -0.03em;
    line-height: 1.2;
    margin-bottom: 8px;
  }
  .subtitle {
    color: var(--muted);
    font-size: 0.9rem;
    line-height: 1.5;
  }
  .subtitle a {
    color: var(--accent);
    text-decoration: none;
  }

  /* Cards */
  .card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 20px;
    margin-bottom: 16px;
  }
  .card h2 {
    font-size: 0.8rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--muted);
    margin-bottom: 12px;
  }
  .card p {
    font-size: 0.85rem;
    color: var(--fg);
    line-height: 1.6;
  }

  /* Prompt chips */
  .prompt-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 12px;
  }
  .prompt-chip {
    font-family: 'Fira Code', monospace;
    font-size: 0.75rem;
    padding: 6px 12px;
    background: var(--accent-subtle);
    color: var(--accent);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    cursor: default;
    transition: all 0.15s;
    user-select: all;
  }
  .prompt-chip:hover {
    border-color: var(--accent);
  }

  /* Reference grid */
  .ref-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    margin-top: 12px;
  }
  @media (max-width: 520px) {
    .ref-grid { grid-template-columns: 1fr; }
  }
  .ref-item {
    background: var(--surface-alt);
    border-radius: var(--radius);
    padding: 12px;
  }
  .ref-item h3 {
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--muted);
    margin-bottom: 6px;
  }
  .ref-item ul {
    list-style: none;
    font-size: 0.8rem;
  }
  .ref-item li {
    padding: 2px 0;
    font-family: 'Fira Code', monospace;
    font-size: 0.75rem;
    color: var(--fg);
  }
  .ref-item .oos {
    color: var(--red);
  }

  /* Inspector */
  .inspector-row {
    display: flex;
    gap: 8px;
    margin-bottom: 16px;
  }
  .inspector-input {
    flex: 1;
    font-family: 'Fira Code', monospace;
    font-size: 0.8rem;
    padding: 8px 12px;
    background: var(--surface-alt);
    color: var(--fg);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    outline: none;
    transition: border-color 0.15s;
  }
  .inspector-input:focus {
    border-color: var(--accent);
  }
  .inspector-input::placeholder {
    color: var(--muted-light);
  }
  .inspector-btn {
    font-family: inherit;
    font-size: 0.8rem;
    font-weight: 600;
    padding: 8px 16px;
    background: var(--fg);
    color: var(--bg);
    border: none;
    border-radius: var(--radius);
    cursor: pointer;
    transition: opacity 0.15s;
    white-space: nowrap;
  }
  .inspector-btn:hover { opacity: 0.85; }
  .inspector-btn:disabled { opacity: 0.4; cursor: default; }
  .inspector-result {
    display: none;
  }
  .inspector-result.visible {
    display: block;
  }
  .result-badge {
    display: inline-block;
    font-family: 'Fira Code', monospace;
    font-size: 0.7rem;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: var(--radius);
    margin-bottom: 8px;
  }
  .badge-cart { background: var(--accent-subtle); color: var(--accent); }
  .badge-checkout { background: var(--green-bg); color: var(--green); }
  .badge-order { background: #FEF3C7; color: #92400E; }
  .badge-error { background: var(--red-bg); color: var(--red); }
  .result-json {
    background: var(--code-bg);
    color: var(--code-fg);
    font-family: 'Fira Code', monospace;
    font-size: 0.72rem;
    padding: 16px;
    border-radius: var(--radius);
    overflow-x: auto;
    max-height: 400px;
    overflow-y: auto;
    white-space: pre;
    line-height: 1.5;
  }

  /* Request log */
  .log-section {
    margin-top: 16px;
  }
  .log-section h3 {
    font-size: 0.75rem;
    font-weight: 700;
    color: var(--muted);
    margin-bottom: 8px;
  }
  .log-empty {
    font-size: 0.8rem;
    color: var(--muted-light);
    font-style: italic;
  }
  .log-entry {
    display: flex;
    align-items: baseline;
    gap: 8px;
    padding: 6px 0;
    border-bottom: 1px solid var(--border);
    font-size: 0.75rem;
  }
  .log-entry:last-child { border-bottom: none; }
  .log-method {
    font-family: 'Fira Code', monospace;
    font-weight: 600;
    color: var(--accent);
    min-width: 36px;
  }
  .log-url {
    font-family: 'Fira Code', monospace;
    color: var(--fg);
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .log-time {
    font-family: 'Fira Code', monospace;
    color: var(--muted-light);
    font-size: 0.68rem;
    white-space: nowrap;
  }

  /* Flow steps */
  .flow-steps {
    margin-top: 12px;
  }
  .flow-step {
    display: flex;
    gap: 12px;
    padding: 8px 0;
  }
  .step-num {
    font-family: 'Fira Code', monospace;
    font-size: 0.7rem;
    font-weight: 600;
    color: var(--accent);
    min-width: 20px;
    text-align: right;
    padding-top: 1px;
  }
  .step-body {
    flex: 1;
  }
  .step-call {
    font-family: 'Fira Code', monospace;
    font-size: 0.75rem;
    color: var(--fg);
    font-weight: 500;
  }
  .step-desc {
    font-size: 0.78rem;
    color: var(--muted);
    margin-top: 2px;
  }

  /* Back link */
  .back-link {
    display: inline-block;
    font-size: 0.8rem;
    color: var(--muted);
    text-decoration: none;
    margin-bottom: 24px;
    transition: color 0.15s;
  }
  .back-link:hover { color: var(--accent); }

  /* Footer */
  footer {
    margin-top: 48px;
    padding-top: 24px;
    border-top: 1px solid var(--border);
    text-align: center;
  }
  footer p {
    font-size: 0.75rem;
    color: var(--muted-light);
  }
  footer a {
    color: var(--accent);
    text-decoration: none;
  }
</style>
</head>
<body>

<div class="container">

  <a href="/" class="back-link">&larr; Back to API Explorer</a>

  <header>
    <div class="header-row">
      <span class="version-tag">UCP 2026-04-08</span>
      <div class="theme-toggle">
        <button onclick="setTheme('light')">Light</button>
        <button onclick="setTheme('system')" class="active">System</button>
        <button onclick="setTheme('dark')">Dark</button>
      </div>
    </div>
    <h1>Platform Demo</h1>
    <p class="subtitle">
      A real AI agent shopping via <a href="/.well-known/ucp">UCP</a>.
      Open the chat widget to browse products, add to cart, and complete
      a purchase &mdash; every UCP API call is visible as a tool invocation.
    </p>
  </header>

  <!-- How it works -->
  <div class="card">
    <h2>How it works</h2>
    <p>
      The chat widget in the bottom-right is a Runtype Persona powered by an AI agent
      with UCP tools. When you ask it to shop, it makes real HTTP requests to this
      server's UCP endpoints &mdash; the same calls any platform agent would make.
      Tool calls appear inline in the conversation so you can see the protocol in action.
    </p>
    <div class="flow-steps">
      <div class="flow-step">
        <span class="step-num">1</span>
        <div class="step-body">
          <div class="step-call">ucp_discover</div>
          <div class="step-desc">Fetch capabilities &amp; payment handlers</div>
        </div>
      </div>
      <div class="flow-step">
        <span class="step-num">2</span>
        <div class="step-body">
          <div class="step-call">ucp_search_catalog</div>
          <div class="step-desc">Browse products with search &amp; filters</div>
        </div>
      </div>
      <div class="flow-step">
        <span class="step-num">3</span>
        <div class="step-body">
          <div class="step-call">ucp_get_product</div>
          <div class="step-desc">Product detail with option selection</div>
        </div>
      </div>
      <div class="flow-step">
        <span class="step-num">4</span>
        <div class="step-body">
          <div class="step-call">ucp_create_cart &rarr; ucp_create_checkout</div>
          <div class="step-desc">Cart + checkout session with fulfillment</div>
        </div>
      </div>
      <div class="flow-step">
        <span class="step-num">5</span>
        <div class="step-body">
          <div class="step-call">ucp_update_checkout</div>
          <div class="step-desc">Select shipping option, apply discounts</div>
        </div>
      </div>
      <div class="flow-step">
        <span class="step-num">6</span>
        <div class="step-body">
          <div class="step-call">ucp_complete_checkout</div>
          <div class="step-desc">Submit payment &amp; place order</div>
        </div>
      </div>
      <div class="flow-step">
        <span class="step-num">7</span>
        <div class="step-body">
          <div class="step-call">ucp_get_order</div>
          <div class="step-desc">Confirm order &amp; fulfillment details</div>
        </div>
      </div>
    </div>
  </div>

  <!-- Quick prompts -->
  <div class="card">
    <h2>Try saying</h2>
    <div class="prompt-chips">
      <span class="prompt-chip">"What flowers do you have?"</span>
      <span class="prompt-chip">"I'd like a dozen red roses"</span>
      <span class="prompt-chip">"Ship to Portland, OR 97201"</span>
      <span class="prompt-chip">"Apply discount code 10OFF"</span>
      <span class="prompt-chip">"Complete my order"</span>
    </div>
  </div>

  <!-- Session inspector -->
  <div class="card">
    <h2>Session Inspector</h2>
    <p style="margin-bottom: 12px; font-size: 0.82rem;">
      Look up any cart, checkout, or order by ID to see its current state and request log.
    </p>
    <div class="inspector-row">
      <input type="text" class="inspector-input" id="sessionIdInput"
             placeholder="Paste a cart, checkout, or order ID"
             onkeydown="if(event.key==='Enter')lookupSession()">
      <button class="inspector-btn" id="lookupBtn" onclick="lookupSession()">Lookup</button>
    </div>
    <div class="inspector-result" id="inspectorResult">
      <span class="result-badge" id="resultBadge"></span>
      <div class="result-json" id="resultJson"></div>
      <div class="log-section" id="logSection">
        <h3>Request Log</h3>
        <div id="logEntries"></div>
      </div>
    </div>
  </div>

  <!-- Test data reference -->
  <div class="card">
    <h2>Test Data</h2>
    <div class="ref-grid">
      <div class="ref-item">
        <h3>Products</h3>
        <ul>
          <li>bouquet_roses &mdash; $25&ndash;$50</li>
          <li>pot_ceramic &mdash; $10&ndash;$25</li>
          <li>bouquet_sunflowers &mdash; $25</li>
          <li>bouquet_tulips &mdash; $30</li>
          <li>orchid_white &mdash; $45</li>
          <li class="oos">gardenias &mdash; $20 (OOS)</li>
        </ul>
      </div>
      <div class="ref-item">
        <h3>Discount Codes</h3>
        <ul>
          <li>10OFF &mdash; 10% off</li>
          <li>WELCOME20 &mdash; 20% off</li>
          <li>FIXED500 &mdash; $5 off</li>
        </ul>
      </div>
      <div class="ref-item">
        <h3>Fulfillment</h3>
        <ul>
          <li>Shipping: Standard $5, Express $15</li>
          <li>Pickup: Downtown, Midtown, Uptown</li>
        </ul>
      </div>
      <div class="ref-item">
        <h3>Payment</h3>
        <ul>
          <li>google_pay &mdash; succeeds</li>
          <li>shop_pay &mdash; succeeds</li>
          <li>fail_token &mdash; declines</li>
        </ul>
      </div>
    </div>
  </div>

  <footer>
    <p>
      <a href="/.well-known/ucp">Discovery Profile</a> &middot;
      <a href="/">API Explorer</a> &middot;
      UCP Demo Server on Cloudflare Workers
    </p>
  </footer>

</div>

<script>
  // Theme toggle
  function setTheme(t) {
    if (t === 'system') {
      document.documentElement.removeAttribute('data-theme');
      localStorage.removeItem('theme');
    } else {
      document.documentElement.setAttribute('data-theme', t);
      localStorage.setItem('theme', t);
    }
    document.querySelectorAll('.theme-toggle button').forEach(b => {
      b.classList.toggle('active', b.textContent.toLowerCase() === t);
    });
  }
  (function() {
    var saved = localStorage.getItem('theme');
    if (saved) setTheme(saved);
  })();

  // Session inspector
  async function lookupSession() {
    var id = document.getElementById('sessionIdInput').value.trim();
    if (!id) return;
    var btn = document.getElementById('lookupBtn');
    btn.disabled = true;
    btn.textContent = '...';
    try {
      var [sessionRes, logsRes] = await Promise.all([
        fetch('/platform/api/session/' + encodeURIComponent(id)),
        fetch('/platform/api/logs/' + encodeURIComponent(id))
      ]);
      var result = document.getElementById('inspectorResult');
      var badge = document.getElementById('resultBadge');
      var json = document.getElementById('resultJson');
      var logEntries = document.getElementById('logEntries');
      result.classList.add('visible');

      if (!sessionRes.ok) {
        badge.className = 'result-badge badge-error';
        badge.textContent = 'NOT FOUND';
        json.textContent = 'No cart, checkout, or order found with this ID.';
        logEntries.innerHTML = '';
        document.getElementById('logSection').style.display = 'none';
        return;
      }

      var session = await sessionRes.json();
      var logs = await logsRes.json();

      badge.className = 'result-badge badge-' + session.type;
      badge.textContent = session.type.toUpperCase();
      json.textContent = JSON.stringify(session.data, null, 2);

      // Render logs
      var logSection = document.getElementById('logSection');
      if (logs.logs && logs.logs.length > 0) {
        logSection.style.display = 'block';
        logEntries.innerHTML = logs.logs.map(function(l) {
          var ts = l.timestamp ? l.timestamp.split('T')[1].split('.')[0] : '';
          return '<div class="log-entry">' +
            '<span class="log-method">' + l.method + '</span>' +
            '<span class="log-url">' + l.url + '</span>' +
            '<span class="log-time">' + ts + '</span>' +
          '</div>';
        }).join('');
      } else {
        logSection.style.display = session.type === 'checkout' ? 'block' : 'none';
        logEntries.innerHTML = '<div class="log-empty">No request logs for this session.</div>';
      }
    } catch (e) {
      var result = document.getElementById('inspectorResult');
      result.classList.add('visible');
      document.getElementById('resultBadge').className = 'result-badge badge-error';
      document.getElementById('resultBadge').textContent = 'ERROR';
      document.getElementById('resultJson').textContent = e.message;
    } finally {
      btn.disabled = false;
      btn.textContent = 'Lookup';
    }
  }
</script>

<!-- Runtype Persona Chat Widget -->
<script src="https://cdn.jsdelivr.net/npm/@runtypelabs/persona@3.10.0/dist/install.global.js" data-config='{"apiUrl":"https://api.runtype.com","clientToken":"ct_test_01kp2sr6_6eaf2053b7ce962b8cedd04f6f17ffc6","parserType":"json","theme":{"palette":{"colors":{"primary":{"500":"#0F766E","600":"#0D6D64"},"gray":{"50":"#FAFAF9","100":"#F5F5F4","200":"#E7E5E4","500":"#78716C","900":"#1C1917"}},"typography":{"fontFamily":{"sans":"Manrope, system-ui, sans-serif"}},"radius":{"md":"6px","lg":"8px"}}},"launcher":{"enabled":true,"title":"UCP Shopping Agent","subtitle":"Buy flowers with AI over UCP","position":"bottom-right"},"features":{"showToolCalls":true}}'></script>

</body>
</html>"""


@router.get("/platform", response_class=HTMLResponse)
async def platform():
  return PLATFORM_HTML
