# HD 4.1 — GSS gate-spike findings (dataset #3 kickoff)

**Status:** read-only probe complete; **VERDICT: GO** for the full GSS build (no
reopen-sequencing). Awaiting maintainer authorization before any loader/schema.
**Date:** 2026-06-02. **Scope:** scope-first probe only — no loader, no schema,
no dataset commit. Mirrors the HD 3.1 → HD 3.2 gate → scope → build sequence.

GSS = NSF/NCSES **Survey of Graduate Students and Postdoctorates in S&E** (GSS),
staged at `data/raw/gss/` as 53 per-year zips FY1972–2024, each carrying
`gssYYYY_code.sas7bdat` (microdata-format) + `gssYYYY_Code.xlsx` (3-sheet wide
tabulation). Ratified as dataset #3 (`seeds/overrides.md` 2026-05-31), GSS-first,
SED deferred. Kill condition (override §12): a fatal identity-join problem (no
clean key) **OR** a non-decomposable discontinuity → reopen GSS-first sequencing.
**Neither fired.**

All numbers below were produced by stdlib-only read-only probes (xlsx = zip+XML;
`zipfile` + `xml.etree`), installing nothing and reading no bytes the pinned
runtime can't. Probe scripts are reproducible and can be promoted to
`etl/spikes/gss/` if the build is authorized.

---

## Check 1 — §3 acquisition-format decision (pivotal: GSS is NOT CSV-native)

Neither `sas7bdat` nor `xlsx` loads under the pinned runtime (`duckdb` + `pypdf`
only — confirmed empirically: `pandas`/`openpyxl`/`pyreadstat` all absent). Per
the §3 acquisition-format lock, convert **once, at acquisition, to CSV**.

**(a) Source-of-truth — do SAS and XLSX carry the same records?**
The XLSX is the **published wide tabulation**: 3 sheets (Race, Support, PD_NFR),
one row per **institution × field** (`gss_code`/`hdg_code`), counts as columns,
**native `UNITID` in column B**. Internal reconciliation is exact:

| Year | Race rows | Support rows | Race FT-total | Support FT-total | Frame match | Total match |
|------|-----------|--------------|---------------|------------------|-------------|-------------|
| 1975 | 7,741 | 7,741 | 219,648 | 219,648 | ✓ | ✓ (exact) |
| 2008 | 9,782 | 9,782 | 449,613 | 449,613 | ✓ | ✓ (exact) |

The 3 sheets share one institution×field frame and cross-foot exactly. The
`sas7bdat` is a valid 64-bit little-endian SAS file (1975: page_size 131072 ×
113 pages = 14,811,136 B = file size exactly) — the same data in microdata
format. Exact SAS↔XLSX **row-count** reconciliation is the only step needing a
SAS reader (`pyreadstat`); because XLSX is authoritative (below), that is a
**one-time acquisition provenance cross-check, not a build dependency.**

**(b) Conversion path — DECISION: XLSX → CSV (per sheet), authoritative; SAS kept as provenance sibling.**
The XLSX sheets *are* the analytical product at our exact target grain
(institution × field × demographic / support-mechanism counts, UNITID-keyed). A
**stdlib XLSX→CSV converter** (Race/Support/PD_NFR → 3 CSVs/year) reads them with
**zero new dependencies** — strictly better than the FedSupport precedent, which
feared a SAS→`pyreadstat` path. The `sas7bdat` is retained as the provenance/
audit sibling (analogous to FedSupport's PDF audit sibling). **Runtime stays
`duckdb` + `pypdf`; conversion is acquisition-time only.**

> Implementation note for the converter: the XLSX `<dimension>` ref is the bogus
> Excel-max `A1:…1048576`; the converter must count actual `<row>` elements, not
> trust the dimension (the probe already does this).

**(c) v3.0 deposit-hygiene gates carried forward from the start.** Converted CSVs
are **generated** → the generator emits UTF-8/LF (the HD-4.x complement to
`_load_fedsupport.write_text_clean`). The as-downloaded zips (SAS + XLSX) are
**provenance** → `-text` in `.gitattributes` + SHA-256 pins in
`data/raw/MANIFEST.md` so the blanket `eol=lf` can't strip them (per the
2026-06-02 inverted-provenance finding). Index/HEAD `cat-file` blob checks, zero
NUL, and provenance==MANIFEST gates apply.

**This §3 decision sets the pattern for every future NCSES-microdata-zip survey
(SED, other surveys arriving as SAS+XLSX): XLSX→CSV stdlib-authoritative, SAS as
provenance sibling, no new runtime dep.**

---

## Check 2 — two-number spine-join receipt (identity)

GSS carries **native IPEDS UNITID on 100% of rows in every year 1972–2024**
(`uidMiss = 0` for all 53 years). There is **no era-A UNITID gap** — the decisive
contrast with HERD (whose pre-2010 rows are UNITID-NULL). A small number of rows
carry the `999999` "no-IPEDS-match" sentinel (e.g. Scripps Research Institute,
≈1 institution / 478 students in 2023) — a bounded, named residual analogous to
FedSupport's `na_ffrdc`, **not** a coverage gap.

