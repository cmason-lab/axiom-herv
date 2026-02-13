# STRICTERV TopN RepeatMasker → modkit → matrices → deltas → plots/report

This folder contains a small pipeline (bash + python) to:
1) define a **“STRICT ERV”** RepeatMasker panel (Top *N* `repName`s by masked bp),
2) run `modkit stats` per sample over those regions,
3) build **sample × repName** matrices (percent + counts + valid coverage),
4) compute **within-astronaut Δ (delta) vs baseline** (L–45),
5) generate plots and a summary report.

> **Terminology used in scripts**
> - **repName** = RepeatMasker element name (e.g., `MER57F`, `HERV...`)
> - **STRICT ERV** here means: `repFamily` starts with `ERV` **excluding** `ERVL-MaLR`.
> - **ALLMODS** means the modkit output includes columns for three mod codes:
>   - `m` = 5mC, `h` = 5hmC, `a` = 6mA (as emitted in the per-sample stats tables).
> - **Δ / delta** is computed **per astronaut** relative to that astronaut’s baseline timepoint `L-45` and is in **percent points**.

---

## Inputs you need

1) **RepeatMasker hg38 table** (gzipped)
- Default path in scripts:  
  `/athena/masonlab/scratch/als4067/hg38.rmsk.txt.gz`

2) **Per-sample modified-base BED.gz** files (one per sample, already produced upstream)
- The filelist builder expects files like:  
  `/athena/masonlab/scratch/als4067/S001.5mC.filtered_mod.bed.gz`  
  (`S###` prefix is used as the sample ID)

3) **Sample sheet** used for deltas/plots/report
- Default path in scripts:  
  `/athena/masonlab/scratch/als4067/FIXED_ERV_ONLY/axiom_sample_sheet.tsv`
- Must include at least: `sample_id`, `crew_member`, `time_point`, `collection_tube`

---

## Outputs (what you’ll get)

Within your `OUT` directory (default shown below), the pipeline produces:

- `targets/`
  - strict-ERV repName bp ranking
  - TopN repName list
  - merged BED of target regions with `repName` as 4th column
- `stats/`
  - per-sample modkit stats TSVs
- `matrices/`
  - `matrix.ALLMODS.<TAG>.percent_[m|h|a].tsv` (samples × repName)
  - `matrix.ALLMODS.<TAG>.valid_[m|h|a].tsv`
  - `matrix.ALLMODS.<TAG>.count_[m|h|a].tsv`
  - `matrix.ALLMODS.<TAG>.repnames.txt`
- `deltas/`
  - `DELTA.ALLMODS.<TAG>.percent_m.tsv`
  - `DELTA.ALLMODS.<TAG>.percent_h.tsv`
  - `DELTA.ALLMODS.<TAG>.meta_used.tsv`
- `reports/`
  - `reports/report_<TAG>/` (from the downstream report runner)
- `plots_<TAG>/`
  - heatmaps + line plots + archived tables used for plotting

---

## Quickstart (typical run order)

### 0) Set output base directory
Most scripts hardcode:
```bash
OUT=/athena/masonlab/scratch/als4067/FIXED_ERV_ONLY
```
Edit `OUT=...` in the scripts if you’re running elsewhere.

### 1) Build STRICTERV TopN target BED
```bash
bash 01_build_strictERV_TOP20.sh 20
```

### 2) Build the modkit filelist (one row per sample)
```bash
bash 02_make_filelist_strictERV_ALLMODS.sh 20
```

### 3) Submit modkit stats jobs (Slurm array)
Capped concurrency (default `%10`):
```bash
bash 03_submit_modkit_strictERV.sh
```

Or “full send” / custom cap:
```bash
bash 03_submit_modkit_strictERV_fullsend.sh 40   # e.g., cap at 40 concurrent tasks
bash 03_submit_modkit_strictERV_fullsend.sh      # no cap
```

### 4) Post-processing once stats are complete
This runs: matrices → deltas → report
```bash
bash 99_postmodkit_all_v4c.sh
```

### 5) (Optional) Generate plots
```bash
bash 41_run_plots_STRICTERV_v4c.sh
```

---

## IMPORTANT: keep TAG consistent (v4 vs v4c)

One script writes the filelist with a tag like:
- `STRICTERVrepNameTOP20.v4`

But the post-modkit / report / plot scripts expect:
- `STRICTERVrepNameTOP20.v4c`

If your output filenames don’t match, downstream steps won’t find files.
Fix by choosing **one** convention and updating it everywhere:
- in the filelist builder (`tag=...`)
- in post-modkit (`TAG=...`)
- in report/plot runners (`TAG=...`)

---

## Script-by-script (short explanations)

