# PANEL_SKIPPER — Locked Engineering Decisions

Locked engineering decisions for the quadrivium HERD pipeline. Entries are dated, carry a one-sentence reason, and are not relitigated. Edits require a stated reason and a date.

External contributors can read this to understand why the codebase is shaped the way it is.

---

## §8 — Locked decisions

- **Environment isolation:** `uv` with `pyproject.toml` + committed `uv.lock`; chosen over `venv`+`requirements.txt` because reproducibility is the load-bearing constraint (Zenodo deposit). Installed with **uv 0.11.8** on **2026-04-29** (Python 3.12.10). The dep graph is pinned by `uv.lock`; the resolver itself is pinned by this line.

- **Pinned dependency files are deposit artifacts.** `pyproject.toml` and `uv.lock` are versioned alongside loader code and held to the same reproducibility standard. Exact-version pins only; ranges are not allowed in `[project.dependencies]`.

- **HD 2.4 §2 amendment-lock — DST publication-regime contraction (locked 2026-05-10).** Reason: *FY 2024 DST publication regime contracted from 86 PDFs to 55; Tables 28–54 (engineering subfield rankings, agency-specific rankings) became Table-Builder-only at HD 2.4.a Round 1.*

  **Disposition:** Option (b) Table-Builder-CSV-snapshot accepted with seven-item discipline (access date, SHA-256, cold-reader instruction, query-parameter YAML sidecar pattern, tool-interface stability disclaimer, two-tier re-verification path, methods-note cross-reference). §2 amendment-lock applied to `docs/methods_notes/herd_panel_etl_scoping.md`: §2(b) clarified (per-spot-year anchor-source table added — FY 2024 = Table Builder CSV snapshot); §2(d) split into §2(d.1) "Static-PDF anchors" and §2(d.2) "Table Builder CSV snapshots" carrying the seven-item staging discipline; §2(e) NEW "Publication-regime stability caveat." Methods-note regime-change paragraph added to `docs/methods_notes/reconstructive_harmonization.md` §6 ("What the deposit ships") under new sub-section "Reproducibility under publication-regime drift" — frames the regime change as the methodology working on its own conditions (Reconstructive Harmonization clause (a) extended to the verification-anchor layer), not an apology.

