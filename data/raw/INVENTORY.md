# NSF HERD Raw Inventory

Generated: 2026-04-29 from `NSF_HERD.zip` (99,597,912 bytes) at project root.
Extracted to inspection-only temp folder `_tmp_herd_inspect/` (NOT to `data/raw/herd/`).
This inventory drives the harmonization design; the spec assumed a wide schema, the
raw data is already long-format keyed by `(questionnaire_no, question, row, column)`.

## 1. Top-level archive contents

- 53 nested year zips: `higher_education_r_and_d_YYYY.zip` for `YYYY` in 1972..2024.
- `Guide To Herd Data Files FY24.pdf` (399 KB) — official NSF documentation. Read this
  before finalizing the crosswalks; we did not parse it (no PDF tooling on the laptop yet).

## 2. Per-year file shape

Each year zip contains exactly two files:

- `herd_YYYY.csv` (1972-2015) **or** `herdYYYY.csv` (2016-2024) — naming convention
  changes silently at 2016. The ETL must accept both patterns.
- `herd_YYYY.sas7bdat` (or `herdYYYY.sas7bdat`) — same data, SAS native format.
  Plan: ignore the SAS file and consume CSV. Only fall back to SAS if a CSV is
  malformed (none observed yet).

## 3. Row counts and reporting universe by year

| Year | CSV name        | Rows    | Distinct insts | Notes |
|------|-----------------|---------|----------------|-------|
| 1972 | herd_1972.csv   |   9,228 | 584 | |
| 1973 | herd_1973.csv   |  20,196 | 584 | |
| 1974 | herd_1974.csv   |  18,839 | 594 | |
| 1975 | herd_1975.csv   |  17,508 | 534 | |
| 1976 | herd_1976.csv   |  18,072 | 534 | |
| 1977 | herd_1977.csv   |  17,514 | 535 | |
| 1978 | herd_1978.csv   |   7,602 | **316** | **anomaly: half coverage** |
| 1979 | herd_1979.csv   |  22,307 | 560 | |
| 1980 | herd_1980.csv   |  29,140 | 558 | |
| 1981 | herd_1981.csv   |  49,474 | 556 | first year `03 Equipment expenditures by S&E field` appears |
| 1982-1992 | herd_YYYY.csv | 36-58k | 554-578 | stable era |
| 1993 | herd_1993.csv   |  38,579 | **686** | **universe expansion (+108 insts vs 1992)** |
| 1994 | herd_1994.csv   |  50,377 | 646 | |
| 1995-2002 | herd_YYYY.csv | 46-55k | 640-660 | stable era |
| 2003 | herd_2003.csv   |  76,612 | 659 | **format expansion: Non-S&E + per-agency Federal** |
| 2004-2009 | herd_YYYY.csv | 74-78k | 634-708 | stable in this format |
| 2010 | herd_2010.csv   | 231,499 | 744 | **survey redesign: new question grid + IPEDS UNITID** |
| 2011 | herd_2011.csv   | 264,087 | **912** | **pilot/transition spike** |
| 2012-2015 | herd_YYYY.csv | 226-233k | 633-652 | post-redesign steady state |
| 2016 | herd2016.csv    | 230,494 | 639 | **filename underscore dropped** |
| 2017 | herd2017.csv    | 238,032 | 643 | **adds `Engineering, industrial and manufacturing`, `01.1 Inclusion of Institution funds`, `Life sciences, natural resources and conservation`** |
| 2018-2023 | herd2018.csv ... | 237-258k | 637-664 | |
| 2024 | herd2024.csv    | 264,321 | 681 | **adds Q15 Headcount of personnel, Q16 FTEs (researchers/technicians/support)** |

## 4. CSV schema by era

The data is already long-format: each row is one cell of one questionnaire grid.
The key is `(institution, year, questionnaire_no, question, row, column)`. The
`row` field carries the discipline label (e.g., `Engineering, chemical`); the
`column` field carries the source-of-funds label (e.g., `Federal`, `DOD`, `NSF`).

### Era A: 1972-2009 (`fice` regime)

20 columns:

```
fice, fice_combined, year, hbcu_flag, has_med_sch_flag, hhe_flag,
toi_code, hdg_code, toc_code, pilot_fy09_flag,
inst_name_long, inst_city, inst_state, inst_zip,
questionnaire_no, question, row, column, data, status
```

