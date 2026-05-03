"""Plot helpers for the compaction assignment."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence


def save_basic_report_plot(partition_ids: Sequence[str], penalties: Sequence[float], costs: Sequence[float], output_path: str | Path) -> None:
    import matplotlib.pyplot as plt

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
