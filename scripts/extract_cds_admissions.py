#!/usr/bin/env python3
"""
Extract admissions data from CDS PDF/XLSX files.
Outputs: data/manual/cds_admissions.csv
"""
import re
import csv
import os

import pdfplumber
import openpyxl

CACHE_DIR = '/Users/luizeduardodeomenabreda/Desktop/college-match/data/cds_cache'
OUT_CSV   = '/Users/luizeduardodeomenabreda/Desktop/college-match/data/manual/cds_admissions.csv'

SCHOOLS = [
    # unitid, cds_year, filenames (list), skip_cd (True = section-only file, no C/D)
    (109651, '2024-25', ['artcenter_109651_cds_2024-25.pdf'], False),
    (143084, '2025-26', ['augustana_143084_cds_2025-26.pdf'], False),
    (164580, '2025-26', ['babson_164580_cds_2025-26.pdf'], False),
    (189097, '2024-25', ['barnard_189097_cds_2024-25.pdf'], False),
    (164924, '2024-25', ['bc_164924_cds_2024-25.pdf'], False),
    (164739, '2023-24', ['bentley_164739_cds_2023-24.pdf'], False),
    (164748, '2025-26', ['berklee_164748_cds_2025-26.pdf'], False),
    (165015, '2025-26', ['brandeis_165015_cds_2025-26.pdf'], False),
    # BU: section PDFs B/G/H — no C or D sections
    (164988, '2025',   ['bu_164988_cds_2025_b.pdf', 'bu_164988_cds_2025_g.pdf', 'bu_164988_cds_2025_h.pdf'], True),
    (230038, '2025-26', ['byu_230038_cds_2025-26.pdf'], False),
    (169080, '2025-26', ['calvin_169080_cds_2025-26.pdf'], False),
    (201645, '2025-26', ['cwru_201645_cds_2025-26.pdf'], False),
    # DePaul: section B only
    (144740, '2025-26', ['depaul_b_144740_cds_2025-26.pdf'], True),
    # DePauw: section H only
    (150400, '2024-25', ['depauw_h_150400_cds_2024-25.pdf'], True),
    (212054, '2025-26', ['drexel_212054_cds_2025-26.pdf'], False),
    (139658, '2025-26', ['emory_139658_cds_2025-26.pdf'], False),
    # ERAU: HTML error file
    (133553, '2023-24', ['erau_133553_cds_2023-24.pdf'], True),
    # Georgetown: HTML Box file
    (131496, '2025-26', ['georgetown_131496_cds_2025-26.pdf'], True),
    (131469, '2025-26', ['gwu_131469_cds_2025-26.pdf'], False),
    (131520, '2024-25', ['howard_131520_cds_2024-25.pdf'], False),
    # JHU: both files are HTML error pages
    (162928, '2025-26', ['jhu_162928_cds_2025-26.pdf'], True),
    (117946, '2024-25', ['lmu_117946_cds_2024-25.pdf'], False),
    # Mt Holyoke: section PDFs B/G/H
    (166939, '2024-25', ['mtholyoke_b_166939_cds_2024-25.pdf', 'mtholyoke_g_166939_cds_2024-25.pdf', 'mtholyoke_h_166939_cds_2024-25.pdf'], True),
    (135726, '2025-26', ['miami_135726_cds_2025-26.pdf'], False),
    # ND: HTML 403
    (152080, '2024-25', ['nd_152080_cds_2024-25.pdf'], True),
    (167358, '2024-25', ['northeastern_167358_cds_2024-25.pdf'], False),
    (147767, '2025-26', ['northwestern_147767_cds_2025-26.pdf'], False),
    (193900, '2025-26', ['nyu_193900_cds_2025-26.pdf'], False),
    (227757, '2025-26', ['rice_227757_cds_2025-26.pdf'], False),
    (195003, '2024-25', ['rit_195003_cds_2024-25.pdf'], False),
    (195030, '2025-26', ['rochester_195030_cds_2025-26.pdf'], False),
    (122931, '2025-26', ['scu_122931_cds_2025-26.pdf'], False),
    (196413, '2025-26', ['syracuse_196413_cds_2025-26.pdf'], False),
    (228875, '2024-25', ['tcu_228875_cds_2024-25.pdf'], False),
    (168148, '2025-26', ['tufts_168148_cds_2025-26.pdf'], False),
    (144050, '2025-26', ['uchicago_144050_cds_2025-26.pdf'], False),
    (123961, '2025-26', ['usc_123961_cds_2025-26.pdf'], False),
    (122612, '2024-25', ['usf_122612_cds_2024-25.pdf'], False),
    (221999, '2024-25', ['vanderbilt_221999_cds_2024-25.xlsx'], False),
    (179867, '2025-26', ['washu_179867_cds_2025-26.pdf'], False),
]


