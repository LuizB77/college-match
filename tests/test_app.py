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

from src.matcher import load_data, match, explain_exclusion

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
    if program_earnings is None:
        pytest.skip("program_earnings.csv not found")
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
    if program_earnings is None:
        pytest.skip("program_earnings.csv not found")
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


def test_hidden_gems_only(df, program_earnings):
    """hidden_gems_only filter must keep only non-Reach schools with high program strength."""
    if program_earnings is None:
        pytest.skip("program_earnings.csv not found")
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
    results_gems, funnel = match(df, client_gems, program_earnings=program_earnings)
    # Hidden gems must be a strict subset
    assert len(results_gems) < len(results_all), "Hidden gems filter must reduce school count"
    # No Reach schools in hidden gems
    if "selectivity_tier" in results_gems.columns:
        reach_in_gems = (results_gems["selectivity_tier"] == "Reach").sum()
        assert reach_in_gems == 0, f"Hidden gems must not include Reach schools, found {reach_in_gems}"
    # Funnel must show the hidden gems step
    steps = [step for step, _ in funnel]
    assert any("hidden gem" in s.lower() for s in steps), f"Expected hidden gems step in funnel: {steps}"


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
    """App must load with defaults, no exception, Schools that fit = 3147."""
    at = _fresh_at(_apptest_cls).run()
    assert not at.exception, f"App crashed on default load: {at.exception}"
    metric = next((m for m in at.metric if "Schools that fit" in m.label), None)
    assert metric is not None, "Missing 'Schools that fit' metric"
    assert metric.value == "3147", f"Expected 3147 schools with no filters, got {metric.value}"


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
    assert count < 3147, f"Expected Catholic filter to reduce count below 3147, got {count}"


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


def test_clear_all(_apptest_cls):
    """After changing filters and clicking 'Clear all filters', count returns to 3147."""
    at = _fresh_at(_apptest_cls)
    # Apply a restrictive filter first
    at.session_state["sb_budget"]      = 10_000
    at.session_state["sb_require_f1"]  = True
    at.run()
    before = next((m for m in at.metric if "Schools that fit" in m.label), None)
    assert before is not None
    before_count = int(before.value.replace(",", ""))
    assert before_count < 3147

    # Click "Clear all filters"
    clear_btn = next((b for b in at.button if "Clear" in b.label), None)
    assert clear_btn is not None, "Could not find 'Clear all filters' button"
    clear_btn.click().run()
    assert not at.exception, f"App crashed after clear: {at.exception}"
    after = next((m for m in at.metric if "Schools that fit" in m.label), None)
    assert after is not None
    after_count = int(after.value.replace(",", ""))
    assert after_count == 3147, f"Expected 3147 after clear, got {after_count}"
