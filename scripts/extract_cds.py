#!/usr/bin/env python3
"""
extract_cds.py — hybrid CDS extractor with measured accuracy.

Strategies per file type (tried in order):
  PDF  : pdfplumber table rows → text-regex patterns
  XLSX : openpyxl direct cell search
  Both : sanity-check outputs; log fields that need LLM review when key present

Usage:
  .venv/bin/python scripts/extract_cds.py                    # all schools
  .venv/bin/python scripts/extract_cds.py --unitid 166027    # one school
  .venv/bin/python scripts/extract_cds.py --measure          # accuracy table
  .venv/bin/python scripts/extract_cds.py --download         # fetch missing files
"""

import argparse
import csv
import os
import re
import sys
import urllib.request
from pathlib import Path
from typing import Optional

try:
    import pdfplumber
except ImportError:
    pdfplumber = None  # type: ignore

try:
    import openpyxl
except ImportError:
    openpyxl = None  # type: ignore

CACHE = Path(__file__).resolve().parent.parent / "data" / "cds_cache"
GT_PATH = Path(__file__).resolve().parent.parent / "data" / "manual" / "intl_aid.csv"

# ── School config ──────────────────────────────────────────────────────────────
# "all": single PDF with all sections
# "H"/"B"/"G": per-section PDFs (split CDS)
# "xlsx": XLSX file
SCHOOL_CONFIG: dict[str, dict] = {
    "117946": {  # LMU
        "name": "Loyola Marymount University",
        "year": "2024-25",
        "source_url": "https://academics.lmu.edu/media/lmuacademics/ir/cds/CDS_2024-25_REVISED.pdf",
        "files": {"all": "lmu_117946_cds_2024-25.pdf"},
    },
    "122612": {  # USF
        "name": "University of San Francisco",
        "year": "2024-25",
        "source_url": "",
        "files": {"all": "usf_122612_cds_2024-25.pdf"},
    },
    "122931": {  # SCU
        "name": "Santa Clara University",
        "year": "2025-26",
        "source_url": "",
        "files": {"all": "scu_122931_cds_2025-26.pdf"},
    },
    "123961": {  # USC
        "name": "University of Southern California",
        "year": "2025-26",
        "source_url": "https://oir.usc.edu/wp-content/uploads/sites/3/2026/10/CDS_2025-26_FINAL.pdf",
        "files": {"all": "usc_123961_cds_2025-26.pdf"},
    },
    "130794": {  # Yale
        "name": "Yale University",
        "year": "2025-26",
        "source_url": "https://oir.yale.edu/sites/default/files/yale_cds_2025-26_md_20260616.pdf",
        "files": {"all": "yale_130794_cds_2025-26.pdf"},
    },
    "133553": {  # ERAU
        "name": "Embry-Riddle Aeronautical University",
        "year": "2023-24",
        "source_url": "",
        "files": {"all": "erau_133553_cds_2023-24.pdf"},
    },
    "139658": {  # Emory
        "name": "Emory University",
        "year": "2025-26",
        "source_url": "",
        "files": {"all": "emory_139658_cds_2025-26.pdf"},
    },
    "143084": {  # Augustana
        "name": "Augustana College",
        "year": "2025-26",
        "source_url": "",
        "files": {"all": "augustana_143084_cds_2025-26.pdf"},
    },
    "144050": {  # UChicago
        "name": "University of Chicago",
        "year": "2025-26",
        "source_url": "https://data.uchicago.edu/files/2026/08/CDS_2025-2026_to_publish-1.pdf",
        "files": {"all": "uchicago_144050_cds_2025-26.pdf"},
    },
    "147767": {  # Northwestern
        "name": "Northwestern University",
        "year": "2025-26",
        "source_url": "https://enrollment.northwestern.edu/data/2025-2026.pdf",
        "files": {"all": "northwestern_147767_cds_2025-26.pdf"},
    },
    "164739": {  # Bentley
        "name": "Bentley University",
        "year": "2023-24",
        "source_url": "",
        "files": {"all": "bentley_164739_cds_2023-24.pdf"},
    },
    "164748": {  # Berklee
        "name": "Berklee College of Music",
        "year": "2025-26",
        "source_url": "https://www.berklee.edu/sites/default/files/2026-02/CDS_2025-2026.pdf",
        "files": {"all": "berklee_164748_cds_2025-26.pdf"},
    },
    "164924": {  # Boston College
        "name": "Boston College",
        "year": "2024-25",
        "source_url": "",
        "files": {"all": "bc_164924_cds_2024-25.pdf"},
    },
    "164988": {  # BU (split)
        "name": "Boston University",
        "year": "2024-25",
        "source_url": "https://www.bu.edu/asir/files/2025/03/cds-2025-h.pdf",
        "files": {"H": "bu_164988_cds_2025_h.pdf", "B": "bu_164988_cds_2025_b.pdf", "G": "bu_164988_cds_2025_g.pdf"},
    },
    "165015": {  # Brandeis
        "name": "Brandeis University",
        "year": "2025-26",
        "source_url": "",
        "files": {"all": "brandeis_165015_cds_2025-26.pdf"},
    },
    "166027": {  # Harvard
        "name": "Harvard University",
        "year": "2025-26",
        "source_url": "https://oira.harvard.edu/files/2026/07/CDS_2025-2026.pdf",
        "files": {"all": "harvard_166027_cds_2025-26.pdf"},
    },
    "166683": {  # MIT
        "name": "Massachusetts Institute of Technology",
        "year": "2025-26",
        "source_url": "https://ir.mit.edu/projects/2025-26-common-data-set/",
        "files": {"all": "mit_166683_cds_2025-26.pdf"},  # Cloudflare-protected; download manually
    },
    "166939": {  # MtHolyoke (split — H section lacks H6)
        "name": "Mount Holyoke College",
        "year": "2024-25",
        "source_url": "https://www.mtholyoke.edu/common-data-set",
        "files": {"H": "mtholyoke_h_166939_cds_2024-25.pdf", "B": "mtholyoke_b_166939_cds_2024-25.pdf", "G": "mtholyoke_g_166939_cds_2024-25.pdf"},
    },
    "167358": {  # Northeastern
        "name": "Northeastern University",
        "year": "2024-25",
        "source_url": "https://uds.northeastern.edu/wp-content/uploads/2026/03/CDS-2024-25.pdf",
        "files": {"all": "northeastern_167358_cds_2024-25.pdf"},
    },
    "168148": {  # Tufts
        "name": "Tufts University",
        "year": "2025-26",
        "source_url": "https://provost.tufts.edu/institutionalresearch/wp-content/uploads/sites/5/CDS_2025-2026.pdf",
        "files": {"all": "tufts_168148_cds_2025-26.pdf"},
    },
    "169080": {  # Calvin
        "name": "Calvin University",
        "year": "2025-26",
        "source_url": "",
        "files": {"all": "calvin_169080_cds_2025-26.pdf"},
    },
    "179867": {  # WashU
        "name": "Washington University in St. Louis",
        "year": "2025-26",
        "source_url": "",
        "files": {"all": "washu_179867_cds_2025-26.pdf"},
    },
    "182670": {  # Dartmouth
        "name": "Dartmouth College",
        "year": "2025-26",
        "source_url": "https://www.dartmouth.edu/oir/pdfs/cds_2025-26.pdf",
        "files": {"all": "dartmouth_182670_cds_2025-26.pdf"},
    },
    "189097": {  # Barnard
        "name": "Barnard College",
        "year": "2024-25",
        "source_url": "",
        "files": {"all": "barnard_189097_cds_2024-25.pdf"},
    },
    "190150": {  # Columbia
        "name": "Columbia University",
        "year": "2025-26",
        "source_url": "https://opir.columbia.edu/sites/opir.columbia.edu/files/content/Common%20Data%20Set/2025-26_Columbia_College_and_Columbia_Enginnering_CDS.pdf",
        "files": {"all": "columbia_190150_cds_2025-26.pdf"},
    },
    "193900": {  # NYU
        "name": "New York University",
        "year": "2025-26",
        "source_url": "https://www.nyu.edu/content/dam/nyu/institutionalResearch/documents/cds-2025-2026/CDS%202025-2026%20FINAL%20(no%20G).pdf",
        "files": {"all": "nyu_193900_cds_2025-26.pdf"},
    },
    "194578": {  # Pratt
        "name": "Pratt Institute",
        "year": "2025-26",
        "source_url": "https://www.pratt.edu/wp-content/uploads/2026/02/2025-2026-CDS.xlsx",
        "files": {"xlsx": "pratt_194578_cds_2025-26.xlsx"},
    },
    "195030": {  # Rochester
        "name": "University of Rochester",
        "year": "2025-26",
        "source_url": "https://www.rochester.edu/provost/wp-content/uploads/2026/06/CDS-2025-26-completed-for-web.pdf",
        "files": {"all": "rochester_195030_cds_2025-26.pdf"},
    },
    "198419": {  # Duke
        "name": "Duke University",
        "year": "2025-26",
        "source_url": "https://ir.provost.duke.edu/sites/default/files/CDS-2025-26-Duke-University-Final-to-be-published.pdf",
        "files": {"all": "duke_198419_cds_2025-26.pdf"},
    },
    "201645": {  # CWRU
        "name": "Case Western Reserve University",
        "year": "2025-26",
        "source_url": "",
        "files": {"all": "cwru_201645_cds_2025-26.pdf"},
    },
    "212054": {  # Drexel
        "name": "Drexel University",
        "year": "2025-26",
        "source_url": "https://drexel.edu/institutionalresearch/~/media/Drexel/Provost-Group/InstitutionalResearch/Documents/Factbook/CDS_2025-2026.pdf",
        "files": {"all": "drexel_212054_cds_2025-26.pdf"},
    },
    "221999": {  # Vanderbilt
        "name": "Vanderbilt University",
        "year": "2024-25",
        "source_url": "",
        "files": {"xlsx": "vanderbilt_221999_cds_2024-25.xlsx"},
    },
    "227757": {  # Rice
        "name": "Rice University",
        "year": "2025-26",
        "source_url": "",
        "files": {"all": "rice_227757_cds_2025-26.pdf"},
    },
    "228875": {  # TCU
        "name": "Texas Christian University",
        "year": "2024-25",
        "source_url": "",
        "files": {"all": "tcu_228875_cds_2024-25.pdf"},
    },
    "230038": {  # BYU
        "name": "Brigham Young University",
        "year": "2025-26",
        "source_url": "https://assessmentandplanning.byu.edu/0000019d-e4b0-d088-a1dd-eff755a90000/cds-2025-2026-pdf",
        "files": {"all": "byu_230038_cds_2025-26.pdf"},
    },
}

