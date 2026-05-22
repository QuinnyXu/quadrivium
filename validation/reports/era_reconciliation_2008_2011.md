# HD 2.1.b Era Reconciliation Residual Report (FY 2008 / 2009 / 2010 / 2011)

**Authored by:** Skipper, 2026-05-01.

**Scope:** HD 2.1.b residual gate per `docs/hd_2_1_scoping.md` §3. Tests the locked summation rule (§2.1: era-B all-source total = Q9 Total + Q11 Total) against era-A direct field-level totals at the institution × coarse-bucket level. Top-10 institutions by FY 2008 R&D × 7 gating buckets + 2 supporting buckets, year-pairs 2009→2010 (adjacent) and 2008→2011 (long-gap sanity).

**Path B locked.** External-referent search (Step 1 of HD 2.1.b) canvassed NSF, NCSES, ASEE, and academic literature for a published numerical tolerance for the 2010 era boundary. None surfaced — NCSES guidance is qualitative ("exact comparisons may be misleading; contact NCSES"). The locked 5%/15% thresholds remain in force as empirically/descriptively grounded; the methods note will footnote: *"Thresholds set descriptively against practitioner reporting-noise priors; no published NSF/NCSES tolerance surface found at HD 2.1.b external search (sources canvassed: NCSES HERD methodology pages 2021–2024; NSF Science & Engineering Indicators NSB-2025-7; ASEE Engineering by the Numbers; academic literature using HERD longitudinally)."*

## Gate verdict

**REOPEN**

Triggers:

- Bucket-median trigger: Engineering median residual = -5.95% (>5%)
- Bucket-median trigger: Math & CS median residual = -13.98% (>5%)
- Bucket-median trigger: Physical sciences median residual = -5.26% (>5%)
- Bucket-median trigger: Psychology median residual = -20.91% (>5%)
- Bucket-median trigger: Social sciences median residual = +14.10% (>5%)
- Cell trigger: Johns Hopkins University (029977) × Math & CS = -18.79% (>15%)
- Cell trigger: Johns Hopkins University (029977) × Psychology = -101.02% (>15%)
- Cell trigger: University of Wisconsin Madison (003895) × Math & CS = -16.56% (>15%)
- Cell trigger: University of Wisconsin Madison (003895) × Social sciences = +40.74% (>15%)
- Cell trigger: University of California, Los Angeles (001315) × Social sciences = +15.29% (>15%)
- Cell trigger: University of California, San Diego (001317) × Math & CS = +15.46% (>15%)
- Cell trigger: University of California, San Diego (001317) × Psychology = -20.08% (>15%)
- Cell trigger: Duke University (002920) × Engineering = -15.40% (>15%)
- Cell trigger: Duke University (002920) × Life sciences = -24.35% (>15%)
- Cell trigger: Duke University (002920) × Math & CS = -18.17% (>15%)
- Cell trigger: Duke University (002920) × Psychology = -20.91% (>15%)
- Cell trigger: University of Pennsylvania (003378) × Math & CS = -19.58% (>15%)
- Cell trigger: University of Pennsylvania (003378) × Psychology = -26.12% (>15%)
- Cell trigger: University of Pennsylvania (003378) × Social sciences = +15.03% (>15%)
- Cell trigger: Ohio State University all campuses (008802) × Psychology = -56.45% (>15%)
- Cell trigger: Ohio State University all campuses (008802) × Social sciences = +44.75% (>15%)
- Cell trigger: Stanford University (001305) × Engineering = +19.07% (>15%)
- Cell trigger: Stanford University (001305) × Life sciences = -17.54% (>15%)
- Cell trigger: Stanford University (001305) × Physical sciences = -115.06% (>15%)
- Cell trigger: Stanford University (001305) × Social sciences = -17.09% (>15%)
- Cell trigger: Massachusetts Institute of Technology (002178) × Life sciences = +52.50% (>15%)
- Cell trigger: Massachusetts Institute of Technology (002178) × Psychology = -31.77% (>15%)

## Sample

- **Top-10 institutions** (selected by FY 2008 row='All' column='Total' in `Expenditures by S&E field`):

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

- **Substitutions** (institutions in the rank-stream skipped because they were missing one or more of FY 2009 / 2010 / 2011):

