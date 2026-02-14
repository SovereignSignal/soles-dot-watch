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
        .container {{ max-width: 900px; margin: 0 auto; padding: 2rem; }}
        .logo {{ font-size: 3rem; margin-bottom: 0.25rem; }}
        h1 {{ font-size: 2.5rem; margin-bottom: 0.5rem; color: #fff; }}
        .subtitle {{ color: #888; margin-bottom: 2rem; font-size: 1.1rem; }}
        .status {{ background: #1a1a1a; border-radius: 12px; padding: 1.5rem; margin-bottom: 2rem;
                   border: 1px solid #333; }}
        .status-label {{ color: #888; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.05em; }}
        .status-value {{ font-size: 1.2rem; margin-top: 0.25rem; }}
        .search-box {{ display: flex; gap: 0.75rem; margin-bottom: 2rem; }}
        input, select {{ background: #1a1a1a; border: 1px solid #333; border-radius: 8px;
                        padding: 0.75rem 1rem; color: #fff; font-size: 1rem; }}
        input[type=text] {{ flex: 1; }}
        input[type=number] {{ width: 100px; }}
        button {{ background: #2563eb; color: #fff; border: none; border-radius: 8px;
                 padding: 0.75rem 1.5rem; font-size: 1rem; cursor: pointer; font-weight: 600; }}
        button:hover {{ background: #1d4ed8; }}
        button:disabled {{ background: #333; cursor: wait; }}
        #results {{ min-height: 100px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 1rem; }}
        th {{ text-align: left; padding: 0.75rem; border-bottom: 2px solid #333; color: #888;
             font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.05em; }}
        td {{ padding: 0.75rem; border-bottom: 1px solid #222; }}
        .price {{ font-family: 'SF Mono', 'Fira Code', monospace; }}
        .positive {{ color: #22c55e; }}
        .negative {{ color: #ef4444; }}
        .section-title {{ font-size: 1.3rem; margin: 2rem 0 0.5rem; color: #fff; }}
        .muted {{ color: #666; }}
        .loader {{ display: none; text-align: center; padding: 2rem; color: #888; }}
        .api-hint {{ background: #1a1a0a; border: 1px solid #444; border-radius: 8px;
                     padding: 1rem; margin-top: 1rem; font-size: 0.9rem; color: #aaa; }}
        a {{ color: #60a5fa; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
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
            <input type="text" id="query" placeholder="Search sneakers (e.g. Air Jordan 1 Retro High OG)" />
            <input type="number" id="size" placeholder="Size" step="0.5" min="1" max="20" />
            <button id="searchBtn" onclick="doSearch()">Search</button>
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
        async function doSearch() {{
            const query = document.getElementById('query').value.trim();
            if (!query) return;

            const size = document.getElementById('size').value;
            const btn = document.getElementById('searchBtn');
            const loader = document.getElementById('loader');
            const results = document.getElementById('results');

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
                results.innerHTML = `<p class="negative">Error: ${{err.message}}</p>`;
            }} finally {{
                btn.disabled = false;
                loader.style.display = 'none';
            }}
        }}

        document.getElementById('query').addEventListener('keydown', e => {{
            if (e.key === 'Enter') doSearch();
        }});

        function renderResults(data) {{
            const results = document.getElementById('results');
            let html = '';

            if (data.listings && data.listings.length > 0) {{
                html += `<h2 class="section-title">Listings (${{data.listings.length}})</h2>`;
                html += `<table><tr><th>Marketplace</th><th>Name</th><th>Style</th><th>Size</th><th>Price</th></tr>`;
                for (const l of data.listings) {{
                    html += `<tr><td>${{l.marketplace}}</td><td>${{l.name}}</td><td>${{l.style_code}}</td>`;
                    html += `<td>${{l.size || '?'}}</td><td class="price">$${{l.ask_price.toFixed(2)}}</td></tr>`;
                }}
                html += `</table>`;
            }} else {{
                html += `<p class="muted">No listings found.</p>`;
            }}

            if (data.opportunities && data.opportunities.length > 0) {{
                html += `<h2 class="section-title">Arbitrage Opportunities (${{data.opportunities.length}})</h2>`;
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
                html += `</table>`;
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
