# HERD Personnel Sibling — Deposit README

**Artifact:** `data/harmonized/herd_personnel.parquet`
**Pairing:** `data/harmonized/herd_panel.parquet` (financial sibling, 1973–2024)
**Source survey:** NSF Higher Education Research and Development (HERD), Q15
(Headcount of research personnel) and Q16 (Full-time equivalents of research
personnel).
**Authored:** 2026-05-01.

## What this artifact is

A harmonized panel of HERD research-personnel counts at U.S. higher
education institutions. Two measures: headcount (the number of people) and
full-time equivalents (FTE) (the equivalent count if all reported time were
converted to full-time positions). Three personnel functions plus a rolled
total: researchers, technicians, support staff, and total. One row per
(institution, year, measure_type, personnel_function), long format.

This is the personnel half of a paired Zenodo deposit. The financial half
(`herd_panel.parquet`) covers expenditure data 1973–2024; the personnel
half covers research-personnel counts 2020–2024. Same provenance, same
harmonization decisions, separate artifacts because the question types
don't share a value axis (dollars vs. people). The combined methods note
(`docs/methods_notes/reconstructive_harmonization.md`) carries the
harmonization narrative for both.

## Schema (15 columns)

```
institution_id              VARCHAR  (era-B inst_id; FICE-style)
ncses_inst_id               VARCHAR  (era-B identifier)
ipeds_unitid                VARCHAR  (era-B identifier)
inst_name_long              VARCHAR  (cold-reader convenience)
year                        INTEGER  (2022–2024 microdata coverage)
era                         VARCHAR  (constant 'B'; parallel with financial)
measure_type                VARCHAR  ('headcount' or 'fte')
personnel_function          VARCHAR  ('researchers','technicians',
                                      'support_staff','total')
value                       DOUBLE   (persons or fte-persons)
unit                        VARCHAR  ('persons' or 'fte_persons')
source_questionnaire_no     VARCHAR  ('15' or '16')
source_question_canonical   VARCHAR  (FY 2024 Guide canonical label)
source_question_raw         VARCHAR  (HERD CSV raw label)
source_file                 VARCHAR  (e.g., 'herd2024.csv')
notes                       VARCHAR  (nullable; per-row caveats)
```

The four key columns for most analyses are **`measure_type`**,
**`personnel_function`**, **`value`**, and **`unit`**. The `era` column is
constant `'B'` here (Q15 and Q16 are era-B-only questions, no era-A
counterpart) but is retained so the schema reads as a parallel of
`herd_panel.parquet`. There is no discipline axis or source-of-funds axis
on Q15/Q16 — the public-use file rolls personnel to institution × year ×
function only.

## Year coverage

- **2020–2021:** zero microdata rows. Per HD 1.2, NSF released Q15/Q16 in
  aggregate-only form for FYs 2020–2021; no per-institution rows are
  available in the public-use microdata. These years are accessible via
  Table 26 directly and are out of scope for this parquet.
- **2022–2024:** full microdata coverage (~14,859 rows total across the
  three years).

The published-vs-microdata split is the single largest scope boundary on
this artifact. A consumer who wants 2020–2021 personnel totals at the
national level reads Table 26 (5-year longitudinal, FYs 2020–24); a
consumer who wants institution-level personnel detail starts at FY 2022.

## Verification verdict

Reconciled against NCSES Data Table 26 (NSF 26-304). 6-cell scope: 3 years
(2022, 2023, 2024) × 2 measures (Headcount, FTE).

> **FY 2024 exact match; FY 2022/2023 documented divergence ~0.46–0.88%
> structurally explained by FY-2023-anchored standard-form filter
> back-applied to all years.**

The divergence is a known NCSES methodological choice for the longitudinal
Table 26 (the "$1M+ FY 2023 R&D" standard-form criterion is anchored at
FY 2023 and back-applied across the five-year table), not a build issue.
The parquet preserves the all-respondents view; cold readers who need
Table 26 alignment filter to the FY-2023-anchored standard-form respondent
set. Receipts (the cell-by-cell table, the structural argument, response
rates) are in `validation/reports/personnel_table26_reconciliation.md`.

Public-use response rate is 99.40–99.85% across 2022/2023/2024 against the
standard-form survey universe per Table A-3
(`data/reference/nsf26304-taba-003.pdf`) — no completeness concern surfaced
on the inventory side.

## Methods note

Harmonization decisions, the era-B reconstruction rule (financial half),
and the personnel-specific decisions (Q15/Q16 schema, Table 26
verification, FY-2023-anchored filter explanation) live in
`docs/methods_notes/reconstructive_harmonization.md`. The personnel section
parallels the financial spine — same Reconstructive Harmonization framing,
smaller scope.

## Reproducibility

```bash
# Build the parquet from raw HERD zips:
uv run python etl/build_herd_personnel.py

# Regenerate the Table 26 verification grid:
uv run python etl/spikes/personnel_table26_verify.py
```

Inputs:
- `data/raw/herd/higher_education_r_and_d_{2022,2023,2024}.zip`
  (SHA-256s in `data/raw/MANIFEST.md`).
- Anchors: `data/reference/nsf26304-tab026.pdf` (Table 26),
  `data/reference/nsf26304-taba-003.pdf` (Table A-3),
  `data/reference/nsf26304-taba-023.pdf` (table inventory).

A cold reader with the lockfile (`uv.lock`), the raw zips, and these two
scripts reaches the same harmonized parquet and the same verification
grid.
