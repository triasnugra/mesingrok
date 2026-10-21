"""
Chart Visualization with EliZ annotations
=========================================
Uses mplfinance + matplotlib to draw Monday Range, Boxes, and detected setups.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import pandas as pd
import matplotlib.pyplot as plt
import mplfinance as mpf
from matplotlib.patches import Rectangle

from ..core.monday_range import MondayRange
from ..core.levels import Box
from ..core.patterns import Setup


def plot_analysis(
    df: pd.DataFrame,
    symbol: str,
    monday_range: Optional[MondayRange] = None,
    boxes: Optional[List[Box]] = None,
    setups: Optional[List[Setup]] = None,
    save_path: Optional[str] = None,
    style: str = "dark",
    title_suffix: str = "",
) -> None:
    """
    Create a professional annotated chart.
    """
    if boxes is None:
        boxes = []
    if setups is None:
        setups = []

    # Prepare data for mplfinance
    plot_df = df.copy()
    if plot_df.index.tz is not None:
        plot_df.index = plot_df.index.tz_localize(None)

    # Limit to last N bars for clarity
    plot_df = plot_df.iloc[-120:]

    # Base style
    mc = mpf.make_marketcolors(
        up="#26a69a", down="#ef5350", edge="inherit", wick="inherit", volume="in"
    )
    s = mpf.make_mpf_style(
        marketcolors=mc,
        gridstyle="--",
        gridcolor="#333333" if style == "dark" else "#cccccc",
        facecolor="#121212" if style == "dark" else "white",
        figcolor="#121212" if style == "dark" else "white",
        rc={
            "axes.labelcolor": "white" if style == "dark" else "black",
            "xtick.color": "white" if style == "dark" else "black",
            "ytick.color": "white" if style == "dark" else "black",
            "text.color": "white" if style == "dark" else "black",
        },
    )

    add_plots = []
    hlines = []
    colors = []
    linewidths = []
    linestyles = []

    # Monday Range lines
    if monday_range:
        hlines.extend([monday_range.high, monday_range.low])
        colors.extend(["#ff9800", "#ff9800"])
        linewidths.extend([1.5, 1.5])
        linestyles.extend(["--", "--"])

    # Box mid lines (optional)
    for b in boxes:
        hlines.append(b.mid)
        colors.append("#9c27b0" if b.kind == "mid" else "#2196f3")
        linewidths.append(1.0)
        linestyles.append(":")

    # Create figure
    fig, axes = mpf.plot(
        plot_df,
        type="candle",
        style=s,
        title=f"\n{symbol} – EliZ Price Action Analysis {title_suffix}",
        ylabel="Price",
        volume=True,
        figsize=(14, 8),
        returnfig=True,
        hlines=dict(hlines=hlines, colors=colors, linewidths=linewidths, linestyle=linestyles)
        if hlines
        else None,
    )

    ax = axes[0]

    # Draw boxes as rectangles
    xmin, xmax = ax.get_xlim()
    for b in boxes:
        color = {
            "supply": "#ef535080",
            "demand": "#26a69a80",
            "mid": "#ffeb3b40",
        }.get(b.kind, "#ffffff40")
        edge = {
            "supply": "#ef5350",
            "demand": "#26a69a",
            "mid": "#ffeb3b",
        }.get(b.kind, "#ffffff")

        rect = Rectangle(
            (xmin, b.bottom),
            xmax - xmin,
            b.height,
            facecolor=color,
            edgecolor=edge,
            linewidth=1.2,
            alpha=0.3,
            zorder=0,
        )
        ax.add_patch(rect)

        # Label
        ax.text(
            xmax - 1,
            b.mid,
            b.label or b.kind.upper(),
            color=edge,
            fontsize=8,
            va="center",
            ha="right",
            fontweight="bold",
            alpha=0.9,
        )

    # Annotate setups
    for s in setups[:3]:  # max 3 annotations
        color = "#26a69a" if s.direction == "long" else "#ef5350"
        ax.axhline(s.invalidation, color=color, linestyle="-.", linewidth=1.0, alpha=0.7)
        mid_entry = (s.entry_zone[0] + s.entry_zone[1]) / 2
        ax.annotate(
            f"{s.direction.upper()} {s.score}",
            xy=(xmax - 5, mid_entry),
            color=color,
            fontsize=9,
            fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#000000aa", edgecolor=color),
        )

    # Monday Range label
    if monday_range:
        ax.text(
            xmin + 1,
            monday_range.high,
            "Monday High",
            color="#ff9800",
            fontsize=8,
            va="bottom",
        )
        ax.text(
            xmin + 1,
            monday_range.low,
            "Monday Low",
            color="#ff9800",
            fontsize=8,
            va="top",
        )

    plt.tight_layout()

    if save_path:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
        print(f"Chart saved → {save_path}")
    else:
        plt.show()

    plt.close(fig)