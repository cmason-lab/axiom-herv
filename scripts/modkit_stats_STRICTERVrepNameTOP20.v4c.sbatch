#!/usr/bin/env bash
#SBATCH --job-name=modkit_strictERV
#SBATCH --partition=scu-cpu
#SBATCH --cpus-per-task=6
#SBATCH --mem=12G
#SBATCH --time=12:00:00
#SBATCH -o /athena/masonlab/scratch/als4067/FIXED_ERV_ONLY/logs/modkit.%x.%A_%a.out
#SBATCH -e /athena/masonlab/scratch/als4067/FIXED_ERV_ONLY/logs/modkit.%x.%A_%a.err

set -euo pipefail

source ~/miniconda3/etc/profile.d/conda.sh
conda activate axiom_herv

: "${FILELIST:?FILELIST env var must be set via sbatch --export}"

echo "[INFO] host=$(hostname) job=${SLURM_JOB_ID} task=${SLURM_ARRAY_TASK_ID}"
echo "[INFO] python=$(which python3)"
echo "[INFO] modkit=$(which modkit)"
modkit --version || true
echo "[INFO] FILELIST=$FILELIST"

line=$(awk -F'\t' -v n=$((SLURM_ARRAY_TASK_ID+1)) 'NR==n{print; exit}' "$FILELIST" || true)
if [[ -z "${line:-}" ]]; then
  echo "[ERROR] Could not read line n=$((SLURM_ARRAY_TASK_ID+1)) from $FILELIST"
  exit 10
fi

IFS=$'\t' read -r sample bedgz tag regions out <<< "$line"

echo "[INFO] sample=$sample tag=$tag"
echo "[INFO] bedgz=$bedgz"
echo "[INFO] regions=$regions"
echo "[INFO] out=$out"

if [[ ! -s "$regions" ]]; then
  echo "[ERROR] Missing/empty regions bed: $regions"
  exit 12
fi
if [[ ! -s "$bedgz" ]]; then
  echo "[ERROR] Missing/empty bedgz: $bedgz"
  exit 13
fi

# Robust resume/overwrite behavior:
# - if output exists but is empty -> delete and rerun
# - if output exists and non-empty -> skip
if [[ -e "$out" && ! -s "$out" ]]; then
  echo "[WARN] output exists but empty, deleting: $out"
  rm -f "$out"
fi
if [[ -s "$out" ]]; then
  echo "[SKIP] exists: $out"
  exit 0
fi

modkit stats \
  --regions "$regions" \
  --out-table "$out" \
  --mod-codes m,h,a \
  --threads 4 \
  --io-threads 2 \
  "$bedgz"

echo "[DONE] wrote $out"
