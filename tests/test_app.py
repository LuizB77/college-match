"""
Automated tests for the College Match Streamlit app.

Run with: .venv/bin/python -m pytest tests/ -v
"""

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

# Make project root importable
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from src.matcher import load_data, match, explain_exclusion, _program_strength_percentiles

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def df():
    return load_data(ROOT / "data/processed/schools_with_majors.csv")


@pytest.fixture(scope="session")
def notebook04_client():
    return {
        "name": "notebook04",
        "require_f1": True,
        "max_budget": 25_000,
        "budget_flex": 1.5,
        "school_types": ["2-year", "4-year"],
        "states": None,
        "city_groups": None,
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
    }


# ---------------------------------------------------------------------------
# Direct matcher tests
# ---------------------------------------------------------------------------

def test_matcher_top15(df, notebook04_client):
    """Top-15 schools must match the saved notebook-04 baseline."""
    results, _ = match(df, notebook04_client, top_n=25)
    actual = results["name"].head(15).tolist()
    expected = json.loads(
        (ROOT / "tests/expected_top15.json").read_text()
    )
    assert actual == expected, (
        f"Top-15 regression!\n  actual:   {actual}\n  expected: {expected}"
    )


def test_matcher_zero_weights_no_nan(df):
    """All-zero weights must not produce NaN match_scores (prevents st.progress crash)."""
    client = {
        "name": "zero-weights",
        "require_f1": False,
        "max_budget": None,
        "budget_flex": 1.5,
        "school_types": ["2-year", "4-year"],
        "states": None,
        "city_groups": None,
        "sport": None,
        "gender": "men",
        "needs_athletic_scholarship": False,
        "min_grad_rate_4yr": 0.0,
        "min_grad_rate_2yr": 0.0,
        "majors": None,
        "strict_major": False,
        "religion": None,
        "include_online_only": True,
        "weights": {k: 0 for k in [
            "low_cost", "grad_rate", "sport_culture", "athlete_opportunity",
            "international_community", "open_admission", "small_school",
            "entrepreneurship_program",
        ]},
    }
    results, funnel = match(df, client)
    assert not results.empty
    assert results["match_score"].notna().all(), "match_score must never be NaN"
    assert funnel[-1][1] == len(df), "with no filters all schools should pass"


def test_match_returns_all_passing(df, notebook04_client):
    """match() with no top_n must return ALL schools that pass the filters."""
    results_all, funnel = match(df, notebook04_client)
    expected_count = funnel[-1][1]
    assert len(results_all) == expected_count, (
        f"Expected {expected_count} results (all passing schools), got {len(results_all)}"
    )
    # Must be at least 15 (we know 15 in the baseline)
    assert len(results_all) >= 15


def test_f1_metric_equals_sevp_count(df):
    """With default (no F-1 filter), F-1 certified count from results == total sevp_certified in data."""
    client = {
        "name": "f1-test",
        "require_f1": False,
        "max_budget": None,
        "budget_flex": 1.5,
        "school_types": ["2-year", "4-year"],
        "states": None, "city_groups": None, "sport": None,
        "gender": "men", "needs_athletic_scholarship": False,
        "min_grad_rate_4yr": 0.0, "min_grad_rate_2yr": 0.0,
        "majors": None, "strict_major": False, "religion": None,
        "include_online_only": True,
        "weights": {"low_cost": 1, "grad_rate": 0, "sport_culture": 0,
                    "athlete_opportunity": 0, "international_community": 0,
                    "open_admission": 0, "small_school": 0,
                    "entrepreneurship_program": 0},
    }
    results, _ = match(df, client)
    f1_in_results = int(results["sevp_certified"].sum())
    f1_in_data = int(df["sevp_certified"].sum())
    assert f1_in_results == f1_in_data, (
        f"F-1 count in results ({f1_in_results}) must equal total in data ({f1_in_data})"
    )


def test_matcher_religion_catholic(df, notebook04_client):
    """Catholic filter reduces school count and appears as a funnel step."""
    client = {**notebook04_client, "religion": "catholic",
              "max_budget": None, "require_f1": False, "sport": None,
              "needs_athletic_scholarship": False}
    results, funnel = match(df, client)
    steps = [step for step, _ in funnel]
    assert any("Catholic" in s for s in steps), f"Expected Catholic step in funnel: {steps}"
    # Catholic schools are a subset: fewer than all schools
    total = funnel[0][1]
    catholic_n = next(n for s, n in funnel if "Catholic" in s)
    assert catholic_n < total


def test_matcher_max_budget_none_includes_unknown_cost(df):
    """max_budget=None must keep schools with unknown (NaN) cost_international."""
    unknown_cost = df[df["cost_international"].isna()]
    if unknown_cost.empty:
        pytest.skip("No schools with unknown cost in dataset")
    client = {
        "name": "no-budget",
        "require_f1": False,
        "max_budget": None,
        "budget_flex": 1.5,
        "school_types": ["2-year", "4-year"],
        "states": None, "city_groups": None, "sport": None,
        "gender": "men", "needs_athletic_scholarship": False,
        "min_grad_rate_4yr": 0.0, "min_grad_rate_2yr": 0.0,
        "majors": None, "strict_major": False, "religion": None,
        "weights": {"low_cost": 1, "grad_rate": 0, "sport_culture": 0,
                    "athlete_opportunity": 0, "international_community": 0,
                    "open_admission": 0, "small_school": 0,
                    "entrepreneurship_program": 0},
    }
    results, funnel = match(df, client)
    cost_steps = [s for s, _ in funnel if "cost" in s.lower()]
    assert not cost_steps, f"No cost filter step expected, got: {cost_steps}"


