#!/usr/bin/env python3
"""Batch 5 partial upsert — 6 schools researched before interruption, 2026-09-30."""

import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from upsert_intl_aid import upsert_rows

NaN = float("nan")

rows = [
    # ── FILLED ───────────────────────────────────────────────────────────────
    # Loyola University Chicago — H6: 229/259, avg $26,906, G1=$76,490
    dict(
        unitid=146719,
        offers_intl_aid="True",
        meets_full_need_intl=NaN,
        need_blind_intl=NaN,
        pct_intl_aided=round(229/259, 4),
        avg_intl_award=26906,
        cds_total_cost=76490,
        cds_year="2025-26",
        source_url="https://www.luc.edu/media/lucedu/oie/CDS%202025-26%20-%20Loyola%20University%20Chicago%20-%20Final_af.pdf",
        intl_aid_page_url="https://www.luc.edu/finaid/international/",
        quality=NaN,
    ),
    # Oberlin College — H6: 274/274, avg $49,193, G1=$90,461; B2 snippet fallback
    dict(
        unitid=204501,
        offers_intl_aid="True",
        meets_full_need_intl=NaN,
        need_blind_intl=NaN,
        pct_intl_aided=round(274/274, 4),
        avg_intl_award=49193,
        cds_total_cost=90461,
        cds_year="2024-25",
        source_url="https://www.oberlin.edu/institutional-research/common-data-set",
        intl_aid_page_url="https://www.oberlin.edu/admissions-and-aid/financial-aid/international-students",
        quality=NaN,
    ),
    # SMU — H6: 198 aided (non-need-based only), avg $45,354, G1=$92,766; B2 not available
    dict(
        unitid=228246,
        offers_intl_aid="True",
        meets_full_need_intl="False",
        need_blind_intl=NaN,
        pct_intl_aided=NaN,
        avg_intl_award=45354,
        cds_total_cost=92766,
        cds_year="2025-26",
        source_url="https://www.smu.edu/about/leadership-and-administration/institutional-effectiveness/common-data-set/cds-2025-26-part-h-financial-aid.pdf",
        intl_aid_page_url="https://www.smu.edu/enrollment-services/financial-aid/types-of-aid/scholarships/international-scholarships",
        quality=NaN,
    ),
    # ── POLICY-ONLY ──────────────────────────────────────────────────────────
    # Colgate — H6 blank; meets 100% demonstrated need for all admitted incl. internationals; need-aware for intl
    dict(
        unitid=190099,
        offers_intl_aid="True",
        meets_full_need_intl="True",
        need_blind_intl="False",
        pct_intl_aided=NaN,
        avg_intl_award=NaN,
        cds_total_cost=NaN,
        cds_year=NaN,
        source_url=NaN,
        intl_aid_page_url="https://www.colgate.edu/admission-aid/financial-aid/colgate-commitment",
        quality=NaN,
    ),
    # Dickinson — H6 blank; need-based aid available but limited; need-aware for intl
    dict(
        unitid=212009,
        offers_intl_aid="True",
        meets_full_need_intl=NaN,
        need_blind_intl="False",
        pct_intl_aided=NaN,
        avg_intl_award=NaN,
        cds_total_cost=NaN,
        cds_year=NaN,
        source_url=NaN,
        intl_aid_page_url="https://www.dickinson.edu/info/20045/admissions/1179/international_student_financial_aid",
        quality=NaN,
    ),
    # University of St Thomas MN — merit scholarships 30–70% of tuition; no need-based for intl
    dict(
        unitid=174914,
        offers_intl_aid="True",
        meets_full_need_intl=NaN,
        need_blind_intl=NaN,
        pct_intl_aided=NaN,
        avg_intl_award=NaN,
        cds_total_cost=NaN,
        cds_year=NaN,
        source_url=NaN,
        intl_aid_page_url="https://www.stthomas.edu/admissions/international/undergraduate/merit-based-scholarships/",
        quality=NaN,
    ),
]

df = pd.DataFrame(rows)
upsert_rows(df)
print("Batch 5 partial upsert complete.")
