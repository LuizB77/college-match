"""
College Match — Streamlit demo.
Sidebar inputs → src/matcher.py → metrics, cards, detail dialog, compare, map, full table.
"""

import os
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
PRIMARY_COLOR     = "#0B6E4F"
PRIMARY_RGB       = [11, 110, 79]
MAX_BUDGET_SLIDER = 95_000   # at this value the budget filter is disabled ("No limit")

DATA_PATH = Path(__file__).parent / "data" / "processed" / "schools_with_majors.csv"
CIP_PATH  = Path(__file__).parent / "data" / "processed" / "cip_names.csv"
AID_PATH  = Path(__file__).parent / "data" / "manual" / "intl_aid.csv"

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

# IPEDS RELAFFIL code → human-readable label (College Scorecard data dictionary).
RELAFFIL_MAP: dict[int, str] = {
    22: "American Evangelical Lutheran Church",
    24: "African Methodist Episcopal Zion",
    27: "Assemblies of God Church",
    28: "Brethren Church",
    30: "Roman Catholic",
    33: "Wisconsin Evangelical Lutheran Synod",
    34: "Christ and Missionary Alliance Church",
    35: "Christian Reformed Church",
    36: "Evangelical Congregational Church",
    37: "Evangelical Covenant Church of America",
    38: "Evangelical Free Church of America",
    39: "Evangelical Lutheran Church",
    40: "International United Pentecostal Church",
    41: "Free Will Baptist Church",
    42: "Interdenominational",
    43: "Mennonite Brethren Church",
    44: "Moravian Church",
    45: "North American Baptist",
    47: "Pentecostal Holiness Church",
    48: "Christian Churches and Churches of Christ",
    49: "Reformed Church in America",
    50: "Episcopal Church, Reformed",
    51: "African Methodist Episcopal",
    52: "American Baptist",
    53: "American Lutheran",
    54: "Baptist",
    55: "Christian Methodist Episcopal",
    57: "Church of God",
    58: "Church of Brethren",
    59: "Church of the Nazarene",
    60: "Cumberland Presbyterian",
    61: "Christian Church (Disciples of Christ)",
    64: "Free Methodist",
    65: "Friends (Quaker)",
    66: "Presbyterian Church (USA)",
    67: "Lutheran Church in America",
    68: "Lutheran Church — Missouri Synod",
    69: "Mennonite Church",
    71: "United Methodist",
    73: "Protestant Episcopal",
    74: "Churches of Christ",
    75: "Southern Baptist",
    76: "United Church of Christ",
    77: "Protestant, not specified",
    78: "Multiple Protestant Denominations",
    79: "Other Protestant",
    80: "Jewish",
    81: "Reformed Presbyterian Church",
    84: "United Brethren Church",
    87: "Missionary Church",
    88: "Undenominational",
    89: "Wesleyan",
    91: "Greek Orthodox",
    92: "Russian Orthodox",
    93: "Unitarian Universalist",
    94: "Latter Day Saints (Mormon)",
    95: "Seventh Day Adventists",
    97: "Presbyterian Church in America",
    99: "Other religious",
    100: "Original Free Will Baptist",
    101: "Ecumenical Christian",
    102: "Evangelical Christian",
    103: "Presbyterian",
    105: "General Baptist",
    106: "Muslim",
    107: "Plymouth Brethren",
    108: "Non-Denominational",
    110: "Orthodox Christian",
}

_NONE_CODES = {-1, -2}


def affil_label(raw) -> str:
    """Return display label for a raw RELAFFIL value; empty string when none/missing."""
    try:
        if pd.isna(raw):
            return ""
        code = int(raw)
        if code in _NONE_CODES:
            return ""
        return RELAFFIL_MAP.get(code, f"Code {code}")
    except (TypeError, ValueError):
        return ""


# Default sidebar values — used both for first load and "Clear all filters".
DEFAULTS = {
    "sb_budget":       MAX_BUDGET_SLIDER,
    "sb_school_types": ["2-year", "4-year"],
    "sb_states":       [],
    "sb_city_groups":  [],
    "sb_plays_sport":  False,
    "sb_sport":        "Soccer",
    "sb_gender":       "men",
    "sb_scholarship":  False,
    "sb_major":        "None",
    "sb_affil":        "Any",
    "sb_budget_flex":  1.5,
    "sb_grad_4yr":     0,
    "sb_grad_2yr":     0,
    "sb_strict_major": False,
    "sb_require_f1":   False,
    "preset_select":   "Balanced",
}