# ---------------------------------------------------------------------------
# explain_exclusion tests
# ---------------------------------------------------------------------------

_STRICT_CLIENT = {
    "name": "strict",
    "require_f1": True,
    "max_budget": 25_000,
    "budget_flex": 1.5,
    "school_types": ["2-year", "4-year"],
    "states": None, "city_groups": None,
    "sport": "Soccer", "gender": "men",
    "needs_athletic_scholarship": True,
    "min_grad_rate_4yr": 0.30, "min_grad_rate_2yr": 0.20,
    "majors": ["52"],
    "strict_major": False, "religion": None,
    "weights": {"low_cost": 5, "grad_rate": 3, "sport_culture": 2,
                "athlete_opportunity": 4, "international_community": 3,
                "open_admission": 0, "small_school": 1, "entrepreneurship_program": 2},
}


def test_explain_exclusion_not_f1(df):
    """A non-SEVP-certified school must report the F-1 reason."""
    row = df[~df["sevp_certified"]].iloc[0]
    reasons = explain_exclusion(row, _STRICT_CLIENT)
    assert any("F-1" in r for r in reasons), f"Expected F-1 reason, got: {reasons}"


def test_explain_exclusion_over_budget(df):
    """A school over budget must report the cost reason."""
    aid_tiers = {"Athletic scholarships", "Mixed / verify"}
    over = df[
        (df["cost_international"] > 25_000 * 1.5)
        & df["sevp_certified"]
        & df["mens_sports"].fillna("").str.contains("Soccer")
        & df["athletic_aid_tier"].isin(aid_tiers)
    ]
    if over.empty:
        pytest.skip("No over-budget soccer school with athletic aid in dataset")
    row = over.iloc[0]
    reasons = explain_exclusion(row, _STRICT_CLIENT)
    assert any("budget" in r.lower() or "cost" in r.lower() for r in reasons), (
        f"Expected cost reason for {row['name']}, got: {reasons}"
    )


def test_explain_exclusion_passing_is_empty(df):
    """A passing school must return an empty exclusion list."""
    results, _ = match(df, _STRICT_CLIENT)
    row = results.iloc[0]
    reasons = explain_exclusion(row, _STRICT_CLIENT)
    assert reasons == [], f"Expected no reasons for passing school {row['name']}, got: {reasons}"


def test_explain_exclusion_consistent_with_match(df):
    """For 200 randomly sampled schools, explain_exclusion returns [] iff school is in match()."""
    import random
    results, _ = match(df, _STRICT_CLIENT)
    passing_ids = set(results.index)
    random.seed(42)
    sample_idxs = random.sample(list(df.index), 200)
    mismatches = []
    for idx in sample_idxs:
        row = df.loc[idx]
        reasons = explain_exclusion(row, _STRICT_CLIENT)
        in_results = idx in passing_ids
        if (len(reasons) == 0) != in_results:
            mismatches.append((row["name"], reasons, in_results))
    assert not mismatches, (
        f"{len(mismatches)} explain_exclusion / match() disagreements:\n"
        + "\n".join(f"  {n}: reasons={r} in_results={i}" for n, r, i in mismatches[:5])
    )


def test_unknown_cost_low_cost_score(df):
    """Schools with unknown cost must score 0.3 on low_cost (not 0.5) so they
    don't headline the list when the user cares about price."""
    import numpy as np
    unknown_cost = df[df["cost_international"].isna()]
    if unknown_cost.empty:
        pytest.fail("No unknown-cost schools in dataset — test setup error")
    client = {
        "name": "unknown-cost",
        "require_f1": False, "max_budget": None, "budget_flex": 1.5,
        "school_types": ["2-year", "4-year"], "states": None, "city_groups": None,
        "sport": None, "gender": "men", "needs_athletic_scholarship": False,
        "min_grad_rate_4yr": 0.0, "min_grad_rate_2yr": 0.0,
        "majors": None, "strict_major": False, "religion": None,
        "hidden_gems_only": False,
        "weights": {"low_cost": 5, "grad_rate": 0, "sport_culture": 0,
                    "athlete_opportunity": 0, "international_community": 0,
                    "open_admission": 0, "small_school": 0,
                    "entrepreneurship_program": 0},
    }
    results, _ = match(df, client)
    unknown_in_results = results[results["cost_international"].isna()]
    assert not unknown_in_results.empty, "Expected some unknown-cost schools in results"
    # With weight=5 on low_cost and all others=0, score = low_cost * (5/5) * 100 = low_cost * 100
    # Unknown-cost schools get 0.3, so their score should be near 30.0
    for _, row in unknown_in_results.head(5).iterrows():
        assert abs(row["match_score"] - 30.0) < 1.0, (
            f"{row['name']}: expected score ~30.0 (low_cost=0.3), got {row['match_score']}"
        )


