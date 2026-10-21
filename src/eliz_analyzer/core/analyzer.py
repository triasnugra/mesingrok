"""
EliZ Analyzer – Main Orchestrator
=================================
Brings together data, Monday Range, Boxes and Pattern detection
into a single professional analysis engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any

import pandas as pd
import yaml
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from ..data.fetcher import DataFetcher
from .monday_range import MondayRangeCalculator, MondayRange
from .levels import BoxDetector, Box
from .patterns import PatternDetector, Setup

console = Console()


@dataclass
class AnalysisResult:
    symbol: str
    timestamp: datetime
    current_price: float
    monday_range: Optional[MondayRange]
    boxes: List[Box]
    setups: List[Setup]
    position_vs_range: str
    position_vs_boxes: str
    recommendation: str
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "current_price": self.current_price,
            "monday_range": self.monday_range.to_dict() if self.monday_range else None,
            "boxes": [b.to_dict() for b in self.boxes],
            "setups": [s.to_dict() for s in self.setups],
            "position_vs_range": self.position_vs_range,
            "position_vs_boxes": self.position_vs_boxes,
            "recommendation": self.recommendation,
            "notes": self.notes,
        }


class EliZAnalyzer:
    """
    High-level analysis engine following @eliz883 public methodology.
    """

    def __init__(self, config_path: Optional[str] = None, config: Optional[dict] = None):
        if config is not None:
            self.cfg = config
        else:
            cfg_file = Path(config_path or "config/default.yaml")
            if not cfg_file.exists():
                # fallback relative to package
                cfg_file = Path(__file__).parent.parent.parent.parent / "config" / "default.yaml"
            with open(cfg_file, "r", encoding="utf-8") as f:
                self.cfg = yaml.safe_load(f)

        self.fetcher = DataFetcher(
            exchange_id=self.cfg.get("exchange", {}).get("name", "binance"),
            rate_limit=self.cfg.get("exchange", {}).get("rate_limit", True),
        )
        self.monday_calc = MondayRangeCalculator()
        self.box_detector = BoxDetector(
            swing_left=self.cfg.get("boxes", {}).get("swing_left", 5),
            swing_right=self.cfg.get("boxes", {}).get("swing_right", 5),
            atr_multiplier=self.cfg.get("boxes", {}).get("atr_multiplier", 0.4),
            max_boxes=self.cfg.get("boxes", {}).get("max_boxes", 3),
            min_touches=self.cfg.get("boxes", {}).get("min_touches", 2),
        )
        self.pattern_detector = PatternDetector(
            min_penetration_pct=self.cfg.get("patterns", {})
            .get("sweep", {})
            .get("min_penetration_pct", 0.05),
            max_bars_after_sweep=self.cfg.get("patterns", {})
            .get("sweep", {})
            .get("max_bars_after", 12),
        )

    def analyze(
        self,
        symbol: str,
        higher_tf: str = "1w",
        entry_tf: str = "4h",
        monday_tf: str = "1h",
        limit: int = 500,
    ) -> AnalysisResult:
        """
        Run a full EliZ-style analysis on one symbol.
        """
        console.print(Panel(f"[bold]Analyzing {symbol}[/bold]", style="cyan"))

        # 1. Fetch data
        tfs = list({higher_tf, entry_tf, monday_tf})
        data = self.fetcher.fetch_multi_timeframe(symbol, tfs, limit=limit)

        df_higher = data[higher_tf]
        df_entry = data[entry_tf]
        df_monday = data[monday_tf]

        current_price = float(df_entry["close"].iloc[-1])

        # 2. Monday Range
        monday_ranges = self.monday_calc.calculate_from_df(
            df_monday, lookback_weeks=self.cfg.get("monday_range", {}).get("lookback_weeks", 4)
        )
        current_mr = monday_ranges[-1] if monday_ranges else None
        self.monday_calc.summarize(monday_ranges)

        # 3. Boxes on higher TF
        boxes = self.box_detector.detect(df_higher)
        self.box_detector.summarize(boxes)

        # 4. Position assessment
        if current_mr:
            if current_mr.is_inside(current_price):
                pos_range = "INSIDE Monday Range (accumulation / manipulation zone)"
            elif current_mr.is_above(current_price):
                pos_range = "ABOVE Monday High"
            else:
                pos_range = "BELOW Monday Low"
        else:
            pos_range = "No Monday Range available"

        pos_boxes = self.box_detector.price_position(current_price, boxes)

        # 5. Pattern scan
        setups = self.pattern_detector.full_scan(
            df_entry, current_mr, boxes, current_price
        )

        # 6. Recommendation logic (strict EliZ style)
        notes: List[str] = []
        recommendation = "NO TRADE – Sitting on hands"

        if pos_boxes == "between_boxes" or "middle" in pos_range.lower():
            notes.append("Price is in the middle of the range / no-trade zone.")
            notes.append("EliZ: 'Sitting on hands is also a position.'")
            recommendation = "NO TRADE – Middle of nowhere"

        high_score_setups = [s for s in setups if s.score >= self.cfg.get("scoring", {}).get("min_score_for_alert", 70)]

        if high_score_setups:
            best = high_score_setups[0]
            recommendation = f"POTENTIAL {best.direction.upper()} – Score {best.score}"
            notes.append(best.reason)
            notes.append(f"Entry zone: {best.entry_zone[0]:.4f} – {best.entry_zone[1]:.4f}")
            notes.append(f"Invalidation: {best.invalidation:.4f}")
            if best.target_hint:
                notes.append(f"First target hint: {best.target_hint:.4f}")
        else:
            if not notes:
                notes.append("No clear Sweep + Deviation + Reclaim trigger detected.")
                notes.append("Wait for price to reach key level and show reaction.")

        # Always remind the core philosophy
        notes.append("Remember: Strategy gets you in. Discipline makes you money. Risk management keeps you in the market.")

        result = AnalysisResult(
            symbol=symbol,
            timestamp=datetime.now(timezone.utc),
            current_price=current_price,
            monday_range=current_mr,
            boxes=boxes,
            setups=setups,
            position_vs_range=pos_range,
            position_vs_boxes=pos_boxes,
            recommendation=recommendation,
            notes=notes,
        )

        self._print_result(result)
        return result

    def _print_result(self, result: AnalysisResult) -> None:
        table = Table(title=f"EliZ Analysis – {result.symbol}", show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("Current Price", f"{result.current_price:.4f}")
        table.add_row("Position vs Monday Range", result.position_vs_range)
        table.add_row("Position vs Boxes", result.position_vs_boxes)
        table.add_row("Recommendation", f"[bold]{result.recommendation}[/bold]")

        console.print(table)

        if result.setups:
            console.print("\n[bold green]Detected Setups[/bold green]")
            for s in result.setups:
                color = "green" if s.direction == "long" else "red"
                console.print(
                    f"  [{color}]{s.direction.upper()}[/{color}] "
                    f"Score {s.score} | {s.reason}"
                )
                console.print(
                    f"      Entry: {s.entry_zone[0]:.4f}-{s.entry_zone[1]:.4f} | "
                    f"SL: {s.invalidation:.4f}"
                )

        console.print("\n[bold]Notes[/bold]")
        for n in result.notes:
            console.print(f"  • {n}")

    def analyze_multiple(self, symbols: List[str], **kwargs) -> List[AnalysisResult]:
        results = []
        for sym in symbols:
            try:
                results.append(self.analyze(sym, **kwargs))
            except Exception as e:
                console.print(f"[red]Failed {sym}: {e}[/red]")
        return results