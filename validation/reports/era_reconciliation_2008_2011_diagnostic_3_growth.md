# HD 2.1.b Diagnostic 3 — National R&D growth, FY 2008 / 2009 / 2010 / 2011

**Authored by:** Skipper, 2026-05-01.

**Scope:** Pulls HERD all-institutions national R&D totals for FY 2008, 2009, 2010, 2011 to interpret the ~22% institution-total residual (Diagnostic 1, 2008→2011 long-gap) against macro real-growth context. Decides which sub-framing the panel review enters: (b1) <5% cumulative growth (residual is almost entirely definitional drift), (b2) 5-30% (residual decomposes), or (b3) >30% (apparent discontinuity is mostly real growth, framing flips).

## Source

Computed directly from the staged HERD microdata in `data/raw/herd/`, summed across all institutions present in each year. No InfoBriefs or NCSES data tables were fetched; the microdata totals ARE the headline numbers (NSF publishes the same aggregate it produces). Same locked summation rule as the parent residual report:

- **Era A (2008, 2009)**: `question = 'Expenditures by S&E field'`, `row='All'`, `column='Total'`, summed across all institutions.
- **Era B (2010, 2011)**: Q9 + Q11 (`'Federal expenditures by field and agency'` and `'Nonfederal expenditures by field and source'`), `row='All'`, `column='Total'`, summed across all institutions.

**Caveat — current dollars only.** No GDP deflator applied. Deflation is HD 2.5 work. The threshold ladder in the maintainer's sub-framings is specified in current dollars at this stage; constant-dollar growth would be lower than current-dollar growth (BEA GDP price index for R&D rose ~1.5–2.5%/yr in 2008–2011), but the gap between b2 and b3 is wide enough that current-dollar reading is dispositive for sub-framing selection.

**Caveat — population scope.** All-institutions sum, not the standard-form-only filter that NSF Table 26 applies. The published HERD InfoBriefs report all-respondents totals as the headline, so this matches the published-headline definition. Standard-form-only reconciliation is HD 2.7 work.

## National totals

| FY | total ($B, current) | total (kUSD) | n_institutions | source rule |
|---|---:|---:|---:|---|
| 2008 | $51.872B | 51,871,804 | 690 | era_A direct (Expenditures by S&E field, row=All col=Total) |
| 2009 | $54.863B | 54,862,998 | 708 | era_A direct (Expenditures by S&E field, row=All col=Total) |
| 2010 | $61.287B | 61,286,610 | 737 | era_B reconstructed (Q9 + Q11, row=All col=Total) |
| 2011 | $65.274B | 65,274,393 | 896 | era_B reconstructed (Q9 + Q11, row=All col=Total) |

## Growth

| period | growth (current $) |
|---|---:|
| FY2008 → FY2009 | +5.77% |
| FY2009 → FY2010 | +11.71% |
| FY2010 → FY2011 | +6.51% |
| **FY2008 → FY2011 cumulative** | **+25.84%** |

## Sub-framing verdict

**Verdict: (b2) 5-30% — residual decomposes into real growth + definitional drift + Q5 carve-out + unmeasurable residual.**

Cumulative FY2008→FY2011 growth = **+25.84%** in current dollars.

This places the data in the (b2) band: real macro growth and definitional drift are both material contributors to the era-boundary gap. Methods-note must decompose rather than attribute the gap to structural drift alone.

**Decomposition shape.** Note that the institution-total residual (Diagnostic 1, median -22.5% on the fixed top-10 cohort 2008→2011) and the macro growth rate (+25.84% on the all-institutions national pool 2008→2011) measure different things and are NOT directly additive:

- The **residual** is `(era_a_2008 − era_b_recon_2011) / era_a_2008` on a fixed 10-institution cohort. It expresses how much *larger* the era-B reconstruction is than the era-A direct figure for the same institutions.
- The **macro growth** is the pool-wide HERD-defined total change including all institutions (cohort grew from 690 in FY2008 to 896 in FY2011, a ~30% institution-count increase that itself reflects survey expansion, not just real growth).

So the cleaner reading is: HERD-defined national R&D grew ~26% in current dollars between FY2008 and FY2011, with three intertwined drivers — (1) real R&D spending growth, (2) era-B definitional expansion (Q5 clinical trials + training grants + broader scope per FY24 Guide pages 80–83 and 630–633), (3) survey population expansion at the standard-form / short-form boundary in FY2010. The Diagnostic 1 residual measures the same drivers as they show up on a fixed cohort. The Q5 share (Diagnostic 2: ~25% of the adjacent-year gap, ~8pp of the long-gap residual) cleanly sits inside driver (2). What the methods note CANNOT cleanly decompose from HERD alone is the split between (1) and (2): we have HERD-defined growth (which already bakes in the era-B definitional change) but no era-A-equivalent FY2010+ recomputation, so a true "real growth net of definitional change" series would require either external data (BEA / NIPA R&D-by-sector for higher ed, with caveats) or a same-population-same-rule recomputation we are not in scope to build at HD 2.1.

**Methods-note framing locks with this decomposition.** The contribution claim sharpens from *we documented a discontinuity* to *we decomposed it into real macro growth (HERD-defined ~26% over 3 years), a named definitional carve-out we can size (Q5 clinical trials, ~8pp of the long-gap institution-total residual), survey-population expansion at the era boundary (cohort N grew 690→896), and a remaining quantifiable-but-not-internally-explained residual (training grants per FY24 Guide; broader era-B scope language).* This is more methodologically substantive than (b1)'s "structural drift dominates" framing and supports a stronger Thesis-D narrative — the methods note teaches the reader to read the era boundary correctly rather than asserting one driver wins.

## Duke anomaly footnote

Diagnostic 2 reported Duke University's Q5 clinical-trials share at 32.25% (2010) / 32.59% (2011), which **exceeds** Duke's institution-total residual (-22.14% / -33.29%) — i.e., Duke's clinical-trials reporting is larger than the apparent definitional gap at the institution-total grain. Two readings: (i) era A captured some Duke clinical-trial dollars at the institution-total grain that era B's Q5 also captures, making clinical trials *not entirely net new* at the era boundary for Duke (the Q5 carve-out softens as a uniform driver); (ii) Duke's Q5 reporting includes activity beyond the strict FY24 Guide page 14 clinical-trials definition (Duke's health-system reporting practices may include items the Guide doesn't strictly enumerate). Either reading complicates the clean "FY24 Guide page 14 explains the W2 carve-out" account. The methods note should flag this as a known per-institution complication, not lean on Guide page 14 as the full explanation of definitional drift.

## Reproducibility

Script: `etl/spikes/national_totals_2008_2011.py`. Loader: `etl/_load.py read_herd_csv(year)`. Era-A filter: `question = 'Expenditures by S&E field'`, `row='All'`, `column='Total'`, summed across all institutions in the year. Era-B filter: Q9 + Q11 same row/column, summed across all institutions. No deflator. No standard-form-only filter (matches published all-respondents headline; HD 2.7 owns the standard-form reconciliation).
