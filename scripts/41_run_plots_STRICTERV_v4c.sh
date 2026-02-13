#!/usr/bin/env bash
set -euo pipefail

source ~/miniconda3/etc/profile.d/conda.sh
conda activate axiom_herv

OUT=/athena/masonlab/scratch/als4067/FIXED_ERV_ONLY
TAG="STRICTERVrepNameTOP20.v4c"
SHEET="$OUT/axiom_sample_sheet.tsv"
PLOT_DIR="$OUT/plots_${TAG}"

python3 /home/fs01/als4067/AXIOM_HERV/FIXED_ERV_ONLY/scripts/40_make_plots_STRICTERV_v4c.py \
  --out "$OUT" \
  --sheet "$SHEET" \
  --tag "$TAG" \
  --plot_dir "$PLOT_DIR" \
  --topn_heat 30 \
  --max_cols_master 80

echo "[DONE] plots in: $PLOT_DIR"
ls -lh "$PLOT_DIR" | head