| dropped_inst_id | dropped_inst_name | reason |
|---|---|---|
| 009091 | University of Michigan all campuses | missing 2010,2011 |
| 003798 | University of Washington | missing 2010,2011 |
| 008813 | Pennsylvania State University all campuses | missing 2010,2011 |
| 008761 | University of Minnesota all campuses | missing 2010,2011 |

## Coarse aggregation rule (ad-hoc; pre-`crosswalks/discipline_coarse.csv`)

Per HD 2.1.b directive: `crosswalks/discipline_coarse.csv` is HD 2.1.f, gated behind this residual passing. Bucket assignment in this report uses label-prefix predicates and prefers `*, all` rollups where present to avoid leaf double-counting:

- `Engineering, *` → Engineering (era-A `Engineering, all` rollup; era-B `Engineering, all` rollup).
- `Life sciences, *` → Life sciences (`Life sciences, all`).
- `Physical sciences, *` → Physical sciences (`Physical sciences, all`).
- `Mathematical sciences, *` + `Computer sciences, *` (era A) / `Mathematics and statistics, *` + `Computer and information sciences, *` (era B) → Math & CS. Two rollups summed: `Mathematical/Mathematics, all` + `Computer sciences/Computer and information sciences, all`.
- `Environmental sciences, *` (era A) / `Geosciences, *` (era B) → Geosciences/Environmental. Pre-documented W5 drift cell.
- `Psychology, all` → Psychology.
- `Social sciences, *` → Social sciences (`Social sciences, all`).
- `Other sciences, all` → Other sciences nec (supporting).
- `Non-S&E, *` → Non-S&E (supporting; era-A presence: 2003+ only).

## Per-bucket median residuals (10 institutions, 2009→2010)

| bucket | n_cells | median_2009_2010 | max_abs_2009_2010 | median_2008_2011 | gating | pre_doc |
|---|---:|---:|---:|---:|:---:|:---:|
| Engineering | 9 | -5.95% | +19.07% | -21.68% | Y | n |
| Life sciences | 10 | -2.61% | +52.50% | -20.12% | Y | n |
| Math & CS | 9 | -13.98% | +19.58% | -17.62% | Y | n |
| Physical sciences | 10 | -5.26% | +115.06% | -15.61% | Y | n |
| Geosciences/Environmental | 9 | -3.96% | +62.65% | -21.71% | Y | Y |
| Psychology | 9 | -20.91% | +101.02% | -61.73% | Y | n |
| Social sciences | 9 | +14.10% | +44.75% | +5.49% | Y | n |
| Other sciences nec | 7 | -14.80% | +143.47% | -25.00% | n | n |
| Non-S&E | 0 | n/a | n/a | n/a | n | n |

**Reopen rule (per scoping §3.3):** non-pre-doc bucket with |median_2009_2010| > 5% OR any non-pre-doc cell with |residual_2009_2010| > 15%. Pre-doc cells are footnoted as W5 definitional drift, not rule failures.

## Cell-level residual table

One row per (institution × coarse_bucket). `pre_doc_class = Y` flags the W5 Environmental→Geosciences cells; their residuals are reported but do not count against the reopen triggers.

