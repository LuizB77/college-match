# Research protocol — data/manual/intl_aid.csv

## Purpose

`data/manual/intl_aid.csv` provides hand-collected international financial aid data
for schools in the app. Each row is one school (one row per `unitid`).

## Column definitions

| Column | Values | Notes |
|--------|--------|-------|
| `unitid` | integer | IPEDS unit_id |
| `offers_intl_aid` | `TRUE` / `FALSE` | Confirmed from official financial aid page. Blank = no data found. |
| `meets_full_need_intl` | `TRUE` / `FALSE` | School commits to meeting 100% of demonstrated need for internationals. Blank = not confirmed. |
| `need_blind_intl` | `TRUE` / `FALSE` | Admissions is need-blind for international applicants. Blank = not confirmed. |
| `pct_intl_aided` | 0–1 decimal | CDS H6 number aided ÷ CDS B2 nonresident degree-seeking undergrads. Blank if either CDS field is missing. |
| `avg_intl_award` | integer (USD/yr) | CDS H6 average institutional grant/scholarship for aided nonresidents. Blank if not reported. |
| `cds_year` | `YYYY-YY` | Academic year of the CDS document used (e.g. `2025-26`). |
| `source_url` | URL | Direct URL to the CDS PDF or CDS web page. |
| `intl_aid_page_url` | URL | Official financial aid page describing international aid policy. |
| `cds_total_cost` | integer (USD/yr) | CDS G1: tuition + required fees + food and housing (first-year, on-campus). Blank if G1 not published. |
| `quality` | `ok` / `flagged` | Set by `validate_intl_aid.py`. Do not edit manually. |

## Research steps

### Step 1 — Find the Common Data Set

1. Search the school's **institutional research** (IR) page for the most recent CDS.
   - Try: `site:<school.edu> "common data set"` or `<School Name> common data set 2025-26`
   - IR pages are often at `ir.<school.edu>`, `oira.<school.edu>`, or `ira.<school.edu>`.
2. Prefer the **most recent** CDS year (2025-26 if available; 2024-25 otherwise).
3. Record the **direct URL** to the PDF or web page as `source_url`.

### Step 2 — Extract H6 (nonresident scholarship/grant data)

In section **H6** of the CDS, find the row for **"Nonresident"** (or "Non-resident alien"):

| Field | CDS label |
|-------|-----------|
| Number aided | "Number of degree-seeking nonresident alien undergraduates who applied for and were awarded institutional non-need-based scholarship or grant aid" — **or** the H6 number awarded any institutional grant |
| Average award | "Average institutional grant/scholarship award" for nonresidents |

> **Note:** H6 may report "need-based" and "non-need-based" separately. Use the **total** number aided
> (or the higher of the two) and the corresponding average. If only one type is reported, use that.

### Step 3 — Extract B2 (enrollment denominator)

In section **B2**, find the row for **"Nonresident alien"** in the degree-seeking undergraduate column.
This is the denominator for `pct_intl_aided`.

```
pct_intl_aided = H6 number aided ÷ B2 nonresident degree-seeking undergrads
```

Round to 4 decimal places. If either number is missing, leave `pct_intl_aided` blank.

### Step 3a — Section G (CDS total cost)

In section **G1** of the CDS, find the "First-Year Undergraduates" column and record:

| Row | Field |
|-----|-------|
| Tuition (private institution) | tuition |
| Required Fees | fees |
| Food and housing (on-campus) | room+board |

```
cds_total_cost = tuition + required_fees + food_and_housing
```

