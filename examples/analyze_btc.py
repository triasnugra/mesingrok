#!/usr/bin/env python3
"""
Example: Full analysis of BTC/USDT using the EliZ engine.
"""

from eliz_analyzer import EliZAnalyzer
from eliz_analyzer.visualization.charts import plot_analysis
from pathlib import Path

def main():
    analyzer = EliZAnalyzer()

    result = analyzer.analyze(
        symbol="BTC/USDT",
        higher_tf="1w",
        entry_tf="4h",
        monday_tf="1h",
        limit=600,
    )

    print("\n=== JSON Summary ===")
    import json
    print(json.dumps(result.to_dict(), indent=2, default=str))

    # Optional chart
    out_dir = Path("./output/charts")
    out_dir.mkdir(parents=True, exist_ok=True)

    data = analyzer.fetcher.fetch_ohlcv("BTC/USDT", timeframe="4h", limit=600)
    plot_analysis(
        df=data,
        symbol="BTC/USDT",
        monday_range=result.monday_range,
        boxes=result.boxes,
        setups=result.setups,
        save_path=str(out_dir / "BTC_USDT_4h_eliz.png"),
    )

if __name__ == "__main__":
    main()