# ── Data ───────────────────────────────────────────────────────────────────────
@st.cache_data
def get_data(mtime: float):  # mtime makes cache stale whenever the CSV is modified
    return load_data(DATA_PATH)


@st.cache_data
def get_cip_lookup() -> dict:
    """cip4 code → program name."""
    df = pd.read_csv(CIP_PATH, dtype=str)
    return dict(zip(df["cip4"], df["name"]))


@st.cache_data
def get_intl_aid() -> pd.DataFrame:
    """Load manually curated international aid data. Returns empty df if file is missing."""
    if not AID_PATH.exists():
        return pd.DataFrame(columns=["unitid", "offers_intl_aid", "meets_full_need_intl",
                                      "need_blind_intl", "pct_intl_aided", "avg_intl_award",
                                      "cds_year", "source_url"])
    aid = pd.read_csv(AID_PATH, comment="#")
    aid = aid[pd.to_numeric(aid["unitid"], errors="coerce").notna()].copy()
    aid["unitid"] = aid["unitid"].astype(int)
    aid["avg_intl_award"] = pd.to_numeric(aid["avg_intl_award"], errors="coerce")
    for bool_col in ["offers_intl_aid", "meets_full_need_intl", "need_blind_intl"]:
        if bool_col in aid.columns:
            aid[bool_col] = aid[bool_col].map(
                lambda v: True if str(v).strip().upper() == "TRUE" else
                          (False if str(v).strip().upper() == "FALSE" else None)
            )
    return aid


df         = get_data(os.path.getmtime(DATA_PATH))
cip_lookup = get_cip_lookup()
intl_aid   = get_intl_aid()

if not intl_aid.empty:
    df = df.merge(intl_aid, left_on="unit_id", right_on="unitid", how="left")
    df["est_net_cost"] = df["cost_international"] - df["avg_intl_award"]
else:
    df["est_net_cost"]         = float("nan")
    df["offers_intl_aid"]      = None
    df["meets_full_need_intl"] = None
    df["need_blind_intl"]      = None
    df["pct_intl_aided"]       = float("nan")
    df["avg_intl_award"]       = float("nan")
    df["cds_year"]             = None
    df["source_url"]           = None

ALL_SPORTS = sorted({
    s.strip()
    for col in ["mens_sports", "womens_sports"]
    for cell in df[col].dropna()
    for s in cell.split(";")
    if s.strip()
})
ALL_STATES = sorted(df["state"].dropna().unique().tolist())

# ── Session state ──────────────────────────────────────────────────────────────
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

for k in WEIGHT_KEYS:
    if f"w_{k}" not in st.session_state:
        st.session_state[f"w_{k}"] = SLIDER_OPTIONS[PRESETS["Balanced"][k]]


def _apply_preset():
    name = st.session_state["preset_select"]
    if name in PRESETS:
        for k, v in PRESETS[name].items():
            st.session_state[f"w_{k}"] = SLIDER_OPTIONS[v]


def _clear_filters():
    for k, v in DEFAULTS.items():
        st.session_state[k] = v
    for k, v in PRESETS["Balanced"].items():
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
    return sorted(out, key=lambda x: (not x[0], x[1]))


