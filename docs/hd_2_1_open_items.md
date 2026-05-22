# HD 2.1 — Open Items

Running list of real questions that aren't blocking the HD 2.1 critical path. Skipper checks at each HD task boundary; nothing in HD 2.1 reopens unless evidence forces it.

## Pre-1981 Guide field-list variability

- Guide page 18 implies distinct field lists for 1973–74 / 1975–77 / 1978 / 1979 / 1980–89. Row-label harvest collapsed pre-1981 to two fingerprints (1973–1978, 1979–1983).
- Hypothesis: variability lives on the column axis, in column='Total' vs. agency breakdowns, in institution coverage, or in a Guide-narrative distinction not reflected in data files.
- Disposition: not on the HD 2.1 critical path. Investigate at a deliberate side task post-HD-2.1 if the methods note's pre-1981 coverage claim turns out to need it. Otherwise the methods note notes the Guide distinction with "the data files do not reflect this variability at the row-axis level."

## Era-B Q9 vs. Q11 row-label punctuation/spelling drift (2010–2023)

- Logged at HD 2.1.d row-label harvest (2026-05-01).
- Q9 (`Federal expenditures by field and agency`) and Q11 (`Nonfederal expenditures by field and source`) carry seven row labels with **same field, different rendering** in every year 2010–2023:
  - `Engineering, aerospace, aeronautical, and astronautical` (Q9, Oxford comma) vs. `Engineering, aerospace, aeronautical and astronautical` (Q11, no Oxford comma).
  - `Engineering, electrical, electronic, and communications` (Q9, "electronic" singular) vs. `Engineering, electrical, electronics, and communications` (Q11, "electronics" plural).
  - The five Geosciences labels (`-all`, `-atmospheric science and meteorology`, `-geological and earth sciences`, `-ocean sciences and marine sciences`, `-other`): Q9 has `Geosciences, atmospheric sciences, and ocean sciences,` (Oxford comma); Q11 has `Geosciences, atmospheric sciences and ocean sciences,` (no Oxford comma).
- The other 36 labels (2010–2015) / 40 labels (2016–2023) are spelled identically across Q9 and Q11.
- **FY 2024 reconciles:** NSF dropped the Q11 spellings; only the Q9 (Oxford-comma, "electronic" singular) spelling appears in both questions. 2024 carries 47 labels with full Q9–Q11 agreement.
- Field-axis is structurally consistent — the disagreement is a string-rendering inconsistency between the two questions in the same survey. The summation rule (§2.1 of scoping doc) consumes column='Total' from each question and sums; it does NOT depend on string-equality between Q9 and Q11 labels.
- Disposition: rationalize at HD 2.1.e. `crosswalks/discipline_fine.csv` carries a canonical `discipline_fine` value = **the FY 2024 form (Q9 spelling: Oxford comma included, "electronic" singular)** since that is what NSF settled on; the canonical-form choice forward-proofs against any future NSF spelling drift toward FY 2024. One row per raw_row_label variant with `decision_rationale` documenting the punctuation/spelling drift across Q9/Q11 and the FY 2024 reconciliation. No structural escalation needed; not a build blocker for the summation rule.

## Era-B 2024 bucket-size reduction is spelling consolidation, not label removal

- Logged at HD 2.1.d row-label harvest (2026-05-01).
- Era-B row-label fingerprints from HD 2.1.d harvest: 2010–2015 → 50 labels, 2016–2023 → 54 labels, **2024 → 47 labels**. The 2024 reduction (54 → 47) reads on first glance as label removal; it is not.
- The 2024 reduction is **spelling consolidation**: the seven Q9/Q11 Oxford-comma / singular-vs.-plural variants documented in the entry above previously rendered as duplicate rows in the 2016–2023 fingerprint when the harvest counted Q9-spelling and Q11-spelling as distinct row labels. FY 2024 NSF settled on the Q9 spelling for both questions, collapsing each variant pair to a single row.
- **No era-B fields were removed in 2024.** Field-axis stability holds 2016–2024.
- Disposition: methods-note era-B taxonomy-stability passages must be precise about this — the 2024 row count is *consolidated*, not *truncated*. The seven labels affected are listed in the entry above.

