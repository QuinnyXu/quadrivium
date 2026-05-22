# HD 2.1.b Diagnostic 2 — Q5 clinical-trials share test

**Authored by:** Skipper, 2026-05-01 (post-residual diagnostic).

**Scope:** Tests the W2 definitional-drift hypothesis at the institution-year grain. Per FY24 Guide page 82 ('clinical trials and research training grants were explicitly included in the definition of R&D' under HERD; FY24 Guide page 632 names this as a known cause of 'sizable trend changes' between the era-A Academic R&D Expenditures Survey and the era-B HERD), era B captures dollars era A did not. If true, Q5 (clinical trials) plus a research-training-grants share should approximately match the institution-total residual gap from Diagnostic 1.

## Training-grants question availability — confirmed unavailable as a separate question

Verified against `crosswalks/question_map.csv` (36 rows) and `docs/source_documents/herd_fy24_guide.txt`: there is no era-B question that isolates research-training-grant expenditures as a separate carve-out. Per FY24 Guide pages 80–83 and 630–633, training grants are **included in the era-B R&D definition** (i.e., bundled into Q9 + Q11 field-level source rollups), not a discrete attribute question. The training-grants half of the W2 hypothesis therefore cannot be measured from HERD microdata alone — it is hypothesis residual until paired with an external data source (e.g., NIH RePORTER or NSF Award Search training-grant award totals, mappable to institution-year). Diagnostic 2 tests **only the clinical-trials half** of the hypothesis.

This means the comparison framing must be:
- If `clinical_trials_share` alone matches the institution-total gap → clinical trials is the dominant W2 driver; training grants are a smaller residual.
- If `clinical_trials_share` is materially smaller than the gap → training grants and/or other definitional changes (e.g., scope expansion within Q9/Q11 source rollups) account for the remainder.
- If `clinical_trials_share` exceeds the gap → either Q5 is being double-counted (unlikely; Q5 is an attribute carve-out from Q1, parallel to Q9+Q11 field-level totals), or the gap is masked by offsetting drifts elsewhere in the data.

## Per-institution-year shares

| inst_id | inst_name | year | q5_value_kusd | q9_q11_total_kusd | clinical_trials_share | institution_total_residual_pct |
|---|---|---:|---:|---:|---:|---:|
| 029977 | Johns Hopkins University | 2010 | 24,174 | 2,004,482 | 1.21% | -7.98% |
| 001319 | University of California, San Francisco | 2010 | 21,465 | 935,509 | 2.29% | +1.29% |
| 003895 | University of Wisconsin Madison | 2010 | 11,565 | 1,029,295 | 1.12% | -8.11% |
| 001315 | University of California, Los Angeles | 2010 | 15,575 | 936,995 | 1.66% | -5.28% |
| 001317 | University of California, San Diego | 2010 | 15,753 | 943,219 | 1.67% | -7.26% |
| 002920 | Duke University | 2010 | 317,152 | 983,289 | 32.25% | -22.14% |
| 003378 | University of Pennsylvania | 2010 | 42,262 | 836,322 | 5.05% | -15.07% |
| 008802 | Ohio State University all campuses | 2010 | 24,045 | 755,194 | 3.18% | -5.41% |
| 001305 | Stanford University | 2010 | 43,914 | 839,839 | 5.23% | -19.26% |
| 002178 | Massachusetts Institute of Technology | 2010 | 0 | 677,138 | 0.00% | +8.01% |
| 029977 | Johns Hopkins University | 2011 | 22,702 | 2,145,308 | 1.06% | -27.63% |
| 001319 | University of California, San Francisco | 2011 | 23,239 | 995,226 | 2.34% | -12.43% |
| 003895 | University of Wisconsin Madison | 2011 | 11,751 | 1,111,642 | 1.06% | -26.07% |
| 001315 | University of California, Los Angeles | 2011 | 12,000 | 982,357 | 1.22% | -12.72% |
| 001317 | University of California, San Diego | 2011 | 13,921 | 1,009,378 | 1.38% | -19.87% |
| 002920 | Duke University | 2011 | 333,153 | 1,022,207 | 32.59% | -33.29% |
| 003378 | University of Pennsylvania | 2011 | 48,529 | 886,036 | 5.48% | -25.10% |
| 008802 | Ohio State University all campuses | 2011 | 25,384 | 832,126 | 3.05% | -18.44% |
| 001305 | Stanford University | 2011 | 49,898 | 907,971 | 5.50% | -31.93% |
| 002178 | Massachusetts Institute of Technology | 2011 | 0 | 723,610 | 0.00% | -9.70% |

## Comparison summary

| year | n | median clinical_trials_share | median |institution-total residual| | median (|residual| − share) |
|---|---:|---:|---:|---:|
| 2010 | 10 | 1.98% | 8.00% | +6.19pp |
| 2011 | 10 | 1.86% | 22.49% | +16.94pp |

Reading: `(|residual| − share)` is the **unexplained-by-clinical-trials** portion of the institution-total gap, in percentage points. Near-zero → clinical trials alone explains the gap. Materially positive → training grants and/or other definitional changes carry the remainder. Negative → Q5 share exceeds the residual; gap is masked or Q5 captures more than the era-A/era-B definitional difference.

## Synthesis

- **2010**: median clinical_trials_share = 1.98%; median |institution-total residual| = 8.00%; median unexplained gap = +6.19pp.
- **2011**: median clinical_trials_share = 1.86%; median |institution-total residual| = 22.49%; median unexplained gap = +16.94pp.

**Hypothesis read.**
- Unexplained gap within ±5 percentage points → clinical trials alone is the W2 driver; locked W2 carve-out covers it.
- Unexplained gap +5 to +10 pp → clinical trials is a partial driver; training grants / other scope changes carry the residual.
- Unexplained gap > +10 pp → hypothesis substantially under-explains; the W2 carve-out alone cannot bridge era A to era B.
- Negative unexplained gap → Q5 share exceeds the institution-total residual; either Q5 captures dollars beyond the era-A/era-B definitional difference, or other drifts offset.

## Side-finding: question_map.csv canonicalization gap

`crosswalks/question_map.csv` (row 16) carries the canonical descriptor **`Clinical trial R&D expenditures`** for Q5, but the raw HERD CSV question label in FY 2010 / FY 2011 is **`Clinical trials`**. These do not match. Verified via `etl/spikes/_inspect_q5.py` against the FY 2010 and FY 2011 CSVs; the question_map.csv label was authored from FY24 Guide page 5 (the survey instrument's canonical question name), which differs from the per-year microdata column. Filing as a HD 2.1.f follow-up: question_map.csv needs a `raw_question_label` column (or a year-keyed mapping) before code can join on canonical names. Diagnostic 2 was authored against the raw label after surfacing the mismatch.

## Reproducibility

Script: `etl/spikes/residual_2008_2011_diagnostics.py`. Q5 read: question = `'Clinical trials'` (raw microdata label), row='Total', column IS NULL. Q5 absence is treated as 0 dollars (= institution did not report clinical-trial R&D for the year; era-B definitional scope includes clinical trials, so 0 is a legitimate value, not a missing code). Era-B institution total: Q9 row='All' column='Total' + Q11 row='All' column='Total'. Diagnostic 1 residuals are referenced verbatim from the sibling diagnostic.
