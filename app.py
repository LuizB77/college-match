"""
College Match — Streamlit demo.
Sidebar inputs → src/matcher.py → funnel table + ranked results.
"""

import os
import streamlit as st
import pandas as pd

from src.matcher import load_data, match, SHOW_COLS

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="College Match", layout="wide")
st.title("College Match")
st.caption(
    "Matches international student-athletes to US colleges and JUCOs "
    "using cost, athletics, graduation rates, and program data."
)

# ── Data ───────────────────────────────────────────────────────────────────────
DATA_PATH = os.path.join(os.path.dirname(__file__), "data/processed/schools_with_majors.csv")


@st.cache_data
def get_data():
    return load_data(DATA_PATH)


df = get_data()

ALL_SPORTS = sorted({
    s.strip()
    for col in ["mens_sports", "womens_sports"]
    for cell in df[col].dropna()
    for s in cell.split(";")
    if s.strip()
})

ALL_STATES = sorted(df["state"].dropna().unique().tolist())

MAJOR_OPTIONS = {
    "None": None,
    "Business (52)": ["52"],
    "Entrepreneurship (5207)": ["5207"],
    "Engineering (14)": ["14"],
    "Computer Science (11)": ["11"],
    "Health Professions (51)": ["51"],
}

WEIGHT_KEYS = [
    "low_cost",
    "grad_rate",
    "sport_culture",
    "athlete_opportunity",
    "international_community",
    "open_admission",
    "small_school",
    "entrepreneurship_program",
]

FEATURE_LABELS = {
    "low_cost": "Low cost",
    "grad_rate": "Grad rate",
    "sport_culture": "Sport culture",
    "athlete_opportunity": "Athlete opportunity",
    "international_community": "International community",
    "open_admission": "Open admission",
    "small_school": "Small school",
    "entrepreneurship_program": "Entrepreneurship program",
}

# Default weights from notebook 04 cell 2
DEFAULT_WEIGHTS = {
    "low_cost": 5,
    "grad_rate": 3,
    "sport_culture": 2,
    "athlete_opportunity": 4,
    "international_community": 3,
    "open_admission": 0,
    "small_school": 1,
    "entrepreneurship_program": 2,
}

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Client profile")

    # Budget
    st.subheader("Budget")
    max_budget = st.slider("Max budget ($/yr)", 5_000, 80_000, 25_000, step=500,
                           format="$%d",
                           help="Max sticker cost before scholarships.")
    budget_flex = st.slider("Budget flex ×", 1.0, 2.0, 1.5, step=0.1,
                            help="Multiply budget by this to allow athletes on aid to attend.")

    # School
    st.subheader("School")
    school_types = st.multiselect("School types", ["2-year", "4-year"],
                                  default=["2-year", "4-year"])
    states = st.multiselect("States (empty = anywhere)", ALL_STATES, default=[])
    city_groups = st.multiselect("City type (empty = any)",
                                 ["City", "Suburb", "Town", "Rural"], default=[])

    # Sport
    st.subheader("Sport")
    sport_choice = st.selectbox("Sport", ["None"] + ALL_SPORTS, index=ALL_SPORTS.index("Soccer") + 1)
    gender = st.radio("Gender", ["men", "women"], index=0)
    needs_scholarship = st.checkbox("Needs athletic scholarship", value=True)

    # Academics
    st.subheader("Academics")
    major_label = st.selectbox("Major area", list(MAJOR_OPTIONS.keys()), index=1)
    strict_major = st.checkbox("Require exact major (don't count general transfer tracks)",
                               value=False,
                               help="When checked, 2-year schools must offer the major as an associate degree; a general Liberal Arts transfer track no longer qualifies.")
    min_grad_4yr = st.slider("Min grad rate — 4-year", 0, 100, 30, step=5,
                             format="%d%%",
                             help="4-year schools below this are excluded. Schools with unknown rates are kept.")
    min_grad_2yr = st.slider("Min grad rate — 2-year", 0, 100, 20, step=5,
                             format="%d%%")

    # Visa
    st.subheader("Visa")
    require_f1 = st.checkbox("Require F-1 eligibility (SEVP certified)", value=True)

    # Weights
    st.subheader("Score weights  (0 = ignore, 5 = critical)")
    weights = {}
    for k in WEIGHT_KEYS:
        weights[k] = st.slider(FEATURE_LABELS[k], 0, 5, DEFAULT_WEIGHTS[k], key=f"w_{k}")

