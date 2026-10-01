"""Tests for scripts/export_for_web.py."""

import json
import sys
import tempfile
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from scripts.export_for_web import build_schools_json


@pytest.fixture(scope="module")
def schools_json(tmp_path_factory):
    out = tmp_path_factory.mktemp("export") / "schools.json"
    return build_schools_json(out)


@pytest.fixture(scope="module")
def source_unit_ids() -> set[int]:
    df = pd.read_csv(ROOT / "data/processed/schools_with_majors.csv")
    return set(df["unit_id"].astype(int).tolist())


def test_export_count_matches_source(schools_json, source_unit_ids):
    """Every school in schools_with_majors.csv must appear in the export."""
    exported_ids = {s["unit_id"] for s in schools_json}
    missing = source_unit_ids - exported_ids
    assert not missing, f"{len(missing)} schools missing from export: {list(missing)[:5]}"


def test_no_nan_values(schools_json):
    """Export must contain no NaN values — only null (None in Python)."""

    def check(obj, path=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                check(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                check(v, f"{path}[{i}]")
        elif isinstance(obj, float):
            import math
            assert not math.isnan(obj) and not math.isinf(obj), (
                f"NaN/inf found at {path}: {obj}"
            )

    for school in schools_json:
        check(school, root := f"school[{school['unit_id']}]")


def test_required_top_level_keys(schools_json):
    required = {"unit_id", "identity", "athletics", "cost", "other_scholarships",
                "academics", "admissions", "contacts"}
    for school in schools_json:
        missing = required - school.keys()
        assert not missing, f"School {school['unit_id']} missing keys: {missing}"


def test_identity_has_required_fields(schools_json):
    required = {"name", "city", "state", "type", "control"}
    for school in schools_json:
        missing = required - school["identity"].keys()
        assert not missing, f"School {school['unit_id']} identity missing: {missing}"


def test_sports_are_lists(schools_json):
    for school in schools_json:
        assert isinstance(school["athletics"]["mens_sports"], list)
        assert isinstance(school["athletics"]["womens_sports"], list)


def test_majors_are_lists(schools_json):
    for school in schools_json:
        assert isinstance(school["academics"]["majors"], list)


def test_json_serializable(schools_json):
    """Verify the output can round-trip through JSON."""
    text = json.dumps(schools_json)
    loaded = json.loads(text)
    assert len(loaded) == len(schools_json)
