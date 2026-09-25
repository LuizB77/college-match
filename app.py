"""
College Match — Streamlit demo.
Sidebar inputs → src/matcher.py → metrics, cards, map, full table.
"""

from pathlib import Path
import altair as alt
import pydeck as pdk
import streamlit as st
import pandas as pd

from src.matcher import load_data, match, SHOW_COLS

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="College Match",
    page_icon=":material/school:",
    layout="wide",
)

# ── Constants ──────────────────────────────────────────────────────────────────
PRIMARY_COLOR = "#0B6E4F"
PRIMARY_RGB   = [11, 110, 79]   # matches theme primaryColor

DATA_PATH = Path(__file__).parent / "data" / "processed" / "schools_with_majors.csv"

MAJOR_OPTIONS = {
    "None":              None,
    "Business":          ["52"],
    "Entrepreneurship":  ["5207"],
    "Engineering":       ["14"],
    "Computer Science":  ["11"],
    "Health Professions":["51"],
}

WEIGHT_KEYS = [
    "low_cost", "grad_rate", "sport_culture", "athlete_opportunity",
    "international_community", "open_admission", "small_school", "entrepreneurship_program",
]

# Single source of truth for human-readable feature names — used by sliders, cards, and table.
FEATURE_LABELS = {
    "low_cost":               "Low cost",
    "grad_rate":              "Graduation rate",
    "sport_culture":          "Big-time sports",
    "athlete_opportunity":    "Athlete-friendly campus",
    "international_community":"International students",
    "open_admission":         "Open admission",
    "small_school":           "Small school",
    "entrepreneurship_program":"Entrepreneurship program",
}

FEATURE_HELP = {
    "low_cost":               "Cheaper sticker price ranks higher.",
    "grad_rate":              "Schools where more students finish rank higher.",
    "sport_culture":          "Schools with large, well-known athletics programs rank higher.",
    "athlete_opportunity":    "Schools where athletes are a big share of students (more roster spots, more recruiting).",
    "international_community":"Schools with more international students (usually better support).",
    "open_admission":         "Schools that accept everyone rank higher (for weaker academic records).",
    "small_school":           "Smaller schools rank higher.",
    "entrepreneurship_program":"Schools offering an entrepreneurship degree rank higher.",
}

SLIDER_OPTIONS = ["Don't care", "A little", "Somewhat", "Important", "Very important", "Top priority"]
WORD_TO_INT    = {w: i for i, w in enumerate(SLIDER_OPTIONS)}

PRESETS = {
    "Balanced": {
        "low_cost": 5, "grad_rate": 3, "sport_culture": 2, "athlete_opportunity": 4,
        "international_community": 3, "open_admission": 0, "small_school": 1, "entrepreneurship_program": 2,
    },
    "Budget first": {
        "low_cost": 5, "grad_rate": 2, "sport_culture": 0, "athlete_opportunity": 1,
        "international_community": 2, "open_admission": 0, "small_school": 0, "entrepreneurship_program": 0,
    },
    "Athlete first": {
        "low_cost": 3, "grad_rate": 1, "sport_culture": 3, "athlete_opportunity": 5,
        "international_community": 2, "open_admission": 0, "small_school": 0, "entrepreneurship_program": 0,
    },
    "Academics first": {
        "low_cost": 2, "grad_rate": 5, "sport_culture": 0, "athlete_opportunity": 0,
        "international_community": 3, "open_admission": 0, "small_school": 1, "entrepreneurship_program": 1,
    },
    "Future entrepreneur": {
        "low_cost": 3, "grad_rate": 3, "sport_culture": 0, "athlete_opportunity": 0,
        "international_community": 3, "open_admission": 0, "small_school": 0, "entrepreneurship_program": 5,
    },
}

AID_TIERS = {"Athletic scholarships", "Mixed / verify"}


# ── Data ───────────────────────────────────────────────────────────────────────
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