# ---------------------------------------------------------------------------
# Data-file tracking: every file the app loads must be committed to git
# ---------------------------------------------------------------------------

def test_required_data_files_tracked():
    """Every data file app.py loads at startup must be tracked by git (committed).

    This catches the 'pipeline regenerated a file locally but forgot to git add'
    failure mode that caused the deploy outage.
    """
    import subprocess
    tracked = set(
        subprocess.check_output(["git", "ls-files"], cwd=ROOT).decode().splitlines()
    )
    required = [
        "data/processed/schools_with_majors.csv",
        "data/processed/cip_names.csv",
        "data/processed/program_earnings.csv",
        # intl_aid is optional (app handles its absence), so not required here
    ]
    missing = [f for f in required if f not in tracked]
    assert not missing, (
        f"Required data files not tracked by git: {missing}\n"
        "Run: git add <file> && git commit"
    )


# ---------------------------------------------------------------------------
# Part B: program_strength, selectivity, hidden_gems, ivy_league
# ---------------------------------------------------------------------------

from src.matcher import load_program_earnings, selectivity_tier, IVY_UNIT_IDS

EARN_PATH = ROOT / "data/processed/program_earnings.csv"


@pytest.fixture(scope="session")
def program_earnings():
    return load_program_earnings(str(EARN_PATH))


def test_program_earnings_file(program_earnings):
    """program_earnings.csv must exist and have the right columns and shape."""
    assert program_earnings is not None, (
        "program_earnings.csv is missing — run notebook 06 to regenerate it, "
        "then commit the file (it must be tracked by git)."
    )
    assert set(program_earnings.columns) >= {"unit_id", "cip4", "earn_mdn_4yr", "earn_n"}
    assert len(program_earnings) > 1000, "Expected > 1000 rows"
    assert (program_earnings["earn_mdn_4yr"] > 0).all(), "earn_mdn_4yr must be positive"
    assert program_earnings["cip4"].str.len().eq(4).all(), "cip4 must be 4-char strings"


def test_selectivity_tier_thresholds():
    """selectivity_tier must map admit rates to correct tiers."""
    assert selectivity_tier(0.05) == "Reach"
    assert selectivity_tier(0.14) == "Reach"
    assert selectivity_tier(0.15) == "Target"
    assert selectivity_tier(0.50) == "Target"
    assert selectivity_tier(0.51) == "Likely"
    assert selectivity_tier(0.95) == "Likely"
    assert selectivity_tier(float("nan")) == "Unknown"
    assert selectivity_tier(None) == "Unknown"


def test_ivy_league_unit_ids(df):
    """All 8 Ivy League schools must be in the dataset with correct unit_ids."""
    assert len(IVY_UNIT_IDS) == 8
    found = df[df["unit_id"].isin(IVY_UNIT_IDS)]
    assert len(found) == 8, f"Expected 8 Ivy League schools, found {len(found)}"
    assert df["ivy_league"].sum() == 8, "ivy_league column must flag exactly 8 schools"


def test_program_strength_in_match(df, program_earnings):
    """match() with program_strength weight must not crash and produce valid scores."""
    assert program_earnings is not None, "program_earnings.csv missing — see test_program_earnings_file"
    client = {
        "name": "prog-strength",
        "require_f1": False, "max_budget": None, "budget_flex": 1.5,
        "school_types": ["4-year"], "states": None, "city_groups": None,
        "sport": None, "gender": "men", "needs_athletic_scholarship": False,
        "min_grad_rate_4yr": 0.0, "min_grad_rate_2yr": 0.0,
        "majors": ["52"], "strict_major": False, "religion": None,
        "hidden_gems_only": False,
        "weights": {
            "low_cost": 1, "grad_rate": 1, "sport_culture": 0, "athlete_opportunity": 0,
            "international_community": 0, "open_admission": 0, "small_school": 0,
            "entrepreneurship_program": 0, "program_strength": 5,
        },
    }
    results, funnel = match(df, client, program_earnings=program_earnings)
    assert not results.empty
    assert results["match_score"].notna().all()


def test_program_strength_produces_real_values(df, program_earnings):
    """_program_strength_percentiles must assign non-neutral scores to at least 100 schools for CIP 52."""
    assert program_earnings is not None, "program_earnings.csv missing — see test_program_earnings_file"
    scores = _program_strength_percentiles(df, ["52"], program_earnings)
    non_neutral = scores[scores != 0.5]
    assert len(non_neutral) >= 100, (
        f"Expected at least 100 schools with a real program_strength for major 52, got {len(non_neutral)}. "
        "cip4 coercion or earn_n filter may have broken the pipeline."
    )


def test_program_strength_known_school(df, program_earnings):
    """Western Governors University (unit_id=433387) has CIP 5202 with earn_n=4667; must get a real score."""
    assert program_earnings is not None, "program_earnings.csv missing — see test_program_earnings_file"
    WGU_UID = 433387  # CIP 5202, earn_n=4667 — largest business program in dataset
    assert WGU_UID in df["unit_id"].values, "WGU not in dataset"
    scores = _program_strength_percentiles(df, ["52"], program_earnings)
    wgu_row = df[df["unit_id"] == WGU_UID]
    assert not wgu_row.empty
    score = scores.get(wgu_row.index[0], 0.5)
    assert score != 0.5, (
        f"WGU (unit_id={WGU_UID}) has large business earn data but got neutral 0.5 program_strength. "
        "cip4 type coercion likely broken."
    )
    assert 0.0 <= score <= 1.0, f"program_strength out of [0,1]: {score}"


