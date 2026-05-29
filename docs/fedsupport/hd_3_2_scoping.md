# HD 3.2 Scoping — Federal S&E Support module: institution-identity spine + parse/taxonomy

**Status:** scope ratified by principal 2026-05-29. Name-match de-risking spike (§11) **executed and ACCEPTED 2026-05-29**; both lenses concurred PROCEED. **MVP greenlit, sized to the spike's second-pass mechanical baseline + budgeted manual tail.** Deferred items (8→6 taxonomy, HERD path-move, obligation-vs-expenditure seam = HD 3.6) held per §5. MVP surfaces when the spine + receipt land, before any deposit/release work.
**Authored by:** Skipper (engineering scope) + Maintainer (persisted). 2026-05-29.
**Authorization trail:** HD 3.1 gate (K1 FIRED) → §3 acquisition-format lock + §4 cross-survey identity-spine addendum ratified → HD 3.2 scope ratified.

**Inputs grounded in:** `validation/reports/fedsupport/hd_3_1_acquisition_gate_findings.md` (HD 3.1 gate, K1 FIRED — name+state-only identifier); `etl/spikes/spike_fedsupport_acquisition_probe.py` (throwaway gate spike, three-vintage boundary slice); CLAUDE.md §3 acquisition-format lock (xlsx→CSV at acquisition + PDF audit sibling), §4 cross-survey identity-spine addendum (UNITID-canonical, two-number match-rate receipt), §10 multi-survey subtree structure + IPEDS-cycle deferral of comprehensive identity-over-time; `docs/hd_2_1_scoping.md` (format + estimate-table precedent); `etl/_load.py` (extract-on-read → `read_csv_auto` → `UNIFIED_COLS` loader pattern); `data/raw/MANIFEST.md` (zip-provenance / checksum model the CSV staging mirrors).

---

## 1. What ships (one sentence)

HD 3.2 ships the **Federal S&E Support FY2020–FY2023 long-format parse** (Table 12 higher-ed institution rows, xlsx→CSV-at-acquisition, vol-71 column-taxonomy crosswalk) **plus the cross-survey institution-identity spine** (`crosswalks/_shared/`) that resolves that survey's institution set to IPEDS UNITID — the first-class join artifact, built spine-shaped from row one, with per-row `decision_rationale` and a two-number match-rate receipt.

---

## 2. The artifacts to build

Two artifact clusters. The **parse/taxonomy** cluster turns Table 12 into a harmonized long relation; the **spine** cluster makes it joinable to HERD. They are sequenced (parse first — the spine needs the parsed name+state set as its left side) but co-scoped.

| # | Artifact | Path | Role | Notes |
|---|---|---|---|---|
| 1 | Staged raw CSVs + PDF audit siblings | `data/raw/fedsupport/` (gitignored payload; MANIFEST entries tracked) | acquisition | One CSV per (year, Table 12), xlsx→CSV converted **once at acquisition** per §3 lock. PDF sibling per year → `data/reference/`. SHA-256s into `data/raw/MANIFEST.md` (new `fedsupport` section, mirrors HERD zip provenance). The four gate-slice hashes in HD 3.1 §7 are provenance seeds, not deposit entries — re-fetch + re-checksum at acquisition. |
| 2 | `fedsupport` loader | `etl/_load.py` (extend) or `etl/_load_fedsupport.py` (new) | parse | Mirrors `read_herd_csv` extract-on-read → `read_csv_auto` → unified long relation. Strips NCSES title/footnote bands; un-nests the state-header → indented-institution hierarchy in Column A into explicit `state` + `institution_name_raw` columns. **Loader-shape call deferred to build** (extend vs. new module). |
| 3 | Vol-71 column-taxonomy crosswalk | `crosswalks/fedsupport/type_of_activity_map.csv` | RH clause-(a) | 8-col (FY≤2020) → 6-col (FY2021+) type-of-activity crosswalk. Per-row `decision_rationale`. **The 8→6 mapping itself is DEFERRED to execution** (§5) — this scope reserves the artifact + budget, not the resolved rows. |
| 4 | Parsed long relation | `data/harmonized/fedsupport_obligations.parquet` | parse output | Long-format: `(year, state, institution_name_raw, ipeds_unitid, activity_type, value_kusd, source_table, source_file, quality_flag, notes)`. UNITID populated **via artifact #5** (spine), not free-string-matched. |
| 5 | **Institution-identity spine** | `crosswalks/_shared/institution_identity.csv` | RH clause-(a) **first-class object** | name+state → UNITID (canonical) + ncses_inst_id/HERD-side aliases. One row per resolved FedSupport institution, per-row `decision_rationale` (match method: exact / normalized / manual / unresolved). **UNITID-canonical and spine-shaped from row one** (approach (a) seeded by (b), per carry-forward constraint 2). This is the dominant-cost artifact. |
| 6 | Match-rate receipt | `validation/reports/fedsupport/identity_spine_match_rate.md` | RH clause-(c) | Publishes **TWO numbers** per §4: institution-match rate AND dollar-match rate (matched dollars / $48,961,658K FY2023 anchor). Unmatched-tail disposition is **DEFERRED** (§5; default Path B). |
| 7 | Parse validation receipt | `validation/reports/fedsupport/fedsupport_parse_reconciliation.md` | validation | Reconciles the parsed FY2023 Table 12 grand total to the **$48,961,658K higher-ed-only anchor** (HD 3.1 §2 — do NOT free-sum higher-ed + nonprofit). Per-year grand-total receipts for FY2020/2021/2023. |

