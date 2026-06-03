# GSS PD_NFR (postdoc + non-faculty-researcher) panel — validation report (HD 4.3)

**Artifact:** `data/harmonized/gss_pd_nfr.parquet` — long-format postdoctoral
appointees and doctorate-holding non-faculty researchers, FY1972–2024,
native-UNITID-keyed. Built by `etl/build_gss_pd_nfr.py` via
`crosswalks/gss/pd_nfr_column_map.csv`. **Date:** 2026-06-02.

- **Rows:** 4,130,678 · **Institutions:** 541 · **Span:** FY1972–2024 · **Size:**
  9.4 MB · **SHA-256:** `a06c88cda12b662526a67e7f57a09e34f0510c84aa468074a0262ad2edecf211`
- **Overlapping-marginal grain (`measure_group`).** The PD_NFR source sheet is
  **several marginal tables sharing the same totals** (postdoc decomposed by
  support, by degree-type, by citizenship, by gender×mechanism; plus the NFR
  block). Each row carries a `measure_group` ∈ {`support`, `demographic`,
  `mechanism_degree`, `citizenship_degree`, `gender_mechanism`, `gender_support`,
  `degree_origin`, `nfr_demographic`}. **A consumer sums WITHIN a group, never
  across** (which would double-count). Confirmed consistent: the `support`
  marginal and the `demographic` marginal both total **65,850** postdocs (2023).
- **Crosswalk:** 320 columns → 100% coverage (0 unmapped), reconciling the 2017
  relabel (felshp=fel, trneeshp=trn, rsch_grnt=grt, oth_mech=om, `_degr` dropped,
  nmed=nonmedical, unk=unknown, hhs_nih=nih, nonfed=nfed). Non-zero grain.
  Field names deferred (`gss_code` raw).

## 1. §5 published-ground-truth anchor — PASS (Tables 1-9b / 3-2 / 3-4 / 1-2a)

All 16 reconciliation cells exact (2023, "All surveyed fields"):

| Measure | Parquet | Published | Table |
|---|---|---|---|
| Postdoc total | 65,850 | 65,850 | 1-9b / 1-2a |
| NFR total | 34,342 | 34,342 | 1-2a |
| Postdoc federal | 32,155 | 32,155 | 3-2 |
| — institutional | 16,011 | 16,011 | 3-2 |
| — nonfederal-domestic | 9,579 | 9,579 | 3-2 |
| — foreign | 1,159 | 1,159 | 3-2 |
| — self-support | 726 | 726 | 3-2 |
| — unknown | 6,220 | 6,220 | 3-2 |
| Federal: DOD | 2,304 | 2,304 | 3-4 |
| Federal: DOE | 2,172 | 2,172 | 3-4 |
| Federal: NIH | 18,732 | 18,732 | 3-4 |
| Federal: HHS-other | 841 | 841 | 3-4 |
| Federal: NASA | 724 | 724 | 3-4 |
| Federal: NSF | 3,853 | 3,853 | 3-4 |
| Federal: USDA | 1,104 | 1,104 | 3-4 |
| Federal: other | 2,425 | 2,425 | 3-4 |

(Source classes sum to 65,850; agencies sum to the federal 32,155.) Postdoc by
sex (1-2a) also exact: male 37,458 + female 28,392 = 65,850. **Verdict: PASS.**

## 2. Two-number spine receipt (§4, postdoc-total headcount)

| Year | Institution-match | Count-weighted |
|---|---|---|
| 1980 | 256/261 = 98.1% | 18,200 / 18,399 = 98.9% |
| 2008 | 298/302 = 98.7% | 53,560 / 54,164 = 98.9% |
| 2023 | 334/341 = 97.9% | 64,192 / 65,850 = 97.5% |

## 3. Reproducibility
A1: byte-identical across 3 consecutive builds (re-confirmed after the field-code
join; §5 values unchanged). Runtime `duckdb` + `pypdf`. `field_coarse`/`field_fine`
populated for the 91 2023-active `gss_code`s (69.0% of rows) via
`crosswalks/gss/field_code_map.csv` (count-matched to Table 4-3); historical-only
codes NULL pending the dedicated TOD reference (HD 4.3 step 4).

The NIH dominance of postdoc federal support (18,732 / 32,155 = 58%) vs. the more
balanced NIH/NSF split among graduate students is the funding-of-human-capital
signal GSS contributes to the funding→people→productivity thread (§1).