# ── School detail dialog ───────────────────────────────────────────────────────
@st.dialog("School details")
def show_detail(row: pd.Series, selected_gender: str, major_prefixes):
    name = row["name"]
    st.markdown(f"## {name}")

    city_size = row.get("city_size") or "—"
    enrollment = row.get("undergrads")
    enrollment_str = f"{int(enrollment):,}" if pd.notna(enrollment) else "—"
    row_affil_label = affil_label(row.get("religious_affil"))
    affil_str = f"  ·  {row_affil_label}" if row_affil_label else ""
    f1_str = "F-1 certified" if row.get("sevp_certified") else "Not F-1 certified"
    st.caption(
        f"📍 {row['city']}, {row['state']}  ·  {row['school_type']}  ·  "
        f"{row['association']}  ·  {city_size}{affil_str}  ·  {f1_str}\n"
        f"👥 {enrollment_str} undergraduates"
    )

    # Cost
    st.markdown("### Cost")
    cost_intl = row.get("cost_international")
    cost_oos  = row.get("tuition_out_of_state")
    est_net   = row.get("est_net_cost")
    col1, col2 = st.columns(2)
    col1.metric("International estimate / yr", f"${cost_intl:,.0f}" if pd.notna(cost_intl) else "—")
    col2.metric("Out-of-state tuition",        f"${cost_oos:,.0f}"  if pd.notna(cost_oos)  else "—")
    st.caption("Sticker prices before scholarships or financial aid.")

    # International Aid
    if row.get("offers_intl_aid") is not None:
        st.markdown("### International Financial Aid")
        avg_award = row.get("avg_intl_award")
        pct_aided = row.get("pct_intl_aided")
        cds_yr    = row.get("cds_year")
        src_url   = row.get("source_url")
        a1, a2, a3 = st.columns(3)
        a1.metric("Offers need-based intl aid", "Yes" if row.get("offers_intl_aid") else "No")
        a2.metric("Avg award / yr",  f"${avg_award:,.0f}" if pd.notna(avg_award) else "Not reported")
        a3.metric("Est. net cost / yr", f"${est_net:,.0f}" if pd.notna(est_net) else "—")
        flags_aid = []
        if row.get("meets_full_need_intl"):
            flags_aid.append("Meets 100% of demonstrated need")
        if row.get("need_blind_intl"):
            flags_aid.append("Need-blind admission")
        if pct_aided and pd.notna(pct_aided):
            flags_aid.append(f"{pct_aided:.0%} of international students receive aid")
        else:
            flags_aid.append("Aid share unknown")
        if flags_aid:
            st.markdown("  ·  ".join(flags_aid))
        caption_parts = []
        if cds_yr and str(cds_yr) not in ("None", "nan"):
            caption_parts.append(f"CDS year: {cds_yr}")
        st.caption(
            "Source: Common Data Set (Section H6). "
            + ("  ·  ".join(caption_parts) if caption_parts else "")
        )
        if src_url and str(src_url) not in ("None", "nan", "TODO"):
            st.link_button("View Common Data Set ↗", url=str(src_url))

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
    else:
        st.caption("No athletics reported for this school.")

    # Academics
    st.markdown("### Academics")
    grad = row.get("grad_rate")
    grad_str = f"{grad:.0%}" if pd.notna(grad) else "—"
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
    st.button("Clear all filters", use_container_width=True, on_click=_clear_filters)

    st.header("Must-haves")
    st.caption("Schools that fail any of these are removed.")

    budget_val = st.slider(
        "Max the family can pay per year",
        5_000, MAX_BUDGET_SLIDER, step=500, format="$%d",
        key="sb_budget",
    )
    if budget_val >= MAX_BUDGET_SLIDER:
        st.caption("No limit — schools with unknown costs are included.")
        max_budget = None
    else:
        st.caption(f"Budget: ${budget_val:,}/yr")
        max_budget = budget_val

    school_types = st.multiselect(
        "What type of school?", ["2-year", "4-year"],
        key="sb_school_types",
    )
    states      = st.multiselect("Where? (leave empty for anywhere)", ALL_STATES, key="sb_states")
    city_groups = st.multiselect(
        "City size? (leave empty for any)", ["City", "Suburb", "Town", "Rural"],
        key="sb_city_groups",
    )

    plays_sport = st.toggle("Does the student play a sport?", key="sb_plays_sport")
    if plays_sport:
        sport_choice = st.selectbox(
            "Sport", ALL_SPORTS,
            index=ALL_SPORTS.index(st.session_state["sb_sport"])
                  if st.session_state["sb_sport"] in ALL_SPORTS else 0,
            key="sb_sport",
        )
        gender            = st.radio("Gender", ["men", "women"], key="sb_gender")
        needs_scholarship = st.checkbox("Needs an athletic scholarship", key="sb_scholarship")
    else:
        sport_choice      = None
        gender            = st.session_state.get("sb_gender", "men")
        needs_scholarship = False

    major_label = st.selectbox("Intended major", list(MAJOR_OPTIONS.keys()), key="sb_major")

    affil_filter = st.selectbox(
        "Religious affiliation",
        ["Any", "Catholic", "Any religious", "Non-religious"],
        key="sb_affil",
        help="'Any' shows all schools. 'Catholic' = Roman Catholic only. "
             "'Any religious' = schools with a stated affiliation. "
             "'Non-religious' = no stated affiliation.",
    )
    _affil_map = {
        "Any":           None,
        "Catholic":      "catholic",
        "Any religious": "any_religious",
        "Non-religious": "non_religious",
    }
    religion_key = _affil_map[affil_filter]

    with st.expander("Advanced"):
        budget_flex = st.slider(
            "Stretch budget for athletes (scholarships expected)", 1.0, 2.0, step=0.1,
            format="%.1f",
            key="sb_budget_flex",
            help="1.5 = consider schools up to 50% over budget (the athlete may receive aid that closes the gap).",
        )
        min_grad_4yr = st.slider(
            "Min grad rate — 4-year", 0, 100, step=5, format="%d%%",
            key="sb_grad_4yr",
            help="4-year schools below this are excluded. Schools with unknown rates are kept.",
        )
        min_grad_2yr  = st.slider(
            "Min grad rate — 2-year", 0, 100, step=5, format="%d%%",
            key="sb_grad_2yr",
        )
        strict_major  = st.checkbox(
            "Require exact major (don't count general transfer tracks)",
            key="sb_strict_major",
            help="When checked, 2-year schools must offer the major as an associate degree; "
                 "a Liberal Arts transfer track no longer qualifies.",
        )
        require_f1 = st.checkbox("Require F-1 eligibility (SEVP certified)", key="sb_require_f1")

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
    "max_budget":                max_budget,           # None = no limit
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
    "religion":                  religion_key,
    "weights":                   weights,
}

