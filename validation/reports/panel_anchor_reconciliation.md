# FY 2024 Era-B-Internal Cohort-Anchored Verification Report

**Panel ↔ NCSES Table Builder anchor, FY 2024 broad-field × source-class grid.**

**Authored by:** Skipper, 2026-05-24 (HD 2.4.h; production artifact for the HD 2.4.g Branch A spike).

---

## Verdict

**PASS — 58 / 58 substantive cells at +0.000%.** Two cells are STRUCTURAL_ABSENT (UCSF Engineering, federal and nonfederal); neither folds into the pass/fail counts. No cell entered the REVIEW or FAIL band. No systematic-divergence signal.

The harmonized panel (`data/harmonized/herd_panel.parquet`) reproduces the FY 2024 NCSES Table Builder anchor exactly across the 10-institution cohort × 3 broad fields × 2 source classes, at the reconstruction grain the panel is built to support. The era-B-internal reconstruction primitive — Reconstructive Harmonization clause (a) — holds at the verification-anchor layer at deposit-grade precision.

## Scope

This report verifies the FY 2024 era-B all-source reconstruction against an independent NCSES publication. The anchor is the FY 2024 Table Builder grid "R&D Expenditures for All Institutions → By Broad Field and Federal and Nonfederal Sources" (`data/reference/dst-table-builder/dst-table-builder-FY2024.csv`), staged under the §2(d.2) seven-item discipline and documented in `data/reference/MANIFEST.md`. For each cohort institution, the report compares the published anchor value against the panel's reconstructed value at the broad-field rollup grain, for federal and nonfederal source classes.

The grid is the **58-substantive-cell FY 2024 era-B-internal cohort-anchored verification grid** locked under Branch III (PANEL_SKIPPER.md §8, 2026-05-21 / 2026-05-24; `docs/methods_notes/herd_panel_etl_scoping.md` §2(b)). It replaces the pre-Branch-III 240-cell nominal grid. The reference implementation is `etl/spikes/panel_anchor_verify.py` (the Branch A spike); this report is the deposit-grade artifact that the spike output supports.

## What this verifies — and what it does not

This is an **era-B-internal** verification at a single spot year (FY 2024). It confirms that, *within era B*, the panel's all-source reconstruction matches what NCSES publishes for the same year — i.e., that clause (a) (reconstruct what each era can support on its own terms) is exact at FY 2024.

It is **not a bridge across the 2010 era boundary**, and no claim here should be read as one. The cross-era discontinuity is characterized separately by the HD 2.1.b four-driver decomposition of the 2008→2011 institution-total residual (`validation/reports/era_reconciliation_2008_2011.md`) — Reconstructive Harmonization clause (b). That decomposition is the cross-era surface; this report cites it, and does not re-derive or re-claim cross-era comparability.

## Tolerance posture (Path B — empirical/descriptive)

Descriptive bands, principal-authorized 2026-05-24:

| Band | Condition |
|---|---|
| PASS | \|pct_diff\| ≤ 0.5% |
| REVIEW | 0.5% < \|pct_diff\| ≤ 2% |
| FAIL | \|pct_diff\| > 2% (or missing-from-panel) |
| STRUCTURAL_ABSENT | cell absent from the anchor by institution substrate; does not fold into FAIL |

Per HD 2.1 disposition 5 (Path B), the bands are descriptive, not sourced from a published NSF/NCSES tolerance — none surfaced at the HD 2.1.b external-referent search. **The bands were not exercised:** every substantive cell matched the anchor at +0.000%, so no cell reached the REVIEW or FAIL threshold. A future grid expansion that produces non-zero residuals would exercise them; production tolerance for any such expansion locks under separate review.

## Cohort

Ten institutions, the HD 2.1.b reconciliation cohort (top-10 by FY 2008 R&D volume, with the rank-stream substitutions documented in `era_reconciliation_2008_2011.md` §Sample — Stanford and MIT entered the cohort in place of higher-ranked institutions missing era-B FY 2009–2011 rows). The cohort and the UCSF Engineering structural-absence pair are preserved verbatim from the sidecar `data/reference/dst-table-builder-FY2024-query.yaml`; the spike does not re-derive the cohort from a live top-10 query. The FY 2008 selection year is cohort provenance only and carries no cross-era claim; the verification is entirely within FY 2024.

| NCSES inst_id | Institution |
|---|---|
| 029977 | Johns Hopkins University |
| 001319 | University of California, San Francisco |
| 003895 | University of Wisconsin Madison |
| 001315 | University of California, Los Angeles |
| 001317 | University of California, San Diego |
| 002920 | Duke University |
| 003378 | University of Pennsylvania |
| 008802 | Ohio State University all campuses |
| 001305 | Stanford University |
| 002178 | Massachusetts Institute of Technology |

