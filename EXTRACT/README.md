# Note/NILE Output Extraction Jobs

This folder contains small SLURM jobs for extracting notes for a given set of patients.

## Files

- `extract_from_nile_output.sbatch`  
  Extracts **NILE generated output** for a specified set of patient IDs.

  Needs:
  - `ROOT_DIR`: folder containing the NILE output files
  - `IDS_FILE`: text file with one patient ID per line
  - `OUT_FILE`: output file where matched rows will be saved

  Input files should:
  - match the file type the script is searching for
  - use `|` as the separator
  - have the patient ID in the first column

- `rpdr_note_extract.sh`  
  Bash script that does the actual note pull. This can be used separately with RPDR-style notes for extraction.

  Needs:
  - `ROOT_DIR`: folder containing subfolders with report files
  - `IDS_FILE`: text file with one ID per line
  - `OUTPUT_DIR`: folder where extracted files will be saved
  - `KEYPOS`: which ID field to match
    - `1` = EMPI
    - `2` = EPIC_PMRN
    - `4` = MRN

  Input report files should:
  - be inside subfolders under `ROOT_DIR`
  - use `|` as the separator
  - have the expected RPDR header
  - end each report block with `[report_end]`

- `extract_biobank_notes.sbatch`  
  Extracts **raw Biobank notes** for a specified set of patient IDs. This script calls `rpdr_note_extract.sh`.

  Needs:
  - `ROOT_DIR`: main folder containing the Biobank note files
  - `IDS_FILE`: text file with one ID per line
  - `OUTPUT_DIR`: folder where extracted files will be written
  - `KEYPOS`: which ID field to match
    - `1` = EMPI
    - `2` = EPIC_PMRN
    - `4` = MRN
  - `rpdr_note_extract.sh` in the same folder

# How to Use

## 1. Configure the Job Scripts

Open the appropriate `.sbatch` file:

- `extract_from_nile_output.sbatch`
- `extract_biobank_notes.sbatch`

Update the variables at the top of the script to match your project setup.

For `extract_from_nile_output.sbatch`:
- `ROOT_DIR`
- `IDS_FILE`
- `OUT_FILE`

For `extract_biobank_notes.sbatch`:
- `ROOT_DIR`
- `IDS_FILE`
- `OUTPUT_DIR`
- `KEYPOS`

Make sure the paths, file format, and ID column are correct before submitting the job.

---

## 2. Submit the Job

From your cluster login node, run:

```bash
sbatch extract_from_nile_output.sbatch
# or
sbatch extract_biobank_notes.sbatch
```

## 3. Check Logs
   SLURM logs (`slurm-*.out` / `slurm-*.err`) and the extraction log inside your `OUTPUT_DIR` (e.g. `extraction_progress.log`) will show progress and any errors.
