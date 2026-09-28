"""
Upsert helper for data/manual/intl_aid.csv.

Use this instead of pd.concat() to merge batch results into the CSV.
It guarantees:
  - existing rows are updated (not duplicated)
  - rows not in the batch are never dropped
  - row count never decreases
"""

import sys
from pathlib import Path

import pandas as pd

AID_PATH = Path(__file__).parent.parent / "data" / "manual" / "intl_aid.csv"


def upsert_rows(new_rows: pd.DataFrame, aid_path: Path = AID_PATH) -> pd.DataFrame:
    """Load intl_aid.csv, upsert new_rows by unitid, write back, return combined df.

    Args:
        new_rows: DataFrame with the same columns as intl_aid.csv.  Must include
                  a 'unitid' column.  New rows are appended; existing unitids are
                  updated with non-null values from new_rows (null values in
                  new_rows do NOT overwrite existing data).
        aid_path: Path to intl_aid.csv (default: the repo's canonical location).

    Returns:
        The merged DataFrame (also written to aid_path).
    """
    existing = pd.read_csv(aid_path)
    existing["unitid"] = existing["unitid"].astype(int)
    new_rows = new_rows.copy()
    new_rows["unitid"] = new_rows["unitid"].astype(int)

    before = len(existing)
    cols = list(existing.columns)

    # Index both on unitid
    ex = existing.set_index("unitid")
    nr = new_rows.set_index("unitid").reindex(columns=[c for c in cols if c != "unitid"])

    # Update existing rows (only non-null values from new_rows win)
    overlap = nr.index[nr.index.isin(ex.index)]
    for uid in overlap:
        for col in nr.columns:
            val = nr.at[uid, col]
            if pd.notna(val) and str(val).strip() not in ("", "nan", "None"):
                ex.at[uid, col] = val

    # Append brand-new rows
    new_only = nr[~nr.index.isin(ex.index)]
    combined = pd.concat([ex, new_only]).reset_index()
    combined = combined[cols]

    after = len(combined)
    assert after >= before, f"upsert_rows: row count decreased {before} → {after} (bug!)"

    combined.to_csv(aid_path, index=False)
    print(f"upsert_intl_aid: {before} → {after} rows "
          f"({len(overlap)} updated, {len(new_only)} added)")
    return combined


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/upsert_intl_aid.py <new_rows.csv>")
        sys.exit(1)
    new_df = pd.read_csv(sys.argv[1])
    upsert_rows(new_df)