Resolving the GSS institution set to `crosswalks/_shared/institution_identity.csv`
(the HERD + FedSupport spine, 2,679 UNITIDs) by native UNITID, **two distinct
rates** per §4 (GSS's value axis is **headcounts**, so the count-weighted rate is
thread-critical):

| Era (sample) | Institution-match | Count-weighted match | Distinct GSS UNITIDs |
|---|---|---|---|
| 1972 | 98.8% | 99.6% | 257 |
| 1984–1987 (frame contraction) | ~97.4% | **~92.8–93.0%** | ~420 |
| 2000 | 98.2% | 99.0% | 608 |
| 2010 | 99.0% | 99.6% | 592 |
| 2023 | 97.3% | 99.5% | 706 |
| **Range, all 53 yrs** | **97.0–99.1%** | **92.8–99.7%** | 257–733 |

GSS overlaps the HERD+FedSupport funding universe almost entirely — the
human-capital face joins the funding faces on ~97–99% of institutions and ~93–99.7%
of headcounts. The **1984–1987 count dip to ~93%** (institution-match steady at
~97.4% but a few large institutions carrying ~7% of students fall outside the
spine those years) is the one notable feature — flagged for the build's
clause-(c) receipt, not a blocker. **Kill condition (no clean key): NOT
triggered** — UNITID is native, complete, and campus-grained (see Check 4).

What GSS *adds* to the registry is small: **19 GSS-only UNITIDs in 2023** (not in
the spine), mostly PhD-granting research institutes (Scripps, Mayo Graduate
School, Memorial Sloan Kettering, City of Hope, Sanford-Burnham, American Museum
of Natural History) and branch campuses — the spine expands modestly to absorb
them (per §10 active-survey-set scope).

---

## Check 3 — RH era-boundary decomposability (the discontinuities)

GSS discontinuities are **measure-taxonomy + frame** shifts, not identity
boundaries. Each is RH-decomposable:

1. **Race-category taxonomy (OMB-1997) — PRE-BRIDGED by NCSES.** For **1972–2016**
   the Race sheet carries *both* the legacy pre-98 categories (`asian_pi_98`,
   `other_98`) **and** the modern OMB-1997 split (`asian`, `pacific`,
   `multi_non_hisp`) as **parallel columns**. Clause-(a) reconstruction of either
   era is therefore *direct from the file* (no inference); clause-(b) the boundary
   is explicit — at **2017** the legacy columns are simply retired (30 columns
   removed) with **no information loss** (the modern categories continue
   unbroken). This is the cleanest possible taxonomy discontinuity.

2. **2017 redesign — additive detail, continuous backbone.** Race sheet **122 →
   290 columns**: −30 legacy race columns, **+198 new `dr_` (doctoral-level)
   disaggregation** columns across the race × gender × enrollment crossing. The
   institution × field × total-grad backbone is continuous across the boundary
   (the national series grows smoothly: 2016 = 684,825 → 2017 = 649,112 →
   2023 = 818,095). Clause-(b) decomposes the boundary into named components:
   (i) legacy-race retirement (redundant, lossless), (ii) doctoral-level detail
   added (new, additive), (iii) first-year (`frst`) race detail restructured.

3. **Support-sheet re-coding at 2017 — a crosswalk object (funding face
   preserved).** The Support sheet is also re-coded at 2017 (column names change:
   `ft_tot_fed_nsf_v` → `dr_ft_*_fed_nsf_v` family; `hhs_nih`/`hhs_oth` →
   `nih`/`hhs`; mechanism abbreviations `felshp`→`fel`, `rsch_asst`→`ra`), and
   grows to 365 columns. The **semantics are preserved** (mechanism × federal
   agency × federal/nonfederal); this is a clause-(a)/(b) **support-taxonomy
   crosswalk** exactly like the HERD question-map, not a break.

4. **Frame seams (empirically surfaced, beyond the grounding's late-2000s/2017
   flags).** A **1984–1987 frame contraction** (distinct institutions ~610 → ~420,
   the count-match dip above) and a **2014 frame expansion** (~582 → ~725) are
   population/frame changes — the HERD-style cohort/national-pool decomposition
   (à la the 2008→2011 four-driver) applies. The grounding's "late-2000s
   re-baseline" shows **no Race-sheet structural change** (ncols flat at 122
   through 2016); any late-2000s effect is a frame/weighting change, not a
   measure redefinition.

**Kill condition (non-decomposable discontinuity): NOT triggered.** Every GSS
discontinuity is clause-(a) reconstructible and clause-(b) decomposable; the race
taxonomy is *pre-bridged*, and the 2017 redesign is additive over a continuous
backbone.

---

