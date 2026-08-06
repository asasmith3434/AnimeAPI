"""Command-line interface.

Usage (from market-signals-platform/):
    python -m msp.cli init-db
    python -m msp.cli load-companies
    python -m msp.cli ingest-form4 --days-back 5 [--limit 200]
    python -m msp.cli detect-clusters --window 14
    python -m msp.cli report
"""

from datetime import date, timedelta

import click

from . import db, entities
from .ingest import form4
from .signals import insider_cluster


@click.group()
def cli():
    """Market Signals Platform CLI."""


@cli.command("init-db")
def init_db_cmd():
    db.init_db()
    click.echo("Database initialized.")


@cli.command("load-companies")
def load_companies_cmd():
    db.init_db()
    added = entities.load_companies()
    click.echo(f"Companies loaded ({added} new).")


@cli.command("ingest-form4")
@click.option("--date", "date_str", default=None, help="Single day, YYYY-MM-DD.")
@click.option("--days-back", default=1, show_default=True,
              help="Ingest the last N calendar days ending today (skips weekends/holidays).")
@click.option("--limit", default=None, type=int, help="Max filings per day (for testing).")
def ingest_form4_cmd(date_str, days_back, limit):
    db.init_db()
    if date_str:
        days = [date.fromisoformat(date_str)]
    else:
        today = date.today()
        days = [today - timedelta(days=i) for i in range(days_back)]

    for day in sorted(days):
        stats = form4.ingest_day(day, limit=limit)
        click.echo(f"{day}: {stats}")


@cli.command("detect-clusters")
@click.option("--window", default=14, show_default=True, help="Lookback window in days.")
@click.option("--min-buyers", default=2, show_default=True)
@click.option("--min-value", default=50_000.0, show_default=True,
              help="Minimum combined purchase value in USD.")
def detect_clusters_cmd(window, min_buyers, min_value):
    clusters = insider_cluster.find_cluster_buys(
        as_of=date.today(), window_days=window,
        min_buyers=min_buyers, min_total_value=min_value,
    )
    new = insider_cluster.store_signals(clusters)
    click.echo(f"Found {len(clusters)} cluster buys ({new} new signals stored).")


@cli.command("report")
@click.option("--window", default=14, show_default=True)
@click.option("--min-buyers", default=2, show_default=True)
@click.option("--min-value", default=50_000.0, show_default=True)
def report_cmd(window, min_buyers, min_value):
    """Print current insider cluster buys, strongest first."""
    clusters = insider_cluster.find_cluster_buys(
        as_of=date.today(), window_days=window,
        min_buyers=min_buyers, min_total_value=min_value,
    )
    if not clusters:
        click.echo("No insider cluster buys in the window.")
        return

    click.echo(f"\nInsider cluster buys (last {window} days)\n" + "=" * 60)
    for c in clusters:
        ticker = c.issuer_ticker or "?"
        click.echo(
            f"\n{c.issuer_name} ({ticker})\n"
            f"  {c.n_buyers} distinct buyers, "
            f"{c.total_shares:,.0f} shares, ~${c.total_value:,.0f}\n"
            f"  window: {c.first_buy} -> {c.last_buy}\n"
            f"  buyers: {', '.join(c.buyer_names)}"
        )
    click.echo()


if __name__ == "__main__":
    cli()
