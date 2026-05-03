# 📦 Datazip Assignment: Cost-Aware Compaction Strategy for Apache Iceberg

## 🧠 Assignment Ek Line Mein

> 20 partitions mein se kaunhe compact karo — taaki **3000 minutes ke budget** mein **maximum performance gain** mile.

---

## 📚 Table of Contents

1. [Background: Problem Samjho](#1-background-problem-samjho)
2. [Input Data: Kya Milega](#2-input-data-kya-milega)
3. [Kya Banana Hai: Deliverables](#3-kya-banana-hai-deliverables)
4. [Kaise Banana Hai: Step-by-Step Plan](#4-kaise-banana-hai-step-by-step-plan)
5. [Math & Formulas](#5-math--formulas)
6. [Algorithm Design](#6-algorithm-design)
7. [Tech Stack & Tools](#7-tech-stack--tools)
8. [Project Folder Structure](#8-project-folder-structure)
9. [Bonus Explorations](#9-bonus-explorations)
10. [Evaluation Criteria](#10-evaluation-criteria)

---

## 1. Background: Problem Samjho

Apache Iceberg ek large-scale data storage system hai. Isme data **partitions** mein store hota hai (e.g., ek din ka log data = ek partition).

### Problem kya hai?

Time ke saath:
- Har partition mein **bahut saari choti-choti files** ban jaati hain
- Ye choti files queries ko **slow aur costly** banati hain
- **Delete files** bhi accumulate hoti hain jo reads ko aur slow karti hain

### Solution kya hai?

**Compaction** = Choti files ko merge karke badi optimized files banana.

### Lekin challenge kya hai?

| Constraint | Detail |
|---|---|
| Compaction karna costly hai | Compute time + resources lagte hain |
| Budget limited hai | Sirf **3000 minutes (50 compute hours)** per day |
| Sab partitions equal nahi hain | Kuch zyada accessed hain, kuch zyada degraded hain |

**Tumhara kaam:** Decide karo ki **kaunse partitions compact karo** taaki budget ke andar maximum performance gain ho.

---

## 2. Input Data: Kya Milega

JSON file mein **20 partitions** ka data milega. Har partition ke liye ye fields honge:

| Field | Description | Role in Model |
|---|---|---|
| `file_count` | Partition mein total files ki count | Cost calculate karne mein |
| `avg_file_size_mb` | Files ki average size (MB mein) | Small file penalty + cost |
| `delete_file_count` | Logical deletions ki count | Delete penalty calculate karne mein |
| `delete_ratio` | `delete_file_count / file_count` | Threshold check karne mein |
| `avg_delete_file_size_mb` | Delete files ki average size | Cost + penalty mein |
| `partition_access_frequency` | Kitni baar ye partition query hota hai | Access-weighted penalty |
| `small_files_count` | 128MB se choti files ki count | Small file penalty |

### Sample JSON Structure:
```json
[
  {
    "partition_id": "p_001",
    "file_count": 120,
    "avg_file_size_mb": 45.2,
    "delete_file_count": 30,
    "delete_ratio": 0.25,
    "avg_delete_file_size_mb": 12.5,
    "partition_access_frequency": 85,
    "small_files_count": 95
  },
  ...
]
```

---

## 3. Kya Banana Hai: Deliverables

Assignment mein **3 cheezein** submit karni hain:

---

### ✅ Deliverable 1: Optimization Model Design (Mandatory)

Ye ek written document/notebook hoga jisme tum define karoge:

#### A) Performance Penalty Function
- Har partition ko ek **penalty score** do
- Score batata hai: "Ye partition kitna performance degrade kar raha hai?"
- High penalty = compact karna zyada zaroori

#### B) Compaction Cost Model
- Har partition ke liye **cost calculate karo** (minutes mein)
- Formula diya gaya hai (neeche dekho)

#### C) Selection Algorithm / Ranking Logic
- Decide karo ki **kaunse partitions select karo** budget ke andar
- Explain karo ki algorithm kaise decide karta hai

---

### ✅ Deliverable 2: Python Code Simulation (Bonus — but IMPORTANT for job)

Ek Python script/notebook banao jo:
1. JSON data load kare
2. Har partition ka penalty + cost calculate kare
3. Greedy selection algorithm run kare
4. Output de:
   - ✅ Kaunse partitions compact hue
   - 💰 Total cost used (minutes mein)
   - 📈 Expected performance gain
   - ❌ Kaunse skip hue aur kyun

---

### ✅ Deliverable 3: Slides ya 1-Pager (Mandatory)

Ek clean summary document (PDF/PPT/Notion) jisme:
- Tumhara approach explain ho
- Tradeoffs discussed hon
- Simulation results hon (charts/tables ke saath)

---

## 4. Kaise Banana Hai: Step-by-Step Plan

### Step 1: Data Load Karo
```python
import json
import pandas as pd

with open('partitions.json', 'r') as f:
    data = json.load(f)

df = pd.DataFrame(data)
print(df.head())
```

---

### Step 2: Performance Penalty Calculate Karo

Har partition ke liye ek **penalty score** banao jo 3 cheezein consider kare:

```
Penalty = (Small File Penalty + Delete Penalty) × Access Weight

Small File Penalty  = small_files_count / avg_file_size_mb
Delete Penalty      = delete_file_count × avg_delete_file_size_mb
Access Weight       = partition_access_frequency (normalized)
```

```python
def calculate_penalty(row):
    small_file_penalty = row['small_files_count'] / (row['avg_file_size_mb'] + 1e-6)
    delete_penalty = row['delete_file_count'] * row['avg_delete_file_size_mb']
    access_weight = row['partition_access_frequency']
    return (small_file_penalty + delete_penalty) * access_weight

df['penalty'] = df.apply(calculate_penalty, axis=1)
```

---

### Step 3: Compaction Cost Calculate Karo

Assignment ne formula diya hai:

```
Cost (minutes) = file_count × avg_file_size_mb × avg_delete_file_size_mb × 0.001
```

```python
COST_FACTOR = 0.001

def calculate_cost(row):
    return row['file_count'] * row['avg_file_size_mb'] * row['avg_delete_file_size_mb'] * COST_FACTOR

df['compaction_cost'] = df.apply(calculate_cost, axis=1)
```

---

### Step 4: Efficiency Score Calculate Karo

Best partitions wo hain jinki **penalty/cost ratio** sabse high ho (maximum gain, minimum cost):

```python
df['efficiency_score'] = df['penalty'] / df['compaction_cost']
df_sorted = df.sort_values('efficiency_score', ascending=False)
```

---

### Step 5: Greedy Selection Algorithm

Budget ke andar best partitions chunna (Classic **Fractional Knapsack** approach):

```python
BUDGET_MINUTES = 3000  # 50 compute hours

selected = []
total_cost = 0
total_gain = 0

for _, row in df_sorted.iterrows():
    if total_cost + row['compaction_cost'] <= BUDGET_MINUTES:
        selected.append(row['partition_id'])
        total_cost += row['compaction_cost']
        total_gain += row['penalty']

print(f"Selected Partitions: {selected}")
print(f"Total Cost Used: {total_cost:.2f} minutes")
print(f"Total Performance Gain: {total_gain:.2f}")
print(f"Budget Remaining: {BUDGET_MINUTES - total_cost:.2f} minutes")
```

---

### Step 6: Results Visualize Karo

```python
import matplotlib.pyplot as plt

# Bar chart: penalty vs cost per partition
fig, ax = plt.subplots(1, 2, figsize=(14, 5))

df.plot.bar(x='partition_id', y='penalty', ax=ax[0], title='Performance Penalty per Partition')
df.plot.bar(x='partition_id', y='compaction_cost', ax=ax[1], title='Compaction Cost per Partition', color='orange')

plt.tight_layout()
plt.savefig('results.png')
plt.show()
```

---

## 5. Math & Formulas

### Performance Penalty Function

$$\text{Penalty}_i = \left(\frac{\text{small\_files\_count}_i}{\text{avg\_file\_size\_mb}_i} + \text{delete\_file\_count}_i \times \text{avg\_delete\_file\_size\_mb}_i\right) \times \text{partition\_access\_frequency}_i$$

| Component | Intuition |
|---|---|
| `small_files_count / avg_file_size_mb` | Choti files hain + average size bhi choti → penalty high |
| `delete_file_count × avg_delete_file_size_mb` | Zyada deletes = reads slow |
| `× partition_access_frequency` | Zyada access = penalty ka impact zyada |

### Compaction Cost Formula

$$\text{Cost}_i = \text{file\_count}_i \times \text{avg\_file\_size\_mb}_i \times \text{avg\_delete\_file\_size\_mb}_i \times 0.001$$

### Efficiency Score (Selection Criterion)

$$\text{Score}_i = \frac{\text{Penalty}_i}{\text{Cost}_i}$$

### Selection Constraint

$$\sum_{i \in \text{Selected}} \text{Cost}_i \leq 3000 \text{ minutes}$$

---

## 6. Algorithm Design

### Algorithm: Greedy Knapsack

```
INPUT:  20 partitions with penalty and cost
OUTPUT: Set of partitions to compact

1. Calculate penalty(i) for each partition
2. Calculate cost(i) for each partition
3. Calculate score(i) = penalty(i) / cost(i)
4. Sort partitions by score (descending)
5. budget_remaining = 3000
6. FOR each partition in sorted order:
     IF cost(i) <= budget_remaining:
         SELECT partition i
         budget_remaining -= cost(i)
7. RETURN selected partitions
```

### Why Greedy?

- **Simple aur fast** — O(n log n) complexity
- **Optimal for continuous knapsack** — mathematically provable
- **Interpretable** — kisi ko bhi explain karna easy hai

### Alternative Approaches (Mention in Report):

| Approach | Pros | Cons |
|---|---|---|
| Greedy (recommended) | Fast, simple, near-optimal | Not always globally optimal |
| Dynamic Programming | Globally optimal (0/1 knapsack) | Slow for large datasets |
| Linear Programming | Exact solution | Complex to implement |
| ML-based Scoring | Learns from historical data | Needs labeled training data |

---

## 7. Tech Stack & Tools

### Required:
```
Python 3.8+
pandas          — data manipulation
json            — input data parsing
matplotlib      — visualization
seaborn         — better charts (optional)
```

### Installation:
```bash
pip install pandas matplotlib seaborn
```

### Optional (for bonus):
```
scipy           — optimization functions
scikit-learn    — ML-based threshold learning
jupyter         — notebook presentation
plotly          — interactive charts
```

---

## 8. Project Folder Structure

```
datazip-compaction-assignment/
│
├── README.md                    ← Ye file (project overview)
│
├── data/
│   └── partitions.json          ← Input dataset (20 partitions)
│
├── src/
│   ├── penalty.py               ← Penalty function
│   ├── cost.py                  ← Cost model
│   ├── selector.py              ← Greedy selection algorithm
│   └── visualize.py             ← Charts and plots
│
├── notebooks/
│   └── compaction_analysis.ipynb ← Full Jupyter notebook walkthrough
│
├── outputs/
│   ├── selected_partitions.csv   ← Final selection results
│   ├── results_chart.png         ← Visualization
│   └── summary_report.pdf        ← 1-pager / slides
│
└── requirements.txt              ← Python dependencies
```

---

## 9. Bonus Explorations

Agar time ho toh ye bhi add karo — extra marks milenge:

### Bonus 1: Dynamic Weekly Scheduling
- Har din ka budget alag ho sakta hai
- Week ke across partitions schedule karo
- Rolling window approach use karo

### Bonus 2: Threshold Learning from Data
- `delete_ratio_threshold` aur `min_file_size_mb` ko data se seekho
- Percentile-based thresholds use karo:
  ```python
  delete_threshold = df['delete_ratio'].quantile(0.75)  # Top 25% compact karo
  ```

### Bonus 3: Real-World Analogy
Ye problem **CPU cache eviction** jaisi hai:
- Cache = budget
- Cache lines = partitions  
- Eviction policy = compaction selection
- LRU/LFU = greedy by recency/frequency

Similar problems in:
- **CDN cache management** — kaunsi content cache mein rakho
- **Load balancing** — kaunse servers ko scale karo
- **Database index maintenance** — kaunse indexes rebuild karo

---

## 10. Evaluation Criteria

| Criteria | Weightage | Kaise Impress Karo |
|---|---|---|
| Model clarity & rigor | High | Clean math, clear formulas define karo |
| Cost vs. performance reasoning | High | Tradeoffs explicitly discuss karo |
| Compaction triggering logic | High | Thresholds explain karo (delete_ratio, file_size) |
| Communication quality | High | Clean slides, charts, readable code |
| Code quality (bonus) | Bonus | Modular code, comments, test cases |

---

## 🚀 Quick Start: Kahan Se Shuru Karo?

```
Day 1:  Assignment padho → JSON data download karo → pandas mein load karo
Day 2:  Penalty function likho → Cost function likho → Test karo
Day 3:  Greedy algorithm implement karo → Results nikalo
Day 4:  Visualizations banao → 1-pager/slides prepare karo
Day 5:  Review, clean up code, README finalize karo
```

---

## 📌 Key Numbers to Remember

| Parameter | Value |
|---|---|
| Daily Budget | **3000 minutes (50 hours)** |
| Small File Threshold | **128 MB** |
| Cost Factor | **0.001** |
| Cost Formula | `file_count × avg_file_size_mb × avg_delete_file_size_mb × 0.001` |
| Total Partitions | **20** |

---

*Assignment by Datazip | Designed to test optimization thinking, data modeling, and communication skills.*
