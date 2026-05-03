# Cost-Aware Compaction Strategy for Apache Iceberg

This submission is based on the assignment prompt in [DATAZIP ASSIGNMENT 1.pdf](DATAZIP%20ASSIGNMENT%201.pdf) and the implementation hints in [README (9).md](README%20%289%29.md).

## 1. Problem Statement

We have 20 Iceberg partitions. Each partition accumulates small files and delete files over time, which increases query latency. The goal is to select a subset of partitions to compact so that the total compaction cost stays within a daily budget of 3000 minutes while the expected performance gain is maximized.

## 2. Data Signals Used

The model uses the fields described in the prompt and README:

- `file_count`
- `avg_file_size_mb`
- `delete_file_count`
- `delete_ratio`
- `avg_delete_file_size_mb`
- `partition_access_frequency`
- `small_files_count`

The strongest signals are small-file pressure, delete pressure, and how often the partition is queried.

## 3. Performance Penalty Model

The performance penalty is a proxy for query-time degradation.

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

This keeps the model interpretable while still emphasizing partitions that are both degraded and frequently read.

## 4. Compaction Cost Model

The assignment provides the cost formula directly:

$$
\text{cost}_i = \text{file\_count}_i \times \text{avg\_file\_size\_mb}_i \times \text{avg\_delete\_file\_size\_mb}_i \times 0.001
$$

This cost is measured in minutes, and the daily budget is 3000 minutes.

## 5. Selection Logic

Because only 20 partitions are involved, the problem can be treated as a 0/1 knapsack optimization problem.

Objective:

$$
\max \sum_i x_i \cdot \text{penalty}_i
$$

Subject to:

$$
\sum_i x_i \cdot \text{cost}_i \le 3000
$$

and

$$
x_i \in \{0,1\}
$$

The implementation in [compaction_optimizer.py](compaction_optimizer.py) solves this with dynamic programming on scaled minutes, which gives an exact solution after discretization. A greedy score is also included for comparison and quick experimentation.

## 6. Why This Is Better Than Plain Greedy

The README suggests a greedy ratio ranking. That is a good baseline, but it is not guaranteed to be globally optimal. Since the dataset is small, an exact budgeted optimizer is better:

- It respects the budget strictly.
- It finds the best combination of partitions rather than only the best individual ratios.
- It remains easy to explain because the objective is still a simple penalty-to-cost tradeoff.

## 7. Complexity

Let $n$ be the number of partitions and $B$ be the budget after scaling.

- Greedy ranking: $O(n \log n)$
- Exact dynamic programming: $O(nB)$

For $n=20$, the exact version is practical and provides a stronger result.

## 8. Deliverable Summary

The final submission should contain:

- A clear explanation of the penalty model.
- A clear explanation of the cost model.
- A budget-constrained selection algorithm.
- A code simulation that prints selected partitions, total cost, and expected gain.
- A short slide or one-pager summarizing the tradeoff.

## 9. How to Run

1. Place the input JSON at `data/partitions.json`.
2. Run the optimizer script.
3. Export the printed JSON summary into the report or slides.

Example:

```bash
python compaction_optimizer.py --input data/partitions.json --mode exact --output-json outputs/summary.json --output-csv outputs/selected.csv
```

## 10. Final Position

This solution is intentionally simple to explain, but strong enough to justify in an interview or assignment review:

- It uses the data fields in the prompt.
- It keeps cost within budget.
- It prioritizes partitions with high degradation and high query frequency.
- It improves on the README baseline by using exact optimization when possible.