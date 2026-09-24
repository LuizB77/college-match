"""
extract_sevp.py

Extract the SEVP Certified School List from data/raw/sevp/certified-school-list-09-23-26.pdf.

The PDF has no table structure; data is rendered as fixed-layout text.
Column boundaries are derived from the x-positions of the header row words.
Four recovery passes handle common PDF encoding artifacts:

  1. footer        -- skip "Page N of 253" pagination rows
  2. state_split   -- state field absorbed the campus code
                      e.g. "HI HHW214F00151000" → state="HI", code="HHW214F00151000"
  3. char_recovery -- F/M flag chars merged into the preceding campus_name word
                      e.g. "MedicineY" = "Medicine" + F-flag "Y"
  4. state_recovery-- state code bled into the end of the city text
                      e.g. "Amelia Court HouseVA" → city="Amelia Court House", state="VA"

Output: data/raw/sevp/sevp_certified_schools.csv
Columns: school_name, campus_name, f_visa, m_visa, city, state, campus_code, parse_fix
"""

import re
import csv
import random
import statistics
import pathlib
import pdfplumber

PDF_PATH = pathlib.Path("data/raw/sevp/certified-school-list-09-23-26.pdf")
OUT_PATH  = pathlib.Path("data/raw/sevp/sevp_certified_schools.csv")

# ── Validation patterns ───────────────────────────────────────────────────────

# Campus code: 3 uppercase letters + 3 digits + 1 uppercase letter + 8 digits
# Example: SFR214F01777000
CAMPUS_CODE_RE = re.compile(r"^[A-Z]{3}\d{3}[A-Z]\d{8}$")

# State field that absorbed the campus code: "CA LOS214F16740000"
# Group 1 = 2-letter state, Group 2 = campus code
STATE_CODE_BLEED_RE = re.compile(r"^([A-Z]{2}) ([A-Z]{3}\d{3}[A-Z]\d{8})$")

# ── Header / title detection ──────────────────────────────────────────────────

HEADER_REQUIRED = {"SCHOOL", "CAMPUS", "CITY", "ST", "CODE"}

def is_header_row(words):
    return HEADER_REQUIRED.issubset({w["text"] for w in words})

def is_title_row(words):
    joined = " ".join(w["text"] for w in words)
    return "SEVP" in joined or "Certified Schools" in joined or "September" in joined

def is_footer_row(parsed):
    # "Page N of 253" appears at the bottom of each page
    return "Page" in (parsed.get("campus_name") or "")

# ── Word grouping ─────────────────────────────────────────────────────────────

def group_words_into_rows(words, y_tolerance=3):
    """Group extract_words() output into rows by proximity of top y-coordinate."""
    if not words:
        return []
    words_sorted = sorted(words, key=lambda w: (w["top"], w["x0"]))
    rows = []
    current_row = [words_sorted[0]]
    current_top = words_sorted[0]["top"]
    for w in words_sorted[1:]:
        if abs(w["top"] - current_top) <= y_tolerance:
            current_row.append(w)
        else:
            rows.append(sorted(current_row, key=lambda x: x["x0"]))
            current_row = [w]
            current_top = w["top"]
    rows.append(sorted(current_row, key=lambda x: x["x0"]))
    return rows

# ── Column boundary extraction ────────────────────────────────────────────────

def extract_column_boundaries(header_words):
    """
    Return {column_name: x0} from the header row.
    Two "CAMPUS" tokens appear: first anchors campus_name, second anchors campus_code.
    """
    sorted_words = sorted(header_words, key=lambda w: w["x0"])
    tokens       = [(w["text"], w["x0"]) for w in sorted_words]
    campus_xs    = [x for t, x in tokens if t == "CAMPUS"]
    return {
        "school_name": next((x for t, x in tokens if t == "SCHOOL"),       None),
        "campus_name": campus_xs[0] if len(campus_xs) >= 1               else None,
        "F":           next((x for t, x in tokens if t == "F"),            None),
        "M":           next((x for t, x in tokens if t == "M"),            None),
        "city":        next((x for t, x in tokens if t == "CITY"),         None),
        "state":       next((x for t, x in tokens if t == "ST"),           None),
        "campus_code": campus_xs[1] if len(campus_xs) >= 2               else None,
    }

# ── Word → column assignment ──────────────────────────────────────────────────

def assign_column(x0, boundaries):
    """
    Return the column whose left boundary is the largest value ≤ (x0 + 8pt).
    The 8pt tolerance accounts for data chars sitting ~6pt left of their header.
    """
    ordered = sorted(
        ((col, bx) for col, bx in boundaries.items() if bx is not None),
        key=lambda cb: cb[1],
    )
    assigned = None
    for col, bx in ordered:
        if x0 >= bx - 8:
            assigned = col
    return assigned