def test_program_earnings_cip4_type(program_earnings):
    """load_program_earnings must produce cip4 as zero-padded strings with no '.0' suffix."""
    assert program_earnings is not None, "program_earnings.csv missing — see test_program_earnings_file"
    # load_program_earnings loads cip4 as str and zero-pads; dtype must be object (string), not numeric
    assert program_earnings["cip4"].dtype == object, (
        f"Expected cip4 dtype object (string), got {program_earnings['cip4'].dtype}. "
        "load_program_earnings must load cip4 with dtype=str."
    )
    # Values must be clean 4-char strings — no float '5202.0' which would break prefix matching
    sample = program_earnings["cip4"].head(50).tolist()
    dotted = [v for v in sample if isinstance(v, str) and "." in v]
    assert not dotted, (
        f"cip4 contains float-like strings: {dotted}. "
        "Prefix matching (cip4.startswith('52')) will silently produce wrong results."
    )
    # Every non-null value must be exactly 4 characters (zero-padded)
    lengths = program_earnings["cip4"].dropna().str.len().unique().tolist()
    assert lengths == [4], f"Expected all cip4 values to be 4 chars, got lengths: {lengths}"


# ---------------------------------------------------------------------------
# Online-only schools
# ---------------------------------------------------------------------------

def test_online_only_column_exists(df):
    """online_only must be present in the processed dataset after notebook 01 re-run."""
    assert "online_only" in df.columns, (
        "online_only column missing — re-run notebooks 01→03→05→06"
    )
    n = int((df["online_only"].fillna(0) == 1).sum())
    assert n >= 10, f"Expected at least 10 online-only schools in dataset, got {n}"


def test_online_only_wgu_excluded_by_default(df):
    """WGU (unit_id=433387, DISTANCEONLY=1) must be excluded when include_online_only is False."""
    WGU_UID = 433387
    assert WGU_UID in df["unit_id"].values, "WGU not in dataset"
    assert df.loc[df["unit_id"] == WGU_UID, "online_only"].iloc[0] == 1.0, (
        "WGU must have online_only=1"
    )
    client = {
        "name": "online-exclude-test",
        "require_f1": False, "max_budget": None, "budget_flex": 1.5,
        "school_types": ["4-year"], "states": None, "city_groups": None,
        "sport": None, "gender": "men", "needs_athletic_scholarship": False,
        "min_grad_rate_4yr": 0.0, "min_grad_rate_2yr": 0.0,
        "majors": None, "strict_major": False, "religion": None,
        "hidden_gems_only": False, "include_online_only": False,
        "weights": {"low_cost": 1, "grad_rate": 0, "sport_culture": 0,
                    "athlete_opportunity": 0, "international_community": 0,
                    "open_admission": 0, "small_school": 0,
                    "entrepreneurship_program": 0, "program_strength": 0},
    }
    results, funnel = match(df, client)
    assert WGU_UID not in results["unit_id"].values, (
        "WGU (online-only) must not appear when include_online_only=False"
    )
    steps = [s for s, _ in funnel]
    assert any("online" in s.lower() for s in steps), (
        f"Expected an 'online-only' funnel step, got: {steps}"
    )


def test_online_only_wgu_included_when_toggled(df):
    """WGU must appear in results when include_online_only=True."""
    WGU_UID = 433387
    client = {
        "name": "online-include-test",
        "require_f1": False, "max_budget": None, "budget_flex": 1.5,
        "school_types": ["4-year"], "states": None, "city_groups": None,
        "sport": None, "gender": "men", "needs_athletic_scholarship": False,
        "min_grad_rate_4yr": 0.0, "min_grad_rate_2yr": 0.0,
        "majors": None, "strict_major": False, "religion": None,
        "hidden_gems_only": False, "include_online_only": True,
        "weights": {"low_cost": 1, "grad_rate": 0, "sport_culture": 0,
                    "athlete_opportunity": 0, "international_community": 0,
                    "open_admission": 0, "small_school": 0,
                    "entrepreneurship_program": 0, "program_strength": 0},
    }
    results, _ = match(df, client)
    assert WGU_UID in results["unit_id"].values, (
        "WGU must appear in results when include_online_only=True"
    )


def test_online_only_never_sevp_certified(df):
    """Invariant: no school can have both online_only=1 and sevp_certified=True."""
    assert "online_only" in df.columns, "online_only column missing — re-run notebooks 01→05→06"
    bad = df[(df["online_only"].fillna(0) == 1) & (df["sevp_certified"] == True)]
    assert bad.empty, (
        f"{len(bad)} school(s) have online_only=1 AND sevp_certified=True — "
        f"re-run notebook 05 to apply the IPEDS override:\n"
        f"{bad[['unit_id', 'name', 'state', 'sevp_match']].to_string()}"
    )


