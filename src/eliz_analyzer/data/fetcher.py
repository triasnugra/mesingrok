"""
Data Fetcher using ccxt
-----------------------
Clean, rate-limit aware OHLCV loader for Binance (and other exchanges).
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any

import ccxt
import pandas as pd
from rich.console import Console

console = Console()


class DataFetcher:
    """Fetch OHLCV data with proper timezone handling and caching."""

    def __init__(
        self,
        exchange_id: str = "binance",
        api_key: Optional[str] = None,
        secret: Optional[str] = None,
        rate_limit: bool = True,
        timeout: int = 30000,
    ):
        exchange_class = getattr(ccxt, exchange_id)
        self.exchange = exchange_class(
            {
                "apiKey": api_key,
                "secret": secret,
                "enableRateLimit": rate_limit,
                "timeout": timeout,
                "options": {"defaultType": "spot"},  # change to 'future' if needed
            }
        )
        self._cache: Dict[str, pd.DataFrame] = {}

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1h",
        since: Optional[int] = None,
        limit: int = 1000,
        max_retries: int = 3,
    ) -> pd.DataFrame:
        """
        Fetch OHLCV and return a clean pandas DataFrame indexed by UTC datetime.
        """
        cache_key = f"{symbol}_{timeframe}_{since}_{limit}"
        if cache_key in self._cache:
            return self._cache[cache_key].copy()

        for attempt in range(max_retries):
            try:
                raw = self.exchange.fetch_ohlcv(
                    symbol, timeframe=timeframe, since=since, limit=limit
                )
                if not raw:
                    raise ValueError(f"Empty OHLCV returned for {symbol} {timeframe}")

                df = pd.DataFrame(
                    raw, columns=["timestamp", "open", "high", "low", "close", "volume"]
                )
                df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
                df.set_index("timestamp", inplace=True)
                df = df.astype(
                    {
                        "open": float,
                        "high": float,
                        "low": float,
                        "close": float,
                        "volume": float,
                    }
                )
                df = df[~df.index.duplicated(keep="last")]
                df.sort_index(inplace=True)

                self._cache[cache_key] = df
                return df.copy()

            except (ccxt.NetworkError, ccxt.ExchangeError) as e:
                console.print(f"[yellow]Attempt {attempt+1} failed: {e}[/yellow]")
                time.sleep(2 ** attempt)

        raise RuntimeError(f"Failed to fetch {symbol} {timeframe} after {max_retries} retries")

    def fetch_multi_timeframe(
        self,
        symbol: str,
        timeframes: List[str],
        limit: int = 500,
    ) -> Dict[str, pd.DataFrame]:
        """Fetch several timeframes at once."""
        result = {}
        for tf in timeframes:
            console.print(f"  → Fetching {symbol} [{tf}] ...")
            result[tf] = self.fetch_ohlcv(symbol, timeframe=tf, limit=limit)
        return result

    def get_monday_start(self, dt: datetime) -> datetime:
        """Return the Monday 00:00 UTC of the week containing dt."""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        # weekday: Monday=0
        days_since_monday = dt.weekday()
        monday = (dt - timedelta(days=days_since_monday)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        return monday

    def clear_cache(self):
        self._cache.clear()