| inst_id | discipline_coarse | era_a_2008_kusd | era_a_2009_kusd | era_b_recon_2010_kusd | era_b_recon_2011_kusd | residual_2009_2010_pct | residual_2008_2011_pct | pre_doc_class | likely_cause |
|---|---|---:|---:|---:|---:|---:|---:|:---:|---|
| 029977 | Engineering | 619,406 | 703,165 | 781,990 | 854,997 | -11.21% | -38.03% | n | elevated; W6/W2 carve-out drift candidate |
| 029977 | Life sciences | 738,962 | 787,092 | 817,017 | 862,492 | -3.80% | -16.72% | n | minor; W6 population-scope shift / imputation differences |
| 029977 | Math & CS | 95,611 | 99,969 | 118,755 | 128,153 | -18.79% | -34.04% | n | OUT OF BAND — investigate |
| 029977 | Physical sciences | 128,188 | 146,274 | 166,459 | 176,047 | -13.80% | -37.34% | n | elevated; W6/W2 carve-out drift candidate |
| 029977 | Geosciences/Environmental | 46,864 | 51,224 | 50,844 | 44,843 | +0.74% | +4.31% | Y | W5 definitional drift (Environmental→Geosciences scope expansion) |
| 029977 | Psychology | 3,953 | 2,550 | 5,126 | 5,374 | -101.02% | -35.95% | n | OUT OF BAND — investigate |
| 029977 | Social sciences | 5,910 | 9,182 | 9,156 | 8,026 | +0.28% | -35.80% | n | within reporting noise |
| 029977 | Other sciences nec | 42,033 | 56,814 | 47,905 | 55,615 | +15.68% | -32.31% | n | OUT OF BAND — investigate |
| 029977 | Non-S&E | n/a | n/a | 7,230 | 9,761 | n/a | n/a | n | missing-data |
| 001319 | Engineering | n/a | n/a | n/a | n/a | n/a | n/a | n | missing-data |
| 001319 | Life sciences | 862,987 | 930,283 | 920,548 | 981,233 | +1.05% | -13.70% | n | within reporting noise |
| 001319 | Math & CS | n/a | n/a | n/a | n/a | n/a | n/a | n | missing-data |
| 001319 | Physical sciences | 22,195 | 17,414 | 14,961 | 13,993 | +14.09% | +36.95% | n | elevated; W6/W2 carve-out drift candidate |
| 001319 | Geosciences/Environmental | n/a | n/a | n/a | n/a | n/a | n/a | Y | missing-data |
| 001319 | Psychology | n/a | n/a | n/a | n/a | n/a | n/a | n | missing-data |
| 001319 | Social sciences | n/a | n/a | n/a | n/a | n/a | n/a | n | missing-data |
| 001319 | Other sciences nec | n/a | n/a | n/a | n/a | n/a | n/a | n | missing-data |
| 001319 | Non-S&E | n/a | n/a | n/a | n/a | n/a | n/a | n | missing-data |
| 003895 | Engineering | 93,405 | 97,479 | 98,468 | 116,207 | -1.01% | -24.41% | n | within reporting noise |
| 003895 | Life sciences | 567,870 | 623,414 | 632,202 | 685,841 | -1.41% | -20.77% | n | within reporting noise |
| 003895 | Math & CS | 24,097 | 23,977 | 27,947 | 28,344 | -16.56% | -17.62% | n | OUT OF BAND — investigate |
| 003895 | Physical sciences | 61,386 | 84,589 | 89,792 | 88,088 | -6.15% | -43.50% | n | elevated; W6/W2 carve-out drift candidate |
| 003895 | Geosciences/Environmental | 66,517 | 49,630 | 46,004 | 48,645 | +7.31% | +26.87% | Y | W5 definitional drift (Environmental→Geosciences scope expansion) |
| 003895 | Psychology | 8,959 | 6,912 | 6,731 | 7,251 | +2.62% | +19.06% | n | minor; W6 population-scope shift / imputation differences |
| 003895 | Social sciences | 59,276 | 65,910 | 39,060 | 48,203 | +40.74% | +18.68% | n | OUT OF BAND — investigate |
| 003895 | Other sciences nec | 267 | 208 | 82 | 144 | +60.58% | +46.07% | n | OUT OF BAND — investigate |
| 003895 | Non-S&E | n/a | n/a | 89,009 | 88,919 | n/a | n/a | n | missing-data |
| 001315 | Engineering | 56,907 | 61,850 | 64,504 | 67,967 | -4.29% | -19.44% | n | minor; W6 population-scope shift / imputation differences |
| 001315 | Life sciences | 649,978 | 648,574 | 657,557 | 688,596 | -1.39% | -5.94% | n | within reporting noise |
| 001315 | Math & CS | 22,243 | 23,422 | 23,766 | 23,932 | -1.47% | -7.59% | n | within reporting noise |
| 001315 | Physical sciences | 65,190 | 71,443 | 72,020 | 75,370 | -0.81% | -15.62% | n | within reporting noise |
| 001315 | Geosciences/Environmental | 10,872 | 13,147 | 13,668 | 17,239 | -3.96% | -58.56% | Y | W5 definitional drift (Environmental→Geosciences scope expansion) |
| 001315 | Psychology | 12,074 | 14,986 | 15,186 | 17,347 | -1.33% | -43.67% | n | within reporting noise |
| 001315 | Social sciences | 38,759 | 39,781 | 33,698 | 32,680 | +15.29% | +15.68% | n | OUT OF BAND — investigate |
| 001315 | Other sciences nec | 15,455 | 16,792 | 19,278 | 19,319 | -14.80% | -25.00% | n | elevated; W6/W2 carve-out drift candidate |
| 001315 | Non-S&E | n/a | n/a | 37,318 | 39,907 | n/a | n/a | n | missing-data |
| 001317 | Engineering | 92,934 | 98,604 | 113,218 | 109,397 | -14.82% | -17.71% | n | elevated; W6/W2 carve-out drift candidate |
| 001317 | Life sciences | 476,841 | 495,438 | 537,457 | 607,235 | -8.48% | -27.35% | n | elevated; W6/W2 carve-out drift candidate |
| 001317 | Math & CS | 50,982 | 48,595 | 41,083 | 40,512 | +15.46% | +20.54% | n | OUT OF BAND — investigate |
| 001317 | Physical sciences | 52,512 | 55,187 | 57,596 | 61,649 | -4.37% | -17.40% | n | minor; W6 population-scope shift / imputation differences |
| 001317 | Geosciences/Environmental | 144,932 | 148,322 | 149,403 | 139,142 | -0.73% | +3.99% | Y | W5 definitional drift (Environmental→Geosciences scope expansion) |
| 001317 | Psychology | 8,845 | 17,946 | 21,550 | 25,418 | -20.08% | -187.37% | n | OUT OF BAND — investigate |
| 001317 | Social sciences | 12,766 | 12,830 | 14,025 | 14,826 | -9.31% | -16.14% | n | elevated; W6/W2 carve-out drift candidate |
| 001317 | Other sciences nec | 2,215 | 2,435 | 3,650 | 5,405 | -49.90% | -144.02% | n | OUT OF BAND — investigate |
| 001317 | Non-S&E | n/a | n/a | 5,237 | 5,794 | n/a | n/a | n | missing-data |
| 002920 | Engineering | 39,047 | 40,346 | 46,558 | 56,074 | -15.40% | -43.61% | n | OUT OF BAND — investigate |
| 002920 | Life sciences | 655,202 | 673,352 | 837,336 | 860,743 | -24.35% | -31.37% | n | OUT OF BAND — investigate |
| 002920 | Math & CS | 11,667 | 12,295 | 14,529 | 15,111 | -18.17% | -29.52% | n | OUT OF BAND — investigate |
| 002920 | Physical sciences | 18,064 | 18,350 | 19,714 | 20,883 | -7.43% | -15.61% | n | elevated; W6/W2 carve-out drift candidate |
| 002920 | Geosciences/Environmental | 17,211 | 16,450 | 18,074 | 20,948 | -9.87% | -21.71% | Y | W5 definitional drift (Environmental→Geosciences scope expansion) |
| 002920 | Psychology | 3,329 | 18,028 | 21,797 | 23,325 | -20.91% | -600.66% | n | OUT OF BAND — investigate |
| 002920 | Social sciences | 22,386 | 26,200 | 22,506 | 21,157 | +14.10% | +5.49% | n | elevated; W6/W2 carve-out drift candidate |
| 002920 | Other sciences nec | n/a | n/a | n/a | n/a | n/a | n/a | n | missing-data |
| 002920 | Non-S&E | n/a | n/a | 2,775 | 3,966 | n/a | n/a | n | missing-data |
| 003378 | Engineering | 33,568 | 34,593 | 36,651 | 40,847 | -5.95% | -21.68% | n | elevated; W6/W2 carve-out drift candidate |
| 003378 | Life sciences | 590,059 | 606,702 | 663,497 | 725,635 | -9.36% | -22.98% | n | elevated; W6/W2 carve-out drift candidate |
| 003378 | Math & CS | 10,685 | 14,066 | 16,820 | 18,520 | -19.58% | -73.33% | n | OUT OF BAND — investigate |
| 003378 | Physical sciences | 28,680 | 32,377 | 31,918 | 30,065 | +1.42% | -4.83% | n | within reporting noise |
| 003378 | Geosciences/Environmental | 743 | 490 | 797 | 1,565 | -62.65% | -110.63% | Y | W5 definitional drift (Environmental→Geosciences scope expansion) |
| 003378 | Psychology | 5,644 | 6,378 | 8,044 | 9,128 | -26.12% | -61.73% | n | OUT OF BAND — investigate |
| 003378 | Social sciences | 32,199 | 26,820 | 22,790 | 20,083 | +15.03% | +37.63% | n | OUT OF BAND — investigate |
| 003378 | Other sciences nec | 6,666 | 5,342 | 13,006 | 5,679 | -143.47% | +14.81% | n | OUT OF BAND — investigate |
| 003378 | Non-S&E | n/a | n/a | 42,799 | 34,514 | n/a | n/a | n | missing-data |
| 008802 | Engineering | 149,077 | 145,610 | 145,812 | 166,439 | -0.14% | -11.65% | n | within reporting noise |
| 008802 | Life sciences | 408,489 | 426,315 | 431,561 | 488,033 | -1.23% | -19.47% | n | within reporting noise |
| 008802 | Math & CS | 40,304 | 38,420 | 40,017 | 41,080 | -4.16% | -1.93% | n | minor; W6 population-scope shift / imputation differences |
| 008802 | Physical sciences | 31,694 | 32,800 | 35,251 | 32,237 | -7.47% | -1.71% | n | elevated; W6/W2 carve-out drift candidate |
| 008802 | Geosciences/Environmental | 10,567 | 9,981 | 9,742 | 10,531 | +2.39% | +0.34% | Y | W5 definitional drift (Environmental→Geosciences scope expansion) |
| 008802 | Psychology | 7,238 | 7,924 | 12,397 | 13,326 | -56.45% | -84.11% | n | OUT OF BAND — investigate |
| 008802 | Social sciences | 39,276 | 37,339 | 20,630 | 22,713 | +44.75% | +42.17% | n | OUT OF BAND — investigate |
| 008802 | Other sciences nec | 15,947 | 18,072 | 24,164 | 19,664 | -33.71% | -23.31% | n | OUT OF BAND — investigate |
| 008802 | Non-S&E | n/a | n/a | 35,620 | 38,103 | n/a | n/a | n | missing-data |
| 001305 | Engineering | 148,776 | 156,600 | 126,744 | 121,699 | +19.07% | +18.20% | n | OUT OF BAND — investigate |
| 001305 | Life sciences | 410,123 | 425,500 | 500,125 | 555,984 | -17.54% | -35.57% | n | OUT OF BAND — investigate |
| 001305 | Math & CS | 26,046 | 26,081 | 29,728 | 30,923 | -13.98% | -18.72% | n | elevated; W6/W2 carve-out drift candidate |
| 001305 | Physical sciences | 57,078 | 43,036 | 92,552 | 97,040 | -115.06% | -70.01% | n | OUT OF BAND — investigate |
| 001305 | Geosciences/Environmental | 21,205 | 22,253 | 26,391 | 26,141 | -18.60% | -23.28% | Y | W5 definitional drift (Environmental→Geosciences scope expansion) |
| 001305 | Psychology | 9,376 | 11,153 | 11,857 | 13,865 | -6.31% | -47.88% | n | elevated; W6/W2 carve-out drift candidate |
| 001305 | Social sciences | 15,621 | 19,560 | 22,903 | 22,741 | -17.09% | -45.58% | n | OUT OF BAND — investigate |
| 001305 | Other sciences nec | n/a | n/a | n/a | n/a | n/a | n/a | n | missing-data |
| 001305 | Non-S&E | n/a | n/a | 29,539 | 39,578 | n/a | n/a | n | missing-data |
| 002178 | Engineering | 218,937 | 230,997 | 265,373 | 305,042 | -14.88% | -39.33% | n | elevated; W6/W2 carve-out drift candidate |
| 002178 | Life sciences | 218,413 | 257,208 | 122,182 | 118,854 | +52.50% | +45.58% | n | OUT OF BAND — investigate |
| 002178 | Math & CS | 51,355 | 52,328 | 55,870 | 58,420 | -6.77% | -13.76% | n | elevated; W6/W2 carve-out drift candidate |
| 002178 | Physical sciences | 104,397 | 114,870 | 117,749 | 115,445 | -2.51% | -10.58% | n | minor; W6 population-scope shift / imputation differences |
| 002178 | Geosciences/Environmental | 28,828 | 35,856 | 39,530 | 39,735 | -10.25% | -37.83% | Y | W5 definitional drift (Environmental→Geosciences scope expansion) |
| 002178 | Psychology | 1,203 | 1,382 | 1,821 | 2,080 | -31.77% | -72.90% | n | OUT OF BAND — investigate |
| 002178 | Social sciences | 7,978 | 7,934 | 8,788 | 11,345 | -10.76% | -42.20% | n | elevated; W6/W2 carve-out drift candidate |
| 002178 | Other sciences nec | 28,515 | 35,527 | 34,909 | 42,793 | +1.74% | -50.07% | n | within reporting noise |
| 002178 | Non-S&E | n/a | n/a | 30,916 | 29,896 | n/a | n/a | n | missing-data |