## question_map.csv canonical-vs-raw label gap

- Logged at HD 2.1.b Diagnostic 2 (2026-05-01).
- `crosswalks/question_map.csv` was authored from FY24 Guide pages 5–6 / 13–22 (instrument-canonical question names). Per-year HERD CSV column headers carry abbreviated forms — e.g., Q5 canonical `Clinical trial R&D expenditures` (Guide page 5) vs. raw CSV `Clinical trials`.
- Discovery: Diagnostic 2 (Q5 share test) needed a label-aware join between question_map.csv and per-year microdata; the canonical/raw mismatch surfaced as a join-key problem.
- Disposition: **HD 2.1.f mechanical task, not blocking.** Add a `raw_question_label` field to `crosswalks/question_map.csv` (or a sibling `question_label_aliases.csv` if multiple raw renderings exist per canonical row) so build code joins on raw labels reliably. Same code change applies to all rows where canonical and raw differ; surface and resolve during HD 2.1.f authoring.

## Era-B FY 2017 expansion: `Social sciences, anthropology` arrives

- Logged at HD 2.1.d row-label harvest (2026-05-01).
- INVENTORY.md §5.2 / §6 documents two FY 2017 additions: `Engineering, industrial and manufacturing` and `Life sciences, natural resources and conservation`. The harvest confirmed both at expected year.
- Harvest also surfaced **two undocumented FY 2017 additions**: `Physical sciences, materials science` and `Social sciences, anthropology`. Both first-seen 2016, present in Q9 and Q11 every year through 2024, with first-positive-value 2016.
- Disposition: not a build blocker. INVENTORY.md §5.2 / §6 should add these two labels to the FY 2017 micro-expansion entry at the next INVENTORY pass. HD 2.1.e adds the rows to `crosswalks/discipline_fine.csv` with `year_range_start = 2016` and `decision_rationale` citing the harvest and FY24 Guide page 18 line items if the Guide carries them.

## FY 2017 status='u' — Guide-undocumented quality code