## Check 4 — class-(b) requirements-discovery (grain / Seam B)

**GSS grain is campus-clean — the inverse of FedSupport's Seam-B problem.** GSS
reports at **native campus-level IPEDS UNITID**: Texas A&M → **8 distinct campus
UNITIDs** (College Station 228723, Corpus Christi, Commerce, Kingsville,
International, West Texas, …), University of California → **10** (Berkeley 110635,
Davis, Irvine, UCLA, …), Wisconsin → **11**, Massachusetts → 7, Maryland → 6
(single-UNITID systems like Penn State 214777, Johns Hopkins 162928, Ohio State
204796 are single because that is their *IPEDS* structure). The GSS field grain
(`gss_code`) sits **below** the institution key and does **not** touch identity.

**Requirements-discovery for IPEDS #4 (the B-first rationale, override §12):**
- GSS does **not** stress the system-vs-campus seam the way the override
  hypothesized; it **relieves** it. Because GSS is campus-grained natively, it is
  a ready **campus-enumeration reference** for decomposing FedSupport's
  *system-level* obligations (which campuses exist under a system, and their
  relative headcount size) — an asset to the Seam-B decomposition, not a new
  burden.
- The genuine new requirement GSS surfaces is smaller and different: (i) the
  registry must absorb a **PhD-granting research-institute sub-universe**
  (Scripps/Mayo/Sloan Kettering — outside the R&D-survey universe), and (ii) a
  few GSS institutions carry **newer `49xxxx`-block UNITIDs** for plausibly
  related entities (Purdue 490805, Texas Tech 492689, Western Michigan 490373 —
  small branch/satellite counts), a concrete instance of the **UNITID-vintage /
  reassignment** problem §4/§10 already defer to the IPEDS cycle.

**Honest calibration (for Vision, override §12 kill condition):** B-first's
requirements-discovery value is **real but smaller than projected** — GSS is so
identity-clean that it confirms IPEDS #4 can resolve at campus grain (which GSS
already uses) rather than surfacing a novel seam requirement. The **primary**
deciding rationale (GSS = the funding-of-human-capital third face completing the
thesis) is **fully vindicated** (Thesis, below). This does not fire the kill
condition (GSS did surface *a* requirement — the research-institute sub-universe
and UNITID-vintage hints) but it does down-weight the discovery argument relative
to the thesis argument.

---

## Thesis confirmation — GSS is the funding-of-human-capital face

The **Support sheet is present and joinable across the full 1972–2024 span**
(verified 1972 / 2000 / 2017 / 2024). It carries the funding axis at the
institution × field grain: **support mechanism** (fellowship / traineeship /
research-assistantship / teaching-assistantship / other) × **federal agency**
(DOD, DOE, HHS/NIH, NASA, NSF, USDA, other) × **federal vs nonfederal** (institutional,
other-US, foreign, self-support). Post-2017 it is *richer* (doctoral-level
`dr_*` breakouts: `dr_ft_ra_fed_nih_v`, `dr_ft_fel_fed_nsf_v`, …).

This is precisely what makes GSS the **funding → people → productivity** face
(§1): it composes with HERD (R&D expenditure-OUT by federal agency) and the
FedSupport module (federal S&E obligations-IN by agency) on the **institution-year
hub**, via a **shared federal-agency taxonomy** (NSF, NIH, DOD, DOE, NASA, USDA).
The near-term productivity tier (funding-conversion efficiency) gains a
human-capital denominator — federally-funded graduate researchers and postdocs
per research dollar — without leaving the survey-data envelope.

---

## Verdict + recommended next step

- **Kill condition 1 (no clean identity key): NOT triggered** — 100% native
  campus-level UNITID, all 53 years; 97–99% institution / 93–99.7% count spine
  match.
- **Kill condition 2 (non-decomposable discontinuity): NOT triggered** — every
  boundary is clause-(a) reconstructible / clause-(b) decomposable; race taxonomy
  pre-bridged; 2017 redesign additive over a continuous backbone.
- **Thesis: confirmed** — the Support funding face joins HERD + FedSupport on the
  institution-year hub across the full span.

**GO for the full GSS build** (GSS-first sequencing holds; no reopen). Recommended
build shape mirrors HD 3.2: (1) acquisition — stdlib XLSX→CSV conversion (3
sheets/year), SAS provenance sibling, `data/raw/MANIFEST.md` SHA pins + `-text`;
(2) long-format harmonized panel on institution × field × enrollment-status ×
demographic × support-mechanism, native-UNITID-keyed; (3) crosswalks for the
race-taxonomy bridge, the 2017 support re-coding, and the `gss_code`/`hdg_code`
field taxonomy; (4) two-number spine receipt + the 1984–87 / 2014 / 2017 boundary
decompositions; (5) v3.0 deposit-hygiene gates from the start.

**STOP — awaiting maintainer authorization before any loader/schema/dataset
commit.**