## ARRA case-(a) confirmation

ARRA case-(a) check: federal stream is bundled into Q9 column='Total' by NSF's aggregation. Within HD 2.1.b's resource budget, no published-NSF-federal-aggregate external reconciliation was attempted (HD 2.7 owns external reconciliation per scoping §8.7). Internal consistency check: if all-source residuals (this report) are within band, the all-source rule reconstructs without an explicit ARRA add — consistent with case (a) build assumption. Residuals exceeding the band on federal-heavy buckets (Engineering, Physical sciences, Life sciences) would be the empirical signal for case (b).

## Methods-note framing language (conditional)

> *"Reopen — the simple Q9 + Q11 all-source rule does not reconstruct era-A field-level totals within the locked residual band on a non-pre-documented bucket or cell. Surface to panel for widen-rule (case (b) ARRA add, additional component) vs. absorb-into-band (descriptive band widening) call. HD 2.1.b halts at this report; HD 2.1.c–.i remain locked behind the reopen disposition."*

## Reproducibility

Script: `etl/spikes/residual_2008_2011.py`. Loaders: `etl/_load.py read_herd_csv(year)` for 2008 / 2009 / 2010 / 2011. Question filter: era A `'Expenditures by S&E field'`, column='Total'; era B `'Federal expenditures by field and agency'` + `'Nonfederal expenditures by field and source'`, column='Total'. Bucket filter: coarse-rollup labels only (e.g., `Engineering, all`) — leaves are not double-counted into rollups. Math & CS sums two rollups. Population filter: institutions present (row='All' total > 0) in all four years 2008–2011. Substitutions documented above.

