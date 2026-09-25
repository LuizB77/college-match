"""
Core matching logic extracted verbatim from notebooks/04_match.ipynb.
Do not change scoring weights here without also updating the notebook.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# Columns present in every valid schools_with_majors.csv.
_REQUIRED_COLS = [
    "name", "state", "school_type", "association",
    "cost_international", "grad_rate", "pct_international",
    "athlete_share", "athletic_aid_tier", "sport_culture_pct",
    "sevp_certified", "offers_entrepreneurship", "has_athletics",
    "undergrads", "open_admission", "mens_sports", "womens_sports",
    "bachelor_cips", "associate_cips", "programs_known",
    "has_transfer_track", "religious_affil",
]

# unit_ids for the 8 Ivy League schools.
IVY_UNIT_IDS = {
    130794,   # Yale University
    166027,   # Harvard University
    182670,   # Dartmouth College
    186131,   # Princeton University
    190150,   # Columbia University in the City of New York
    190415,   # Cornell University
    215062,   # University of Pennsylvania
    217156,   # Brown University
}

# ADMCON7 codes → human-readable test policy labels (per data dictionary)
ADMCON7_LABELS = {
    1: "Required",
    2: "Recommended",
    3: "Neither required nor recommended",
    4: "Do not know",
    5: "Considered but not required",
}

# Columns shown in results tables (same list as notebook 04 cell 3).
SHOW_COLS = [
    "name", "state", "school_type", "association",
    "cost_international", "grad_rate",
    "pct_international", "athlete_share",
    "offers_entrepreneurship", "match_score", "top_reasons",
]


def load_program_earnings(
    path="data/processed/program_earnings.csv",
) -> pd.DataFrame | None:
    """Load program_earnings.csv if it exists; return None otherwise."""
    import os
    if not os.path.exists(path):
        return None
    pe = pd.read_csv(path, dtype={"cip4": str})
    pe["unit_id"] = pd.to_numeric(pe["unit_id"], errors="coerce")
    pe["earn_mdn_4yr"] = pd.to_numeric(pe["earn_mdn_4yr"], errors="coerce")
    pe["earn_n"] = pd.to_numeric(pe["earn_n"], errors="coerce").fillna(1)
    # Ensure cip4 is always zero-padded 4-char string
    pe["cip4"] = pe["cip4"].apply(lambda x: str(x).zfill(4) if pd.notna(x) else x)
    return pe.dropna(subset=["unit_id", "earn_mdn_4yr"])


def selectivity_tier(admit_rate) -> str:
    """Classify a school by admit rate into Reach / Target / Likely / Unknown."""
    if pd.isna(admit_rate):
        return "Unknown"
    if admit_rate == 0.0:
        return "Likely"   # open admission stored as 0 in the data
    if admit_rate < 0.15:
        return "Reach"
    if admit_rate <= 0.50:
        return "Target"
    return "Likely"


def _program_strength_percentiles(
    df: pd.DataFrame,
    major_prefixes: list[str] | None,
    program_earnings: pd.DataFrame | None,
) -> pd.Series:
    """
    Return a 0–1 program-strength percentile for each row in df.

    With a major: earnings-weighted average of earn_mdn_4yr for programs matching the
    major prefix, percentile-ranked among schools that offer that major.
    No major: percentile of median_earnings_10yr (institution-level).
    Missing / 2-year schools with no earnings = 0.5.
    """
    result = pd.Series(0.5, index=df.index)

    if not major_prefixes or program_earnings is None:
        # Institution-level earnings percentile
        if "median_earnings_10yr" in df.columns:
            ranked = df["median_earnings_10yr"].rank(pct=True)
            result = ranked.fillna(0.5)
        return result

    # Build weighted-average earnings per school for the matching major prefix
    # Limit to bachelor's programs matching any prefix
    def _prefix_match(cip4: str) -> bool:
        return any(cip4.startswith(p) for p in major_prefixes)

    pe = program_earnings[program_earnings["cip4"].apply(_prefix_match)].copy()
    if pe.empty:
        return result

    # Weighted average earn_mdn_4yr per school
    pe["weighted"] = pe["earn_mdn_4yr"] * pe["earn_n"]
    agg = pe.groupby("unit_id").agg(
        total_weighted=("weighted", "sum"),
        total_n=("earn_n", "sum"),
    )
    agg = agg[agg["total_n"] > 0]
    agg["avg_earn"] = agg["total_weighted"] / agg["total_n"]

    # Percentile among schools that have earnings for this major
    agg["pct"] = agg["avg_earn"].rank(pct=True)

    # Map back to df rows via unit_id
    unit_to_pct = agg["pct"].to_dict()
    result = df["unit_id"].map(unit_to_pct).fillna(0.5)
    return result


def load_data(path="data/processed/schools_with_majors.csv") -> pd.DataFrame:
    """Load and prep the schools dataset (verbatim from notebook 04 cell 1)."""
    df = pd.read_csv(path)

    missing = [c for c in _REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError(
            f"schools_with_majors.csv is missing columns: {missing}. "
            "Re-run the full pipeline (nb01 → nb03_athletics → nb05_sevp_link → nb06_majors)."
        )

    df[["bachelor_cips", "associate_cips"]] = df[["bachelor_cips", "associate_cips"]].fillna("")

    # Collapse 12 city-size labels into 4 groups clients understand
    def city_group(s):
        if pd.isna(s):
            return None
        s = s.lower()
        for k in ["city", "suburb", "town", "rural"]:
            if k in s:
                return k.capitalize()

    df["city_group"] = df["city_size"].apply(city_group)

    # Derived columns
    df["selectivity_tier"] = df["admit_rate"].apply(selectivity_tier)
    df["ivy_league"] = df["unit_id"].isin(IVY_UNIT_IDS)

    return df


def match(
    df: pd.DataFrame,
    client: dict,
    top_n: int | None = None,
    program_earnings: pd.DataFrame | None = None,
):
    """
    Apply hard filters then rank by weighted score (verbatim from notebook 04 cell 3).

    Returns
    -------
    results_df : pd.DataFrame
        All passing schools sorted by match_score descending (or top_n if given).
    funnel : list[tuple[str, int]]
        (step_label, count_remaining) after each filter.
    """
    c = df.copy()
    funnel = [("Start", len(c))]

    if client.get("require_f1", True):
        c = c[c["sevp_certified"]]      # no F-1 certification = can't enroll on a student visa
        funnel.append(("After SEVP F-1 certified", len(c)))

    # --- 1. Hard filters: fail one = excluded. ---
    c = c[c["school_type"].isin(client["school_types"])]
    funnel.append(("After school type", len(c)))

    if client.get("states"):
        c = c[c["state"].isin(client["states"])]
        funnel.append(("After states", len(c)))

    if client.get("city_groups"):
        c = c[c["city_group"].isin(client["city_groups"])]
        funnel.append(("After city size", len(c)))

    # Religion filter (None / "catholic" / "any_religious" / "non_religious")
    religion = client.get("religion")
    if religion:
        _none_affil = {-1, -2}
        if religion == "catholic":
            c = c[c["religious_affil"] == 30]
            funnel.append(("After religious affiliation: Catholic", len(c)))
        elif religion == "any_religious":
            c = c[
                c["religious_affil"].notna()
                & ~c["religious_affil"].isin(_none_affil)
            ]
            funnel.append(("After religious affiliation: Any religious", len(c)))
        elif religion == "non_religious":
            c = c[
                c["religious_affil"].isna()
                | c["religious_affil"].isin(_none_affil)
            ]
            funnel.append(("After religious affiliation: Non-religious", len(c)))

    # Cost filter: skipped when max_budget is None (no limit set in UI)
    max_budget = client.get("max_budget")
    if max_budget is not None:
        limit = max_budget * client.get("budget_flex", 1.0)
        c = c[c["cost_international"] <= limit]        # unknown cost (NaN) is excluded
        funnel.append((f"After cost <= ${limit:,.0f}", len(c)))

    if client.get("sport"):
        col = "mens_sports" if client["gender"] == "men" else "womens_sports"
        has_sport = c[col].fillna("").apply(
            lambda s: client["sport"] in [x.strip() for x in s.split(";")]
        )
        c = c[has_sport]
        funnel.append((f"After has {client['gender']}'s {client['sport']}", len(c)))

    if client.get("needs_athletic_scholarship"):
        c = c[c["athletic_aid_tier"].isin(["Athletic scholarships", "Mixed / verify"])]
        funnel.append(("After athletic scholarships available", len(c)))

    mg4, mg2 = client.get("min_grad_rate_4yr"), client.get("min_grad_rate_2yr")
    if mg4 or mg2:
        # Each school gets the threshold for its type; missing grad rate is kept, not punished
        threshold = np.where(c["school_type"] == "4-year", mg4 or 0, mg2 or 0)
        c = c[c["grad_rate"].isna() | (c["grad_rate"] >= threshold)]
        funnel.append(("After minimum grad rate", len(c)))

    if client.get("majors"):
        prefixes = client["majors"]

        def has_major(cips):
            return any(c.startswith(p) for c in str(cips).split(";") if c for p in prefixes)

        strict = client.get("strict_major", False)

        def major_ok(r):
            if not r["programs_known"]:
                return True    # no program data: unknown, not failing -> keep
            if r["school_type"] == "4-year":
                return has_major(r["bachelor_cips"])
            # JUCO: the major itself, or (when not strict) a general transfer track (CIP 24.01)
            return has_major(r["associate_cips"]) or (not strict and r["has_transfer_track"])

        c = c[c.apply(major_ok, axis=1)]
        funnel.append((f"After offers major {prefixes}", len(c)))

    if client.get("hidden_gems_only"):
        # Pre-compute program_strength percentile on the filtered pool to apply threshold
        _pg_strength = _program_strength_percentiles(c, client.get("majors"), program_earnings)
        _selectivity = c["selectivity_tier"] if "selectivity_tier" in c.columns else c["admit_rate"].apply(selectivity_tier)
        mask = (_pg_strength >= 0.75) & (_selectivity != "Reach")
        c = c[mask]
        funnel.append(("After hidden gems filter", len(c)))

    if c.empty:
        return c, funnel

    # --- 2. Features on a 0-1 scale (percentile among remaining schools). Missing = 0.5 neutral. ---
    f = pd.DataFrame(index=c.index)
    f["low_cost"] = 1 - c["cost_international"].rank(pct=True)     # cheaper = higher
    # Schools with no published price get 0.3 (slightly below neutral) so they don't
    # headline the list when a user cares about cost — but they're not buried either.
    f["low_cost"] = f["low_cost"].fillna(0.3)
    f["grad_rate"] = c["grad_rate"].rank(pct=True)
    f["sport_culture"] = c["sport_culture_pct"] / 100              # already a percentile
    f["athlete_opportunity"] = c["athlete_share"].rank(pct=True)
    f["international_community"] = c["pct_international"].rank(pct=True)
    f["open_admission"] = c["open_admission"].astype(float)
    f["small_school"] = 1 - c["undergrads"].rank(pct=True)          # smaller = higher
    f["entrepreneurship_program"] = c["offers_entrepreneurship"].astype(float)
    f["program_strength"] = _program_strength_percentiles(c, client.get("majors"), program_earnings)
    f = f.fillna(0.5)

    # --- 3. Weighted score 0-100 + the 2 features that contributed most ---
    w = pd.Series(client["weights"], dtype=float)
    contrib = f[w.index] * w
    total_w = w.sum()
    if total_w > 0:
        c["match_score"] = (contrib.sum(axis=1) / total_w * 100).round(1)
    else:
        c["match_score"] = 50.0          # all weights zero → equal score, no ranking
    c["top_reasons"] = contrib.apply(lambda r: ", ".join(r.nlargest(2).index), axis=1)

    results = c.sort_values("match_score", ascending=False)
    if top_n is not None:
        results = results.head(top_n)
    return results, funnel


def explain_exclusion(
    row: pd.Series,
    client: dict,
    program_earnings: pd.DataFrame | None = None,
    full_df: pd.DataFrame | None = None,
) -> list[str]:
    """
    Return a list of plain-English reasons why *row* fails the hard filters in *client*.

    An empty list means the school passes all filters (it would appear in match() results).
    Reuses the exact same rules as match() so the two can never disagree.

    full_df is required only when hidden_gems_only=True (needed to compute percentile rank).
    """
    reasons = []

    if client.get("require_f1", True):
        if not row.get("sevp_certified"):
            reasons.append("Not F-1 certified (SEVP)")

    if row.get("school_type") not in client["school_types"]:
        reasons.append(f"School type '{row.get('school_type')}' not in {client['school_types']}")

    if client.get("states"):
        if row.get("state") not in client["states"]:
            reasons.append(f"State {row.get('state')} not in selected states")

    if client.get("city_groups"):
        # Compute city_group the same way load_data does
        raw_size = row.get("city_size")
        city_group = None
        if pd.notna(raw_size):
            s = str(raw_size).lower()
            for k in ["city", "suburb", "town", "rural"]:
                if k in s:
                    city_group = k.capitalize()
                    break
        if city_group not in client["city_groups"]:
            reasons.append(f"City size '{city_group}' not in {client['city_groups']}")

    religion = client.get("religion")
    if religion:
        _none_affil = {-1, -2}
        affil = row.get("religious_affil")
        affil_int = None
        try:
            affil_int = int(affil) if pd.notna(affil) else None
        except (TypeError, ValueError):
            pass
        if religion == "catholic":
            if affil_int != 30:
                reasons.append("Not Catholic-affiliated")
        elif religion == "any_religious":
            if affil_int is None or affil_int in _none_affil:
                reasons.append("No stated religious affiliation")
        elif religion == "non_religious":
            if affil_int is not None and affil_int not in _none_affil:
                reasons.append("Has a religious affiliation")

    max_budget = client.get("max_budget")
    if max_budget is not None:
        limit = max_budget * client.get("budget_flex", 1.0)
        cost = row.get("cost_international")
        if pd.isna(cost) or cost > limit:
            cost_str = f"${cost:,.0f}" if pd.notna(cost) else "unknown"
            reasons.append(f"Cost {cost_str} is over the ${limit:,.0f} budget")

    if client.get("sport"):
        col = "mens_sports" if client.get("gender") == "men" else "womens_sports"
        sports_raw = row.get(col)
        sports_raw = sports_raw if pd.notna(sports_raw) else ""
        sports_list = [x.strip() for x in str(sports_raw).split(";")]
        if client["sport"] not in sports_list:
            gender_label = client.get("gender", "men")
            reasons.append(f"No {gender_label}'s {client['sport']} team")

    if client.get("needs_athletic_scholarship"):
        tier = row.get("athletic_aid_tier")
        if tier not in ("Athletic scholarships", "Mixed / verify"):
            reasons.append("No athletic scholarships in its division")

    mg4 = client.get("min_grad_rate_4yr")
    mg2 = client.get("min_grad_rate_2yr")
    if mg4 or mg2:
        threshold = mg4 if row.get("school_type") == "4-year" else (mg2 or 0)
        if threshold:
            grad = row.get("grad_rate")
            if pd.notna(grad) and grad < threshold:
                reasons.append(
                    f"Graduation rate {grad:.0%} is below the {threshold:.0%} minimum"
                )

    if client.get("majors"):
        prefixes = client["majors"]

        def has_major(cips):
            return any(c.startswith(p) for c in str(cips).split(";") if c for p in prefixes)

        programs_known = row.get("programs_known", False)
        strict = client.get("strict_major", False)
        if programs_known:
            if row.get("school_type") == "4-year":
                if not has_major(row.get("bachelor_cips", "")):
                    reasons.append(f"Doesn't offer {', '.join(prefixes)} programs")
            else:
                if not has_major(row.get("associate_cips", "")) and not (
                    not strict and row.get("has_transfer_track")
                ):
                    reasons.append(f"Doesn't offer {', '.join(prefixes)} programs")

    if client.get("hidden_gems_only"):
        admit = row.get("admit_rate")
        tier = row.get("selectivity_tier") or selectivity_tier(admit)
        if tier == "Reach":
            rate_str = f"{admit:.0%}" if pd.notna(admit) else "unknown"
            reasons.append(f"Highly selective (admit rate {rate_str})")
        elif full_df is not None:
            # Compute program_strength percentile for this row against the full pool
            ps_series = _program_strength_percentiles(full_df, client.get("majors"), program_earnings)
            ps_val = ps_series.get(row.name, 0.5)
            if ps_val < 0.75:
                reasons.append("Not a hidden gem: graduate outcomes below the top quarter")

    return reasons
