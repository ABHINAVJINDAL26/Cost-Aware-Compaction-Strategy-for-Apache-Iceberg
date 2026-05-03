"""Penalty model for compaction scoring."""

from __future__ import annotations

from dataclasses import dataclass


EPSILON = 1e-9


@dataclass
class PartitionMetrics:
    partition_id: str
    file_count: int
    avg_file_size_mb: float
    delete_file_count: int
    delete_ratio: float
    avg_delete_file_size_mb: float
    partition_access_frequency: float
    small_files_count: int
    small_file_pressure: float = 0.0
    delete_pressure: float = 0.0
    access_weight: float = 0.0
    penalty: float = 0.0
    compaction_cost: float = 0.0
    efficiency_score: float = 0.0
    threshold_signal: bool = False


def calculate_penalty(partition: PartitionMetrics, max_access_frequency: float) -> float:
    small_file_pressure = partition.small_files_count / max(partition.avg_file_size_mb, EPSILON)
    delete_pressure = partition.delete_file_count * partition.avg_delete_file_size_mb
    access_weight = partition.partition_access_frequency / max(max_access_frequency, EPSILON)
    return (small_file_pressure + delete_pressure) * (1.0 + access_weight)