- Institution ID: `fice` (6-digit).
- State as `inst_state` (2-letter).
- No IPEDS UNITID, no agency-name standardization.
- Column count, header text, and column order are constant across the entire era.

### Era B: 2010-2024 (`inst_id` + IPEDS regime)

23 columns:

```
inst_id, year, ncses_inst_id, ipeds_unitid, hbcu_flag, med_sch_flag, hhe_flag,
toi_code, hdg_code, toc_code,
inst_name_long, inst_city, inst_state_code, inst_zip,
questionnaire_no, question, row, column, data, status,
othinfo, othinfo_s, standardized_agency_names
```

- Institution IDs: `inst_id` (6-digit, same code-space as `fice`), `ncses_inst_id`
  (e.g., `U0626001`), `ipeds_unitid` (e.g., `111966`). All three appear together.
- `inst_state_code` (renamed from `inst_state`).
- `hbcu_flag` rendered as `0`/`1` (was `T`/`F` pre-2010).
- New columns: `othinfo`, `othinfo_s` (free text annotations), `standardized_agency_names`.
- `pilot_fy09_flag` dropped at the 2010 boundary.

## 5. Question / row / column codeset by era

The harmonization work lives here. The discipline taxonomy and source-of-funds
taxonomy both shift; the breaks below are observed in the data, not inferred.

### 5.1 Question grid

| Era | Distinct questionnaire_no | Distinct question text | Notes |
|-----|---------------------------|------------------------|-------|
| 1972-1980 | `01, 02, 04` (+ a `04 Capital expenditures by area` module that drops out by ~1984) | 3-4 | Pre-equipment module |
| 1981-1996 | `01, 02, 03, 04` then `01, 02, 03` | 3-4 | `03 Equipment expenditures by S&E field` added 1981 |
| 1997-2002 | `01, 01a, 02, 03` | 4-5 | `01a Passed through to subrecipients` added 1997 |
| 2003-2009 | `01, 01a, 01b, 02, 02a, 02b, 03` | 6-7 | **2003 format expansion**: Non-S&E + per-agency Federal added |
| 2010-2016 | ~180 codes (`01.a` through `14J09`, plus `NA_01..NA_03`) | ~50-130 | **survey redesign 2010** — completely new question grid |
| 2017-2023 | ~210 codes; adds `01.1 Inclusion of Institution funds`, `02.a..02.f Foreign funds` detail, `09F03/H01/J*`/etc. | ~135 | minor expansions |
| 2024     | ~213 codes; adds `15 Headcount of personnel`, `16 FTEs` | ~129 | personnel module — new variable family |

`questionnaire_no` values that look like a US state code (`AL`, `CA`, `TX`...) or a
ZIP code (`52242`, `06106-2791`...) are NOT data rows in the science sense — they
appear to be questionnaire-tracking / footnote rows keyed by institution location.
They must be filtered out before harmonization.

### 5.2 Discipline taxonomy in `row` (for `02 Expenditures by S&E field`)

| Era | Row count in `02` | Defining labels | Crosswalk strategy |
|-----|-------------------|-----------------|--------------------|
| 1972-2002 | 34 | `Engineering, aeronautical and astronautical`, `Engineering, electrical`, `Computer sciences, all`, `Mathematical sciences, all`, `Environmental sciences, atmospheric sciences`, `Life sciences, biological sciences`, `Life sciences, medical sciences`, `Physical sciences, astronomy` | map fine labels here |
| 2003-2009 | 43 (+Non-S&E) | same S&E labels as 1972-2002, plus `Non-S&E, business and management`, `Non-S&E, communications, journalism, library science`, etc. | same S&E mapping; new Non-S&E band |
| 2010-2016 | 43 | RENAMED: `Computer sciences` → `Computer and information sciences`; `Engineering, aeronautical and astronautical` → `Engineering, aerospace, aeronautical, and astronautical`; `Engineering, electrical` → `Engineering, electrical, electronic, and communications`; `Mathematical sciences` → `Mathematics and statistics`; `Environmental sciences` → `Geosciences, atmospheric sciences, and ocean sciences`; `Life sciences, biological sciences` → `Life sciences, biological and biomedical sciences`; `Life sciences, medical sciences` → `Life sciences, health sciences`; `Engineering, bioengineering and biomedical` → `Engineering, bioengineering and biomedical engineering` | one-to-one rename crosswalk |
| 2017-2024 | 47 | adds `Engineering, industrial and manufacturing`, `Life sciences, natural resources and conservation` | net-new fine codes; coarse Engineering still resolves |