def clean(t):
    return re.sub(r'\(cid:\d+\)', '', t or '')


def is_real_pdf(path):
    """Return False if file is HTML/error, True if a genuine PDF."""
    try:
        with open(path, 'rb') as f:
            header = f.read(5)
        return header == b'%PDF-'
    except Exception:
        return False


def extract_text_from_pdf(path):
    lines = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            raw = page.extract_text() or ''
            lines.extend(clean(raw).split('\n'))
    return lines


def parse_num(s):
    """Strip commas and parens from a number string."""
    return re.sub(r'[,\s\(\)]', '', str(s))


def normalize_date(raw):
    """
    Normalize date strings from CDS to a human-readable form.
    Handles: "1 15", "1/15", "12/16", "Jan 1st", "January 15",
             "1-Jan", "4-Jan", "15-Jan", "Jan 1st"
    """
    raw = raw.strip()
    if not raw:
        return ''

    months = {
        '1':'Jan','2':'Feb','3':'Mar','4':'Apr','5':'May','6':'Jun',
        '7':'Jul','8':'Aug','9':'Sep','10':'Oct','11':'Nov','12':'Dec',
    }
    month_names = {
        'jan':'Jan','feb':'Feb','mar':'Mar','apr':'Apr','may':'May','jun':'Jun',
        'jul':'Jul','aug':'Aug','sep':'Sep','oct':'Oct','nov':'Nov','dec':'Dec',
        'january':'Jan','february':'Feb','march':'Mar','april':'Apr',
        'june':'Jun','july':'Jul','august':'Aug','september':'Sep',
        'october':'Oct','november':'Nov','december':'Dec',
    }

    # Excel-style "D-Mon" like "1-Jan", "4-Jan", "15-Jan"
    m = re.match(r'^(\d{1,2})-([A-Za-z]{3,9})$', raw)
    if m:
        d = m.group(1)
        mon = month_names.get(m.group(2).lower(), m.group(2))
        return f"{mon} {d}"

    # "Mon-D" like "Jan-15"
    m = re.match(r'^([A-Za-z]{3,9})-(\d{1,2})$', raw)
    if m:
        mon = month_names.get(m.group(1).lower(), m.group(1))
        return f"{mon} {m.group(2)}"

    # Numeric "M D" or "M/D"
    m = re.match(r'^(\d{1,2})[/\s]+(\d{1,2})$', raw)
    if m:
        mon = months.get(m.group(1), m.group(1))
        return f"{mon} {m.group(2)}"

    # Text date "Jan 1st", "January 15", etc.
    m = re.match(r'^([A-Za-z]+)\s+(\d{1,2})', raw)
    if m:
        mon = month_names.get(m.group(1).lower(), m.group(1))
        return f"{mon} {m.group(2)}"

    # Pass through anything else
    return raw


# ─── PDF extraction ──────────────────────────────────────────────────────────

