# Equipment-series era boundary — HD 2.4.f findings

**Date:** 2026-05-10
**Spike:** `etl/spikes/spike_equipment_era_boundary.py`
**Spike output:** `etl/spikes/spike_equipment_era_boundary_output.txt`
**Verdict:** **DIVERGENT (soft).** Equipment-series methods-note footnote queued for HD 2.4.i.

## 1. Question

Is the equipment-expenditure series continuous across the 2009→2010 era boundary, or does the Item-3-to-Q14 question reframing introduce a level shift? The two raw questions are:

- **Era-A Item 3** (1981–2009): *"Current fund research equipment expenditures by field"* — current-period expense treatment.
- **Era-B Q14** (2010–2024): *"Capitalized R&D equipment expenditures by field and source"* — capitalized treatment per FY24 Guide.

Per scoping doc §1(b), both ship as `expenditure_type='r&d_equipment'`, `source_class='all_source'` rows. HD 2.4.f tests whether the parallel-rows assumption holds empirically.

## 2. Cohort, grain, criteria

**Cohort:** top-10-by-FY-2008-R&D (continuity with HD 2.1.b's `era_reconciliation_2008_2011.md`).

**Spot years:** FY 2008, 2009 (era-A Item 3); FY 2010, 2011 (era-B Q14).

**Cell grain:** `expenditure_type='r&d_equipment'`, `source_class='all_source'`, `form_type='standard'`, `discipline_fine='All'` (institution-year equipment total at the canonical rollup row).

**Verdict criteria (pre-committed at HD 2.4.f kickoff):**

- **Sign-consistent + magnitude-stable** → parallel-rows-assumption holds. No methods-note footnote.
- **Divergent** → equipment-series footnote at HD 2.4.i naming the divergence with empirical magnitudes.

**Bands (pre-committed, no result-driven tuning):**

- Sign-consistent: every populated cell `> 0`.
- Magnitude-stable: per-institution 2009→2010 ratio in `[0.5, 2.0]` (allows up to 2× absorbed as real growth + modest reframing).

## 3. Per-institution per-year r&d_equipment totals (kUSD current)

| inst_id | institution | FY2008 (Item 3) | FY2009 (Item 3) | FY2010 (Q14) | FY2011 (Q14) |
|---|---|---:|---:|---:|---:|
| 029977 | Johns Hopkins University | 69,818 | 68,137 | 78,763 | 76,041 |
| 001319 | University of California, San Francisco | 16,765 | 17,941 | 20,965 | 21,878 |
| 003895 | University of Wisconsin Madison | 35,804 | 50,228 | 39,758 | 47,329 |
| 001315 | University of California, Los Angeles | 31,191 | 25,855 | 24,972 | 30,068 |
| 001317 | University of California, San Diego | 35,460 | 34,689 | 39,048 | 40,950 |
| 002920 | Duke University | 7,249 | 10,884 | 10,735 | 12,583 |
| 003378 | University of Pennsylvania | 18,763 | 16,634 | 42,635 | 26,511 |
| 008802 | Ohio State University all campuses | 24,227 | 22,513 | 22,151 | 18,991 |
| 001305 | Stanford University | 18,231 | 17,096 | 33,141 | 34,596 |
| 002178 | Massachusetts Institute of Technology | 31,470 | 32,704 | 41,251 | 47,620 |

**Sign-consistency:** 40 / 40 populated cells `> 0`. **PASS.**

## 4. Boundary ratio (Q14 FY2010 / Item 3 FY2009)

| inst_id | institution | Item 3 FY2009 | Q14 FY2010 | ratio | in band [0.5, 2.0] |
|---|---|---:|---:|---:|---|
| 029977 | Johns Hopkins University | 68,137 | 78,763 | 1.156 | OK |
| 001319 | University of California, San Francisco | 17,941 | 20,965 | 1.169 | OK |
| 003895 | University of Wisconsin Madison | 50,228 | 39,758 | 0.792 | OK |
| 001315 | University of California, Los Angeles | 25,855 | 24,972 | 0.966 | OK |
| 001317 | University of California, San Diego | 34,689 | 39,048 | 1.126 | OK |
| 002920 | Duke University | 10,884 | 10,735 | 0.986 | OK |
| 003378 | University of Pennsylvania | 16,634 | 42,635 | **2.563** | **OUT** |
| 008802 | Ohio State University all campuses | 22,513 | 22,151 | 0.984 | OK |
| 001305 | Stanford University | 17,096 | 33,141 | 1.939 | OK |
| 002178 | Massachusetts Institute of Technology | 32,704 | 41,251 | 1.261 | OK |

**Distribution (n=10):** min 0.792, p25 0.984, **median 1.141**, p75 1.261, max 2.563, mean 1.294.

**Magnitude-stability:** 9 / 10 in `[0.5, 2.0]`. **FAIL (technical).**

**Outlier reading.** University of Pennsylvania shows FY2009 16,634 → FY2010 42,635 → FY2011 26,511, with FY2011 reverting back toward the FY2009 level (FY2011 / FY2010 = 0.62). This reads as a one-year equipment-purchase spike at UPenn (a capital project or major instrument acquisition), not a sustained Item-3-to-Q14 reframing artifact. The single outlier is not symptomatic of a systematic boundary level shift.

## 5. Cohort-aggregate boundary ratios

| Aggregate | Value |
|---|---:|
| FY 2008 cohort-total | 288,978 kUSD |
| FY 2009 cohort-total | 296,681 kUSD |
| FY 2010 cohort-total | 353,419 kUSD |
| FY 2011 cohort-total | 356,567 kUSD |
| **Cohort boundary ratio (FY2010 / FY2009)** | **1.191** |
| Cohort 2011/2008 ratio (long-gap) | 1.234 |

The single-year cohort boundary jump (19.1%) is *above* expected steady-state growth but absorbs within HD 2.1.b's three-year long-gap context (~26% national R&D growth FY 2008→FY 2011 ~= 8% annual compounded). The boundary jump is one year of slightly-elevated growth, not a categorical level shift.

## 6. Leaf-sum cross-check — known issue, NOT an HD 2.4.f finding

Section [4] of the spike output shows a systematic ~85–100% delta between the `discipline_fine='All'` row value and the sum across `discipline_fine != 'All'` for every populated (institution, year) cell. This is the **rollup-vs-leaf double-counting** behavior already documented for the HD 2.4.i methods-note paragraph per scoping doc §14.3:

- Era-A Item 3 (and era-B Q14) emit both coarse rollups (`'Engineering, all'`) and leaf disciplines (`'Engineering, biomedical'`, `'Engineering, chemical'`, ...) into `discipline_fine`.
- Summing `discipline_fine != 'All'` double-counts coarse rollup + leaf rows.
- The `'All'` row is the canonical institution-year total; leaf-sum is a naive cross-check that triggers on the known pattern.

The 40/40 anomaly is expected behavior given the panel's `discipline_fine` projection; the cross-check is preserved in the spike for transparency but adds nothing to the HD 2.4.f verdict. The HD 2.4.i methods-note paragraph on rollup-vs-leaf double-counting (already docketed per §14.3) handles the cold-reader guidance.

## 7. Disposition

**Two readings:**

- **Empirical (sign + magnitude metrics):** 9 / 10 in-band sign-consistent. The one outlier is a single-institution one-year spike that reverts. Median ratio 1.14 is within HD 2.1.b real-growth context. Empirical magnitudes are mostly stable.
- **Categorical (question-text framing):** The accounting framing changes at the boundary — current-fund expense treatment (era-A) vs. capitalized treatment per FY24 Guide (era-B). This is a documented definitional discontinuity in the question wording itself, independent of how stable empirical magnitudes turn out at most institutions.

**Verdict reasoning.** Per Reconstructive Harmonization clause (b) — *"decompose what crossing the discontinuity actually involves into named, quantified components"* — the cold reader is owed the footnote even when empirical magnitudes are mostly stable. The footnote names a *known* definitional discontinuity at HD 2.4.i with the spike's empirical magnitudes; the discontinuity is *categorical* with mostly-stable empirics, not a catastrophic level-shift. The 9 / 10 in-band read supports the parallel-rows-assumption framing as a workable empirical posture; the categorical accounting-framing change is what motivates the footnote.

**Counter-case (parallel-rows assumption with one-line UPenn note) considered + rejected.** The empirical 9/10 in-band PASS could support a one-line note instead of a full footnote. Rejected because the categorical framing change is documented in the question text and would surface as a deposit-audit objection if the methods note did not name it explicitly. The cost of the footnote at HD 2.4.i is low; the audit-protection value is high.

## 8. Verdict

**DIVERGENT (soft).** Equipment-series footnote queued for HD 2.4.i methods-note integration per scoping doc §10 row 10. The footnote carries the spike's empirical magnitudes (median boundary ratio 1.14, 9/10 in [0.5, 2.0], one outlier at UPenn 2.56× FY 2009 reverting at FY 2011, cohort-aggregate boundary ratio 1.19) and names the current-fund-vs.-capitalized framing change. Parallel `expenditure_type='r&d_equipment'` rows ship across both eras as the methodology contract; the footnote is the consumer-side caveat.

**HD 2.4.f sub-task: substantively complete.**
