#!/usr/bin/env bash
set -euo pipefail

TAG="STRICTERVrepNameTOP20.v4c"
OUT=/athena/masonlab/scratch/als4067/FIXED_ERV_ONLY
SHEET=/athena/masonlab/scratch/als4067/FIXED_ERV_ONLY/axiom_sample_sheet.tsv

# conda
source ~/miniconda3/etc/profile.d/conda.sh
conda activate axiom_herv

# 0) check stats count
N=$(ls -1 $OUT/stats/stats.S*.ALLMODS.${TAG}.tsv 2>/dev/null | wc -l || true)
echo "[INFO] found stats files: $N"
if [[ "$N" -lt 20 ]]; then
  echo "[WARN] looks incomplete (<20). If you expect 23, wait for modkit to finish."
fi

# 1) matrices
python3 /home/fs01/als4067/AXIOM_HERV/FIXED_ERV_ONLY/scripts/10_build_repname_matrices_from_stats.py \
  --stats_dir "$OUT/stats" \
  --tag "$TAG" \
  --out_dir "$OUT/matrices"

# 2) deltas (m,h only)
python3 /home/fs01/als4067/AXIOM_HERV/FIXED_ERV_ONLY/scripts/20_build_delta_from_matrices.py \
  --sheet "$SHEET" \
  --tag "$TAG" \
  --matrix_m "$OUT/matrices/matrix.ALLMODS.${TAG}.percent_m.tsv" \
  --matrix_h "$OUT/matrices/matrix.ALLMODS.${TAG}.percent_h.tsv" \
  --out_dir "$OUT/deltas"

# 3) report
/home/fs01/als4067/AXIOM_HERV/FIXED_ERV_ONLY/scripts/30_run_report_STRICTERV_v4c.sh

echo "[DONE] full post-modkit pipeline for $TAG"
