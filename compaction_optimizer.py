"""Cost-aware compaction optimizer for Apache Iceberg partitions.

Reads a JSON array of partition records, computes a performance-penalty proxy
and a compaction cost, then solves the budgeted selection problem with either:
  - exact  : 0/1 knapsack dynamic programming (globally optimal)
  - greedy : efficiency-ratio ranking (fast baseline)

Usage
-----
python compaction_optimizer.py --input data/partitions.json --mode exact \
    --output-json outputs/summary.json \
    --output-csv  outputs/selected.csv \
    --output-plot outputs/results_chart.png

Expected input schema (one object per partition)::

    {
        "partition_id"              : "p_001",
        "file_count"                : 120,
        "avg_file_size_mb"          : 45.2,
        "delete_file_count"         : 30,
        "delete_ratio"              : 0.25,
        "avg_delete_file_size_mb"   : 12.5,
        "partition_access_frequency": 85,
        "small_files_count"         : 95
    }
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Sequence

from src.penalty import PartitionMetrics
from src.selector import enrich_partitions, greedy_selection
from src.visualize import save_basic_report_plot, save_full_report_plot


DEFAULT_BUDGET_MINUTES = 3000.0
DEFAULT_COST_FACTOR = 0.001
DEFAULT_DELETE_RATIO_THRESHOLD = 0.20
DEFAULT_TARGET_FILE_SIZE_MB = 128.0
DEFAULT_SMALL_FILE_THRESHOLD_MB = 128.0


def _require_field(row: dict[str, Any], field: str) -> Any:
    if field not in row:
        raise ValueError(f"Missing required field: {field}")
    return row[field]


def load_partitions(input_path: Path) -> list[PartitionMetrics]:
    raw_data = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(raw_data, list):
        raise ValueError("Input JSON must contain a top-level array of partitions.")

    partitions: list[PartitionMetrics] = []
    for index, row in enumerate(raw_data, start=1):
        if not isinstance(row, dict):
            raise ValueError(f"Partition at index {index} is not a JSON object.")

        file_count = int(_require_field(row, "file_count"))
        avg_file_size_mb = float(_require_field(row, "avg_file_size_mb"))
        delete_file_count = int(_require_field(row, "delete_file_count"))
        avg_delete_file_size_mb = float(_require_field(row, "avg_delete_file_size_mb"))
        partition_access_frequency = float(_require_field(row, "partition_access_frequency"))
        small_files_count = int(_require_field(row, "small_files_count"))
        partition_id = str(row.get("partition_id", f"partition_{index:03d}"))

        delete_ratio_raw = row.get("delete_ratio")
        if delete_ratio_raw is None:
            delete_ratio = delete_file_count / file_count if file_count else 0.0
        else:
            delete_ratio = float(delete_ratio_raw)

        partitions.append(
            PartitionMetrics(
                partition_id=partition_id,
                file_count=file_count,
                avg_file_size_mb=avg_file_size_mb,
                delete_file_count=delete_file_count,
                delete_ratio=delete_ratio,
                avg_delete_file_size_mb=avg_delete_file_size_mb,
                partition_access_frequency=partition_access_frequency,
                small_files_count=small_files_count,
            )
        )

    return partitions


def exact_knapsack_selection(
    partitions: Sequence[PartitionMetrics],
    budget_minutes: float,
    *,
    scale: int = 100,
) -> tuple[list[PartitionMetrics], float, float]:
    if not partitions:
        return [], 0.0, 0.0

    budget_units = int(round(budget_minutes * scale))
    costs = [max(1, int(round(partition.compaction_cost * scale))) for partition in partitions]
    values = [partition.penalty for partition in partitions]

    dp = [0.0] * (budget_units + 1)
    keep = [bytearray(budget_units + 1) for _ in partitions]

    for index, cost_units in enumerate(costs):
        value = values[index]
        if cost_units > budget_units:
            continue

        for budget_index in range(budget_units, cost_units - 1, -1):
            candidate_value = dp[budget_index - cost_units] + value
            if candidate_value > dp[budget_index] + 1e-12:
                dp[budget_index] = candidate_value
                keep[index][budget_index] = 1

    best_budget_index = max(range(budget_units + 1), key=dp.__getitem__)
    selected: list[PartitionMetrics] = []
    remaining_budget = best_budget_index

    for index in range(len(partitions) - 1, -1, -1):
        if keep[index][remaining_budget]:
            selected.append(partitions[index])
            remaining_budget -= costs[index]

    selected.reverse()
    total_cost = sum(partition.compaction_cost for partition in selected)
    total_gain = sum(partition.penalty for partition in selected)
    return selected, total_cost, total_gain


def write_selection_csv(output_path: Path, selected: Sequence[PartitionMetrics]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "partition_id",
        "file_count",
        "avg_file_size_mb",
        "delete_file_count",
        "delete_ratio",
        "avg_delete_file_size_mb",
        "partition_access_frequency",
        "small_files_count",
        "small_file_pressure",
        "delete_pressure",
        "access_weight",
        "penalty",
        "compaction_cost",
        "efficiency_score",
        "threshold_signal",
    ]

    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for partition in selected:
            writer.writerow({name: getattr(partition, name) for name in fieldnames})


def build_summary(
    all_partitions: Sequence[PartitionMetrics],
    selected_partitions: Sequence[PartitionMetrics],
    budget_minutes: float,
    mode: str,
) -> dict[str, Any]:
    selected_ids = {partition.partition_id for partition in selected_partitions}
    skipped_partitions = [partition for partition in all_partitions if partition.partition_id not in selected_ids]

    total_cost = sum(partition.compaction_cost for partition in selected_partitions)
    total_gain = sum(partition.penalty for partition in selected_partitions)

    return {
        "mode": mode,
        "budget_minutes": budget_minutes,
        "selected_count": len(selected_partitions),
        "skipped_count": len(skipped_partitions),
        "total_cost_minutes": round(total_cost, 4),
        "budget_remaining_minutes": round(budget_minutes - total_cost, 4),
        "expected_performance_gain": round(total_gain, 4),
        "selected_partitions": [partition.partition_id for partition in selected_partitions],
        "skipped_partitions": [partition.partition_id for partition in skipped_partitions],
        "selected_details": [asdict(partition) for partition in selected_partitions],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Cost-aware compaction optimizer for Apache Iceberg partitions.")
    parser.add_argument("--input", default="data/partitions.json", help="Path to the partitions JSON file.")
    parser.add_argument("--budget-minutes", type=float, default=DEFAULT_BUDGET_MINUTES, help="Daily compaction budget in minutes.")
    parser.add_argument("--output-json", default="", help="Optional path for a JSON summary output.")
    parser.add_argument("--output-csv", default="", help="Optional path for the selected partitions CSV output.")
    parser.add_argument("--output-plot", default="outputs/results_chart.png", help="Path for the saved chart image.")
    parser.add_argument(
        "--mode",
        choices=("exact", "greedy"),
        default="exact",
        help="Selection strategy. 'exact' solves the 0/1 knapsack on scaled minutes; 'greedy' uses ratio ranking.",
    )
    args = parser.parse_args(argv)

    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(
            f"Input file not found: {input_path}. Place the partition JSON at this path or pass --input."
        )

    partitions = load_partitions(input_path)
    enriched_partitions = enrich_partitions(partitions)

    if args.mode == "greedy":
        selected_partitions, total_cost, total_gain = greedy_selection(enriched_partitions, args.budget_minutes)
    else:
        selected_partitions, total_cost, total_gain = exact_knapsack_selection(enriched_partitions, args.budget_minutes)

    summary = build_summary(enriched_partitions, selected_partitions, args.budget_minutes, args.mode)
    summary["total_cost_minutes"] = round(total_cost, 4)
    summary["expected_performance_gain"] = round(total_gain, 4)

    print(json.dumps(summary, indent=2))

    if args.output_csv:
        write_selection_csv(Path(args.output_csv), selected_partitions)

    if args.output_json:
        output_path = Path(args.output_json)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    if args.output_plot:
        plot_path = Path(args.output_plot)
        selected_ids = {partition.partition_id for partition in selected_partitions}
        statuses = [
            "Selected" if partition.partition_id in selected_ids else "Skipped"
            for partition in enriched_partitions
        ]
        save_full_report_plot(
            partition_ids=[partition.partition_id for partition in enriched_partitions],
            penalties=[partition.penalty for partition in enriched_partitions],
            costs=[partition.compaction_cost for partition in enriched_partitions],
            efficiency_scores=[partition.efficiency_score for partition in enriched_partitions],
            statuses=statuses,
            total_cost=total_cost,
            budget_minutes=args.budget_minutes,
            output_path=plot_path,
        )
    else:
        save_basic_report_plot(
            [partition.partition_id for partition in enriched_partitions],
            [partition.penalty for partition in enriched_partitions],
            [partition.compaction_cost for partition in enriched_partitions],
            Path("outputs/results_chart.png"),
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())