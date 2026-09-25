"""
College Match — Streamlit demo.
Sidebar inputs → src/matcher.py → funnel table + ranked results.
"""

import altair as alt
import streamlit as st
import pandas as pd
from pathlib import Path

from src.matcher import load_data, match, SHOW_COLS

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="College Match", layout="wide")
st.title("College Match")
st.caption(
    "Matches international student-athletes to US colleges and JUCOs "
    "using cost, athletics, graduation rates, and program data."
)

# ── Data ───────────────────────────────────────────────────────────────────────
DATA_PATH = Path(__file__).parent / "data" / "processed" / "schools_with_majors.csv"


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

# Plain-language major names; values are CIP prefixes passed to the matcher.
MAJOR_OPTIONS = {
    "None": None,
    "Business": ["52"],
    "Entrepreneurship": ["5207"],
    "Engineering": ["14"],
    "Computer Science": ["11"],
    "Health Professions": ["51"],
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
    "grad_rate": "Graduation rate",
    "sport_culture": "Big-time sports",
    "athlete_opportunity": "Athlete-friendly campus",
    "international_community": "International students",
    "open_admission": "Open admission",
    "small_school": "Small school",
    "entrepreneurship_program": "Entrepreneurship program",
}

FEATURE_HELP = {
    "low_cost": "Cheaper sticker price ranks higher.",
    "grad_rate": "Schools where more students finish rank higher.",
    "sport_culture": "Schools with large, well-known athletics programs rank higher.",
    "athlete_opportunity": "Schools where athletes are a big share of students (more roster spots, more recruiting).",
    "international_community": "Schools with more international students (usually better support).",
    "open_admission": "Schools that accept everyone rank higher (for weaker academic records).",
    "small_school": "Smaller schools rank higher.",
    "entrepreneurship_program": "Schools offering an entrepreneurship degree rank higher.",
}

# Word labels map 1-to-1 onto 0–5 integers.
SLIDER_OPTIONS = ["Don't care", "A little", "Somewhat", "Important", "Very important", "Top priority"]
WORD_TO_INT = {w: i for i, w in enumerate(SLIDER_OPTIONS)}

PRESETS = {
    "Balanced": {
        "low_cost": 5, "grad_rate": 3, "sport_culture": 2, "athlete_opportunity": 4,
        "international_community": 3, "open_admission": 0, "small_school": 1,
        "entrepreneurship_program": 2,
    },
    "Budget first": {
        "low_cost": 5, "grad_rate": 2, "sport_culture": 0, "athlete_opportunity": 1,
        "international_community": 2, "open_admission": 0, "small_school": 0,
        "entrepreneurship_program": 0,
    },
    "Athlete first": {
        "low_cost": 3, "grad_rate": 1, "sport_culture": 3, "athlete_opportunity": 5,
        "international_community": 2, "open_admission": 0, "small_school": 0,
        "entrepreneurship_program": 0,
    },
    "Academics first": {
        "low_cost": 2, "grad_rate": 5, "sport_culture": 0, "athlete_opportunity": 0,
        "international_community": 3, "open_admission": 0, "small_school": 1,
        "entrepreneurship_program": 1,
    },
    "Future entrepreneur": {
        "low_cost": 3, "grad_rate": 3, "sport_culture": 0, "athlete_opportunity": 0,
        "international_community": 3, "open_admission": 0, "small_school": 0,
        "entrepreneurship_program": 5,
    },
}

# Session state for weight sliders: stores word strings so select_slider can read them directly.
# Only initialised once; the preset on_change callback overwrites them.
for k in WEIGHT_KEYS:
    if f"w_{k}" not in st.session_state:
        st.session_state[f"w_{k}"] = SLIDER_OPTIONS[PRESETS["Balanced"][k]]


