"""
Monday Range Calculator
=======================
EliZ's core weekly framework.

"The Monday Range defines Monday's high and low: this is where liquidity is
concentrated and the week's movement is prepared. As long as the price remains
within this range, the market accumulates and manipulates..."
— @eliz883
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any

import pandas as pd
from rich.console import Console

console = Console()


@dataclass
class MondayRange:
    """Single Monday Range object."""

    week_start: datetime          # Monday 00:00 UTC
    high: float
    low: float
    high_time: Optional[datetime] = None
    low_time: Optional[datetime] = None
    closed: bool = False          # True if the Monday candle/period is finished

    @property
    def mid(self) -> float:
        return (self.high + self.low) / 2.0

    @property
    def range_size(self) -> float:
        return self.high - self.low

    @property
    def range_pct(self) -> float:
        return (self.range_size / self.low) * 100 if self.low > 0 else 0.0

    def is_inside(self, price: float) -> bool:
        return self.low <= price <= self.high

    def is_above(self, price: float) -> bool:
        return price > self.high

    def is_below(self, price: float) -> bool:
        return price < self.low

    def distance_to_high(self, price: float) -> float:
        return price - self.high

    def distance_to_low(self, price: float) -> float:
        return self.low - price

    def to_dict(self) -> Dict[str, Any]:
        return {
            "week_start": self.week_start.isoformat(),
            "high": self.high,
            "low": self.low,
            "mid": self.mid,
            "range_size": self.range_size,
            "range_pct": round(self.range_pct, 3),
            "closed": self.closed,
            "high_time": self.high_time.isoformat() if self.high_time else None,
            "low_time": self.low_time.isoformat() if self.low_time else None,
        }


class MondayRangeCalculator:
    """
    Calculates Monday Ranges from OHLCV data.

    Methodology (aligned with EliZ public statements):
    - Take the highest High and lowest Low of the Monday period
      (00:00 UTC Monday → 00:00 UTC Tuesday).
    - This becomes the reference framework for the entire week.
    - Inside the range → accumulation / manipulation (prefer no trade).
    - Outside + deviation + reclaim → high-probability setups.
    """

    def __init__(self, timezone_str: str = "UTC"):
        self.tz = timezone.utc

    def _get_monday(self, ts: pd.Timestamp) -> datetime:
        """Return Monday 00:00 of the week of the given timestamp."""
        if ts.tzinfo is None:
            ts = ts.tz_localize("UTC")
        else:
            ts = ts.tz_convert("UTC")
        days_since_monday = ts.weekday()
        monday = (ts - pd.Timedelta(days=days_since_monday)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        return monday.to_pydatetime()

    def calculate_from_df(
        self,
        df: pd.DataFrame,
        lookback_weeks: int = 8,
    ) -> List[MondayRange]:
        """
        Compute Monday Ranges from an intraday (preferably 1h or 15m) DataFrame.

        Parameters
        ----------
        df : pd.DataFrame
            Must have columns: open, high, low, close and DatetimeIndex in UTC.
        lookback_weeks : int
            How many past complete Monday Ranges to return.

        Returns
        -------
        List[MondayRange] sorted from oldest to newest.
        """
        if df.empty:
            return []

        df = df.copy()
        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC")
        else:
            df.index = df.index.tz_convert("UTC")

        # Add week identifier (Monday date)
        df["monday"] = df.index.map(self._get_monday)

        ranges: List[MondayRange] = []
        grouped = df.groupby("monday")

        for monday_dt, group in grouped:
            # Only consider bars that actually belong to Monday
            # (weekday == 0)
            monday_bars = group[group.index.weekday == 0]
            if monday_bars.empty:
                continue

            high = float(monday_bars["high"].max())
            low = float(monday_bars["low"].min())
            high_time = monday_bars["high"].idxmax().to_pydatetime()
            low_time = monday_bars["low"].idxmin().to_pydatetime()

            # A Monday Range is "closed" once Tuesday has started
            now = datetime.now(timezone.utc)
            closed = now > (monday_dt + timedelta(days=1))

            mr = MondayRange(
                week_start=monday_dt,
                high=high,
                low=low,
                high_time=high_time,
                low_time=low_time,
                closed=closed,
            )
            ranges.append(mr)

        # Keep only the most recent N weeks
        ranges = sorted(ranges, key=lambda r: r.week_start)[-lookback_weeks:]
        return ranges

    def get_current_range(self, df: pd.DataFrame) -> Optional[MondayRange]:
        """Return the most recent (current or last completed) Monday Range."""
        ranges = self.calculate_from_df(df, lookback_weeks=2)
        if not ranges:
            return None
        return ranges[-1]

    def get_previous_range(self, df: pd.DataFrame) -> Optional[MondayRange]:
        ranges = self.calculate_from_df(df, lookback_weeks=3)
        if len(ranges) < 2:
            return None
        return ranges[-2]

    def summarize(self, ranges: List[MondayRange]) -> None:
        """Pretty print ranges for CLI."""
        console.print("\n[bold cyan]Monday Ranges[/bold cyan]")
        for r in ranges:
            status = "[green]CLOSED[/green]" if r.closed else "[yellow]ACTIVE[/yellow]"
            console.print(
                f"  Week {r.week_start.date()} | "
                f"High: {r.high:.4f} | Low: {r.low:.4f} | "
                f"Size: {r.range_pct:.2f}% | {status}"
            )