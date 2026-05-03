# Cost-Aware Compaction Strategy for Apache Iceberg

An optimizer to decide which partitions in an Apache Iceberg table should be compacted to maximize query performance improvement while staying within a 3000-minute daily compute budget.

## Problem Summary

Apache Iceberg tables accumulate many small files and delete files over time. That increases read overhead and query latency. Compaction rewrites those files into fewer, larger files, but compaction itself costs compute time.

The assignment asks for an optimization strategy that:
- estimates the performance penalty of each partition,
- estimates the compaction cost of each partition,
- selects partitions to compact under a fixed budget,
- and explains the tradeoff clearly in a report or slides.

## Input Data

The input dataset is a JSON array of 20 partitions. Each partition record contains:

- `partition_id`
- `file_count`
- `avg_file_size_mb`
- `delete_file_count`
- `delete_ratio`
- `avg_delete_file_size_mb`
- `partition_access_frequency`
- `small_files_count`

Example record:

```json
{
  "partition_id": "p_001",
  "file_count": 120,
  "avg_file_size_mb": 45.2,
  "delete_file_count": 30,
  "delete_ratio": 0.25,
  "avg_delete_file_size_mb": 12.5,
  "partition_access_frequency": 85,
  "small_files_count": 95
}
```

## Repository Contents

- `compaction_optimizer.py` - main executable entrypoint
- `src/penalty.py` - penalty model and partition dataclass
- `src/cost.py` - compaction cost model
- `src/selector.py` - enrichment and greedy selection logic
- `src/visualize.py` - chart generation utilities
- `data/partitions.json` - provided input dataset
- `outputs/` - generated summary JSON, CSV, and chart image
- `assignment_solution.md` - write-up version of the solution
- `DATAZIP ASSIGNMENT 1.pdf` - original assignment prompt

## Modeling Approach

### 1) Performance Penalty

The penalty model combines three signals:
- small file pressure
- delete file pressure
- query access frequency

The score used in the implementation is:

$$
\text{small\_file\_pressure}_i = \frac{\text{small\_files\_count}_i}{\max(\text{avg\_file\_size\_mb}_i, \epsilon)}
$$

$$
\text{delete\_pressure}_i = \text{delete\_file\_count}_i \times \text{avg\_delete\_file\_size\_mb}_i
$$

$$
\text{access\_weight}_i = \frac{\text{partition\_access\_frequency}_i}{\max_j(\text{partition\_access\_frequency}_j)}
$$

$$
\text{penalty}_i = (\text{small\_file\_pressure}_i + \text{delete\_pressure}_i) \times (1 + \text{access\_weight}_i)
$$

This keeps the model interpretable while emphasizing partitions that are both degraded and frequently queried.

### 2) Compaction Cost

The assignment specifies the cost formula in minutes:

$$
\text{cost}_i = \text{file\_count}_i \times \text{avg\_file\_size\_mb}_i \times \text{avg\_delete\_file\_size\_mb}_i \times 0.001
$$

### 3) Selection Strategy

Two selection modes are supported:

- `exact`: 0/1 knapsack dynamic programming, globally optimal for the scaled budget problem
- `greedy`: efficiency ratio ranking, used as a fast baseline

The efficiency score is:

$$
\text{score}_i = \frac{\text{penalty}_i}{\text{cost}_i}
$$

## Why Exact Selection Is Used

The dataset contains only 20 partitions, so an exact 0/1 knapsack solution is practical and gives a stronger result than greedy-only ranking.
Greedy is still included for comparison and experimentation.

## How the Script Works

1. Load the JSON dataset.
2. Convert each row into a typed partition object.
3. Compute penalty and cost for every partition.
4. Rank or optimize partitions under the budget.
5. Save the results to JSON, CSV, and a chart image.

## How to Run

Install dependencies first:

```bash
pip install -r requirements.txt
```

Run the optimizer:

```bash
python compaction_optimizer.py --input data/partitions.json --mode exact \
  --output-json outputs/summary.json \
  --output-csv outputs/selected.csv \
  --output-plot outputs/results_chart.png
```

To compare with the greedy baseline:

```bash
python compaction_optimizer.py --input data/partitions.json --mode greedy \
  --output-json outputs/summary.json \
  --output-csv outputs/selected.csv \
  --output-plot outputs/results_chart.png
```

## Output Files

The script writes these artifacts:

- `outputs/summary.json` - full run summary, selected partitions, and budget usage
- `outputs/selected.csv` - row-wise details for selected partitions
- `outputs/results_chart.png` - 4-panel visualization of penalties, costs, efficiency, and budget usage

## Result on the Provided Dataset

Using the provided `data/partitions.json`, the exact mode produced:

- Selected partitions: 20
- Skipped partitions: 0
- Total compaction cost: 733.5877 minutes
- Budget remaining: 2266.4123 minutes
- Expected performance gain: 19756.3569

That means every partition fits within the daily budget under the current scoring model, so all 20 partitions are selected.

## Project Structure

```text
.
├── compaction_optimizer.py
├── README.md
├── assignment_solution.md
├── requirements.txt
├── DATAZIP ASSIGNMENT 1.pdf
├── data/
│   └── partitions.json
├── outputs/
│   ├── selected.csv
│   ├── summary.json
│   └── results_chart.png
└── src/
    ├── __init__.py
    ├── cost.py
    ├── penalty.py
    ├── selector.py
    └── visualize.py
```

## Notes

- `src/penalty.py` contains the shared `PartitionMetrics` dataclass.
- `src/cost.py` keeps the cost model separate from the main script.
- `src/selector.py` handles enrichment and greedy ranking.
- `src/visualize.py` saves the final chart image.
- The root script remains the main entrypoint so the project is easy to run from the command line.

## What's Included

- Optimization model with penalty and cost calculations
- 0/1 knapsack exact solver plus greedy baseline
- Full data pipeline with typed partition objects
- 4-panel visualization with status indicators
- JSON, CSV, and image outputs
- Complete source code and test dataset
