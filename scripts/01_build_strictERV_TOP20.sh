#!/usr/bin/env bash
set -euo pipefail

# Where outputs go
OUT=/athena/masonlab/scratch/als4067/FIXED_ERV_ONLY
mkdir -p "$OUT/targets"

# Input RepeatMasker
RMSK=/athena/masonlab/scratch/als4067/hg38.rmsk.txt.gz
TOPN=${1:-20}

# Core: chr start end repName repClass repFamily
CORE=$OUT/targets/hg38.rmsk.core.repname.tsv

echo "[INFO] OUT=$OUT"
echo "[INFO] RMSK=$RMSK"
echo "[INFO] TOPN=$TOPN"

if [[ ! -s "$RMSK" ]]; then
  echo "[ERROR] Missing RMSK: $RMSK"
  exit 1
fi

if [[ ! -s "$CORE" ]]; then
  echo "[INFO] Building CORE: $CORE"
  # rmsk columns in your file: chr=$6 start=$7 end=$8 repName=$11 repClass=$12 repFamily=$13
  zcat "$RMSK" | awk 'BEGIN{FS=OFS="\t"}{print $6,$7,$8,$11,$12,$13}' > "$CORE"
fi

build_by_repname () {
  local list="$1"
  local out="$2"
  : > "$out"
  while read -r rn; do
    [[ -z "$rn" ]] && continue
    awk -v r="$rn" 'BEGIN{FS=OFS="\t"} $4==r {print $1,$2,$3}' "$CORE" \
      | sort -k1,1 -k2,2n \
      | bedtools merge -i - \
      | awk -v r="$rn" 'BEGIN{OFS="\t"}{print $1,$2,$3,r}' \
      >> "$out"
  done < "$list"
  sort -k1,1 -k2,2n -o "$out" "$out"
}

# STRICT ERV definition: repFamily starts with ERV but exclude ERVL-MaLR
BP=$OUT/targets/hg38_RM_STRICTERV_repName_bp.tsv
LIST=$OUT/targets/hg38_RM_STRICTERV_repName_TOP${TOPN}.list
BED=$OUT/targets/hg38_RM_STRICTERV_repName_TOP${TOPN}.merged_by_repname.bed

echo "[INFO] Computing STRICT ERV bp per repName -> $BP"
awk 'BEGIN{FS=OFS="\t"}
  ($6 ~ /^ERV/ && $6 != "ERVL-MaLR") {bp[$4]+=$3-$2}
  END{for(k in bp) print k,bp[k]}
' "$CORE" | sort -k2,2nr > "$BP"

cut -f1 "$BP" | head -n "$TOPN" > "$LIST"
echo "[INFO] Building merged bed -> $BED"
build_by_repname "$LIST" "$BED"

echo "[QC] unique repNames (expect TOPN):"
cut -f4 "$BED" | sort -u | wc -l

echo "[QC] repName -> class/family (should be LTR and ERV*; must NOT include ERVL-MaLR):"
cut -f4 "$BED" | sort -u > $OUT/targets/strictERV.repnames.txt
echo -e "repName\tclass\trepFamily" > $OUT/targets/strictERV.class_family.tsv
zcat "$RMSK" | awk -F'\t' 'BEGIN{OFS="\t"}
  NR==FNR{q[$1]=1;next}
  ($11 in q){print $11,$12,$13}
' $OUT/targets/strictERV.repnames.txt - \
  | sort -u >> $OUT/targets/strictERV.class_family.tsv

column -t $OUT/targets/strictERV.class_family.tsv

echo "[DONE] Wrote:"
ls -lh "$BP" "$LIST" "$BED" $OUT/targets/strictERV.class_family.tsv
