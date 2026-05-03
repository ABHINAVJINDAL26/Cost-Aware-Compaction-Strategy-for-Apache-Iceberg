"""Plot helpers for the compaction assignment."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt


COLOR_MAP = {
    "Selected": "#2ecc71",
    "Skipped": "#e74c3c",
    "Not Eligible": "#95a5a6",
}


def save_full_report_plot(
    partition_ids: Sequence[str],
    penalties: Sequence[float],
    costs: Sequence[float],
    efficiency_scores: Sequence[float],
    statuses: Sequence[str],
    total_cost: float,
    budget_minutes: float,
    output_path: str | Path,
) -> None:
    """Four-panel chart: penalty, cost, efficiency, and budget pie."""
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    colors = [COLOR_MAP.get(status, "#95a5a6") for status in statuses]
    patches = [mpatches.Patch(color=color, label=label) for label, color in COLOR_MAP.items()]

    fig, axes = plt.subplots(2, 2, figsize=(16, 11))
    fig.suptitle("Compaction Strategy - Simulation Results", fontsize=16, fontweight="bold", y=0.98)

    ax = axes[0, 0]
    ax.bar(partition_ids, penalties, color=colors, edgecolor="white")
    ax.set_title("Performance Penalty Score per Partition", fontweight="bold")
    ax.set_xlabel("Partition ID")
    ax.set_ylabel("Penalty Score")
    ax.tick_params(axis="x", rotation=45)
    ax.legend(handles=patches, fontsize=8)

    ax = axes[0, 1]
    ax.bar(partition_ids, costs, color=colors, edgecolor="white")
    avg_budget = budget_minutes / max(len(partition_ids), 1)
    ax.axhline(avg_budget, color="red", linestyle="--", linewidth=1.2, label=f"Avg budget/partition ({avg_budget:.0f} min)")
    ax.set_title("Compaction Cost per Partition (minutes)", fontweight="bold")
    ax.set_xlabel("Partition ID")
    ax.set_ylabel("Cost (minutes)")
    ax.tick_params(axis="x", rotation=45)
    ax.legend(fontsize=8)

    ax = axes[1, 0]
    ax.bar(partition_ids, efficiency_scores, color=colors, edgecolor="white")
    ax.set_title("Efficiency Score (Penalty / Cost) - Selection Basis", fontweight="bold")
    ax.set_xlabel("Partition ID")
    ax.set_ylabel("Efficiency Score")
    ax.tick_params(axis="x", rotation=45)
    ax.legend(handles=patches, fontsize=8)

    ax = axes[1, 1]
    budget_left = max(budget_minutes - total_cost, 0.0)
    ax.pie(
        [total_cost, budget_left],
        labels=[
            f"Used\n{total_cost:.0f} min\n({100 * total_cost / budget_minutes:.1f}%)",
            f"Remaining\n{budget_left:.0f} min\n({100 * budget_left / budget_minutes:.1f}%)",
        ],
        colors=["#2ecc71", "#ecf0f1"],
        startangle=90,
        wedgeprops={"edgecolor": "white", "linewidth": 2},
        textprops={"fontsize": 11},
    )
    ax.set_title(f"Budget Utilisation (Total: {budget_minutes:.0f} min)", fontweight="bold")

    fig.tight_layout()
    fig.savefig(output, dpi=160, bbox_inches="tight")
    plt.close(fig)


def save_basic_report_plot(partition_ids: Sequence[str], penalties: Sequence[float], costs: Sequence[float], output_path: str | Path) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    axes[0].bar(partition_ids, penalties, color="#4472c4")
    axes[0].set_title("Performance Penalty")
    axes[0].tick_params(axis="x", rotation=45)

    axes[1].bar(partition_ids, costs, color="#ed7d31")
    axes[1].set_title("Compaction Cost")
    axes[1].tick_params(axis="x", rotation=45)

    fig.tight_layout()
    fig.savefig(output, dpi=160)
    plt.close(fig)