def extract_from_lines(lines):
    """
    Returns dict: app_fee, app_fee_waiver, rd_deadline,
                  transfer_applicants, transfer_admitted, transfer_enrolled
    """
    result = {
        'app_fee': '', 'app_fee_waiver': '',
        'rd_deadline': '',
        'transfer_applicants': '', 'transfer_admitted': '', 'transfer_enrolled': '',
    }

    # ── Application fee (C13) ────────────────────────────────────────────────
    # Multiple C13 label formats encountered:
    #   "C13.Application fee", "C13 Application Fee", "C13 C13-C20: Admission Policies\nApplicationFee"
    #   "C1301 Does your institution have an application fee?"
    c13_idx = None
    for i, line in enumerate(lines):
        if (re.search(r'C13[\s\.\-].*Application\s*Fee', line, re.I)
                or re.search(r'C13[\s\.]?Application\s*fee', line, re.I)
                or re.match(r'C1301\b', line)
                # Drexel: "C13 C13-C20: Admission Policies" followed by "ApplicationFee" next line
                or (re.match(r'^C13\b', line) and i+1 < len(lines)
                    and re.match(r'^Application\s*Fee', lines[i+1], re.I))):
            c13_idx = i
            break

    if c13_idx is not None:
        i = c13_idx
        # Search within next 30 lines for amount
        for j in range(i, min(i+30, len(lines))):
            l = lines[j]
            # "Amount of application fee: $XX" or "Amount of application fee: XX"
            m = re.search(r'Amount\s*of\s*application\s*fee[:\s]+\$?([\d,]+(?:\.\d+)?)', l, re.I)
            if m:
                try:
                    result['app_fee'] = str(int(float(m.group(1).replace(',', ''))))
                except Exception:
                    result['app_fee'] = m.group(1)
                break
            # "C1302 Amount of application fee: $75"
            m = re.search(r'C1302.*Amount.*fee[:\s]+\$?([\d,]+(?:\.\d+)?)', l, re.I)
            if m:
                try:
                    result['app_fee'] = str(int(float(m.group(1).replace(',', ''))))
                except Exception:
                    result['app_fee'] = m.group(1)
                break
            # Label alone, value on next line: "Amountofapplicationfee:"
            m2 = re.search(r'Amount\s*of\s*application\s*fee\s*:?\s*$', l, re.I)
            if m2 and j+1 < len(lines):
                next_l = lines[j+1]
                m3 = re.search(r'^\$?([\d,]+(?:\.\d+)?)$', next_l.strip())
                if m3:
                    try:
                        result['app_fee'] = str(int(float(m3.group(1).replace(',', ''))))
                    except Exception:
                        result['app_fee'] = m3.group(1)
                    break

        # Waiver: "Can it be waived for applicants with financial need?"
        for j in range(i, min(i+30, len(lines))):
            l = lines[j]
            if re.search(r'Can it be waived for applicants with financial need', l, re.I):
                # Extract what comes after the label on the same line
                after = re.sub(r'Can it be waived for applicants with financial need[\?\s:]*', '', l, flags=re.I).strip()

                # Pattern 1: "✓ Yes" / "4 Yes" / "Yes" alone (no "No")
                if re.search(r'[✓4✔✗]\s*Yes', after):
                    result['app_fee_waiver'] = 'Yes'
                elif re.search(r'[✓4✔✗]\s*No', after):
                    result['app_fee_waiver'] = 'No'
                elif re.match(r'^Y\b', after):
                    result['app_fee_waiver'] = 'Yes'
                elif re.match(r'^N\b', after):
                    result['app_fee_waiver'] = 'No'
                elif re.search(r'\bYes\b', after) and not re.search(r'\bNo\b', after):
                    result['app_fee_waiver'] = 'Yes'
                elif re.search(r'\bx\b', after, re.I):
                    result['app_fee_waiver'] = 'Yes'
                else:
                    # Check next 1-4 lines for marker
                    for k in range(j+1, min(j+5, len(lines))):
                        nxt = lines[k].strip()
                        # Standalone X or checkmark
                        if re.match(r'^[Xx✓4✔]$', nxt):
                            result['app_fee_waiver'] = 'Yes'
                            break
                        # "C1303 Can it be waived ... Y"
                        m3 = re.search(r'C1303.*([YN])\s*$', nxt)
                        if m3:
                            result['app_fee_waiver'] = 'Yes' if m3.group(1) == 'Y' else 'No'
                            break
                        # "Yes" alone
                        if re.match(r'^Yes\b', nxt, re.I) and not re.search(r'No', nxt):
                            result['app_fee_waiver'] = 'Yes'
                            break
                break

    # ── RD deadline (C14) ───────────────────────────────────────────────────
    # Check if "No" is the answer to closing date before extracting date
    c14_idx = None
    for i, line in enumerate(lines):
        if re.search(r'C14[\s\.\-].*Application\s*closing\s*date', line, re.I):
            c14_idx = i
            break

    if c14_idx is not None:
        i = c14_idx
        # Check whether the school answered "No" to having a closing date
        closing_date_no = False
        for j in range(i, min(i+5, len(lines))):
            l = lines[j]
            # Handles both spaced and concatenated forms:
            # "Does your institution have an application closing date?"
            # "Doesyourinstitutionhaveanapplicationclosingdate?"
            if re.search(r'Does\s*your\s*institution\s*have\s*an\s*application\s*closing\s*date', l, re.I):
                after = re.sub(r'Does\s*your\s*institution\s*have\s*an\s*application\s*closing\s*date[\?\s]*', '', l, flags=re.I).strip()
                # "Yes 4 No" or "✓ No" → No is checked (school has no deadline)
                if re.search(r'[✓4✔]\s*No', after):
                    closing_date_no = True
                elif re.search(r'[✓4✔]\s*Yes', after):
                    closing_date_no = False
                elif re.match(r'^Yes\b', after, re.I):
                    closing_date_no = False
                elif re.match(r'^Y', after):
                    # Drexel: "YResponse 'Y' or 'N'" — Y = Yes
                    closing_date_no = False
                # If "Yes No" both present without clear marker, assume has closing date
                break

        if not closing_date_no:
            for j in range(i, min(i+20, len(lines))):
                l = lines[j]
                # Handle both spaced "Application closing date (fall)" and
                # concatenated "Applicationclosingdate(fall)"
                m = re.search(r'Application\s*closing\s*date\s*\(fall\)\s*:?\s*(.*)', l, re.I)
                if m:
                    raw = m.group(1).strip().lstrip(':').strip()
                    if raw and not re.match(r'^[YN]$', raw):  # skip bare Y/N answers
                        result['rd_deadline'] = normalize_date(raw)
                    break
                # Barnard format: "C1402 Application closing date (fall) Y"
                m2 = re.search(r'C1402\s+Application closing date.*', l, re.I)
                if m2:
                    break

    # ── Transfer data (D2) ──────────────────────────────────────────────────
    d2_idx = None
    for i, line in enumerate(lines):
        # Match: "D2" alone, "D2." or "D2 Provide..." or "D2. Provide..."
        # Also Barnard-style "D201 Men" (numbered items within D2 subsection)
        if (re.match(r'^D2[\s\.\:\-]?$', line.strip())
                or re.match(r'^D2[\s\.]', line.strip())
                or re.match(r'^D201\b', line.strip())):
            d2_idx = i
            break

    if d2_idx is not None:
        i = d2_idx
        # Strategy 1: Single table with Applicants/Admitted/Enrolled columns
        # Look for "Total X Y Z" within next 30 lines
        total_found = False
        for j in range(i, min(i+35, len(lines))):
            l = lines[j]
            # "Total 288 226 98" or "Total (1,956) (1,077) (274)" or "Total 2,229 1,394 1,187"
            m = re.match(r'^Total\s+[\(\s]*([,\d]+)[\)\s]+[\(\s]*([,\d]+)[\)\s]+[\(\s]*([,\d]+)', l, re.I)
            if m:
                result['transfer_applicants'] = parse_num(m.group(1))
                result['transfer_admitted']    = parse_num(m.group(2))
                result['transfer_enrolled']    = parse_num(m.group(3))
                total_found = True
                break

        if not total_found:
            # Strategy 2: Drexel-style — 3 separate sub-tables
            # Look for 3 consecutive "Total N" lines (each with a single number)
            totals = []
            for j in range(i, min(i+60, len(lines))):
                l = lines[j]
                m = re.match(r'^Total\s+([\d,]+)\s*$', l.strip())
                if m:
                    totals.append(parse_num(m.group(1)))
                if len(totals) == 3:
                    result['transfer_applicants'] = totals[0]
                    result['transfer_admitted']    = totals[1]
                    result['transfer_enrolled']    = totals[2]
                    break

        if not total_found and not result['transfer_applicants']:
            # Strategy 2b: Calvin-style — last data row has 3 numbers without "Total" label
            # Look for a row with exactly 3 comma-free numbers after the header
            # (within D2 section, before D3)
            for j in range(i+1, min(i+30, len(lines))):
                l = lines[j]
                # Stop at next section
                if re.match(r'^D3[\s\.]', l.strip()):
                    break
                # Line with just numbers separated by spaces (possibly leading whitespace)
                m = re.match(r'^\s*([\d,]+)\s+([\d,]+)\s+([\d,]+)\s*$', l)
                if m:
                    # Keep this as candidate (last one wins = Total row)
                    candidate = (parse_num(m.group(1)), parse_num(m.group(2)), parse_num(m.group(3)))
            try:
                if candidate[0]:
                    result['transfer_applicants'] = candidate[0]
                    result['transfer_admitted']    = candidate[1]
                    result['transfer_enrolled']    = candidate[2]
            except Exception:
                pass

        if not (result['transfer_applicants']):
            # Strategy 3: Barnard-style — D205/D210/D215 labeled rows
            # "D205 Total 1253"
            totals3 = []
            for j in range(i, min(i+80, len(lines))):
                l = lines[j]
                m = re.match(r'^D\d{3}\s+Total\s+([\d,]+)', l)
                if m:
                    totals3.append(parse_num(m.group(1)))
                if len(totals3) == 3:
                    result['transfer_applicants'] = totals3[0]
                    result['transfer_admitted']    = totals3[1]
                    result['transfer_enrolled']    = totals3[2]
                    break

    return result


