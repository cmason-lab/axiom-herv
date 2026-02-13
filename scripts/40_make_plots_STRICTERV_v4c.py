#!/usr/bin/env python3
import os, re, argparse
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable

MOD_CODE_TO_NAME = {"m": "5mC", "h": "5hmC", "a": "6mA"}

def norm_timepoint(tp: str) -> str:
    tp = str(tp).strip()
    if tp.startswith("L-"):
        return tp
    m = re.search(r"\bFD(\d+)\b", tp)
    if m:
        return f"FD{int(m.group(1))}"
    if tp.startswith("R+"):
        return tp
    return tp

def timepoint_sort_key(tp: str):
    tp = str(tp).strip()
    if tp.startswith("L-"):
        # L-45 should come before L-10 etc -> sort by number
        try:
            return (0, int(tp[2:]))
        except:
            return (0, 999)
    m = re.match(r"FD(\d+)$", tp)
    if m:
        return (1, int(m.group(1)))
    if tp.startswith("R+"):
        try:
            return (2, int(tp[2:]))
        except:
            return (2, 999)
    return (9, 999)

def load_sample_sheet(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, sep="\t", dtype=str)
    df.columns = [c.strip() for c in df.columns]

    # normalize colnames
    rename = {}
    for c in df.columns:
        lc = c.strip().lower()
        if lc in ("sample_id", "sampleid"): rename[c] = "sample_id"
        if lc in ("crew_member", "crewmember", "crew"): rename[c] = "crew_member"
        if lc in ("time_point", "timepoint"): rename[c] = "time_point"
    df = df.rename(columns=rename)

    for req in ["sample_id", "crew_member", "time_point"]:
        if req not in df.columns:
            raise SystemExit(f"[ERROR] Missing column {req}. Columns={list(df.columns)}")

    df["sample_id"] = df["sample_id"].astype(str).str.strip()
    df["crew_member"] = df["crew_member"].astype(str).str.strip()
    df["time_point"] = df["time_point"].map(norm_timepoint)
    df["tp_key"] = df["time_point"].map(timepoint_sort_key)

    df = df.sort_values(["crew_member", "tp_key"]).reset_index(drop=True)
    return df

def robust_sym_limits(values: np.ndarray, q=0.99):
    vals = values[np.isfinite(values)]
    if vals.size == 0:
        return (-1, 1)
    hi = np.quantile(np.abs(vals), q)
    if hi == 0:
        hi = float(np.max(np.abs(vals)) + 1e-6)
    return (-hi, hi)

def zscore_by_feature(df: pd.DataFrame) -> pd.DataFrame:
    mu = df.mean(axis=0)
    sd = df.std(axis=0).replace(0, np.nan)
    return (df - mu) / sd

def plot_master_heatmap(D: pd.DataFrame, sheet: pd.DataFrame, outpng: str, title: str, zscore=False, max_cols=80):
    if D.empty:
        return

    keep = set(D.index)
    order = [s for s in sheet["sample_id"].tolist() if s in keep]
    Z = D.loc[order].copy()
    if zscore:
        Z = zscore_by_feature(Z)

    if max_cols is not None and Z.shape[1] > max_cols:
        var = Z.var(axis=0).sort_values(ascending=False)
        Z = Z[var.index[:max_cols]]

    meta = sheet.set_index("sample_id").loc[order]
    ylab = [f"{meta.loc[s,'crew_member']} | {meta.loc[s,'time_point']} | {s}" for s in order]

    arr = Z.to_numpy()
    vmin, vmax = robust_sym_limits(arr, q=0.99)

    fig = plt.figure(figsize=(max(14, 0.35*Z.shape[1]), max(8, 0.28*Z.shape[0])))
    ax = plt.gca()
    im = ax.imshow(arr, aspect="auto", vmin=vmin, vmax=vmax)
    ax.set_title(title + (" (zscore)" if zscore else " (Δ vs baseline)"))
    ax.set_yticks(np.arange(len(order)))
    ax.set_yticklabels(ylab, fontsize=7)
    ax.set_xticks(np.arange(Z.shape[1]))
    ax.set_xticklabels(Z.columns.tolist(), rotation=90, fontsize=7)
    plt.colorbar(im, ax=ax, fraction=0.02, pad=0.02)
    plt.tight_layout()
    fig.savefig(outpng, dpi=300)
    plt.close(fig)

