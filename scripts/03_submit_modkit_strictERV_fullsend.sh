#!/usr/bin/env bash
set -euo pipefail

OUT=/athena/masonlab/scratch/als4067/FIXED_ERV_ONLY

# Use whichever filelist you are actually using:
FILELIST="$OUT/filelist.ALLMODS.STRICTERVrepNameTOP20.tsv"
# If you instead used the dedup filelist created from the old pipeline, switch to:
# FILELIST="$OUT/axiom_stats_filelist.ALLMODS.STRICTERVrepNameTOP20.v4.dedup.tsv"

SBATCH=/home/fs01/als4067/AXIOM_HERV/FIXED_ERV_ONLY/scripts/modkit_stats_onejob.sbatch

# Concurrency cap:
#   - set to empty for NO cap (full send)
#   - or set to a number like 20, 30, 40
CAP="${1:-}"

if [[ ! -s "$FILELIST" ]]; then
  echo "[ERROR] Missing filelist: $FILELIST"
  exit 1
fi
if [[ ! -s "$SBATCH" ]]; then
  echo "[ERROR] Missing sbatch script: $SBATCH"
  exit 2
fi

# Derive array size from filelist rows
N=$(( $(wc -l < "$FILELIST") - 1 ))
if (( N <= 0 )); then
  echo "[ERROR] Filelist has no data rows: $FILELIST"
  exit 3
fi

# Basic QC: ensure no duplicate output paths
dup=$(awk 'NR>1{print $5}' "$FILELIST" | sort | uniq -d | head -n 1 || true)
if [[ -n "${dup:-}" ]]; then
  echo "[ERROR] Duplicate out paths detected (example): $dup"
  echo "Fix filelist before submitting."
  exit 4
fi

# Build sbatch --array string
if [[ -n "${CAP:-}" ]]; then
  ARR="1-${N}%${CAP}"
else
  ARR="1-${N}"
fi

echo "[INFO] FILELIST=$FILELIST"
echo "[INFO] tasks N=$N"
echo "[INFO] submitting: sbatch --array=${ARR} ${SBATCH}"

sbatch --array="${ARR}" "$SBATCH"
