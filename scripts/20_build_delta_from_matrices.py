#!/usr/bin/env python3
import os, re, argparse
import numpy as np
import pandas as pd

def read_sheet_tsv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, sep="\t", dtype=str)
    if df.shape[1] == 1:
        df = pd.read_csv(path, sep=r"\s+", engine="python", dtype=str)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    return df

def simplify_timepoint(tp: str) -> str:
    tp = str(tp).strip()
    if tp.startswith("FD4"): return "FD4"
    if tp.startswith("FD7"): return "FD7"
    if tp.startswith("L-45"): return "L-45"
    if tp.startswith("R+"):
        m = re.match(r"(R\+\d+)", tp)
        if m: return m.group(1)
    return tp

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheet", required=True, help="axiom_sample_sheet.tsv")
    ap.add_argument("--tag", required=True)
    ap.add_argument("--matrix_m", required=True, help="percent_m matrix (samples x repName)")
    ap.add_argument("--matrix_h", required=True, help="percent_h matrix (samples x repName)")
    ap.add_argument("--out_dir", required=True)
    ap.add_argument("--baseline_tp", default="L-45")
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    m = pd.read_csv(args.matrix_m, sep="\t", index_col=0)
    h = pd.read_csv(args.matrix_h, sep="\t", index_col=0)
    m.index = m.index.astype(str).str.strip()
    h.index = h.index.astype(str).str.strip()

    # Load sheet
    sheet = read_sheet_tsv(args.sheet)
    needed = ["sample_id", "time_point", "crew_member", "collection_tube"]
    for c in needed:
        if c not in sheet.columns:
            raise SystemExit(f"[ERROR] sample sheet missing {c}. Columns={list(sheet.columns)}")

    sheet["sample_id"] = sheet["sample_id"].astype(str).str.strip()
    sheet["tp"] = sheet["time_point"].astype(str).str.strip().map(simplify_timepoint)
    sheet["astronaut"] = sheet["crew_member"].astype(str).str.strip()
    sheet["tube"] = sheet["collection_tube"].astype(str).str.strip()

    # Align sheet to matrix samples
    samples = m.index.tolist()
    sheet_sub = sheet[sheet["sample_id"].isin(samples)].copy()
    missing = sorted(set(samples) - set(sheet_sub["sample_id"]))
    if missing:
        raise SystemExit(f"[ERROR] Unmapped sample IDs (not in sheet): {missing}")

    sheet_sub = sheet_sub.set_index("sample_id").loc[samples].copy()

    # Baseline per astronaut
    base_tp = args.baseline_tp
    base = sheet_sub[sheet_sub["tp"] == base_tp].copy()
    if base.empty:
        raise SystemExit(f"[ERROR] No baseline samples found with tp={base_tp}")

    # Require baseline for each astronaut present
    astr_all = sorted(sheet_sub["astronaut"].unique().tolist())
    astr_base = sorted(base["astronaut"].unique().tolist())
    lacking = sorted(set(astr_all) - set(astr_base))
    if lacking:
        raise SystemExit(f"[ERROR] astronauts missing baseline ({base_tp}): {lacking}")

    # Baseline matrices (if multiple baselines per astronaut, take mean)
    m_base = {}
    h_base = {}
    for a in astr_all:
        idx = base[base["astronaut"] == a].index
        m_base[a] = m.loc[idx].mean(axis=0)
        h_base[a] = h.loc[idx].mean(axis=0)

    # Compute deltas
    dm = m.copy() * np.nan
    dh = h.copy() * np.nan
    for sid in samples:
        a = sheet_sub.loc[sid, "astronaut"]
        dm.loc[sid] = m.loc[sid] - m_base[a]
        dh.loc[sid] = h.loc[sid] - h_base[a]

    # Write
    out_m = os.path.join(args.out_dir, f"DELTA.ALLMODS.{args.tag}.percent_m.tsv")
    out_h = os.path.join(args.out_dir, f"DELTA.ALLMODS.{args.tag}.percent_h.tsv")
    dm.to_csv(out_m, sep="\t", index=True, float_format="%.8g")
    dh.to_csv(out_h, sep="\t", index=True, float_format="%.8g")

    # QC mapping file
    qc = sheet_sub[["tp","astronaut","tube"]].copy()
    qc.to_csv(os.path.join(args.out_dir, f"DELTA.ALLMODS.{args.tag}.meta_used.tsv"), sep="\t", index=True)

    print("[DONE] wrote:", out_m)
    print("[DONE] wrote:", out_h)
    print("[DONE] wrote meta:", os.path.join(args.out_dir, f"DELTA.ALLMODS.{args.tag}.meta_used.tsv"))

if __name__ == "__main__":
    main()
