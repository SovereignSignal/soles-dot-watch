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

        /* Tab bar */
        .tab-bar {{ display: flex; gap: 0; border-bottom: 2px solid #333; margin-bottom: 1.25rem; }}
        .tab {{ padding: 0.75rem 1.25rem; font-size: 0.95rem; color: #888; cursor: pointer;
               border-bottom: 2px solid transparent; margin-bottom: -2px; transition: all 0.15s;
               display: flex; align-items: center; gap: 0.5rem; user-select: none; }}
        .tab:hover {{ color: #ccc; }}
        .tab.active {{ color: #fff; border-bottom-color: #2563eb; font-weight: 600; }}
        .tab.tab-arb.active {{ border-bottom-color: #22c55e; }}
        .tab-badge {{ background: #22c55e; color: #000; font-size: 0.7rem; font-weight: 700;
                     padding: 0.15rem 0.45rem; border-radius: 10px; }}
        .tab-badge-muted {{ background: #333; color: #aaa; font-size: 0.7rem; font-weight: 600;
                           padding: 0.15rem 0.45rem; border-radius: 10px; }}
        .tab-panel {{ display: none; }}
        .tab-panel.active {{ display: block; }}
        .no-opps-msg {{ background: #1a1a1a; border: 1px solid #333; border-radius: 12px;
                       padding: 2rem; text-align: center; color: #888; }}
        .no-opps-msg-title {{ font-size: 1.1rem; color: #aaa; margin-bottom: 0.5rem; }}

        /* Profit summary banner */
        .profit-banner {{ background: linear-gradient(135deg, #052e16, #0a3a1a); border: 1px solid #166534;
                         border-radius: 12px; padding: 1.25rem 1.5rem; margin-bottom: 1.5rem; }}
        .profit-banner-title {{ font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.05em;
                               color: #4ade80; margin-bottom: 0.5rem; }}
        .profit-stats {{ display: flex; gap: 2rem; flex-wrap: wrap; }}
        .profit-stat {{ text-align: center; }}
        .profit-stat-value {{ font-size: 1.6rem; font-weight: 700; color: #22c55e;
                             font-family: 'SF Mono', 'Fira Code', monospace; }}
        .profit-stat-label {{ font-size: 0.75rem; color: #86efac; margin-top: 2px; }}

        /* Arbitrage opportunity cards */
        .opp-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
                    gap: 0.85rem; margin-bottom: 1rem; }}
        .opp-card {{ background: #111; border: 1px solid #1e3a1e; border-radius: 12px;
                    padding: 1rem 1.15rem; transition: border-color 0.15s, transform 0.15s; }}
        .opp-card:hover {{ border-color: #22c55e; transform: translateY(-1px); }}
        .opp-card-header {{ display: flex; gap: 0.75rem; align-items: center; margin-bottom: 0.75rem; }}
        .opp-card-img {{ width: 56px; height: 56px; object-fit: contain; border-radius: 8px;
                        background: #fff; flex-shrink: 0; }}
        .opp-card-img-ph {{ width: 56px; height: 56px; border-radius: 8px; background: #252525;
                           display: flex; align-items: center; justify-content: center;
                           font-size: 1.4rem; flex-shrink: 0; }}
        .opp-card-title {{ flex: 1; min-width: 0; }}
        .opp-card-name {{ font-size: 0.9rem; color: #fff; font-weight: 600;
                         white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
        .opp-card-sku {{ font-size: 0.75rem; color: #888; margin-top: 2px; }}
        .opp-card-profit {{ text-align: right; }}
        .opp-card-profit-val {{ font-size: 1.3rem; font-weight: 700; color: #22c55e;
                               font-family: 'SF Mono', 'Fira Code', monospace; }}
        .opp-card-profit-label {{ font-size: 0.65rem; color: #86efac; }}

        .opp-flow {{ display: flex; align-items: stretch; gap: 0; margin-bottom: 0.6rem;
                    border-radius: 8px; overflow: hidden; }}
        .opp-flow-buy {{ flex: 1; background: #0c1f1c; padding: 0.6rem 0.75rem; }}
        .opp-flow-arrow {{ display: flex; align-items: center; justify-content: center;
                          background: #1a2e1a; padding: 0 0.5rem; color: #22c55e; font-size: 1.1rem; }}
        .opp-flow-sell {{ flex: 1; background: #0c1f1c; padding: 0.6rem 0.75rem; text-align: right; }}
        .opp-flow-label {{ font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.04em;
                          color: #888; margin-bottom: 2px; }}
        .opp-flow-mkt {{ font-size: 0.8rem; color: #ccc; }}
        .opp-flow-price {{ font-size: 1rem; font-weight: 600;
                          font-family: 'SF Mono', 'Fira Code', monospace; }}
        .opp-flow-buy .opp-flow-price {{ color: #60a5fa; }}
        .opp-flow-sell .opp-flow-price {{ color: #22c55e; }}
        .opp-flow-link {{ font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.04em;
                         color: #60a5fa; text-decoration: none; display: block; margin-bottom: 2px; }}
        .opp-flow-link:hover {{ text-decoration: underline; color: #93bbfc; }}
        .opp-flow-mkt-link {{ font-size: 0.8rem; color: #ccc; text-decoration: none; font-weight: 500; }}
        .opp-flow-mkt-link:hover {{ color: #fff; text-decoration: underline; }}
        .opp-card-meta {{ display: flex; justify-content: space-between; font-size: 0.75rem; color: #888; }}

        /* Sneaker group cards (listings) */
        .listings-toggle {{ background: #1a1a1a; border: 1px solid #333; border-radius: 8px;
                           padding: 0.75rem 1rem; color: #aaa; cursor: pointer; text-align: center;
                           margin-top: 1rem; font-size: 0.9rem; transition: all 0.15s; }}
        .listings-toggle:hover {{ border-color: #555; color: #fff; }}
        .sneaker-group {{ background: #111; border: 1px solid #2a2a2a; border-radius: 12px;
                         padding: 1.25rem; margin-bottom: 1rem; }}
        .group-header {{ display: flex; gap: 1rem; align-items: center; margin-bottom: 0.75rem; }}
        .group-img {{ width: 80px; height: 80px; object-fit: contain; border-radius: 10px;
                     background: #fff; flex-shrink: 0; }}
        .group-img-placeholder {{ width: 80px; height: 80px; border-radius: 10px; background: #252525;
                                 display: flex; align-items: center; justify-content: center;
                                 font-size: 2rem; flex-shrink: 0; }}
        .group-info {{ flex: 1; min-width: 0; }}
        .group-name {{ font-size: 1.1rem; color: #fff; font-weight: 600; }}
        .group-meta {{ font-size: 0.8rem; color: #888; margin-top: 2px; }}

        /* Size pills */
        .size-label {{ font-size: 0.75rem; color: #888; text-transform: uppercase;
                      letter-spacing: 0.05em; margin-bottom: 0.4rem; }}
        .size-pills {{ display: flex; flex-wrap: wrap; gap: 0.4rem; margin-bottom: 0.75rem; }}
        .size-pill {{ background: #1a1a1a; border: 1px solid #333; border-radius: 8px;
                     padding: 0.35rem 0.6rem; font-size: 0.8rem; color: #ccc; cursor: pointer;
                     text-align: center; transition: all 0.15s; display: flex; flex-direction: column;
                     align-items: center; min-width: 52px; }}
        .size-pill:hover {{ background: #2563eb; border-color: #2563eb; color: #fff; }}
        .size-price {{ font-size: 0.65rem; color: #888; margin-top: 1px; }}
        .size-pill:hover .size-price {{ color: rgba(255,255,255,0.7); }}

        /* Individual listing rows within a group */
        .listing-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
                        gap: 0.5rem; }}
        .listing-card {{ background: #1a1a1a; border: 1px solid #2a2a2a; border-radius: 8px;
                        padding: 0.65rem 0.85rem; display: flex; gap: 0.5rem; align-items: center;
                        transition: border-color 0.15s; }}
        .listing-card:hover {{ border-color: #444; }}
        .listing-info {{ flex: 1; min-width: 0; }}
        .listing-name {{ font-size: 0.85rem; color: #fff; margin-bottom: 2px;
                        white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
        .listing-detail {{ font-size: 0.75rem; color: #888; }}
        .listing-price {{ font-family: 'SF Mono', 'Fira Code', monospace; font-size: 1rem;
                         color: #22c55e; font-weight: 600; white-space: nowrap; }}

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
                <input type="text" id="query" placeholder="Search any sneaker by name, style code, or brand..."
                       autocomplete="off" />
                <div class="ac-dropdown" id="acDropdown"></div>
            </div>
            <button id="searchBtn" onclick="doSearch()">Find Deals</button>
        </div>

        <div class="quick-section" id="quickSection">
            <div class="quick-label">Quick searches &mdash; or type anything above</div>
            <div class="quick-pills">
                <span class="pill" onclick="quickSearch('Air Jordan 1 Retro High OG')">Jordan 1 High OG</span>
                <span class="pill" onclick="quickSearch('Air Jordan 4 Retro')">Jordan 4 Retro</span>
                <span class="pill" onclick="quickSearch('Air Jordan 11 Retro')">Jordan 11 Retro</span>
                <span class="pill" onclick="quickSearch('Air Jordan 3 Retro')">Jordan 3 Retro</span>
                <span class="pill" onclick="quickSearch('Nike Dunk Low')">Nike Dunk Low</span>
                <span class="pill" onclick="quickSearch('Nike SB Dunk Low')">SB Dunk Low</span>
                <span class="pill" onclick="quickSearch('Air Force 1 Low')">Air Force 1 Low</span>
                <span class="pill" onclick="quickSearch('Nike Air Max 1')">Air Max 1</span>
                <span class="pill" onclick="quickSearch('Nike Air Max 90')">Air Max 90</span>
                <span class="pill" onclick="quickSearch('Yeezy Boost 350 V2')">Yeezy 350 V2</span>
                <span class="pill" onclick="quickSearch('Yeezy Slide')">Yeezy Slide</span>
                <span class="pill" onclick="quickSearch('New Balance 550')">New Balance 550</span>
                <span class="pill" onclick="quickSearch('New Balance 2002R')">New Balance 2002R</span>
                <span class="pill" onclick="quickSearch('Adidas Samba OG')">Adidas Samba</span>
                <span class="pill" onclick="quickSearch('Adidas Gazelle')">Adidas Gazelle</span>
                <span class="pill" onclick="quickSearch('ASICS Gel-Kayano 14')">ASICS Kayano 14</span>
                <span class="pill" onclick="quickSearch('Salomon XT-6')">Salomon XT-6</span>
                <span class="pill" onclick="quickSearch('Travis Scott')">Travis Scott</span>
                <span class="pill" onclick="quickSearch('Off-White Nike')">Off-White x Nike</span>
                <span class="pill" onclick="quickSearch('A Bathing Ape Bapesta')">BAPE Bapesta</span>
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

            const btn = document.getElementById('searchBtn');
            const loader = document.getElementById('loader');
            const results = document.getElementById('results');

            btn.disabled = true;
            loader.style.display = 'block';
            results.innerHTML = '';

            let url = `/api/search?query=${{encodeURIComponent(query)}}`;

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

        /* ---- Tab switching ---- */
        function switchTab(tabId) {{
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
            document.querySelector(`[data-tab="${{tabId}}"]`).classList.add('active');
            document.getElementById(tabId).classList.add('active');
        }}

        /* ---- Render results ---- */
        function renderResults(data) {{
            const results = document.getElementById('results');
            let html = '';

            if (data.error) {{
                html += `<div class="error-msg">${{data.error}}</div>`;
            }}

            const opps = data.opportunities || [];
            const listings = data.listings || [];

            if (listings.length === 0 && opps.length === 0 && !data.error) {{
                html += `<p class="muted" style="margin-top:1rem;">No listings found. Try a different search term.</p>`;
                results.innerHTML = html;
                return;
            }}

            /* ========== TAB BAR ========== */
            const defaultTab = opps.length > 0 ? 'panelArb' : 'panelListings';
            const arbBadge = opps.length > 0
                ? `<span class="tab-badge">${{opps.length}}</span>`
                : `<span class="tab-badge-muted">0</span>`;

            /* Group listings for count */
            const norm = s => (s || '').replace(/[^a-zA-Z0-9]/g, '').toUpperCase();
            const groups = {{}};
            for (const l of listings) {{
                const key = norm(l.style_code) || l.name.toUpperCase();
                if (!groups[key]) groups[key] = {{ name: l.name, style_code: l.style_code, image_url: l.image_url, listings: [] }};
                groups[key].listings.push(l);
                if (l.image_url && !groups[key].image_url) groups[key].image_url = l.image_url;
            }}
            const groupList = Object.values(groups);

            html += `<div class="tab-bar">`;
            html += `<div class="tab tab-arb ${{defaultTab === 'panelArb' ? 'active' : ''}}" data-tab="panelArb" onclick="switchTab('panelArb')">Arbitrage Deals ${{arbBadge}}</div>`;
            html += `<div class="tab ${{defaultTab === 'panelListings' ? 'active' : ''}}" data-tab="panelListings" onclick="switchTab('panelListings')">All Listings <span class="tab-badge-muted">${{listings.length}}</span></div>`;
            html += `</div>`;

            /* ========== ARBITRAGE PANEL ========== */
            html += `<div id="panelArb" class="tab-panel ${{defaultTab === 'panelArb' ? 'active' : ''}}">`;

            if (opps.length > 0) {{
                /* Build image lookup from listings */
                const imgLookup = {{}};
                for (const l of listings) {{
                    const k = norm(l.style_code);
                    if (l.image_url && !imgLookup[k]) imgLookup[k] = l.image_url;
                }}

                /* Profit summary banner */
                const bestNet = Math.max(...opps.map(o => o.est_net_profit));
                const avgNet = opps.reduce((s, o) => s + o.est_net_profit, 0) / opps.length;
                const totalNet = opps.reduce((s, o) => s + o.est_net_profit, 0);

                html += `<div class="profit-banner">`;
                html += `<div class="profit-banner-title">Potential Arbitrage Opportunities</div>`;
                html += `<div class="profit-stats">`;
                html += `<div class="profit-stat"><div class="profit-stat-value">${{opps.length}}</div><div class="profit-stat-label">Opportunities</div></div>`;
                html += `<div class="profit-stat"><div class="profit-stat-value">$${{bestNet.toFixed(0)}}</div><div class="profit-stat-label">Best Net Profit</div></div>`;
                html += `<div class="profit-stat"><div class="profit-stat-value">$${{avgNet.toFixed(0)}}</div><div class="profit-stat-label">Avg Net Profit</div></div>`;
                html += `<div class="profit-stat"><div class="profit-stat-value">$${{totalNet.toFixed(0)}}</div><div class="profit-stat-label">Total If All Flipped</div></div>`;
                html += `</div></div>`;

                /* Opportunity cards */
                html += `<div class="opp-grid">`;
                for (const o of opps) {{
                    const normSku = norm(o.style_code);
                    const imgUrl = o.buy_image_url || imgLookup[normSku];
                    const img = imgUrl
                        ? `<img class="opp-card-img" src="${{imgUrl}}" alt="" onerror="this.outerHTML='<div class=\\'opp-card-img-ph\\'>👟</div>'">`
                        : `<div class="opp-card-img-ph">👟</div>`;
                    const profitPct = o.buy_price > 0 ? ((o.est_net_profit / o.buy_price) * 100).toFixed(0) : '?';

                    html += `<div class="opp-card">`;
                    html += `<div class="opp-card-header">`;
                    html += img;
                    html += `<div class="opp-card-title">`;
                    html += `<div class="opp-card-name" title="${{o.name}}">${{o.name}}</div>`;
                    html += `<div class="opp-card-sku">${{o.style_code || ''}} &middot; Size ${{o.size}}</div>`;
                    html += `</div>`;
                    html += `<div class="opp-card-profit">`;
                    html += `<div class="opp-card-profit-val">+$${{o.est_net_profit.toFixed(0)}}</div>`;
                    html += `<div class="opp-card-profit-label">${{profitPct}}% ROI</div>`;
                    html += `</div></div>`;

                    const buyLink = o.buy_url
                        ? `<a href="${{o.buy_url}}" target="_blank" rel="noopener" class="opp-flow-link">Verify &amp; Buy on</a>`
                        : `<div class="opp-flow-label">Buy on</div>`;
                    const sellLink = o.sell_url
                        ? `<a href="${{o.sell_url}}" target="_blank" rel="noopener" class="opp-flow-link">Verify &amp; Sell on</a>`
                        : `<div class="opp-flow-label">Sell on</div>`;
                    const buyMkt = o.buy_url
                        ? `<a href="${{o.buy_url}}" target="_blank" rel="noopener" class="opp-flow-mkt-link">${{o.buy_marketplace}}</a>`
                        : `<div class="opp-flow-mkt">${{o.buy_marketplace}}</div>`;
                    const sellMkt = o.sell_url
                        ? `<a href="${{o.sell_url}}" target="_blank" rel="noopener" class="opp-flow-mkt-link">${{o.sell_marketplace}}</a>`
                        : `<div class="opp-flow-mkt">${{o.sell_marketplace}}</div>`;

                    html += `<div class="opp-flow">`;
                    html += `<div class="opp-flow-buy">${{buyLink}}${{buyMkt}}`;
                    html += `<div class="opp-flow-price">$${{o.buy_price.toFixed(0)}}</div></div>`;
                    html += `<div class="opp-flow-arrow">&rarr;</div>`;
                    html += `<div class="opp-flow-sell">${{sellLink}}${{sellMkt}}`;
                    html += `<div class="opp-flow-price">$${{o.sell_price.toFixed(0)}}</div></div>`;
                    html += `</div>`;

                    html += `<div class="opp-card-meta">`;
                    html += `<span>Gross: $${{o.gross_spread.toFixed(0)}} (${{o.gross_spread_pct.toFixed(0)}}%)</span>`;
                    html += `<span>Net after ~9.5% fees: $${{o.est_net_profit.toFixed(0)}}</span>`;
                    html += `</div>`;
                    html += `</div>`;
                }}
                html += `</div>`;
                html += `<p class="muted" style="margin-top:0.75rem">&#9888;&#65039; Prices are estimates from a third-party aggregator and may be delayed. Always click through to verify current prices on each marketplace before buying or selling. Net estimates include seller fees (~9.5%) but not shipping or taxes.</p>`;
            }} else {{
                html += `<div class="no-opps-msg">`;
                html += `<div class="no-opps-msg-title">No arbitrage opportunities found</div>`;
                html += `<p>The same shoe needs to be available on both StockX and GOAT with a price difference to create an opportunity. Try searching for popular models like "Nike Dunk Low" or "Jordan 1 Retro".</p>`;
                html += `</div>`;
            }}
            html += `</div>`;

            /* ========== LISTINGS PANEL ========== */
            html += `<div id="panelListings" class="tab-panel ${{defaultTab === 'panelListings' ? 'active' : ''}}">`;

            if (listings.length > 0) {{
                html += `<h2 class="section-title" style="margin-top:0">${{groupList.length}} Sneaker${{groupList.length !== 1 ? 's' : ''}} Found (${{listings.length}} listings)</h2>`;

                for (const g of groupList) {{
                    const img = g.image_url
                        ? `<img class="group-img" src="${{g.image_url}}" alt="" onerror="this.outerHTML='<div class=\\'group-img-placeholder\\'>👟</div>'">`
                        : `<div class="group-img-placeholder">👟</div>`;

                    const sizeMap = {{}};
                    for (const l of g.listings) {{
                        if (l.size && l.size > 0) {{
                            if (!sizeMap[l.size]) sizeMap[l.size] = [];
                            sizeMap[l.size].push(l);
                        }}
                    }}
                    const sizes = Object.keys(sizeMap).map(Number).sort((a, b) => a - b);
                    const marketplaces = [...new Set(g.listings.map(l => l.marketplace))];
                    const priceRange = g.listings.length > 0
                        ? `$${{Math.min(...g.listings.map(l => l.ask_price)).toFixed(0)}}` +
                          (Math.min(...g.listings.map(l => l.ask_price)) !== Math.max(...g.listings.map(l => l.ask_price))
                            ? ` &ndash; $${{Math.max(...g.listings.map(l => l.ask_price)).toFixed(0)}}` : '')
                        : '';

                    html += `<div class="sneaker-group">`;
                    html += `<div class="group-header">${{img}}<div class="group-info">`;
                    html += `<div class="group-name">${{g.name}}</div>`;
                    html += `<div class="group-meta">${{g.style_code || ''}}${{g.style_code && priceRange ? ' &middot; ' : ''}}${{priceRange}}</div>`;
                    html += `<div class="group-meta">${{marketplaces.join(', ')}}</div>`;
                    html += `</div></div>`;

                    if (sizes.length > 0) {{
                        html += `<div class="size-label">Available sizes</div>`;
                        html += `<div class="size-pills">`;
                        for (const sz of sizes) {{
                            const lowest = Math.min(...sizeMap[sz].map(l => l.ask_price));
                            html += `<span class="size-pill">`;
                            html += `${{sz}}<span class="size-price">$${{lowest.toFixed(0)}}</span></span>`;
                        }}
                        html += `</div>`;
                    }}

                    html += `<div class="listing-grid">`;
                    for (const l of g.listings.sort((a, b) => a.ask_price - b.ask_price)) {{
                        const sizeStr = l.size ? `Size ${{l.size}}` : '';
                        const nameEl = l.url
                            ? `<a href="${{l.url}}" target="_blank" rel="noopener" style="color:#fff;text-decoration:none">${{l.marketplace}}</a>`
                            : l.marketplace;
                        html += `<div class="listing-card"><div class="listing-info">`;
                        html += `<div class="listing-name">${{nameEl}}</div>`;
                        html += `<div class="listing-detail">${{sizeStr}}</div>`;
                        html += `</div><div class="listing-price">$${{l.ask_price.toFixed(2)}}</div></div>`;
                    }}
                    html += `</div></div>`;
                }}
            }} else {{
                html += `<p class="muted">No listings found.</p>`;
            }}
            html += `</div>`;

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
                "buy_url": o.buy_listing.url,
                "buy_image_url": o.buy_listing.image_url,
                "sell_marketplace": o.sell_marketplace,
                "sell_price": o.sell_listing.ask_price,
                "sell_url": o.sell_listing.url,
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
