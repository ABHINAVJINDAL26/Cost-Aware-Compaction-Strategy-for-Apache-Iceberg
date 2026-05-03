# Cost-Aware Compaction Strategy for Apache Iceberg

This project solves a budgeted partition compaction problem for Apache Iceberg.
The goal is to choose which partitions to compact so that performance gain is
maximized while the daily compute budget stays within limits.

## Project Structure

- `compaction_optimizer.py` - main entrypoint
- `src/penalty.py` - performance penalty model
- `src/cost.py` - compaction cost model
- `src/selector.py` - enrichment and greedy selection
- `src/visualize.py` - report charts
- `data/partitions.json` - input dataset
- `outputs/` - generated CSV, JSON, and chart outputs

## Input Schema

Each partition record should include:

- `partition_id`
- `file_count`
- `avg_file_size_mb`
- `delete_file_count`
- `delete_ratio`
- `avg_delete_file_size_mb`
- `partition_access_frequency`
- `small_files_count`

## Models

### Performance Penalty

Small-file pressure and delete pressure are combined, then weighted by access frequency.

### Compaction Cost

The assignment uses:

$$
\text{Cost}_i = \text{file\_count}_i \times \text{avg\_file\_size\_mb}_i \times \text{avg\_delete\_file\_size\_mb}_i \times 0.001
$$

## How to Run

```bash
python compaction_optimizer.py --input data/partitions.json --mode exact \
  --output-json outputs/summary.json \
  --output-csv outputs/selected.csv \
  --output-plot outputs/results_chart.png
```

## Output Files

- `outputs/summary.json` - run summary and selected partitions
- `outputs/selected.csv` - row-wise selected partition metrics
- `outputs/results_chart.png` - simulation chart

## Notes

- `exact` mode uses 0/1 knapsack DP for an optimal budgeted selection.
- `greedy` mode uses efficiency-ratio ranking as a fast baseline.