def parse_row(row_words, boundaries):
    """Assign each word to its column; join multi-word values with spaces."""
    cols = {k: [] for k in boundaries}
    for w in row_words:
        col = assign_column(w["x0"], boundaries)
        if col is not None:
            cols[col].append(w["text"])
    return {col: " ".join(words) for col, words in cols.items()}

# ── Row validation ────────────────────────────────────────────────────────────

def validate_row(row):
    """Return (True, None) if valid; (False, reason) otherwise."""
    f  = row.get("F", "").strip()
    m  = row.get("M", "").strip()
    st = row.get("state", "").strip()
    cd = row.get("campus_code", "").strip()
    if f not in ("Y", "N"):
        return False, f"F='{f}' not Y/N"
    if m not in ("Y", "N"):
        return False, f"M='{m}' not Y/N"
    if not (len(st) == 2 and st.isupper() and st.isalpha()):
        return False, f"state='{st}' not 2 uppercase letters"
    if not CAMPUS_CODE_RE.match(cd):
        return False, f"campus_code='{cd}' does not match pattern"
    return True, None

# ── Char-level column position learning ──────────────────────────────────────
#
# F/M flags: in this PDF, pdfplumber renders Y and N flag characters at
# fixed x-positions across all pages. Two variants exist (0.72pt apart)
# caused by the character width difference between 'Y' and 'N'.
#   F: x0 = 390.72 (for "Y") or 390.00 (for "N")  → median ≈ 390.72
#   M: x0 = 405.12 (for "N") or 405.84 (for "Y")  → median ≈ 405.12
# ±1.5pt tolerance captures both variants reliably.
#
# State column: from header, ST x0 ≈ 492.8. Actual first-char positions
# observed at x0 ≈ 490.4–493.2 (median ≈ 492). A −3pt left tolerance
# gives a state zone starting at ≈489, which cleanly separates state chars
# from city chars (city ends ≤ 487 in every observed row).

F_POS_INIT     = 390.72
M_POS_INIT     = 405.12
STATE_POS_INIT = 492.0   # from char-level observation; header is at 492.8
FLAG_TOL       = 1.5
STATE_LEFT_TOL = 3       # state zone starts state_pos() - STATE_LEFT_TOL

_f_samples:     list = []
_m_samples:     list = []
_state_samples: list = []

def collect_positions_from_page(page_chars):
    """
    Scan a page's chars for F/M flag and state-column chars.
    Called once per page. Collection stops at 200 samples each (stable median).
    """
    for c in page_chars:
        t = c["text"]
        x = c["x0"]
        # F flag: Y or N near the F column
        if len(_f_samples) < 200 and t in ("Y", "N") and abs(x - F_POS_INIT) <= 3.0:
            _f_samples.append(x)
        # M flag: Y or N near the M column
        elif len(_m_samples) < 200 and t in ("Y", "N") and abs(x - M_POS_INIT) <= 3.0:
            _m_samples.append(x)
        # State first char: any uppercase letter within ±2pt of STATE_POS_INIT
        # (narrow window avoids nearby city chars, which end ≤ 487)
        elif len(_state_samples) < 200 and t.isalpha() and t.isupper() and abs(x - STATE_POS_INIT) <= 2.0:
            _state_samples.append(x)

def f_pos():
    return statistics.median(_f_samples)     if len(_f_samples)     >= 5 else F_POS_INIT
def m_pos():
    return statistics.median(_m_samples)     if len(_m_samples)     >= 5 else M_POS_INIT
def state_pos():
    return statistics.median(_state_samples) if len(_state_samples) >= 5 else STATE_POS_INIT

# ── Char-level text reconstruction ───────────────────────────────────────────

def chars_to_text(chars):
    """
    Concatenate char dicts sorted by x0.
    In this PDF, word spacing is encoded as explicit space characters in the
    char stream, so sorting by x0 and joining gives the correct string.
    """
    if not chars:
        return ""
    return "".join(c["text"] for c in sorted(chars, key=lambda c: c["x0"])).strip()

# ── Fix 3: char-level F/M flag recovery ──────────────────────────────────────

