#!/usr/bin/env python3
"""
Auto-check every URL in data/manual/opportunities.csv and write back
check_status / check_date columns.

check_status:
  "auto-checked"  — page loaded, mentions "international", amount visible
  "failed"        — any check failed
  "n/a"           — no URL on the row (shouldn't happen in practice)

Run:  python scripts/check_opportunities.py
"""

from __future__ import annotations

import re
import sys
import time
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
import requests

CSV_PATH   = Path(__file__).parent.parent / "data" / "manual" / "opportunities.csv"
TODAY      = date.today().isoformat()
TIMEOUT    = 15          # seconds per request
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36"
)


def _extract_numbers(amount: str) -> list[str]:
    """Pull bare numeric strings from an amount field, e.g. '$3,000/yr' → ['3000']."""
    nums = re.findall(r"[\d,]+", amount)
    return [n.replace(",", "") for n in nums if n.replace(",", "").isdigit() and int(n.replace(",", "")) > 100]


def _is_homepage_redirect(original_url: str, final_url: str) -> bool:
    """True when the server silently redirected us to the site root."""
    orig = urlparse(original_url)
    final = urlparse(final_url)
    if orig.netloc != final.netloc:
        return True          # crossed to a different domain
    # If the original path was non-trivial and we ended up at "/" or "/#…"
    if orig.path.strip("/") and final.path.strip("/") in ("", "index.html", "index.php"):
        return True
    return False


def check_row(url: str, amount: str) -> tuple[bool, bool, bool | str]:
    """
    Returns (page_ok, mentions_international, amount_found).
    amount_found is the string "n/a" when there is nothing to look for.
    """
    if not url or url in ("nan", "None"):
        return False, False, False

    try:
        resp = requests.get(
            url,
            timeout=TIMEOUT,
            headers={"User-Agent": USER_AGENT},
            allow_redirects=True,
        )
    except Exception:
        return False, False, False

    if resp.status_code != 200:
        return False, False, False

    if _is_homepage_redirect(url, resp.url):
        return False, False, False

    text = resp.text.lower()

    page_ok = True
    mentions_intl = "international" in text

    # Amount check
    nums = _extract_numbers(str(amount))
    if not nums:
        amount_found: bool | str = "n/a"
    else:
        amount_found = any(n in text.replace(",", "") for n in nums)

    return page_ok, mentions_intl, amount_found


def status(page_ok, mentions_intl, amount_found) -> str:
    if not page_ok:
        return "failed"
    if not mentions_intl:
        return "failed"
    if amount_found is False:   # explicit False — not "n/a"
        return "failed"
    return "auto-checked"


def main():
    df = pd.read_csv(CSV_PATH)

    results = []
    for _, row in df.iterrows():
        url    = str(row.get("url", "")).strip()
        amount = str(row.get("amount", "")).strip()
        school = row.get("school_name", "?")
        name   = row.get("name", "?")

        print(f"  checking  {school[:30]:<30}  {name[:35]:<35}", end="  ", flush=True)

        page_ok, m_intl, a_found = check_row(url, amount)
        s = status(page_ok, m_intl, a_found)
        print(f"page_ok={page_ok}  intl={m_intl}  amt={a_found}  → {s}")
        results.append((s, TODAY))
        time.sleep(0.4)   # polite crawl rate

    df["check_status"] = [r[0] for r in results]
    df["check_date"]   = [r[1] for r in results]
    df.to_csv(CSV_PATH, index=False)
    print(f"\nWrote {len(df)} rows → {CSV_PATH}")

    # Summary table
    print("\n── Summary ──────────────────────────────────────────────────────────────")
    print(f"{'School':<35} {'Name':<35} {'Status'}")
    print("-" * 85)
    for _, row in df.iterrows():
        print(f"{str(row['school_name'])[:35]:<35} {str(row['name'])[:35]:<35} {row['check_status']}")

    n_ok  = (df["check_status"] == "auto-checked").sum()
    n_bad = (df["check_status"] == "failed").sum()
    print(f"\nauto-checked: {n_ok}   failed: {n_bad}")


if __name__ == "__main__":
    main()
