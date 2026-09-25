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

from src.matcher import load_data, match

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
    results, funnel = match(df, client, top_n=25)
    assert not results.empty
    assert results["match_score"].notna().all(), "match_score must never be NaN"
    assert funnel[-1][1] == len(df), "with no filters all schools should pass"


def test_matcher_religion_catholic(df, notebook04_client):
    """Catholic filter reduces school count and appears as a funnel step."""
    client = {**notebook04_client, "religion": "catholic",
              "max_budget": None, "require_f1": False, "sport": None,
              "needs_athletic_scholarship": False}
    results, funnel = match(df, client, top_n=25)
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
    results, funnel = match(df, client, top_n=25)
    cost_steps = [s for s, _ in funnel if "cost" in s.lower()]
    assert not cost_steps, f"No cost filter step expected, got: {cost_steps}"


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