- **HD 2.4 W4 NULL-handling lock — empirical re-characterization amendment (original locked 2026-05-09; amended 2026-05-10 PM).** Reason: *the W4 NULL spike's three-spot-year sample (FY 2008 / 2017 / 2024) produced a fundamentally incomplete empirical baseline. The locked "FY-2017-only / non-Total-only" assertion was a sampling artifact, not data behavior.*

  **Original lock state (2026-05-09).** W4 NULL-handling lock shipped with the four-value `quality_flag` enum (`reported / imputed / estimated / unspecified_zero`), the least-good-flag-wins propagation ordering (`unspecified_zero < estimated < imputed < reported`), the row-absent-as-zero arithmetic per FY24 Guide pages 8 / 23, and the Stage 9 sanity assertion "every output row with `quality_flag='unspecified_zero'` carries `year=2017` and column != 'Total'."

  **Surface (2026-05-10).** HD 2.4.b round 1 Stage 5 smoke test emitted 9 panel rows with `quality_flag='unspecified_zero'` at FY 2020 Q14 `column='Total'` / institution_id `'003446'` (South Carolina State University, HBCU). Both clauses of the locked assertion violated. HD 2.4.d disposition probe extended scope from three spot years to all era-B years 2010–2024 + short-form (`etl/spikes/probe_era_b_status_u_full.py`); findings substantially re-characterize the baseline:

  - ~4,000 `status='u'` rows across era-B 2010–2022, not FY-2017-only (range 117–874/year, declining trend).
  - 106 distinct institutions emit; 56 multi-year; several emit for 10+ consecutive years. Pattern is predominantly smaller / less-research-intensive institutions and HBCUs.
  - FY 2023 and FY 2024 contain zero `status='u'` rows — NSF retired the encoding without Guide documentation of the convention change (sixth instance of publication-regime stability pattern).
  - Panel impact is 9 rows at FY 2020 Q14 `column='Total'` / SCSU.

  **Disposition (locked 2026-05-10 PM):** Option **δ (re-characterize the W4 baseline)** + Option **γ-allow (let the 9 panel rows propagate)**. Carving the 9 SCSU rows would create an HBCU-specific exclusion footnote that reads worse at deposit-audit time than acknowledging broader codeset scope; the values are positive numeric (4–17 kUSD across 9 leaves) and represent reported R&D dollars carrying a status flag, not data degradation. Reconstructive Harmonization clause (a) doctrine ("reconstruct what each era can support on its own terms") aligns with updating the W4 baseline to reflect the data.

  **What landed:**
  - `validation/reports/herd_null_characterization_findings.md` — revision header at top noting 2026-05-10 PM amendment; original three-spot-year characterization preserved as §§1–5 "Initial characterization (revised 2026-05-10)"; new §§6–8 add corrected empirical baseline with per-year `status='u'` counts, institutional emission pattern, FY 2023+ retirement evidence + three-tier corrected baseline locked.
  - `docs/methods_notes/herd_panel_etl_scoping.md` §1 — `quality_flag` value semantics for `unspecified_zero` updated to: *"The FY24 Guide documents `'u'` as a valid status code; the empirical scope of its emission across era-B 2010–2022 (~4,000 rows, 106 institutions, retired FY 2023+) is documented in this deposit's quality-flag characterization."* Posture: the deposit documents empirical scope, not Guide deficiency.
  - `docs/methods_notes/herd_panel_etl_scoping.md` §6.2 Stage 9 — sanity assertion text replaced with three-tier corrected baseline: (a) era-A `unspecified_zero` rows raise (era-A never emits `status='u'`), (b) era-B rows outside 2010–2022 raise (resumption warrants panel reconvene), (c) era-B 2010–2022 rows allowed per corrected baseline.
  - `crosswalks/era_b_reconstruction_rule.yaml` `quality_flag_propagation.consumer_contract` — Stage 9 assertion clause updated with the three-tier corrected baseline; existing propagation ordering and row-absence semantics preserved.
  - `etl/build_herd_panel.py` Stage 9 — assertion implementation matches the three-tier corrected baseline.

  **Revised kill criterion for the W4 NULL-handling lock:**
  - Codeset extensions (new enum values beyond `reported / imputed / estimated / unspecified_zero`) still require Guide-documented anchor or panel-touch per CLAUDE.md §4 codeset-extension policy.
  - Empirical scope adjustments to existing enum values (where the value appears, with what frequency) do NOT require codeset extension treatment; they require updating the lock's empirical baseline documentation. Two-tier gate: novel codeset values escalate to panel; scope shifts on existing values pass through documentation.
  - Drift-defense assertion redesigned per the three-tier corrected baseline above.

- **HD 2.4 sampling methodology lesson — three-spot-year sampling insufficient for cross-temporal NCSES encoding patterns (locked 2026-05-10 PM).** Reason: *two cases now of three-spot-year sampling producing a substantively wrong baseline. The pattern generalizes to spike design discipline beyond `status='u'`.*

  **Empirical evidence:**
  - HD 2.4 W4 NULL characterization spike sampled FY 2008 / 2017 / 2024 and concluded `status='u'` is "FY-2017-only / non-Total-only"; full era-B scan (HD 2.4.d round 1) showed ~4,000 rows across 2010–2022.
  - HD 1.4 era-B reconstruction-rule spike anchored to N=34 era-A cells without first scanning era-B for question-structure changes; the rule-design surface (era B fragmented the single field-level question into two source-class questions) was caught by the spike's failure mode but not by the spike's sampling design.

  **Lesson:** *Spike sampling for empirical characterization of cross-temporal NCSES encoding patterns must default to era-wide coverage; three-spot-year sampling is reserved for spikes whose kill condition does not depend on cross-temporal scope completeness.*

  **Operational discipline (Skipper authority, effective for HD 2.4.e+ sub-tasks):**
  - Spike question framing: when the question is *"what is the empirical scope of an encoding convention across time?"* the answer cannot be sampled from three spot years. Default to era-wide coverage (era-A 1975-2009, era-B 2010-2024) for empirical-characterization spikes.
  - Three-spot-year sampling reserved for: assumption-testing spikes whose kill condition is not cross-temporal; proof-of-concept spikes.
  - Cycle-cost trade-off: era-wide coverage runs ~10-15× the years of a three-spot scan but typically completes in <30s on era-B data given DuckDB's per-year scan speed.

