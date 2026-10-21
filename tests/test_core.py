"""
Basic unit tests for the EliZ Analyzer core modules.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone

from eliz_analyzer.core.monday_range import MondayRangeCalculator, MondayRange
from eliz_analyzer.core.levels import BoxDetector
from eliz_analyzer.core.patterns import PatternDetector


def make_sample_df(n=200, start_price=50000.0):
    """Generate synthetic OHLCV for testing."""
    dates = pd.date_range(
        end=datetime.now(timezone.utc), periods=n, freq="1h", tz="UTC"
    )
    np.random.seed(42)
    returns = np.random.normal(0, 0.002, n)
    close = start_price * np.cumprod(1 + returns)
    high = close * (1 + np.abs(np.random.normal(0, 0.001, n)))
    low = close * (1 - np.abs(np.random.normal(0, 0.001, n)))
    open_ = np.roll(close, 1)
    open_[0] = start_price
    volume = np.random.uniform(100, 1000, n)

    df = pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=dates,
    )
    return df


def test_monday_range_calculation():
    df = make_sample_df(400)
    calc = MondayRangeCalculator()
    ranges = calc.calculate_from_df(df, lookback_weeks=4)
    assert len(ranges) >= 1
    for r in ranges:
        assert r.high >= r.low
        assert r.range_size >= 0


def test_box_detector():
    df = make_sample_df(100)
    # Upsample conceptually – just use the same df as "weekly-like"
    detector = BoxDetector(max_boxes=3, min_touches=1)
    boxes = detector.detect(df)
    # May be 0–3 boxes depending on swings
    assert isinstance(boxes, list)


def test_pattern_detector_no_crash():
    df = make_sample_df(100)
    detector = PatternDetector()
    # Create a fake Monday Range
    mr = MondayRange(
        week_start=datetime.now(timezone.utc) - timedelta(days=3),
        high=float(df["high"].max()),
        low=float(df["low"].min()),
        closed=True,
    )
    setups = detector.analyze_monday_range(df, mr)
    assert isinstance(setups, list)


if __name__ == "__main__":
    test_monday_range_calculation()
    test_box_detector()
    test_pattern_detector_no_crash()
    print("All basic tests passed.")