def attempt_char_recovery(row_words, page_chars, boundaries):
    """
    Recover campus_name, F, and M when pdfplumber merged a flag char into a
    campus_name word (e.g. "MedicineY" = "Medicine" + F-flag "Y").

    Strategy:
      - Find the Y/N char at x0 ≈ f_pos() → F value; same for m_pos() → M value
      - Rebuild campus_name from all chars in [campus_name_x, city_x), minus flags
      - Keep school_name, city, state, campus_code from the word-level parse

    Returns a row dict, or None if either flag cannot be located.
    """
    if not row_words:
        return None

    row_top    = min(w["top"] for w in row_words) - 2
    row_bottom = max(w.get("bottom", w["top"] + 12) for w in row_words) + 2

    # Include space chars (encoded explicitly in this PDF)
    row_chars = [c for c in page_chars
                 if row_top <= c["top"] <= row_bottom and c["text"] != ""]
    if not row_chars:
        return None

    fp, mp = f_pos(), m_pos()

    f_cands = [c for c in row_chars if abs(c["x0"] - fp) <= FLAG_TOL and c["text"] in ("Y", "N")]
    m_cands = [c for c in row_chars if abs(c["x0"] - mp) <= FLAG_TOL and c["text"] in ("Y", "N")]

    if not f_cands or not m_cands:
        return None

    f_char, m_char = f_cands[0], m_cands[0]
    flag_ids = {id(f_char), id(m_char)}

    # campus_name zone: [campus_name_x, city_x) — this range spans the F/M
    # columns, so overflow chars that were merged into the name word are
    # naturally included; only the flag chars themselves are excluded.
    campus_x = boundaries.get("campus_name")
    city_x   = boundaries.get("city")
    if campus_x is None or city_x is None:
        return None

    campus_chars = [c for c in row_chars
                    if campus_x - 2 <= c["x0"] < city_x and id(c) not in flag_ids]

    word_parsed = parse_row(row_words, boundaries)
    return {
        "school_name": word_parsed["school_name"].strip(),
        "campus_name": chars_to_text(campus_chars),
        "F":           f_char["text"],
        "M":           m_char["text"],
        "city":        word_parsed["city"].strip(),
        "state":       word_parsed["state"].strip(),
        "campus_code": word_parsed["campus_code"].strip(),
    }

# ── Fix 4: state-column char recovery ────────────────────────────────────────

def attempt_state_recovery(row_words, page_chars, boundaries, base_row=None):
    """
    Recover city and state when the 2-letter state code bled into the city text
    (e.g. "Amelia Court HouseVA" → city="Amelia Court House", state="VA").

    State column position is learned from valid rows (median x0 of uppercase
    letter chars observed at the ST column position; same approach as F/M flags).
    State zone: [state_pos() − STATE_LEFT_TOL, campus_code_x − 8]
    From char-level inspection: state chars are at x0 ≈ 490–494; city chars
    end at x0 ≤ 487. A −3pt left tolerance gives a clean split at ≈489.

    Exactly 2 uppercase letter chars are expected in the state zone.
    City is rebuilt from all remaining chars in [city_x, leftmost_state_char_x0).

    base_row: if provided, use its campus_name / F / M / campus_code
              (allows chaining after char_recovery when only state/city failed).

    Returns a row dict, or None if exactly 2 state chars cannot be identified.
    """
    if not row_words:
        return None

    state_x  = boundaries.get("state")
    city_x   = boundaries.get("city")
    code_x   = boundaries.get("campus_code")
    if state_x is None or city_x is None:
        return None

    sp          = state_pos()
    state_left  = sp - STATE_LEFT_TOL
    # State zone ends where campus_code zone begins (with 8pt tolerance applied)
    state_right = (code_x - 8) if code_x is not None else (sp + 25)

    row_top    = min(w["top"] for w in row_words) - 2
    row_bottom = max(w.get("bottom", w["top"] + 12) for w in row_words) + 2

    row_chars = [c for c in page_chars
                 if row_top <= c["top"] <= row_bottom and c["text"] != ""]
    if not row_chars:
        return None

    # State chars: uppercase letters in the state zone, sorted by x0
    state_zone = sorted(
        [c for c in row_chars
         if state_left <= c["x0"] <= state_right
         and c["text"].isalpha() and c["text"].isupper()],
        key=lambda c: c["x0"],
    )

    if len(state_zone) < 2:
        return None  # fewer than 2 uppercase chars in zone → can't recover

    # Take the 2 rightmost uppercase chars — the state code is always the
    # rightmost pair before campus_code, even if an additional uppercase
    # city char (e.g. the 'S' of "SPRINGS") falls in the left part of the zone
    state_chars = state_zone[-2:]
    state_str   = "".join(c["text"] for c in state_chars)

    # City chars: everything to the left of the leftmost state char (in city zone)
    split_x      = state_chars[0]["x0"]
    state_ids    = {id(c) for c in state_chars}
    city_chars   = [c for c in row_chars
                    if city_x - 2 <= c["x0"] < split_x and id(c) not in state_ids]
    city_str     = chars_to_text(city_chars)

    # Use base_row for fields already correctly recovered by char_recovery;
    # fall back to word-level parse if base_row not provided
    if base_row is not None:
        school_name = base_row["school_name"]
        campus_name = base_row["campus_name"]
        f_val       = base_row["F"]
        m_val       = base_row["M"]
        campus_code = base_row["campus_code"]
    else:
        wp          = parse_row(row_words, boundaries)
        school_name = wp["school_name"].strip()
        campus_name = wp["campus_name"].strip()
        f_val       = wp["F"].strip()
        m_val       = wp["M"].strip()
        campus_code = wp["campus_code"].strip()

    return {
        "school_name": school_name,
        "campus_name": campus_name,
        "F":           f_val,
        "M":           m_val,
        "city":        city_str,
        "state":       state_str,
        "campus_code": campus_code,
    }

