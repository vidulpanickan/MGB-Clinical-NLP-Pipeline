#!/usr/bin/env python3
"""
Process one batch_<N>.csv using the specified pipeline, producing:
  - DAILY/daily_batch_<N>.csv
  - MONTH/month_batch_<N>.csv
  - ROLLUP/rollup_daily_batch_<N>.csv
  - ROLLUP/rollup_month_batch_<N>.csv
  - log/processing_batch<N>.log

Notes on rollup outputs:
- Rollup uses a LEFT join CHILD_CUI -> ROLLUP_CUI (many-to-many allowed).
- Unmapped CUIs are kept by setting parent_cui = child_cui.
- Rollup MONTH counts are computed from rollup DAILY after de-duping
  (EMPI, date, parent_cui), so each parent CUI is counted at most once per day.

Usage:
  python process_one_batch.py --batch 29
"""

import argparse
import gc
import sys
import traceback
from datetime import datetime
from pathlib import Path

import pandas as pd


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--batch", type=int, required=True, help="Batch number, e.g., 29")
    p.add_argument(
        "--input-dir",
        default="/data/vbio-methodsdev/SHARE/BIOBANK/2025/WORK/meta/BATCHED_DATA",
        help="Directory containing batch_*.csv",
    )
    p.add_argument(
        "--output-root",
        default="/data/vbio-methodsdev/SHARE/BIOBANK/2025/WORK/meta/BIOBANK_CUI_COUNTS",
        help="Root output directory (will create DAILY, MONTH, ROLLUP, log)",
    )
    p.add_argument(
        "--map-file",
        default="/data/vbio-methodsdev/SHARE/BIOBANK/2025/WORK/meta/BIOBANK_CUI_COUNTS/get_rollup/GLOBAL_CUI_ROLLUP_UMLS2021AB_VID_13MAY2025.csv",
        help="Rollup mapping CSV with CHILD_CUI,ROLLUP_CUI",
    )
    args = p.parse_args()

    batch = args.batch
    input_dir = Path(args.input_dir)
    out_root = Path(args.output_root)

    daily_dir = out_root / "DAILY"
    month_dir = out_root / "MONTH"
    rollup_dir = out_root / "ROLLUP"
    log_dir = out_root / "log"

    # Ensure output dirs exist
    daily_dir.mkdir(parents=True, exist_ok=True)
    month_dir.mkdir(parents=True, exist_ok=True)
    rollup_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    infile = input_dir / f"batch_{batch}.csv"

    daily_out = daily_dir / f"daily_batch_{batch}.csv"
    month_out = month_dir / f"month_batch_{batch}.csv"

    rollup_daily_out = rollup_dir / f"rollup_daily_batch_{batch}.csv"
    rollup_month_out = rollup_dir / f"rollup_month_batch_{batch}.csv"

    logfile = log_dir / f"processing_batch{batch}.log"
    map_path = Path(args.map_file)

    start_time_iso = datetime.utcnow().isoformat(timespec="seconds") + "Z"

    # Track counts for both success + failure logs
    input_rows = 0
    after_dropna = 0
    invalid_date_rows = 0
    daily_rows = 0
    monthly_rows = 0
    rollup_daily_total = 0
    rollup_month_total = 0

    # Structured, ordered log helper (single summary file)
    def write_log(status, **kv):
        ordered_keys = [
            "batch",
            "input_file",
            "status",
            "start_time",
            "end_time",
            "input_rows",
            "rows_after_dropna",
            "invalid_date_rows",
            "daily_rows",
            "monthly_rows",
            "rollup_daily_rows",
            "rollup_month_rows",
            "message",
            "error_type",
        ]
        base = {
            "batch": str(batch),
            "input_file": str(infile),
            "status": status,
            "start_time": start_time_iso,
            "end_time": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "input_rows": str(kv.get("input_rows", "")),
            "rows_after_dropna": str(kv.get("rows_after_dropna", "")),
            "invalid_date_rows": str(kv.get("invalid_date_rows", "")),
            "daily_rows": str(kv.get("daily_rows", "")),
            "monthly_rows": str(kv.get("monthly_rows", "")),
            "rollup_daily_rows": str(kv.get("rollup_daily_rows", "")),
            "rollup_month_rows": str(kv.get("rollup_month_rows", "")),
            "message": kv.get("message", ""),
            "error_type": kv.get("error_type", ""),
        }
        lines = [f"{k}={base[k]}" for k in ordered_keys]
        logfile.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Guards
    if not infile.exists():
        write_log("MISSING", message="Input file not found")
        sys.exit(1)
    if not map_path.exists():
        write_log("MISSING_MAP", message="Rollup mapping file not found")
        sys.exit(1)

    try:
        # =========================
        # ORIGINAL DAILY + MONTH PIPELINE (same outputs, more robust IO)
        # =========================

        # Read only the first 4 columns as strings (robust to extra columns)
        df = pd.read_csv(
            infile,
            sep="|",
            dtype=str,
            header=None,
            usecols=[0, 1, 2, 3],
            names=["EMPI", "rd", "date", "cui"],
        )

        # Drop a header row if one slipped in (minimal safeguard)
        # (e.g., "EMPI|rd|date|cui" appears as first data row)
        hdr_mask = (
            df["EMPI"].astype(str).str.strip().str.lower().eq("empi")
            & df["date"].astype(str).str.strip().str.lower().eq("date")
        )
        if hdr_mask.any():
            df = df.loc[~hdr_mask].reset_index(drop=True)

        df = df[["EMPI", "date", "cui"]]
        input_rows = len(df)

        # Drop rows missing any required field
        df.dropna(inplace=True)
        after_dropna = len(df)

        # Normalize date; drop invalid dates (prevents blank/NaN dates in outputs)
        df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime("%Y-%m-%d")
        invalid_date_rows = int(df["date"].isna().sum())
        df = df.dropna(subset=["date"])

        # CUI explode/clean
        df["cui"] = df["cui"].str.split(",")
        df = df.explode("cui", ignore_index=True)
        df["cui"] = df["cui"].str.strip()

        # Keep only flags ending with 'Y', then strip that 'Y'
        df = df[df["cui"].notna() & (df["cui"] != "") & df["cui"].str.endswith("Y")]
        df["cui"] = df["cui"].str[:-1]
        df = df[df["cui"].notna() & (df["cui"] != "")]

        daily = df.drop_duplicates(["EMPI", "date", "cui"])
        daily_rows = len(daily)
        daily.to_csv(daily_out, index=False)

        del df
        gc.collect()

        # Compute month efficiently from normalized YYYY-MM-DD string
        daily["month"] = daily["date"].str.slice(5, 7) + "-" + daily["date"].str.slice(0, 4)

        # Monthly counts: daily is already unique per (EMPI,date,cui),
        # so groupby size gives "days per month" directly.
        monthly = (
            daily.dropna(subset=["month"])
            .groupby(["EMPI", "month", "cui"])
            .size()
            .reset_index(name="count")
        )
        monthly_rows = len(monthly)
        monthly.to_csv(month_out, index=False)

        del monthly
        gc.collect()

        # =========================
        # ROLLUP (YEAR-CHUNKED, APPEND OUTPUTS)
        # =========================

        map_df = pd.read_csv(
            map_path, dtype=str, usecols=["CHILD_CUI", "ROLLUP_CUI"]
        ).drop_duplicates()

        # Overwrite rollup outputs if they already exist
        if rollup_daily_out.exists():
            rollup_daily_out.unlink()
        if rollup_month_out.exists():
            rollup_month_out.unlink()

        daily_src = daily.dropna(subset=["EMPI", "date", "cui"])[
            ["EMPI", "date", "month", "cui"]
        ].copy()

        daily_src["year"] = pd.to_numeric(
            daily_src["date"].str.slice(0, 4), errors="coerce"
        ).astype("Int16")

        # Only iterate years present (faster + supports out-of-range years)
        years = sorted(daily_src["year"].dropna().unique().tolist())

        rollup_daily_header = True
        rollup_month_header = True

        for year in years:
            ysrc = daily_src[daily_src["year"] == year]
            if ysrc.empty:
                continue

            j = ysrc.merge(
                map_df,
                left_on="cui",
                right_on="CHILD_CUI",
                how="left",
                sort=False,
            )

            parents = j.dropna(subset=["ROLLUP_CUI"])[
                ["EMPI", "date", "month", "ROLLUP_CUI"]
            ].rename(columns={"ROLLUP_CUI": "parent_cui"})

            self_rows = ysrc[["EMPI", "date", "month", "cui"]].rename(
                columns={"cui": "parent_cui"}
            )

            rdu_full = (
                pd.concat([parents, self_rows], ignore_index=True)
                .drop_duplicates(subset=["EMPI", "date", "parent_cui"])
                .reset_index(drop=True)
            )

            # Rollup DAILY (append)
            rdu_full[["EMPI", "date", "parent_cui"]].to_csv(
                rollup_daily_out,
                mode="a",
                header=rollup_daily_header,
                index=False,
            )
            rollup_daily_header = False
            rollup_daily_total += len(rdu_full)

            # Rollup MONTH (append)
            rm = (
                rdu_full.dropna(subset=["month"])
                .groupby(["EMPI", "month", "parent_cui"])
                .size()
                .reset_index(name="count")
            )
            rm.to_csv(
                rollup_month_out,
                mode="a",
                header=rollup_month_header,
                index=False,
            )
            rollup_month_header = False
            rollup_month_total += len(rm)

            del ysrc, j, parents, self_rows, rdu_full, rm
            gc.collect()

        del daily_src, map_df, daily
        gc.collect()

        # SUCCESS log (this is the key missing piece in the original)
        write_log(
            "SUCCESS",
            input_rows=input_rows,
            rows_after_dropna=after_dropna,
            invalid_date_rows=invalid_date_rows,
            daily_rows=daily_rows,
            monthly_rows=monthly_rows,
            rollup_daily_rows=rollup_daily_total,
            rollup_month_rows=rollup_month_total,
            message="OK",
        )

    except Exception as e:
        err_type = type(e).__name__
        tb = traceback.format_exc()
        short_msg = f"{err_type}: {str(e).strip()}"

        write_log(
            "FAILED",
            input_rows=input_rows,
            rows_after_dropna=after_dropna,
            invalid_date_rows=invalid_date_rows,
            daily_rows=daily_rows,
            monthly_rows=monthly_rows,
            rollup_daily_rows=rollup_daily_total,
            rollup_month_rows=rollup_month_total,
            message=short_msg,
            error_type=err_type,
        )

        # Mirror full traceback to stderr so Slurm *.err captures detail
        sys.stderr.write(tb + "\n")
        sys.stderr.flush()
        sys.exit(1)


if __name__ == "__main__":
    main()