## Structural absence — UCSF Engineering

The FY 2024 anchor export contains **58 substantive cells, not the nominal 60** (10 institutions × 3 fields × 2 source classes). University of California, San Francisco (001319) is missing both Engineering cells — federal and nonfederal.

This is a **structural absence at the institution substrate, not a suppression and not a zero.** UCSF is a health-sciences-only institution; it has no Engineering school. The UC system's Engineering R&D base lives at Berkeley, San Diego, Los Angeles, Irvine, and Davis — not San Francisco. The two cells are therefore reported as `STRUCTURAL_ABSENT` and rendered `—` throughout, never as `0`: a structural absence (no discipline exists at the institution) is methodologically distinct from a documented zero (zero R&D in an existing discipline), and coercing it to a zero would misrepresent the substrate. The spike's kill condition treats a non-null, non-zero panel value at either UCSF Engineering cell as a substrate-shape kill signal; neither fired.

## Reconstruction grain — the broad-field rollup row

*(Methods-note prose seed. Transplants to `docs/methods_notes/reconstructive_harmonization.md` §6 ("What the deposit ships") at HD 2.4.i; tracked as the §14.3 rollup-vs-leaf paragraph in the `docs/methods_notes/herd_panel_etl_scoping.md` §10 timeline. Authored once here; adapted there — not re-derived.)*

The reconciliation grain is the **broad-field rollup row, not the free-sum of fine leaves.** The panel carries, for every coarse bucket, both a `<bucket>, all` rollup row (e.g. `Engineering, all`) and the underlying fine leaves (`Engineering, mechanical`, and so on). The Table Builder anchor reports the broad-field rollup. Reconciling on `discipline_coarse` alone would match both the rollup row and the fine leaves and double-count — producing roughly twice the anchor across every cell. The verification therefore filters panel rows on `discipline_fine IN ('Engineering, all', 'Life sciences, all', 'Physical sciences, all')`.

The rollup row is also the **stable comparison surface across the 2010 redesign's fine-leaf shifts.** The 2010 instrument changed which fine fields exist and how they nest; the broad-field rollup is invariant to that churn in a way the fine leaves are not. Anchoring verification (and longitudinal comparison) at the rollup grain is what lets the reconstruction be checked against published totals without taking a dependency on the fine-leaf taxonomy holding still across the boundary.

## Quality flags — the JHU `imputed` cells (falsification receipt)

Of the 58 substantive cells, 55 carry `quality_flag='reported'` and 3 carry `quality_flag='imputed'`: Johns Hopkins University's nonfederal cells in all three fields (Engineering, Life sciences, Physical sciences). All three match the anchor at +0.000%; the flag records NCSES's imputation of the nonfederal component, not a panel discrepancy.

We tested an explicit hypothesis: that the `imputed` nonfederal flag signals **classified-DOD reporting conventions** — the chain from JHU's Applied Physics Laboratory to MIT's Lincoln Laboratory to Caltech's JPL. **The hypothesis is falsified:**

- **MIT — the canonical comparator — reports rather than imputes.** All three MIT nonfederal rollup cells are `reported`. If the flag tracked classified-DOD reporting, the DOD FFRDC operator would carry it; it does not.
- **Five of the six named UARC/DOD-lab universities** in the panel (MIT, Georgia Tech, Penn State, UT Austin, University of Washington — Caltech the lone exception) do **not** carry the pattern.
- **Base rate:** at the FY 2024 nonfederal rollup grain, `imputed` appears on 162 cells across 32 institutions, out of 4,640 cells across 669 institutions (~3.5% of cells, ~4.8% of institutions). The carriers skew toward **smaller and less-research-intensive institutions** (Caltech — smaller but highly research-intensive — is the partial exception that shows the skew is along both dimensions, not size alone). JHU's three flags are an instance of this broad practice, not a DOD artifact.

The flags do not affect the verification result. They are recorded here for transparency, and the falsified hypothesis is documented rather than left as a hedge.[^skew]

[^skew]: This institution-size-and-intensity skew parallels the W4 `status='u'` characterization in PANEL_SKIPPER.md §8 (era-B 2010–2022 nulls, which skew toward the same institution profile). Two distinct quality flags showing similar substrate-side distribution patterns is empirically noted, methodologically unresolved — preserved for future investigation or HD 2.4.i methods-note integration if it proves substantive.

## Per-cell results

All 60 grid cells (58 substantive + 2 structural-absent), ordered by institution. Values in thousands of current USD (kUSD), matching the anchor convention. Δ% is `100 × (panel − anchor) / anchor`.

