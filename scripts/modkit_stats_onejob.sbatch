#!/usr/bin/env bash
#SBATCH --job-name=modkit_strictERV
#SBATCH --partition=scu-cpu
#SBATCH --cpus-per-task=6
#SBATCH --mem=12G
#SBATCH --time=12:00:00
#SBATCH -o /athena/masonlab/scratch/als4067/FIXED_ERV_ONLY/logs/modkit.strictERV.%A_%a.out
#SBATCH -e /athena/masonlab/scratch/als4067/FIXED_ERV_ONLY/logs/modkit.strictERV.%A_%a.err

set -euo pipefail

OUT=/athena/masonlab/scratch/als4067/FIXED_ERV_ONLY
FILELIST="${FILELIST:-/athena/masonlab/scratch/als4067/FIXED_ERV_ONLY/filelist.ALLMODS.STRICTERVrepNameTOP20.v4.tsv}"
# If you're using the dedup-from-old filelist, swap to:
# FILELIST=$OUT/axiom_stats_filelist.ALLMODS.STRICTERVrepNameTOP20.v4.dedup.tsv

source ~/.bashrc
conda activate axiom_herv

echo "[INFO] host=$(hostname) job=${SLURM_JOB_ID} task=${SLURM_ARRAY_TASK_ID}"
echo "[INFO] modkit=$(which modkit)"
modkit --version || true

line=$(awk -F'\t' -v n=$((SLURM_ARRAY_TASK_ID+1)) 'NR==n{print; exit}' "$FILELIST" || true)
if [[ -z "${line:-}" ]]; then
  echo "[ERROR] Could not read line n=$((SLURM_ARRAY_TASK_ID+1)) from $FILELIST"
  exit 10
fi

IFS=$'\t' read -r sample bedgz tag regions out <<< "$line"

echo "[INFO] sample=$sample"
echo "[INFO] bedgz=$bedgz"
echo "[INFO] regions=$regions"
echo "[INFO] out=$out"

if [[ ! -s "$regions" ]]; then
  echo "[ERROR] Missing regions bed: $regions"
  exit 12
fi
if [[ ! -s "$bedgz" ]]; then
  echo "[ERROR] Missing bedgz: $bedgz"
  exit 13
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
