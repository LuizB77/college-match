"""
Generate match fixtures for 5 canonical client profiles.

Output: export/match_fixtures.json

Usage:
    python scripts/export_match_fixtures.py
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from src.matcher import load_data, load_program_earnings, match, explain_exclusion

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
df = load_data(ROOT / "data/processed/schools_with_majors.csv")
pe = load_program_earnings(str(ROOT / "data/processed/program_earnings.csv"))
alumni_path = ROOT / "data/processed/notable_alumni.csv"
alumni_df = (
    pd.read_csv(alumni_path, dtype={"unit_id": int, "sitelinks": int})
    if alumni_path.exists()
    else None
)

# ---------------------------------------------------------------------------
# Profiles
# ---------------------------------------------------------------------------
PROFILES = [
    {
        "id": "soccer_men",
        "client": {
            "require_f1": True,
            "max_budget": 25_000,
            "budget_flex": 1.5,
            "school_types": ["2-year", "4-year"],
            "sport": "Soccer",
            "gender": "men",
            "needs_athletic_scholarship": True,
            "min_grad_rate_4yr": 0.30,
            "min_grad_rate_2yr": 0.20,
            "majors": ["52"],
            "strict_major": False,
            "religion": None,
            "weights": {
                "low_cost": 5, "grad_rate": 3, "sport_culture": 2,
                "athlete_opportunity": 4, "international_community": 3,
                "open_admission": 0, "small_school": 1,
                "entrepreneurship_program": 2,
            },
        },
    },
    {
        "id": "volleyball_women",
        "client": {
            "require_f1": True,
            "max_budget": 30_000,
            "budget_flex": 1.5,
            "school_types": ["2-year", "4-year"],
            "sport": "Volleyball",
            "gender": "women",
            "needs_athletic_scholarship": True,
            "min_grad_rate_4yr": 0.40,
            "min_grad_rate_2yr": 0.25,
            "majors": ["31"],
            "strict_major": False,
            "religion": None,
            "weights": {
                "low_cost": 4, "grad_rate": 4, "sport_culture": 3,
                "athlete_opportunity": 5, "international_community": 2,
                "open_admission": 0, "small_school": 2,
                "entrepreneurship_program": 0,
            },
        },
    },
    {
        "id": "business_gems",
        "client": {
            "require_f1": True,
            "max_budget": None,
            "school_types": ["4-year"],
            "needs_athletic_scholarship": False,
            "min_grad_rate_4yr": 0.50,
            "majors": ["52"],
            "strict_major": True,
            "hidden_gems_only": True,
            "religion": None,
            "weights": {
                "low_cost": 3, "grad_rate": 4, "sport_culture": 0,
                "athlete_opportunity": 0, "international_community": 3,
                "open_admission": 0, "small_school": 2,
                "entrepreneurship_program": 5,
                "program_strength": 4,
            },
        },
    },
    {
        "id": "transfer_4yr",
        "client": {
            "require_f1": True,
            "max_budget": 35_000,
            "budget_flex": 1.0,
            "school_types": ["4-year"],
            "sport": "Basketball",
            "gender": "men",
            "needs_athletic_scholarship": False,
            "min_grad_rate_4yr": 0.35,
            "majors": ["52"],
            "strict_major": False,
            "religion": None,
            "weights": {
                "low_cost": 4, "grad_rate": 5, "sport_culture": 1,
                "athlete_opportunity": 3, "international_community": 2,
                "open_admission": 0, "small_school": 1,
                "entrepreneurship_program": 1,
            },
        },
    },
    {
        "id": "catholic",
        "client": {
            "require_f1": True,
            "max_budget": 50_000,
            "budget_flex": 1.0,
            "school_types": ["4-year"],
            "sport": "Soccer",
            "gender": "women",
            "needs_athletic_scholarship": False,
            "min_grad_rate_4yr": 0.50,
            "religion": "catholic",
            "weights": {
                "low_cost": 2, "grad_rate": 5, "sport_culture": 2,
                "athlete_opportunity": 3, "international_community": 4,
                "open_admission": 0, "small_school": 1,
                "entrepreneurship_program": 1,
            },
        },
    },
]


def run_profile(profile: dict) -> dict:
    pid = profile["id"]
    client = profile["client"]

    # Run match
    results, funnel = match(df, client, program_earnings=pe, alumni_df=alumni_df)

    # Secondary sort: break ties deterministically by unit_id ascending
    results = results.sort_values(["match_score", "unit_id"], ascending=[False, True])

    ranked_unit_ids = results["unit_id"].astype(int).tolist()
    scores = {str(uid): round(float(score), 1)
              for uid, score in zip(results["unit_id"], results["match_score"])}

    # Build funnel as list of [label, count] pairs
    funnel_out = [[label, count] for label, count in funnel]

    # --- Collect sample schools for explain_exclusion ---
    # Top 15 matched schools (will have empty reasons)
    top15_ids = set(ranked_unit_ids[:15])

    # For excluded schools: iterate df in unit_id order, collect first example
    # of each unique first-reason string (up to 15 examples).
    matched_ids = set(ranked_unit_ids)
    exclusion_examples: dict[str, int] = {}  # first_reason -> unit_id
    df_sorted = df.sort_values("unit_id")
    for _, row in df_sorted.iterrows():
        if len(exclusion_examples) >= 15:
            break
        uid = int(row["unit_id"])
        if uid in matched_ids:
            continue
        reasons = explain_exclusion(row, client, pe, full_df=df, alumni_df=alumni_df)
        if reasons:
            first_reason = reasons[0]
            if first_reason not in exclusion_examples:
                exclusion_examples[first_reason] = uid

    excluded_sample_ids = set(exclusion_examples.values())

    # All sample IDs
    all_sample_ids = top15_ids | excluded_sample_ids

    # Run explain_exclusion for all samples
    # Use boolean mask (not set_index) so row.name stays the integer index position,
    # which is required for ps_series.get(row.name, 0.5) inside explain_exclusion.
    explain_out: dict[str, list[str]] = {}
    for uid in all_sample_ids:
        mask = df["unit_id"] == uid
        if mask.any():
            row = df[mask].iloc[0]
            reasons = explain_exclusion(row, client, pe, full_df=df, alumni_df=alumni_df)
            explain_out[str(uid)] = reasons

    print(
        f"  {pid}: {len(ranked_unit_ids)} ranked schools, "
        f"{len(explain_out)} explain_exclusion entries "
        f"({len(top15_ids)} top-15, {len(excluded_sample_ids)} exclusion examples)"
    )

    return {
        "id": pid,
        "client": client,
        "ranked_unit_ids": ranked_unit_ids,
        "scores": scores,
        "funnel": funnel_out,
        "explain_exclusion": explain_out,
    }


def main():
    output_profiles = []
    for profile in PROFILES:
        print(f"Processing profile: {profile['id']}")
        output_profiles.append(run_profile(profile))

    fixture = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "profiles": output_profiles,
    }

    out_path = ROOT / "export" / "match_fixtures.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(fixture, f, ensure_ascii=False, separators=(",", ":"))

    print(f"\nWrote match fixtures to {out_path}")


if __name__ == "__main__":
    main()