# ── Session state for weight sliders ──────────────────────────────────────────
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

    st.header("Must-haves")
    st.caption("Schools that fail any of these are removed.")

    max_budget = st.slider(
        "Max the family can pay per year",
        5_000, 80_000, 25_000, step=500, format="$%d",
    )
    school_types = st.multiselect(
        "What type of school?", ["2-year", "4-year"], default=["2-year", "4-year"],
    )
    states     = st.multiselect("Where? (leave empty for anywhere)", ALL_STATES, default=[])
    city_groups = st.multiselect(
        "City size? (leave empty for any)", ["City", "Suburb", "Town", "Rural"], default=[],
    )

    plays_sport = st.toggle("Does the student play a sport?", value=True)
    if plays_sport:
        sport_choice      = st.selectbox("Sport", ALL_SPORTS, index=ALL_SPORTS.index("Soccer"))
        gender            = st.radio("Gender", ["men", "women"], index=0)
        needs_scholarship = st.checkbox("Needs an athletic scholarship", value=True)
    else:
        sport_choice      = None
        gender            = "men"
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
        min_grad_2yr  = st.slider("Min grad rate — 2-year", 0, 100, 20, step=5, format="%d%%")
        strict_major  = st.checkbox(
            "Require exact major (don't count general transfer tracks)", value=False,
            help="When checked, 2-year schools must offer the major as an associate degree; "
                 "a Liberal Arts transfer track no longer qualifies.",
        )
        require_f1 = st.checkbox("Require F-1 eligibility (SEVP certified)", value=True)

    st.divider()

    st.header("What matters most")
    st.caption("These don't remove schools; they decide the order of what's left.")

    st.selectbox(
        "Start from a preset", list(PRESETS.keys()),
        key="preset_select", on_change=_apply_preset,
    )

    weights = {}
    for k in WEIGHT_KEYS:
        word = st.select_slider(
            FEATURE_LABELS[k], options=SLIDER_OPTIONS,
            key=f"w_{k}", help=FEATURE_HELP[k],
        )
        weights[k] = WORD_TO_INT[word]

    total_weight = sum(weights.values())
    if total_weight == 0:
        st.caption("All preferences set to 'Don't care' — results are unranked.")
    else:
        chart_data = pd.DataFrame([
            {"Preference": FEATURE_LABELS[k], "Share (%)": round(v / total_weight * 100)}
            for k, v in weights.items() if v > 0
        ]).sort_values("Share (%)", ascending=False)

        chart = (
            alt.Chart(chart_data).mark_bar()
            .encode(
                x=alt.X("Share (%):Q", axis=alt.Axis(title=None, labels=False, ticks=False)),
                y=alt.Y("Preference:N", sort="-x", axis=alt.Axis(title=None)),
                tooltip=["Preference", "Share (%)"],
            )
            .properties(height=max(60, len(chart_data) * 24), title="What's driving the ranking")
            .configure_axis(grid=False)
            .configure_view(strokeWidth=0)
        )
        st.altair_chart(chart, use_container_width=True)

# ── Build client dict ──────────────────────────────────────────────────────────
client = {
    "name":                    "Streamlit session",
    "require_f1":              require_f1,
    "max_budget":              max_budget,
    "budget_flex":             budget_flex,
    "school_types":            school_types if school_types else ["2-year", "4-year"],
    "states":                  states if states else None,
    "city_groups":             city_groups if city_groups else None,
    "sport":                   sport_choice,
    "gender":                  gender,
    "needs_athletic_scholarship": needs_scholarship,
    "min_grad_rate_4yr":       min_grad_4yr / 100,
    "min_grad_rate_2yr":       min_grad_2yr / 100,
    "majors":                  MAJOR_OPTIONS[major_label],
    "strict_major":            strict_major,
    "weights":                 weights,
}

# ── Run matcher ────────────────────────────────────────────────────────────────
results, funnel = match(df, client, top_n=25)

# ── Header ─────────────────────────────────────────────────────────────────────
st.title("College Match")
st.markdown(
    "Find U.S. colleges and junior colleges that fit an international student's "
    "budget, sport, major, and visa needs."
)

# ── Metrics ────────────────────────────────────────────────────────────────────
m1, m2, m3 = st.columns(3)
with m1:
    st.metric("Schools that fit", len(results) if not results.empty else 0)
with m2:
    if not results.empty:
        median_cost = results["cost_international"].median()
        st.metric(
            "Median yearly cost (before scholarships)",
            f"${median_cost:,.0f}" if pd.notna(median_cost) else "—",
        )
    else:
        st.metric("Median yearly cost (before scholarships)", "—")
with m3:
    if client.get("sport") and not results.empty:
        aid_count = results["athletic_aid_tier"].isin(AID_TIERS).sum()
        st.metric("Offer athletic scholarships", aid_count)

# ── Empty state ────────────────────────────────────────────────────────────────
if results.empty:
    st.info("No schools pass the current filters. Try relaxing budget, grad rate, or sport filters.")
    st.stop()

# ── Helper: split top_reasons key string → two plain labels ───────────────────
def split_reasons(raw: str):
    parts = [p.strip() for p in str(raw).split(",", 1)]
    w1 = FEATURE_LABELS.get(parts[0], parts[0]) if len(parts) > 0 else ""
    w2 = FEATURE_LABELS.get(parts[1], parts[1]) if len(parts) > 1 else ""
    return w1, w2

# ── Result cards — top 6 ──────────────────────────────────────────────────────
st.subheader("Top matches")
top6 = results.head(6).reset_index(drop=True)
card_cols = st.columns(3)