| Institution | Field | Source | Anchor (kUSD) | Panel (kUSD) | Δ% | Flag | Disposition |
|---|---|---|---:|---:|---:|---|---|
| Duke University | Engineering | federal | 92,243 | 92,243 | +0.000% | reported | PASS |
| Duke University | Engineering | nonfederal | 27,385 | 27,385 | +0.000% | reported | PASS |
| Duke University | Life sciences | federal | 856,722 | 856,722 | +0.000% | reported | PASS |
| Duke University | Life sciences | nonfederal | 463,442 | 463,442 | +0.000% | reported | PASS |
| Duke University | Physical sciences | federal | 28,052 | 28,052 | +0.000% | reported | PASS |
| Duke University | Physical sciences | nonfederal | 3,395 | 3,395 | +0.000% | reported | PASS |
| Johns Hopkins University | Engineering | federal | 1,645,349 | 1,645,349 | +0.000% | reported | PASS |
| Johns Hopkins University | Engineering | nonfederal | 66,799 | 66,799 | +0.000% | imputed | PASS |
| Johns Hopkins University | Life sciences | federal | 962,169 | 962,169 | +0.000% | reported | PASS |
| Johns Hopkins University | Life sciences | nonfederal | 385,521 | 385,521 | +0.000% | imputed | PASS |
| Johns Hopkins University | Physical sciences | federal | 339,814 | 339,814 | +0.000% | reported | PASS |
| Johns Hopkins University | Physical sciences | nonfederal | 15,979 | 15,979 | +0.000% | imputed | PASS |
| Massachusetts Institute of Technology | Engineering | federal | 240,944 | 240,944 | +0.000% | reported | PASS |
| Massachusetts Institute of Technology | Engineering | nonfederal | 172,945 | 172,945 | +0.000% | reported | PASS |
| Massachusetts Institute of Technology | Life sciences | federal | 92,776 | 92,776 | +0.000% | reported | PASS |
| Massachusetts Institute of Technology | Life sciences | nonfederal | 39,394 | 39,394 | +0.000% | reported | PASS |
| Massachusetts Institute of Technology | Physical sciences | federal | 142,218 | 142,218 | +0.000% | reported | PASS |
| Massachusetts Institute of Technology | Physical sciences | nonfederal | 56,747 | 56,747 | +0.000% | reported | PASS |
| Ohio State University all campuses | Engineering | federal | 130,390 | 130,390 | +0.000% | reported | PASS |
| Ohio State University all campuses | Engineering | nonfederal | 130,991 | 130,991 | +0.000% | reported | PASS |
| Ohio State University all campuses | Life sciences | federal | 509,298 | 509,298 | +0.000% | reported | PASS |
| Ohio State University all campuses | Life sciences | nonfederal | 564,272 | 564,272 | +0.000% | reported | PASS |
| Ohio State University all campuses | Physical sciences | federal | 37,561 | 37,561 | +0.000% | reported | PASS |
| Ohio State University all campuses | Physical sciences | nonfederal | 11,573 | 11,573 | +0.000% | reported | PASS |
| Stanford University | Engineering | federal | 102,868 | 102,868 | +0.000% | reported | PASS |
| Stanford University | Engineering | nonfederal | 61,635 | 61,635 | +0.000% | reported | PASS |
| Stanford University | Life sciences | federal | 751,119 | 751,119 | +0.000% | reported | PASS |
| Stanford University | Life sciences | nonfederal | 451,267 | 451,267 | +0.000% | reported | PASS |
| Stanford University | Physical sciences | federal | 80,304 | 80,304 | +0.000% | reported | PASS |
| Stanford University | Physical sciences | nonfederal | 23,371 | 23,371 | +0.000% | reported | PASS |
| University of California, Los Angeles | Engineering | federal | 72,994 | 72,994 | +0.000% | reported | PASS |
| University of California, Los Angeles | Engineering | nonfederal | 55,860 | 55,860 | +0.000% | reported | PASS |
| University of California, Los Angeles | Life sciences | federal | 697,811 | 697,811 | +0.000% | reported | PASS |
| University of California, Los Angeles | Life sciences | nonfederal | 629,250 | 629,250 | +0.000% | reported | PASS |
| University of California, Los Angeles | Physical sciences | federal | 56,805 | 56,805 | +0.000% | reported | PASS |
| University of California, Los Angeles | Physical sciences | nonfederal | 21,459 | 21,459 | +0.000% | reported | PASS |
| University of California, San Diego | Engineering | federal | 161,714 | 161,714 | +0.000% | reported | PASS |
| University of California, San Diego | Engineering | nonfederal | 89,058 | 89,058 | +0.000% | reported | PASS |
| University of California, San Diego | Life sciences | federal | 685,305 | 685,305 | +0.000% | reported | PASS |
| University of California, San Diego | Life sciences | nonfederal | 460,352 | 460,352 | +0.000% | reported | PASS |
| University of California, San Diego | Physical sciences | federal | 69,123 | 69,123 | +0.000% | reported | PASS |
| University of California, San Diego | Physical sciences | nonfederal | 34,730 | 34,730 | +0.000% | reported | PASS |
| University of California, San Francisco | Engineering | federal | — | — | — | — | STRUCTURAL_ABSENT |
| University of California, San Francisco | Engineering | nonfederal | — | — | — | — | STRUCTURAL_ABSENT |
| University of California, San Francisco | Life sciences | federal | 988,789 | 988,789 | +0.000% | reported | PASS |
| University of California, San Francisco | Life sciences | nonfederal | 1,067,105 | 1,067,105 | +0.000% | reported | PASS |
| University of California, San Francisco | Physical sciences | federal | 47,844 | 47,844 | +0.000% | reported | PASS |
| University of California, San Francisco | Physical sciences | nonfederal | 23,899 | 23,899 | +0.000% | reported | PASS |
| University of Pennsylvania | Engineering | federal | 63,768 | 63,768 | +0.000% | reported | PASS |
| University of Pennsylvania | Engineering | nonfederal | 60,758 | 60,758 | +0.000% | reported | PASS |
| University of Pennsylvania | Life sciences | federal | 832,231 | 832,231 | +0.000% | reported | PASS |
| University of Pennsylvania | Life sciences | nonfederal | 827,654 | 827,654 | +0.000% | reported | PASS |
| University of Pennsylvania | Physical sciences | federal | 57,553 | 57,553 | +0.000% | reported | PASS |
| University of Pennsylvania | Physical sciences | nonfederal | 27,082 | 27,082 | +0.000% | reported | PASS |
| University of Wisconsin Madison | Engineering | federal | 108,643 | 108,643 | +0.000% | reported | PASS |
| University of Wisconsin Madison | Engineering | nonfederal | 86,345 | 86,345 | +0.000% | reported | PASS |
| University of Wisconsin Madison | Life sciences | federal | 554,664 | 554,664 | +0.000% | reported | PASS |
| University of Wisconsin Madison | Life sciences | nonfederal | 635,470 | 635,470 | +0.000% | reported | PASS |
| University of Wisconsin Madison | Physical sciences | federal | 76,564 | 76,564 | +0.000% | reported | PASS |
| University of Wisconsin Madison | Physical sciences | nonfederal | 39,829 | 39,829 | +0.000% | reported | PASS |