- Logged at HD 2.4 W4 NULL characterization spike (`etl/spikes/spike_herd_null_characterization.py`, 2026-05-09).
- 244 rows in FY 2017 carry `status='u'`, which is not in the FY24 Guide's documented codeset {Blank=Normal, `i`=Imputed, `n`=Data not available, `e`=Estimated by NCSES (era A only)}. Findings: `validation/reports/herd_null_characterization_findings.md` §4.2.
- All 244 occur on per-source-class detail columns (`Institution funds`, `Nonprofit organziations` [sic — spelling preserved in raw], `Business`, `Nonfederal`); **never on `column='Total'`**. Sample rows show `data='0'` consistently. Plausible reading: a respondent-marked "unspecified zero" or "user-confirmed zero" code that NCSES introduced and later retired (zero occurrences in FY 2008 or FY 2024 across the spike's three spot years).
- Disposition: **no HD 2.4 build impact** (the era-B reconstruction rule consumes `column='Total'` only). Preserved in the harmonized panel as `quality_flag='unspecified_zero'` on the rare rows that emit with this status, per the W4 NULL handling lock (`docs/methods_notes/herd_panel_etl_scoping.md` §1, §6.2 Stage 6, §14.9). Methods-note drift footnote candidate. Investigation deferred — would need NCSES historical-codeset documentation (or a direct NCSES inquiry) to resolve the encoding semantics.

## Pre-1981 fingerprint: leaf-vs-rollup mix more varied than original §3(b) claim

- Logged at HD 2.4.b round 1 Stage 4 smoke test (2026-05-10).
- Scoping doc §3(b) (original) claimed "1975–1978 emits only `*, all` rollup rows; 1979 onward emits leaves." The Stage 4 panel build empirically contradicts this: 1975 emits 1,442 rollups + 2,734 leaves + 534 grand-`All` rows. 1976–1978 follow the same mixed pattern.
- Three transitions visible (rather than the two §3(b) names):
  - **1975–1978** — mixed rollup + leaf fingerprint at ~3:5 rollup:leaf ratio.
  - **1979–1980** — leaf-density step up (1979: 3,231 rollups + 3,592 leaves; 1980: 3,449 rollups + 7,067 leaves).
  - **1981 onward** — Item 3 equipment series introduction roughly doubles total row count (1981: 6,766 rollups + 13,812 leaves; consistent through 2009).
- Empirical detail preserved: see `etl/spikes/stage_4_smoke_test_output.txt` "Pre-1981 fingerprint check" section (HD 2.4.b round 1 run, 2026-05-10).
- Disposition: **HD 2.4.i methods-note refinement, not blocking.** Update §3(b) language and the methods-note pre-1981 fingerprint footnote to name three transitions instead of two. Build is correct (it emits the rows verbatim from raw CSVs after discipline-fine join); the prose that describes the data needs more empirical precision. Not a build blocker. Logged for HD 2.4.i methods-note refinement pass.

## FY 1978 and FY 1988 ~32% row-count drops — upstream, not build-side

- Logged at HD 2.4.b round 1 Stage 4 smoke test (2026-05-10).
- Stage 4 panel build surfaced FY 1978 = 3,194 rows (vs FY 1977 = 4,718) and FY 1988 = 15,970 rows (vs FY 1987 = 23,478). Both drops ~32% of prior year. Probe (`etl/spikes/probe_1978_1988_drops.py`, output `etl/spikes/probe_1978_1988_drops_output.txt`) ran characterization at three grains (Stage 1 raw, Stage 2 in-scope, Stage 4 panel) plus distinct-institution counts to determine upstream-vs-build-side.
- **Two distinct upstream patterns:**
  - **FY 1978 — institution-count drop.** Distinct institutions reporting dropped from 535 (FY 1977) to **316** (FY 1978), a **41% drop in survey participation**. Stage 1 raw rows dropped 56.6% (17,514 → 7,602). Per-institution row density actually *recovered* slightly (~24 rows/inst FY 1978 vs ~33 FY 1977). Plausibly NSF survey methodology / coverage change at FY 1978 (federal budget contraction era; transition between Academic R&D Expenditures Survey vintages).
  - **FY 1988 — per-institution row-density drop.** Distinct institutions unchanged (554 → 554). Stage 1 raw rows dropped 29.3% (52,106 → 36,852). Per-institution row density dropped ~32%. Plausibly a temporary methodology change in survey instrument that reduced rows-per-institution.
- Stage 4 panel drop magnitude (-32% in both years) matches the upstream Stage 1 drop. **Build is faithfully passing through upstream patterns; not a build-side issue.**
- Disposition: **HD 2.4.i methods-note treatment, not blocking.** The methods note's coverage discussion notes both anomalies as documented upstream HERD-coverage variability, parallel to how the existing 1972 / 1973–1974 / 1990–2024 coverage statements handle other coverage discontinuities. Investigation of the underlying NSF methodology change at FY 1978 / FY 1988 deferred to NCSES historical-publications documentation hunt (HD 2.4.i, ~1-half-day budget already absorbed there per Vision verdict 2026-05-10) — same hunt that targets the FY 1973–1974 `'c'` codeset semantic. Logged here so the deferred work has a concrete touch list.

## PANEL_SKIPPER.md §8 usage pattern — quarter-boundary disposition

- Logged at HD 2.4.d W4 amendment surface (2026-05-10 PM).
- PANEL_SKIPPER.md §8 ("Locked decisions") has been touched only twice across multiple weeks of HD 2.4 substantive work: (i) HD 2.4 §2 amendment-lock for DST publication-regime contraction (2026-05-10 morning), and (ii) HD 2.4.d W4 NULL-handling amendment (2026-05-10 PM). Between those two entries, HD 2.4.a/b/c shipped substantive Vision-locked dispositions (era-A status codeset carve-out + FY 1975 floor; Short Form Q2 Option (b) staging; Item 3 raw label drift; codeset-extension policy locked at CLAUDE.md §6; ~4 distinct panel reviews' worth of decisions) that did NOT land in PANEL_SKIPPER §8. They live in their source-of-truth artifacts (CLAUDE.md §6, scoping doc §3, this file, validation reports) but not in the §8 locked-decisions log.
- **Two readings**, both defensible:
  - **(a) §8 should be the locked-decisions log it was designed to be.** Backfill HD 2.4.a/b/c Vision-locked dispositions; subsequent HD 2.4 sub-tasks (HD 2.4.e+) bank each Vision-locked decision in §8 as it lands. Cost: ~1 half-day backfill + ~5 min per future entry.
  - **(b) §8 appropriately reserved for major panel-touch decisions only.** The DST regime amendment and W4 amendment are panel-touch decisions in a way that the era-A codeset carve-out and Short Form Q2 staging are not — they revise locked artifacts (scoping doc §2; YAML quality_flag_propagation block) rather than extend established patterns. Routine Vision-locked dispositions live in their source-of-truth artifacts; §8 carries the methodologically significant evolutions. No backfill needed; the inconsistency is design, not gap.
- **Disposition: quarter-boundary review (mid-June panel) call.** Process-discipline question, not load-bearing for HD 2.4 closure. Vision's lens is appropriate venue; mid-June review can disposition (a) vs (b) with a full quarter of HD 2.4 audit-trail evidence in hand. The decision affects whether HD 2.4.e+ sub-tasks bank routine dispositions in §8 or not.
- Recommendation for the interim (now → mid-June): **default to reading (b)** — bank only major panel-touch decisions in §8; routine Vision-locked dispositions live in source-of-truth artifacts. If mid-June verdict is (a), backfill at that point; if (b), the interim discipline is already aligned.

## FY 2020 status='u' on Q14 column='Total' — W4 baseline scope refinement

- Logged at HD 2.4.b round 1 Stage 5 smoke test (2026-05-10).
- The W4 NULL characterization spike (`validation/reports/herd_null_characterization_findings.md`, 2026-05-09) scanned FY 2008 / FY 2017 / FY 2024 spot years and characterized `status='u'` as "244 rows in FY 2017 only, non-Total columns only, `data='0'` empirically." Scoping doc §6.2 Stage 9 sanity assertion (locked 2026-05-09) is "every output row with `quality_flag='unspecified_zero'` carries `year=2017`" — a drift-defense assertion against the W4 baseline.
- HD 2.4.b round 1 Stage 5 full era-B scan (2010–2024) surfaced **9 rows at FY 2020, Q14, `column='Total'`, institution_id `'003446'`, `quality_flag='unspecified_zero'`, positive numeric values (4–17 kUSD)** across 9 distinct `discipline_fine` leaves. These rows violate the W4-baseline scope on three axes: year (FY 2020 ≠ FY 2017), column (`'Total'` not non-Total), data ('positive numeric' not '0'). The W4 spike's empirical scope was incomplete because it only scanned three spot years; HD 2.4.b's full-era-B scan extends the baseline.
- **Build behavior is correct.** Stage 3's CASE expression case-folds `UPPER(status)='U' → 'unspecified_zero'` per the locked codeset; the 9 rows project through to the panel with the correct flag. The build is faithfully passing through what the raw HERD CSVs encoded.
- **Disposition (locked HD 2.4.d 2026-05-10 PM, Vision consultation):** **Option δ (re-characterize the W4 baseline) + Option γ-allow (let the 9 panel rows propagate).** Full era-B status='u' probe (`etl/spikes/probe_era_b_status_u_full.py`) extended the empirical scope from FY-2017-only / non-Total-only to era-B-wide 2010–2022 (~4,000 rows across 13 years, 106 institutions, retired FY 2023+). The W4 spike's "FY-2017-only" baseline was a sampling artifact. The 9 FY 2020 SCSU rows propagate as legitimate `unspecified_zero` panel rows; the W4 lock's empirical baseline is corrected; the Stage 9 sanity assertion is redesigned to defend the three-tier corrected baseline (era-A NOT expected by construction; era-B 2010–2022 allowed per documented baseline; era-B 2023+ NOT expected per retirement evidence). See PANEL_SKIPPER.md §8 W4 amendment entry (2026-05-10 PM) for the full disposition record.
- Empirical anchors:
  - `etl/spikes/probe_era_b_status_u_full.py` + `_output.txt` — full era-B re-characterization probe.
  - `validation/reports/herd_null_characterization_findings.md` — revised W4 baseline (original three-spot-year characterization preserved as initial section; corrected era-B-wide baseline as locked section).
  - `etl/spikes/probe_unspec_zero.py` + Stage 5 smoke test output — original surface from HD 2.4.b round 1.

## Q9/Q11 row-absence asymmetry at FY 2017/2024

- Logged at HD 2.4 W4 NULL characterization spike (`etl/spikes/spike_herd_null_characterization.py`, 2026-05-09).
- At the (institution, discipline_fine) grain, FULL OUTER JOIN of Q9 Total-column rows against Q11 Total-column rows reveals a **persistent asymmetry**: 22–28% of cells have nonfederal R&D but no federal R&D, vs. 7–14% inverse. Findings: `validation/reports/herd_null_characterization_findings.md` §4.4.
  - FY 2017: Q9 row absent / Q11 value present = 4,592 (28.08%); Q9 value present / Q11 row absent = 2,281 (13.95%); both present = 9,478 (57.97%).
  - FY 2024: Q9 row absent / Q11 value present = 3,684 (22.11%); Q9 value present / Q11 row absent = 1,177 (7.06%); both present = 11,799 (70.82%).
- The asymmetry is large and persistent; row-absence-as-zero is the dominant null pattern on the era-B reconstruction's input side. Reading: institutions emit Q11 rows for disciplines where they have *only* nonfederal funding more than twice as often as the inverse — consistent with federal R&D being concentrated in fewer disciplines than nonfederal R&D for the marginal institution.
- Disposition: **no HD 2.4 build impact** — the era-B reconstruction rule (`crosswalks/era_b_reconstruction_rule.yaml` + W4 row-absent-as-zero lock) already handles row-absence correctly via FULL OUTER JOIN + COALESCE-to-zero. Methodologically interesting; worth a paragraph in the methods note's reconstruction-rule discussion eventually, framed as the federal/nonfederal concentration asymmetry. Not for HD 2.4 to resolve. Surface for downstream attention (a Primary Piece on agency-level federal R&D concentration could lean on this finding).

## HD 2.4.g precondition gate blocked — Table Builder maintenance window

- HD 2.4.g precondition gate blocked 2026-05-10 PM. NSF NCSES Table Builder under maintenance; estimated return next Monday (2026-05-17). Precondition verification requires interactive UI access; resumes when Table Builder available. HD 2.4.g substantive work (240-cell grid) cannot begin until precondition passes.
- Infrastructure already on disk: `etl/spikes/spike_dst_table_builder_reproducibility.py` (consumes maintainer-staged CSVs, surfaces byte/content-identity verdict), `data/reference/dst-table-builder/` staging directory. Spike returns NEEDS-STAGING (exit 3) until CSVs land; PASS (exit 0) on byte/content-identity; FAIL (exit 2) on non-deterministic exports (Vision kill criterion -> panel reconvene).
- Resume action 2026-05-17 (or whenever Table Builder available): maintainer runs the dual export per the HD 2.4.g precondition-gate spec (JHU 029977 × Engineering + Life sciences + Physical sciences × Federal + Nonfederal, FY 2024); stages two CSVs at `data/reference/dst-table-builder/precondition_export_{1,2}.csv` plus `precondition_metadata.txt`; Skipper runs the spike, surfaces verdict, proceeds to Surface 1 (historical anchor availability) on PASS.