def astronaut_small_multiples_heatmap(D: pd.DataFrame, sheet: pd.DataFrame, outpng: str, title: str, topn=30):
    if D.empty:
        return

    meta = sheet.set_index("sample_id")
    crews = sorted(sheet["crew_member"].unique().tolist())

    var = D.var(axis=0).sort_values(ascending=False)
    feats = var.index[:min(topn, len(var))].tolist()

    mats = {}
    all_vals = []
    for crew in crews[:4]:
        sids = sheet[sheet["crew_member"] == crew].sort_values("tp_key")["sample_id"].tolist()
        sids = [s for s in sids if s in D.index]
        if not sids:
            continue
        X = D.loc[sids, feats].to_numpy().T
        mats[crew] = (sids, X)
        all_vals.append(X)

    if len(all_vals) == 0:
        return

    stacked = np.concatenate([x.ravel() for x in all_vals])
    vmin, vmax = robust_sym_limits(stacked, q=0.99)

    fig = plt.figure(figsize=(16, 10))
    for i, crew in enumerate(crews[:4], start=1):
        ax = plt.subplot(2, 2, i)
        if crew not in mats:
            ax.set_axis_off()
            continue

        sids, X = mats[crew]
        im = ax.imshow(X, aspect="auto", vmin=vmin, vmax=vmax)

        ax.set_title(f"{crew}")
        ax.set_yticks(np.arange(len(feats)))
        ax.set_yticklabels(feats, fontsize=7)

        tps = [meta.loc[s, "time_point"] for s in sids]
        ax.set_xticks(np.arange(len(tps)))
        ax.set_xticklabels(tps, rotation=45, ha="right", fontsize=8)

        divider = make_axes_locatable(ax)
        cax = divider.append_axes("right", size="3%", pad=0.08)
        cbar = plt.colorbar(im, cax=cax)
        cbar.ax.tick_params(labelsize=8)
        cbar.set_label("Δ (percent points)", fontsize=9)

    plt.suptitle(title + f" | top {len(feats)} variable features", y=0.98, fontsize=14)
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(outpng, dpi=300)
    plt.close(fig)