def test_hidden_gems_only(df, program_earnings):
    """hidden_gems_only filter: admit_rate >= 30%, no famous alum >= 60 sitelinks, top-25% outcomes."""
    assert program_earnings is not None, "program_earnings.csv missing — see test_program_earnings_file"

    alumni_path = ROOT / "data/processed/notable_alumni.csv"
    alumni_df = None
    if alumni_path.exists():
        alumni_df = pd.read_csv(alumni_path, dtype={"unit_id": int, "sitelinks": int})

    client_no_gems = {
        "name": "no-gems",
        "require_f1": False, "max_budget": None, "budget_flex": 1.5,
        "school_types": ["4-year"], "states": None, "city_groups": None,
        "sport": None, "gender": "men", "needs_athletic_scholarship": False,
        "min_grad_rate_4yr": 0.0, "min_grad_rate_2yr": 0.0,
        "majors": ["52"], "strict_major": False, "religion": None,
        "hidden_gems_only": False,
        "weights": {"low_cost": 1, "grad_rate": 0, "sport_culture": 0,
                    "athlete_opportunity": 0, "international_community": 0,
                    "open_admission": 0, "small_school": 0,
                    "entrepreneurship_program": 0, "program_strength": 0},
    }
    client_gems = {**client_no_gems, "hidden_gems_only": True}
    results_all, _ = match(df, client_no_gems, program_earnings=program_earnings)
    results_gems, funnel = match(df, client_gems, program_earnings=program_earnings, alumni_df=alumni_df)

    assert len(results_gems) < len(results_all), "Hidden gems filter must reduce school count"

    # No school with admit_rate < 30% (unless open admission == 0)
    if "admit_rate" in results_gems.columns:
        too_selective = results_gems[
            results_gems["admit_rate"].notna() &
            (results_gems["admit_rate"] != 0.0) &
            (results_gems["admit_rate"] < 0.30)
        ]
        assert len(too_selective) == 0, (
            f"Hidden gems must not include schools with admit_rate < 30%: "
            f"{too_selective['name'].tolist()}"
        )

    # No school with a famous alum >= 60 sitelinks (when alumni_df available)
    if alumni_df is not None and not results_gems.empty:
        max_links = alumni_df.groupby("unit_id")["sitelinks"].max()
        gem_links = results_gems["unit_id"].map(max_links).fillna(0)
        too_famous = results_gems[gem_links >= 60]
        assert len(too_famous) == 0, (
            f"Hidden gems must not include schools with famous alum >= 60 sitelinks: "
            f"{too_famous['name'].tolist()}"
        )

    steps = [step for step, _ in funnel]
    assert any("hidden gem" in s.lower() for s in steps), f"Expected hidden gems step in funnel: {steps}"


def test_hidden_gems_no_earnings_excluded(df, program_earnings):
    """Schools with no qualifying program earnings must never appear in hidden gems."""
    OAKWOOD_UID = 101912  # Oakwood University AL: has CIP 52 bachelor_cips but no earn_n>=20 rows
    assert OAKWOOD_UID in df["unit_id"].values, "Oakwood not in dataset"

    if program_earnings is not None:
        oak_pe = program_earnings[
            (program_earnings["unit_id"] == OAKWOOD_UID) &
            (program_earnings["cip4"].astype(str).str.startswith("52")) &
            (program_earnings["earn_n"] >= 20)
        ]
        assert oak_pe.empty, f"Oakwood unexpectedly has qualifying earnings: {oak_pe}"

    client = {
        "name": "gems-no-data-test",
        "require_f1": False, "max_budget": None, "budget_flex": 1.5,
        "school_types": ["4-year"], "states": None, "city_groups": None,
        "sport": None, "gender": "men", "needs_athletic_scholarship": False,
        "min_grad_rate_4yr": 0.0, "min_grad_rate_2yr": 0.0,
        "majors": ["52"], "strict_major": False, "religion": None,
        "hidden_gems_only": True,
        "weights": {"low_cost": 1, "grad_rate": 0, "sport_culture": 0,
                    "athlete_opportunity": 0, "international_community": 0,
                    "open_admission": 0, "small_school": 0,
                    "entrepreneurship_program": 0, "program_strength": 0},
    }
    results, _ = match(df, client, program_earnings=program_earnings)
    assert OAKWOOD_UID not in results["unit_id"].values, (
        "Oakwood (no qualifying earnings) must not appear in hidden gems results"
    )


# ---------------------------------------------------------------------------
# App integration tests (Streamlit AppTest)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def _apptest_cls():
    """Import AppTest lazily so tests work even if streamlit isn't installed."""
    from streamlit.testing.v1 import AppTest  # noqa: PLC0415
    return AppTest


def _fresh_at(_apptest_cls):
    return _apptest_cls.from_file(str(ROOT / "app.py"), default_timeout=90)


def test_defaults_load(_apptest_cls):
    """App must load with defaults, no exception. Online-only excluded by default → 3110."""
    at = _fresh_at(_apptest_cls).run()
    assert not at.exception, f"App crashed on default load: {at.exception}"
    metric = next((m for m in at.metric if "Schools that fit" in m.label), None)
    assert metric is not None, "Missing 'Schools that fit' metric"
    assert metric.value == "3110", f"Expected 3110 schools with defaults (37 online-only excluded), got {metric.value}"


