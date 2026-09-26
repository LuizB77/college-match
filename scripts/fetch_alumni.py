#!/usr/bin/env python3
"""
Fetch notable alumni from Wikidata for every school in schools_with_majors.csv.

Wikidata link: IPEDS ID (P1771) → school item → P69 (educated at) → person item.
Per person: English label, sitelinks count (fame proxy), Portuguese Wikipedia
presence (Brazil relevance), English Wikipedia URL.
Occupations are fetched in a second pass for the top-5 alumni per school.

Saves: data/processed/notable_alumni.csv

Usage:
    python scripts/fetch_alumni.py          # full run
    python scripts/fetch_alumni.py --dry-run  # first batch only (testing)

Requires: pip install requests (not a runtime dependency — script-only)
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import pandas as pd

try:
    import requests
except ImportError:
    sys.exit("Missing dependency: pip install requests")

ROOT      = Path(__file__).parent.parent
DATA_PATH = ROOT / "data/processed/schools_with_majors.csv"
OUT_PATH  = ROOT / "data/processed/notable_alumni.csv"

SPARQL_URL = "https://query.wikidata.org/sparql"
UA = (
    "CollegeMatchBot/1.0 "
    "(https://github.com/LuizB77/college-match; contact: luiz.0breda@gmail.com)"
)

BATCH     = 200   # IPEDS IDs per main query
PAUSE     = 2.5   # seconds between batches (Wikidata polite use)
TIMEOUT   = 90    # seconds per HTTP request
RETRIES   = 3

# ── Wikidata SPARQL queries ───────────────────────────────────────────────────

MAIN_QUERY = """
SELECT ?ipedsId ?person ?personLabel ?sitelinks ?hasPtWiki ?enWikiUrl WHERE {{
  VALUES ?ipedsId {{ {values} }}
  ?school wdt:P1771 ?ipedsId .
  ?person wdt:P69 ?school ;
          wikibase:sitelinks ?sitelinks .
  OPTIONAL {{
    ?enArt schema:about ?person ;
           schema:isPartOf <https://en.wikipedia.org/> ;
           schema:name     ?enWikiName .
    BIND(CONCAT("https://en.wikipedia.org/wiki/",
                REPLACE(?enWikiName, " ", "_")) AS ?enWikiUrl)
  }}
  BIND(EXISTS {{
    ?ptArt schema:about ?person ;
           schema:isPartOf <https://pt.wikipedia.org/> .
  }} AS ?hasPtWiki)
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" . }}
}}
ORDER BY DESC(?sitelinks)
LIMIT 5000
"""

OCC_QUERY = """
SELECT ?person (SAMPLE(?lbl) AS ?occupation) WHERE {{
  VALUES ?person {{ {wikidata_ids} }}
  OPTIONAL {{
    ?person wdt:P106 ?occ .
    ?occ rdfs:label ?lbl .
    FILTER(LANG(?lbl) = "en")
  }}
}}
GROUP BY ?person
"""


# ── Helpers ───────────────────────────────────────────────────────────────────

def sparql_query(query: str, label: str) -> list[dict]:
    """Run a SPARQL query with retry logic. Returns bindings or []."""
    for attempt in range(1, RETRIES + 1):
        try:
            resp = requests.get(
                SPARQL_URL,
                params={"query": query, "format": "json"},
                headers={
                    "User-Agent": UA,
                    "Accept": "application/sparql-results+json",
                },
                timeout=TIMEOUT,
            )
            resp.raise_for_status()
            return resp.json()["results"]["bindings"]
        except requests.exceptions.Timeout:
            print(f"  [{label}] timeout (attempt {attempt}/{RETRIES})", flush=True)
        except Exception as exc:
            print(f"  [{label}] {type(exc).__name__}: {exc} (attempt {attempt}/{RETRIES})", flush=True)
        if attempt < RETRIES:
            time.sleep(PAUSE * attempt)
    return []


def v(binding: dict, key: str) -> str | None:
    return binding[key]["value"] if key in binding else None


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true",
                        help="Process only the first batch (for testing).")
    args = parser.parse_args()

    schools   = pd.read_csv(DATA_PATH)
    unit_ids  = schools["unit_id"].dropna().astype(int).tolist()
    ipeds_str = [str(u) for u in unit_ids]

    batches = [ipeds_str[i:i + BATCH] for i in range(0, len(ipeds_str), BATCH)]
    if args.dry_run:
        batches = batches[:1]
        print(f"DRY RUN — processing {len(batches)} batch of ≤{BATCH} schools only.")

    n_batches = len(batches)
    print(f"Schools: {len(ipeds_str)}  |  batches: {n_batches} (≤{BATCH} each)", flush=True)

    all_rows: list[dict] = []
    failed = 0

    for i, batch in enumerate(batches, 1):
        values = " ".join(f'"{x}"' for x in batch)
        label  = f"batch {i}/{n_batches}"
        print(f"{label} ({len(batch)} schools) … ", end="", flush=True)

        bindings = sparql_query(MAIN_QUERY.format(values=values), label)
        print(f"{len(bindings)} rows", flush=True)

        if not bindings:
            failed += 1

        for b in bindings:
            ipeds  = v(b, "ipedsId")
            p_url  = v(b, "person")
            if not ipeds or not p_url:
                continue
            all_rows.append({
                "unit_id":     int(ipeds),
                "wikidata_id": p_url.split("/")[-1],
                "name":        v(b, "personLabel"),
                "sitelinks":   int(v(b, "sitelinks") or 0),
                "has_pt_wiki": v(b, "hasPtWiki") == "true",
                "en_wiki_url": v(b, "enWikiUrl"),
            })

        if i < n_batches:
            time.sleep(PAUSE)

    if not all_rows:
        print("ERROR: no alumni found across all batches.", file=sys.stderr)
        sys.exit(1)

    df = pd.DataFrame(all_rows)

    # Deduplicate: same person may appear multiple times per school (rare Wikidata quirk)
    df = df.drop_duplicates(subset=["unit_id", "wikidata_id"])

    # Keep top 10 per school by sitelinks
    df = (
        df.sort_values("sitelinks", ascending=False)
          .groupby("unit_id").head(10)
          .sort_values(["unit_id", "sitelinks"], ascending=[True, False])
          .reset_index(drop=True)
    )

    # ── Second pass: occupations for top-5 per school ─────────────────────────
    top5_ids = (
        df.groupby("unit_id").head(5)["wikidata_id"]
          .drop_duplicates().tolist()
    )
    print(f"\nFetching occupations for {len(top5_ids)} top alumni …", flush=True)

    occ_map: dict[str, str] = {}
    occ_batch_size = 200
    occ_batches = [top5_ids[i:i + occ_batch_size]
                   for i in range(0, len(top5_ids), occ_batch_size)]

    for j, obatch in enumerate(occ_batches, 1):
        wd_ids = " ".join(f"wd:{wid}" for wid in obatch)
        lbl    = f"occ {j}/{len(occ_batches)}"
        print(f"  {lbl} … ", end="", flush=True)
        bindings2 = sparql_query(OCC_QUERY.format(wikidata_ids=wd_ids), lbl)
        print(f"{len(bindings2)} rows", flush=True)
        for b in bindings2:
            pid = v(b, "person")
            occ = v(b, "occupation")
            if pid:
                occ_map[pid.split("/")[-1]] = occ or ""
        if j < len(occ_batches):
            time.sleep(PAUSE)

    df["occupation"] = df["wikidata_id"].map(occ_map)

    df.to_csv(OUT_PATH, index=False)

    schools_with = df["unit_id"].nunique()
    total_rows   = len(df)
    size_kb      = OUT_PATH.stat().st_size / 1024

    print(f"\nSchools with ≥1 alum : {schools_with}")
    print(f"Total rows           : {total_rows}")
    print(f"File size            : {size_kb:.1f} KB  →  {OUT_PATH}")
    if failed:
        print(f"Failed batches       : {failed}  (re-run to retry)", file=sys.stderr)


if __name__ == "__main__":
    main()