- **HD 2.4.g entry sub-action — stop-and-surface dispositions (locked 2026-05-20).** Two locked dispositions (item-2 substrate-source: Skipper call per available NCSES historical publication; item-5 MANIFEST architecture: separate `data/reference/MANIFEST.md`). Skipper ran items 1–6 against an estimated 1–1.5 half-day budget; the actual session surfaced two **blocking findings** that stopped the sub-action short of full completion.

  **Finding 1 — Table-Builder-driving blocker (item 1).** The NSF NCSES Table Builder at `https://ncsesdata.nsf.gov/builder/herd` is a JavaScript SPA; WebFetch returned the bare app shell ("NCSES | NSF") without any rendered UI surface. No documented URL-parameter export contract was discoverable via search or NCSES-site walks. The FY 2024 grid CSV stage requires a human-driven UI path.

  **Finding 2 — Historical-vintage regime-stability blocker (item 2).**
  - **FY 2017** has a published DST (NSF 19-302 / archive namespace `ncsesdata.nsf.gov/herd/2017/`, accessed via Wayback). The DST publishes the institution × field × source-of-funds matrix as **three 2-D slices** (Table 12 field × source; Table 21 institution × source; Table 22 institution × field) — **not** the 3-D matrix the §2(b) verification grid wants. The 3-D matrix cannot be cell-reconstructed from the three 2-D slices without margin assumptions that defeat the verification purpose.
  - **FY 2010** and **FY 2008** historical archives at the per-year namespace returned 404 on live URLs and were not located in the Wayback namespace probed during this session.

  **Three scope-shape branches surfaced for resolution.**
  - **Branch I — contract the verification grid to FY 2024 only.** The 60-cell FY 2024 sub-grid consumes the Table Builder CSV snapshot directly per §2(d.2). Historical vintages downgrade to descriptive caveats in the methods note.
  - **Branch II — reconstruct the historical spot-year cells from the published 2-D slices where possible.** Adds methodological complexity at the verification-anchor layer that arguably defeats the verification purpose.
  - **Branch III — drop the per-spot-year historical anchor; rely on HD 2.1.b's residual report as the cross-era verification surface** and use the FY 2024 grid as the era-B-internal verification anchor. Reframes Branch A from "cell-by-cell cross-era verification" to "era-B-internal cohort-anchored verification at the most recent spot year," with the era-boundary characterization absorbed entirely into the HD 2.1.b decomposition.

  **What shipped:**
  - **Item 3 — YAML sidecar template scaffolded** at `data/reference/dst-table-builder-FY{YEAR}-query.yaml.template`.
  - **Item 5 — `data/reference/MANIFEST.md` shipped** per Option (b): new MANIFEST parallel to `data/raw/MANIFEST.md`. Covers 7 PDFs + 3 dst-table-builder files.