### `01_build_strictERV_TOP20.sh`
- Reads RepeatMasker table (`hg38.rmsk.txt.gz`)
- Builds a core table: `chr start end repName repClass repFamily`
- Computes masked bp per `repName` under STRICTERV definition (`repFamily ~ /^ERV/` and not `ERVL-MaLR`)
- Selects TopN repNames and writes:
  - `targets/hg38_RM_STRICTERV_repName_TOP<N>.list`
  - `targets/hg38_RM_STRICTERV_repName_TOP<N>.merged_by_repname.bed`  
    (intervals merged per repName via `bedtools merge`)
- Writes a QC table mapping repName → class/family

### `02_make_filelist_strictERV_ALLMODS.sh`
- Uses the target BED from step 1
- Scans for per-sample `S*.5mC.filtered_mod.bed.gz`
- Writes a TSV filelist with columns:  
  `sample  bed_gz  tag  regions  out`
- Sorts rows deterministically by sample ID

### `03_submit_modkit_strictERV.sh`
- Submits a Slurm **array job** sized from the filelist row count (minus header)
- Uses a fixed concurrency cap (`%10`)
- Points to a Slurm script template: `modkit_stats_onejob.sbatch`

### `03_submit_modkit_strictERV_fullsend.sh`
- Same purpose as the basic submitter, but:
  - lets you choose a concurrency cap (`CAP`) or remove the cap
  - does a QC check that there are no duplicate output paths in the filelist

### `modkit_stats_onejob.sbatch`
- Slurm “one task = one sample” job.
- Typically reads the `FILELIST` row for `SLURM_ARRAY_TASK_ID` and runs `modkit stats`
  over the provided `regions` BED, writing the per-sample stats TSV.
- **Note:** this file is referenced by the submit scripts; edit it if your cluster
  partitions/modules/resources differ.

### `10_build_repname_matrices_from_stats.py`
- Loads all per-sample stats tables matching:
  `stats_dir/stats.S*.ALLMODS.<tag>.tsv`
- Sums modkit stats rows by `name` (repName) and calculates:
  - percent = `100 * count_<mod> / count_valid_<mod>`
  - plus raw `count` and `valid` matrices
- Writes `percent_`, `count_`, `valid_` matrices for `m`, `h`, and `a`

### `20_build_delta_from_matrices.py`
- Loads:
  - `matrix.ALLMODS.<tag>.percent_m.tsv`
  - `matrix.ALLMODS.<tag>.percent_h.tsv`
  - `axiom_sample_sheet.tsv`
- Requires `L-45` baseline for **each** astronaut.
- Computes Δ per astronaut:
  - Δ(sample, repName) = percent(sample, repName) − mean_baseline(astronaut, repName)
- Writes:
  - `DELTA.ALLMODS.<tag>.percent_m.tsv`
  - `DELTA.ALLMODS.<tag>.percent_h.tsv`
  - `DELTA.ALLMODS.<tag>.meta_used.tsv`

### `30_run_report_STRICTERV_v4c.sh`
- Runs your downstream analysis/report script:
  `axiom2_repeat_methylation_delta_analysis_run.py`
- Passes the same STRICTERV delta matrices into both `--erv_*` and `--ltr_*` flags
  (so the report code can run without separate ERV/LTR inputs).

### `40_make_plots_STRICTERV_v4c.py`
- Reads DELTA matrices from `OUT/deltas/`
- Creates:
  - master heatmaps (Δ and z-scored)
  - per-astronaut small-multiples heatmaps
  - per-astronaut line plots for:
    - mean Δ across repNames
    - RMSE distance-from-baseline across repNames
- Uses “sparse” plotting logic (connects existing points even if intermediate timepoints are missing)

### `41_run_plots_STRICTERV_v4c.sh`
- Convenience wrapper to run `40_make_plots_STRICTERV_v4c.py` inside the `axiom_herv` conda env.

### `99_postmodkit_all_v4c.sh`
- Convenience “do everything after modkit finished” driver:
  1) quick stats-file count check
  2) build matrices
  3) build deltas (m/h)
  4) run the report script

---

## Environment / dependencies

- `bash`, `awk`, `sort`, `zcat`
- `bedtools` (used for merging intervals)
- Python 3 + `pandas`, `numpy`, `matplotlib`
- `conda` env expected by wrappers: `axiom_herv`

---

## Common failure modes

- **Tag mismatch** (v4 vs v4c): downstream scripts can’t find the expected files.
- **Missing baseline** (`L-45`) for an astronaut: delta step exits with an error.
- **Sample IDs don’t match** between sample sheet and matrix index: delta step errors.
- **Filelist points to wrong inputs** or outputs collide: fullsend submitter will catch duplicate outputs.

---

## Contact / context

This pipeline was written for the Axiom-2 ONT repeat-element modified-base workflow,
but it is general enough to reuse for any RepeatMasker repName panel with per-sample
mod-call BED.gz inputs and a metadata sheet.
