"""
Box / Zone Detector
===================
Implements EliZ's "draw three boxes on the Weekly chart" philosophy.

"Open the $BTC chart. Set the timeframe to weekly. Draw three boxes.
You’ll already understand the market better than 99 per cent of the ‘gurus’."
— @eliz883

We detect swing highs/lows and expand them into zones using ATR.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple

import numpy as np
import pandas as pd
from rich.console import Console

console = Console()


@dataclass
class Box:
    """A supply or demand zone."""

    top: float
    bottom: float
    kind: str                     # "supply" | "demand" | "mid"
    strength: int = 1             # number of touches / respect
    start_time: Optional[pd.Timestamp] = None
    end_time: Optional[pd.Timestamp] = None
    label: str = ""

    @property
    def mid(self) -> float:
        return (self.top + self.bottom) / 2.0

    @property
    def height(self) -> float:
        return self.top - self.bottom

    def contains(self, price: float) -> bool:
        return self.bottom <= price <= self.top

    def is_above(self, price: float) -> bool:
        return price > self.top

    def is_below(self, price: float) -> bool:
        return price < self.bottom

    def to_dict(self) -> Dict[str, Any]:
        return {
            "top": self.top,
            "bottom": self.bottom,
            "mid": self.mid,
            "kind": self.kind,
            "strength": self.strength,
            "label": self.label,
            "start_time": self.start_time.isoformat() if self.start_time else None,
        }


class BoxDetector:
    """
    Detects key horizontal zones from swing points on higher timeframes.
    Designed to produce the classic "3 boxes" view EliZ recommends.
    """

    def __init__(
        self,
        swing_left: int = 5,
        swing_right: int = 5,
        atr_period: int = 14,
        atr_multiplier: float = 0.4,
        max_boxes: int = 3,
        min_touches: int = 2,
    ):
        self.swing_left = swing_left
        self.swing_right = swing_right
        self.atr_period = atr_period
        self.atr_multiplier = atr_multiplier
        self.max_boxes = max_boxes
        self.min_touches = min_touches

    def _atr(self, df: pd.DataFrame) -> pd.Series:
        high = df["high"]
        low = df["low"]
        close = df["close"]
        tr = pd.concat(
            [
                high - low,
                (high - close.shift()).abs(),
                (low - close.shift()).abs(),
            ],
            axis=1,
        ).max(axis=1)
        return tr.rolling(self.atr_period, min_periods=1).mean()

    def _find_swing_points(self, df: pd.DataFrame) -> Tuple[List[int], List[int]]:
        """Return indices of swing highs and swing lows."""
        highs = []
        lows = []
        for i in range(self.swing_left, len(df) - self.swing_right):
            window_high = df["high"].iloc[i - self.swing_left : i + self.swing_right + 1]
            window_low = df["low"].iloc[i - self.swing_left : i + self.swing_right + 1]
            if df["high"].iloc[i] == window_high.max():
                highs.append(i)
            if df["low"].iloc[i] == window_low.min():
                lows.append(i)
        return highs, lows

    def detect(self, df: pd.DataFrame) -> List[Box]:
        """
        Main detection routine.

        Returns up to `max_boxes` most relevant zones, ordered from highest
        (supply) to lowest (demand). The middle one is labelled "mid".
        """
        if len(df) < self.swing_left + self.swing_right + 10:
            return []

        atr = self._atr(df)
        current_atr = float(atr.iloc[-1])
        zone_half = current_atr * self.atr_multiplier

        swing_high_idx, swing_low_idx = self._find_swing_points(df)

        # Collect candidate levels
        candidates: List[Dict] = []

        for idx in swing_high_idx:
            price = float(df["high"].iloc[idx])
            candidates.append(
                {
                    "price": price,
                    "kind": "supply",
                    "time": df.index[idx],
                    "idx": idx,
                }
            )

        for idx in swing_low_idx:
            price = float(df["low"].iloc[idx])
            candidates.append(
                {
                    "price": price,
                    "kind": "demand",
                    "time": df.index[idx],
                    "idx": idx,
                }
            )

        if not candidates:
            return []

        # Cluster nearby levels
        candidates = sorted(candidates, key=lambda x: x["price"], reverse=True)
        clusters: List[List[Dict]] = []
        used = set()

        for i, c in enumerate(candidates):
            if i in used:
                continue
            cluster = [c]
            used.add(i)
            for j, other in enumerate(candidates):
                if j in used:
                    continue
                if abs(c["price"] - other["price"]) <= zone_half * 2:
                    cluster.append(other)
                    used.add(j)
            clusters.append(cluster)

        # Build boxes from clusters
        boxes: List[Box] = []
        for cluster in clusters:
            prices = [c["price"] for c in cluster]
            kinds = [c["kind"] for c in cluster]
            top = max(prices) + zone_half * 0.5
            bottom = min(prices) - zone_half * 0.5
            # Dominant kind
            kind = max(set(kinds), key=kinds.count)
            strength = len(cluster)
            start_time = min(c["time"] for c in cluster)

            if strength >= self.min_touches or len(clusters) <= self.max_boxes:
                boxes.append(
                    Box(
                        top=top,
                        bottom=bottom,
                        kind=kind,
                        strength=strength,
                        start_time=start_time,
                    )
                )

        # Keep the strongest / most relevant max_boxes
        boxes = sorted(boxes, key=lambda b: b.strength, reverse=True)[: self.max_boxes]
        boxes = sorted(boxes, key=lambda b: b.top, reverse=True)  # high → low

        # Label them
        if len(boxes) >= 3:
            boxes[0].label = "Supply / Resistance"
            boxes[0].kind = "supply"
            boxes[1].label = "Mid / No-Trade Zone"
            boxes[1].kind = "mid"
            boxes[2].label = "Demand / Support"
            boxes[2].kind = "demand"
        elif len(boxes) == 2:
            boxes[0].label = "Supply / Resistance"
            boxes[0].kind = "supply"
            boxes[1].label = "Demand / Support"
            boxes[1].kind = "demand"
        elif len(boxes) == 1:
            boxes[0].label = "Key Level"
            # keep original kind

        return boxes

    def price_position(self, price: float, boxes: List[Box]) -> str:
        """Describe where the current price sits relative to the boxes."""
        if not boxes:
            return "no_boxes"

        for b in boxes:
            if b.contains(price):
                return f"inside_{b.kind}"

        # Outside
        highest = max(boxes, key=lambda b: b.top)
        lowest = min(boxes, key=lambda b: b.bottom)
        if price > highest.top:
            return "above_all"
        if price < lowest.bottom:
            return "below_all"
        return "between_boxes"  # classic middle-of-nowhere

    def summarize(self, boxes: List[Box]) -> None:
        console.print("\n[bold cyan]Detected Boxes (Higher TF)[/bold cyan]")
        for b in boxes:
            color = {
                "supply": "red",
                "demand": "green",
                "mid": "yellow",
            }.get(b.kind, "white")
            console.print(
                f"  [{color}]{b.label or b.kind.upper()}[/{color}] "
                f"| {b.bottom:.4f} – {b.top:.4f} "
                f"(strength {b.strength})"
            )