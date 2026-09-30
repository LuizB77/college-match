# International Aid Queue Run Summary

**Date:** 2026-09-30  
**Status:** STOPPED — two consecutive batches below 30% fill rate

---

## Batches Run

| Batch | Schools | Filled | Fill Rate | Notes |
|-------|---------|--------|-----------|-------|
| 1     | ~20     | ~15    | ~75%      | est. from 2026-09-27 date group |
| 2     | ~20     | ~10    | ~50%      | est. from 2026-09-27 date group |
| 3     | 20      | 7      | 35%       | commit 3dd3a4d |
| 4     | 20      | 8      | 40%       | commit 3102be7 |
| partial | 6     | 3      | 50%       | interrupted; commit 5f471bb |
| 5     | 22      | 3      | **14%**   | commit bddf7b4 — below 30% |
| 6     | 20      | 4      | **20%**   | commit a2ad57f — below 30% |

Batches 5 and 6 both fell below 30% fill rate → stop condition met.

---

## Final Counts

| Status        | Count |
|---------------|-------|
| filled        | 57    |
| policy_only   | 102   |
| not_found     | 8     |
| **Total done**| **159** |
| pending       | ~1,471 |
| Queue cap     | 200   |

---

## Data Quality

- **Flagged rows:** 0 (validate_intl_aid.py clean on all 166 intl_aid.csv rows)
- **Rows with source_url:** 86 (57 filled + some policy_only with CDS links)
- **Rows without source_url:** 80 (policy-only rows where CDS was inaccessible)

---

## Fallback Usage (agent_snippet)

Snippet fallback (manual PDF reading via pdfplumber when extract_cds.py returns missing) was used for all batch 6 CDS extractions. The extract_cds.py script requires schools to be pre-registered in SCHOOL_CONFIG; new schools were extracted directly. Fallback reads were performed for:

- **CMC (112260):** Table extraction bypassed cid: encoding; H6=53/186, avg=$64,997
- **Kenyon (203535):** Full text extraction; H6=160/212, avg=$67,659; G1=$89,600
- **Augustana SD (219000):** openpyxl extraction from XLSX; H6=242/246, avg=$27,797; G1=$53,522
- **Columbia Chicago (144281):** Table extraction (partial cid: encoding); H6=178/209, avg=$10,942; G1=$56,856

Several PDFs (Swarthmore, Carleton, Stetson, Union) were confirmed to be blank/unfilled CDS templates — form field values not rendered in the PDF text layer. Marked policy_only after confirming aid availability via official FA pages.

---

## Why Stopped

**Stopping condition:** Two consecutive batches with fill rate < 30%.

- **Batch 5:** 3 filled / 22 schools = **14%** (schools from tail of earlier queue segment)
- **Batch 6:** 4 filled / 20 schools = **20%** (mix of selective LACs and mid-tier schools)

Root cause: The queue has shifted toward schools whose CDS forms are either:
1. Blank/unfilled PDF templates (Swarthmore, Carleton, Stetson, Union — form fields not parseable)
2. Hosted on SharePoint or Issuu with no direct PDF access (St Lawrence, Rollins, Hofstra)
3. Schools that only publish H6 via inaccessible formats (XLSX with SCHOOL_CONFIG not registered)

Policy-only rows still have value (offers_intl_aid, intl_aid_page_url) for app display, but the low fill rate signals diminishing returns on CDS extraction effort.

---

## Recommendations

1. **Register priority schools in SCHOOL_CONFIG** in extract_cds.py so they can be batch-extracted automatically (CMC, Kenyon, Augustana SD, Columbia Chicago done manually this run).
2. **Improve PDF accessibility detection** — skip blank-template PDFs early by checking if G1 tuition cell is empty.
3. **SharePoint/Issuu CDS workaround** — for schools hosting CDS on SharePoint, consider fetching the IPEDS data directly instead.
4. **Resume with top-priority remaining schools** — 41 schools remain before the 200-cap. Prioritize those in `priority_group = 1` with likely accessible PDFs.

---

## check_deploy.sh

```
55 passed, 4 deselected in 23.50s
=== check_deploy.sh PASSED ===
```
