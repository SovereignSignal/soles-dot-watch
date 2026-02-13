#!/usr/bin/env python3
"""
Jordan Arbitrage Watcher — CLI entry point.

Find price differences for Air Jordans across sneaker marketplaces.

Usage:
    python main.py search "1 Retro High OG"
    python main.py search "4 Retro Bred" --size 10
    python main.py lookup DZ5485-612 --size 10.5
    python main.py demo
"""

import argparse
import sys
from pathlib import Path

# Add project root to path so imports work
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

load_dotenv()

from src.display import console, show_listings, show_opportunities
from src.watcher import get_available_adapters, scan_for_arbitrage


def cmd_search(args: argparse.Namespace) -> None:
    """Search for a sneaker by name and find arbitrage."""
    console.print(f"\n[bold]Searching for Air Jordan {args.query}...[/bold]\n")

    listings, opps = scan_for_arbitrage(
        query=args.query,
        size=args.size,
        min_profit=args.min_profit,
    )

    show_listings(listings)
    console.print()
    show_opportunities(opps)


def cmd_lookup(args: argparse.Namespace) -> None:
    """Look up a specific sneaker by Nike style code."""
    console.print(f"\n[bold]Looking up style code {args.style_code}...[/bold]\n")

    listings, opps = scan_for_arbitrage(
        query=args.style_code,
        size=args.size,
        style_code=args.style_code,
        min_profit=args.min_profit,
    )

    show_listings(listings)
    console.print()
    show_opportunities(opps)


def cmd_status(args: argparse.Namespace) -> None:
    """Show which marketplace APIs are configured."""
    from src.marketplaces.ebay import EbayAdapter
    from src.marketplaces.goat import GoatAdapter
    from src.marketplaces.kicksdb import KicksDBAdapter
    from src.marketplaces.stockx import StockXAdapter

    adapters = [
        ("KicksDB (kicks.dev)", KicksDBAdapter(), "KICKSDB_API_KEY", "50K free/month"),
        ("StockX via RapidAPI", StockXAdapter(), "RAPIDAPI_KEY", "100 free/month"),
        ("GOAT via Retailed", GoatAdapter(), "RETAILED_API_KEY", "50 free requests"),
        ("eBay Browse API", EbayAdapter(), "EBAY_CLIENT_ID + EBAY_CLIENT_SECRET", "Free sandbox"),
    ]

    console.print("\n[bold]Marketplace API Status[/bold]\n")
    for label, adapter, env_var, tier in adapters:
        status = "[green]CONFIGURED[/green]" if adapter.configured else "[red]NOT SET[/red]"
        console.print(f"  {status}  {label}")
        if not adapter.configured:
            console.print(f"           [dim]Set {env_var} — {tier}[/dim]")
    console.print()

    configured = get_available_adapters()
    if not configured:
        console.print(
            "[yellow]No APIs configured yet. See README.md for setup instructions.[/yellow]\n"
        )
    else:
        console.print(
            f"[green]{len(configured)} source(s) active.[/green] "
            "Run 'python main.py search \"1 Retro\"' to try it.\n"
        )


def cmd_demo(args: argparse.Namespace) -> None:
    """Run with sample data to show what the output looks like."""
    from datetime import datetime
    from src.models.sneaker import ArbitrageOpportunity, Condition, SneakerListing
    from src.arbitrage import find_arbitrage

    console.print("\n[bold]Demo Mode — Sample Arbitrage Data[/bold]\n")
    console.print("[dim]This uses fake data to show you what real output looks like.[/dim]\n")

    sample_listings = [
        SneakerListing(
            marketplace="StockX",
            name='Air Jordan 1 Retro High OG "Chicago Lost & Found"',
            style_code="DZ5485-612",
            size=10.0,
            ask_price=340.00,
            condition=Condition.NEW,
            retail_price=180.00,
        ),
        SneakerListing(
            marketplace="GOAT",
            name='Air Jordan 1 Retro High OG "Chicago Lost & Found"',
            style_code="DZ5485-612",
            size=10.0,
            ask_price=325.00,
            condition=Condition.NEW,
            retail_price=180.00,
        ),
        SneakerListing(
            marketplace="eBay",
            name='Air Jordan 1 Retro High OG "Chicago Lost & Found"',
            style_code="DZ5485-612",
            size=10.0,
            ask_price=299.99,
            condition=Condition.NEW,
            retail_price=180.00,
        ),
        SneakerListing(
            marketplace="Flight Club",
            name='Air Jordan 1 Retro High OG "Chicago Lost & Found"',
            style_code="DZ5485-612",
            size=10.0,
            ask_price=360.00,
            condition=Condition.NEW,
            retail_price=180.00,
        ),
        SneakerListing(
            marketplace="StockX",
            name='Air Jordan 4 Retro "Bred Reimagined"',
            style_code="FV5029-006",
            size=10.0,
            ask_price=275.00,
            condition=Condition.NEW,
            retail_price=210.00,
        ),
        SneakerListing(
            marketplace="GOAT",
            name='Air Jordan 4 Retro "Bred Reimagined"',
            style_code="FV5029-006",
            size=10.0,
            ask_price=258.00,
            condition=Condition.NEW,
            retail_price=210.00,
        ),
        SneakerListing(
            marketplace="eBay",
            name='Air Jordan 4 Retro "Bred Reimagined"',
            style_code="FV5029-006",
            size=10.0,
            ask_price=245.00,
            condition=Condition.NEW,
            retail_price=210.00,
        ),
        SneakerListing(
            marketplace="Kicks Crew",
            name='Air Jordan 4 Retro "Bred Reimagined"',
            style_code="FV5029-006",
            size=10.0,
            ask_price=289.00,
            condition=Condition.NEW,
            retail_price=210.00,
        ),
    ]

    show_listings(sample_listings)
    console.print()

    opps = find_arbitrage(sample_listings, min_gross_spread=5.0)
    show_opportunities(opps)

    console.print(
        "\n[bold blue]To use real data, configure your API keys "
        "(see 'python main.py status').[/bold blue]\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Air Jordan Arbitrage Watcher — find price gaps across sneaker marketplaces.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py demo                              Show sample output
  python main.py status                            Check API configuration
  python main.py search "1 Retro High OG"          Search by name
  python main.py search "4 Retro Bred" --size 10   Filter by size
  python main.py lookup DZ5485-612 --size 10.5      Look up by style code
        """,
    )
    subparsers = parser.add_subparsers(dest="command")

    # search
    p_search = subparsers.add_parser("search", help="Search by sneaker name")
    p_search.add_argument("query", help='Search term (e.g. "1 Retro High OG")')
    p_search.add_argument("--size", type=float, help="Shoe size filter")
    p_search.add_argument("--min-profit", type=float, default=0.0, help="Min net profit ($)")
    p_search.set_defaults(func=cmd_search)

    # lookup
    p_lookup = subparsers.add_parser("lookup", help="Look up by Nike style code")
    p_lookup.add_argument("style_code", help='Style code (e.g. "DZ5485-612")')
    p_lookup.add_argument("--size", type=float, help="Shoe size filter")
    p_lookup.add_argument("--min-profit", type=float, default=0.0, help="Min net profit ($)")
    p_lookup.set_defaults(func=cmd_lookup)

    # status
    p_status = subparsers.add_parser("status", help="Show API configuration status")
    p_status.set_defaults(func=cmd_status)

    # demo
    p_demo = subparsers.add_parser("demo", help="Run with sample data")
    p_demo.set_defaults(func=cmd_demo)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    args.func(args)


if __name__ == "__main__":
    main()
