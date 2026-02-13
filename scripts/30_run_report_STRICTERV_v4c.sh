#!/usr/bin/env bash
set -euo pipefail

TAG="STRICTERVrepNameTOP20.v4c"
OUT=/athena/masonlab/scratch/als4067/FIXED_ERV_ONLY

# Update this if your sheet is elsewhere:
SHEET=/athena/masonlab/scratch/als4067/FIXED_ERV_ONLY/axiom_sample_sheet.tsv

DM=$OUT/deltas/DELTA.ALLMODS.${TAG}.percent_m.tsv
DH=$OUT/deltas/DELTA.ALLMODS.${TAG}.percent_h.tsv
REPORT_DIR=$OUT/reports/report_${TAG}

# conda
source ~/miniconda3/etc/profile.d/conda.sh
conda activate axiom_herv

python3 /home/fs01/als4067/AXIOM_HERV/scripts/axiom2_repeat_methylation_delta_analysis_run.py \
  --sheet "$SHEET" \
  --erv_5mc "$DM" --erv_5hmc "$DH" \
  --ltr_5mc "$DM" --ltr_5hmc "$DH" \
  --out_dir "$REPORT_DIR"

echo "[DONE] Report in: $REPORT_DIR"
