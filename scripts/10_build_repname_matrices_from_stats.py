#!/usr/bin/env python3
import os, re, glob, argparse
import numpy as np
import pandas as pd

def infer_sample(path: str) -> str:
    b = os.path.basename(path)
    m = re.search(r"stats\.(S\d{3})\.", b)
    if not m:
        raise ValueError(f"Cannot infer sample from filename: {b}")
    return m.group(1)

def safe_percent(count, valid):
    count = count.astype(float)
    valid = valid.astype(float)
    out = np.full_like(count, np.nan, dtype=float)
    mask = valid > 0
    out[mask] = 100.0 * (count[mask] / valid[mask])
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stats_dir", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--out_dir", required=True)
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    patt = os.path.join(args.stats_dir, f"stats.S*.ALLMODS.{args.tag}.tsv")
    files = sorted(glob.glob(patt))
    if not files:
        raise SystemExit(f"[ERROR] No files matched: {patt}")

    mats = {m: {} for m in ["m","h","a"]}
    mats_valid = {m: {} for m in ["m","h","a"]}
    mats_count = {m: {} for m in ["m","h","a"]}

    all_repnames = set()
    samples = []

    for f in files:
        sample = infer_sample(f)
        samples.append(sample)

        df = pd.read_csv(f, sep="\t")
        if "name" not in df.columns:
            raise SystemExit(f"[ERROR] Missing 'name' column in {f}. Columns={list(df.columns)[:20]}")

        # Expect modkit columns
        need = []
        for m in ["m","h","a"]:
            need += [f"count_{m}", f"count_valid_{m}"]
        for c in need:
            if c not in df.columns:
                raise SystemExit(f"[ERROR] Missing column {c} in {f}")

        g = df.groupby("name", dropna=False)[need].sum().reset_index()
        rep = g["name"].astype(str).tolist()
        all_repnames.update(rep)

        for m in ["m","h","a"]:
            c = g[f"count_{m}"].astype(float)
            v = g[f"count_valid_{m}"].astype(float)
            p = safe_percent(c.values, v.values)

            mats[m][sample] = dict(zip(rep, p))
            mats_valid[m][sample] = dict(zip(rep, v.values))
            mats_count[m][sample] = dict(zip(rep, c.values))

    # Build consistent column order
    repnames = sorted(all_repnames)

    def to_df(dct):
        out = pd.DataFrame(index=sorted(set(samples)), columns=repnames, dtype=float)
        for s, mp in dct.items():
            for r, val in mp.items():
                out.loc[s, r] = val
        return out

    out_prefix = os.path.join(args.out_dir, f"matrix.ALLMODS.{args.tag}")

    for m in ["m","h","a"]:
        dfp = to_df(mats[m])
        dfv = to_df(mats_valid[m])
        dfc = to_df(mats_count[m])

        dfp.to_csv(out_prefix + f".percent_{m}.tsv", sep="\t", index=True, float_format="%.8g")
        dfv.to_csv(out_prefix + f".valid_{m}.tsv",   sep="\t", index=True, float_format="%.8g")
        dfc.to_csv(out_prefix + f".count_{m}.tsv",   sep="\t", index=True, float_format="%.8g")

    # Save repName list
    with open(out_prefix + ".repnames.txt", "w") as fh:
        for r in repnames:
            fh.write(r + "\n")

    print("[DONE] Wrote matrices to:", args.out_dir)
    print("[DONE] samples:", len(set(samples)), "repNames:", len(repnames))
    print("[HINT] Example:", out_prefix + ".percent_m.tsv")

if __name__ == "__main__":
    main()