# ── Build client dict ──────────────────────────────────────────────────────────
client = {
    "name": "Streamlit session",
    "require_f1": require_f1,
    "max_budget": max_budget,
    "budget_flex": budget_flex,
    "school_types": school_types if school_types else ["2-year", "4-year"],
    "states": states if states else None,
    "city_groups": city_groups if city_groups else None,
    "sport": sport_choice if sport_choice != "None" else None,
    "gender": gender,
    "needs_athletic_scholarship": needs_scholarship,
    "min_grad_rate_4yr": min_grad_4yr / 100,
    "min_grad_rate_2yr": min_grad_2yr / 100,
    "majors": MAJOR_OPTIONS[major_label],
    "strict_major": strict_major,
    "weights": weights,
}

# ── Run matcher ────────────────────────────────────────────────────────────────
results, funnel = match(df, client, top_n=25)

# ── Funnel table ───────────────────────────────────────────────────────────────
st.subheader("Filter funnel")

# Replace CIP codes in the major step label with the selected major's display name.
major_display = major_label if major_label != "None" else ""
pretty_funnel = []
for step, n in funnel:
    if step.startswith("After offers major") and major_display:
        step = f"After offers major: {major_display.split(' (')[0]}"
    pretty_funnel.append((step, n))

funnel_df = pd.DataFrame(pretty_funnel, columns=["Step", "Schools remaining"])
st.dataframe(funnel_df, use_container_width=False, hide_index=True)

# ── Results ────────────────────────────────────────────────────────────────────
st.subheader("Top matches")

if results.empty:
    st.info("No schools pass the current filters. Try relaxing budget, grad rate, or sport filters.")
else:
    display = results[SHOW_COLS].copy()
    display["cost_international"] = display["cost_international"].apply(
        lambda x: f"${x:,.0f}" if pd.notna(x) else "—"
    )
    display["grad_rate"] = display["grad_rate"].apply(
        lambda x: f"{x:.0%}" if pd.notna(x) else "—"
    )
    display["pct_international"] = display["pct_international"].apply(
        lambda x: f"{x:.0%}" if pd.notna(x) else "—"
    )
    display["athlete_share"] = display["athlete_share"].apply(
        lambda x: f"{x:.0%}" if pd.notna(x) else "—"
    )
    # Map internal feature keys in "top_reasons" to readable labels; one per line for full visibility.
    def readable_reasons(s):
        return "\n".join(FEATURE_LABELS.get(r.strip(), r.strip()) for r in str(s).split(","))

    display["top_reasons"] = display["top_reasons"].apply(readable_reasons)

    display = display.rename(columns={
        "name": "School",
        "state": "ST",
        "school_type": "Type",
        "association": "Association",
        "cost_international": "Intl cost/yr",
        "grad_rate": "Grad rate",
        "pct_international": "% Intl",
        "athlete_share": "Athlete share",
        "offers_entrepreneurship": "Entrep.",
        "match_score": "Score",
        "top_reasons": "Top reasons",
    })

    col_config = {
        "Top reasons": st.column_config.TextColumn("Top reasons", width="medium"),
    }
    st.dataframe(display, use_container_width=True, hide_index=True, column_config=col_config)

    st.caption(
        "**How to read this:** Costs are sticker prices before scholarships — "
        "athletes may pay significantly less. "
        "2-year grad rates understate success because early transfers count as non-completers. "
        "Scores are relative to this client's filtered pool (0–100), not absolute quality."
    )

    csv = results[SHOW_COLS].to_csv(index=False).encode()
    st.download_button("Download results (CSV)", csv, "college_match_results.csv", "text/csv")