This is the pre/post-2010 fine-label rename, NOT a 1996 break.
**The "1996 fine-detail break" in the spec was not observed in raw data**. 1995 and
1996 use the same 34-field taxonomy. The locked schema rule "_fine columns NULL
pre-1996" should be revisited with Vision before we hard-code it.

### 5.3 Source-of-funds taxonomy in `column` (for `02`)

| Era | Distinct column values | Notes |
|-----|------------------------|-------|
| 1972-2002 | `Federal`, `Total` | only Federal vs. Total in field-level rows |
| 2003-2009 | `DOD, DOE, HHS, NASA, NSF, USDA, Other agencies, Federal, Total` (9) | per-agency split appears |
| 2010-2024 | `DOD, DOE, HHS, NASA, NSF, USDA, Other agencies, Total` (8) | aggregate `Federal` no longer published as a separate column in `02`; must be reconstructed as sum of agencies |

Question `01 Source` columns (institution-level, not field-level) carry the
broader taxonomy: `Federal`, `Industry`, `Institution funds, total`, `State and
local government`, `Total`. The 2010 redesign promotes these to `01.a..01.g` and
adds `02.a..02.f Foreign funds`.

## 6. Observed breakpoints, mapped

Restated against the spec's expected breaks:

- **1996 discipline-code shift (claimed in spec)** — NOT observed in the raw CSVs.
  The discipline label set in `row` is identical 1995 and 1996. There may be a
  documentation-level rationale (perhaps in the FY24 Guide PDF), but the data
  doesn't carry it. Flag for Vision: do we trust the spec or the data?
- **2003 format expansion (real, observed)** — Non-S&E rows + per-agency Federal
  columns appear in `02`. New questionnaire codes `02a`, `02b`, `01b` appear.
- **2010 survey redesign (real, observed, dramatic)** — schema columns change
  (`fice` → `inst_id`/`ipeds_unitid`), questionnaire codes go from 7 to 180,
  fine discipline labels are renamed.
- **2017 micro-expansion (real, observed)** — `Engineering, industrial and
  manufacturing` and `Life sciences, natural resources and conservation`
  added. New `01.1 Inclusion of Institution funds` module.
- **2024 personnel module (real, observed)** — `15 Headcount of personnel` and
  `16 FTEs` (Researchers / Technicians / Support Staff / Total). Net-new
  variable family — does NOT fit the financial `expenditure_type` schema
  cleanly. Either widen the schema's `expenditure_type` enum to include
  `headcount` / `fte`, or carve a sibling table.
- **1978 partial-coverage anomaly (real, observed)** — only 316 institutions and
  no equipment module; 1978 must be flagged as a partial-coverage year in the
  panel and excluded from continuous-panel reconciliations.
- **1992-1993 universe expansion (real, observed)** — distinct institutions jump
  from 578 to 686. Probably the change in HEGIS→IPEDS framing or the
  community-college addition; should be noted but not "fixed."
- **2010-2011 universe spike (real, observed)** — 744 → 912 → 652. Looks like a
  pilot rollover. Check the FY24 Guide for the official story.

## 7. Status codes in `data` / `status`

A `status` column carries cell-level annotations:
- `e` = estimated (seen 1972, 1997)
- `i` = imputed (seen 2024 personnel)
- empty = reported value
- 2010+ also surface text annotations like `No expenditures` in nearby columns

Plan: preserve `status` verbatim in a `status_raw` column on the harmonized panel
and document it in the data dictionary. Do not collapse silently.

## 8. Surprises (things not in the spec)

1. **Already-long format.** The schema spec assumed wide CSVs to be melted. The
   raw is already in long form keyed by questionnaire/question/row/column. Most
   of the ETL is *unpivoting nothing* and *labeling something*.
2. **1996 break not visible.** Our spec's "_fine NULL pre-1996" rule has no
   support in the discipline taxonomy. The real fine-label break is 2010.
