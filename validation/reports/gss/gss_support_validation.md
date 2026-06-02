# GSS Support panel — validation report (HD 4.2 MVP)

**Artifact:** `data/harmonized/gss_support.parquet` — the long-format GSS funding
face (full-time graduate students by support mechanism × federal agency ×
fed/nonfed, FY1972–2024, native-UNITID-keyed). Built by `etl/build_gss_support.py`
from the converted CSVs (`etl/acquire_gss.py`) via the Support-column crosswalk
(`crosswalks/gss/support_column_map.csv`). **Date:** 2026-06-02.

- **Rows:** 10,847,111 · **Institutions:** 849 (UNITID, union over 53 years) ·
  **Span:** FY1972–2024 · **Size:** 22.6 MB · **SHA-256:**
  `de8acded3032ef1d31a7473597abae7fc32a8675074e4d0882bff81556f72010`
- **Grain:** non-zero values only; an omitted (institution × field × degree ×
  gender × mechanism × source × agency) cell is a **structural zero** (GSS reports
  a complete grid with explicit zeros — 2023: 86.5% of support cells are 0, 13.5%
  positive, 0 empty/suppressed; the convention is lossless).

## 1. Cross-sheet reconciliation (lossless-melt receipt) — EXACT

The parquet's canonical core tuple *(all_grad, total, all-mechanism, all_sources,
all-agency)*, summed over institution × field, must equal the Race sheet's
full-time grand total (`ft_tot_all_races_v`) — the independent cross-sheet anchor
(HD 4.1 gate). Reproduced **to the unit**, confirming the wide→long melt +
crosswalk + structural-zero drop is lossless:

| Year | Parquet all-grad/all-sources FT total | Race `ft_tot` (gate) | Match |
|------|----------------------------------------|----------------------|-------|
| 1975 | 219,648 | 219,648 | ✓ |
| 2008 | 449,613 | 449,613 | ✓ |
| 2023 | 598,588 | 598,588 | ✓ |

## 2. Two-number spine receipt (§4)

Distinct GSS UNITIDs resolved to `crosswalks/_shared/institution_identity.csv`
(HERD + FedSupport spine), reported as institution-match AND FT-headcount-weighted
match:

| Year | Institution-match | Count-weighted match |
|------|-------------------|----------------------|
| 1975 | 523/529 = 98.9% | 217,574 / 219,648 = 99.1% |
| 2008 | 579/585 = 99.0% | 447,572 / 449,613 = 99.5% |
| 2023 | 679/697 = 97.4% | 595,636 / 598,588 = 99.5% |

The funding face joins the HERD+FedSupport universe on ~97–99% of institutions and
≥99% of headcounts; the unmatched residual is the GSS-only institutions (research
institutes + branches, HD 4.1 Check 2) the spine expands to absorb.

## 3. 2017 boundary continuity (clause-b)

The all-grad all-sources core is **continuous** across the 2017 redesign — a
modest step, not a cliff (national FT all-grad all-sources total):

| 2014 | 2015 | 2016 | 2017 | 2018 | 2019 |
|------|------|------|------|------|------|
| 492,170 | 506,262 | 508,773 | 480,788 | 491,449 | 502,442 |

The 2016→2017 step (−5.5%) is the redesign/frame change; the named clause-(b)
components (secondary-axis swap gender→degree, agency relabel `hhs_nih`→`nih`,
mechanism abbreviations) are documented in `crosswalks/gss/support_column_map.csv`
and `docs/gss/hd_4_2_build_scope.md`. The crosswalk reconciles pre/post spellings
to one canonical tuple, so the series is continuous by construction.

## 4. Funding-face decomposition (sanity, 2023, all-grad total)

Source classes sum exactly to the all-sources total (598,588): federal 82,764 ·
nonfederal 261,737 · self-support 254,087. Federal agencies sum exactly to the
federal total (82,764): **NIH 23,172 · NSF 21,209 · other-federal 14,631 · DOD
9,171 · DOE 5,757 · USDA 3,332 · HHS-other 3,314 · NASA 2,178** — the same agency
taxonomy as HERD (R&D-out by agency) and FedSupport (federal S&E obligations by
agency), joinable on the institution-year hub.

Degree levels present post-2017 (2023 rows): all_grad 271,096 · doctoral 183,670 ·
masters 158,200.

## 5. Reproducibility

- **A1 determinism:** byte-identical across **three** consecutive builds (total
  `ORDER BY`; the structural-zero grain + crosswalk join are deterministic).
- **A1b validity:** the crosswalk is UTF-8/LF, ASCII-clean; the parquet is binary
  (`*.parquet binary` in `.gitattributes`).
- **Runtime:** `duckdb` + `pypdf` only — no new dependency (acquisition is stdlib).

## 6. Known scope (MVP)

- **Field names deferred.** `gss_code` (131 distinct) / `hdg_code` carried raw;
  `field_coarse`/`field_fine` NULL pending the NCSES GSS field-code reference.
- **Support sheet only.** The Race (enrollment/demographic) and PD_NFR (postdoc)
  siblings are deferred to later increments.
- **Suppression.** No empty/suppressed support cells observed (2023 fully numeric);
  a suppression flag is a future refinement if early years differ.