Store as an integer in `cds_total_cost`. This is used as the denominator for `est_net_cost` and replaces the less-accurate IPEDS figure. If G1 is blank (institution hasn't published next-year costs yet), leave `cds_total_cost` blank.

> Note: The CDS G section reports the *upcoming* academic year's costs (e.g., CDS 2025-26 reports 2026-27 costs). This is intentional — the CDS is used by prospective students deciding where to apply.

### Step 3b — Section C (application fee) and D (transfer data)

For each school, also extract the following into `data/manual/cds_admissions.csv`:

| Column | CDS location | Notes |
|--------|-------------|-------|
| `app_fee` | C2 — "Application fee" | Integer USD; blank if waived/none |
| `app_fee_waiver` | C2 — "Can it be waived?" | `Yes` / `No` |
| `rd_deadline` | C1 — "Regular" row, "Deadline" column | Date string as printed (e.g. "Feb 1") |
| `transfer_applicants` | D — "Number of transfer applicants" | Integer |
| `transfer_admitted` | D — "Number admitted" | Integer |
| `transfer_enrolled` | D — "Number enrolled" | Integer |
| `cds_year` | From document header | e.g. `2025-26` |
| `source_url` | Same as `source_url` in intl_aid.csv | Direct PDF link |

The `unitid` column uses the same IPEDS unit_id as `intl_aid.csv`.

> **Skip** if the school's CDS PDF is section-only (e.g. only _h or _g sections cached).
> Leave numeric fields blank rather than zero when the section is absent.

### Step 4 — International aid policy page

Visit the school's official financial aid website and find the page describing international student aid.

Record:
- `intl_aid_page_url` — the page URL
- `offers_intl_aid` — `TRUE` if the page confirms any need-based grant/scholarship for internationals; `FALSE` if the page explicitly states no institutional aid for internationals
- `meets_full_need_intl` — `TRUE` if the school commits to meeting 100% of demonstrated need for internationals
- `need_blind_intl` — `TRUE` if admissions is explicitly need-blind for international applicants

Leave blank if the page doesn't address the question. **Never guess.**

## Rules

1. **Never guess.** If a field can't be confirmed from an official source, leave it blank.
2. Use only official `.edu` URLs. No third-party aggregators.
3. `cds_year` must match the source document — e.g., if the file is titled "2025-26 CDS" but H6 data
   is labeled "2024-2025 Final," record `2024-25`.
4. `avg_intl_award` is in USD per year (no dollar sign, no commas).
5. `pct_intl_aided` is a decimal between 0 and 1 (e.g., `0.7884` not `78.84`).
6. Do not add a row for a school already in the file — update the existing row instead.
7. Update `intl_aid_queue.csv` status after every school attempted:
   - `filled` — H6 numbers found and recorded
   - `policy_only` — policy flags set but no H6 numbers found in CDS
   - `not_found` — CDS not found or school has no international population
   - `pending` — not yet attempted

## Quality flags (set by validate_intl_aid.py)

A row is flagged (`quality = "flagged"`) if any of:
- `pct_intl_aided` is outside [0, 1]
- `avg_intl_award` > `cds_total_cost × 1.05` when `cds_total_cost` is present (award exceeds plausible total cost — likely data error); if `cds_total_cost` is absent, compares against IPEDS `cost_international` instead
- `cds_year` is older than 2022-23
- `pct_intl_aided` or `avg_intl_award` is present but `source_url` is missing

Flagged rows are excluded from the app. Fix the underlying data issue, then re-run the validator.

## Queue cap

Stop the research queue when **any** of the following is true:

1. **200 schools done**: the number of rows in `intl_aid_queue.csv` with `status = filled` or
   `status = policy_only` reaches 200.

2. **Batch quality drops**: a single batch's share of `not_found` results exceeds 60 % of
   the schools attempted in that batch (e.g., 13 out of 20 not found → 65 % → stop).

3. **Consecutive low fill rate**: two consecutive batches each have a filled rate below 30 %
   (filled ÷ attempted, where attempted = filled + policy_only + not_found for that batch).
   Pause the queue and report the fill rates for both batches before continuing.

**Rationale:** Beyond 200 filled/policy rows the marginal value per school decreases while
research effort stays constant. A >60 % not-found rate means the remaining queue is dominated
by schools whose CDS is not publicly accessible; continuing wastes time without improving
app coverage. Two consecutive under-30 % fill batches signal the queue has shifted to schools
that either don't publish H6 data or only offer merit aid — worth reassessing priority before
continuing.

**How to check before starting a batch:**
```python
import pandas as pd
q = pd.read_csv("data/manual/intl_aid_queue.csv")
done = q["status"].isin(["filled", "policy_only"]).sum()
print(f"{done} done — cap is 200")

# Check fill rate for the last two batches
attempted = q[q["attempted_date"].notna() & (q["status"] != "pending")]
attempted = attempted.sort_values("attempted_date")
for date, grp in attempted.groupby("attempted_date"):
    filled = (grp["status"] == "filled").sum()
    total = len(grp)
    print(f"{date}: {filled}/{total} filled ({filled/total:.0%})")
```

## Queue filtering

Before adding a school to the queue, verify it is not online-only. Schools with
`online_only = 1` in `data/processed/schools_clean.csv` do not have a residential campus
and cannot meaningfully be compared on CDS H6 data — skip them entirely.

```python
import pandas as pd
schools = pd.read_csv("data/processed/schools_clean.csv")
online_ids = set(schools.loc[schools["online_only"] == 1, "unit_id"])

q = pd.read_csv("data/manual/intl_aid_queue.csv")
# Drop any pending online-only rows before processing
q = q[~((q["unit_id"].isin(online_ids)) & (q["status"] == "pending"))]
```
