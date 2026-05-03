"""Compaction cost model."""

from __future__ import annotations

from .penalty import PartitionMetrics


DEFAULT_COST_FACTOR = 0.001
EPSILON = 1e-9


def calculate_cost(partition: PartitionMetrics, cost_factor: float = DEFAULT_COST_FACTOR) -> float:
    cost = partition.file_count * partition.avg_file_size_mb * partition.avg_delete_file_size_mb * cost_factor
    return cost if cost > 0 else EPSILON
