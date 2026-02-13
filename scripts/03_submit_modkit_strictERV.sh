#!/usr/bin/env bash
set -euo pipefail

OUT=/athena/masonlab/scratch/als4067/FIXED_ERV_ONLY
FILELIST=$OUT/filelist.ALLMODS.STRICTERVrepNameTOP20.tsv
SBATCH=/home/fs01/als4067/AXIOM_HERV/FIXED_ERV_ONLY/scripts/modkit_stats_onejob.sbatch

if [[ ! -s "$FILELIST" ]]; then
  echo "[ERROR] Missing filelist: $FILELIST"
  exit 1
fi

N=$(( $(wc -l < "$FILELIST") - 1 ))
echo "[INFO] submitting array 1-${N} (from $FILELIST)"
sbatch --array=1-${N}%10 "$SBATCH"
