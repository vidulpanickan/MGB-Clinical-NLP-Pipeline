# Note Extraction Jobs

This folder contains small SLURM jobs for extracting notes for a given set of patients.

## Files

- `extract_from_nile_output.sbatch`
  Extracts **NILE generated output** output for a specified set of patient IDs

- `rpdr_note_extract.sh`  
  Bash script that does the actual note pull. This can be used seprately with rpdr style notes for extraction

- `extract_biobank_notes.sbatch`  
  Extracts **raw Biobank notes** for a specified set of patient IDs. This script calls rpdr_note_extract.sh.

# How to Use

## 1. Configure the Job Scripts

Open the appropriate `.sbatch` file:

- `extract_from_nile_output.sbatch`
- `extract_biobank_notes.sbatch`

Update the variables at the top of the script to match your project setup:

- `ROOT_DIR` – Directory containing input files  
- `IDS_FILE` – File containing patient IDs  
- `OUTPUT_DIR` – Directory where extracted notes will be saved  
- `KEYPOS` – Column number in the input file containing the patient ID  

Make sure all file paths and column indices are correct before submitting the job.

---

## 2. Submit the Job

From your cluster login node, run:

```{bash}
sbatch extract_from_nile_output.sbatch
# or
sbatch extract_biobank_notes.sbatch
```

## 3. Check Logs
   SLURM logs (`slurm-*.out` / `slurm-*.err`) and the extraction log inside your `OUTPUT_DIR` (e.g. `extraction_progress.log`) will show progress and any errors.