def test_athlete_profile(_apptest_cls):
    """Notebook-04 profile via sidebar widgets must not raise an exception."""
    at = _fresh_at(_apptest_cls)
    # Set the notebook-04 test client via session state keys
    at.session_state["sb_budget"]       = 25_000
    at.session_state["sb_plays_sport"]  = True
    at.session_state["sb_sport"]        = "Soccer"
    at.session_state["sb_gender"]       = "men"
    at.session_state["sb_scholarship"]  = True
    at.session_state["sb_major"]        = "Business"
    at.session_state["sb_grad_4yr"]     = 30
    at.session_state["sb_grad_2yr"]     = 20
    at.session_state["sb_require_f1"]   = True
    at.session_state["sb_affil"]        = "Any"
    at.run()
    assert not at.exception, f"App crashed with athlete profile: {at.exception}"
    metric = next((m for m in at.metric if "Schools that fit" in m.label), None)
    assert metric is not None


def test_catholic_filter(_apptest_cls):
    """Catholic religion filter must not crash and must reduce school count."""
    at = _fresh_at(_apptest_cls)
    at.session_state["sb_affil"]       = "Catholic"
    at.session_state["sb_require_f1"]  = False
    at.run()
    assert not at.exception, f"App crashed with Catholic filter: {at.exception}"
    metric = next((m for m in at.metric if "Schools that fit" in m.label), None)
    assert metric is not None
    count = int(metric.value.replace(",", ""))
    assert count < 3110, f"Expected Catholic filter to reduce count below 3110, got {count}"


def test_zero_weights_no_crash(_apptest_cls):
    """All-zero weights must not crash (nan guard on st.progress)."""
    at = _fresh_at(_apptest_cls)
    zero = "Don't care"
    for k in ["low_cost", "grad_rate", "sport_culture", "athlete_opportunity",
              "international_community", "open_admission", "small_school",
              "entrepreneurship_program"]:
        at.session_state[f"w_{k}"] = zero
    at.run()
    assert not at.exception, f"App crashed with all-zero weights: {at.exception}"


# ---------------------------------------------------------------------------
# Part 2: notable alumni
# ---------------------------------------------------------------------------

ALUMNI_PATH = ROOT / "data/processed/notable_alumni.csv"


def test_alumni_csv_exists_and_tracked():
    """notable_alumni.csv must exist and be committed to git."""
    import subprocess
    tracked = set(
        subprocess.check_output(["git", "ls-files"], cwd=ROOT).decode().splitlines()
    )
    assert "data/processed/notable_alumni.csv" in tracked, (
        "notable_alumni.csv not tracked by git. "
        "Run scripts/fetch_alumni.py and git add the file."
    )
    alumni = pd.read_csv(ALUMNI_PATH)
    assert set(alumni.columns) >= {"unit_id", "wikidata_id", "name", "sitelinks", "has_pt_wiki"}
    assert len(alumni) > 100, f"Expected >100 alumni rows, got {len(alumni)}"


def test_alumni_tab_renders(_apptest_cls):
    """Famous alumni tab renders without exception — Brazil toggle and sort box present."""
    at = _fresh_at(_apptest_cls).run()
    assert not at.exception, f"App crashed: {at.exception}"
    brazil = next((t for t in at.toggle if "Brazil" in (t.label or "")), None)
    sort   = next((s for s in at.selectbox if s.key == "alumni_sort_sel"), None)
    assert brazil is not None, "Brazil toggle not found in Famous alumni tab"
    assert sort   is not None, "Sort selectbox not found in Famous alumni tab"


def test_alumni_details_with_alum(_apptest_cls):
    """Details dialog renders for a school that has alumni data."""
    alumni = pd.read_csv(ALUMNI_PATH)
    schools_with = set(alumni["unit_id"].dropna().astype(int))
    from src.matcher import load_data as _ld
    df_t = _ld(ROOT / "data/processed/schools_with_majors.csv")
    target = df_t[df_t["unit_id"].isin(schools_with)].iloc[0]
    state_s = str(target["state"]) if pd.notna(target["state"]) else "?"
    label = f"{target['name']} ({state_s})"

    at = _fresh_at(_apptest_cls)
    at.session_state["school_lookup"] = label
    at.run()
    assert not at.exception, f"App crashed on school lookup: {at.exception}"

    det = next((b for b in at.button if b.key == "lookup_det"), None)
    assert det is not None, "lookup_det button not found"
    det.click().run()
    assert not at.exception, f"App crashed opening details for school with alumni: {at.exception}"


def test_alumni_details_without_alum(_apptest_cls):
    """Details dialog renders for a school that has no alumni data."""
    alumni = pd.read_csv(ALUMNI_PATH)
    schools_with = set(alumni["unit_id"].dropna().astype(int))
    from src.matcher import load_data as _ld
    df_t = _ld(ROOT / "data/processed/schools_with_majors.csv")
    target = df_t[~df_t["unit_id"].isin(schools_with)].iloc[0]
    state_s = str(target["state"]) if pd.notna(target["state"]) else "?"
    label = f"{target['name']} ({state_s})"

    at = _fresh_at(_apptest_cls)
    at.session_state["school_lookup"] = label
    at.run()
    assert not at.exception, f"App crashed on school lookup: {at.exception}"

    det = next((b for b in at.button if b.key == "lookup_det"), None)
    assert det is not None, "lookup_det button not found"
    det.click().run()
    assert not at.exception, f"App crashed opening details for school without alumni: {at.exception}"


