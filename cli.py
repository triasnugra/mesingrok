"""
Command Line Interface for EliZ Analyzer
========================================
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

import click
from rich.console import Console

from .core.analyzer import EliZAnalyzer
from .visualization.charts import plot_analysis

console = Console()


@click.group()
@click.version_option(version="1.0.0")
def main():
    """
    EliZ (@eliz883) Price Action Analysis Engine

    Pure Price Action • Monday Range • Liquidity Sweep • Deviation + Reclaim
    """
    pass


@main.command()
@click.argument("symbol", default="BTC/USDT")
@click.option("--higher-tf", default="1w", help="Higher timeframe for boxes (default 1w)")
@click.option("--entry-tf", default="4h", help="Entry timeframe (default 4h)")
@click.option("--monday-tf", default="1h", help="Timeframe for Monday Range calc")
@click.option("--limit", default=500, help="Number of candles to fetch")
@click.option("--chart", is_flag=True, help="Generate annotated chart")
@click.option("--save-chart", type=click.Path(), help="Path to save chart image")
@click.option("--json-out", type=click.Path(), help="Save full result as JSON")
@click.option("--config", type=click.Path(exists=True), help="Custom config YAML")
def analyze(
    symbol: str,
    higher_tf: str,
    entry_tf: str,
    monday_tf: str,
    limit: int,
    chart: bool,
    save_chart: Optional[str],
    json_out: Optional[str],
    config: Optional[str],
):
    """
    Analyze a single symbol with the full EliZ methodology.
    """
    analyzer = EliZAnalyzer(config_path=config)
    result = analyzer.analyze(
        symbol=symbol,
        higher_tf=higher_tf,
        entry_tf=entry_tf,
        monday_tf=monday_tf,
        limit=limit,
    )

    if chart or save_chart:
        # Re-fetch entry TF data for plotting
        data = analyzer.fetcher.fetch_ohlcv(symbol, timeframe=entry_tf, limit=limit)
        path = save_chart or f"./output/charts/{symbol.replace('/', '_')}_{entry_tf}.png"
        plot_analysis(
            df=data,
            symbol=symbol,
            monday_range=result.monday_range,
            boxes=result.boxes,
            setups=result.setups,
            save_path=path,
        )

    if json_out:
        Path(json_out).parent.mkdir(parents=True, exist_ok=True)
        with open(json_out, "w", encoding="utf-8") as f:
            json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)
        console.print(f"[green]JSON saved → {json_out}[/green]")


@main.command()
@click.option(
    "--symbols",
    "-s",
    multiple=True,
    default=["BTC/USDT", "ETH/USDT", "SOL/USDT"],
    help="Symbols to scan (can be repeated)",
)
@click.option("--higher-tf", default="1w")
@click.option("--entry-tf", default="4h")
@click.option("--config", type=click.Path(exists=True))
def scan(symbols: List[str], higher_tf: str, entry_tf: str, config: Optional[str]):
    """
    Scan multiple symbols and rank potential setups.
    """
    analyzer = EliZAnalyzer(config_path=config)
    results = analyzer.analyze_multiple(
        list(symbols), higher_tf=higher_tf, entry_tf=entry_tf
    )

    # Simple ranking
    console.print("\n[bold magenta]═══ SCAN SUMMARY ═══[/bold magenta]")
    ranked = []
    for r in results:
        best_score = max((s.score for s in r.setups), default=0)
        ranked.append((best_score, r))

    ranked.sort(key=lambda x: x[0], reverse=True)
    for score, r in ranked:
        status = r.recommendation
        console.print(f"  {r.symbol:12} | Best score {score:3} | {status}")


@main.command()
def philosophy():
    """
    Print the core trading philosophy of @eliz883.
    """
    text = """
[bold cyan]Core Philosophy of @eliz883 (EliZ)[/bold cyan]

1. [bold]Strategy gets you in. Discipline makes you money.
   Risk management keeps you in the market.[/bold]

2. Entry is only 1% of the game. The other 99% is:
   - Managing profits
   - Controlling emotions
   - Sticking to the plan

3. Never chase price. The market will always offer another opportunity.

4. Without a clear trigger → do nothing.
   Sitting on hands is also a position.

5. Simplify: Open the weekly chart. Draw three boxes.
   You will understand the market better than 99% of the gurus.

6. The only high-probability triggers:
   - Liquidity Sweep outside the range
   - Deviation (false break)
   - Reclaim + clear reaction

7. Middle of the range = No-Trade Zone.

8. Focus on reaction, not the level itself.
   Level alone is never a signal.

[dim]This tool is a faithful implementation of the public teachings of EliZ.
It is not financial advice. Always do your own research and risk management.[/dim]
"""
    console.print(text)


if __name__ == "__main__":
    main()