# ── Swap cost → est_net_cost where intl aid data is present ───────────────────
has_aid_estimate = df["est_net_cost"].notna()
if has_aid_estimate.any():
    df_for_match = df.copy()
    df_for_match.loc[has_aid_estimate, "cost_international"] = df_for_match.loc[
        has_aid_estimate, "est_net_cost"
    ]
else:
    df_for_match = df

# ── Run matcher ────────────────────────────────────────────────────────────────
results, funnel = match(df_for_match, client, top_n=25)

# Restore original sticker cost for display; keep est_net_cost alongside.
if has_aid_estimate.any() and not results.empty:
    results = results.copy()
    results["cost_international"] = results.index.map(df["cost_international"])
    results["est_net_cost"]       = results.index.map(df["est_net_cost"])

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_find, tab_how = st.tabs(["Find schools", "How it works"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Find schools
# ══════════════════════════════════════════════════════════════════════════════
with tab_find:

    st.title("College Match")
    st.markdown(
        "Find U.S. colleges and junior colleges that fit an international student's "
        "budget, sport, major, and visa needs."
    )

    # "Schools that fit" = last funnel step (all schools passing every hard filter)
    schools_that_fit = funnel[-1][1] if funnel else 0

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Schools that fit", schools_that_fit)
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
            st.metric("Offer athletic scholarships", int(aid_count))
        else:
            st.metric("Offer athletic scholarships", "—")
    with m4:
        if not results.empty:
            f1_count = int(results["sevp_certified"].sum())
            st.metric("F-1 certified", f1_count)
        else:
            st.metric("F-1 certified", "—")

    # Empty state
    if results.empty:
        st.info("No schools pass the current filters. Try relaxing budget, grad rate, or sport filters.")
    else:
        # Result cards — top 6
        st.subheader("Top matches")
        top6      = results.head(6).reset_index(drop=True)
        card_cols = st.columns(3)

        for i, row in top6.iterrows():
            with card_cols[i % 3]:
                with st.container(border=True):
                    rank = i + 1
                    st.markdown(f"**#{rank} · {row['name']}**")
                    st.caption(
                        f"{row['city']}, {row['state']}  ·  {row['school_type']}  ·  "
                        f"{row['association'] or '—'}"
                    )

                    cost = row["cost_international"]
                    est  = row.get("est_net_cost")
                    has_est = pd.notna(est)
                    display_cost = est if has_est else cost
                    st.markdown(f"### {'$' + f'{display_cost:,.0f}' if pd.notna(display_cost) else '—'}")
                    if has_est:
                        pct_aided = row.get("pct_intl_aided")
                        aided_note = (
                            f" · {pct_aided:.0%} of internationals receive aid"
                            if pd.notna(pct_aided)
                            else " · aid share unknown"
                        )
                        st.caption(f"per year · Estimated cost if aided{aided_note}")
                    else:
                        st.caption("per year · sticker price before scholarships")

                    score = float(row.get("match_score") or 50.0)
                    score = max(0.0, min(100.0, score)) if score == score else 50.0  # clamp; guard NaN
                    st.progress(score / 100, text=f"Match score: {score:.1f} / 100")

                    badges = []
                    if row.get("sevp_certified"):
                        badges.append(("F-1 certified", "green"))
                    else:
                        badges.append(("Not F-1 certified", "red"))
                    if row.get("offers_intl_aid") is True:
                        badges.append(("Intl aid", "blue"))
                    elif row.get("athletic_aid_tier") in AID_TIERS:
                        badges.append(("Athletic aid", "blue"))
                    if row.get("offers_entrepreneurship"):
                        badges.append(("Entrepreneurship", "orange"))
                    if row.get("school_type") == "2-year" and row.get("has_transfer_track"):
                        badges.append(("Transfer track", "violet"))
                    row_affil = affil_label(row.get("religious_affil"))
                    if row_affil:
                        badges.append((row_affil, "gray"))
                    st.markdown(" ".join(f":{c}-badge[{l}]" for l, c in badges))

                    w1, w2 = split_reasons(row["top_reasons"])
                    st.caption(f"Why: {' · '.join(filter(None, [w1, w2]))}")

                    if st.button("Details", key=f"det_{rank}", use_container_width=True):
                        show_detail(row, gender, client.get("majors"))

        # Compare
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
                cost      = r["cost_international"]
                grad      = r["grad_rate"]
                pct_i     = r["pct_international"]
                a_shr     = r["athlete_share"]
                aid_tier_val = r.get("athletic_aid_tier") or "No athletics"
                aff = affil_label(r.get("religious_affil"))
                table[r["name"]] = {
                    "Cost/yr":          f"${cost:,.0f}" if pd.notna(cost) else "—",
                    "Grad rate":        f"{grad:.0%}"   if pd.notna(grad) else "—",
                    "% International":  f"{pct_i:.0%}"  if pd.notna(pct_i) else "—",
                    "Athlete share":    f"{a_shr:.0%}"  if pd.notna(a_shr) else "—",
                    "Association":      r.get("association") or "—",
                    "Aid tier":         aid_tier_val,
                    "Affiliation":      aff or "—",
                    "F-1 certified":    "Yes" if r.get("sevp_certified") else "No",
                    "Entrepreneurship": "Yes" if r["offers_entrepreneurship"] else "No",
                    "Score":            f"{r['match_score']:.1f}",
                    "Why #1":           c_w1,
                    "Why #2":           c_w2,
                }
            st.dataframe(pd.DataFrame(table), use_container_width=True)

        # Full table
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
                lambda x: f"${x:,.0f}" if pd.notna(x) else "—")
            display["grad_rate"]         = display["grad_rate"].apply(
                lambda x: f"{x:.0%}" if pd.notna(x) else "—")
            display["pct_international"] = display["pct_international"].apply(
                lambda x: f"{x:.0%}" if pd.notna(x) else "—")
            display["athlete_share"]     = display["athlete_share"].apply(
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

        # Funnel
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

        # Map
        st.subheader("Where they are")
        map_df = results[
            ["name", "city", "state", "lat", "lon", "cost_international", "match_score"]
        ].dropna(subset=["lat", "lon"]).reset_index(drop=True).copy()
        map_df["rank"]     = map_df.index + 1
        map_df["is_top6"]  = map_df["rank"] <= 6
        map_df["color"]    = map_df["is_top6"].apply(
            lambda t: PRIMARY_RGB + [230] if t else [150, 150, 150, 160])
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

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — How it works
# ══════════════════════════════════════════════════════════════════════════════
with tab_how:

    # ── How matching works ─────────────────────────────────────────────────────
    st.header("How matching works")
    st.markdown(
        """
**1 · Must-haves remove schools that can't work**

First, any school that fails a hard requirement is removed entirely. Wrong budget,
missing sport, no F-1 certification, grad rate too low — fail one, and the school is out.
This step ensures every result is actually a realistic option, not just a "close enough" one.

**2 · Preferences decide the order of what's left**

The remaining schools are scored by what you said matters most. Each preference gets a
weight (0 = ignore, "Top priority" = 5). Schools score higher when they excel at the
things you care about most — cheap, athlete-friendly, strong programs, and so on.
A school that's great on your top two priorities will usually beat one that's mediocre on all five.

**3 · Every result tells you why it ranked there**

Each card shows the top two reasons it scored well ("Low cost · Athlete-friendly campus").
Use that to check whether the tool's reasoning matches your gut. If a school is ranked #1
mostly because of a preference you don't actually care about, lower that weight and rerun.
        """
    )

    # ── What each preference means ────────────────────────────────────────────
    st.header("What each preference means")
    for k in WEIGHT_KEYS:
        with st.expander(FEATURE_LABELS[k]):
            st.markdown(FEATURE_HELP[k])

    # ── Where the data comes from ─────────────────────────────────────────────
    st.header("Where the data comes from")
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**College Scorecard**")
        st.markdown(
            "Costs, enrollment, graduation rates, and program offerings. "
            "Published by the U.S. Department of Education. "
            "Data year: 2022–23 academic year."
        )
        st.link_button("collegescorecard.ed.gov/data ↗", "https://collegescorecard.ed.gov/data")

        st.markdown("**SEVP Certified School List**")
        st.markdown(
            "Which schools are authorized to enroll F-1 (student visa) students. "
            "Maintained by U.S. Immigration and Customs Enforcement. "
            "List extracted: September 2026."
        )
        st.link_button("studyinthestates.dhs.gov ↗", "https://studyinthestates.dhs.gov/school-search")

    with col_b:
        st.markdown("**EADA — Equity in Athletics Data Analysis**")
        st.markdown(
            "Sport rosters, athletic aid, division, and athletics spending. "
            "Submitted annually by schools to the U.S. Department of Education. "
            "Survey year: 2024–25."
        )
        st.link_button("ope.ed.gov/athletics ↗", "https://ope.ed.gov/athletics")

        st.markdown("**Common Data Set — Section H6**")
        st.markdown(
            "Per-school international student financial aid: whether the school offers "
            "need-based aid to internationals, average award amounts, and admission policy. "
            "Collected manually from each school's published CDS. "
            "Coverage is limited — only schools in our database with a filed CDS are included."
        )
        st.link_button("commondataset.org ↗", "https://www.commondataset.org")

    # ── Limitations ───────────────────────────────────────────────────────────
    st.header("What this tool can't tell you")
    st.markdown(
        """
- **You'll probably pay less than the listed cost.** The prices shown are official sticker prices
  before any scholarship, grant, or athletic aid is applied. Student-athletes often pay significantly
  less — sometimes nothing at all.

- **2-year graduation rates undercount success.** A student who transfers to a 4-year university
  after one year counts as a "non-completer" in the data, even if they go on to graduate with a
  bachelor's degree. Treat 2-year rates as a rough floor, not a ceiling.

- **Athletic scholarship figures are team averages, not per-sport.** Schools report total aid
  divided across all athletes of that gender. One sport with heavy investment can raise the average
  for every sport at that school.

- **"Big-time sports" is measured by spending, not fame.** A school with high athletics spending
  is investing in its programs, but that doesn't always mean national TV exposure or famous coaches.

- **Scores are relative to your search, not absolute grades.** A score of 85 means this school
  ranked very well among the options that passed your filters. The same school might score 60
  in a different search with different filters or preferences.

- **F-1 eligibility data has a lag.** The SEVP list was last downloaded in September 2026.
  A small number of schools may have been certified or decertified since then. Always confirm
  directly with the school's international admissions office.

- **Schools with no program data are still shown.** If a school has no entries in the College
  Scorecard's program data, it passes the major filter automatically (we don't know it doesn't
  offer your major — we just don't have data either way).

- **International aid figures are manually collected and may be outdated.** Aid data comes from
  each school's Common Data Set (Section H6), entered by hand. Only a small number of schools
  have been filed so far. Figures are per-school averages across all international aided students
  — your actual award depends on your family's financial situation and the school's specific policy.
  Always confirm with the school's financial aid office before making decisions.
        """
    )

    # ── About ─────────────────────────────────────────────────────────────────
    st.divider()
    st.caption(
        "Built by Luiz Breda · "
        "[College Match on GitHub](https://github.com/LuizB77/college-match)"
    )
