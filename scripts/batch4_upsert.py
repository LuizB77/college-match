#!/usr/bin/env python3
"""Batch 4 upsert — 20 schools researched 2026-09-30."""

import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from upsert_intl_aid import upsert_rows

NaN = float("nan")

rows = [
    # ── FILLED: H6 numbers from CDS ──────────────────────────────────────────
    # Knox — merit-only, 100% aided (323/323)
    dict(
        unitid=146427,
        offers_intl_aid="True",
        meets_full_need_intl=NaN,
        need_blind_intl=NaN,
        pct_intl_aided=round(323/323, 4),
        avg_intl_award=46793,
        cds_total_cost=74757,
        cds_year="2025-26",
        source_url="https://www.knox.edu/documents/OIRA/FINAL%20CDS_2025-2026_PDF.pdf",
        intl_aid_page_url="https://www.knox.edu/admission/apply-to-knox/international-applicants/financial-aid-and-visa-information",
        quality=NaN,
    ),
    # F&M — meets 100% demonstrated need (need-aware)
    dict(
        unitid=212577,
        offers_intl_aid="True",
        meets_full_need_intl="True",
        need_blind_intl="False",
        pct_intl_aided=round(152/305, 4),
        avg_intl_award=58920,
        cds_total_cost=77220,
        cds_year="2024-25",
        source_url="https://www.fandm.edu/_resources/pdfs/IR_CDS%202024-25.pdf",
        intl_aid_page_url="https://www.fandm.edu/financial-aid/guidance-and-information.html",
        quality=NaN,
    ),
    # Gettysburg — avg only; pct omitted (H6 aided 326 > B2 total 289; likely CDS data error)
    dict(
        unitid=212674,
        offers_intl_aid="True",
        meets_full_need_intl=NaN,
        need_blind_intl=NaN,
        pct_intl_aided=NaN,
        avg_intl_award=59613,
        cds_total_cost=85640,
        cds_year="2024-25",
        source_url="https://www.gettysburg.edu/offices/institutional-research/pdfs/2025/cds_2024-2025_final.pdf",
        intl_aid_page_url="https://www.gettysburg.edu/admissions-aid/international-students/financial-aid-international-students",
        quality=NaN,
    ),
    # Trinity — meets full demonstrated need
    dict(
        unitid=130590,
        offers_intl_aid="True",
        meets_full_need_intl="True",
        need_blind_intl=NaN,
        pct_intl_aided=round(245/295, 4),
        avg_intl_award=66488,
        cds_total_cost=93240,
        cds_year="2024-25",
        source_url="https://www.trincoll.edu/asic/wp-content/uploads/sites/125/2025/12/CDS-2024-2025-Trinity-College.pdf",
        intl_aid_page_url="https://www.trincoll.edu/admissions/finaid/international-students/",
        quality=NaN,
    ),
    # Wesleyan — need-blind for all, meets 100% need; 2022-23 CDS (most recent available)
    dict(
        unitid=130697,
        offers_intl_aid="True",
        meets_full_need_intl="True",
        need_blind_intl="True",
        pct_intl_aided=round(84/311, 4),
        avg_intl_award=83185,
        cds_total_cost=86350,
        cds_year="2022-23",
        source_url="https://www.wesleyan.edu/ir/data-sets/CDS_2022-2023.pdf",
        intl_aid_page_url="https://www.wesleyan.edu/admission/affordability-and-aid/index.html",
        quality=NaN,
    ),
    # Richmond — meets 100% need, need-aware for intl
    dict(
        unitid=233374,
        offers_intl_aid="True",
        meets_full_need_intl="True",
        need_blind_intl="False",
        pct_intl_aided=round(187/287, 4),
        avg_intl_award=67911,
        cds_total_cost=89540,
        cds_year="2025-26",
        source_url="https://oir.richmond.edu/pdfs/CDS2025-2026SectionH.pdf",
        intl_aid_page_url="https://financialaid.richmond.edu/applying/international.html",
        quality=NaN,
    ),
    # Middlebury — meets full need for admitted intl (limited need-blind)
    dict(
        unitid=230959,
        offers_intl_aid="True",
        meets_full_need_intl="True",
        need_blind_intl="False",
        pct_intl_aided=round(192/337, 4),
        avg_intl_award=79468,
        cds_total_cost=NaN,
        cds_year="2024-25",
        source_url="https://www.middlebury.edu/sites/default/files/2025-04/Middlebury%20CDS%202024_2025.pdf",
        intl_aid_page_url="https://www.middlebury.edu/college/admissions/financial-aid",
        quality=NaN,
    ),
    # Wellesley — aided count derived from total/avg (71 = 6677733/94053); need-aware
    dict(
        unitid=168218,
        offers_intl_aid="True",
        meets_full_need_intl="True",
        need_blind_intl="False",
        pct_intl_aided=round(71/292, 4),
        avg_intl_award=94053,
        cds_total_cost=NaN,
        cds_year="2025-26",
        source_url="https://wellesley-college.files.svdcdn.com/production/administrative-departments/OIR/CDS_2025-2026-FINAL.pdf",
        intl_aid_page_url="https://www.wellesley.edu/sfs",
        quality=NaN,
    ),
    # ── POLICY-ONLY ──────────────────────────────────────────────────────────
    # Macalester — H6 blank; meets full need confirmed; need-aware for intl
    dict(
        unitid=173902,
        offers_intl_aid="True",
        meets_full_need_intl="True",
        need_blind_intl="False",
        pct_intl_aided=NaN,
        avg_intl_award=NaN,
        cds_total_cost=NaN,
        cds_year=NaN,
        source_url=NaN,
        intl_aid_page_url="https://www.macalester.edu/financial-aid/apply/international/",
        quality=NaN,
    ),
    # Wake Forest — H6 blank; merit-only for internationals; no need-based
    dict(
        unitid=199847,
        offers_intl_aid="True",
        meets_full_need_intl="False",
        need_blind_intl=NaN,
        pct_intl_aided=NaN,
        avg_intl_award=NaN,
        cds_total_cost=NaN,
        cds_year=NaN,
        source_url=NaN,
        intl_aid_page_url="https://admissions.wfu.edu/become-a-deacon/international/",
        quality=NaN,
    ),
    # St Olaf — H6 blank; limited aid; G1=81200 from CDS 2025-26
    dict(
        unitid=174844,
        offers_intl_aid="True",
        meets_full_need_intl=NaN,
        need_blind_intl=NaN,
        pct_intl_aided=NaN,
        avg_intl_award=NaN,
        cds_total_cost=81200,
        cds_year="2025-26",
        source_url="https://wp.stolaf.edu/iea/files/2026/01/StOlaf_CDS_2025-26.xlsx-CDS-H-1.pdf",
        intl_aid_page_url="https://wp.stolaf.edu/financialaid/how-to-apply-for-financial-aid-international/",
        quality=NaN,
    ),
    # St John's NY — merit + need-based scholarships; CDS not located
    dict(
        unitid=195809,
        offers_intl_aid="True",
        meets_full_need_intl=NaN,
        need_blind_intl=NaN,
        pct_intl_aided=NaN,
        avg_intl_award=NaN,
        cds_total_cost=NaN,
        cds_year=NaN,
        source_url=NaN,
        intl_aid_page_url="https://www.stjohns.edu/admission/scholarships",
        quality=NaN,
    ),
    # St Thomas University FL — merit $9k-$13k by GPA
    dict(
        unitid=137476,
        offers_intl_aid="True",
        meets_full_need_intl=NaN,
        need_blind_intl=NaN,
        pct_intl_aided=NaN,
        avg_intl_award=NaN,
        cds_total_cost=NaN,
        cds_year=NaN,
        source_url=NaN,
        intl_aid_page_url="https://www.stu.edu/admissions/international-admissions/",
        quality=NaN,
    ),
    # Fairleigh Dickinson — merit up to $24k/yr; no need-based
    dict(
        unitid=184603,
        offers_intl_aid="True",
        meets_full_need_intl=NaN,
        need_blind_intl=NaN,
        pct_intl_aided=NaN,
        avg_intl_award=NaN,
        cds_total_cost=NaN,
        cds_year=NaN,
        source_url=NaN,
        intl_aid_page_url="https://www.fdu.edu/admissions/international/scholarships/",
        quality=NaN,
    ),
    # Barry — merit scholarships available (small); no need-based
    dict(
        unitid=132471,
        offers_intl_aid="True",
        meets_full_need_intl=NaN,
        need_blind_intl=NaN,
        pct_intl_aided=NaN,
        avg_intl_award=NaN,
        cds_total_cost=NaN,
        cds_year=NaN,
        source_url=NaN,
        intl_aid_page_url="https://www.barry.edu/en/financial-aid/undergraduate/international-students",
        quality=NaN,
    ),
    # California College of the Arts — merit $20k-$25k; no need-based
    dict(
        unitid=110370,
        offers_intl_aid="True",
        meets_full_need_intl=NaN,
        need_blind_intl=NaN,
        pct_intl_aided=NaN,
        avg_intl_award=NaN,
        cds_total_cost=NaN,
        cds_year=NaN,
        source_url=NaN,
        intl_aid_page_url="https://portal.cca.edu/essentials/financial-aid/steps-to-apply-and-types-of-aid/international-students/",
        quality=NaN,
    ),
    # NYIT — International Leadership Scholarship + academic merit awards
    dict(
        unitid=194091,
        offers_intl_aid="True",
        meets_full_need_intl=NaN,
        need_blind_intl=NaN,
        pct_intl_aided=NaN,
        avg_intl_award=NaN,
        cds_total_cost=NaN,
        cds_year=NaN,
        source_url=NaN,
        intl_aid_page_url="https://www.nyit.edu/admissions/international/student-aid/",
        quality=NaN,
    ),
    # Indiana Wesleyan National & Global — min $10k gift aid for internationals
    dict(
        unitid=488679,
        offers_intl_aid="True",
        meets_full_need_intl=NaN,
        need_blind_intl=NaN,
        pct_intl_aided=NaN,
        avg_intl_award=NaN,
        cds_total_cost=NaN,
        cds_year=NaN,
        source_url=NaN,
        intl_aid_page_url="https://www.indwes.edu/admissions/tuition-aid/aid-options",
        quality=NaN,
    ),
    # National Louis — International Bachelor's Degree Scholarship (10% tuition) + others
    dict(
        unitid=147536,
        offers_intl_aid="True",
        meets_full_need_intl=NaN,
        need_blind_intl=NaN,
        pct_intl_aided=NaN,
        avg_intl_award=NaN,
        cds_total_cost=NaN,
        cds_year=NaN,
        source_url=NaN,
        intl_aid_page_url="https://nl.edu/admissions/international-students/affordable-tuition-and-scholarships/",
        quality=NaN,
    ),
    # Seattle University — merit ≥$8k/yr; no need-based for internationals
    dict(
        unitid=236595,
        offers_intl_aid="True",
        meets_full_need_intl=NaN,
        need_blind_intl=NaN,
        pct_intl_aided=NaN,
        avg_intl_award=NaN,
        cds_total_cost=NaN,
        cds_year=NaN,
        source_url=NaN,
        intl_aid_page_url="https://www.seattleu.edu/financial-aid/receiving-financial-aid/international-student-financial-aid/",
        quality=NaN,
    ),
]

df = pd.DataFrame(rows)
upsert_rows(df)
print("Batch 4 upsert complete.")
