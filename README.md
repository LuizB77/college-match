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

## Known limitations

- Costs are sticker prices before scholarships; no public data on what international students actually pay.
- 2-year grad rates understate success — early transfers count as non-completers.
- Athletic aid is reported per gender, not per sport.
- "Sport culture" is proxied by total athletics spending, not fame directly.
- Match scores are percentiles relative to each client's filtered pool, not absolute quality.
- SEVP list is extracted from a PDF: ~0.2% of rows are unrecoverable (NJ/VT/ME prefix collisions); ~1.5% of schools are flagged as likely linkage misses (aliases, small institutions); manual alias table in `notebooks/05_sevp_link.ipynb`.
- Online-only units are excluded from F-1 eligibility.
- EADA multi-division schools ("Other") are remapped by keyword; ~5 multi-division NCAA schools remain grouped as "Other small-college".
