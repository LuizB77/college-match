"""
Export processed school data to export/schools.json for the web app.

Usage:
    python scripts/export_for_web.py
    python scripts/export_for_web.py --out path/to/output.json
"""

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Optional

import pandas as pd

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"


def _nan_to_none(v):
    """Convert NaN/inf floats to None so json.dumps produces null."""
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    return v


def _clean(v):
    """Recursively replace NaN with None in nested structures."""
    if isinstance(v, dict):
        return {k: _clean(val) for k, val in v.items()}
    if isinstance(v, list):
        return [_clean(i) for i in v]
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    # pandas NA / NaT
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    return v


def _split_sports(val) -> list[str]:
    if not val or (isinstance(val, float) and math.isnan(val)):
        return []
    return [s.strip() for s in str(val).split(";") if s.strip()]


def _split_cips(val) -> list[str]:
    if not val or (isinstance(val, float) and math.isnan(val)):
        return []
    return [c.strip() for c in str(val).split(";") if c.strip()]


def selectivity_tier(admit_rate) -> str:
    if pd.isna(admit_rate):
        return "Unknown"
    if admit_rate == 0.0:
        return "Likely"
    if admit_rate < 0.15:
        return "Reach"
    if admit_rate <= 0.50:
        return "Target"
    return "Likely"


def load_intl_aid() -> pd.DataFrame:
    path = DATA / "manual" / "intl_aid.csv"
    df = pd.read_csv(path)
    return df[df["quality"] == "ok"].copy()


def load_opportunities() -> pd.DataFrame:
    path = DATA / "manual" / "opportunities.csv"
    df = pd.read_csv(path)
    mask = (df["check_status"] == "auto-checked") | (df["verified"] == "yes")
    return df[mask].copy()


def load_contacts() -> pd.DataFrame:
    return pd.read_csv(DATA / "manual" / "intl_contacts.csv")


def load_program_earnings() -> pd.DataFrame:
    path = DATA / "processed" / "program_earnings.csv"
    df = pd.read_csv(path)
    df["unit_id"] = pd.to_numeric(df["unit_id"], errors="coerce")
    df["earn_mdn_4yr"] = pd.to_numeric(df["earn_mdn_4yr"], errors="coerce")
    df["earn_n"] = pd.to_numeric(df["earn_n"], errors="coerce")
    return df.dropna(subset=["unit_id", "earn_mdn_4yr"])