# ─── XLSX extraction (Vanderbilt) ───────────────────────────────────────────

def extract_from_xlsx(path):
    result = {
        'app_fee': '', 'app_fee_waiver': '',
        'rd_deadline': '',
        'transfer_applicants': '', 'transfer_admitted': '', 'transfer_enrolled': '',
    }

    wb = openpyxl.load_workbook(path, data_only=True)

    # ── C sheet ──
    c_sheet = None
    for name in wb.sheetnames:
        if re.search(r'CDS-C|^C$', name.strip()):
            c_sheet = wb[name]
            break

    if c_sheet:
        rows = list(c_sheet.iter_rows(values_only=True))
        for idx, row in enumerate(rows):
            row_str = ' '.join(str(v) for v in row if v is not None)

            # Application fee amount
            if re.search(r'Amount of application fee', row_str, re.I):
                for v in row:
                    if isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0:
                        result['app_fee'] = str(int(v))
                        break
                    if isinstance(v, str):
                        m = re.match(r'^\$?([\d,]+(?:\.\d+)?)$', v.strip())
                        if m:
                            try:
                                result['app_fee'] = str(int(float(m.group(1).replace(',', ''))))
                            except Exception:
                                result['app_fee'] = m.group(1)
                            break

            # Waiver
            if re.search(r'Can it be waived for applicants with financial need', row_str, re.I):
                # In Vanderbilt XLSX: row has ('Can it be waived...', None, ..., 'X', None, ...)
                # X appears in the 'Yes' column (typically col D index ~3-4, before 'No' col)
                # Check if X appears before encountering the word 'No'
                vals_non_none = [(i, v) for i, v in enumerate(row) if v is not None]
                found_x_before_no = False
                for pos, v in vals_non_none:
                    if str(v) == 'X':
                        found_x_before_no = True
                        break
                    if str(v) == 'No':
                        break
                if found_x_before_no:
                    result['app_fee_waiver'] = 'Yes'

            # RD deadline
            if re.search(r'Application closing date \(fall\)', row_str, re.I):
                for v in row:
                    if v and not re.search(r'Application closing date', str(v), re.I):
                        s = str(v).strip()
                        if s and s not in ('None',):
                            result['rd_deadline'] = normalize_date(s)
                            break

    # ── D sheet ──
    d_sheet = None
    for name in wb.sheetnames:
        if re.search(r'CDS-D|^D$', name.strip()):
            d_sheet = wb[name]
            break

    if d_sheet:
        rows = list(d_sheet.iter_rows(values_only=True))
        for idx, row in enumerate(rows):
            # Total row: may have None as first cell, "Total" somewhere, then numbers
            row_vals = [v for v in row if v is not None]
            is_total_row = any(v == 'Total' or (isinstance(v, str) and v.strip() == 'Total')
                               for v in row_vals)
            if is_total_row:
                # Collect numeric values from the row (after "Total" label)
                nums = []
                past_total = False
                for v in row:
                    if v == 'Total' or (isinstance(v, str) and v.strip() == 'Total'):
                        past_total = True
                        continue
                    if past_total and isinstance(v, (int, float)) and not isinstance(v, bool):
                        nums.append(int(v))
                    elif past_total and isinstance(v, str) and re.match(r'^=SUM', v):
                        # Formula not resolved; sum gender rows above
                        pass
                if len(nums) >= 3:
                    result['transfer_applicants'] = str(nums[0])
                    result['transfer_admitted']    = str(nums[1])
                    result['transfer_enrolled']    = str(nums[2])
                    break
                elif len(nums) == 0:
                    # Sum from gender rows above (Men, Women, Another Gender, Unknown)
                    app_sum, adm_sum, enr_sum = 0, 0, 0
                    for k in range(max(0, idx-6), idx):
                        mrow = rows[k]
                        mvals = [v for v in mrow if isinstance(v, (int, float)) and not isinstance(v, bool)]
                        if len(mvals) >= 3:
                            app_sum += int(mvals[0])
                            adm_sum += int(mvals[1])
                            enr_sum += int(mvals[2])
                    if app_sum > 0:
                        result['transfer_applicants'] = str(app_sum)
                        result['transfer_admitted']    = str(adm_sum)
                        result['transfer_enrolled']    = str(enr_sum)
                    break

    return result


