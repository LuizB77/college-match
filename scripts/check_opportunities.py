#!/usr/bin/env python3
"""
Auto-check every URL in data/manual/opportunities.csv and write back
check_status / check_date columns.

check_status values:
  "auto-checked"  — page loaded and passed all type-appropriate content checks
  "blocked"       — HTTP 403/429 (site blocks bots); shown in app with a caveat
  "failed"        — 404, homepage redirect, or failed content checks
  (unchanged)     — TODO placeholder rows are left as-is

Content rules by type:
  merit_scholarship / need_based / athletic:
      page_ok AND mentions "international" AND amount_found (or amount is blank → n/a)
  competition / entrepreneurship_center / accelerator / other:
      page_ok only (these pages rarely list international eligibility by name)

Run:  python scripts/check_opportunities.py
"""

from __future__ import annotations

import re
import time
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
import requests

CSV_PATH   = Path(__file__).parent.parent / "data" / "manual" / "opportunities.csv"
TODAY      = date.today().isoformat()
TIMEOUT    = 15
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36"
)

# Rows whose name starts with this prefix are skipped (Luiz fills them in later)
TODO_PREFIX = "TODO"

# Types where page_ok is sufficient (no "international" text required)
PAGE_OK_TYPES = {"competition", "entrepreneurship_center", "accelerator", "other"}


def _extract_numbers(amount: str) -> list[str]:
    """Pull bare numeric strings from an amount field, e.g. '$3,000/yr' → ['3000']."""
    nums = re.findall(r"[\d,]+", amount)
    return [n.replace(",", "") for n in nums
            if n.replace(",", "").isdigit() and int(n.replace(",", "")) > 100]


def _is_homepage_redirect(original_url: str, final_url: str) -> bool:
    """True when the server silently redirected us to the site root."""
    orig  = urlparse(original_url)
    final = urlparse(final_url)
    if orig.netloc != final.netloc:
        return True
    if orig.path.strip("/") and final.path.strip("/") in ("", "index.html", "index.php"):
        return True
    return False


def fetch_page(url: str) -> tuple[int, str, str]:
    """
    Fetch url and return (status_code, final_url, body_text).
    Returns (0, url, "") on connection error.
    """
    try:
        resp = requests.get(
            url,
            timeout=TIMEOUT,
            headers={"User-Agent": USER_AGENT},
            allow_redirects=True,
        )
        return resp.status_code, resp.url, resp.text
    except Exception:
        return 0, url, ""


def classify(
    status_code: int,
    final_url: str,
    body_text: str,
    original_url: str,
    row_type: str,
    amount: str,
) -> str:
    """Compute check_status from a fetched page."""
    if status_code in (403, 429):
        return "blocked"

    if status_code != 200 or _is_homepage_redirect(original_url, final_url):
        return "failed"

    # Page loaded successfully
    if row_type in PAGE_OK_TYPES:
        return "auto-checked"

    # merit_scholarship / need_based / athletic
    text_lower = body_text.lower()
    if "international" not in text_lower:
        return "failed"

    nums = _extract_numbers(str(amount))
    if not nums:
        return "auto-checked"   # no specific amount to verify → n/a

    return "auto-checked" if any(n in text_lower.replace(",", "") for n in nums) else "failed"


def main():
    df = pd.read_csv(CSV_PATH)

    new_statuses: list[str] = []
    new_dates:    list[str] = []

    for _, row in df.iterrows():
        name   = str(row.get("name", "")).strip()
        url    = str(row.get("url",  "")).strip()
        amount = str(row.get("amount", "")).strip()
        rtype  = str(row.get("type", "")).strip()
        school = str(row.get("school_name", "?"))

        # Skip placeholder rows — preserve existing status
        if name.startswith(TODO_PREFIX):
            existing = str(row.get("check_status", "failed"))
            new_statuses.append(existing)
            new_dates.append(str(row.get("check_date", TODAY)))
            print(f"  skipped   {school[:30]:<30}  {name[:35]:<35}  (TODO placeholder)")
            continue

        print(f"  checking  {school[:30]:<30}  {name[:35]:<35}", end="  ", flush=True)

        status_code, final_url, body = fetch_page(url)
        s = classify(status_code, final_url, body, url, rtype, amount)

        print(f"HTTP {status_code}  → {s}")
        new_statuses.append(s)
        new_dates.append(TODAY)
        time.sleep(0.4)

    df["check_status"] = new_statuses
    df["check_date"]   = new_dates
    df.to_csv(CSV_PATH, index=False)
    print(f"\nWrote {len(df)} rows → {CSV_PATH}")

    # Summary table
    print("\n── Results ──────────────────────────────────────────────────────────────")
    print(f"{'School':<35} {'Name':<35} {'Status'}")
    print("-" * 85)
    for _, row in df.iterrows():
        print(f"{str(row['school_name'])[:35]:<35} {str(row['name'])[:35]:<35} {row['check_status']}")

    n_ok      = (df["check_status"] == "auto-checked").sum()
    n_blocked = (df["check_status"] == "blocked").sum()
    n_bad     = (df["check_status"] == "failed").sum()
    print(f"\nauto-checked: {n_ok}   blocked (bot-blocked site): {n_blocked}   failed: {n_bad}")


if __name__ == "__main__":
    main()