def build_schools_json(out_path: Optional[Path] = None) -> list[dict]:
    schools = pd.read_csv(DATA / "processed" / "schools_with_majors.csv")
    intl_aid = load_intl_aid().set_index("unitid")
    opportunities = load_opportunities()
    contacts = load_contacts().set_index("unit_id")
    program_earnings = load_program_earnings()

    # index program_earnings by unit_id for fast lookup
    pe_by_school: dict[int, list[dict]] = {}
    for _, row in program_earnings.iterrows():
        uid = int(row["unit_id"])
        pe_by_school.setdefault(uid, []).append({
            "cip4": int(row["cip4"]) if not pd.isna(row["cip4"]) else None,
            "earn_mdn_4yr": _nan_to_none(row["earn_mdn_4yr"]),
            "earn_n": _nan_to_none(row["earn_n"]),
        })

    # index opportunities by unit_id
    opp_by_school: dict[int, list[dict]] = {}
    for _, row in opportunities.iterrows():
        uid = int(row["unit_id"])
        opp_by_school.setdefault(uid, []).append({
            "type": _nan_to_none(row.get("type")),
            "name": _nan_to_none(row.get("name")),
            "amount": _nan_to_none(row.get("amount")),
            "intl_eligible": _nan_to_none(row.get("intl_eligible")),
            "url": _nan_to_none(row.get("url")),
            "date_checked": _nan_to_none(row.get("date_checked")),
        })

    result = []
    for _, s in schools.iterrows():
        uid = int(s["unit_id"])

        # intl aid block
        aid_row = intl_aid.loc[uid] if uid in intl_aid.index else None
        if aid_row is not None:
            cds_total = _nan_to_none(aid_row.get("cds_total_cost"))
            avg_award = _nan_to_none(aid_row.get("avg_intl_award"))
            est_net = (
                round(cds_total - avg_award, 2)
                if cds_total is not None and avg_award is not None
                else None
            )
            intl_aid_block = {
                "offers_intl_aid": bool(aid_row["offers_intl_aid"]),
                "pct_intl_aided": _nan_to_none(aid_row.get("pct_intl_aided")),
                "avg_intl_award": avg_award,
                "need_blind": _nan_to_none(aid_row.get("need_blind_intl")),
                "meets_full_need": _nan_to_none(aid_row.get("meets_full_need_intl")),
                "cds_total_cost": cds_total,
                "est_net_cost": est_net,
                "cds_year": _nan_to_none(aid_row.get("cds_year")),
                "source_url": _nan_to_none(aid_row.get("source_url")),
                "intl_aid_page_url": _nan_to_none(aid_row.get("intl_aid_page_url")),
            }
        else:
            intl_aid_block = None

        # contacts
        contact_row = contacts.loc[uid] if uid in contacts.index else None
        contacts_block = {
            "intl_admissions_url": _nan_to_none(contact_row["intl_admissions_url"]) if contact_row is not None else None,
            "office_email": _nan_to_none(contact_row["office_email"]) if contact_row is not None else None,
            "office_phone": _nan_to_none(contact_row["office_phone"]) if contact_row is not None else None,
        }

        record = {
            "unit_id": uid,
            "identity": {
                "name": _nan_to_none(s["name"]),
                "city": _nan_to_none(s["city"]),
                "state": _nan_to_none(s["state"]),
                "lat": _nan_to_none(s["lat"]),
                "lon": _nan_to_none(s["lon"]),
                "website": _nan_to_none(s["website"]),
                "type": _nan_to_none(s["school_type"]),
                "control": _nan_to_none(s["control"]),
                "religious_affiliation": _nan_to_none(s["religious_affil"]),
                "city_size": _nan_to_none(s["city_size"]),
            },
            "athletics": {
                "division": _nan_to_none(s["division"]),
                "association": _nan_to_none(s["association"]),
                "athletic_aid_tier": _nan_to_none(s["athletic_aid_tier"]),
                "aid_per_athlete_men": _nan_to_none(s["aid_per_athlete_men"]),
                "aid_per_athlete_women": _nan_to_none(s["aid_per_athlete_women"]),
                "athlete_share": _nan_to_none(s["athlete_share"]),
                "athletics_spending": _nan_to_none(s["athletics_expense"]),
                "sport_culture_percentile": _nan_to_none(s["sport_culture_pct"]),
                "mens_sports": _split_sports(s["mens_sports"]),
                "womens_sports": _split_sports(s["womens_sports"]),
            },
            "cost": {
                "cost_international": _nan_to_none(s["cost_international"]),
                "intl_aid": intl_aid_block,
            },
            "other_scholarships": opp_by_school.get(uid, []),
            "academics": {
                "grad_rate": _nan_to_none(s["grad_rate"]),
                "majors": _split_cips(s["bachelor_cips"]) + _split_cips(s["associate_cips"]),
                "transfer_track": bool(s["has_transfer_track"]),
                "entrepreneurship": bool(s["offers_entrepreneurship"]),
                "programs_known": bool(s["programs_known"]),
                "program_earnings": pe_by_school.get(uid, []),
            },
            "admissions": {
                "admit_rate": _nan_to_none(s["admit_rate"]),
                "selectivity_tier": selectivity_tier(s["admit_rate"]),
                "test_policy": _nan_to_none(s["test_policy"]),
                "sat_read_25": _nan_to_none(s["sat_read_25"]),
                "sat_read_75": _nan_to_none(s["sat_read_75"]),
                "sat_math_25": _nan_to_none(s["sat_math_25"]),
                "sat_math_75": _nan_to_none(s["sat_math_75"]),
                "f1_certified": bool(s["sevp_certified"]),
                "online_only": bool(s["online_only"]),
            },
            "contacts": contacts_block,
        }

        result.append(_clean(record))

    if out_path is None:
        out_path = ROOT / "export" / "schools.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, separators=(",", ":"))

    print(f"Wrote {len(result)} schools to {out_path}")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    build_schools_json(args.out)