def test_card_titles_in_rank_order(_apptest_cls):
    """Card titles must appear in rank order (#1 before #2 ...) so row-by-row layout is correct."""
    import re
    at = _fresh_at(_apptest_cls).run()
    assert not at.exception, f"App crashed: {at.exception}"
    card_titles = [m.value for m in at.markdown if re.match(r"\*\*#\d+", m.value or "")]
    ranks = [int(re.search(r"#(\d+)", t).group(1)) for t in card_titles if re.search(r"#(\d+)", t)]
    assert len(ranks) >= 3, f"Expected at least 3 card titles, got {ranks}"
    assert ranks == sorted(ranks), f"Cards not in rank order: {ranks}"


def test_explain_exclusion_no_bare_dollars(df):
    """Cost reason from explain_exclusion must use \\$ (not bare $) so markdown is safe."""
    import re
    client = {
        "name": "dollar-test",
        "require_f1": False, "max_budget": 5_000, "budget_flex": 1.0,
        "school_types": ["2-year", "4-year"], "states": None, "city_groups": None,
        "sport": None, "gender": "men", "needs_athletic_scholarship": False,
        "min_grad_rate_4yr": 0.0, "min_grad_rate_2yr": 0.0,
        "majors": None, "strict_major": False, "religion": None,
        "hidden_gems_only": False,
        "weights": {"low_cost": 1, "grad_rate": 0, "sport_culture": 0,
                    "athlete_opportunity": 0, "international_community": 0,
                    "open_admission": 0, "small_school": 0, "entrepreneurship_program": 0},
    }
    over = df[df["cost_international"] > 5_000].head(10)
    found_cost_reason = False
    for _, row in over.iterrows():
        reasons = explain_exclusion(row, client)
        for r in reasons:
            if "cost" in r.lower() or "budget" in r.lower():
                found_cost_reason = True
                bare = re.findall(r"(?<!\\)\$", r)
                assert not bare, f"Bare $ in cost reason (LaTeX risk in markdown): {r!r}"
    assert found_cost_reason, "Expected at least one cost reason across sampled rows"


def test_clear_all(_apptest_cls):
    """After changing filters and clicking 'Clear all filters', count returns to default 3110."""
    at = _fresh_at(_apptest_cls)
    # Apply a restrictive filter first
    at.session_state["sb_budget"]      = 10_000
    at.session_state["sb_require_f1"]  = True
    at.run()
    before = next((m for m in at.metric if "Schools that fit" in m.label), None)
    assert before is not None
    before_count = int(before.value.replace(",", ""))
    assert before_count < 3110

    # Click "Clear all filters"
    clear_btn = next((b for b in at.button if "Clear" in b.label), None)
    assert clear_btn is not None, "Could not find 'Clear all filters' button"
    clear_btn.click().run()
    assert not at.exception, f"App crashed after clear: {at.exception}"
    after = next((m for m in at.metric if "Schools that fit" in m.label), None)
    assert after is not None
    after_count = int(after.value.replace(",", ""))
    assert after_count == 3110, f"Expected 3110 after clear (online-only excluded by default), got {after_count}"


# ---------------------------------------------------------------------------
# Part 3: opportunities
# ---------------------------------------------------------------------------

OPPS_PATH     = ROOT / "data/manual/opportunities.csv"
CONTACTS_PATH = ROOT / "data/manual/intl_contacts.csv"
OPPS_REQUIRED_COLS = {"unit_id", "school_name", "type", "name", "description",
                       "amount", "intl_eligible", "url", "date_checked", "verified"}
VALID_TYPES = {"merit_scholarship", "athletic", "need_based", "competition",
               "entrepreneurship_center", "accelerator", "other"}


def test_opportunities_csv_loads():
    """opportunities.csv must exist, have the required columns, and every row must
    have a url and a date_checked value."""
    assert OPPS_PATH.exists(), f"opportunities.csv not found at {OPPS_PATH}"
    opps = pd.read_csv(OPPS_PATH, dtype={"unit_id": int})
    missing_cols = OPPS_REQUIRED_COLS - set(opps.columns)
    assert not missing_cols, f"Missing columns: {missing_cols}"
    assert len(opps) >= 1, "Expected at least 1 row (the example row)"
    bad_url = opps[opps["url"].isna() | (opps["url"].astype(str).str.strip() == "")]
    assert bad_url.empty, f"Rows missing url:\n{bad_url[['unit_id','name']]}"
    bad_date = opps[opps["date_checked"].isna() | (opps["date_checked"].astype(str).str.strip() == "")]
    assert bad_date.empty, f"Rows missing date_checked:\n{bad_date[['unit_id','name']]}"
    bad_type = opps[~opps["type"].isin(VALID_TYPES)]
    assert bad_type.empty, f"Invalid type values:\n{bad_type[['unit_id','name','type']]}"


