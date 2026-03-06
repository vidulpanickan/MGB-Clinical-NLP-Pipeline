# NILE Processor

A Java-based processor that takes clinical notes in CSV, database, RPDR, or Parquet format, runs NILE on the text, and writes structured output files.

The NILE tool is available here and can be copied into your own folder:

```
/data/vbio-methodsdev/SHARE/NILE/
```

Compiling builds the Java processor from the source code, while running uses that built processor on your input data. In general, you compile once unless the code changes, and you run the program each time you want to process a new file.

---

## Requirements

- Java JDK 20 or later (`java` and `javac` available on PATH)
  - Check if Java is installed by running `java -version`
- A copy of the NILE folder in your project directory
  - Source location: `/data/vbio-methodsdev/SHARE/NILE/`
- `NILE/lib` JAR files present in the project folder
- Dictionary file: `NILE/NER_dictionary.txt`
- Example input files are provided for quick testing

---

## Directory Layout (Example)

```
.
├─ NILE/
│  ├─ NILECSVProcessor.java (and/or .class)
│  ├─ NER_dictionary.txt
│  └─ lib/
├─ data/
│  └─ example_csv.csv
└─ output/
   └─ csv_processing/
```

---

## What It Works With

This project can run NILE on clinical text from:

- CSV files of notes
- Databases such as MySQL or SQL Server
- RPDR format text files
- Parquet files containing clinical notes

All modes use the NILE library and produce structured pipe-delimited output files with extracted medical concept codes and certainty values.

---

## Usage

### 1. Compile

Compile builds the Java processor from the source code. This is usually only needed once, unless the code changes.

Navigate to the project root and run the appropriate compile command.

**macOS / Linux**
```bash
javac -cp ".:NILE/lib/nile_20.jar:NILE/lib/opencsv-5.12.0.jar:NILE/lib/commons-lang3-3.12.0.jar:NILE/lib/commons-collections4-4.4.jar" \
  NILE/NILECSVProcessor.java
```

**Windows (Command Prompt)**
```cmd
javac -cp ".;NILE\lib\nile_20.jar;NILE\lib\opencsv-5.12.0.jar;NILE\lib\commons-lang3-3.12.0.jar;NILE\lib\commons-collections4-4.4.jar" NILE\NILECSVProcessor.java
```

---

### 2. Run

Run starts the processor on your actual input data. You do this each time you want to process a new file.

**macOS / Linux**
```bash
java -cp ".:NILE/lib/nile_20.jar:NILE/lib/opencsv-5.12.0.jar:NILE/lib/commons-lang3-3.12.0.jar:NILE/lib/commons-collections4-4.4.jar" \
  NILE.NILECSVProcessor \
  --dictionary-path NILE/NER_dictionary.txt \
  --input-csv data/example_csv.csv \
  --output-csv output/csv_processing/output.csv
```

**Windows (Command Prompt)**
```cmd
java -cp ".;NILE\lib\nile_20.jar;NILE\lib\opencsv-5.12.0.jar;NILE\lib\commons-lang3-3.12.0.jar;NILE\lib\commons-collections4-4.4.jar" NILE.NILECSVProcessor ^
  --dictionary-path NILE\NER_dictionary.txt ^
  --input-csv data\example_csv.csv ^
  --output-csv output\csv_processing/output.csv
```

---

### 3. Example Data

Example input CSV:

```
NILE/data/example_csv.csv
```

---

## Parameters

### Required Parameters

| Parameter | Description |
|---|---|
| `--dictionary-path` | Path to the NER dictionary file |
| `--input-csv` | Path to the input CSV file |
| `--output-csv` | Path to the output CSV file |

### Optional Column Mappings

| Parameter | Default Value |
|---|---|
| `--patient-num-col` | `patient_num` |
| `--encounter-num-col` | `encounter_num` |
| `--start-date-col` | `start_date` |
| `--notes-col` | `notes` |

### Example with Explicit Column Mappings

```bash
java -cp ".:NILE/lib/nile_20.jar:NILE/lib/opencsv-5.12.0.jar:NILE/lib/commons-lang3-3.12.0.jar:NILE/lib/commons-collections4-4.4.jar" \
  NILE.NILECSVProcessor \
  --dictionary-path NILE/NER_dictionary.txt \
  --input-csv data/example_csv.csv \
  --output-csv output/csv_processing/output.csv \
  --patient-num-col patient_num \
  --encounter-num-col encounter_num \
  --start-date-col start_date \
  --notes-col notes
```

---

## Output

The CSV processor reads a comma-separated CSV file and writes a pipe-delimited output file with columns:

```
patient_num|encounter_num|start_date|code_certainty
```

---

## Quality Control

After processing, verify that the NILE output contains the expected number of records. Check that the note count in the output matches the input note count. If some notes were dropped during processing, certain characters in the notes field may be causing issues with the NILE run.

To clean problematic characters from your input data, you can use:

```python
df["notes"] = (
    df["notes"]
    .str.strip(r"\/")
    .str.replace('"', "", regex=False)
)
```

---

## Summary

| Step | Description |
|---|---|
| **Compile** | Build the Java processor from source |
| **Run** | Use the processor on your data |
| **Input** | Clinical notes in CSV, database, RPDR, or Parquet format |
| **Output** | Structured pipe-delimited files with NILE concept codes and certainty values |This preprocessing step removes or replaces characters that commonly interfere with CSV parsing and NILE processing.