Disposition counts: **PASS 58, REVIEW 0, FAIL 0, STRUCTURAL_ABSENT 2.**

## Reproducibility

The per-cell table above is generated from the committed spike output, not hand-transcribed. To reproduce end-to-end:

```bash
uv sync
uv run python etl/spikes/panel_anchor_verify.py
```

The reference implementation and its output are pinned at commit `e39ad4c`. The verdict is anchored to this input-and-code version:

| Artifact | SHA-256 |
|---|---|
| `data/harmonized/herd_panel.parquet` | `196132459f07725ed2d863d748dd637640a76e77245f87f8bb72d8dfad0c6fcc` |
| `data/reference/dst-table-builder/dst-table-builder-FY2024.csv` | `e0fc1f7b08f32f8963463ba591e18a188fbfc9d9f4584f2ffc50778ef46738a6` |
| `etl/spikes/_out/panel_anchor_verify_FY2024.parquet` | `217e7937bb0847912b46134042cb0f43384887baaba6597543137725ffc7e41d` |

The panel parquet SHA-256 reflects a deterministic re-serialization of the panel — a build row-ordering fix applied after the spike was committed at `e39ad4c` — whose content is identical to the e39ad4c-era panel; only the row order written to the file changed. Report authored against repository state `df84886`. The anchor CSV SHA-256 matches `data/reference/MANIFEST.md`. The spike re-asserts the verdict on every run; a divergence between a future panel build and this report's values is itself a finding — re-run the reproducer and compare against the SHA-256s above before treating the report as stale.

## References

- `etl/spikes/panel_anchor_verify.py` — reference implementation (Branch A spike).
- `crosswalks/era_b_reconstruction_rule.yaml` — the era-B-internal all-source reconstruction rule verified here.
- `validation/reports/era_reconciliation_2008_2011.md` — HD 2.1.b cross-era decomposition (clause (b); the cross-era surface this report defers to).
- `docs/methods_notes/herd_panel_etl_scoping.md` §2(b) — cohort + anchor-source table; §10 — HD 2.4.g/h timeline.
- `data/reference/dst-table-builder-FY2024-query.yaml` — anchor query sidecar; cohort + structural-absence source of truth.
- PANEL_SKIPPER.md §8 — HD 2.4.g substrate-shape lock (Branch III) and the HD 2.4.g combined entry.
