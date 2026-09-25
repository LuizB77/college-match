"""
College Match — Streamlit demo.
Sidebar inputs → src/matcher.py → metrics, cards, detail dialog, compare, map, full table.
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
PRIMARY_RGB   = [11, 110, 79]

DATA_PATH     = Path(__file__).parent / "data" / "processed" / "schools_with_majors.csv"
CIP_PATH      = Path(__file__).parent / "data" / "processed" / "cip_names.csv"

MAJOR_OPTIONS = {
    "None":               None,
    "Business":           ["52"],
    "Entrepreneurship":   ["5207"],
    "Engineering":        ["14"],
    "Computer Science":   ["11"],
    "Health Professions": ["51"],
}

WEIGHT_KEYS = [
    "low_cost", "grad_rate", "sport_culture", "athlete_opportunity",
    "international_community", "open_admission", "small_school", "entrepreneurship_program",
]

# Single source of truth for human-readable feature names.
FEATURE_LABELS = {
    "low_cost":                "Low cost",
    "grad_rate":               "Graduation rate",
    "sport_culture":           "Big-time sports",
    "athlete_opportunity":     "Athlete-friendly campus",
    "international_community": "International students",
    "open_admission":          "Open admission",
    "small_school":            "Small school",
    "entrepreneurship_program":"Entrepreneurship program",
}

FEATURE_HELP = {
    "low_cost":                "Cheaper sticker price ranks higher.",
    "grad_rate":               "Schools where more students finish rank higher.",
    "sport_culture":           "Schools with large, well-known athletics programs rank higher.",
    "athlete_opportunity":     "Schools where athletes are a big share of students (more roster spots, more recruiting).",
    "international_community": "Schools with more international students (usually better support).",
    "open_admission":          "Schools that accept everyone rank higher (for weaker academic records).",
    "small_school":            "Smaller schools rank higher.",
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


@st.cache_data
def get_cip_lookup() -> dict:
    """cip4 code → program name (stripped trailing period)."""
    df = pd.read_csv(CIP_PATH, dtype=str)
    return dict(zip(df["cip4"], df["name"]))


df         = get_data()
cip_lookup = get_cip_lookup()

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


# ── Helpers ────────────────────────────────────────────────────────────────────
def split_reasons(raw: str):
    parts = [p.strip() for p in str(raw).split(",", 1)]
    w1 = FEATURE_LABELS.get(parts[0], parts[0]) if parts else ""
    w2 = FEATURE_LABELS.get(parts[1], parts[1]) if len(parts) > 1 else ""
    return w1, w2


def _program_list(cips_str: str, major_prefixes):
    """Return (is_match, name) tuples from a semicolon-separated CIP string."""
    if not cips_str:
        return []
    out = []
    for code in cips_str.split(";"):
        if not code:
            continue
        name = cip_lookup.get(code, code)
        is_match = bool(major_prefixes and any(code.startswith(p) for p in major_prefixes))
        out.append((is_match, name))
    # matching programs first
    return sorted(out, key=lambda x: (not x[0], x[1]))


# ── School detail dialog ───────────────────────────────────────────────────────
@st.dialog("School details")
def show_detail(row: pd.Series, selected_gender: str, major_prefixes):
    name = row["name"]
    st.markdown(f"## {name}")

    city_size = row.get("city_size") or "—"
    enrollment = row.get("undergrads")
    enrollment_str = f"{int(enrollment):,}" if pd.notna(enrollment) else "—"
    st.caption(
        f"📍 {row['city']}, {row['state']}  ·  {row['school_type']}  ·  "
        f"{row['association']}  ·  {city_size}\n"
        f"👥 {enrollment_str} undergraduates"
    )

    # Cost
    st.markdown("### Cost")
    cost_intl = row.get("cost_international")
    cost_oos  = row.get("tuition_out_of_state")
    col1, col2 = st.columns(2)
    col1.metric("International estimate / yr", f"${cost_intl:,.0f}" if pd.notna(cost_intl) else "—")
    col2.metric("Out-of-state tuition",        f"${cost_oos:,.0f}"  if pd.notna(cost_oos)  else "—")
    st.caption("Sticker prices before scholarships or financial aid.")

    # Athletics
    if row.get("has_athletics"):
        st.markdown("### Athletics")
        aid_tier = row.get("athletic_aid_tier") or "—"
        division = row.get("association") or "—"
        aid_col = "aid_per_athlete_men" if selected_gender == "men" else "aid_per_athlete_women"
        aid_val  = row.get(aid_col)
        aid_str  = f"${aid_val:,.0f} / yr" if pd.notna(aid_val) and aid_val > 0 else "Not reported"

        sports_col = "mens_sports" if selected_gender == "men" else "womens_sports"
        sports_raw = row.get(sports_col) or ""
        sports_list = [s.strip() for s in sports_raw.split(";") if s.strip()]

        c1, c2, c3 = st.columns(3)
        c1.metric("Division / association", division)
        c2.metric("Aid tier",               aid_tier)
        c3.metric(f"Avg aid per {selected_gender}'s athlete", aid_str)

        if sports_list:
            st.markdown(f"**{selected_gender.capitalize()}'s sports offered:** " + " · ".join(sports_list))

    # Academics
    st.markdown("### Academics")
    grad = row.get("grad_rate")
    grad_str = f"{grad:.0%}" if pd.notna(grad) else "Not reported"
    if row["school_type"] == "2-year" and pd.notna(grad):
        grad_str += " *(understates success — students who transfer early count as non-completers)*"
    pct_intl = row.get("pct_international")
    pct_str  = f"{pct_intl:.0%}" if pd.notna(pct_intl) else "—"

    c1, c2 = st.columns(2)
    c1.markdown(f"**Grad rate:** {grad_str}")
    c2.markdown(f"**International students:** {pct_str}")

    flags = []
    if row.get("has_transfer_track"):
        flags.append("Transfer track (Liberal Arts, CIP 24.01)")
    if row.get("offers_entrepreneurship"):
        flags.append("Entrepreneurship program (CIP 52.07)")
    if row.get("open_admission"):
        flags.append("Open admission")
    if flags:
        st.markdown("**Programs & policies:** " + " · ".join(flags))

    # Programs
    assoc_progs = _program_list(row.get("associate_cips", ""), major_prefixes)
    bach_progs  = _program_list(row.get("bachelor_cips",  ""), major_prefixes)

    if assoc_progs or bach_progs:
        st.markdown("### Programs offered")
        if assoc_progs:
            st.markdown("**Associate's degrees**")
            for is_match, pname in assoc_progs[:20]:
                prefix = "★ " if is_match else "· "
                st.markdown(f"&nbsp;&nbsp;{prefix}{pname}", unsafe_allow_html=True)
        if bach_progs:
            st.markdown("**Bachelor's degrees**")
            for is_match, pname in bach_progs[:20]:
                prefix = "★ " if is_match else "· "
                st.markdown(f"&nbsp;&nbsp;{prefix}{pname}", unsafe_allow_html=True)
        if major_prefixes:
            st.caption("★ = matches your selected major")
    else:
        st.caption("No program data available in the College Scorecard for this school.")

    # Website
    website = row.get("website")
    if pd.notna(website) and website:
        st.link_button("Visit school website ↗", url=str(website))


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Must-haves")
    st.caption("Schools that fail any of these are removed.")

    max_budget = st.slider(
        "Max the family can pay per year", 5_000, 80_000, 25_000, step=500, format="$%d",
    )
    school_types = st.multiselect(
        "What type of school?", ["2-year", "4-year"], default=["2-year", "4-year"],
    )
    states      = st.multiselect("Where? (leave empty for anywhere)", ALL_STATES, default=[])
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
            "Stretch budget for athletes (scholarships expected)", 1.0, 2.0, 1.5, step=0.1,
            format="%.1f",
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
            FEATURE_LABELS[k], options=SLIDER_OPTIONS, key=f"w_{k}", help=FEATURE_HELP[k],
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
            .configure_axis(grid=False).configure_view(strokeWidth=0)
        )
        st.altair_chart(chart, use_container_width=True)

# ── Build client dict ──────────────────────────────────────────────────────────
client = {
    "name":                      "Streamlit session",
    "require_f1":                require_f1,
    "max_budget":                max_budget,
    "budget_flex":               budget_flex,
    "school_types":              school_types if school_types else ["2-year", "4-year"],
    "states":                    states if states else None,
    "city_groups":               city_groups if city_groups else None,
    "sport":                     sport_choice,
    "gender":                    gender,
    "needs_athletic_scholarship":needs_scholarship,
    "min_grad_rate_4yr":         min_grad_4yr / 100,
    "min_grad_rate_2yr":         min_grad_2yr / 100,
    "majors":                    MAJOR_OPTIONS[major_label],
    "strict_major":              strict_major,
    "weights":                   weights,
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

# ── Result cards — top 6 ──────────────────────────────────────────────────────
st.subheader("Top matches")
top6      = results.head(6).reset_index(drop=True)
card_cols = st.columns(3)

for i, row in top6.iterrows():
    with card_cols[i % 3]:
        with st.container(border=True):
            rank = i + 1
            st.markdown(f"**#{rank} · {row['name']}**")
            st.caption(f"{row['city']}, {row['state']}  ·  {row['school_type']}  ·  {row['association']}")

            cost = row["cost_international"]
            st.markdown(f"### {'$' + f'{cost:,.0f}' if pd.notna(cost) else '—'}")
            st.caption("per year · sticker price before scholarships")

            score = float(row["match_score"])
            st.progress(score / 100, text=f"Match score: {score:.1f} / 100")

            badges = [("F-1 certified", "green")]
            if row.get("athletic_aid_tier") in AID_TIERS:
                badges.append(("Athletic aid", "blue"))
            if row.get("offers_entrepreneurship"):
                badges.append(("Entrepreneurship", "orange"))
            if row.get("school_type") == "2-year" and row.get("has_transfer_track"):
                badges.append(("Transfer track", "violet"))
            st.markdown(" ".join(f":{c}-badge[{l}]" for l, c in badges))

            w1, w2 = split_reasons(row["top_reasons"])
            st.caption(f"Why: {' · '.join(filter(None, [w1, w2]))}")

            if st.button("Details", key=f"det_{rank}", use_container_width=True):
                show_detail(row, gender, client.get("majors"))

# ── Compare ────────────────────────────────────────────────────────────────────
st.subheader("Compare schools")
compare_names = st.multiselect(
    "Select up to 3 schools to compare side by side",
    options=results["name"].tolist(),
    max_selections=3,
)
if len(compare_names) >= 2:
    sel = results[results["name"].isin(compare_names)]
    table = {}
    for _, r in sel.iterrows():
        c_w1, c_w2 = split_reasons(r["top_reasons"])
        cost   = r["cost_international"]
        grad   = r["grad_rate"]
        pct_i  = r["pct_international"]
        a_shr  = r["athlete_share"]
        table[r["name"]] = {
            "Cost/yr":          f"${cost:,.0f}" if pd.notna(cost) else "—",
            "Grad rate":        f"{grad:.0%}"   if pd.notna(grad) else "—",
            "% International":  f"{pct_i:.0%}"  if pd.notna(pct_i) else "—",
            "Athlete share":    f"{a_shr:.0%}"  if pd.notna(a_shr) else "—",
            "Association":      r.get("association") or "—",
            "Aid tier":         r.get("athletic_aid_tier") or "—",
            "Entrepreneurship": "Yes" if r["offers_entrepreneurship"] else "No",
            "Score":            f"{r['match_score']:.1f}",
            "Why #1":           c_w1,
            "Why #2":           c_w2,
        }
    st.dataframe(pd.DataFrame(table), use_container_width=True)

# ── Full table in expander ─────────────────────────────────────────────────────
with st.expander("See all matches as a table"):
    display  = results[SHOW_COLS].copy()
    reasons  = display["top_reasons"].str.split(", ", n=1, expand=True)
    display["why_1"] = reasons[0].map(
        lambda x: FEATURE_LABELS.get(str(x).strip(), str(x).strip()) if pd.notna(x) else ""
    )
    display["why_2"] = (
        reasons[1] if 1 in reasons.columns else pd.Series("", index=display.index)
    ).map(lambda x: FEATURE_LABELS.get(str(x).strip(), str(x).strip()) if pd.notna(x) else "")
    display = display.drop(columns=["top_reasons"])

    display["cost_international"] = display["cost_international"].apply(
        lambda x: f"${x:,.0f}" if pd.notna(x) else "—")
    display["grad_rate"]          = display["grad_rate"].apply(
        lambda x: f"{x:.0%}" if pd.notna(x) else "—")
    display["pct_international"]  = display["pct_international"].apply(
        lambda x: f"{x:.0%}" if pd.notna(x) else "—")
    display["athlete_share"]      = display["athlete_share"].apply(
        lambda x: f"{x:.0%}" if pd.notna(x) else "—")
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

# ── Funnel ─────────────────────────────────────────────────────────────────────
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
map_df["color"]    = map_df["is_top6"].apply(lambda t: PRIMARY_RGB + [230] if t else [150, 150, 150, 160])
map_df["radius"]   = map_df["is_top6"].apply(lambda t: 55_000 if t else 38_000)
map_df["cost_fmt"] = map_df["cost_international"].apply(
    lambda x: f"${x:,.0f}" if pd.notna(x) else "—")

layer = pdk.Layer(
    "ScatterplotLayer", data=map_df,
    get_position="[lon, lat]", get_fill_color="color", get_radius="radius", pickable=True,
)
view = pdk.ViewState(latitude=38.5, longitude=-96.5, zoom=3, pitch=0)
tooltip = {
    "html": "<b>{name}</b><br/>{city}, {state}<br/>Cost: {cost_fmt}/yr<br/>Score: {match_score}",
    "style": {"backgroundColor": "white", "color": "#1A1A1A",
               "padding": "8px", "borderRadius": "4px", "fontSize": "13px"},
}
st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view, tooltip=tooltip))
st.caption("Top 6 in green · remaining matches in gray · hover for details.")