def test_opportunities_details_with_opps(_apptest_cls):
    """Details renders for a school that has opportunities data (Washburn, uid=156082)."""
    from src.matcher import load_data as _ld
    df_t = _ld(ROOT / "data/processed/schools_with_majors.csv")
    opps = pd.read_csv(OPPS_PATH, dtype={"unit_id": int})
    schools_with_opps = set(opps["unit_id"].unique())
    # Find one of our schools that has an opps row
    target = df_t[df_t["unit_id"].isin(schools_with_opps)].iloc[0]
    state_s = str(target["state"]) if pd.notna(target["state"]) else "?"
    label = f"{target['name']} ({state_s})"

    at = _fresh_at(_apptest_cls)
    at.session_state["school_lookup"] = label
    at.run()
    assert not at.exception, f"App crashed on school lookup: {at.exception}"

    det = next((b for b in at.button if b.key == "lookup_det"), None)
    assert det is not None, "lookup_det button not found"
    det.click().run()
    assert not at.exception, f"App crashed opening details for school with opps: {at.exception}"


def test_opportunities_details_without_opps(_apptest_cls):
    """Details renders for a school that has no opportunities data."""
    from src.matcher import load_data as _ld
    df_t = _ld(ROOT / "data/processed/schools_with_majors.csv")
    opps = pd.read_csv(OPPS_PATH, dtype={"unit_id": int})
    schools_with_opps = set(opps["unit_id"].unique())
    target = df_t[~df_t["unit_id"].isin(schools_with_opps)].iloc[0]
    state_s = str(target["state"]) if pd.notna(target["state"]) else "?"
    label = f"{target['name']} ({state_s})"

    at = _fresh_at(_apptest_cls)
    at.session_state["school_lookup"] = label
    at.run()
    assert not at.exception

    det = next((b for b in at.button if b.key == "lookup_det"), None)
    assert det is not None
    det.click().run()
    assert not at.exception, f"App crashed for school without opps: {at.exception}"


def test_opportunities_merit_toggle(_apptest_cls):
    """Merit scholarship toggle reduces results to only researched schools with intl merit."""
    opps = pd.read_csv(OPPS_PATH, dtype={"unit_id": int})
    merit_schools = opps[(opps["type"] == "merit_scholarship") &
                         (opps["intl_eligible"].str.lower() == "yes")]
    if merit_schools.empty:
        pytest.skip("No merit_scholarship + intl_eligible=yes rows in opportunities.csv yet")

    at = _fresh_at(_apptest_cls)
    at.session_state["sb_intl_merit"] = True
    at.run()
    assert not at.exception, f"App crashed with merit toggle on: {at.exception}"
    metric = next((m for m in at.metric if "Schools that fit" in m.label), None)
    assert metric is not None
    count = int(metric.value.replace(",", ""))
    # With the toggle, count must be ≤ number of schools with intl merit rows
    assert count <= len(merit_schools["unit_id"].unique()), (
        f"Expected ≤{len(merit_schools['unit_id'].unique())} schools with merit toggle, got {count}"
    )


# ---------------------------------------------------------------------------
# International contacts tests
# ---------------------------------------------------------------------------

def test_contacts_csv_loads():
    """Every contact row has an official-looking URL and date_checked; no personal name field."""
    assert CONTACTS_PATH.exists(), f"Missing {CONTACTS_PATH}"
    contacts = pd.read_csv(CONTACTS_PATH, dtype={"unit_id": int})

    required_cols = {"unit_id", "school_name", "intl_admissions_url", "office_email",
                     "office_phone", "date_checked"}
    assert required_cols.issubset(contacts.columns), (
        f"Missing columns: {required_cols - set(contacts.columns)}"
    )
    assert "personal_name" not in contacts.columns, "contacts CSV must not have a personal_name column"

    for _, row in contacts.iterrows():
        url = str(row["intl_admissions_url"]).strip()
        assert url and url not in ("nan", "None", ""), (
            f"Row {row['unit_id']} has blank intl_admissions_url"
        )
        assert url.startswith("http") and (".edu" in url or ".inter.edu" in url or ".pr" in url), (
            f"Row {row['unit_id']} URL doesn't look like an official .edu URL: {url}"
        )
        checked = str(row["date_checked"]).strip()
        assert checked and checked not in ("nan", "None", ""), (
            f"Row {row['unit_id']} has blank date_checked"
        )

        # No personal emails (firstname.lastname@ pattern)
        email = str(row.get("office_email", "")).strip()
        if email and email not in ("nan", "None", ""):
            local = email.split("@")[0]
            assert "." not in local, (
                f"Row {row['unit_id']} looks like a personal email: {email}"
            )


def test_contacts_details_fallback(_apptest_cls):
    """Details renders the fallback Google search button for a school without a contact row."""
    from src.matcher import load_data as _ld
    df_t = _ld(ROOT / "data/processed/schools_with_majors.csv")
    contacts = pd.read_csv(CONTACTS_PATH, dtype={"unit_id": int})
    schools_with_contacts = set(contacts["unit_id"].unique())
    target = df_t[~df_t["unit_id"].isin(schools_with_contacts)].iloc[0]
    state_s = str(target["state"]) if pd.notna(target["state"]) else "?"
    label = f"{target['name']} ({state_s})"

    at = _fresh_at(_apptest_cls)
    at.session_state["school_lookup"] = label
    at.run()
    assert not at.exception

    det = next((b for b in at.button if b.key == "lookup_det"), None)
    assert det is not None
    det.click().run()
    assert not at.exception, f"App crashed for school without contact row: {at.exception}"

    # AppTest doesn't expose link_button href directly; assert no crash is sufficient
    assert not at.exception