## Appendix: HD 1.4 Threshold Ladder Application (HD 2.1.h)

The HD 1.4 threshold ladder (CLAUDE.md §6) was anchored to **N=34 field-leaf cells** of 2009 spend ratios (24 leaves + 9 `*, all` rollups + 1 grand `All`). HD 2.1.b's residual analysis above is computed at the **coarse-bucket × institution × year-pair grain** (7 gating + 2 supporting buckets × 10 institutions). These are different units. Per CLAUDE.md §6 / `docs/hd_2_1_scoping.md` §6.2, the ladder application here is **approximate documentation, not a fresh kill condition** — the (b₂) decomposition framing is locked.

**Ratio conversion.** HD 1.4 ratios = `2010 / 2009`; HD 2.1.b residuals = `(era_a − era_b_recon) / era_a`, so `ratio = 1 − residual_pct`. A cell is outside [0.95, 1.05] iff `|residual_pct| > 5%`. A cell is outside [0.5, 2.0] iff `residual_pct > 50% OR residual_pct < −100%`.

**Cell counts** (non-pre-doc, non-missing, residual_2009_2010_pct, n=63 cells):

- Outside [0.95, 1.05]: ~46 of 63 cells (well above the structural ≥6 threshold).
- Outside [0.5, 2.0]: 5 cells — 029977 Psychology (−101.02%), 003895 Other sciences nec (+60.58%), 003378 Other sciences nec (−143.47%), 001305 Physical sciences (−115.06%), 002178 Life sciences (+52.50%).
- 2009→2010 mapping: per HD 1.4 outcome (CLAUDE.md §6), 2010 has no `Expenditures by S&E field` question; era-A field totals fragment into Q9 + Q11 source-class questions (many-to-many at the question level).

**Verdict: Structural.** All three structural triggers fire independently — ≥6 cells outside [0.95, 1.05]; ≥1 cell outside [0.5, 2.0] (five, in fact); and the era-A→era-B question mapping is not one-to-one. Any one alone would suffice.

This verdict is documentation only. Methods-note framing remains the **(b₂) decomposition** per CLAUDE.md §6 HD 2.1.b outcome subsection; no framing change is triggered.