def plot_lines_sparse(values_by_sample: pd.Series, sheet: pd.DataFrame, outpng: str, title: str, ylabel: str):
    """
    Sparse plotting per astronaut: connect only existing points.
    This ensures e.g. R+30 continues even if R+14 is missing (no NaN break).
    """
    meta = sheet.set_index("sample_id")
    crews = sorted(sheet["crew_member"].unique().tolist())

    # global x positions for consistent time axis
    global_tps = sorted(sheet["time_point"].unique().tolist(), key=timepoint_sort_key)
    tp_to_x = {tp: i for i, tp in enumerate(global_tps)}

    fig = plt.figure(figsize=(13, 5))
    ax = plt.gca()

    for crew in crews:
        sids = sheet[sheet["crew_member"] == crew].sort_values("tp_key")["sample_id"].tolist()
        xs, ys = [], []
        for sid in sids:
            if sid not in values_by_sample.index:
                continue
            tp = meta.loc[sid, "time_point"]
            if tp not in tp_to_x:
                continue
            val = values_by_sample.loc[sid]
            if pd.isna(val):
                continue
            xs.append(tp_to_x[tp])
            ys.append(float(val))

        if len(xs) == 0:
            continue

        ax.plot(xs, ys, marker="o", linewidth=2, label=crew)

    ax.axhline(0, linewidth=1)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.set_xticks(np.arange(len(global_tps)))
    ax.set_xticklabels(global_tps, rotation=45, ha="right")
    ax.legend()
    plt.tight_layout()
    fig.savefig(outpng, dpi=300)
    plt.close(fig)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="OUT dir that contains deltas/")
    ap.add_argument("--sheet", required=True, help="axiom_sample_sheet.tsv")
    ap.add_argument("--tag", required=True, help="e.g. STRICTERVrepNameTOP20.v4c")
    ap.add_argument("--plot_dir", required=True, help="output dir for PNGs")
    ap.add_argument("--topn_heat", type=int, default=30)
    ap.add_argument("--max_cols_master", type=int, default=80)
    args = ap.parse_args()

    OUT = args.out
    os.makedirs(args.plot_dir, exist_ok=True)
    tables_dir = os.path.join(args.plot_dir, "tables")
    os.makedirs(tables_dir, exist_ok=True)

    sheet = load_sample_sheet(args.sheet)

    # We read already-built DELTAs: samples x repNames
    for code, modname in MOD_CODE_TO_NAME.items():
        delta_path = os.path.join(OUT, "deltas", f"DELTA.ALLMODS.{args.tag}.percent_{code}.tsv")
        if not os.path.exists(delta_path):
            print(f"[WARN] missing {delta_path}")
            continue

        D = pd.read_csv(delta_path, sep="\t", index_col=0)
        D.index = D.index.astype(str).str.strip()

        # Save a copy into plot_dir/tables for archival
        D.to_csv(os.path.join(tables_dir, f"DELTA.ALLMODS.{args.tag}.{modname}.samples_x_repName.tsv"), sep="\t")

        # Heatmaps
        plot_master_heatmap(
            D, sheet,
            outpng=os.path.join(args.plot_dir, f"HM.MASTER.DELTA.ALLMODS.{args.tag}.{modname}.png"),
            title=f"Δ {modname} | {args.tag} — all samples",
            zscore=False,
            max_cols=args.max_cols_master
        )
        plot_master_heatmap(
            D, sheet,
            outpng=os.path.join(args.plot_dir, f"HM.MASTER.ZSCORE.ALLMODS.{args.tag}.{modname}.png"),
            title=f"Δ {modname} | {args.tag} — all samples",
            zscore=True,
            max_cols=args.max_cols_master
        )
        astronaut_small_multiples_heatmap(
            D, sheet,
            outpng=os.path.join(args.plot_dir, f"HM.ASTROS.DELTA.ALLMODS.{args.tag}.{modname}.png"),
            title=f"Δ {modname} | {args.tag} — per astronaut",
            topn=args.topn_heat
        )

        # Line plots (sparse, continuous to R+30)
        mean_by_sample = D.mean(axis=1, skipna=True)
        plot_lines_sparse(
            mean_by_sample, sheet,
            outpng=os.path.join(args.plot_dir, f"LINE.MEAN_DELTA.ALLMODS.{args.tag}.{modname}.png"),
            title=f"{modname} | {args.tag} | mean Δ across repNames (astronaut-normalized)",
            ylabel="Mean Δ across repNames"
        )

        rmse_by_sample = D.apply(lambda r: float(np.sqrt(np.nanmean(r.to_numpy(dtype=float)**2))), axis=1)
        plot_lines_sparse(
            rmse_by_sample, sheet,
            outpng=os.path.join(args.plot_dir, f"LINE.RMSE_DISTANCE.ALLMODS.{args.tag}.{modname}.png"),
            title=f"{modname} | {args.tag} | distance-from-baseline (RMSE of Δ across repNames)",
            ylabel="RMSE(Δ)"
        )

    print("[DONE] Wrote PNGs into:", args.plot_dir)
    print("[DONE] Tables into:", tables_dir)

if __name__ == "__main__":
    main()