for i, row in top6.iterrows():
    col = card_cols[i % 3]
    with col:
        with st.container(border=True):
            rank = i + 1
            st.markdown(f"**#{rank} · {row['name']}**")
            st.caption(f"{row['city']}, {row['state']}  ·  {row['school_type']}  ·  {row['association']}")

            cost = row["cost_international"]
            cost_str = f"${cost:,.0f}" if pd.notna(cost) else "—"
            st.markdown(f"### {cost_str}")
            st.caption("per year · sticker price before scholarships")

            score = float(row["match_score"])
            st.progress(score / 100, text=f"Match score: {score:.1f} / 100")

            # Badges
            badges = [("F-1 certified", "green")]
            if row.get("athletic_aid_tier") in AID_TIERS:
                badges.append(("Athletic aid", "blue"))
            if row.get("offers_entrepreneurship"):
                badges.append(("Entrepreneurship", "orange"))
            if row.get("school_type") == "2-year" and row.get("has_transfer_track"):
                badges.append(("Transfer track", "violet"))

            st.markdown(" ".join(f":{c}-badge[{l}]" for l, c in badges))

            w1, w2 = split_reasons(row["top_reasons"])
            why = " · ".join(filter(None, [w1, w2]))
            st.caption(f"Why: {why}")

# ── Full table in expander ─────────────────────────────────────────────────────
with st.expander("See all matches as a table"):
    display = results[SHOW_COLS].copy()

    reasons = display["top_reasons"].str.split(", ", n=1, expand=True)
    display["why_1"] = reasons[0].map(
        lambda x: FEATURE_LABELS.get(str(x).strip(), str(x).strip()) if pd.notna(x) else ""
    )
    display["why_2"] = (
        reasons[1] if 1 in reasons.columns else pd.Series("", index=display.index)
    ).map(lambda x: FEATURE_LABELS.get(str(x).strip(), str(x).strip()) if pd.notna(x) else "")
    display = display.drop(columns=["top_reasons"])

    display["cost_international"] = display["cost_international"].apply(
        lambda x: f"${x:,.0f}" if pd.notna(x) else "—"
    )
    display["grad_rate"]        = display["grad_rate"].apply(lambda x: f"{x:.0%}" if pd.notna(x) else "—")
    display["pct_international"] = display["pct_international"].apply(lambda x: f"{x:.0%}" if pd.notna(x) else "—")
    display["athlete_share"]    = display["athlete_share"].apply(lambda x: f"{x:.0%}" if pd.notna(x) else "—")

    display = display.rename(columns={
        "name": "School", "state": "ST", "school_type": "Type", "association": "Association",
        "cost_international": "Intl cost/yr", "grad_rate": "Grad rate",
        "pct_international": "% Intl", "athlete_share": "Athlete share",
        "offers_entrepreneurship": "Entrep.", "match_score": "Score",
        "why_1": "Why #1", "why_2": "Why #2",
    })
    st.dataframe(display, use_container_width=True, hide_index=True)

    st.caption(
        "**How to read this:** Costs are sticker prices before scholarships — athletes may pay significantly less. "
        "2-year grad rates understate success because early transfers count as non-completers. "
        "Scores are relative to this client's filtered pool (0–100), not absolute quality."
    )

    csv = results[SHOW_COLS].to_csv(index=False).encode()
    st.download_button("Download results (CSV)", csv, "college_match_results.csv", "text/csv")

# ── Funnel (collapsed by default) ─────────────────────────────────────────────
with st.expander("Filter funnel"):
    pretty_funnel = []
    for step, n in funnel:
        if step.startswith("After offers major") and major_label != "None":
            step = f"After offers major: {major_label}"
        pretty_funnel.append((step, n))
    st.dataframe(
        pd.DataFrame(pretty_funnel, columns=["Step", "Schools remaining"]),
        use_container_width=False, hide_index=True,
    )

# ── Map ────────────────────────────────────────────────────────────────────────
st.subheader("Where they are")

map_df = results[["name", "city", "state", "lat", "lon", "cost_international", "match_score"]].dropna(
    subset=["lat", "lon"]
).reset_index(drop=True).copy()

map_df["rank"]     = map_df.index + 1
map_df["is_top6"]  = map_df["rank"] <= 6
map_df["color"]    = map_df["is_top6"].apply(
    lambda t: PRIMARY_RGB + [230] if t else [150, 150, 150, 160]
)
map_df["radius"]   = map_df["is_top6"].apply(lambda t: 55_000 if t else 38_000)
map_df["cost_fmt"] = map_df["cost_international"].apply(
    lambda x: f"${x:,.0f}" if pd.notna(x) else "—"
)

layer = pdk.Layer(
    "ScatterplotLayer",
    data=map_df,
    get_position="[lon, lat]",
    get_fill_color="color",
    get_radius="radius",
    pickable=True,
)

view = pdk.ViewState(latitude=38.5, longitude=-96.5, zoom=3, pitch=0)

tooltip = {
    "html": (
        "<b>{name}</b><br/>"
        "{city}, {state}<br/>"
        "Cost: {cost_fmt}/yr<br/>"
        "Score: {match_score}"
    ),
    "style": {
        "backgroundColor": "white",
        "color": "#1A1A1A",
        "padding": "8px",
        "borderRadius": "4px",
        "fontSize": "13px",
    },
}

st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view, tooltip=tooltip))
st.caption("Top 6 in green · remaining matches in gray · hover for details.")
