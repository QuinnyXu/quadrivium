# GSS Race (enrollment/demographic) panel — validation report (HD 4.3)

**Artifact:** `data/harmonized/gss_race.parquet` — long-format graduate-student
enrollment by enrollment-status × degree × gender × race, FY1972–2024,
native-UNITID-keyed. Built by `etl/build_gss_race.py` via
`crosswalks/gss/race_column_map.csv`. **Date:** 2026-06-02.

- **Rows:** 12,661,021 · **Institutions:** 854 · **Span:** FY1972–2024 · **Size:**
  22.3 MB · **SHA-256:** `ce2b3527046ecd9a16dc2b014204cd680eb6a4006513573286294f14abaab6be`
- **Grain:** non-zero values; omitted cell = structural zero. Field names deferred
  (`gss_code` raw; `field_coarse/fine` NULL). `enrollment_status` ∈ {full_time,
  part_time, full_time_first_year} (first-year is a **subset** of full_time —
  total grad = full_time + part_time); `degree_level` ∈ {all_grad, masters,
  doctoral} (ma/dr post-2017); `gender` ∈ {total, men, women}; `race` modern OMB-1997
  set + retained pre-1998 legacy (`asian_pacific_legacy`, `other_legacy`).
- **Crosswalk:** 300 columns → 282 canonical tuples, 100% coverage. The race
  taxonomy is **pre-bridged** (HD 4.1 Check 3): legacy `asian_pi_98`/`other_98`
  map to distinct `*_legacy` race values (kept, not dropped, §4); the 2017
  relabels `multi_non_hisp`↔`multi`, `unknown`↔`unk` reconcile to one tuple.

## 1. §5 published-ground-truth anchor — PASS (Tables 4-3, 1-2a; NSF 25-317)

All cells exact (2023):

| Measure | Parquet | Published | Table |
|---|---|---|---|
| Total grad (FT+PT) | 818,095 | 818,095 | 4-3 / 1-2a |
| All full-time | 598,588 | 598,588 | 4-3 |
| First-time full-time | 203,798 | 203,798 | 4-3 |
| Part-time | 219,507 | 219,507 | 4-3 |
| Male (FT+PT) | 422,321 | 422,321 | 1-2a |
| Female (FT+PT) | 395,774 | 395,774 | 1-2a |
| Master's total (FT+PT) | 510,866 | 510,866 | 4-3 |
| Doctoral total (FT+PT) | 307,229 | 307,229 | 4-3 |

(Master's 510,866 + Doctoral 307,229 = 818,095; Male 422,321 + Female 395,774 =
818,095.) **Verdict: PASS.**

## 2. Cross-sheet + internal consistency
Full-time all-grad totals match the Support panel and the Race source exactly
(1975 = 219,648; 2008 = 449,613; 2023 = 598,588). Men + women = total at every
spot-year (2023 FT: 309,437 + 289,151 = 598,588).

## 3. Two-number spine receipt (§4, all_grad FT+PT headcount)

| Year | Institution-match | Count-weighted |
|---|---|---|
| 1975 | 551/557 = 98.9% | 325,066 / 328,510 = 99.0% |
| 2008 | 587/593 = 99.0% | 628,537 / 631,489 = 99.5% |
| 2023 | 683/702 = 97.3% | 814,389 / 818,095 = 99.5% |

## 4. Reproducibility
A1: byte-identical across 3 consecutive builds (re-confirmed after the field-code
join; §5 values unchanged). Runtime `duckdb` + `pypdf`. `field_coarse`/`field_fine`
populated for the 91 2023-active `gss_code`s (83.5% of rows) via
`crosswalks/gss/field_code_map.csv` (count-matched to Table 4-3); historical-only
codes NULL pending the dedicated TOD reference (HD 4.3 step 4).
