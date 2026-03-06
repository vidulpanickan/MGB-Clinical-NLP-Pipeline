# Medical/Biobank Data ETL Processor

A Python-based ETL (Extract, Transform, Load) script that processes batches of medical or biobank data. It takes raw patient records containing clinical codes, cleans the data, calculates code frequency per patient on daily and monthly bases, and maps codes to broader parent categories for a summarized rollup view.

---

## What It Does

### 1. Setup and Ingestion

- **Batch argument:** Requires a `--batch` number (e.g., `29`) to identify which file to process. Optional arguments include paths for input, output, and mapping directories.
- **Input format:** Reads a pipe-separated (`|`) CSV file with at least three columns: `EMPI` (unique patient identifier), `date`, and `cui` (Concept Unique Identifier — standardized medical codes).

### 2. Data Cleaning & Transformation

- **Date formatting:** Converts dates to `YYYY-MM-DD` format; drops rows with invalid or missing dates.
- **Exploding codes:** Splits rows where a patient has multiple comma-separated CUIs (e.g., `C0001, C0002`) so each code gets its own row.
- **Filtering:** Keeps only CUIs ending in `"Y"`, then strips the trailing `"Y"` from each code.

### 3. Base Aggregations

| Output File | Description |
|---|---|
| `daily_batch_<N>.csv` | One record per patient per CUI per day (duplicates removed) |
| `month_batch_<N>.csv` | Count of distinct days per month a patient had each CUI |

### 4. Rollup Aggregations

- **Mapping:** Loads a mapping file to translate specific "Child" CUIs to broader "Parent/Rollup" CUIs. Codes without a parent map to themselves.
- **Year-by-year processing:** Rollups are processed one year at a time to conserve memory.

| Output File | Description |
|---|---|
| `rollup_daily_batch_<N>.csv` | One record per patient per parent category per day |
| `rollup_month_batch_<N>.csv` | Count of days per month a patient triggered each parent category |

### 5. Logging and Error Handling

- Generates a structured log file (`processing_batch<N>.log`) recording row counts at each pipeline stage: input rows, rows after cleaning, and final output rows.
- On failure, the error reason is written to the log and a full traceback is printed for capture by job schedulers (e.g., Slurm).

---

## Usage

```bash
python etl_processor.py --batch 29
```

### Arguments

| Argument | Required | Description |
|---|---|---|
| `--batch` | Yes | Batch number to process (e.g., `29`) |
| `--input-dir` | No | Path to input data directory |
| `--output-dir` | No | Path to output directory |
| `--mapping-dir` | No | Path to CUI mapping files directory |

---

## Output Files

| File | Description |
|---|---|
| `daily_batch_<N>.csv` | Deduplicated daily patient-CUI records |
| `month_batch_<N>.csv` | Monthly aggregation of daily CUI records |
| `rollup_daily_batch_<N>.csv` | Daily records rolled up to parent CUI categories |
| `rollup_month_batch_<N>.csv` | Monthly aggregation of rollup daily records |
| `processing_batch<N>.log` | Row counts and error messages for each pipeline stage |


