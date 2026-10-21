"""
Streamlit Dashboard for EliZ Analyzer
Run with: streamlit run app_streamlit.py
"""

import streamlit as st
from eliz_analyzer import EliZAnalyzer
from eliz_analyzer.visualization.charts import plot_analysis
import tempfile
from pathlib import Path

st.set_page_config(
    page_title="EliZ Price Action Analyzer",
    page_icon="📊",
    layout="wide",
)

st.title("EliZ (@eliz883) Price Action Analyzer")
st.markdown(
    "> *Strategy gets you in. Discipline makes you money. Risk management keeps you in the market.*"
)

with st.sidebar:
    st.header("Settings")
    symbol = st.text_input("Symbol", value="BTC/USDT")
    higher_tf = st.selectbox("Higher TF (Boxes)", ["1w", "1d", "12h"], index=0)
    entry_tf = st.selectbox("Entry TF", ["4h", "1h", "15m"], index=0)
    limit = st.slider("Candles", 200, 1000, 500)
    run = st.button("Analyze", type="primary")

if run:
    with st.spinner(f"Analyzing {symbol} ..."):
        analyzer = EliZAnalyzer()
        result = analyzer.analyze(
            symbol=symbol,
            higher_tf=higher_tf,
            entry_tf=entry_tf,
            limit=limit,
        )

    col1, col2, col3 = st.columns(3)
    col1.metric("Current Price", f"{result.current_price:.4f}")
    col2.metric("Recommendation", result.recommendation)
    col3.metric("Setups Found", len(result.setups))

    st.subheader("Position Assessment")
    st.write(f"**vs Monday Range:** {result.position_vs_range}")
    st.write(f"**vs Boxes:** {result.position_vs_boxes}")

    if result.monday_range:
        st.subheader("Monday Range")
        mr = result.monday_range
        st.write(f"High: `{mr.high:.4f}` | Low: `{mr.low:.4f}` | Size: `{mr.range_pct:.2f}%`")

    if result.boxes:
        st.subheader("Boxes")
        for b in result.boxes:
            st.write(f"- **{b.label or b.kind}**: `{b.bottom:.4f}` – `{b.top:.4f}`")

    if result.setups:
        st.subheader("Detected Setups")
        for s in result.setups:
            color = "green" if s.direction == "long" else "red"
            st.markdown(
                f":{color}[**{s.direction.upper()}**] Score **{s.score}**  \n"
                f"{s.reason}  \n"
                f"Entry: `{s.entry_zone[0]:.4f}` – `{s.entry_zone[1]:.4f}` | "
                f"Invalidation: `{s.invalidation:.4f}`"
            )
    else:
        st.info("No high-probability Sweep + Deviation + Reclaim trigger detected. Sitting on hands.")

    st.subheader("Notes")
    for n in result.notes:
        st.write(f"• {n}")

    # Chart
    st.subheader("Annotated Chart")
    with tempfile.TemporaryDirectory() as tmp:
        chart_path = Path(tmp) / "chart.png"
        data = analyzer.fetcher.fetch_ohlcv(symbol, timeframe=entry_tf, limit=limit)
        plot_analysis(
            df=data,
            symbol=symbol,
            monday_range=result.monday_range,
            boxes=result.boxes,
            setups=result.setups,
            save_path=str(chart_path),
        )
        st.image(str(chart_path), use_container_width=True)

st.markdown("---")
st.caption(
    "Educational implementation of public teachings by @eliz883. Not financial advice. "
    "Always manage risk and do your own research."
)