# ─── Source URL mapping ─────────────────────────────────────────────────────
SOURCE_URLS = {
    109651: 'https://www.artcenter.edu/academics/academic-resources/academic-affairs.html',
    143084: 'https://www.augustana.edu/about/institutional-research/common-data-set',
    164580: 'https://www.babson.edu/media/babson/site-assets/content-assets/about/institutional-research/common-data-sets/',
    189097: 'https://barnard.edu/institutional-research/common-data-set',
    164924: 'https://www.bc.edu/content/bc-web/offices/institutional-research/common-data-set.html',
    164739: 'https://www.bentley.edu/offices/institutional-research/common-data-set',
    164748: 'https://www.berklee.edu/institutional-research/common-data-set',
    165015: 'https://www.brandeis.edu/oir/data-facts/common-data-set.html',
    164988: 'https://www.bu.edu/oir/data/common-data-set/',
    230038: 'https://ir.byu.edu/cds/',
    169080: 'https://calvin.edu/offices-services/institutional-research/common-data-set/',
    201645: 'https://case.edu/registrar/faculty-staff/institutional-research/common-data-set',
    144740: 'https://www.depaul.edu/about/fast-facts-and-rankings/common-data-set/',
    150400: 'https://www.depauw.edu/offices/institutional-research/common-data-set/',
    212054: 'https://drexel.edu/oir/data-summaries/common-data-set/',
    139658: 'https://provost.emory.edu/data/common-data-set/',
    133553: 'https://erau.edu/about/institutional-research/common-data-set',
    131496: 'https://irp.georgetown.edu/common-data-set/',
    131469: 'https://irp.gwu.edu/common-data-set',
    131520: 'https://howard.edu/institutional-research/common-data-set',
    162928: 'https://oir.jhu.edu/common-data-set/',
    117946: 'https://ir.lmu.edu/common-data-set/',
    166939: 'https://www.mtholyoke.edu/ir/common-data-set',
    135726: 'https://umia.miami.edu/data-reports/common-data-set/index.html',
    152080: 'https://nd.edu/about/facts/common-data-set/',
    167358: 'https://www.northeastern.edu/institutional-research/common-data-set/',
    147767: 'https://www.northwestern.edu/institutional-research/data-facts/common-data-set.html',
    193900: 'https://www.nyu.edu/about/news-publications/publications/common-data-set.html',
    227757: 'https://oir.rice.edu/common-data-set',
    195003: 'https://www.rit.edu/academicaffairs/institutionalresearch/common-data-set',
    195030: 'https://www.rochester.edu/ir/common-data-set.html',
    122931: 'https://www.scu.edu/provost/institutional-research/common-data-set/',
    196413: 'https://oir.syr.edu/publications/common-data-set/',
    228875: 'https://ir.tcu.edu/common-data-set/',
    168148: 'https://provost.tufts.edu/institutional-research/common-data-set/',
    144050: 'https://registrar.uchicago.edu/data-statistics/common-data-set/',
    123961: 'https://oir.usc.edu/common-data-set/',
    122612: 'https://www.usf.edu/institutional-effectiveness/common-data-set/',
    221999: 'https://registrar.vanderbilt.edu/institutional-research/common-data-set.php',
    179867: 'https://oue.wustl.edu/data/common-data-set/',
}


