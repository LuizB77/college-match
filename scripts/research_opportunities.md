# Research instructions — data/manual/opportunities.csv

## Purpose

`data/manual/opportunities.csv` tracks hand-collected scholarship and program data
that isn't in any public dataset. Each row is a single opportunity at a single school.

## Column definitions

| Column | Values | Notes |
|--------|--------|-------|
| `unit_id` | integer | IPEDS unit_id matching schools_with_majors.csv |
| `school_name` | text | Readable label only; not used in joins |
| `type` | `merit_scholarship` / `athletic` / `need_based` / `competition` / `entrepreneurship_center` / `accelerator` / `other` | |
| `name` | text | Official name of the scholarship or program |
| `description` | text | One sentence from the school's website |
| `amount` | text | As published ("$10,000/yr", "up to full tuition") — blank if none |
| `intl_eligible` | `yes` / `no` / `unknown` | Whether international students are explicitly eligible |
| `url` | URL | **Must be an official school page (.edu domain)** |
| `date_checked` | YYYY-MM-DD | When you opened the URL and confirmed it still exists |
| `verified` | `yes` / `no` | Set to `yes` only after a human confirmed the page is current |

## Rules

1. **Only add rows with an official .edu URL you confirmed exists.**
   No guesses, no aggregators, no third-party scholarship databases.
2. If a school has nothing findable, add no row — silence is accurate.
3. `verified = no` is the default for new rows until a human re-checks the page.
4. Keep `description` short: copy the key phrase from the school's page.
5. For `intl_eligible`, use `yes` only if the school page explicitly says
   international students qualify. Use `unknown` when it's not mentioned.

## Research workflow

For each school to research:

1. Search: `"<school name>" international students merit scholarship site:<school>.edu`
   and `"<school name>" pitch competition OR entrepreneurship center site:<school>.edu`
2. Open the page, confirm it loads and matches.
3. Add a row with `verified = no` and today's date.

## Schools researched (see log below)

Update this log after each research session.

| Date | Researcher | Schools covered | Rows added |
|------|------------|-----------------|------------|
| 2026-09-26 | Claude (automated) | See commit "Opportunities" | See CSV |
