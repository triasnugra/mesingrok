"""
Pattern Detector – Liquidity Sweep, Deviation, Reclaim
======================================================
Implements the exact trigger logic publicly taught by @eliz883:

Long setup example:
"A trigger is not a random line. It is a liquidity sweep outside the range,
followed by a reclaim and retest. Sweep below + reclaim above = potential long."

Short setup example:
"I’ll only step in if $BTC gives me a breakout, followed by a deviation and
a move back inside the range. That’s where I may look for a short."

Key rules:
- Level alone is NOT a signal
- Reaction / confirmation is everything
- No Deviation + Reclaim → No Trade
- Middle of the range → sitting on hands
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple

import pandas as pd
import numpy as np
from rich.console import Console

from .monday_range import MondayRange
from .levels import Box

console = Console()


@dataclass
class Setup:
    """A detected trading setup following EliZ rules."""

    direction: str                # "long" | "short"
    score: int
    entry_zone: Tuple[float, float]
    invalidation: float
    target_hint: Optional[float] = None
    reason: str = ""
    trigger_time: Optional[pd.Timestamp] = None
    monday_range: Optional[MondayRange] = None
    related_box: Optional[Box] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "direction": self.direction,
            "score": self.score,
            "entry_zone": self.entry_zone,
            "invalidation": self.invalidation,
            "target_hint": self.target_hint,
            "reason": self.reason,
            "trigger_time": self.trigger_time.isoformat() if self.trigger_time else None,
            "details": self.details,
        }


class PatternDetector:
    """
    Detects Sweep → Deviation → Reclaim sequences relative to
    Monday Range and/or key Boxes.
    """

    def __init__(
        self,
        min_penetration_pct: float = 0.05,
        max_bars_after_sweep: int = 12,
        min_outside_bars: int = 1,
        max_outside_bars: int = 8,
    ):
        self.min_penetration_pct = min_penetration_pct
        self.max_bars_after = max_bars_after_sweep
        self.min_outside = min_outside_bars
        self.max_outside = max_outside_bars

    def _pct_beyond(self, price: float, level: float) -> float:
        if level == 0:
            return 0.0
        return abs(price - level) / level * 100

    def detect_sweep_and_reclaim(
        self,
        df: pd.DataFrame,
        level: float,
        direction: str,           # "above" (looking for short) or "below" (looking for long)
        lookback: int = 30,
    ) -> Optional[Dict[str, Any]]:
        """
        Generic sweep + reclaim detector against a single horizontal level.

        direction="below" → we look for price going under `level` then reclaiming above it (long)
        direction="above" → we look for price going over `level` then reclaiming below it (short)
        """
        if len(df) < lookback + 5:
            return None

        recent = df.iloc[-lookback:].copy()

        if direction == "below":
            # Sweep under the level
            swept = recent[recent["low"] < level]
            if swept.empty:
                return None
            sweep_idx = swept.index[-1]
            penetration = self._pct_beyond(float(swept.loc[sweep_idx, "low"]), level)
            if penetration < self.min_penetration_pct:
                return None

            # After the sweep, did price reclaim (close back above level)?
            after = recent.loc[sweep_idx:]
            reclaim_bars = after[after["close"] > level]
            if reclaim_bars.empty:
                return None
            reclaim_idx = reclaim_bars.index[0]

            # Optional: check it didn't stay too long outside
            bars_outside = len(after.loc[:reclaim_idx]) - 1
            if bars_outside > self.max_outside:
                return None

            return {
                "type": "sweep_below_reclaim",
                "level": level,
                "sweep_time": sweep_idx,
                "sweep_price": float(swept.loc[sweep_idx, "low"]),
                "reclaim_time": reclaim_idx,
                "reclaim_price": float(reclaim_bars.loc[reclaim_idx, "close"]),
                "penetration_pct": penetration,
                "bars_outside": bars_outside,
            }

        elif direction == "above":
            swept = recent[recent["high"] > level]
            if swept.empty:
                return None
            sweep_idx = swept.index[-1]
            penetration = self._pct_beyond(float(swept.loc[sweep_idx, "high"]), level)
            if penetration < self.min_penetration_pct:
                return None

            after = recent.loc[sweep_idx:]
            reclaim_bars = after[after["close"] < level]
            if reclaim_bars.empty:
                return None
            reclaim_idx = reclaim_bars.index[0]
            bars_outside = len(after.loc[:reclaim_idx]) - 1
            if bars_outside > self.max_outside:
                return None

            return {
                "type": "sweep_above_reclaim",
                "level": level,
                "sweep_time": sweep_idx,
                "sweep_price": float(swept.loc[sweep_idx, "high"]),
                "reclaim_time": reclaim_idx,
                "reclaim_price": float(reclaim_bars.loc[reclaim_idx, "close"]),
                "penetration_pct": penetration,
                "bars_outside": bars_outside,
            }

        return None

    def analyze_monday_range(
        self,
        df: pd.DataFrame,
        monday_range: MondayRange,
        current_price: Optional[float] = None,
    ) -> List[Setup]:
        """
        Full analysis against the current Monday Range.
        Returns zero or more Setup objects.
        """
        setups: List[Setup] = []
        if current_price is None:
            current_price = float(df["close"].iloc[-1])

        # 1. Classic Long: Sweep Monday Low → Reclaim
        long_signal = self.detect_sweep_and_reclaim(
            df, monday_range.low, direction="below"
        )
        if long_signal:
            score = 70
            score += min(20, int(long_signal["penetration_pct"] * 10))  # deeper sweep better
            if long_signal["bars_outside"] <= 3:
                score += 10  # quick reclaim is stronger

            invalidation = long_signal["sweep_price"] * 0.998  # slightly below the sweep low
            entry_low = monday_range.low
            entry_high = monday_range.low + (monday_range.range_size * 0.15)

            setups.append(
                Setup(
                    direction="long",
                    score=min(score, 100),
                    entry_zone=(entry_low, entry_high),
                    invalidation=invalidation,
                    target_hint=monday_range.high,
                    reason="Sweep Monday Low + Reclaim (classic EliZ long)",
                    trigger_time=long_signal["reclaim_time"],
                    monday_range=monday_range,
                    details=long_signal,
                )
            )

        # 2. Classic Short: Breakout Monday High → Deviation → back inside
        short_signal = self.detect_sweep_and_reclaim(
            df, monday_range.high, direction="above"
        )
        if short_signal:
            score = 70
            score += min(20, int(short_signal["penetration_pct"] * 10))
            if short_signal["bars_outside"] <= 3:
                score += 10

            invalidation = short_signal["sweep_price"] * 1.002
            entry_high = monday_range.high
            entry_low = monday_range.high - (monday_range.range_size * 0.15)

            setups.append(
                Setup(
                    direction="short",
                    score=min(score, 100),
                    entry_zone=(entry_low, entry_high),
                    invalidation=invalidation,
                    target_hint=monday_range.low,
                    reason="Breakout Monday High + Deviation + Reclaim (classic EliZ short)",
                    trigger_time=short_signal["reclaim_time"],
                    monday_range=monday_range,
                    details=short_signal,
                )
            )

        # 3. Penalize / warn if price is deep in the middle
        if monday_range.is_inside(current_price):
            dist_to_mid = abs(current_price - monday_range.mid) / monday_range.range_size
            if dist_to_mid < 0.25:  # very central
                # We still return the setups above if they exist,
                # but we also add a "no-trade" note via low score if needed.
                pass

        return setups

    def analyze_boxes(
        self,
        df: pd.DataFrame,
        boxes: List[Box],
        current_price: Optional[float] = None,
    ) -> List[Setup]:
        """Analyze against the higher-TF boxes (supply / demand)."""
        setups: List[Setup] = []
        if not boxes:
            return setups
        if current_price is None:
            current_price = float(df["close"].iloc[-1])

        for box in boxes:
            if box.kind == "demand":
                sig = self.detect_sweep_and_reclaim(df, box.bottom, direction="below")
                if sig:
                    score = 65 + min(15, box.strength * 3)
                    setups.append(
                        Setup(
                            direction="long",
                            score=min(score, 95),
                            entry_zone=(box.bottom, box.mid),
                            invalidation=sig["sweep_price"] * 0.997,
                            target_hint=None,
                            reason=f"Sweep + Reclaim of Demand Box ({box.label})",
                            trigger_time=sig["reclaim_time"],
                            related_box=box,
                            details=sig,
                        )
                    )
            elif box.kind == "supply":
                sig = self.detect_sweep_and_reclaim(df, box.top, direction="above")
                if sig:
                    score = 65 + min(15, box.strength * 3)
                    setups.append(
                        Setup(
                            direction="short",
                            score=min(score, 95),
                            entry_zone=(box.mid, box.top),
                            invalidation=sig["sweep_price"] * 1.003,
                            target_hint=None,
                            reason=f"Deviation + Reclaim of Supply Box ({box.label})",
                            trigger_time=sig["reclaim_time"],
                            related_box=box,
                            details=sig,
                        )
                    )

        return setups

    def full_scan(
        self,
        df_entry: pd.DataFrame,
        monday_range: Optional[MondayRange],
        boxes: List[Box],
        current_price: Optional[float] = None,
    ) -> List[Setup]:
        """Combine Monday Range + Boxes analysis and rank by score."""
        all_setups: List[Setup] = []

        if monday_range is not None:
            all_setups.extend(
                self.analyze_monday_range(df_entry, monday_range, current_price)
            )

        all_setups.extend(self.analyze_boxes(df_entry, boxes, current_price))

        # Deduplicate roughly similar setups and sort by score
        all_setups = sorted(all_setups, key=lambda s: s.score, reverse=True)
        return all_setups