3. **State-code questionnaire rows.** `questionnaire_no` values like `AL`, `CA`,
   `06106` are tracking rows, not data. They must be filtered upstream of any
   numeric reduction.
4. **Two institution IDs to reconcile from 2010 forward.** `inst_id` (continues
   FICE-style 6-digit), `ncses_inst_id` (NCSES internal), `ipeds_unitid`. The
   crosswalk `fice ↔ ipeds_unitid` is implicit in the post-2010 rows; we can
   build it for free from those years and back-extend pre-2010.
5. **2024 personnel module is not financial.** Q15/Q16 carry headcount and FTEs.
   The locked schema's `expenditure_type` doesn't fit. Decision needed.
6. **`pilot_fy09_flag` exists 1972-2009 then disappears.** Confirms 2009 had a
   pilot run of the 2010 redesign; cells flagged here may need different
   treatment.
7. **No PDF text extractor on the laptop.** The FY24 Guide carries canonical
   break documentation we did not read. Add `pypdf` or `pdfminer.six` to the env
   and re-read the Guide before finalizing crosswalks.

## 9. Provenance

- Source: `NSF_HERD.zip` at project root, SHA-256 recorded in
  `data/raw/MANIFEST.md` (HD 1.1, 2026-04-29).
- Staged: `data/raw/herd/` (gitignored, allow-listed for `INVENTORY.md`,
  `MANIFEST.md`, `.gitignore`).
- Inspector: Skipper (panel-review pass, Q1 Weeks 1-2 kickoff, 2026-04-29).

## 10. Corrections (HD 1.2, 2026-04-29)

### 10.1 Personnel module is 2020-2024, not 2024-only

§5.1 / §6 / §8 item 5 say "2024 personnel module." That is wrong. Per
the FY24 Guide: "In FY2020, Question 15 was revised, and a new Question
16 was added." The HERD public-use CSVs carry `questionnaire_no` 15 and
16 rows in **2022, 2023, 2024** (~2,400-2,550 rows of each per year):

| Year | Q15 rows | Q16 rows |
|------|----------|----------|
| 2022 | ~2,400 | ~2,390 |
| 2023 | ~2,486 | ~2,486 |
| 2024 | ~2,550 | ~2,550 |

NCSES Data Table 26 (NSF 26-304) publishes aggregate totals for FYs
2020-2024, suggesting 2020-2021 microdata exists somewhere — under the
pre-revision Q15 structure or as aggregate-only. To confirm during W3
when the personnel sibling pipeline runs.

**Implication:** the personnel sibling carries 3 years of microdata
(2022-2024) at minimum, with 2020-2021 published aggregates available
for cross-reference in the methods note. Materially better paired-deposit
story than the 1-year framing.

### 10.2 State-code/ZIP non-data rows are an era-A artifact only

§5.1 calls out `questionnaire_no` matching `^[A-Z]{2}$` or ZIP-like
patterns as non-data tracking rows that must be filtered. HD 1.2
empirically validates that these rows do **not** appear in 2024 at all
(zero non-data rows in the 2024 CSV by that filter). The era-A filter
is still correct to apply universally (cheap, harmless), but the
validation expectation should reflect that era-B rows (2010+) shouldn't
trigger it.

### 10.3 Public reconciliation anchors for the personnel sibling exist

NCSES Data Table 26 (NSF 26-304), stashed at
`data/reference/nsf26304-tab026.pdf`, supplies clean one-cell anchors
for the personnel sibling reconciliation:

- All personnel functions, Headcount, FY 2024: **1,086,850**
- All personnel functions, FTEs, FY 2024: **525,960**
- Plus function-level breakdowns (Researchers / R&D technicians / R&D
  support staff) for FYs 2020-2024.

**Constraint:** Table 26 includes only institutions reporting $1M+ in
total R&D in FY 2023 (standard form population). Reconciliation queries
must filter to the same population, not free-sum across all rows.

### 10.4 §5.2 wording ("1996 fine-detail break") is now superseded

Per Vision Round 2 verdict (PANEL_VISION.md), the `_fine` NULL rule is
dropped entirely. The §5.2 line "The locked schema rule '_fine columns
NULL pre-1996' should be revisited with Vision before we hard-code it"
is resolved: rule is dropped. NULL is a data fact, not a rule.