- **HD 2.4.g entry sub-action continuation — FY 2024 grid anchor staged + substrate finding locked (2026-05-21).** Maintainer drove the Table Builder UI 2026-05-21, landed the FY 2024 grid anchor CSV at `data/reference/dst-table-builder/dst-table-builder-FY2024.csv` (SHA-256 `e0fc1f7b08f32f8963463ba591e18a188fbfc9d9f4584f2ffc50778ef46738a6`, 3,472 bytes), and surfaced a substantive empirical finding that reshapes the §2(b) grid composition.

  **Finding 1 — Table Builder UI navigation hazard.** Correct measure path: "R&D Expenditures for All Institutions" > "By Broad Field and Federal and Nonfederal Sources". The reproducer must explicitly **deselect** the "Detailed Field of Study" dimension; the detailed-field × standard-form-only coupling is a UI navigation hazard for cold reproducers who walk the YAML sidecar's `query_parameters` block to re-issue the query. The standard-form-only detailed-field view is not the all-respondents grid the reconstruction rule expects.

  **Finding 2 — UCSF Engineering structural absence (empirical substrate finding).** The FY 2024 export contains 58 substantive cells, not the nominal 60 (10 institutions × 3 disciplines × 2 source classes). UCSF (inst_id 001319) is missing both Engineering cells (federal and nonfederal). Diagnosis: UCSF is a health-sciences-only institution; the UC system Engineering R&D base lives at Berkeley, San Diego, Los Angeles, Irvine, and Davis — not San Francisco. The cell absence is structural at the institution-substrate level (no Engineering school exists), not suppression, not a NCSES disclosure-rule artifact.

  **Finding 3 — 58-cell empirical grid replaces 60-cell nominal grid (Path A disposition).** Disposition: **Path A — accept the 58-cell empirical grid as the FY 2024 verification anchor; document the UCSF Engineering structural absence honestly in the scoping doc, methods note, YAML sidecar, MANIFEST, and citations.** Path A is preferred over coercing the FY 2024 grid back to a nominal 60-cell composition with imputed UCSF Engineering zeros: structural substrate absence is methodologically distinct from a documented zero (zero R&D in an existing discipline) and should not be papered over.

  **§2(b) re-shape pass (2026-05-21 — Branch III adopted).** §2(b) header renamed to "FY 2024 era-B-internal cohort-anchored verification grid — locked." Per-spot-year anchor table contracted from 4 rows to 2 rows (FY 2024 anchor + cross-era verification surface inherited from `validation/reports/era_reconciliation_2008_2011.md`). FY 2017 / FY 2010 / FY 2008 rows moved to a new "§2(b) caveat block — historical-vintage anchors deferred" carrying Branch III rationale + three expansion triggers (NCSES historical-publications hunt; future surface; reviewer-driven re-open). 240-cell nominal grid retired; 58-substantive-cell FY 2024 era-B-internal cohort-anchored verification grid is the artifact.

  **Filename convention alignment (2026-05-21).** Sidecar materialized at scoping-doc-convention filename `data/reference/dst-table-builder-FY2024-query.yaml` (matches `dst-table-builder-FY{year}-query.yaml` convention from `herd_panel_etl_scoping.md` §2(d.2)).

  **Pre-commit kill criteria (locked 2026-05-21).** For any future verification-grid expansion (a NCSES historical-publications hunt that surfaces a static-PDF anchor for FY 2017 / FY 2010 / FY 2008; a contributor-proposed methodology amendment to the substrate-shape disposition; a reviewer-driven re-open at deposit time): the expansion lands only if (a) the static-PDF anchor publishes the 3-D matrix at the cohort grain, not 2-D slices that defeat the verification purpose; (b) the substrate-shape finding (UCSF Engineering structural absence) propagates honestly into the expanded grid, not papered over with imputed zeros; (c) the methods-note language ships the expansion as a clause-(a) reconstruction primitive at that vintage, not as a bridge to the FY 2024 anchor.

