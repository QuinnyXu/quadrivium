# HERD panel duplicate-row fan-out: finding and fix

Found 2026-10-01 during data-quality review ahead of a Power BI benchmarking project (College of Engineering, plus Computer Science and Geosciences).

## Finding

`data/harmonized/herd_panel.parquet` (v4.0.0 and earlier) carried **43,306 exact duplicate rows**, all in era B (FY2010-2023).

**Root cause.** `_load_discipline_fine_crosswalk` projects `discipline_fine.csv` to `(era, raw_row_label, discipline_fine, discipline_coarse)` and drops the year-range columns. Seven era-B Q11 raw labels carry two crosswalk rows with split year ranges (2010-2015 and 2016-2023) and identical mappings: aerospace, electrical (the "electronics" plural), and the five Geosciences labels. The year-range-blind join `ON era AND raw_row_label` therefore fanned those Q11 rows out x2. The duplicated Q11 rows then flowed into the Q9+Q11 reconstruction (`source_class='all_source'`), the Q11 `nonfederal` rows, and Q14 `r&d_equipment`.

**Why earlier checks missed it.** The FY2024 verification grid (58 cells) is FY2024-only, and FY2024 uses canonical labels (no fan-out). Stage 9 had no grain-uniqueness assertion.

## Impact (v4.0.0 and earlier)

- Geosciences (all rows) double-counted FY2010-2023, including a spurious FY2009->2010 "jump" ($2.92B -> $5.97B). Corrected: $2.92B -> $2.99B.
- Electrical and aerospace engineering sub-fields inflated; Engineering sub-fields summed to ~$12.0B vs $9.33B for "Engineering, all" in FY2010. Corrected: they agree to within 0.1%.
- `Engineering, all`, Computer and information sciences, institution-level `All` totals, FY2024, federal rows, and the attributes/personnel panels were NOT affected. National all-institution totals are unchanged.

## Fix

1. `SELECT DISTINCT` in `_load_discipline_fine_crosswalk` (mappings for the duplicated keys are identical; verified 89 distinct keys = 89 distinct full mappings).
2. New Stage 9 assertion 11: unique panel grain `(institution_id, year, discipline_fine, expenditure_type, source_class, form_type, source_questionnaire_no)`.

## Verification

| Check | Result |
|---|---|
| Rows | 1,462,094 -> 1,418,788 (-43,306) |
| New vs old (EXCEPT, both directions) | 0 rows added, 0 rows with changed values; the removed rows equal the exact-duplicate count |
| Grain duplicates | 0 |
| Institution-year `All` R&D totals, FY2009/2010/2019/2023/2024 | identical old vs new |
| Era-B reconstruction identity (161,441 cells) | residual 0.0 |
| `panel_anchor_verify.py` | 58 PASS / 0 FAIL / 2 STRUCTURAL_ABSENT |
| `herd_panel_attributes.parquet` | byte-identical |

New SHA-256 recorded in `data/harmonized/MANIFEST.md`.

## Not affected / to re-check before release

- The identity spine (`build_fedsupport_identity_spine.py`) reads HERD only for UNITID presence, so it is unaffected.
- The 2008->2011 era-reconciliation figures (e.g. UCSD Geosciences FY2010 era-B 139,142 kUSD) are not doubled, so they appear to predate the defect; re-verify before the next release.
- Release: this changes a shipped deposit file. A patch version (4.0.1) with a methods-note erratum and Zenodo re-deposit is the Maintainer's call (CLAUDE.md §10).
