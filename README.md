# MGB Clinical NLP Pipeline Roadmap

Turn **raw clinical notes** into **patient‑level UMLS concept counts**, rolled up to
parent concepts. The NLP tool used is **NILE** (Narrative Information Linear Extraction, a
Java‑based clinical NLP tool from the CELEHS lab at Harvard). This is the single
document to read before running on **ERISTwo** (CentOS HPC, SLURM) or a **BWH local
compute machine** (Windows / Linux, no scheduler).

> **How to use this doc:** go to **[§1 Pick your path](#1-pick-your-path)** first — it routes you to the
> exact steps for your data. Everything converges on **[§7 Common downstream](#7-common-downstream--batch--count--roll-up)**.

---

## 1. Pick your path

**The pipeline is chosen by two things: *where the data lives* and *what format it's in*.**
Find your row, follow the section.

```
WHERE IS YOUR DATA + WHAT FORMAT?
│
├─ A ─ RPDR notes  (folders of .txt files, pipe‑delimited, [report_end] blocks)
│      │
│      ├─ A1  Small patient set ............... run NILE directly, then post‑process        → §4.1
│      ├─ A2  Full Biobank (very large) ....... run NILE as an array, batch, post‑process    → §4.2
│      └─ A3  Biobank subset (some patients) .. EXTRACT those patients first, then A1        → §4.3
│
├─ B ─ Database notes  (SQL Server, e.g. RAProd5) — one pipeline: NILE connects & reads
│      │                                                                                       
│      ├─ B1  From a Windows machine on the BWH network ...............................       → §5.1
│      └─ B2  From ERISTwo HPC .......................................................         → §5.2
│
└─ C ─ Flat‑file notes  (CSV, or other text export)
       └─ normalize to the CSV layout, then run NILE, then post‑process                       → §6
```

| Path | Data | Size | What you run | Section |
|------|------|------|--------------|---------|
| **A1** | RPDR folders | small | NILE directly → post‑process | §4.1 |
| **A2** | RPDR folders (Biobank) | huge | `run_nile_on_all.sbatch` → `make_batches.sbatch` → post‑process | §4.2 |
| **A3** | RPDR folders, subset of patients | any | `extract_biobank_notes.sbatch` → then A1 | §4.3 |
| **B1** | SQL Server | any | `NILEDatabaseProcessor` from Windows (BWH) | §5.1 |
| **B2** | SQL Server | any | `NILEDatabaseProcessor` from ERISTwo | §5.2 |
| **C**  | CSV / flat file | any | `NILECSVProcessor` → post‑process | §6 |

**All paths produce the same thing** — NILE output where every concept is a **UMLS CUI**
tagged **present (`Y`)** or **negated (`N`)** — and then flow through the same
downstream (**[§7](#7-common-downstream--batch--count--roll-up)**): keep present → count per patient per day/month → roll up to parent CUIs.

```
                                              ┌──────────── §7 COMMON DOWNSTREAM ───────────┐
 A / B / C  ──►  NILE  ──►  CUIs + Y/N   ──►  │  keep Y → daily/monthly counts → roll up    │
                (§2 bundle)  (raw output)     │  to parent CUIs via global rollup dictionary │
                                              └──────────────────────────────────────────────┘
```

> **Two "dictionaries" — do not confuse them.**
> • **NILE dictionary** — `NILE/NER_dictionary.txt` (`term|CUI`, ~87 MB, ships in the bundle). Used *inside* NILE to find CUIs in text.
> • **Global CUI‑rollup dictionary** — `GLOBAL_CUI_ROLLUP_*.csv` (`CHILD_CUI,ROLLUP_CUI`). Used at the very end to aggregate child CUIs to parents.

---

## 2. The NILE bundle — compile once, everyone runs

NILE lives in **`refactored-nile-processing-main/`**. The goal: **compile it one time,
keep the compiled classes + dictionary + jars together in this folder, and share the
whole folder** so collaborators *just run* — no compiling on ERISTwo, ever.

```
refactored-nile-processing-main/
├─ NILE/
│  ├─ NILERPDRProcessor.java     + .class   ← compiled once, shipped
│  ├─ NILECSVProcessor.java      + .class
│  ├─ NILEDatabaseProcessor.java + .class
│  ├─ NILEParquetProcessor.java  + .class
│  ├─ NER_dictionary.txt                    ← the NILE dictionary (term|CUI, ~87 MB)
│  ├─ NLPproperties.txt                     ← DB connection template (Path B)
│  ├─ sqljdbc_auth/                         ← Windows SQL auth DLL (Path B1)
│  └─ lib/                                  ← all jars (nile_20.jar, opencsv, parquet, jdbc…)
├─ data/            example_rpdr.txt · example_csv.csv · example_parquet.parquet
└─ scripts/         compile.sh · run.sh · build-classpath.sh
```

### Build the shareable bundle (do this ONCE, on a Java‑20 machine)

Java bytecode is portable, so compiling once on any JDK 20 works everywhere with a JDK 20+
runtime. Do it on ERISTwo (which has JDK 20) or any box with JDK 20 installed.

```bash
cd refactored-nile-processing-main
# compile all four processors in one go (writes NILE/*.class next to the sources):
bash scripts/compile.sh all
# — or compile just what you need, e.g. RPDR + CSV:
bash scripts/compile.sh rpdr
bash scripts/compile.sh csv
```

`scripts/compile.sh` picks the right classpath per processor automatically. If you'd
rather do it by hand:

```bash
JAVAC=/apps/lib/java/jdk-20.0.2/bin/javac       # ERISTwo path; or your local JDK 20
$JAVAC -cp ".:NILE/lib/nile_20.jar" NILE/NILERPDRProcessor.java
$JAVAC -cp ".:NILE/lib/nile_20.jar:NILE/lib/opencsv-5.12.0.jar:NILE/lib/commons-lang3-3.12.0.jar:NILE/lib/commons-collections4-4.4.jar" NILE/NILECSVProcessor.java
```

**Verify, then share:** confirm `NILE/*.class` exist, then hand off the whole
`refactored-nile-processing-main/` folder (classes included). Collaborators need **only a
JDK 20 runtime** — no `javac`, no recompiling.

> `scripts/compile.sh` currently hard‑codes a macOS JDK path
> (`/Library/Java/JavaVirtualMachines/jdk-20.jdk/...`). On ERISTwo, either edit
> `JAVA_20_BIN` in `scripts/build-classpath.sh` to `/apps/lib/java/jdk-20.0.2/bin`, or
> just use the manual `javac` line above.

---

## 3. Prerequisites

| Need | ERISTwo (CentOS HPC) | BWH local machine |
|------|----------------------|-------------------|
| **Java 20 runtime** (to *run* NILE) | `/apps/lib/java/jdk-20.0.2/bin/java` | Install JDK 20+; `java -version` must show `20` and `64‑Bit` |
| **The NILE bundle** (§2, with `.class` built) | Copy `refactored-nile-processing-main/` into your project dir | Same folder, copied locally |
| **Python env** (`pandas`, `pyarrow`, `numpy`) for post‑processing | `module load conda && conda activate nlp` | `conda create -n nlp python=3.11 pandas pyarrow numpy` |
| **Global CUI‑rollup dictionary** | `…/BIOBANK_CUI_COUNTS/get_rollup/GLOBAL_CUI_ROLLUP_UMLS2021AB_VID_13MAY2025.csv` | copy locally |
| **SLURM** | yes — `sbatch` | no — use the plain‑bash variants shown per path |

> Run NILE from the folder that **contains** `NILE/`, and always launch classes with the
> package prefix: `NILE.NILERPDRProcessor` (not `NILERPDRProcessor`).

---

## 4. Path A — RPDR notes

**Format:** pipe‑delimited `.txt`, one or more per folder, header
`EMPI|EPIC_PMRN|MRN_Type|MRN|Report_Number|Report_Date_Time|Report_Description|Report_Status|Report_Type|Report_Text`,
each report block terminated by `[report_end]`.

### 4.1 — Small patient set → run NILE directly

Best when you have a handful of RPDR files / patients. No array job, no 155‑way batching.

```bash
cd refactored-nile-processing-main
JAVA=/apps/lib/java/jdk-20.0.2/bin/java        # or your local JDK 20
DICT=NILE/NER_dictionary.txt

# run NILE on each RPDR file:
for f in /path/to/rpdr_notes/*.txt; do
  "$JAVA" -cp ".:NILE/lib/nile_20.jar" NILE.NILERPDRProcessor \
      --dictionary-path "$DICT" \
      --input-rpdr "$f" \
      --output-csv "out/$(basename "${f%.txt}").csv"
done

# combine into one file and treat it as batch 1 for post-processing:
cat out/*.csv | grep -v '^EMPI|EPIC_PMRN|Report_Date_Time' > BATCHED_DATA/batch_1.csv
```

Then post‑process a single batch — **[§7](#7-common-downstream--batch--count--roll-up)** with `--batch 1`.

### 4.2 — Full Biobank (very large) → array + batch

The Biobank notes are split across 17 folders (`part_01 … part_17`). Run NILE as a SLURM
array (one task per folder), then batch by patient, then post‑process.

```bash
# 1) NILE on all 17 folders in parallel  (writes Raw_NILE_output/*.csv)
sbatch run_nile_on_all.sbatch                       # #SBATCH --array=1-17
sbatch --export=ALL,FORCE=1 run_nile_on_all.sbatch  # reprocess from scratch (e.g. new dictionary)

# 2) split all NILE output into 155 patient-keyed batches (one pass)
sbatch make_batches.sbatch                          # → BATCHED_DATA/batch_1..155.csv + id_to_batch.csv

# 3) count + roll up every batch — see §7
```

- `run_nile_on_all.sbatch`: validates each file's header, skips already‑finished files
  (resumable), writes to `.partial` and renames only on success, logs `[OK]/[FAIL]`.
- `make_batches.sbatch`: batches by `EMPI % 155` so **every row for a patient stays in one
  batch** (required for correct per‑patient counts); also writes an `id_to_batch.csv` audit table.

### 4.3 — Biobank subset (some patients) → extract, then run NILE

When you need just a cohort out of the huge Biobank set, **extract those patients' notes
first**, then treat the result as a small set (§4.1).

```bash
# edit ROOT_DIR / IDS_FILE / OUTPUT_DIR / KEYPOS at the top of the script, then:
sbatch extract_biobank_notes.sbatch      # calls rpdr_note_extract.sh under the hood
# single machine (no SLURM):
./rpdr_note_extract.sh "$ROOT_DIR" "$IDS_FILE" "$OUTPUT_DIR" 1
```

- `IDS_FILE`: one patient ID per line.
- `KEYPOS`: which ID column to match — **1 = EMPI, 2 = EPIC_PMRN, 4 = MRN**.
- Output: extracted RPDR files for your cohort → run NILE on them via **§4.1**.

> **Already have NILE output and just want a cohort's rows?** Skip re‑running NILE:
> ```bash
> find "$ROOT_DIR" -type f -name '*.txt' -print0 \
>   | xargs -0 awk -F'|' 'NR==FNR{ids[$1]=1;next} ($1 in ids)' "$IDS_FILE" > "$OUT_FILE"
> ```

---

## 5. Path B — Database notes (SQL Server)

**One pipeline:** NILE connects to the SQL Server, reads notes directly, and writes
pipe‑delimited output. The *only* difference between B1 and B2 is **where you launch it
from** (both use `NILEDatabaseProcessor` and an `NLPproperties.txt` config).

**Configure once** — copy the template and fill it in (don't edit the shared original):

```bash
cp NILE/NLPproperties.txt NILE/NLPproperties_yourname.txt
# set: server, dbname, tablename, patientIDcol/docIDcol/datecolumn/notecolumn/notetype,
#      patstart/patend/patincrement (patient-ID range + batch size), notelengthlimit, outputfolder
# leave user/password BLANK to use integrated (Windows) auth
```

### 5.1 — From a Windows machine on the BWH network

Uses Windows integrated auth (connects *as you*), so your account needs DB access.

```bat
cd /d "D:\NLP_tools\LATEST_NILE\refactored-nile-processing-main"
java "-Djava.library.path=NILE\sqljdbc_auth" -cp ".;NILE\lib\*" NILE.NILEDatabaseProcessor "NILE\NLPproperties_yourname.txt"
```

- `-Djava.library.path=NILE\sqljdbc_auth` points at the **folder** with the auth DLL.
- Java must be **64‑bit** (`java -version` shows `64‑Bit`), or auth fails — see §9.
- Optional: dump the table to a flat file first with `bcp`, then run Path C instead:
  ```bat
  bcp "SELECT CAST(PATIENT_NUM AS varchar(50)) PATIENT_NUM, CAST(ENCOUNTER_NUM AS varchar(50)) ENCOUNTER_NUM, CONVERT(varchar(30),START_DATE,126) START_DATE, REPLACE(REPLACE(REPLACE(COALESCE(CONVERT(varchar(max),OBSERVATION_BLOB),''),CHAR(13),' '),CHAR(10),' '),CHAR(124),'') OBSERVATION_BLOB FROM [RA_Prod5].[dbo].[observation_fact_notes] WITH (NOLOCK)" queryout "\\...\raprod5_obs_text_full.txt" -c -t "|" -r 0x0a -a 16000 -T -S PHSQLRPDR322
  ```

### 5.2 — From ERISTwo HPC

Same processor, launched on the cluster (Linux classpath separator `:`, forward slashes):

```bash
cd refactored-nile-processing-main
/apps/lib/java/jdk-20.0.2/bin/java -cp ".:NILE/lib/*" NILE.NILEDatabaseProcessor NILE/NLPproperties_yourname.txt
```

- ERISTwo must be able to reach the SQL Server host/port, and the config must carry valid
  credentials (integrated Windows auth is a Windows‑only feature; on Linux set `user`/`password`).

**Output:** files named `batch_{patstart}_{patend}.csv`, pipe‑delimited
(`patient_id|doc_id|date|note_type|code_certainty`). Then go to **[§7](#7-common-downstream--batch--count--roll-up)**.

> ⚠️ **Column note:** the DB output has an extra `note_type` column, so the CUI codes are in
> the **5th** column, whereas post‑processing expects codes in the **4th**. Before §7, drop
> `note_type` (keep `patient_id|doc_id|date|code_certainty`) so codes land in column 4.

---

## 6. Path C — Flat‑file / CSV notes

For notes already exported as CSV (or any flat file you can shape into CSV). Target layout:

```
patient_num,encounter_num,start_date,notes
```

```bash
cd refactored-nile-processing-main
JAVA=/apps/lib/java/jdk-20.0.2/bin/java
CP=".:NILE/lib/nile_20.jar:NILE/lib/opencsv-5.12.0.jar:NILE/lib/commons-lang3-3.12.0.jar:NILE/lib/commons-collections4-4.4.jar"

"$JAVA" -cp "$CP" NILE.NILECSVProcessor \
  --dictionary-path NILE/NER_dictionary.txt \
  --input-csv data/notes.csv \
  --output-csv out/nile_out.csv
# column names differ? override: --patient-num-col --encounter-num-col --start-date-col --notes-col
```

**Output:** `patient_num|encounter_num|start_date|code_certainty` (codes already in column 4).
Treat it as a batch and go to **[§7](#7-common-downstream--batch--count--roll-up)**.

> **QC before running:** NILE can drop notes containing stray `"`, `\`, or `|`. Clean first:
> ```python
> df["notes"] = df["notes"].str.strip(r"\/").str.replace('"', "", regex=False)
> ```

---

## 7. Common downstream — batch → count → roll up

Every path lands here with NILE output whose 4th column is the comma‑separated CUI list
(`C0010054Y,C0013182N,…`). `Y` = present, `N` = negated.

**(Large sets only) batch by patient** — §4.2's `make_batches.sbatch` already did this.
For small sets, you made a single `batch_1.csv` in §4.1/§6.

**Count + roll up** — `generated_counts_rollup.py` (from `POSTPROCESS/`), per batch:

1. Clean dates → `YYYY-MM-DD`, drop bad rows.
2. Explode comma‑separated CUIs to one per row.
3. **Keep present only:** keep CUIs ending in `Y`, then strip the `Y`.
4. **Base counts:** `daily_batch_N.csv` (patient × CUI × day) · `month_batch_N.csv` (distinct days/month per CUI).
5. **Roll up:** left‑join each CUI → `ROLLUP_CUI` via the global rollup dictionary; **unmapped
   CUIs map to themselves**. Done year‑by‑year to bound memory. →
   `rollup_daily_batch_N.csv`, `rollup_month_batch_N.csv`.
6. **Log:** `processing_batch<N>.log` records row counts at every stage + `SUCCESS`/`FAILED`.

**ERISTwo (all 155 batches as an array):**
```bash
# process_nile_output.sbatch: #SBATCH --array=1-155 ; module load conda ; conda activate nlp
sbatch process_nile_output.sbatch
```

**Single machine / small set (loop, or just `--batch 1`):**
```bash
conda activate nlp
for b in $(seq 1 155); do            # or: for b in 1
  python3 generated_counts_rollup.py --batch "$b" \
    --input-dir  /path/to/BATCHED_DATA \
    --output-root /path/to/OUTPUT \
    --map-file   /path/to/GLOBAL_CUI_ROLLUP_UMLS2021AB_VID_13MAY2025.csv
done
```

Outputs land under `<output-root>/{DAILY,MONTH,ROLLUP,log}/`.

---

## 8. Output reference

**NILE raw output** (codes = present `Y` / negated `N`):

| Path | Columns |
|------|---------|
| RPDR (A) | `EMPI \| EPIC_PMRN \| Report_Date_Time \| Code_Certainties` |
| CSV (C)  | `patient_num \| encounter_num \| start_date \| code_certainty` |
| DB (B)   | `patient_id \| doc_id \| date \| note_type \| code_certainty` *(drop `note_type` before §7)* |

**Post‑process output** (one set per batch, under `OUTPUT/`):

| File | Grain | Columns |
|------|-------|---------|
| `DAILY/daily_batch_N.csv` | patient × CUI × day | `EMPI,date,cui` |
| `MONTH/month_batch_N.csv` | patient × CUI × month | `EMPI,month,cui,count` |
| `ROLLUP/rollup_daily_batch_N.csv` | patient × **parent** CUI × day | `EMPI,date,parent_cui` |
| `ROLLUP/rollup_month_batch_N.csv` | patient × **parent** CUI × month | `EMPI,month,parent_cui,count` |
| `log/processing_batch<N>.log` | — | per‑stage row counts + status |

`month` = `MM-YYYY`; `count` = distinct days in that month the patient had the concept.

---

## 9. Troubleshooting

| Symptom | Cause → Fix |
|---------|-------------|
| `Could not find or load main class NILERPDRProcessor` | Missing package prefix → `NILE.NILERPDRProcessor`, run from the dir containing `NILE/`. |
| Compiled on macOS, won't run on ERISTwo | Bytecode is portable — just needs a **JDK 20 runtime**. Check `java -version`. |
| Fewer notes in output than input | Stray `"` `\` `|` in text → clean (see §6 QC) and rerun (`FORCE=1` for A2). |
| `This driver is not configured for integrated authentication` (Path B1) | 32‑bit JVM **or** mismatched `mssql-jdbc` jar vs auth DLL → use 64‑bit JDK; keep only the matching jar in `NILE\lib`. |
| Post‑process puts wrong values in `cui` | Column misalignment — codes must be the **4th** column (drop DB `note_type`, §5). |
| Rollup job OOMs | Already year‑chunked; raise `#SBATCH --mem` or split the batch. |
| Patient's counts look doubled | Rows for one patient split across batches → batch on `EMPI % 155` (`make_batches.sbatch`); don't hand‑split. |
| `MISSING_MAP` in the log | `--map-file` path wrong → point at `GLOBAL_CUI_ROLLUP_*.csv`. |

---

## 10. Cheat sheet

```bash
# ── Path A2 · Full Biobank on ERISTwo ────────────────────────────────
sbatch run_nile_on_all.sbatch          # notes → CUIs        (array 1-17)
sbatch make_batches.sbatch             # → 155 patient batches
sbatch process_nile_output.sbatch      # counts + parent-CUI roll-ups (array 1-155)
sbatch --export=ALL,FORCE=1 run_nile_on_all.sbatch     # reprocess after dictionary change

# ── Path A1/A3 · Small set or subset (no scheduler) ──────────────────
sbatch extract_biobank_notes.sbatch    # (A3 only) pull a cohort's notes first
for f in notes/*.txt; do java -cp ".:NILE/lib/nile_20.jar" NILE.NILERPDRProcessor \
  --dictionary-path NILE/NER_dictionary.txt --input-rpdr "$f" --output-csv "out/$(basename "${f%.txt}").csv"; done
cat out/*.csv | grep -v '^EMPI|EPIC' > BATCHED_DATA/batch_1.csv
python3 generated_counts_rollup.py --batch 1 --input-dir BATCHED_DATA --output-root OUTPUT \
  --map-file GLOBAL_CUI_ROLLUP_UMLS2021AB_VID_13MAY2025.csv

# ── Path B · Database ────────────────────────────────────────────────
# Windows (BWH): java "-Djava.library.path=NILE\sqljdbc_auth" -cp ".;NILE\lib\*" NILE.NILEDatabaseProcessor NILE\NLPproperties_you.txt
# ERISTwo:       java -cp ".:NILE/lib/*" NILE.NILEDatabaseProcessor NILE/NLPproperties_you.txt

# ── Path C · CSV ─────────────────────────────────────────────────────
java -cp ".:NILE/lib/nile_20.jar:NILE/lib/opencsv-5.12.0.jar:NILE/lib/commons-lang3-3.12.0.jar:NILE/lib/commons-collections4-4.4.jar" \
  NILE.NILECSVProcessor --dictionary-path NILE/NER_dictionary.txt --input-csv notes.csv --output-csv out/nile_out.csv

# ── Checks ───────────────────────────────────────────────────────────
grep -l '\[FAIL\]' output/rpdr_processing/logs/*.log   # NILE failures?
grep -L SUCCESS OUTPUT/log/processing_batch*.log        # any batch that didn't finish?
```

---

### Reference
- Pipeline scripts: `github.com/vidulpanickan/MGB-Clinical-NLP-Pipeline` — `EXTRACT/` (Path A3), `NILE/` (§2), `POSTPROCESS/` (§7).
- Shared NILE install (ERISTwo): `/data/vbio-methodsdev/SHARE/NILE/`
- NILE / CELEHS: Narrative Information Linear Extraction, Harvard CELEHS lab.
</content>
