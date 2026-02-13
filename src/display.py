"""Rich terminal output for arbitrage results."""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.arbitrage import DEFAULT_SELLER_FEES
from src.models.sneaker import ArbitrageOpportunity, SneakerListing

console = Console()


def show_listings(listings: list[SneakerListing], title: str = "Listings Found") -> None:
    """Display a table of all collected listings."""
    if not listings:
        console.print("[yellow]No listings found.[/yellow]")
        return

    table = Table(title=title, show_lines=True)
    table.add_column("Marketplace", style="cyan")
    table.add_column("Name", max_width=40)
    table.add_column("Style Code", style="magenta")
    table.add_column("Size", justify="right")
    table.add_column("Ask Price", justify="right", style="green")
    table.add_column("Retail", justify="right", style="dim")

    for l in sorted(listings, key=lambda x: x.ask_price):
        retail = f"${l.retail_price:.0f}" if l.retail_price else "-"
        table.add_row(
            l.marketplace,
            l.name[:40],
            l.style_code,
            f"{l.size}" if l.size else "?",
            f"${l.ask_price:.2f}",
            retail,
        )

    console.print(table)


def show_opportunities(opps: list[ArbitrageOpportunity]) -> None:
    """Display arbitrage opportunities in a rich table."""
    if not opps:
        console.print(
            Panel(
                "[yellow]No arbitrage opportunities found with current criteria.[/yellow]\n"
                "Try broadening your search or lowering the minimum profit threshold.",
                title="No Opportunities",
            )
        )
        return

    table = Table(title="Arbitrage Opportunities", show_lines=True)
    table.add_column("#", justify="right", style="dim")
    table.add_column("Sneaker", max_width=35)
    table.add_column("Size", justify="right")
    table.add_column("Buy From", style="green")
    table.add_column("Buy @", justify="right", style="green")
    table.add_column("Sell On", style="red")
    table.add_column("Sell @", justify="right", style="red")
    table.add_column("Gross $", justify="right", style="yellow bold")
    table.add_column("Gross %", justify="right")
    table.add_column("Est Net $", justify="right", style="bold")

    for i, opp in enumerate(opps, 1):
        sell_fee = DEFAULT_SELLER_FEES.get(
            opp.sell_marketplace,
            DEFAULT_SELLER_FEES.get(opp.sell_marketplace.lower(), 10.0),
        )
        net = opp.net_profit(sell_fee_pct=sell_fee)
        net_style = "green bold" if net > 0 else "red bold"

        table.add_row(
            str(i),
            opp.buy_listing.name[:35],
            f"{opp.size}",
            opp.buy_marketplace,
            f"${opp.buy_listing.ask_price:.2f}",
            opp.sell_marketplace,
            f"${opp.sell_listing.ask_price:.2f}",
            f"${opp.gross_spread:.2f}",
            f"{opp.gross_spread_pct:.1f}%",
            f"[{net_style}]${net:.2f}[/{net_style}]",
        )

    console.print(table)
    console.print(
        f"\n[dim]Found {len(opps)} opportunities. "
        f"Net profit estimates include seller fees but not shipping or taxes.[/dim]"
    )
