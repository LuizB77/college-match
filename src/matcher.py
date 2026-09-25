"""
Core matching logic extracted verbatim from notebooks/04_match.ipynb.
Do not change algorithms here without also updating the notebook.
"""

import numpy as np
import pandas as pd


# Columns shown in results tables (same list as notebook 04 cell 3).
SHOW_COLS = [
    "name", "state", "school_type", "association",
    "cost_international", "grad_rate",
    "pct_international", "athlete_share",
    "offers_entrepreneurship", "match_score", "top_reasons",
]


def load_data(path="data/processed/schools_with_majors.csv") -> pd.DataFrame:
    """Load and prep the schools dataset (verbatim from notebook 04 cell 1)."""
    df = pd.read_csv(path)
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
    return df


def match(df: pd.DataFrame, client: dict, top_n: int = 25):
    """
    Apply hard filters then rank by weighted score (verbatim from notebook 04 cell 3).

    Returns
    -------
    results_df : pd.DataFrame
        Top `top_n` schools sorted by match_score descending.
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

    if client["states"]:
        c = c[c["state"].isin(client["states"])]
        funnel.append(("After states", len(c)))

    if client["city_groups"]:
        c = c[c["city_group"].isin(client["city_groups"])]
        funnel.append(("After city size", len(c)))

    limit = client["max_budget"] * client.get("budget_flex", 1.0)
    c = c[c["cost_international"] <= limit]            # unknown cost (NaN) is excluded too
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
    if mg4 is not None or mg2 is not None:
        # Each school gets the threshold for its type; missing grad rate is kept, not punished
        threshold = np.where(c["school_type"] == "4-year", mg4 or 0, mg2 or 0)
        c = c[c["grad_rate"].isna() | (c["grad_rate"] >= threshold)]
        funnel.append(("After minimum grad rate", len(c)))

    if client.get("majors"):
        prefixes = client["majors"]

        def has_major(cips):
            return any(c.startswith(p) for c in str(cips).split(";") if c for p in prefixes)

        def major_ok(r):
            if not r["programs_known"]:
                return True    # no program data: unknown, not failing -> keep
            if r["school_type"] == "4-year":
                return has_major(r["bachelor_cips"])
            # JUCO: the major itself, or a general transfer track (Liberal Arts, CIP 24.01)
            return has_major(r["associate_cips"]) or r["has_transfer_track"]

        c = c[c.apply(major_ok, axis=1)]
        funnel.append((f"After offers major {prefixes}", len(c)))

    if c.empty:
        return c, funnel

    # --- 2. Features on a 0-1 scale (percentile among remaining schools). Missing = 0.5 neutral. ---
    f = pd.DataFrame(index=c.index)
    f["low_cost"] = 1 - c["cost_international"].rank(pct=True)     # cheaper = higher
    f["grad_rate"] = c["grad_rate"].rank(pct=True)
    f["sport_culture"] = c["sport_culture_pct"] / 100              # already a percentile
    f["athlete_opportunity"] = c["athlete_share"].rank(pct=True)
    f["international_community"] = c["pct_international"].rank(pct=True)
    f["open_admission"] = c["open_admission"].astype(float)
    f["small_school"] = 1 - c["undergrads"].rank(pct=True)          # smaller = higher
    f["entrepreneurship_program"] = c["offers_entrepreneurship"].astype(float)
    f = f.fillna(0.5)

    # --- 3. Weighted score 0-100 + the 2 features that contributed most ---
    w = pd.Series(client["weights"], dtype=float)
    contrib = f[w.index] * w
    c["match_score"] = (contrib.sum(axis=1) / w.sum() * 100).round(1)
    c["top_reasons"] = contrib.apply(lambda r: ", ".join(r.nlargest(2).index), axis=1)

    results = c.sort_values("match_score", ascending=False).head(top_n)
    return results, funnel
