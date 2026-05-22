# HD 2.1.b Diagnostic 1 — Institution-total grain residual re-run

**Authored by:** Skipper, 2026-05-01 (post-residual diagnostic).

**Scope:** Re-runs the residual computation at the `row='All', column='Total'` (institution-total) grain rather than the coarse-bucket grain. Same 10 institutions as `era_reconciliation_2008_2011.md`. Hypothesis under test (per maintainer's directive): institution-total residuals show the same systematic direction as bucket-level (era-B > era-A by 5–25%) but with smaller magnitude — corroborating the definitional-drift reading (era B includes clinical trials and research training grants that era A excluded; FY24 Guide page 14).

**Sign convention:** `residual = (era_a - era_b_recon) / era_a`. A *negative* residual means era-B reconstruction is **larger** than era-A direct (era-B > era-A), consistent with the hypothesis.

## Sample

Same 10 institutions as the parent residual report (top-10 by FY 2008 row='All' column='Total' in `Expenditures by S&E field`, present in all of FY 2009 / 2010 / 2011):

| rank | inst_id | inst_name | fy2008_total_kusd |
|---:|---|---|---:|
| 1 | 029977 | Johns Hopkins University | 1,680,927 |
| 2 | 001319 | University of California, San Francisco | 885,182 |
| 3 | 003895 | University of Wisconsin Madison | 881,777 |
| 4 | 001315 | University of California, Los Angeles | 871,478 |
| 5 | 001317 | University of California, San Diego | 842,027 |
| 6 | 002920 | Duke University | 766,906 |
| 7 | 003378 | University of Pennsylvania | 708,244 |
| 8 | 008802 | Ohio State University all campuses | 702,592 |
| 9 | 001305 | Stanford University | 688,225 |
| 10 | 002178 | Massachusetts Institute of Technology | 659,626 |

## Per-institution institution-total residuals

| inst_id | inst_name | era_a_2008_kusd | era_a_2009_kusd | era_b_recon_2010_kusd | era_b_recon_2011_kusd | residual_2009_2010_pct | residual_2008_2011_pct |
|---|---|---:|---:|---:|---:|---:|---:|
| 029977 | Johns Hopkins University | 1,680,927 | 1,856,270 | 2,004,482 | 2,145,308 | -7.98% | -27.63% |
| 001319 | University of California, San Francisco | 885,182 | 947,697 | 935,509 | 995,226 | +1.29% | -12.43% |
| 003895 | University of Wisconsin Madison | 881,777 | 952,119 | 1,029,295 | 1,111,642 | -8.11% | -26.07% |
| 001315 | University of California, Los Angeles | 871,478 | 889,995 | 936,995 | 982,357 | -5.28% | -12.72% |
| 001317 | University of California, San Diego | 842,027 | 879,357 | 943,219 | 1,009,378 | -7.26% | -19.87% |
| 002920 | Duke University | 766,906 | 805,021 | 983,289 | 1,022,207 | -22.14% | -33.29% |
| 003378 | University of Pennsylvania | 708,244 | 726,768 | 836,322 | 886,036 | -15.07% | -25.10% |
| 008802 | Ohio State University all campuses | 702,592 | 716,461 | 755,194 | 832,126 | -5.41% | -18.44% |
| 001305 | Stanford University | 688,225 | 704,183 | 839,839 | 907,971 | -19.26% | -31.93% |
| 002178 | Massachusetts Institute of Technology | 659,626 | 736,102 | 677,138 | 723,610 | +8.01% | -9.70% |

## Across-institution distribution

| year_pair | n | median | Q1 | Q3 | sign: negative (era-B > era-A) | sign: positive (era-A > era-B) |
|---|---:|---:|---:|---:|---:|---:|
| 2009→2010 (adjacent) | 10 | -7.62% | -13.33% | -5.31% | 8 | 2 |
| 2008→2011 (long-gap sanity) | 10 | -22.49% | -27.24% | -14.15% | 10 | 0 |

## Synthesis

- **Direction (2009→2010):** era-B > era-A. Sign-consistent across all 10 institutions: **False** (8 negative / 2 positive).
- **Direction (2008→2011):** era-B > era-A. Sign-consistent across all 10 institutions: **True** (10 negative / 0 positive).
- **Median magnitude:** -7.62% (2009→2010); -22.49% (2008→2011).

**Hypothesis read.** If institution-total residuals are sign-consistent across institutions and in the same direction as the bucket-level gap (parent report: 5 of 7 gating buckets era-B > era-A), the definitional-drift hypothesis is corroborated at the institution-total grain. Mixed sign across institutions would suggest the picture is messier than a single uniform definitional shift.

## Reproducibility

Script: `etl/spikes/residual_2008_2011_diagnostics.py`. Imports selection logic and `era_a_total_all` from `etl/spikes/residual_2008_2011.py`. Era-B institution total: Q9 row='All' column='Total' + Q11 row='All' column='Total' (`era_b_institution_total`). Same 10 institutions as the parent report.