# ─── Main ───────────────────────────────────────────────────────────────────

def main():
    rows = []
    problems = []
    stats = {'app_fee': 0, 'app_fee_waiver': 0, 'rd_deadline': 0, 'transfer': 0}

    for (unitid, cds_year, filenames, skip_cd) in SCHOOLS:
        rec = {
            'unitid': unitid,
            'app_fee': '',
            'app_fee_waiver': '',
            'rd_deadline': '',
            'transfer_applicants': '',
            'transfer_admitted': '',
            'transfer_enrolled': '',
            'cds_year': cds_year,
            'source_url': SOURCE_URLS.get(unitid, ''),
        }

        if skip_cd:
            reason = 'section-only file or bad/missing PDF'
            problems.append(f"Skipped ({reason}): {filenames}")
            rows.append(rec)
            continue

        for fname in filenames:
            path = os.path.join(CACHE_DIR, fname)
            if not os.path.exists(path):
                problems.append(f"Missing file: {fname}")
                continue

            try:
                if fname.endswith('.xlsx'):
                    extracted = extract_from_xlsx(path)
                else:
                    if not is_real_pdf(path):
                        problems.append(f"Not a real PDF (HTML/error): {fname}")
                        continue
                    lines = extract_text_from_pdf(path)
                    extracted = extract_from_lines(lines)

                for key in extracted:
                    if not rec[key] and extracted[key]:
                        rec[key] = extracted[key]

            except Exception as e:
                problems.append(f"Error processing {fname}: {e}")

        rows.append(rec)

        if rec['app_fee']:            stats['app_fee'] += 1
        if rec['app_fee_waiver']:     stats['app_fee_waiver'] += 1
        if rec['rd_deadline']:        stats['rd_deadline'] += 1
        if rec['transfer_applicants']: stats['transfer'] += 1

    # Write CSV
    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    fieldnames = ['unitid','app_fee','app_fee_waiver','rd_deadline',
                  'transfer_applicants','transfer_admitted','transfer_enrolled',
                  'cds_year','source_url']
    with open(OUT_CSV, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {OUT_CSV}")
    print(f"\nField coverage:")
    for k, v in stats.items():
        print(f"  {k}: {v}/{len(rows)} schools")

    print(f"\nProblems/notes ({len(problems)}):")
    for p in problems:
        print(f"  - {p}")

    print("\nPer-school results:")
    for r in rows:
        print(f"  {r['unitid']:7}  fee={r['app_fee']:5}  waiver={r['app_fee_waiver']:3}  "
              f"deadline={r['rd_deadline']:12}  "
              f"xfer={r['transfer_applicants']}/{r['transfer_admitted']}/{r['transfer_enrolled']}")


if __name__ == '__main__':
    main()
