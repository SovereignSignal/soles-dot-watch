"""
soles.watch — Web server for Railway deployment.

Provides a JSON API and a simple HTML dashboard for sneaker arbitrage.
"""

import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse

from src.arbitrage import DEFAULT_SELLER_FEES
from src.watcher import get_available_adapters, scan_for_arbitrage

app = FastAPI(
    title="soles.watch",
    description="Sneaker arbitrage finder — compare prices across marketplaces",
    version="0.1.0",
)


@app.get("/")
def index() -> HTMLResponse:
    """Serve a simple landing page / dashboard."""
    adapters = get_available_adapters()
    source_count = len(adapters)
    source_names = ", ".join(a.name for a in adapters) if adapters else "None configured"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>soles.watch</title>
    <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>👟</text></svg>">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
               background: #0a0a0a; color: #e0e0e0; min-height: 100vh; }}
        .container {{ max-width: 960px; margin: 0 auto; padding: 2rem; }}
        .logo {{ font-size: 3rem; margin-bottom: 0.25rem; }}
        h1 {{ font-size: 2.5rem; margin-bottom: 0.5rem; color: #fff; }}
        .subtitle {{ color: #888; margin-bottom: 2rem; font-size: 1.1rem; }}
        .status {{ background: #1a1a1a; border-radius: 12px; padding: 1.5rem; margin-bottom: 1.5rem;
                   border: 1px solid #333; }}
        .status-label {{ color: #888; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.05em; }}
        .status-value {{ font-size: 1.2rem; margin-top: 0.25rem; }}

        /* Search box with autocomplete */
        .search-box {{ display: flex; gap: 0.75rem; margin-bottom: 0.5rem; position: relative; }}
        .search-wrap {{ flex: 1; position: relative; }}
        input, select {{ background: #1a1a1a; border: 1px solid #333; border-radius: 8px;
                        padding: 0.75rem 1rem; color: #fff; font-size: 1rem; }}
        input[type=text] {{ width: 100%; }}
        input[type=number] {{ width: 100px; }}
        button {{ background: #2563eb; color: #fff; border: none; border-radius: 8px;
                 padding: 0.75rem 1.5rem; font-size: 1rem; cursor: pointer; font-weight: 600;
                 white-space: nowrap; }}
        button:hover {{ background: #1d4ed8; }}
        button:disabled {{ background: #333; cursor: wait; }}

        /* Autocomplete dropdown */
        .ac-dropdown {{ display: none; position: absolute; top: 100%; left: 0; right: 0;
                       background: #1a1a1a; border: 1px solid #444; border-top: none;
                       border-radius: 0 0 8px 8px; z-index: 100; max-height: 400px;
                       overflow-y: auto; box-shadow: 0 8px 24px rgba(0,0,0,0.5); }}
        .ac-item {{ display: flex; align-items: center; gap: 0.75rem; padding: 0.65rem 1rem;
                   cursor: pointer; border-bottom: 1px solid #222; transition: background 0.1s; }}
        .ac-item:last-child {{ border-bottom: none; }}
        .ac-item:hover, .ac-item.ac-active {{ background: #252525; }}
        .ac-img {{ width: 48px; height: 48px; object-fit: contain; border-radius: 6px;
                  background: #fff; flex-shrink: 0; }}
        .ac-img-placeholder {{ width: 48px; height: 48px; border-radius: 6px; background: #333;
                              display: flex; align-items: center; justify-content: center;
                              font-size: 1.3rem; flex-shrink: 0; }}
        .ac-info {{ flex: 1; min-width: 0; }}
        .ac-name {{ font-size: 0.9rem; color: #fff; white-space: nowrap; overflow: hidden;
                   text-overflow: ellipsis; }}
        .ac-meta {{ font-size: 0.75rem; color: #888; margin-top: 2px; }}

        /* Quick-search pills */
        .quick-section {{ margin-bottom: 2rem; }}
        .quick-label {{ font-size: 0.8rem; color: #666; text-transform: uppercase;
                       letter-spacing: 0.05em; margin-bottom: 0.5rem; }}
        .quick-pills {{ display: flex; flex-wrap: wrap; gap: 0.5rem; }}
        .pill {{ background: #1a1a1a; border: 1px solid #333; border-radius: 20px;
                padding: 0.4rem 0.9rem; font-size: 0.85rem; color: #ccc; cursor: pointer;
                transition: all 0.15s; }}
        .pill:hover {{ background: #2563eb; border-color: #2563eb; color: #fff; }}

        /* Results */
        #results {{ min-height: 100px; }}
        .section-title {{ font-size: 1.3rem; margin: 2rem 0 0.75rem; color: #fff; }}

        /* Listing cards */
        .listing-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
                        gap: 0.75rem; }}
        .listing-card {{ background: #1a1a1a; border: 1px solid #2a2a2a; border-radius: 10px;
                        padding: 0.85rem; display: flex; gap: 0.75rem; align-items: center;
                        transition: border-color 0.15s; }}
        .listing-card:hover {{ border-color: #444; }}
        .listing-img {{ width: 64px; height: 64px; object-fit: contain; border-radius: 8px;
                       background: #fff; flex-shrink: 0; }}
        .listing-img-placeholder {{ width: 64px; height: 64px; border-radius: 8px; background: #252525;
                                   display: flex; align-items: center; justify-content: center;
                                   font-size: 1.6rem; flex-shrink: 0; }}
        .listing-info {{ flex: 1; min-width: 0; }}
        .listing-name {{ font-size: 0.85rem; color: #fff; margin-bottom: 2px;
                        white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
        .listing-detail {{ font-size: 0.75rem; color: #888; }}
        .listing-price {{ font-family: 'SF Mono', 'Fira Code', monospace; font-size: 1.05rem;
                         color: #22c55e; font-weight: 600; white-space: nowrap; }}
        .listing-marketplace {{ display: inline-block; background: #252525; border-radius: 4px;
                               padding: 1px 6px; font-size: 0.7rem; color: #aaa; margin-top: 2px; }}

        /* Opportunity table */
        table {{ width: 100%; border-collapse: collapse; margin-top: 0.75rem; }}
        th {{ text-align: left; padding: 0.75rem; border-bottom: 2px solid #333; color: #888;
             font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.05em; }}
        td {{ padding: 0.75rem; border-bottom: 1px solid #222; font-size: 0.9rem; }}
        .price {{ font-family: 'SF Mono', 'Fira Code', monospace; }}
        .positive {{ color: #22c55e; }}
        .negative {{ color: #ef4444; }}
        .muted {{ color: #666; }}
        .loader {{ display: none; text-align: center; padding: 2rem; color: #888; }}
        .api-hint {{ background: #1a1a0a; border: 1px solid #444; border-radius: 8px;
                     padding: 1rem; margin-top: 1rem; font-size: 0.9rem; color: #aaa; }}
        a {{ color: #60a5fa; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        .error-msg {{ color: #ef4444; background: #1a1010; border: 1px solid #3a1515;
                     border-radius: 8px; padding: 1rem; margin-top: 1rem; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">👟👀</div>
        <h1>soles.watch</h1>
        <p class="subtitle">Find sneaker price gaps across marketplaces</p>

        <div class="status">
            <div class="status-label">Data Sources</div>
            <div class="status-value">{source_count} active &mdash; {source_names}</div>
        </div>

        <div class="search-box">
            <div class="search-wrap">
                <input type="text" id="query" placeholder="Search sneakers by name or style code..."
                       autocomplete="off" />
                <div class="ac-dropdown" id="acDropdown"></div>
            </div>
            <input type="number" id="size" placeholder="Size" step="0.5" min="1" max="20" />
            <button id="searchBtn" onclick="doSearch()">Search</button>
        </div>

        <div class="quick-section" id="quickSection">
            <div class="quick-label">Popular searches</div>
            <div class="quick-pills">
                <span class="pill" onclick="quickSearch('Air Jordan 1 Retro High OG')">Jordan 1 High OG</span>
                <span class="pill" onclick="quickSearch('Air Jordan 4 Retro')">Jordan 4 Retro</span>
                <span class="pill" onclick="quickSearch('Yeezy Boost 350 V2')">Yeezy 350 V2</span>
                <span class="pill" onclick="quickSearch('Nike Dunk Low')">Nike Dunk Low</span>
                <span class="pill" onclick="quickSearch('New Balance 550')">New Balance 550</span>
                <span class="pill" onclick="quickSearch('Air Force 1 Low')">Air Force 1 Low</span>
                <span class="pill" onclick="quickSearch('Nike SB Dunk Low')">SB Dunk Low</span>
                <span class="pill" onclick="quickSearch('Air Jordan 11 Retro')">Jordan 11 Retro</span>
            </div>
        </div>

        <div class="loader" id="loader">Searching marketplaces...</div>
        <div id="results"></div>

        <div class="api-hint" id="apiHint" style="display: {'none' if source_count > 0 else 'block'}">
            No marketplace APIs configured yet. Set environment variables for at least one source:<br>
            <code>KICKSDB_API_KEY</code> &mdash; <a href="https://kicks.dev/">kicks.dev</a> (recommended, 50K free/month)<br>
            <code>RAPIDAPI_KEY</code> &mdash; <a href="https://rapidapi.com/">rapidapi.com</a> (StockX data)<br>
            <code>RETAILED_API_KEY</code> &mdash; <a href="https://retailed.io/">retailed.io</a> (GOAT data)<br>
            <code>EBAY_CLIENT_ID</code> + <code>EBAY_CLIENT_SECRET</code> &mdash;
            <a href="https://developer.ebay.com/">developer.ebay.com</a>
        </div>
    </div>

    <script>
        /* ---- Autocomplete / Typeahead ---- */
        let acTimer = null;
        let acIndex = -1;
        const queryInput = document.getElementById('query');
        const acDropdown = document.getElementById('acDropdown');

        queryInput.addEventListener('input', () => {{
            clearTimeout(acTimer);
            const q = queryInput.value.trim();
            if (q.length < 2) {{ acDropdown.style.display = 'none'; return; }}
            acTimer = setTimeout(() => fetchSuggestions(q), 300);
        }});

        queryInput.addEventListener('keydown', e => {{
            const items = acDropdown.querySelectorAll('.ac-item');
            if (e.key === 'ArrowDown') {{
                e.preventDefault();
                acIndex = Math.min(acIndex + 1, items.length - 1);
                updateAcHighlight(items);
            }} else if (e.key === 'ArrowUp') {{
                e.preventDefault();
                acIndex = Math.max(acIndex - 1, -1);
                updateAcHighlight(items);
            }} else if (e.key === 'Enter') {{
                if (acIndex >= 0 && items[acIndex]) {{
                    items[acIndex].click();
                }} else {{
                    acDropdown.style.display = 'none';
                    doSearch();
                }}
            }} else if (e.key === 'Escape') {{
                acDropdown.style.display = 'none';
                acIndex = -1;
            }}
        }});

        document.addEventListener('click', e => {{
            if (!e.target.closest('.search-wrap')) acDropdown.style.display = 'none';
        }});

        function updateAcHighlight(items) {{
            items.forEach((el, i) => el.classList.toggle('ac-active', i === acIndex));
        }}

        async function fetchSuggestions(q) {{
            try {{
                const resp = await fetch(`/api/suggest?q=${{encodeURIComponent(q)}}`);
                const data = await resp.json();
                if (!data.suggestions || data.suggestions.length === 0) {{
                    acDropdown.style.display = 'none';
                    return;
                }}
                acIndex = -1;
                acDropdown.innerHTML = data.suggestions.map(s => {{
                    const img = s.image_url
                        ? `<img class="ac-img" src="${{s.image_url}}" alt="" onerror="this.outerHTML='<div class=\\'ac-img-placeholder\\'>👟</div>'">`
                        : `<div class="ac-img-placeholder">👟</div>`;
                    const retail = s.retail_price ? `Retail $${{s.retail_price}}` : '';
                    const code = s.style_code ? `${{s.style_code}}` : '';
                    const meta = [code, retail].filter(Boolean).join(' &middot; ');
                    return `<div class="ac-item" data-name="${{s.name}}" data-code="${{s.style_code || ''}}">
                        ${{img}}
                        <div class="ac-info">
                            <div class="ac-name">${{s.name}}</div>
                            <div class="ac-meta">${{meta}}</div>
                        </div>
                    </div>`;
                }}).join('');
                acDropdown.style.display = 'block';

                acDropdown.querySelectorAll('.ac-item').forEach(el => {{
                    el.addEventListener('click', () => {{
                        queryInput.value = el.dataset.code || el.dataset.name;
                        acDropdown.style.display = 'none';
                        doSearch();
                    }});
                }});
            }} catch (_) {{
                acDropdown.style.display = 'none';
            }}
        }}

        /* ---- Quick-search pills ---- */
        function quickSearch(term) {{
            queryInput.value = term;
            acDropdown.style.display = 'none';
            doSearch();
        }}

        /* ---- Main search ---- */
        async function doSearch() {{
            const query = queryInput.value.trim();
            if (!query) return;

            const size = document.getElementById('size').value;
            const btn = document.getElementById('searchBtn');
            const loader = document.getElementById('loader');
            const results = document.getElementById('results');

            document.getElementById('quickSection').style.display = 'none';
            btn.disabled = true;
            loader.style.display = 'block';
            results.innerHTML = '';

            let url = `/api/search?query=${{encodeURIComponent(query)}}`;
            if (size) url += `&size=${{size}}`;

            try {{
                const resp = await fetch(url);
                const data = await resp.json();
                renderResults(data);
            }} catch (err) {{
                results.innerHTML = `<div class="error-msg">Error: ${{err.message}}</div>`;
            }} finally {{
                btn.disabled = false;
                loader.style.display = 'none';
            }}
        }}

        /* ---- Render results ---- */
        function renderResults(data) {{
            const results = document.getElementById('results');
            let html = '';

            if (data.error) {{
                html += `<div class="error-msg">${{data.error}}</div>`;
            }}

            if (data.listings && data.listings.length > 0) {{
                html += `<h2 class="section-title">Listings (${{data.listings.length}})</h2>`;
                html += `<div class="listing-grid">`;
                for (const l of data.listings) {{
                    const img = l.image_url
                        ? `<img class="listing-img" src="${{l.image_url}}" alt="" onerror="this.outerHTML='<div class=\\'listing-img-placeholder\\'>👟</div>'">`
                        : `<div class="listing-img-placeholder">👟</div>`;
                    const sizeStr = l.size ? `Size ${{l.size}}` : '';
                    const code = l.style_code || '';
                    const detail = [code, sizeStr].filter(Boolean).join(' &middot; ');
                    const nameEl = l.url
                        ? `<a href="${{l.url}}" target="_blank" rel="noopener" style="color:#fff;text-decoration:none">${{l.name}}</a>`
                        : l.name;
                    html += `<div class="listing-card">
                        ${{img}}
                        <div class="listing-info">
                            <div class="listing-name" title="${{l.name}}">${{nameEl}}</div>
                            <div class="listing-detail">${{detail}}</div>
                            <div class="listing-marketplace">${{l.marketplace}}</div>
                        </div>
                        <div class="listing-price">$${{l.ask_price.toFixed(2)}}</div>
                    </div>`;
                }}
                html += `</div>`;
            }} else if (!data.error) {{
                html += `<p class="muted" style="margin-top:1rem;">No listings found. Try a different search term or remove the size filter.</p>`;
            }}

            if (data.opportunities && data.opportunities.length > 0) {{
                html += `<h2 class="section-title">Arbitrage Opportunities (${{data.opportunities.length}})</h2>`;
                html += `<div style="overflow-x:auto">`;
                html += `<table><tr><th>Sneaker</th><th>Size</th><th>Buy From</th><th>Buy @</th>`;
                html += `<th>Sell On</th><th>Sell @</th><th>Gross</th><th>Est Net</th></tr>`;
                for (const o of data.opportunities) {{
                    const netClass = o.est_net_profit >= 0 ? 'positive' : 'negative';
                    html += `<tr><td>${{o.name}}</td><td>${{o.size}}</td>`;
                    html += `<td>${{o.buy_marketplace}}</td><td class="price">$${{o.buy_price.toFixed(2)}}</td>`;
                    html += `<td>${{o.sell_marketplace}}</td><td class="price">$${{o.sell_price.toFixed(2)}}</td>`;
                    html += `<td class="price positive">$${{o.gross_spread.toFixed(2)}}</td>`;
                    html += `<td class="price ${{netClass}}">$${{o.est_net_profit.toFixed(2)}}</td></tr>`;
                }}
                html += `</table></div>`;
                html += `<p class="muted" style="margin-top:0.75rem">Net estimates include seller fees but not shipping or taxes.</p>`;
            }} else if (data.listings && data.listings.length > 0) {{
                html += `<p class="muted" style="margin-top:1rem">No arbitrage opportunities found for these listings.</p>`;
            }}

            results.innerHTML = html;
        }}
    </script>
</body>
</html>"""
    return HTMLResponse(content=html)


@app.get("/api/search")
def api_search(
    query: str = Query(..., description="Sneaker search term"),
    size: float | None = Query(None, description="Shoe size filter"),
    style_code: str | None = Query(None, description="Style code for exact match"),
    min_profit: float = Query(0.0, description="Minimum net profit"),
):
    """Search marketplaces and return listings + arbitrage opportunities as JSON."""
    try:
        listings, opps = scan_for_arbitrage(
            query=query,
            size=size,
            style_code=style_code,
            min_profit=min_profit,
        )
    except RuntimeError as e:
        return {"error": str(e), "listings": [], "opportunities": []}

    return {
        "query": query,
        "size": size,
        "listings": [
            {
                "marketplace": l.marketplace,
                "name": l.name,
                "style_code": l.style_code,
                "size": l.size,
                "ask_price": l.ask_price,
                "condition": l.condition.value,
                "url": l.url,
                "image_url": l.image_url,
                "retail_price": l.retail_price,
            }
            for l in sorted(listings, key=lambda x: x.ask_price)
        ],
        "opportunities": [
            {
                "name": o.buy_listing.name,
                "style_code": o.style_code,
                "size": o.size,
                "buy_marketplace": o.buy_marketplace,
                "buy_price": o.buy_listing.ask_price,
                "sell_marketplace": o.sell_marketplace,
                "sell_price": o.sell_listing.ask_price,
                "gross_spread": o.gross_spread,
                "gross_spread_pct": o.gross_spread_pct,
                "est_net_profit": o.net_profit(
                    sell_fee_pct=DEFAULT_SELLER_FEES.get(
                        o.sell_marketplace,
                        DEFAULT_SELLER_FEES.get(o.sell_marketplace.lower(), 10.0),
                    )
                ),
            }
            for o in opps
        ],
    }


@app.get("/api/suggest")
def api_suggest(
    q: str = Query(..., min_length=2, description="Partial search term"),
):
    """Return lightweight product suggestions for typeahead (name, style code, image)."""
    adapters = get_available_adapters()
    if not adapters:
        return {"suggestions": []}

    # Use first adapter for fast suggestions
    adapter = adapters[0]
    try:
        listings = adapter.search(q)
    except Exception:
        return {"suggestions": []}

    # Deduplicate by style_code — we only need product-level info
    seen: dict[str, dict] = {}
    for l in listings:
        key = l.style_code.upper() if l.style_code else l.name
        if key not in seen:
            seen[key] = {
                "name": l.name,
                "style_code": l.style_code,
                "image_url": l.image_url,
                "retail_price": l.retail_price,
            }

    return {"suggestions": list(seen.values())[:10]}


@app.get("/api/status")
def api_status():
    """Return which marketplace APIs are configured."""
    adapters = get_available_adapters()
    return {
        "configured_sources": [a.name for a in adapters],
        "count": len(adapters),
    }


@app.get("/health")
def health():
    """Health check for Railway."""
    return {"status": "ok"}
