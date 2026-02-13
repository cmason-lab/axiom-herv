#!/usr/bin/env bash
set -euo pipefail

OUT=/athena/masonlab/scratch/als4067/FIXED_ERV_ONLY
TOPN=${1:-20}

REGIONS=$OUT/targets/hg38_RM_STRICTERV_repName_TOP${TOPN}.merged_by_repname.bed
FILELIST=$OUT/filelist.ALLMODS.STRICTERVrepNameTOP${TOPN}.tsv

if [[ ! -s "$REGIONS" ]]; then
  echo "[ERROR] Missing regions BED: $REGIONS"
  exit 1
fi

echo -e "sample\tbed_gz\ttag\tregions\tout" > "$FILELIST"

# Inputs: one per sample (we know these include m/h/a outputs based on your v2 stats)
for bedgz in /athena/masonlab/scratch/als4067/S*.5mC.filtered_mod.bed.gz; do
  [[ -e "$bedgz" ]] || continue
  b=$(basename "$bedgz")
  sample="${b%%.*}"  # S001 from S001.5mC.filtered_mod.bed.gz
  tag="STRICTERVrepNameTOP${TOPN}.v4"
  out="$OUT/stats/stats.${sample}.ALLMODS.${tag}.tsv"
  echo -e "${sample}\t${bedgz}\t${tag}\t${REGIONS}\t${out}" >> "$FILELIST"
done

# sort deterministically by sample
{ head -n 1 "$FILELIST"; tail -n +2 "$FILELIST" | sort -k1,1; } > "${FILELIST}.tmp"
mv "${FILELIST}.tmp" "$FILELIST"

echo "[DONE] Wrote $FILELIST"
echo "[QC] lines incl header:" $(wc -l < "$FILELIST")
echo "[QC] samples:" $(awk 'NR>1{print $1}' "$FILELIST" | wc -l)
head -n 5 "$FILELIST"
