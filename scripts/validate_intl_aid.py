#!/usr/bin/env python3
"""
validate_intl_aid.py — flag suspect rows in data/manual/intl_aid.csv.

Flagging rules (any one is sufficient):
  - pct_intl_aided outside [0, 1]
  - avg_intl_award > school's cost_international (award exceeds total billed cost)
  - cds_year older than 2022-23
  - pct_intl_aided or avg_intl_award is present but source_url is blank

Flagged rows get quality = "flagged"; all others get quality = "ok".
Writes the result back to intl_aid.csv in-place.
Exits non-zero if any row is flagged.
"""

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
AID_PATH = ROOT / "data" / "manual" / "intl_aid.csv"
SCHOOLS_PATH = ROOT / "data" / "processed" / "schools_with_sevp.csv"

MIN_CDS_YEAR = "2022-23"


def _year_ok(year_str) -> bool:
    """Return True if cds_year is 2022-23 or newer."""
    if pd.isna(year_str) or str(year_str).strip() == "":
        return True  # blank → no data, not a stale data problem
    try:
        start = int(str(year_str).strip()[:4])
        return start >= 2022
    except ValueError:
        return False  # unparseable → flag it


def validate(aid_path: Path = AID_PATH, schools_path: Path = SCHOOLS_PATH) -> pd.DataFrame:
    aid = pd.read_csv(aid_path, comment="#")
    aid = aid[pd.to_numeric(aid["unitid"], errors="coerce").notna()].copy()
    aid["unitid"] = aid["unitid"].astype(int)
    aid["avg_intl_award"] = pd.to_numeric(aid["avg_intl_award"], errors="coerce")
    aid["pct_intl_aided"] = pd.to_numeric(aid["pct_intl_aided"], errors="coerce")
    if "cds_total_cost" in aid.columns:
        aid["cds_total_cost"] = pd.to_numeric(aid["cds_total_cost"], errors="coerce")
    else:
        aid["cds_total_cost"] = float("nan")

    schools = pd.read_csv(schools_path, usecols=["unit_id", "cost_international"])
    schools = schools.rename(columns={"unit_id": "unitid"})
    schools["unitid"] = schools["unitid"].astype(int)

    merged = aid.merge(schools, on="unitid", how="left")

    reasons: list[list[str]] = [[] for _ in range(len(merged))]

    # Rule 1: pct_intl_aided out of range
    mask = merged["pct_intl_aided"].notna() & (
        (merged["pct_intl_aided"] < 0) | (merged["pct_intl_aided"] > 1)
    )
    for i in merged[mask].index:
        reasons[i].append(f"pct_intl_aided={merged.at[i,'pct_intl_aided']:.4f} outside [0,1]")

    # Rule 2: avg_intl_award > cost ceiling (use cds_total_cost×1.05 when available, else cost_international)
    has_award = merged["avg_intl_award"].notna()
    has_cds_cost = merged["cds_total_cost"].notna()
    has_ipeds_cost = merged["cost_international"].notna()
    # When CDS cost present: flag if award > cds_total_cost * 1.05
    over_cds = has_award & has_cds_cost & (merged["avg_intl_award"] > merged["cds_total_cost"] * 1.05)
    for i in merged[over_cds].index:
        reasons[i].append(
            f"avg_intl_award={merged.at[i,'avg_intl_award']:,.0f} > "
            f"cds_total_cost×1.05={merged.at[i,'cds_total_cost']*1.05:,.0f}"
        )
    # When CDS cost absent: fall back to IPEDS cost_international (strict equality)
    over_ipeds = has_award & ~has_cds_cost & has_ipeds_cost & (merged["avg_intl_award"] > merged["cost_international"])
    for i in merged[over_ipeds].index:
        reasons[i].append(
            f"avg_intl_award={merged.at[i,'avg_intl_award']:,.0f} > "
            f"cost_international={merged.at[i,'cost_international']:,.0f} (no cds_total_cost)"
        )

    # Rule 3: cds_year too old
    for i, row in merged.iterrows():
        if not _year_ok(row.get("cds_year")):
            reasons[i].append(f"cds_year={row['cds_year']} older than {MIN_CDS_YEAR}")

    # Rule 4: numbers present but source_url missing
    has_numbers = merged["avg_intl_award"].notna() | merged["pct_intl_aided"].notna()
    no_source = merged["source_url"].isna() | (merged["source_url"].astype(str).str.strip() == "")
    for i in merged[has_numbers & no_source].index:
        reasons[i].append("H6 numbers present but source_url is blank")

    merged["quality"] = ["flagged" if r else "ok" for r in reasons]
    merged["flag_reason"] = ["; ".join(r) for r in reasons]

    # Drop the IPEDS join column before writing back (keep cds_total_cost from aid)
    out = merged.drop(columns=["cost_international", "flag_reason"], errors="ignore")
    # Drop flag_reason from aid (we print it but don't persist it)
    # Keep quality column in the output
    # Preserve original column order, appending quality at the end if new
    orig_cols = list(pd.read_csv(aid_path, comment="#", nrows=0).columns)
    if "quality" not in orig_cols:
        orig_cols.append("quality")
    out = out[[c for c in orig_cols if c in out.columns]]
    out.to_csv(aid_path, index=False)

    # Return merged (with flag_reason) for reporting
    return merged


def main() -> int:
    result = validate()
    flagged = result[result["quality"] == "flagged"]
    ok_count = (result["quality"] == "ok").sum()
    print(f"Validated {len(result)} rows: {ok_count} ok, {len(flagged)} flagged.")
    if not flagged.empty:
        print("\nFlagged rows:")
        for _, row in flagged.iterrows():
            print(f"  unitid={row['unitid']} ({row.get('flag_reason','')})")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