# ── Utility ────────────────────────────────────────────────────────────────────

def _to_int(s: str) -> Optional[int]:
    """Parse a string like '$74,186' or '74186' or '74,186.00' to int."""
    if s is None:
        return None
    s = str(s).strip().replace("$", "").replace(",", "")
    s = re.sub(r"\.00$", "", s)
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return None


def _first_num(text: str, min_val: int = 0, max_val: int = 9_999_999) -> Optional[int]:
    """Return first integer in text that is within [min_val, max_val]."""
    for m in re.finditer(r"\$?\s*([\d,]+)(?:\.\d+)?", text):
        v = _to_int(m.group(1))
        if v is not None and min_val <= v <= max_val:
            return v
    return None


def _clean(text: str) -> str:
    """Remove (cid:) escapes; collapse runs of spaces/tabs but KEEP newlines."""
    text = re.sub(r"\(cid:\d+\)", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def _clean_inline(text: str) -> str:
    """Fully collapse whitespace including newlines (for table-cell labels)."""
    text = re.sub(r"\(cid:\d+\)", "", text)
    return re.sub(r"\s+", " ", text).strip()


# ── PDF H6 extraction ──────────────────────────────────────────────────────────

def _find_h6_page(pages: list[str]) -> int:
    """Return page index of the H6 section header, or -1."""
    for i, txt in enumerate(pages):
        # Standard: "H6." or "H6 " at line start + nonresident context
        if re.search(r"^H6[\.\s-]", txt, re.M) and re.search(r"nonresident|international", txt, re.I):
            # Exclude pages that only mention H6 in the preamble (before page 15)
            if i >= 2:
                return i
        # BU-style: "H6. Aid to undergraduate international"
        if re.search(r"H6\.\s+Aid to undergraduate", txt, re.I):
            return i
    return -1


def _extract_h6_from_text(text: str, next_text: str = "") -> tuple[Optional[int], Optional[int]]:
    """
    Extract (aided_count, avg_award) from the H6 section text.
    Handles ⇒-prefix, inline, next-line, and BU-style formats.
    """
    combined = text + " " + next_text

    # BU-style: "Number of recipients 224" / "Average aid $50,568"
    m = re.search(r"Number of recipients\s+(\d[\d,]*)", combined, re.I)
    if m:
        count = _to_int(m.group(1))
        m2 = re.search(r"Average aid\s+\$?([\d,]+)", combined, re.I)
        avg = _to_int(m2.group(1)) if m2 else None
        return count, avg

    # Standard format: find count after "awarded need-based or non-need-based aid:"
    count: Optional[int] = None
    avg: Optional[int] = None

    # Extract aided count from H6: integer that appears between the question
    # "provide the number of ... nonresidents who were awarded ..." and the average question.
    # All patterns use line-based search (no re.S) to avoid cross-line greedy matches.
    lines = combined.split("\n")

    # Find the H6 section header line first so we don't confuse earlier sections
    # (e.g. H4 "Provide the number of...") with H6 count questions.
    h6_line = -1
    for j, ln in enumerate(lines):
        if re.search(r"^H6[\.\s-]|H6\.\s+Aid to undergraduate", ln, re.I):
            h6_line = j
            break

    # Find lines marking the start of the count question and the average question,
    # only searching after the H6 header.
    q_start = q_end = avg_start = -1
    for j, ln in enumerate(lines):
        if h6_line >= 0 and j <= h6_line:
            continue
        if re.search(r"provide the number of|degree-seeking nonresidents? who were", ln, re.I):
            if q_start == -1:
                q_start = j
        if re.search(r"non.need.based\s+aid:?", ln, re.I):
            q_end = j
        if re.search(r"Average\s+dollar\s+amount", ln, re.I) and avg_start == -1:
            avg_start = j

    # The count is the first standalone integer between q_start and avg_start
    search_start = max(0, q_start) if q_start >= 0 else 0
    search_end   = avg_start if avg_start > search_start else min(search_start + 8, len(lines))
    for j in range(search_start, search_end):
        ln = lines[j].strip()
        # Standalone integer (possibly with ⇒ prefix), or integer at EOL after "...aid:"
        m_standalone = re.search(r"^[⇒→►]?\s*\$?([\d,]+)\s*$", ln)
        m_eol        = re.search(r"(?:aid:|number\s+of)\s+([\d,]+)\s*$", ln, re.I)
        m_inline     = re.search(r"non.need.based\s+aid:?\s+([\d,]+)\s*$", ln, re.I)
        m_wrapped    = re.search(r"non[-–]need[-–]\s+([\d,]+)\s*$", ln, re.I)
        m_awarded    = re.search(r"were\s+awarded\s+([\d,]+)\s*$", ln, re.I)
        for m in (m_standalone, m_eol, m_inline, m_wrapped, m_awarded):
            if m:
                v = _to_int(m.group(1))
                if v and 1 <= v <= 20_000:
                    count = v
                    break
        if count is not None:
            break

    # Average award — search line-by-line for the "Average dollar amount" question,
    # then grab the first plausible dollar amount on the same or next few lines.
    lines = combined.split("\n")
    for j, ln in enumerate(lines):
        if re.search(r"Average\s+dollar\s+amount", ln, re.I):
            # Check inline first (e.g. "... nonresidents: $92,699" or "$87841")
            m2 = re.search(r"\$\s*([\d,]+(?:\.\d+)?)", ln)
            if m2:
                v = _to_int(m2.group(1))
                if v and v > 1000:
                    avg = v
                    break
            # Search next 4 lines
            for k in range(j + 1, min(j + 5, len(lines))):
                candidate = re.search(r"^[⇒→►]?\s*\$?([\d,]+(?:\.\d+)?)\s*$", lines[k].strip())
                if candidate:
                    v = _to_int(candidate.group(1))
                    if v and v > 1000:
                        avg = v
                        break
                # Also: "nonresidents: $84,185" style at end of continuing line
                m_inline = re.search(r"nonresidents?:?\s*\$?\s*([\d,]+)", lines[k], re.I)
                if m_inline:
                    v = _to_int(m_inline.group(1))
                    if v and v > 1000:
                        avg = v
                        break
            break

    return count, avg


def extract_h6_pdf(pages: list[str]) -> tuple[Optional[int], Optional[int], str]:
    """
    Extract (aided_count, avg_award, provenance) from a list of page texts.
    provenance is 'h6_text' or 'h6_missing'.
    """
    idx = _find_h6_page(pages)
    if idx == -1:
        return None, None, "h6_missing"
    next_pg = pages[idx + 1] if idx + 1 < len(pages) else ""
    count, avg = _extract_h6_from_text(pages[idx], next_pg)
    return count, avg, "h6_text"


# ── PDF B2 extraction ──────────────────────────────────────────────────────────

def extract_b2_pdf(pdf_path: Path) -> tuple[Optional[int], str]:
    """
    Extract total degree-seeking nonresident undergrads from B2 table.
    Returns (count, provenance).
    """
    if pdfplumber is None:
        return None, "b2_missing"
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            for pg in pdf.pages:
                for tbl in pg.extract_tables():
                    for row in tbl:
                        if not row:
                            continue
                        label = _clean_inline(str(row[0] or ""))
                        if re.search(r"nonresident", label, re.I):
                            nums = []
                            for cell in row[1:]:
                                v = _to_int(str(cell or ""))
                                if v is not None and v > 0:
                                    nums.append(v)
                            if len(nums) >= 2:
                                return nums[1], "b2_table"
                            if len(nums) == 1:
                                return nums[0], "b2_table"
            # Text fallback
            for pg in pdf.pages:
                txt = pg.extract_text() or ""
                m = re.search(r"[Nn]onresident\s+alien[^\n]{0,50}?(\d{1,4})\s+(\d{1,4})", txt)
                if m:
                    return _to_int(m.group(2)), "b2_regex"
    except Exception:
        pass
    return None, "b2_missing"


# ── PDF G1 extraction ──────────────────────────────────────────────────────────

_TUITION_LABEL = re.compile(r"[Tt]uition:?(?:\s*$|\s*\$)", re.M)
_FEES_LABEL    = re.compile(r"[Rr]equired\s*[Ff]ee|[Mm]andatory\s*[Ff]ee|[Ff]ull.time\s+(?:mandatory|required)", re.I)
_HOUSING_LABEL = re.compile(r"[Ff]ood\s*(?:and|&)\s*[Hh]ousing|[Rr]oom\s*(?:and|&)\s*[Bb]oard|on-campus\)|[Hh]ousing.*on.campus", re.I)


def _is_public_variant(label: str) -> bool:
    """True if this is an in-district / in-state / out-of-state tuition row."""
    return bool(re.search(r"district|in.state|out.of.state|non.resid", label, re.I))


def extract_g1_pdf(pdf_path: Path) -> tuple[Optional[int], str]:
    """
    Extract total cost (tuition + required fees + food/housing) from G1.
    Returns (cost, provenance).
    """
    if pdfplumber is None:
        return None, "g1_missing"
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            pages = pdf.pages
            for i, pg in enumerate(pages):
                txt = pg.extract_text() or ""
                if not (re.search(r"\bG1\b", txt) and re.search(r"[Tt]uition", txt)):
                    continue

                # G1 can span onto the next page — collect rows from p[i] and p[i+1]
                window_pages = [pages[i]] + ([pages[i + 1]] if i + 1 < len(pages) else [])
                tuition = fees = housing = None

                # ── Table strategy ───────────────────────────────────────────
                for wp in window_pages:
                    for tbl in wp.extract_tables():
                        for row in tbl:
                            if not row or row[0] is None:
                                continue
                            label = _clean_inline(str(row[0]))
                            val = None
                            for cell in row[1:]:
                                if cell is not None:
                                    v = _to_int(str(cell))
                                    if v and v > 500:
                                        val = v
                                        break
                            if val is None:
                                continue
                            if _TUITION_LABEL.search(label) and not _is_public_variant(label):
                                tuition = tuition or val
                            elif _FEES_LABEL.search(label) and not _is_public_variant(label):
                                fees = fees or val
                            elif _HOUSING_LABEL.search(label):
                                housing = housing or val

                if tuition and housing:
                    return tuition + (fees or 0) + housing, "g1_table"

                # ── Text-regex strategy ──────────────────────────────────────
                tuition = fees = housing = None
                for wp in window_pages:
                    for ln in (wp.extract_text() or "").split("\n"):
                        if _TUITION_LABEL.search(ln) and not _is_public_variant(ln):
                            v = _first_num(ln, 5000, 200_000)
                            if v: tuition = tuition or v
                        elif _FEES_LABEL.search(ln) and not _is_public_variant(ln):
                            v = _first_num(ln, 100, 20_000)  # fees often < $5 000
                            if v: fees = fees or v
                        elif _HOUSING_LABEL.search(ln):
                            v = _first_num(ln, 1000, 200_000)
                            if v: housing = housing or v
                if tuition and housing:
                    return tuition + (fees or 0) + housing, "g1_regex"
                break  # found G1 page, stop searching

    except Exception:
        pass
    return None, "g1_missing"


# ── XLSX extraction ────────────────────────────────────────────────────────────

def extract_xlsx(xlsx_path: Path) -> dict:
    """Extract aided_count, avg_award, n_total_intl, cds_total_cost from XLSX."""
    if openpyxl is None:
        return {}
    wb = openpyxl.load_workbook(str(xlsx_path), data_only=True)

    result: dict = {}
    fallback_log: list[str] = []

    for sheet in wb.worksheets:
        rows_text = []
        for row in sheet.iter_rows(values_only=True):
            row_vals = [v for v in row if v is not None]
            if row_vals:
                rows_text.append(row_vals)

        for j, row_vals in enumerate(rows_text):
            s = " | ".join(str(v).strip() for v in row_vals)

            # H6 count
            if re.search(r"provide the number.*nonresident.*awarded|awarded.*nonresident.*number", s, re.I):
                for k in range(j, min(j + 3, len(rows_text))):
                    nums = [v for v in rows_text[k] if isinstance(v, (int, float)) and 1 <= v <= 5000]
                    if nums:
                        result.setdefault("aided_count", int(nums[0]))
                        break

            # H6 average
            if re.search(r"average dollar amount.*nonresident|average.*financial aid.*nonresident", s, re.I):
                for k in range(j, min(j + 3, len(rows_text))):
                    nums = [v for v in rows_text[k] if isinstance(v, (int, float)) and 1000 < v < 200_000]
                    if nums:
                        result.setdefault("avg_award", int(nums[0]))
                        break

            # B2 nonresident
            if re.search(r"^nonresidents?\s*\|", s, re.I) or (
                len(row_vals) >= 3 and re.search(r"nonresident", str(row_vals[0]), re.I)
            ):
                nums = [_to_int(str(v)) for v in row_vals[1:] if _to_int(str(v)) and _to_int(str(v)) > 0]
                if len(nums) >= 2:
                    result.setdefault("n_total_intl", nums[1])

            # G1 tuition
            if re.search(r"^Tuition:?\s*\|", s) and not re.search(r"district|in.state|out.of.state", s, re.I):
                nums = [_to_int(str(v)) for v in row_vals[1:] if _to_int(str(v)) and _to_int(str(v)) > 5000]
                if nums:
                    result.setdefault("tuition", nums[0])

            # G1 required fees
            if re.search(r"Required Fee", s, re.I):
                nums = [_to_int(str(v)) for v in row_vals[1:] if _to_int(str(v)) is not None and _to_int(str(v)) >= 0]
                if nums:
                    result.setdefault("fees", nums[0])

            # G1 food and housing
            if re.search(r"[Ff]ood.*[Hh]ousing|[Hh]ousing.*[Ff]ood|[Rr]oom.*[Bb]oard", s, re.I):
                nums = [_to_int(str(v)) for v in row_vals[1:] if _to_int(str(v)) and _to_int(str(v)) > 1000]
                if nums:
                    result.setdefault("housing", nums[0])

    if "tuition" in result and "housing" in result:
        result["cds_total_cost"] = result["tuition"] + result.get("fees", 0) + result["housing"]

    return result


# ── LLM snippet fallback ───────────────────────────────────────────────────────

_LLM_LOG: list[dict] = []


def _llm_fallback(unitid: str, field: str, snippet: str) -> Optional[int]:
    """
    Send a page snippet to Claude API to extract a missing field.
    Logs the attempt. Returns None if no API key is available.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    _LLM_LOG.append({"unitid": unitid, "field": field, "snippet_len": len(snippet)})
    if not api_key:
        return None
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        prompts = {
            "aided_count": "How many degree-seeking nonresident/international undergrads received institutional financial aid? Reply with the integer only.",
            "avg_award":   "What is the average dollar amount of institutional financial aid awarded to degree-seeking nonresident undergrads? Reply with the integer only (no $ or commas).",
            "n_total_intl":"How many degree-seeking nonresident alien undergrads are enrolled total? Reply with the integer only.",
            "cds_total_cost": "What is the sum of tuition + required fees + food and housing (on-campus) for a full-time undergraduate? Reply with the integer only (no $ or commas).",
        }
        question = prompts.get(field, f"Extract the value for {field}. Reply with the integer only.")
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=50,
            messages=[{
                "role": "user",
                "content": f"From this CDS page excerpt:\n\n{snippet[:3000]}\n\n{question}",
            }],
        )
        text = response.content[0].text.strip()
        return _to_int(re.search(r"[\d,]+", text).group()) if re.search(r"[\d,]+", text) else None
    except Exception:
        return None


# ── Main per-school extractor ──────────────────────────────────────────────────

def extract_school(unitid: str) -> dict:
    """
    Extract CDS fields for one school.
    Returns dict with keys: aided_count, avg_award, n_total_intl, cds_total_cost,
    pct_intl_aided (computed), and fallback_fields (list of fields that hit LLM).
    """
    cfg = SCHOOL_CONFIG.get(unitid)
    if cfg is None:
        return {"error": f"unitid {unitid} not in SCHOOL_CONFIG"}

    files = cfg["files"]
    result: dict = {
        "unitid": unitid,
        "name": cfg["name"],
        "year": cfg["year"],
        "aided_count": None,
        "avg_award": None,
        "n_total_intl": None,
        "cds_total_cost": None,
        "fallback_fields": [],
        "notes": "",
    }

    # ── XLSX path ──────────────────────────────────────────────────────────────
    if "xlsx" in files:
        xlsx_path = CACHE / files["xlsx"]
        if not xlsx_path.exists():
            result["notes"] = "XLSX not found"
            return result
        xlsx_data = extract_xlsx(xlsx_path)
        result["aided_count"] = xlsx_data.get("aided_count")
        result["avg_award"] = xlsx_data.get("avg_award")
        result["n_total_intl"] = xlsx_data.get("n_total_intl")
        result["cds_total_cost"] = xlsx_data.get("cds_total_cost")
        _apply_sanity_and_fallback(unitid, result, xlsx_path)
        _compute_pct(result)
        return result

    # ── PDF path ───────────────────────────────────────────────────────────────
    def _pages(key: str) -> list[str]:
        fname = files.get(key) or files.get("all", "")
        path = CACHE / fname if fname else None
        if not path or not path.exists():
            return []
        try:
            with pdfplumber.open(str(path)) as pdf:
                return [_clean(pg.extract_text() or "") for pg in pdf.pages]
        except Exception as e:
            result["notes"] += f" PDF error({key}): {e}"
            return []

    # H section
    h_pages = _pages("H") or _pages("all")
    if h_pages:
        aided, avg, prov = extract_h6_pdf(h_pages)
        result["aided_count"] = aided
        result["avg_award"] = avg
        if prov == "h6_missing":
            # Try LLM fallback with the most likely page text
            for p in h_pages:
                if "H6" in p:
                    result["aided_count"] = _llm_fallback(unitid, "aided_count", p)
                    result["avg_award"]   = _llm_fallback(unitid, "avg_award", p)
                    result["fallback_fields"].extend(["aided_count", "avg_award"])
                    break
    else:
        result["notes"] += " H file not found"

    # B section
    b_key = "B" if "B" in files else "all"
    b_fname = files.get(b_key, "")
    b_path = CACHE / b_fname if b_fname else None
    if b_path and b_path.exists():
        n_total, prov = extract_b2_pdf(b_path)
        result["n_total_intl"] = n_total
        if n_total is None:
            # LLM fallback
            pages = _pages(b_key)
            snippet = next((p for p in pages if "nonresident" in p.lower()), "")
            result["n_total_intl"] = _llm_fallback(unitid, "n_total_intl", snippet)
            if result["n_total_intl"]:
                result["fallback_fields"].append("n_total_intl")
    else:
        result["notes"] += " B file not found"

    # G section
    g_key = "G" if "G" in files else "all"
    g_fname = files.get(g_key, "")
    g_path = CACHE / g_fname if g_fname else None
    if g_path and g_path.exists():
        cost, prov = extract_g1_pdf(g_path)
        result["cds_total_cost"] = cost
        if cost is None:
            pages = _pages(g_key)
            snippet = next((p for p in pages if re.search(r"\bG1\b", p)), "")
            result["cds_total_cost"] = _llm_fallback(unitid, "cds_total_cost", snippet)
            if result["cds_total_cost"]:
                result["fallback_fields"].append("cds_total_cost")
    else:
        result["notes"] += " G file not found"

    _apply_sanity_and_fallback(unitid, result, g_path)
    _compute_pct(result)
    return result


def _compute_pct(result: dict) -> None:
    aided = result.get("aided_count")
    total = result.get("n_total_intl")
    if aided and total and total > 0:
        result["pct_intl_aided"] = round(aided / total, 4)
    else:
        result["pct_intl_aided"] = None


def _apply_sanity_and_fallback(unitid: str, result: dict, context_path) -> None:
    """Flag implausible values; clear them so LLM fallback can be triggered."""
    pct = None
    if result.get("aided_count") and result.get("n_total_intl"):
        pct = result["aided_count"] / result["n_total_intl"]
    avg = result.get("avg_award")
    cost = result.get("cds_total_cost")

    if pct is not None and not (0 < pct <= 1.01):
        result["notes"] += f" pct={pct:.3f} out of range"
        result["aided_count"] = None
    if avg is not None and cost is not None and avg > cost:
        result["notes"] += " avg_award > cost (implausible)"


# ── Ground-truth loader ────────────────────────────────────────────────────────

def load_ground_truth() -> dict[str, dict]:
    gt: dict[str, dict] = {}
    with open(GT_PATH) as f:
        for row in csv.DictReader(f):
            gt[row["unitid"]] = row
    return gt


# ── Accuracy measurement ───────────────────────────────────────────────────────

def _pct_diff(extracted: Optional[float], gt: Optional[float]) -> Optional[float]:
    if extracted is None or gt is None or gt == 0:
        return None
    return abs(extracted - gt) / abs(gt)


def grade(extracted, gt, tol=0.02) -> str:
    """exact / close / wrong / missing / n/a."""
    if gt is None:
        return "n/a"
    if extracted is None:
        return "missing"
    diff = _pct_diff(float(extracted), float(gt))
    if diff is None:
        return "missing"
    if diff <= 0.002:
        return "exact"
    if diff <= tol:
        return "close"
    return "wrong"


_HELD_OUT_SEED = 42
_HELD_OUT_N    = 10

# Schools whose PDF content was opened / examined during development.
# They must not appear in held-out (which must stay unseen until final eval).
_INSPECTED_UIDS = {
    "117946",  # LMU
    "164739",  # Bentley
    "164988",  # BU
    "166027",  # Harvard
    "167358",  # Northeastern
    "193900",  # NYU
    "198419",  # Duke
    "201645",  # CWRU
    "212054",  # Drexel
}


def split_gt_uids() -> tuple[list[str], list[str]]:
    """Return (tune_uids, heldout_uids) sorted, deterministic (seed=42).
    - quality != 'ok' rows are excluded entirely.
    - Inspected schools can only appear in tune, never held-out.
    """
    import random
    gt = load_ground_truth()
    eligible_all = sorted(
        uid for uid, row in gt.items()
        if uid in SCHOOL_CONFIG and row.get("quality", "ok").strip() == "ok"
    )
    # Held-out pool: never-inspected only
    heldout_pool = [u for u in eligible_all if u not in _INSPECTED_UIDS]
    n_heldout = min(_HELD_OUT_N, len(heldout_pool))
    rng = random.Random(_HELD_OUT_SEED)
    heldout = sorted(rng.sample(heldout_pool, n_heldout))
    tune = sorted(u for u in eligible_all if u not in set(heldout))
    return tune, heldout


def _run_accuracy(uid_subset: list[str], label: str) -> None:
    """Print accuracy table for the given uid subset."""
    from collections import defaultdict

    gt = load_ground_truth()
    counts: dict[str, dict[str, int]] = {
        f: defaultdict(int) for f in ["pct", "avg", "cost"]
    }
    rows = []

    for uid in uid_subset:
        gt_row = gt[uid]
        gt_pct  = float(gt_row["pct_intl_aided"]) if gt_row.get("pct_intl_aided") else None
        gt_avg  = float(gt_row["avg_intl_award"]) if gt_row.get("avg_intl_award") else None
        gt_cost = float(gt_row["cds_total_cost"]) if gt_row.get("cds_total_cost") else None

        ext = extract_school(uid)

        g_pct  = grade(ext.get("pct_intl_aided"), gt_pct)
        g_avg  = grade(ext.get("avg_award"), gt_avg)
        g_cost = grade(ext.get("cds_total_cost"), gt_cost)

        rows.append({
            "uid": uid,
            "name": SCHOOL_CONFIG[uid]["name"][:28],
            "pct": g_pct,
            "avg": g_avg,
            "cost": g_cost,
            "fallback": ",".join(ext.get("fallback_fields", [])),
            "notes": ext.get("notes", "").strip(),
        })

        for field, g in [("pct", g_pct), ("avg", g_avg), ("cost", g_cost)]:
            counts[field][g] += 1

    print(f"\n=== {label} (n={len(rows)}) ===")
    hdr = f"{'uid':>8}  {'name':<28}  {'pct':>7}  {'avg':>7}  {'cost':>7}  notes"
    print(hdr)
    print("-" * len(hdr))
    for r in rows:
        pct_str  = f"{r['pct']:<7}" if r["pct"] != "n/a" else "  n/a  "
        avg_str  = f"{r['avg']:<7}" if r["avg"] != "n/a" else "  n/a  "
        cost_str = f"{r['cost']:<7}" if r["cost"] != "n/a" else "  n/a  "
        print(f"{r['uid']:>8}  {r['name']:<28}  {pct_str}  {avg_str}  {cost_str}  {r['notes'][:40]}")

    print()
    print(f"{'Field':<8}  {'exact':>6}  {'close':>6}  {'wrong':>6}  {'missing':>8}  {'n/a':>4}  {'exact%':>7}")
    for field in ["pct", "avg", "cost"]:
        c = counts[field]
        eligible = c["exact"] + c["close"] + c["wrong"] + c["missing"]
        exact_pct = f"{100*c['exact']/eligible:.0f}%" if eligible else "—"
        print(f"{field:<8}  {c['exact']:>6}  {c['close']:>6}  {c['wrong']:>6}  {c['missing']:>8}  {c.get('n/a',0):>4}  {exact_pct:>7}")

    return counts


def measure_accuracy(split: str = "tune") -> None:
    """Print accuracy table. split='tune'|'heldout'|'both'."""
    tune, heldout = split_gt_uids()
    if split == "tune":
        _run_accuracy(tune, "TUNING SET")
    elif split == "heldout":
        _run_accuracy(heldout, "HELD-OUT SET")
    else:  # both
        _run_accuracy(tune, "TUNING SET")
        _run_accuracy(heldout, "HELD-OUT SET")

    if _LLM_LOG:
        print(f"\nLLM fallback triggered {len(_LLM_LOG)} times:")
        for entry in _LLM_LOG:
            print(f"  unitid={entry['unitid']}  field={entry['field']}")


# ── Download missing files ─────────────────────────────────────────────────────

def download_missing() -> None:
    for uid, cfg in SCHOOL_CONFIG.items():
        files = cfg["files"]
        key = "xlsx" if "xlsx" in files else "all"
        if key not in files:
            continue
        path = CACHE / files[key]
        if path.exists():
            continue
        url = cfg.get("source_url", "")
        if not url or "cloudflare" in url.lower():
            print(f"SKIP {uid} {cfg['name']} — no direct URL")
            continue
        print(f"Downloading {uid} {cfg['name']} …", end=" ", flush=True)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                path.write_bytes(r.read())
            print(f"OK ({path.stat().st_size//1024}K)")
        except Exception as e:
            print(f"FAILED: {e}")


# ── CLI ────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--unitid", help="Extract one school")
    parser.add_argument("--measure", action="store_true", help="Accuracy table on tuning set")
    parser.add_argument("--held-out", action="store_true", help="Accuracy table on held-out set")
    parser.add_argument("--both", action="store_true", help="Accuracy tables for both splits")
    parser.add_argument("--show-split", action="store_true", help="Print tune/heldout uid lists")
    parser.add_argument("--download", action="store_true", help="Download missing files")
    args = parser.parse_args()

    if args.download:
        download_missing()
        return

    if args.show_split:
        tune, heldout = split_gt_uids()
        print("TUNE:", tune)
        print("HELD-OUT:", heldout)
        return

    if args.both:
        measure_accuracy("both")
        return

    if getattr(args, "held_out", False):
        measure_accuracy("heldout")
        return

    if args.measure:
        measure_accuracy("tune")
        return

    if args.unitid:
        r = extract_school(args.unitid)
        for k, v in r.items():
            print(f"  {k}: {v}")
        return

    # Default: process all
    print("unitid,name,aided_count,n_total_intl,pct_intl_aided,avg_award,cds_total_cost,year,fallback_fields,notes")
    for uid in sorted(SCHOOL_CONFIG):
        r = extract_school(uid)
        print(",".join(str(r.get(k, "")) for k in [
            "unitid", "name", "aided_count", "n_total_intl", "pct_intl_aided",
            "avg_award", "cds_total_cost", "year", "fallback_fields", "notes"
        ]))


if __name__ == "__main__":
    main()
