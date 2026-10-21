"""
EliZ (@eliz883) Price Action Analysis Engine
=============================================

Professional crypto analysis machine built strictly on the public trading
philosophy of Italian trader EliZ (@eliz883):

- Pure Price Action (no lagging indicators as primary decision)
- Monday Range as weekly framework
- Liquidity Sweep / Stop Run
- Deviation (false break) + Reclaim
- Higher-timeframe Boxes / Zones (preferably 3 boxes on Weekly)
- Strict no-trade in the middle of the range
- Discipline & Risk Management over entry prediction

This package provides:
- Data fetching (ccxt)
- Monday Range calculation
- Swing-based / ATR boxes
- Pattern detection (Sweep, Deviation, Reclaim)
- Multi-timeframe scoring engine
- Chart annotation & reporting
- CLI + Streamlit dashboard

Author: Community implementation based on public posts of @eliz883
License: MIT
"""

__version__ = "1.0.0"
__author__ = "EliZ Analyzer Contributors"

from .core.analyzer import EliZAnalyzer
from .core.monday_range import MondayRangeCalculator
from .core.levels import BoxDetector
from .core.patterns import PatternDetector

__all__ = [
    "EliZAnalyzer",
    "MondayRangeCalculator",
    "BoxDetector",
    "PatternDetector",
]