**Where the §10 path-move rides.** The flat HERD crosswalks (`crosswalks/*.csv`) move to `crosswalks/herd/` **with** artifact #3 landing — the first `fedsupport` crosswalk. This is the §10-locked tie-the-move-to-a-touch-moment. Listed here as a sequencing fact; the move itself is **DEFERRED** to execution (§5), it is not an HD 3.2 design decision.

---

## 3. The ~2× linkage-surface call-out (Vision flag ③ — named explicitly)

**The institution-identity spine is the entry-phase ~2× allocation. This is anticipated spend, not overrun.**

Per `[[feedback-hd-entry-phase-budget]]` and HD 3.1 §8: the Federal S&E Support module carries **no shared join key** with HERD/IPEDS. The only identifier is NSF house-style abbreviated name + state grouping (`Auburn U., Auburn`; `U. Alabama, The, Birmingham`) — which will **not** string-match HERD `inst_name_long` or IPEDS canonical names. This is a known cross-source-linkage-without-a-shared-key discontinuity surface, the most expensive kind of crosswalk this project builds.

The budget consequence, stated up front so the principal reads the number as expected:

- A **mechanical crosswalk baseline** (e.g., a documented column-rename map) is ~1 unit.
- The **name-reconciliation spine** is **~2× that baseline** — because it requires a normalization pass, a fuzzy/assisted match round, a manual-resolution tail for the abbreviations that defeat normalization, and a per-row `decision_rationale` audit trail for every match decision. The ~2× lives almost entirely in artifact #5 (the spine) and is the reason this dataset's entry phase costs what it costs.

If the spine comes in at ~2× the mechanical baseline, **that is the scope working as designed.** The overrun signal is not ~2× — it is drift past ~2× toward ~4×, which is what §4 guards against.

---

## 4. HARD scope guardrail — kill identity-object drift on sight

**The spine resolves ONLY the FY2020–FY2023 Federal S&E Support institution set to UNITID. Nothing else.**

This is the explicit guardrail per carry-forward constraint 3. Stated as a kill condition, not a preference:

- **In scope:** the ~1,110-institution FY2023 higher-ed set, plus whatever additional institutions appear in FY2020/2021/2022 Table 12 but not FY2023 (the active-survey-set scope, §4 addendum). Each resolved to a current UNITID with a `decision_rationale`.
- **OUT of scope — KILL on sight:** comprehensive institution-identity-over-time as a reconstruction object. Mergers, renames across decades, UNITID reassignment history, dead-institution resolution, the full NCSES↔IPEDS registry. That is the **IPEDS-cycle** deliverable (§10), explicitly deferred.