def _apply_preset():
    name = st.session_state["preset_select"]
    if name in PRESETS:
        for k, v in PRESETS[name].items():
            st.session_state[f"w_{k}"] = SLIDER_OPTIONS[v]


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:

    # ── Must-haves ─────────────────────────────────────────────────────────────
    st.header("Must-haves")
    st.caption("Schools that fail any of these are removed.")

    max_budget = st.slider(
        "Max the family can pay per year",
        5_000, 80_000, 25_000, step=500, format="$%d",
    )

    school_types = st.multiselect(
        "What type of school?", ["2-year", "4-year"], default=["2-year", "4-year"],
    )

    states = st.multiselect("Where? (leave empty for anywhere)", ALL_STATES, default=[])
    city_groups = st.multiselect(
        "City size? (leave empty for any)", ["City", "Suburb", "Town", "Rural"], default=[],
    )

    plays_sport = st.toggle("Does the student play a sport?", value=True)
    if plays_sport:
        sport_choice = st.selectbox("Sport", ALL_SPORTS, index=ALL_SPORTS.index("Soccer"))
        gender = st.radio("Gender", ["men", "women"], index=0)
        needs_scholarship = st.checkbox("Needs an athletic scholarship", value=True)
    else:
        sport_choice = None
        gender = "men"
        needs_scholarship = False

    major_label = st.selectbox("Intended major", list(MAJOR_OPTIONS.keys()), index=1)

    with st.expander("Advanced"):
        budget_flex = st.slider(
            "Stretch budget for athletes (scholarships expected)",
            1.0, 2.0, 1.5, step=0.1, format="%.1f",
            help="1.5 = consider schools up to 50% over budget (the athlete may receive aid that closes the gap).",
        )
        min_grad_4yr = st.slider(
            "Min grad rate — 4-year", 0, 100, 30, step=5, format="%d%%",
            help="4-year schools below this are excluded. Schools with unknown rates are kept.",
        )
        min_grad_2yr = st.slider("Min grad rate — 2-year", 0, 100, 20, step=5, format="%d%%")
        strict_major = st.checkbox(
            "Require exact major (don't count general transfer tracks)", value=False,
            help="When checked, 2-year schools must offer the major as an associate degree; "
                 "a Liberal Arts transfer track no longer qualifies.",
        )
        require_f1 = st.checkbox("Require F-1 eligibility (SEVP certified)", value=True)

    st.divider()

    # ── What matters most ──────────────────────────────────────────────────────
    st.header("What matters most")
    st.caption("These don't remove schools; they decide the order of what's left.")

    st.selectbox(
        "Start from a preset",
        list(PRESETS.keys()),
        key="preset_select",
        on_change=_apply_preset,
    )

    weights = {}
    for k in WEIGHT_KEYS:
        word = st.select_slider(
            FEATURE_LABELS[k],
            options=SLIDER_OPTIONS,
            key=f"w_{k}",
            help=FEATURE_HELP[k],
        )
        weights[k] = WORD_TO_INT[word]

    # Weight breakdown bar chart
    total_weight = sum(weights.values())
    if total_weight == 0:
        st.caption("All preferences set to 'Don't care' — results are unranked.")
    else:
        chart_data = pd.DataFrame([
            {"Preference": FEATURE_LABELS[k], "Share (%)": round(v / total_weight * 100)}
            for k, v in weights.items()
            if v > 0
        ]).sort_values("Share (%)", ascending=False)

        chart = (
            alt.Chart(chart_data)
            .mark_bar()
            .encode(
                x=alt.X("Share (%):Q", axis=alt.Axis(title=None, labels=False, ticks=False)),
                y=alt.Y("Preference:N", sort="-x", axis=alt.Axis(title=None)),
                tooltip=["Preference", "Share (%)"],
            )
            .properties(
                height=max(60, len(chart_data) * 24),
                title="What's driving the ranking",
            )
            .configure_axis(grid=False)
            .configure_view(strokeWidth=0)
        )
        st.altair_chart(chart, use_container_width=True)

# ── Build client dict ──────────────────────────────────────────────────────────
client = {
    "name": "Streamlit session",
    "require_f1": require_f1,
    "max_budget": max_budget,
    "budget_flex": budget_flex,
    "school_types": school_types if school_types else ["2-year", "4-year"],
    "states": states if states else None,
    "city_groups": city_groups if city_groups else None,
    "sport": sport_choice,
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

pretty_funnel = []
for step, n in funnel:
    if step.startswith("After offers major") and major_label != "None":
        step = f"After offers major: {major_label}"
    pretty_funnel.append((step, n))

funnel_df = pd.DataFrame(pretty_funnel, columns=["Step", "Schools remaining"])
st.dataframe(funnel_df, use_container_width=False, hide_index=True)

# ── Results ────────────────────────────────────────────────────────────────────
st.subheader("Top matches")

if results.empty:
    st.info("No schools pass the current filters. Try relaxing budget, grad rate, or sport filters.")
else:
    display = results[SHOW_COLS].copy()

    # Split "key1, key2" top_reasons into two plain-language columns.
    reasons = display["top_reasons"].str.split(", ", n=1, expand=True)
    display["why_1"] = reasons[0].map(
        lambda x: FEATURE_LABELS.get(str(x).strip(), str(x).strip()) if pd.notna(x) else ""
    )
    display["why_2"] = (
        reasons[1] if 1 in reasons.columns
        else pd.Series("", index=display.index)
    ).map(lambda x: FEATURE_LABELS.get(str(x).strip(), str(x).strip()) if pd.notna(x) else "")

    display = display.drop(columns=["top_reasons"])

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
        "why_1": "Why #1",
        "why_2": "Why #2",
    })

    st.dataframe(display, use_container_width=True, hide_index=True)

    st.caption(
        "**How to read this:** Costs are sticker prices before scholarships — "
        "athletes may pay significantly less. "
        "2-year grad rates understate success because early transfers count as non-completers. "
        "Scores are relative to this client's filtered pool (0–100), not absolute quality."
    )

    csv = results[SHOW_COLS].to_csv(index=False).encode()
    st.download_button("Download results (CSV)", csv, "college_match_results.csv", "text/csv")
