# College Match: data-driven college matching for international student-athletes

This project matches Brazilian and other international student-athletes to US colleges and junior colleges (JUCOs) using two public datasets: the US Department of Education's College Scorecard (cost, enrollment, graduation rates, location) and the Equity in Athletics Data Analysis (EADA) dataset (sport offerings, athletic divisions, scholarship availability, recruiting spend). A candidate school must pass a set of hard filters — school type, cost ceiling, sport availability, scholarship tier — before being ranked by a weighted score that combines cost, graduation rate, sport culture, athlete share of enrollment, and international community size. Weights are set per client based on their priorities.

## Data sources

- **College Scorecard** — "Most Recent Institution-Level Data" CSV from [collegescorecard.ed.gov/data](https://collegescorecard.ed.gov/data). Download and place at `data/raw/Most-Recent-Cohorts-Institution.csv`.
- **EADA** — "Data for academic year 2024-25" from [ope.ed.gov/athletics](https://ope.ed.gov/athletics). Unzip and place `instLevel.xlsx` and `schools.xlsx` at `data/raw/eada/`.

## Notebooks

| Notebook | What it does |
|---|---|
| `01_load_and_check` | Loads Scorecard, selects columns, applies operating/type/control filters, builds `schools_clean.csv` |
| `02_explore` | Exploratory charts: international student cost by school type, distribution of international share, top schools by % international |
| `03_athletics` | Joins EADA data, builds athletic aid tier, association group, sport culture percentile, saves `schools_with_athletics.csv` |
| `04_match` | Client intake dictionary → hard filters → weighted score → ranked shortlist |
| `05_sevp_link` | Links schools to the SEVP certified-institution list; flags F-1 eligibility; saves `schools_with_sevp.csv` |

## Testing

### Unit + integration tests (local)

```bash
.venv/bin/python -m pytest tests/ -v
```

Run this before every push. The suite covers matcher correctness, explain_exclusion consistency, program_strength, selectivity tiers, hidden gems, Ivy League flags, and Streamlit AppTest integration.

### Deploy smoke-test (must run after every push)

```bash
bash scripts/check_deploy.sh
```

This script clones `origin/main` into a temp directory, creates a **fresh venv** from `requirements.txt` only (no local packages), installs `pytest`, and runs the full test suite. It catches any "works locally, fails in prod" regressions — missing exports, modules that need to be added to `requirements.txt`, files that were not committed, or anything that depends on local state.

**Always run `check_deploy.sh` after pushing** — it is the closest approximation to what the live app actually sees.

### Test descriptions

| Test | What it checks |
|---|---|
| `test_matcher_top15` | `match()` reproduces the notebook-04 top-15 baseline exactly |
| `test_match_returns_all_passing` | `match()` with no `top_n` returns all schools that pass filters |
| `test_f1_metric_equals_sevp_count` | F-1 metric equals total SEVP-certified schools in the dataset |
| `test_matcher_zero_weights_no_nan` | All-zero weights produce no NaN scores |
| `test_matcher_religion_catholic` | Catholic filter appears in funnel and reduces count |
| `test_matcher_max_budget_none_includes_unknown_cost` | No-budget mode skips the cost funnel step |
| `test_explain_exclusion_*` | `explain_exclusion()` is consistent with `match()` for 200-school sample |
| `test_program_earnings_file` | `program_earnings.csv` has correct columns and positive earnings |
| `test_selectivity_tier_thresholds` | Reach / Target / Likely / Unknown thresholds are correct |
| `test_ivy_league_unit_ids` | All 8 Ivy League schools identified by unit_id |
| `test_program_strength_in_match` | `program_strength` weight produces valid scores |
| `test_hidden_gems_only` | Hidden gems filter removes Reach schools and reduces count |
| `test_defaults_load` | App loads with no exception; "Schools that fit" = 3147 |
| `test_athlete_profile` | Athlete profile via sidebar session state; no exception |
| `test_catholic_filter` | Catholic filter via AppTest; count < 3147 |
| `test_zero_weights_no_crash` | All sliders at "Don't care"; no `st.progress` crash |
| `test_clear_all` | Restrictive filters → Clear → count returns to 3147 |

## Known limitations

- Costs are sticker prices before scholarships; no public data on what international students actually pay.
- 2-year grad rates understate success — early transfers count as non-completers.
- Athletic aid is reported per gender, not per sport.
- "Sport culture" is proxied by total athletics spending, not fame directly.
- Match scores are percentiles relative to each client's filtered pool, not absolute quality.
- SEVP list is extracted from a PDF: ~0.2% of rows are unrecoverable (NJ/VT/ME prefix collisions); ~1.5% of schools are flagged as likely linkage misses (aliases, small institutions); manual alias table in `notebooks/05_sevp_link.ipynb`.
- Online-only units are excluded from F-1 eligibility.
- EADA multi-division schools ("Other") are remapped by keyword; ~5 multi-division NCAA schools remain grouped as "Other small-college".