**Why this is a hard guardrail and not a soft one.** The "while we're here, the spine would be more useful if it were the full identity object" temptation is Stage-smuggling: it pulls an IPEDS-cycle deliverable into the FedSupport cycle. It does not turn ~2× into ~2.2×; it turns ~2× into **~4×**, because a comprehensive identity-over-time object is a multi-decade entity-resolution build with its own validation surface. Any task framed as "generalize the spine," "make it reusable for all surveys," or "resolve historical identity while we have the names open" is **out of HD 3.2** and reopens as a Vision-level scope call against §10.

The spine is built UNITID-canonical and spine-*shaped* (constraint 2) precisely so that the IPEDS cycle can *extend* it later without a rebuild — but HD 3.2 populates only the FY2020–FY2023 FedSupport rows. Shape now, scope tight.

---

## 5. Explicit deferral list (named, NOT resolved here)

Per the authorization, these are surfaced as deferred-to-execution. HD 3.2 scope reserves the artifact + budget for each; it does **not** resolve them in this doc.

1. **Match-rate target / threshold + unmatched-tail disposition.** Default = **Path B (empirical/descriptive)**, mirroring HD 2.1.b §7 disposition 5 — we build the spine, publish the two match-rate numbers, document the unmatched tail descriptively, no pre-committed pass/fail threshold. A published NCSES match-rate referent surfacing post-build switches to Path A (logged to `seeds/overrides.md`). **Resolved at build, not scoping.**
2. **The 8→6 vol-71 type-of-activity crosswalk (RH-native).** The specific column-mapping rows (which FY2020 columns roll into which FY2021+ columns; whether "Facilities and equipment" = "Facilities for instruction" + something, etc.) are authored at build against the per-table headers. HD 3.1 §4 establishes the discontinuity exists and is RH-native; **the mapping rows are deferred.**
3. **The HERD-crosswalk path-move** (`crosswalks/*.csv` → `crosswalks/herd/`). Rides with artifact #3 per §10. The move mechanics (updating read paths in `etl/build_herd_panel.py`, the harmonized parquets need no move per §10) are a build task, **deferred.**