- **HD 2.4.g §8 combined entry — entry-phase budget retrospective + Branch A spike outcome + tolerance posture + rollup-row grain insight (locked 2026-05-24; HD 2.4.g sub-action CLOSES on this entry).** Reason: *the FY 2024 era-B-internal cohort-anchored verification grid (Branch A) returned 58/58 PASS at +0.000% precision, 2 structural absences (UCSF Engineering), and no systematic-divergence signal — empirically validating Vision Branch III and the Reconstructive Harmonization clause-(a) reconstruction primitive at the verification-anchor layer.*

  **Three interpretive observations (lead-in narrative).**
  1. **Era-B-internal reconstruction primitive empirically exact at FY 2024.** Reconstructive Harmonization clause (a) holds at the verification-anchor layer at deposit-grade precision — all 58 substantive cells matched the FY 2024 Table Builder anchor at +0.000%.
  2. **Vision Branch III empirically validated.** Era-B-internal anchoring at the most recent spot year produces verification at the exact-match level; the reframed §2(b) scope (240-cell nominal grid retired → 58-substantive-cell FY 2024 grid) is empirically defensible.
  3. **Preconditions read produced load-bearing methodological insight.** The `discipline_fine` rollup-grain filter (observation (d)) prevented a systematic double-count that would have manifested as ~2× divergence across all 58 cells. The 0.25-half-day preconditions investment bought verification-grade precision.

  **(a) Entry-phase budget-overrun retrospective.** The HD 2.4.g entry phase ran ~2× the §10 timeline's 1.5-half-day HD 2.4.g allocation (~3 half-days actual). The overrun bought: three substrate-shape findings (the publication-regime discontinuity — the 86→55 DST contraction plus the FY 2017 2-D-slice publication shape that defeats 3-D cell reconstruction; the UCSF Engineering structural absence; the Table Builder UI navigation hazard), the Vision consultation turnaround on the Branch I/II/III scope-shape fork, and the §2(b) re-shape pass scope addition. The overrun is recorded as anticipated investigation, not slip — the cost *is* the substrate-shape findings it bought. Per the entry-phase budget heuristic (`memory/feedback_hd_entry_phase_budget.md`): entry phases that cross a known operational-data discontinuity surface pre-allocate ~2× the §10 baseline.

  **(b) Branch A spike outcome.** `etl/spikes/panel_anchor_verify.py` run end-to-end on the FY 2024 era-B-internal cohort-anchored grid: **58/58 PASS at +0.000% precision**; **2 STRUCTURAL_ABSENT** (UCSF inst_id 001319 Engineering × federal + nonfederal, null panel value — no kill signal fired); **3 cells carry `quality_flag='imputed'`** (Johns Hopkins nonfederal × Engineering / Life sciences / Physical sciences), all matching the anchor at +0.000% — recorded as empirical observation; methodological framing deferred to HD 2.4.h prose plus the queued substrate-scoping probe (below). Preconditions-read insight is the `discipline_fine` rollup-grain filter (observation (d)). The systematic-divergence diagnostic did not fire — median |pct_diff| = 0.000%, below the 0.5% trigger, so it *could not* have fired (the precision records why, not just that it didn't). Spike runtime sub-second post-precondition. Artifacts: `etl/spikes/panel_anchor_verify.py` + `etl/spikes/_out/panel_anchor_verify_FY2024.parquet` (committed 73a9eae). Throwaway spike; production hardening (`validation/reports/panel_anchor_reconciliation.md`, methods-note voice) lands at HD 2.4.h.

  **(c) Tolerance posture.** Skipper-default descriptive bands (PASS |pct_diff| ≤ 0.5%; REVIEW 0.5% < |pct_diff| ≤ 2%; FAIL > 2%) per Path B (empirical/descriptive) tolerance discipline (CLAUDE.md §7 disposition 5). Bands principal-authorized 2026-05-24 (spike header) but **not exercised** — all 58 substantive cells matched at +0.000%, so no cell entered the REVIEW or FAIL band. Production tolerance locks at HD 2.4.h (Vision), based on the broader empirical distribution observed across the validation report's full scope.

  **(d) Rollup-row grain insight.** Era-B reconstruction at the verification-anchor layer requires filtering panel rows on `discipline_fine IN ('Engineering, all', 'Life sciences, all', 'Physical sciences, all')`, not on `discipline_coarse`. Each coarse bucket carries both a `<bucket>, all` rollup row AND the underlying fine leaves; a `discipline_coarse` filter double-counts (rollup + leaves → ~2× the anchor). The rollup row is the stable comparison surface across the 2010 redesign's fine-leaf shifts. Methods-note prose seed for the HD 2.4.h production pass (`validation/reports/panel_anchor_reconciliation.md`).

  **JHU imputed-pattern probe (queued HD 2.4.h scoping item).** The 3 imputed JHU-nonfederal cells are recorded here as empirical observation only. The queued probe is a ~30-minute grep-check at HD 2.4.h scoping of whether other classified-DOD-handling institutions (MIT Lincoln Labs, JPL/Caltech, Sandia affiliations) carry similar imputed-flag patterns at the nonfederal source class. Outcome shapes HD 2.4.h scope: if the APL-DOD signal hypothesis strengthens, the methods-note prose gets richer treatment and possibly a new research seed under the substrate-shape umbrella. Better probed with HD 2.4.h scope-shaping in view than landed here as a §8 empirical detail.

  **HD 2.4.g sub-action: CLOSED on this entry.**