# ── Output row builder ────────────────────────────────────────────────────────

def make_output_row(parsed, fix):
    return {
        "school_name": parsed["school_name"].strip(),
        "campus_name": parsed["campus_name"].strip(),
        "f_visa":      parsed["F"].strip(),
        "m_visa":      parsed["M"].strip(),
        "city":        parsed["city"].strip(),
        "state":       parsed["state"].strip(),
        "campus_code": parsed["campus_code"].strip(),
        "parse_fix":   fix,
    }

# ── Main extraction loop ──────────────────────────────────────────────────────

valid_rows   = []
invalid_rows = []   # (page_num, raw_text, reason)

fix_counts = {
    "none":           0,
    "footer":         0,
    "state_split":    0,
    "char_recovery":  0,
    "state_recovery": 0,
}

current_boundaries = None

print(f"Opening {PDF_PATH} ...")

with pdfplumber.open(PDF_PATH) as pdf:
    total_pages = len(pdf.pages)
    print(f"Total pages: {total_pages}")

    for page_num, page in enumerate(pdf.pages, start=1):
        words = page.extract_words(keep_blank_chars=False, extra_attrs=["top"])
        if not words:
            continue

        # Load chars once per page; used for position learning and all recoveries
        page_chars = page.chars
        collect_positions_from_page(page_chars)

        rows = group_words_into_rows(words, y_tolerance=3)

        for row_words in rows:

            # ── Skip PDF title lines ───────────────────────────────────────
            if is_title_row(row_words):
                continue

            # ── Detect header; update column boundaries ────────────────────
            if is_header_row(row_words):
                current_boundaries = extract_column_boundaries(row_words)
                continue

            if current_boundaries is None:
                continue

            # ── Word-level parse ───────────────────────────────────────────
            parsed = parse_row(row_words, current_boundaries)

            # ── Fix 1: footer rows ─────────────────────────────────────────
            if is_footer_row(parsed):
                fix_counts["footer"] += 1
                continue

            # ── Baseline validation ────────────────────────────────────────
            ok, reason = validate_row(parsed)
            if ok:
                valid_rows.append(make_output_row(parsed, "none"))
                fix_counts["none"] += 1
                continue

            before_raw = " | ".join(f"{k}={v}" for k, v in parsed.items())

            # ── Fix 2: state + code bleed ──────────────────────────────────
            # "HI HHW214F00151000" → state="HI", campus_code="HHW214F00151000"
            state_bleed = STATE_CODE_BLEED_RE.match(parsed.get("state", ""))
            if state_bleed:
                p2 = dict(parsed)
                p2["state"]       = state_bleed.group(1)
                p2["campus_code"] = state_bleed.group(2)
                ok2, _ = validate_row(p2)
                if ok2:
                    out = make_output_row(p2, "state_split")
                    valid_rows.append(out)
                    fix_counts["state_split"] += 1
                    continue
                # state_split alone didn't fix it; fall through

            # ── Fix 3: char-level F/M flag recovery ───────────────────────
            recovered = attempt_char_recovery(row_words, page_chars, current_boundaries)

            if recovered is not None:
                # Also apply state_split if the recovered row still has that bleed
                st2 = STATE_CODE_BLEED_RE.match(recovered.get("state", ""))
                if st2:
                    recovered["state"]       = st2.group(1)
                    recovered["campus_code"] = st2.group(2)

                ok3, reason3 = validate_row(recovered)
                if ok3:
                    valid_rows.append(make_output_row(recovered, "char_recovery"))
                    fix_counts["char_recovery"] += 1
                    continue

                # char_recovery fixed F/M but state/city still wrong →
                # try Fix 4 chained on the char-recovery result
                if "state" in reason3:
                    sr = attempt_state_recovery(
                        row_words, page_chars, current_boundaries, base_row=recovered
                    )
                    if sr is not None:
                        ok4, _ = validate_row(sr)
                        if ok4:
                            valid_rows.append(make_output_row(sr, "state_recovery"))
                            fix_counts["state_recovery"] += 1
                            continue

                # Still invalid after char_recovery (and state_recovery if tried)
                after_raw = " | ".join(f"{k}={v}" for k, v in recovered.items())
                invalid_rows.append((page_num, after_raw, f"after char_recovery: {reason3}"))
                continue

            # ── Fix 4 standalone: state/city bleed without F/M bleed ──────
            # char_recovery returned None (no flag bleed detected), but the
            # row might still have a city/state boundary bleed.
            sr_standalone = attempt_state_recovery(
                row_words, page_chars, current_boundaries, base_row=None
            )
            if sr_standalone is not None:
                ok5, _ = validate_row(sr_standalone)
                if ok5:
                    valid_rows.append(make_output_row(sr_standalone, "state_recovery"))
                    fix_counts["state_recovery"] += 1
                    continue

            # ── Still invalid after all fixes ──────────────────────────────
            invalid_rows.append((page_num, before_raw, reason))

