"""Selection strategies for budgeted compaction."""

from __future__ import annotations

from dataclasses import asdict
from typing import Sequence

from .cost import calculate_cost
from .penalty import PartitionMetrics, calculate_penalty


def enrich_partitions(partitions: Sequence[PartitionMetrics]) -> list[PartitionMetrics]:
    if not partitions:
        return []

    max_access_frequency = max(partition.partition_access_frequency for partition in partitions) or 1.0
    enriched: list[PartitionMetrics] = []

    for partition in partitions:
        penalty = calculate_penalty(partition, max_access_frequency)
        compaction_cost = calculate_cost(partition)
        access_weight = partition.partition_access_frequency / max_access_frequency
        efficiency_score = penalty / compaction_cost
        threshold_signal = partition.delete_ratio >= 0.20 or partition.avg_file_size_mb < 128.0 or partition.small_files_count > 0

        payload = asdict(partition)
        payload.update(
            access_weight=access_weight,
            penalty=penalty,
            compaction_cost=compaction_cost,
            efficiency_score=efficiency_score,
            threshold_signal=threshold_signal,
        )

        enriched.append(
            PartitionMetrics(**payload)
        )

    return enriched


def greedy_selection(partitions: Sequence[PartitionMetrics], budget_minutes: float) -> tuple[list[PartitionMetrics], float, float]:
    ranked = sorted(partitions, key=lambda item: (item.efficiency_score, item.penalty), reverse=True)
    selected: list[PartitionMetrics] = []
    total_cost = 0.0
    total_gain = 0.0

    for partition in ranked:
        if total_cost + partition.compaction_cost <= budget_minutes:
            selected.append(partition)
            total_cost += partition.compaction_cost
            total_gain += partition.penalty

    return selected, total_cost, total_gain
