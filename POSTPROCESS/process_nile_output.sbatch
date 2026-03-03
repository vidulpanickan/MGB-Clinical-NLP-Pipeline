#!/bin/bash
#SBATCH --job-name=batch_extract
#SBATCH --output=/data/vbio-methodsdev/SHARE/BIOBANK/2025/WORK/NEW_PROCESS/LOGS/batch.%A_%a.out
#SBATCH --error=/data/vbio-methodsdev/SHARE/BIOBANK/2025/WORK/NEW_PROCESS/LOGS/batch.%A_%a.err
#SBATCH --partition=short
#SBATCH --mem=120G
#SBATCH --array=47-155
#SBATCH --time=0-03:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1

set -euo pipefail

module load conda
eval "$(conda shell.bash hook)"
conda activate nlp

INPUT_DIR="/data/vbio-methodsdev/SHARE/BIOBANK/2025/WORK/meta/BATCHED_DATA"
OUTPUT_ROOT="/data/vbio-methodsdev/SHARE/BIOBANK/2025/WORK/NEW_PROCESS/OUTPUT_27JAN2026"

python3 rollup_biobank.py \
  --batch "${SLURM_ARRAY_TASK_ID}" \
  --input-dir "${INPUT_DIR}" \
  --output-root "${OUTPUT_ROOT}"
