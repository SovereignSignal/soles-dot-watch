# Air Jordan Arbitrage Watcher

Find price differences for Air Jordans across sneaker marketplaces. Buy low on one platform, sell high on another.

A learning project for understanding market arbitrage through sneaker reselling.

## How It Works

The watcher pulls pricing data from multiple sneaker marketplaces and compares prices for the same shoe (matched by Nike style code and size). When one marketplace has a significantly lower price than another, that's an arbitrage opportunity.

**Supported data sources:**

| Source | What it covers | Free tier |
|--------|---------------|-----------|
| [KicksDB](https://kicks.dev/) | 40+ shops (StockX, GOAT, Flight Club, etc.) | 50,000 req/month |
| [RapidAPI Sneaker DB](https://rapidapi.com/belchiorarkad-FqvHs2EDOtP/api/sneaker-database-stockx) | StockX pricing | 100 req/month |
| [Retailed.io](https://retailed.io/) | GOAT pricing | 50 free requests |
| [eBay Browse API](https://developer.ebay.com/) | eBay listings | Free sandbox |

You only need **one** API key to get started. KicksDB is recommended since it aggregates the most sources.

## Quick Start

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/jordan-arbitrage.git
cd jordan-arbitrage

# Set up Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure API keys
cp .env.example .env
# Edit .env with your API key(s)

# See sample output (no API key needed)
python main.py demo

# Check which APIs you have configured
python main.py status

# Search for arbitrage
python main.py search "1 Retro High OG"
python main.py search "4 Retro Bred" --size 10
python main.py lookup DZ5485-612 --size 10.5
```

## Understanding the Output

The tool shows two things:

1. **Listings** — All prices found across marketplaces, sorted cheapest first
2. **Arbitrage Opportunities** — Pairs where you could buy on one platform and sell on another

For each opportunity:
- **Gross spread** — Raw price difference (sell price minus buy price)
- **Net profit estimate** — After marketplace seller fees (StockX ~9.5%, eBay ~13.25%, etc.)
- Does NOT include shipping costs or sales tax — factor those in yourself

## Key Concepts

- **Ask price** — The lowest price a seller is currently offering
- **Bid price** — The highest price a buyer is willing to pay
- **Style code** — Nike's unique product ID (e.g., DZ5485-612). This is how we match the same shoe across platforms
- **Seller fees** — Each platform takes a cut when you sell (typically 8-13%)
- **Arbitrage** — Buying where it's cheap and selling where it's expensive. In efficient markets, arbitrage opportunities are small and short-lived

## Project Structure

```
jordan-arbitrage/
├── main.py                        # CLI entry point
├── src/
│   ├── arbitrage.py               # Core arbitrage detection engine
│   ├── watcher.py                 # Coordinates marketplace queries
│   ├── display.py                 # Rich terminal output
│   ├── models/
│   │   └── sneaker.py             # Data models (SneakerListing, ArbitrageOpportunity)
│   └── marketplaces/
│       ├── base.py                # Abstract adapter interface
│       ├── ebay.py                # eBay Browse API adapter
│       ├── stockx.py              # StockX via RapidAPI adapter
│       ├── goat.py                # GOAT via Retailed.io adapter
│       └── kicksdb.py            # KicksDB aggregator adapter
├── tests/
├── requirements.txt
├── .env.example
└── README.md
```

## Adding a New Marketplace

1. Create a new file in `src/marketplaces/`
2. Subclass `MarketplaceAdapter` from `base.py`
3. Implement `search()` and `get_by_style_code()`
4. Add it to the adapter list in `src/watcher.py`

## Ideas for Extension

- **Alerts** — Watch specific shoes and get notified when arbitrage appears
- **Historical tracking** — Log prices over time and chart trends
- **Size analysis** — Which sizes have the biggest spreads?
- **Async fetching** — Query all marketplaces in parallel for speed
- **Web dashboard** — Flask/Streamlit frontend instead of CLI