# ── Save CSV ──────────────────────────────────────────────────────────────────

OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
FIELDNAMES = [
    "school_name", "campus_name", "f_visa", "m_visa",
    "city", "state", "campus_code", "parse_fix",
]

with open(OUT_PATH, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
    writer.writeheader()
    writer.writerows(valid_rows)

# ── Diagnostics ───────────────────────────────────────────────────────────────

from collections import Counter

print(f"\n=== Valid rows total and by parse_fix ===")
print(f"  Total valid rows saved: {len(valid_rows)}")
for fix in ("none", "state_split", "char_recovery", "state_recovery"):
    print(f"  {fix:20s}: {fix_counts[fix]}")
print(f"  footer (discarded)   : {fix_counts['footer']}")
print(f"  Still invalid        : {len(invalid_rows)}")

print(f"\n=== Learned column positions ===")
if _f_samples:
    print(f"  F  median={f_pos():.4f}  n={len(_f_samples)}  "
          f"range=[{min(_f_samples):.2f}, {max(_f_samples):.2f}]")
if _m_samples:
    print(f"  M  median={m_pos():.4f}  n={len(_m_samples)}  "
          f"range=[{min(_m_samples):.2f}, {max(_m_samples):.2f}]")
if _state_samples:
    print(f"  ST median={state_pos():.4f}  n={len(_state_samples)}  "
          f"range=[{min(_state_samples):.2f}, {max(_state_samples):.2f}]")

# 10 random recovered rows (parse_fix != "none")
recovered_all = [r for r in valid_rows if r["parse_fix"] != "none"]
rng = random.Random(42)
sample_10 = rng.sample(recovered_all, min(10, len(recovered_all)))

print(f"\n=== 10 random recovered rows (random_state=42) ===")
for r in sample_10:
    print(f"  {r['school_name']} | {r['campus_name']} | "
          f"{r['f_visa']} | {r['m_visa']} | {r['city']} | {r['state']} | {r['parse_fix']}")

# Still-invalid rows (all if < 20)
print(f"\n=== Still-invalid rows ({len(invalid_rows)} total) ===")
limit = len(invalid_rows) if len(invalid_rows) <= 20 else 20
for pg, raw, reason in invalid_rows[:limit]:
    print(f"\n  page={pg}  reason={reason}")
    print(f"  {raw}")
if len(invalid_rows) > 20:
    print(f"\n  ... and {len(invalid_rows) - 20} more")

print(f"\n=== F visa value_counts ===")
for val, count in sorted(Counter(r["f_visa"] for r in valid_rows).items()):
    print(f"  {val}: {count}")

print(f"\n=== M visa value_counts ===")
for val, count in sorted(Counter(r["m_visa"] for r in valid_rows).items()):
    print(f"  {val}: {count}")

print(f"\n=== Kansas (KS) rows: school_name or campus_name contains 'College' or 'University', sorted by school_name ===")
ks_edu = sorted(
    [r for r in valid_rows
     if r["state"] == "KS"
     and any(kw in r["school_name"] or kw in r["campus_name"]
             for kw in ("College", "University", "college", "university"))],
    key=lambda r: r["school_name"],
)
print(f"  ({len(ks_edu)} rows)")
for r in ks_edu:
    print(f"  {r['school_name']} | {r['campus_name']} | {r['city']}")
