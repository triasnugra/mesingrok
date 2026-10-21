# EliZ Price Action Analyzer

**Professional Crypto Analysis Engine based on the public trading methodology of @eliz883 (EliZ)**

> “Strategy gets you in. Discipline makes you money. Risk management keeps you in the market.”  
> — @eliz883

This open-source tool implements the core concepts that Italian trader **EliZ** (@eliz883) has consistently taught publicly across 2023–2026:

- Pure **Price Action** (indicators are secondary)
- **Monday Range** as the weekly framework
- **Liquidity Sweep / Stop Run**
- **Deviation** (false break) + **Reclaim**
- Higher-timeframe **Boxes / Zones** (the famous “draw three boxes on the Weekly”)
- Strict **no-trade in the middle of the range**
- Clear invalidation & risk-first mindset

---

## Features

| Feature                        | Description                                      |
|--------------------------------|--------------------------------------------------|
| Monday Range Calculator        | Automatic High/Low of every Monday (UTC)         |
| 3-Box Detector                 | Swing-based supply / mid / demand zones on HTF   |
| Sweep + Deviation + Reclaim    | Exact trigger logic taught by EliZ               |
| Multi-timeframe scoring        | Higher TF structure + lower TF entry precision   |
| Annotated Charts               | Visual Monday Range + Boxes + Setup zones        |
| CLI + JSON export              | Ready for automation / bots / alerts             |
| Streamlit Dashboard (optional) | Interactive web UI                               |
| Fully configurable             | `config/default.yaml`                            |

---

## Installation

```bash
git clone https://github.com/YOUR_USERNAME/eliz883-analyzer.git
cd eliz883-analyzer

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -r requirements.txt
pip install -e .
```

---

## Quick Start

### Analyze a single symbol

```bash
eliz-analyzer analyze BTC/USDT --chart --save-chart ./output/btc_4h.png
```

### Scan multiple coins

```bash
eliz-analyzer scan -s BTC/USDT -s ETH/USDT -s SOL/USDT -s AVAX/USDT
```

### View the philosophy

```bash
eliz-analyzer philosophy
```

### Python API

```python
from eliz_analyzer import EliZAnalyzer

analyzer = EliZAnalyzer()
result = analyzer.analyze("BTC/USDT", higher_tf="1w", entry_tf="4h")

print(result.recommendation)
for setup in result.setups:
    print(setup.direction, setup.score, setup.reason)
```

---

## How the Engine Thinks (EliZ Rules)

1. **Determine structure** on higher timeframe (Weekly preferred) → draw the 3 boxes.
2. **Calculate Monday Range** (High & Low of Monday).
3. Wait for price to reach an extreme (Monday High/Low or Box edge).
4. Look for:
   - Liquidity taken (sweep)
   - Deviation (false break)
   - Reclaim + clear reaction
5. Only then consider entry with **clear invalidation**.
6. If price is in the middle of the range → **NO TRADE**.

### Classic Long Trigger
```
Sweep below Monday Low / Demand Box
→ Price returns inside (reclaim)
→ Entry on retest with SL below the sweep low
```

### Classic Short Trigger
```
Breakout above Monday High / Supply Box
→ Deviation (fails to hold)
→ Price returns inside the range
→ Entry short with SL above the deviation high
```

---

## Project Structure

```
eliz883-analyzer/
├── config/default.yaml          # All tunable parameters
├── src/eliz_analyzer/
│   ├── data/fetcher.py          # ccxt data layer
│   ├── core/
│   │   ├── monday_range.py      # Monday Range engine
│   │   ├── levels.py            # Box / Zone detector
│   │   ├── patterns.py          # Sweep / Deviation / Reclaim
│   │   └── analyzer.py          # Main orchestrator
│   ├── visualization/charts.py
│   └── cli.py
├── examples/
├── tests/
└── README.md
```

---

## Configuration

Edit `config/default.yaml` to change:

- Exchange & rate limits
- Default symbols
- Timeframes
- Penetration thresholds for sweeps
- Scoring weights
- Chart style

---

## Disclaimer

This software is an **educational implementation** of publicly shared trading concepts by @eliz883.  
It is **not financial advice**. Cryptocurrency trading involves substantial risk of loss.  

Always:
- Use proper risk management
- Never risk more than you can afford to lose
- Do your own research
- “Sitting on hands is also a position.”

---

## License

MIT License – feel free to fork, improve, and share.

---

## Credits

- Original methodology: **@eliz883 (EliZ)** on X
- Community implementation for learning & research purposes

**Built with respect for the pure price action philosophy.**
```