Plus two scoping-surfaced sub-deferrals (named so they don't slip in as silent build asks):

4. **The obligation-vs-expenditure seam decomposition — HD 3.6, RH clause-(b).** Federal-FY commitments vs. institution-FY spending. Per CLAUDE.md §1 analytical thread this is its own decomposition object on the funding-IN ↔ expenditure-OUT join, and is sequenced as **HD 3.6**. HD 3.2 builds the **funding-IN parse + the join spine**; it does **not** build the seam decomposition. **Consumer-hazard carried to HD 3.6 (see §8.5):** the HD 3.2 join contract must explicitly flag the FY-basis difference so a downstream consumer — including a Power BI semantic model built on the parquet — cannot misread a timing gap as funding-conversion efficiency.
5. **Loader-shape call** (extend `etl/_load.py` vs. new `etl/_load_fedsupport.py`). Build decision; the FedSupport schema differs enough from `UNIFIED_COLS` (no questionnaire/discipline grain; activity-type measures) that a sibling module is likely, but that's an execution pick.

---

## 6. MVP vs. production boundary

Assumes 8 half-days/week, single builder. Buckets: **clean** (mechanical), **ambiguous** (defensible-either-way, needs panel touch), **spike** (genuinely unknown).

### MVP (2-week / ~16 half-day) scope — the spine + FY2023 anchor parse

The MVP proves the expensive thing (the spine) against the anchor year, and parses the full FY2020–FY2023 window so the boundary is real, not promised.

| Task | Half-days | Bucket |
|---|---:|---|
| Acquire FY2020/2021/2022/2023 Table 12 (xlsx + PDF); xlsx→CSV once; MANIFEST `fedsupport` section; PDF siblings → `data/reference/`. | 1.0 | clean |
| `fedsupport` loader: band-strip + un-nest state/institution hierarchy → long relation, all 4 years. | 2.0 | ambiguous (hierarchy un-nest is the wrinkle) |
| Parse reconciliation receipt: FY2023 grand total → $48,961,658K higher-ed anchor; per-year grand totals. | 1.0 | clean |
| **Spine — normalization pass.** NSF-abbreviation normalizer (expand `U.`→University, strip `, The`, split city suffix). | 2.0 | spike → MVP (see §11) |
| **Spine — assisted match round** against HERD-side UNITID set (`crosswalks/herd/` + era-B `ipeds_unitid`). Exact + normalized match. | 2.5 | ambiguous |
| **Spine — manual-resolution tail** for normalization-defeating abbreviations; per-row `decision_rationale`. | 3.0 | ambiguous (this is the ~2× core) |
| Two-number match-rate receipt (institution-match % AND dollar-match %). | 1.0 | clean |
| Vol-71 taxonomy crosswalk — **stub only** (artifact exists, FY2023 6-col columns mapped to canonical names; the 8→6 boundary rows deferred). | 0.5 | clean |
| Path-move ride-along (`crosswalks/*.csv` → `crosswalks/herd/`; fix `build_herd_panel.py` read paths; rerun build to confirm bit-identical parquet). | 1.5 | clean (mechanical, but touches the HERD build — verify reproducibility) |
| Buffer / catch-up. | 1.5 | — |
| **MVP total** | **16.0** | ~2 weeks |

**MVP cuts (explicitly out of the 2-week version):**
- The resolved 8→6 vol-71 crosswalk rows (stub only — boundary decomposition deferred).
- The methods-note section for FedSupport (the parse + spine are crosswalk-shaped; prose comes in the production scope).
- Great Expectations suites (HERD's HD 2.6 analog — not MVP).
- The BEA deflator (FedSupport obligations stay current-dollar, mirrors HERD HD 2.5 deferral).
- Any FY2019-and-earlier acquisition (the spine + boundary live in FY2020–FY2023; earlier years are a later era-extension HD).

### Production (8-week) scope — what gets added

| Added over MVP | Half-days | Bucket |
|---|---:|---|
| Resolved vol-71 8→6 type-of-activity crosswalk with per-row `decision_rationale` + boundary characterization. | 2.0 | ambiguous |
| Path A external-referent search for a published NCSES match-rate tolerance (1 half-day budget); override-log path. | 1.0 | clean |
| FedSupport methods-note section (`docs/methods_notes/fedsupport/`) — spine-as-RH-clause-(a) narrative + two-number match-rate receipt framing, cold-reader voice. | 3.0 | ambiguous prose |
| Great Expectations suite for the parse + spine (grand-total invariant, UNITID-uniqueness, no-orphan-state). | 2.0 | clean |
| Era-extension: FY2010s acquisition + parse to widen the funding-IN series (still pre-seam). | 4.0 | clean + spike on early-vintage table format |
| Manual-tail second pass + spine hardening (the unmatched tail almost always has a long thin tail of edge institutions). | 2.0 | ambiguous |
| Zenodo deposit packaging for the **separate `fedsupport` concept DOI** (§10 Decision B; release runbook reused with new params). | 2.0 | clean |
| **Production delta** | **~16 added** | total ~4 weeks build + validation/deposit ≈ 8-week calendar for a part-time builder |

The 8-week framing is honest: the **harmonization (parse + spine) is the 2-week MVP**; the validation receipts, the methods-note section, the resolved boundary crosswalk, the era-extension, and the separate Zenodo deposit are the other ~6 weeks. Same integration-tax ratio HD 2.1 surfaced.

---

## 7. Reuse first

| Need | Reuse | File |
|---|---|---|
| Extract-on-read → `read_csv_auto` → unified long relation | The `read_herd_csv` / `read_herd_short_form_csv` pattern (band handling, encoding fallback, projection to a stable column tuple). | `etl/_load.py` |
| xlsx→CSV-at-acquisition + PDF audit sibling | Pattern proven viable in HD 3.1 gate; PDF-via-pypdf precedent is the Table-26 anchors. | `etl/spikes/spike_fedsupport_acquisition_probe.py`; `data/reference/` |
| Checksum-into-MANIFEST provenance | The HERD zip-provenance model (gitignored payload, tracked MANIFEST + `_checksums.txt`, Windows + POSIX regeneration recipes). | `data/raw/MANIFEST.md` |
| Crosswalk-with-`decision_rationale` shape | Every existing crosswalk carries the column; the spine + taxonomy map mirror it. | `crosswalks/question_map.csv`, `crosswalks/discipline_fine.csv` |
| HERD-side UNITID set for the match | era-B `ipeds_unitid` in the harmonized panel + HERD crosswalks. | `data/harmonized/herd_panel.parquet`; `crosswalks/herd/` (post-move) |
| Two-number RH-clause-(c) receipt format | The era-reconciliation report structure (prose + per-cell table). | `validation/reports/era_reconciliation_2008_2011.md` |
| Scoping-doc + estimate-table format | This document's own structure. | `docs/hd_2_1_scoping.md` |

New code is concentrated in exactly one place that earns it: the **NSF-abbreviation normalizer + match logic** (no HERD precedent — HERD never had to reconcile abbreviated names to UNITID; it carried `ipeds_unitid` natively in era B).

---

## 8. Hidden edges (the non-obvious risks)

1. **The state-header / indented-institution hierarchy in Column A is positional, not keyed.** *(Principal-flagged: the loader's real difficulty.)* Table 12's Column A nests institution rows under state rows by indentation/ordering, with a leading "All states and outlying areas" grand-total row and per-state subtotal rows interleaved. The parser must distinguish grand-total / state-subtotal / institution rows **without a row-type column** — likely by indentation whitespace or by the presence of a state name in a fixed list. Get this wrong and you either double-count (summing subtotals + institutions) or drop institutions. The loader must robustly *infer* state-header vs. institution rows. This is the loader's real difficulty and why it's 2.0 half-days, not 0.5.

2. **NSF abbreviation collisions across the city suffix.** *(Principal-flagged: the most dangerous of the three catches — tested explicitly in the spike, §11.)* `U. Alabama, The, Birmingham` and `U. Alabama, The, Tuscaloosa` are distinct UNITIDs that normalize to nearly identical strings; the city suffix is load-bearing for disambiguation. The normalizer must **preserve** the city token as a disambiguator, not strip it. A normalizer that over-collapses merges two real institutions into one spine row — a silent dollar-misattribution that **survives validation if match-rate is computed at the wrong grain**. The spike must surface any such collapse before MVP.

3. **HERD-side UNITID coverage is canonical-not-complete (§4 addendum).** Era-A HERD has no UNITID. If the spine matches FedSupport institutions against the HERD UNITID set, the era-A coverage gap means some FedSupport institutions match a HERD *name* but have no HERD-side UNITID to anchor to. The spine must resolve to UNITID from the **era-B** HERD side (which carries `ipeds_unitid`), and the match-rate receipt must footnote that the spine's UNITID anchor is era-B-sourced.

4. **The vol-71 column-taxonomy redesign is not 1:1.** HD 3.1 §4: FY2020 has 8 value columns, FY2021+ has 6. "Facilities for instruction…" + "General support for S&E" + "Other S&E activities" do not map cleanly onto "Facilities and equipment" + "Other general support." This is the RH-native boundary — and it means the **harmonized `activity_type` enum has its own decomposition residual**, parallel to HERD's 2008→2011 four-bar. Deferred (§5), but budgeted: the production-scope 2.0 half-days assumes a residual exists.

5. **Obligations are federal-FY, HERD expenditures are institution-FY (the seam → HD 3.6).** *(Principal-flagged: carry to HD 3.6 as a consumer-hazard.)* Even a perfect spine join produces a funding-IN vs. expenditure-OUT series on **different fiscal-year definitions**. HD 3.2 must NOT silently join them as if same-year-comparable. **The HD 3.2 join contract carries an explicit FY-basis flag** (the parsed output marks obligations on the federal-FY basis via a `notes`/contract field) so that **no downstream consumer — including a Power BI semantic model built on the parquet — can misread a timing gap as funding-conversion efficiency.** The seam decomposition itself (clause-(b)) is **HD 3.6**, explicitly deferred (§5.4). The 2 a.m. failure mode is a downstream consumer free-joining FY2023-obligations to FY2023-expenditures and reading the gap as efficiency when half of it is the FY-basis seam — the join contract's FY-basis flag is what prevents it.

---

## 9. Validation plan

- **Parse ground truth:** FY2023 Table 12 grand total = **$48,961,658K** (HD 3.1 §2, higher-ed-only, reconciles to NSF 25-341 InfoBrief $49.0B / 1,110 institutions). Per-year grand totals for FY2020 ($39,122,152K), FY2021 ($43,222,829K), FY2023 anchor. **Filter to higher-ed; do NOT free-sum across nonprofit Table 32/33.** Report → `validation/reports/fedsupport/fedsupport_parse_reconciliation.md`.
- **Spine ground truth (two-number receipt, RH clause-(c)):** institution-match rate (resolved UNITIDs / FedSupport institution count) AND dollar-match rate (matched obligations / $48,961,658K). The two numbers diverge when the unmatched tail is many small institutions (high institution-miss, low dollar-miss) vs. a few large ones (the dangerous case). Report → `validation/reports/fedsupport/identity_spine_match_rate.md`. Threshold = **deferred, default Path B** (§5).
- **MANDATORY — the receipt NARRATES the divergence (locked 2026-05-29).** The receipt is not just the two numbers; it is the numbers **plus the read**. It must publish both rates AND explain why they diverge: the matched set is dollar-heavy (the big public systems), the unmatched tail is small-institution / low-dollar. This is the clause-(c) honesty layer for this dataset — without the narration, a cold reader sees "47% institutions matched" and misreads a working spine (60%+ of the dollar mass) as half-broken. The spike confirmed the divergence runs in the *safe* direction (matched = dollar-heavy); the receipt must say so explicitly. Non-optional MVP deliverable.
- **No deposit ships without both receipts** (§5 deposit-quality bar). The MVP produces both; the resolved threshold/tail-disposition is the production-scope addition.

---

## 10. 2 a.m. risk (one sentence)

The silent pager is **spine drift**: NSF revises an abbreviation or IPEDS reassigns a UNITID between vintages, a normalized match flips to a different institution, and the funding-IN ↔ expenditure-OUT join misattributes dollars with no error thrown — caught only by the two-number match-rate receipt regressing, which is why the receipt is an MVP artifact, not a production afterthought.

---

## 11. Recommendation — name-match de-risking spike (AUTHORIZED, first execution step)

**Spike-then-MVP.** The only genuinely-unknown piece is the NSF-abbreviation normalizer's match yield — everything else is pattern-reuse or a known-cost manual tail. Before committing the full 16-half-day MVP, run a **bounded spike** to size the ~2× number:

> **`etl/spikes/spike_fedsupport_name_match.py`** — budget **3 half-days, kill at 3.** Take the parsed FY2023 institution name+state set (≈1,110 rows; re-fetch FY2023 Table 12 per HD 3.1 §7 URL + SHA, or reuse the gitignored gate scratch), run a first-pass normalizer + exact/normalized match against the era-B HERD UNITID set, and **report the raw normalized-match NUMBER before any manual resolution.**

**Two principal-ratified additions (2026-05-29):**

1. **Report the raw normalized-match NUMBER, not just pass/fail against the 60% gate.** The number *sizes the MVP*: 60% is a **floor-to-proceed** (a 40% manual tail = the ~2× budget assumption), **not a ship target**. How far above 60% the raw yield lands directly determines the manual-resolution effort, so the MVP manual-tail scope (the 3.0-half-day artifact-#5 core) is sized to the *actual* yield, not to a fixed assumption.
2. **Explicitly test the city-disambiguator edge (hidden edge §8.2).** Confirm that multi-campus / city-suffixed institutions (e.g. `U. Alabama, The, Birmingham` vs. `…, Tuscaloosa`) resolve to **DISTINCT UNITIDs**, not silent-merged. Silent UNITID merges are the failure mode that **survives validation if match-rate is computed at the wrong grain** — the most dangerous of the three catches. The spike must surface any collapse before MVP commits.

**Spike discipline (mirror HD 3.1):** point at the one number (raw match yield), test the city-disambiguator, stop at the finding, report. Throwaway code (does not promote); findings → `validation/reports/fedsupport/`.

**Kill / branch conditions (AS RUN — note the mis-specification, corrected below):**
- **Kill at 3 half-days** regardless of completeness. *(Held — spike came in within budget.)*
- ~~**Raw normalized match < ~60%** → surface to Vision.~~ **MIS-SPECIFIED on two dimensions (see correction).**
- ~~**Raw normalized match ≥ ~60%** → MVP greenlights.~~

### §11 kill-metric correction (RATIFIED 2026-05-29 — pin BOTH dimensions)

The spike's kill metric was mis-specified on **two** dimensions at once, and the corrected floor pins both so it cannot be misread on either again:

1. **Wrong AXIS.** It measured the *institution*-match rate, but §9 and the §4 two-number receipt establish the **dollar-match rate** as the thread-critical axis (the funding-IN ↔ expenditure-OUT picture is about dollars, not institution counts).
2. **Wrong PASS.** It measured the *raw first-pass* yield, but the relevant signal is the yield *after the mechanical normalization + assisted-match layers* (the cheap, no-manual-budget layers the ~2× explicitly funds first).

**Corrected floor-to-proceed (locked):** the floor is the **dollar-match rate, measured after the mechanical normalization + assisted-match layers** (the "second-pass" equivalent), NOT the raw first-pass institution rate. The next survey's gate measures against the axis and pass its own scope-doc declares thread-critical.

**The reflex is kept.** The conservative *surface-to-Vision* reflex on a sub-floor reading is preserved deliberately. The asymmetry favors it: an unnecessary surface costs half-days; a missed one costs a wrong build. **Worth naming: the gate worked DESPITE the mis-specification, not because of it** — the surface-to-Vision reflex caught a *passing* result (60.3% dollars, post-mechanical) that a literal mis-specified threshold (35% raw institutions) might have killed outright. The correction makes the next gate measure the right thing; it does not weaken the reflex.

### Spike result (2026-05-29 — ACCEPTED)

- **Raw first pass:** 389/1,111 = 35.0% institutions; 32.4% dollars *(the figure that fired the mis-specified branch)*.
- **Mechanical second pass** (`of`-insertion + token-set head, city token kept; no manual resolution): 527/1,111 = 47.4% institutions; **$29.54B / $48.96B = 60.3% dollars** — clears the corrected floor before manual budget is spent.
- **City-disambiguator (§8.2, most dangerous catch): CLEAN.** 36 same-name-different-city groups, zero silent merges; distinct UNITIDs confirmed. 2 token-set collision-hazard keys = small enumerable watch-list (resolved by the city token), carried to the forward kill condition.
- Parse clean: 1,111 institution rows, grand total reconciles exactly to the $48,961,658K anchor.
- **Verdict: PROCEED** (Skipper engineering read + Vision worth-vs-cost call concur). MVP greenlit, sized to the second-pass baseline; the `of`-rule promoted into the MVP normalizer, city token kept first-class.

### Forward kill condition (Vision's, confirmed — watches the MVP manual tail)

- **PRIMARY:** reopen if the **dollar-match rate has not cleared ~80% by the end of the 3.0-half-day manual-resolution core** (artifact #5) — the tail is not converging at the rate the ~2× budget assumes, trending toward a ~4× signal.
- **SECONDARY:** reopen if the 2 token-set collision-hazard keys prove to be the visible edge of a **systematic same-name collision class** rather than a small enumerable watch-list — the city-token disambiguator would then be insufficient and the spine's validation surface larger than scoped.
- Both **surface to Vision.**

**Hold (per §5):** the 8→6 vol-71 taxonomy crosswalk, the HERD-crosswalk path-move, and the obligation-vs-expenditure seam decomposition (HD 3.6) stay deferred. The era-extension, methods-note, and separate Zenodo deposit are gated behind a working spine + receipt. MVP surfaces before any deposit/release work.

---

**Files referenced (all relative to repo root):**
- `validation/reports/fedsupport/hd_3_1_acquisition_gate_findings.md`
- `etl/spikes/spike_fedsupport_acquisition_probe.py`
- `etl/_load.py`
- `data/raw/MANIFEST.md`
- `docs/hd_2_1_scoping.md`
- `CLAUDE.md` (§3 acquisition lock, §4 spine addendum, §10 subtree structure, §1 analytical thread / HD 3.6 seam)
