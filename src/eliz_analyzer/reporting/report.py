"""
Simple text / markdown report generator.
"""

from __future__ import annotations

from datetime import datetime
from typing import List

from ..core.analyzer import AnalysisResult


def generate_markdown_report(results: List[AnalysisResult]) -> str:
    lines = [
        f"# EliZ Price Action Analysis Report",
        f"**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "> Strategy gets you in. Discipline makes you money. Risk management keeps you in the market.",
        "",
        "---",
        "",
    ]

    for r in results:
        lines.append(f"## {r.symbol}")
        lines.append(f"- **Current Price:** `{r.current_price:.4f}`")
        lines.append(f"- **Position vs Monday Range:** {r.position_vs_range}")
        lines.append(f"- **Position vs Boxes:** {r.position_vs_boxes}")
        lines.append(f"- **Recommendation:** **{r.recommendation}**")
        lines.append("")

        if r.monday_range:
            mr = r.monday_range
            lines.append("### Monday Range")
            lines.append(f"- High: `{mr.high:.4f}`")
            lines.append(f"- Low: `{mr.low:.4f}`")
            lines.append(f"- Size: `{mr.range_pct:.2f}%`")
            lines.append("")

        if r.boxes:
            lines.append("### Boxes")
            for b in r.boxes:
                lines.append(f"- **{b.label or b.kind}**: `{b.bottom:.4f}` – `{b.top:.4f}` (strength {b.strength})")
            lines.append("")

        if r.setups:
            lines.append("### Detected Setups")
            for s in r.setups:
                lines.append(f"- **{s.direction.upper()}** (Score {s.score})")
                lines.append(f"  - Reason: {s.reason}")
                lines.append(f"  - Entry zone: `{s.entry_zone[0]:.4f}` – `{s.entry_zone[1]:.4f}`")
                lines.append(f"  - Invalidation: `{s.invalidation:.4f}`")
            lines.append("")

        lines.append("### Notes")
        for n in r.notes:
            lines.append(f"- {n}")
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)