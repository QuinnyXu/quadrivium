# HERD Financial Panel — ETL Scoping (HD 2.4)

> **LOCKED 2026-05-09.** This document is the locked implementation contract for HD 2.4. Propagation ordering greenlit by maintainer 2026-05-09 and locked into `crosswalks/era_b_reconstruction_rule.yaml` alongside the existing `federal + nonfederal = all_source` rule. Implementation (HD 2.4.a onward) starts in the next personal deep-block session.

**Status:** **LOCKED 2026-05-09.** Implementation contract for HD 2.4. No implementation begun yet.
**Authored:** 2026-05-09 (HD 2.4 scoping pass; revised W4 round 2026-05-09 applying maintainer dispositions on items 1–9 plus four NULL greenlights; final lock round 2026-05-09 applying propagation-ordering greenlight + semantic-clarification confirmation + Stage 9 sanity assertion).
**Author:** Skipper.
**Locks gated by this document:** `etl/build_herd_panel.py`, `etl/spikes/panel_anchor_verify.py`, the DST verification-grid scope (locked Branch A this round), the timing of the Q14 era-boundary spike (locked Option 2 this round), and the `quality_flag` propagation ordering (locked into `crosswalks/era_b_reconstruction_rule.yaml` 2026-05-09).
**No maintainer greenlights pending.** This document is the implementation contract for HD 2.4. Drift between this document, the `era_b_reconstruction_rule.yaml` propagation clause, and the build-script behavior is a CI/test concern, not a re-review concern.

---

## 0. What this document is

The methodology is locked. `docs/methods_notes/reconstructive_harmonization.md` carries the era-A direct read, the era-B reconstruction rule (Q9 + Q11, `column='Total'`), and the four-driver decomposition of the 2010 boundary. The crosswalks are locked: `crosswalks/question_map.csv` (37 rows, including raw-label drift entries), `crosswalks/discipline_coarse.csv` (18 rows), `crosswalks/discipline_fine.csv` (96 rows), `crosswalks/era_b_reconstruction_rule.yaml`. The personnel sibling shipped 2026-05-02 — `data/harmonized/herd_personnel.parquet`, ~14,859 rows, 6-cell Table 26 verification, FY-2023-anchored standard-form filter back-applied as the documented divergence story.

What is missing is the build that turns locked methodology into the 1975–2024 financial parquet (with FY 1972 / 1973 / 1974 carved out per §3(a); raw zips preserved as deposit artifacts). This document scopes that build: how the schema looks, which rows enter the panel, how era-A direct and era-B reconstructed rows assemble, what verification grid backs the deposit, what code structure the build script adopts, and where the discipline boundaries fall between HD 2.4 and adjacent tasks (HD 2.5 deflation, HD 2.7 standard-form reconciliation).

The output of this scoping pass is a locked plan, not code. Implementation runs in follow-up sessions after maintainer greenlight.

---

## 1. Schema (Q1)

The financial panel mirrors the personnel sibling's spirit (long format, institution identifiers, year, era, source-of-truth provenance columns) and diverges where the value axis demands it. The schema is **21 columns** (19 base + `form_type` from §9.1 + `quality_flag` from W4 NULL-handling lock); the column order is locked at deposit time. *(Tally fix 2026-05-10: prior text said "20 columns (18 base + ...)"; the column enumeration below has always been the source of truth and remains unchanged. The base-column count was 19 not 18 — the original tally drifted by one. No schema change; documentation count corrected.)*

```
institution_id              VARCHAR  (era-B inst_id; era-A fice copy)
fice                        VARCHAR  (era-A only; NULL in era-B)
ncses_inst_id               VARCHAR  (era-B only)
ipeds_unitid                VARCHAR  (era-B only)
inst_name_long              VARCHAR  (cold-reader convenience)
year                        INTEGER  (1975–2024; 1972/1973/1974 carved per §3(a))
era                         VARCHAR  ('A' or 'B')
discipline_coarse           VARCHAR  (18 buckets per `discipline_coarse.csv`; nullable)
discipline_fine             VARCHAR  (96 leaves per `discipline_fine.csv`; nullable)
expenditure_type            VARCHAR  ('r&d' or 'r&d_equipment')
source_class                VARCHAR  ('all_source','federal','nonfederal')
form_type                   VARCHAR  ('standard' or 'short')
value                       DOUBLE   (USD, current-year, thousands)
unit                        VARCHAR  ('kUSD_current')
value_type                  VARCHAR  ('current'; reserved for HD 2.5 'constant')
quality_flag                VARCHAR  ('reported','imputed','estimated','unspecified_zero')
source_questionnaire_no     VARCHAR  ('1','2','3','9','11','14',...)
source_question_canonical   VARCHAR  (FY 2024 Guide canonical label)
source_question_raw         VARCHAR  (HERD CSV raw label)
source_file                 VARCHAR  (e.g., 'herd2024.csv')
notes                       VARCHAR  (nullable; per-row caveats)
```

The value-axis block (`value, unit, value_type, quality_flag`) is contiguous by design — a consumer scanning the schema reads the value, its unit, its current-vs-constant disposition, and its quality provenance as a unit. `form_type` sits between `source_class` and `value` so the reconciliation-population filter columns (form_type, source_class) are readable as the population-and-decomposition pair before the value columns begin.

### `quality_flag` value semantics (W4 NULL-handling lock)

- **`reported`** — raw `status` column blank in the source HERD CSV. The institution's own numeric statement, no NSF intervention. Dominant case (~93–97% of in-scope Total-column rows per `validation/reports/herd_null_characterization_findings.md`).
- **`imputed`** — raw `status='i'` in the source HERD CSV. NSF-imputed value, FY24 Guide page 10 documents the code. ~3% of FY 2024 in-scope rows.
- **`estimated`** — raw `status='e'` (case-folded from `'E'` in pre-1990 era-A files per §3(a) Category I lock 2026-05-10), era-A only, FY24 Guide page 25 documents the code. Effectively retired (1 occurrence in entire FY 2008 file, 0 at column='Total' in scope); preserved in the schema for fidelity across 1975–2009 (FY 1973–1974 carved per §3(a)).
- **`unspecified_zero`** — raw `status='u'` (case-folded via `UPPER(status)='U'` per HD 2.4.b round 1 case-fold lock). **The FY24 Guide documents `'u'` as a valid status code; the empirical scope of its emission across era-B 2010–2022 (~4,000 rows, 106 institutions, retired FY 2023+) is documented in this deposit's quality-flag characterization** (`validation/reports/herd_null_characterization_findings.md` §7, locked 2026-05-10 PM). The panel-emitting subset — rows surviving Stage 5's `column='Total'` filter — is 9 rows at FY 2020 Q14 / institution `'003446'` (South Carolina State University; HBCU). Era-A does not emit `status='u'` (verified across 1973–2009 at `etl/spikes/probe_status_c_codeset.py`); era-B 2010–2022 emits it as a routine NCSES code; FY 2023+ retires it. Row-absence at the (institution, year, discipline_fine, source_class) leaf grain is handled by the era-B reconstruction's COALESCE-to-zero arithmetic and does **not** propagate `unspecified_zero` onto reconstructed rows — that separation is load-bearing (row-absence is the institution's documented-zero statement per the Guide pages 8/23, not data degradation). See §6.2 Stage 6 for the propagation rule and §6.2 Stage 9 for the three-tier corrected drift-defense assertion.

**Initial baseline revised 2026-05-10 PM.** The W4 NULL-handling lock's original "FY-2017-only / non-Total-only" empirical baseline (locked 2026-05-09 from the three-spot-year characterization at FY 2008 / 2017 / 2024) was a sampling artifact, not data behavior. HD 2.4.b round 1 surfaced 9 panel-emitting rows violating both clauses; HD 2.4.d ran a full era-B re-characterization probe (`etl/spikes/probe_era_b_status_u_full.py`); Vision consultation 2026-05-10 PM locked the disposition (Option δ + γ-allow). The corrected baseline is summarized above; the audit-trail-preserved validation report carries both states. The sampling-methodology lesson (three-spot-year sampling insufficient for cross-temporal NCSES encoding patterns) is recorded as a process seed candidate at `seeds/research-seeds.md` Part 2 and as a locked-decisions entry at `PANEL_SKIPPER.md` §8.

The four sub-questions answered:

### 1(a) `source_class` as a single column with values `{federal, nonfederal, all_source}`

Locked at single-column long format. The era-A direct read produces one row per (institution, year, discipline_fine) at `source_class='all_source'`, sourced from era-A's `Expenditures by S&E field` `column='Total'`. Era-B reconstruction produces three rows per (institution, year, discipline_fine):

- one `source_class='federal'` row, value = `Q9.column='Total'`,
- one `source_class='nonfederal'` row, value = `Q11.column='Total'`,
- one `source_class='all_source'` row, value = `Q9.Total + Q11.Total` (the era-B reconstruction rule).

Rationale: long format preserves the era-B fragmentation explicitly while still publishing the reconstructed `all_source` row that anchors cross-era analysis. A consumer who wants only the all-source series filters `source_class='all_source'`; a consumer who wants the federal/nonfederal decomposition reads the parallel rows. Three-column-wide format would force era A to carry NULLs in the federal/nonfederal columns and would obscure that era-B's `all_source` row is *reconstructed* rather than read directly. The long-format choice mirrors the personnel sibling's `measure_type` approach and keeps the schema cold-reader-friendly.

### 1(b) `expenditure_type` as a single column with values `{r&d, r&d_equipment}`

Locked at single-column long format. Era-A's `Current fund research equipment expenditures by field` (Item 3, 1981–2009) and era-B's Q14 (`Capitalized R&D equipment expenditures by field`, 2010–2024) ship as `expenditure_type='r&d_equipment'` rows alongside the main `expenditure_type='r&d'` series. Equipment rows ship at `source_class='all_source'` only — neither era's equipment question carries a federal/nonfederal split at the field-level grain, and Q14 is by FY 2024 Guide construction "the portion of their federal and nonfederal R&D expenditures... that went toward the purchase of capitalized R&D equipment." A consumer who wants only the main R&D series filters `expenditure_type='r&d'`; the equipment series rides parallel.

The era-A `expenditure_type='r&d_equipment'` rows are *direct reads* from era-A Item 3; the era-B equivalent rows are *direct reads* from Q14. They are not summed or reconstructed across questions. Whether era-A Item 3 and era-B Q14 align as a continuous equipment series is the open question (Q6 below) — schema does not depend on the answer either way.

### 1(c) Q4 / Q5 carve-outs as institution-year attributes, separate sibling table — **CONFIRMED (W4 round, item 3)**

Q4 (`Medical school R&D expenditures`) and Q5 (`Clinical trial R&D expenditures`) are carve-outs from the institution-year R&D total per CLAUDE.md §6 disposition W2. Including them as separate rows in the field-level panel would invite mis-summation. The sibling attribute table — `data/harmonized/herd_panel_attributes.parquet`, shipping alongside the main panel as a separate artifact — is **confirmed by the maintainer in the W4 review round**:

```
data/harmonized/herd_panel_attributes.parquet
  institution_id              VARCHAR
  year                        INTEGER
  era                         VARCHAR
  med_school_share            DOUBLE  (fraction of institution-year R&D, 0..1)
  clinical_trials_share       DOUBLE  (fraction of institution-year R&D, 0..1)
  med_school_value            DOUBLE  (kUSD_current; raw Q4 value)
  clinical_trials_value       DOUBLE  (kUSD_current; raw Q5 value)
  source_file                 VARCHAR
  notes                       VARCHAR
```

Rationale: keeping the carve-outs out of `herd_panel.parquet`'s row body protects against accidental SUM-over-everything queries that double-count. The sibling parquet is small (~13K rows: ~900 institutions × 15 years × 1 row per institution-year). Era-A side: `era='A'` rows carry NULL for both attributes (Q4/Q5 are era-B-only questions). The HD 2.1.b residual analysis already uses Q5 share at institution-year grain (Diagnostic 2); the attribute table makes that join trivial for downstream consumers.

Alternative considered and rejected: inline `med_school_share` and `clinical_trials_share` columns on the main `herd_panel.parquet` rows. Rejected because (1) the share is institution-year-level, not (institution, year, discipline)-level, so it would replicate across every discipline row and invite confusion; (2) it bloats the row body for an attribute that few queries need.

### 1(d) `value_type` column added now (forward-proofing for HD 2.5)

Locked at *yes, add the column now* with the constant `'current'` for HD 2.4. HD 2.5 deflation work will produce a parallel series at `value_type='constant'` (BEA GDP price index for R&D applied) and will write to the same parquet (or a deflated sibling). Carrying the column at HD 2.4 means HD 2.5 is a row-add, not a schema migration. The cost is one extra column with a constant value at deposit time; the benefit is the contract is set.

The personnel sibling does not carry `value_type` because headcount/FTE are not deflatable. The financial panel inherits `value_type` from the original CLAUDE.md §6 schema specification.

---

## 2. Validation anchor (Q2) — **DST Branch A LOCKED (W4 round, item 1)**

The personnel sibling reconciled against NCSES Data Table 26 (NSF 26-304), a single PDF with five years of standard-form-population totals. The financial-side analog is **HERD Detailed Statistical Tables (DST)** — the published companion volume to each year's HERD release.

### 2(a) DST scope — verified by maintainer 2026-05-09

Maintainer verified DST scope on the NSF NCSES website during the W4 review round. DST publishes:

- Expenditures by **broad and detailed discipline**.
- **Per-institution per-discipline per-funding-source** detail.
- Broken out by **fiscal year**.

This is richer than the original Branch A scoping anticipated (which posited national-level per-discipline totals). The verification can be cell-precise at the institution × year × discipline × source-class grain.

### 2(b) FY 2024 era-B-internal cohort-anchored verification grid — locked

Locked grid scope (re-anchored 2026-05-21 to the Branch III two-row shape per Vision Q3; full rationale at the §13 re-shape lock entry):

- **Cohort:** top-10-by-FY-2008-R&D (the same cohort established at HD 2.1.b for `validation/reports/era_reconciliation_2008_2011.md`; preserves cohort continuity across the residual-test and the panel-anchor verifications).
- **Disciplines:** 3 representative coarse buckets — **Engineering** (anchor; the program's discipline of focus per CLAUDE.md §1) plus **Life sciences** and **Physical sciences** (two contrastive buckets that exercise different funding-source mixes — Life sciences is HHS/NIH-dominated, Physical sciences is more NSF/DOE-distributed; together they sample the federal-agency-mix axis the era-B Q9 fragmentation puts at risk).
- **Source-class views:** `federal`, `nonfederal` per spot year. Optional `all_source` cells run as a reconciliation check against the era-B reconstruction rule (`Q9.Total + Q11.Total` should equal DST's all-source per-discipline total at the standard-form-population subset).

**Anchor table (locked 2026-05-21).** The Branch A verification surface contracts to two anchors: the FY 2024 Table Builder CSV snapshot (the era-B-internal cohort-anchored verification grid proper) and the HD 2.1.b residual report (the cross-era verification surface, inherited from the residual-gate work). Each carries an independent reconstruction-rule check at a different grain:

| Anchor row | Anchor surface | Scope | Verification at HD 2.4.g |
|---|---|---|---|
| FY 2024 era-B-internal cohort-anchored verification grid | `data/reference/dst-table-builder/dst-table-builder-FY2024.csv` Table Builder CSV snapshot (per §2(d.2); SHA-256 `e0fc1f7b…6738a6`; paired YAML sidecar at `data/reference/dst-table-builder-FY2024-query.yaml`) | 10 institutions × 3 disciplines × 2 source classes = **60 cells nominal; 58 substantive** per the FY 2024 export staged 2026-05-21. UCSF Engineering structurally absent (health-sciences-only institution, no Engineering school; UC system Engineering R&D lives at Berkeley, San Diego, Los Angeles, Irvine, and Davis — not San Francisco). The cell absence is structural at the institution-substrate level, not suppression or NCSES disclosure-rule artifact. Path A disposition: accept the 58-cell substantive grid as the FY 2024 anchor; document the structural absence honestly. The grid verifies the era-B reconstruction rule (`Q9.Total + Q11.Total` reconstructs DST all-source per-discipline cells at the standard-form-population subset) at FY 2024, era-B-internal. | consume staged CSV directly |
| Cross-era verification | `validation/reports/era_reconciliation_2008_2011.md` (HD 2.1.b residual report; locked 2026-05-01) | Top-10-by-FY-2008-R&D cohort × 7 coarse buckets × year-pairs 2009→2010 (adjacent) and 2008→2011 (long-gap). Full residual-gate verdict (REOPEN at HD 2.1.b §3.3) plus three diagnostics (institution-total grain, Q5 clinical-trials share, national-pool growth + cohort expansion). The verification surface is the four-driver decomposition characterizing the 2010 era boundary (real growth, definitional change, cohort expansion, bounded unmeasurable residual) — the cross-era verification *is* the boundary characterization per the methods-note §2 / Appendix D–G receipts. | inherited from HD 2.1.b; HD 2.4.g consumes the existing report rather than re-running the residual gate |

The two-row contraction is the re-shape pass disposition (Vision Q1 Branch III, 2026-05-21): the FY 2024 grid is era-B-internal cohort-anchored verification of the reconstruction rule against an external static-anchor surface (the Table Builder CSV snapshot); the cross-era verification is the HD 2.1.b boundary characterization, which already exists as a deposit-grade artifact. Two independent verification surfaces at two distinct grains anchor the deposit; multiplying spot-year anchors across the FY 2017 / FY 2010 / FY 2008 vintages does not earn its complexity at the current verification-anchor scope. Receipt-level FY 2017 / FY 2010 / FY 2008 caveats live in the caveat block below.

**§2(b) caveat block — historical-vintage anchors deferred (locked 2026-05-21).**

Prior versions of this section carried FY 2017, FY 2010, and FY 2008 as additional spot-year anchor rows on the per-spot-year anchor table, with the verification posture "Static PDF if available on NCSES historical-publications archive; else Table Builder CSV snapshot." The re-shape pass (2026-05-21) moved these three vintages out of the locked anchor table on the Branch III disposition: at the current verification-anchor scope, FY 2024 era-B-internal verification (anchor row 1) plus HD 2.1.b cross-era boundary characterization (anchor row 2) together discharge the era-B reconstruction-rule and era-boundary-discontinuity verification responsibilities the deposit owes a cold reader. Materializing FY 2017 / FY 2010 / FY 2008 Table Builder snapshots adds spot-year residual cells against the same era-B reconstruction rule across an unverified historical-vintage publication-regime axis, without adding a verification surface the existing two-row anchor table doesn't already discharge.

The FY 2017 / FY 2010 / FY 2008 vintages remain in scope for future expansion if any of the following triggers fires:

- **HD 2.4.i NCSES historical-publications hunt produces a credible static-PDF anchor at the 3-D matrix at cohort grain** for any of the three vintages (institution × discipline × source-class at top-10-cohort grain, parallel to the FY 2024 grid surface). A credible static-PDF surface for any vintage flips that vintage's anchor surface from "deferred per Branch III" to "static-PDF anchor active" and re-engages the per-spot-year anchor-source table for that row.
- **A Q2 surface produces the same** — e.g., a Q2 NSF linkage piece or a Q2 piece using HERD historical data surfaces a published 3-D matrix at cohort grain at a historical vintage that the FY 2024 anchor doesn't already cover.
- **A journal reviewer at the Q2 / Q3 publication arc cites verification scope as defect** — i.e., reviewer comment on a Q2 or Q3 piece claims the deposit's verification surface is insufficient and names historical-vintage cohort-grain anchors as the missing element. Reviewer cover is a documented external trigger; in that case, the affected vintages get full anchor staging per the seven-item §2(d.2) discipline, and the per-spot-year anchor-source table re-expands.

Until one of the three triggers fires, the historical-vintage anchors remain deferred and the two-row anchor table above is the locked Branch A verification surface.

Reserved sidecar paths (`data/reference/dst-table-builder-FY2017-query.yaml`, `…-FY2010-query.yaml`, `…-FY2008-query.yaml`) and the template at `data/reference/dst-table-builder-FY{YEAR}-query.yaml.template` remain on disk as scaffolding ready to materialize if a trigger engages. `data/reference/MANIFEST.md` and `docs/source_documents/citations.md` preserve the "Reserved" subsection rows for the same reason.

Spot-year rationale (preserved from original scoping):

- **FY 2008** anchors the era-A direct read at the residual-test long-gap baseline (cohort-year continuity with HD 2.1.b).
- **FY 2010** anchors the era-B reconstruction's first year and tests the `Q9 + Q11` rule's national reproduction at the standard-form-population subset.
- **FY 2017** anchors the FY 2016 field revisions and the FY 2017 leaf additions (`Engineering, industrial and manufacturing`; `Life sciences, natural resources and conservation`; `Physical sciences, materials science`; `Social sciences, anthropology` per `docs/hd_2_1_open_items.md`).
- **FY 2024** anchors the most recent year and the FY 2024 Q9/Q11 spelling consolidation (Q9-form-only) per the open-items doc.

**Cell pass criteria:** parquet free-sum of the standard-form-population subset (filtered at the parquet side per DST's published criterion) against the anchor's published value (PDF cell or Table Builder CSV cell, per the per-spot-year anchor source above), within rounding tolerance. Sign-consistent divergences with structural explanation (e.g., the personnel-sibling FY-2023-anchored filter pattern) document as divergence, not as build-blocker.

### 2(c) Branch B — institution-total fallback (NOT APPLICABLE per W4 lock)

~~If DST does not disaggregate national totals by discipline, the verification grid is institution-total only...~~

**Branch B is marked not applicable per maintainer verification 2026-05-09.** The maintainer-verified DST scope (per-institution per-discipline per-funding-source per-year) supports Branch A's full grid. Branch B (B1 institution × year totals; B2 national-pool totals only) was the contingency for a weaker DST publication regime; the actual DST publication is richer than the contingency anticipated, so the contingency does not engage.

### 2(d) Sub-actions added at HD 2.4.a — anchor staging

HD 2.4.a Round 1 surfaced that NCSES reduced the FY 2024 DST publication regime from 86 PDFs to 55 and pushed Tables 28–54 (engineering subfield rankings, agency-specific rankings) to the NSF NCSES Table Builder interactive tool — Table-Builder-only, no static PDF. The full institution × discipline × source-class matrix the §2(b) Branch A grid anchors on does not exist as a single FY 2024 PDF. The original §2(d) "stage all DST PDFs" plan needs splitting: some anchor cells come from static PDFs (where NSF still publishes them), other anchor cells come from Table Builder CSV snapshots staged with discipline. §2(d) is split into §2(d.1) and §2(d.2) accordingly.

#### 2(d.1) Static-PDF anchors

PDFs to be staged at HD 2.4.a where the publication regime supports them. The FY 2024 DST publication is the canonical format reference; historical DSTs (FY 2008 / FY 2010 / FY 2017) ship as PDFs only where available, with regime-stability verification deferred to the HD 2.4.g entry sub-action (see §13).

Staged in HD 2.4.a Round 1 (already landed; SHA-256s in `data/raw/MANIFEST.md`, citations in `docs/source_documents/citations.md` with access dates):

- **`data/reference/nsf26304.pdf`** — FY 2024 full DST report.
- **`data/reference/nsf26304-tab010.pdf`** — Table 10 (R&D expenditures by R&D field and source of funds: FY 2024).
- **`data/reference/nsf26304-tab011.pdf`** — Table 11 (Federally financed R&D expenditures by federal agency and R&D field: FY 2024).
- **`data/reference/nsf26304-tab015.pdf`** — Table 15 (R&D expenditures ranked by all R&D, by R&D field: FY 2024).

Tables 10 / 11 / 15 are the FY 2024 anchors that survive in PDF form. Tables 28–54 (institution × engineering subfield × source-class; institution × agency × field) do not exist as FY 2024 PDFs and are anchored via §2(d.2).

**Historical staging (HD 2.4.g entry sub-action).** FY 2008 / FY 2010 / FY 2017 DST publications staged at HD 2.4.g entry when historical regime stability is verified. If a given historical vintage is unavailable as a PDF (some NSF historical publications are tabular-only) or its publication regime contracted prior to FY 2024 in a way that changes the anchor surface, the spot-year contracts to the cells the available DSTs publish or the §2(d.2) Table Builder CSV snapshot path applies. Per Vision's caveat, this is not assumed; it is verified.

Staging discipline mirrors the personnel sibling's `data/reference/nsf26304-tab026.pdf` pattern: PDFs landed under `data/reference/`, named per the actual NCSES filename, with citation entries (URL, access date) in `docs/source_documents/citations.md`.

#### 2(d.2) Table Builder CSV snapshots — locked staging procedure

Where the publication regime does not support a static-PDF anchor — currently FY 2024 Tables 28–54, potentially the analogous historical-vintage cells subject to HD 2.4.g entry verification — the anchor is a **Table Builder CSV snapshot** staged with the seven-item discipline below. The CSV snapshot is the canonical anchor for the deposit's reproducibility contract; if the live NSF Table Builder tool's behavior diverges from the snapshot, the snapshot remains canonical.

**Seven-item staging discipline (locked 2026-05-10):**

1. **Access date** — recorded explicitly in `docs/source_documents/citations.md` for the staged CSV. The Table Builder is a live tool; the access date pins the cell values to the regime in effect at staging time.
2. **SHA-256** — staged CSV gets a SHA-256 entry in the audit trail (`data/raw/MANIFEST.md` if the existing MANIFEST is the audit trail, or a parallel `data/reference/MANIFEST.md` if the existing convention does not extend to `data/reference/` — verify at HD 2.4.g implementation).
3. **Cold-reader instruction** — the methods note carries a short reproducibility paragraph (see `docs/methods_notes/reconstructive_harmonization.md` §6 regime-change paragraph) telling a cold reader (a) consume the staged CSV directly as the deposit's reproducibility contract, and (b) optionally re-query the Table Builder with the staged YAML query parameters and reconcile against the snapshot if the live tool still persists.
4. **Query-parameter YAML sidecar** — every staged Table Builder CSV ships with a sibling YAML at `data/reference/dst-table-builder-FY{year}-query.yaml` capturing the exact query parameters used to produce the snapshot. The sidecar mirrors the documentation discipline of `crosswalks/era_b_reconstruction_rule.yaml`. Schema/template (the YAML's contents) is documented here; the actual sidecar files are NOT created at HD 2.4.a — they land at HD 2.4.g when the Table Builder queries actually run.

   **YAML schema/template (locked 2026-05-10):**

   ```yaml
   # Table Builder Query Parameter Sidecar
   #
   # Captures the exact NSF NCSES Table Builder query parameters that
   # produced the paired CSV snapshot. The CSV snapshot is the deposit's
   # canonical reproducibility anchor; this YAML captures the query so a
   # cold reader can (optionally) re-query the live Table Builder and
   # reconcile against the snapshot while the NSF tool persists.
   #
   # Drift between the live tool and the snapshot is anticipated; the
   # snapshot remains canonical per the methods-note tool-interface-stability
   # disclaimer.

   sidecar_id: dst-table-builder-FY{year}-query
   sidecar_name: "DST Table Builder query for FY {year} institution × discipline × source-class anchor"
   authored_at: "{HD 2.4.g run date}"
   authored_by: "Skipper (HD 2.4.g)"

   csv_snapshot:
     path: "data/reference/dst-table-builder-FY{year}.csv"
     sha256: "{SHA-256 of the staged CSV}"
     access_date: "{YYYY-MM-DD}"

   tool_source:
     name: "NSF NCSES Table Builder"
     url: "{canonical Table Builder URL at access date}"

   query_parameters:
     dataset: "HERD"
     fiscal_year: {year}
     institutions: [<list of NSF inst_ids selected>]
     disciplines: [<list of discipline_fine values selected>]
     source_class_breakdown: [federal, nonfederal, all_source]   # or per-cell selection
     additional_filters: {}                                       # e.g., medical-school-only, standard-form-only
     output_format: csv

   regime_provenance:
     publication_regime_at_access: "{e.g., FY 2024 DST contracted from 86 PDFs to 55; Tables 28–54 Table-Builder-only}"
     anchor_classification: "Table-Builder-only" | "PDF-available-but-CSV-canonical-for-this-grid"
     pdf_alternative_available: false | true
     pdf_alternative_path: "{if applicable}"
   ```

   The schema is the lock; the per-year sidecar files materialize at HD 2.4.g.
5. **Tool-interface stability disclaimer** — methods-note language: *"The Table Builder CSV snapshot is the canonical anchor for this verification. NSF may evolve the Table Builder interface; if the live tool's behavior diverges from the snapshot, the snapshot remains the deposit's reproducibility contract."* Lands in `docs/methods_notes/reconstructive_harmonization.md` §6 regime-change paragraph; cross-referenced from the verification report (`validation/reports/panel_anchor_reconciliation.md`) authored at HD 2.4.h.
6. **Two-tier re-verification path:**
   - **Tier (a)** — consume the staged CSV directly. Always works; frozen at staging time. This is the deposit's reproducibility contract.
   - **Tier (b)** — re-query Table Builder using the staged YAML's query parameters and reconcile against the snapshot. Works while the NSF Table Builder persists at the URL captured in the YAML; verifies the live tool against the snapshot. Failure of Tier (b) (snapshot-vs-live divergence, or tool sunset) does not break the deposit — Tier (a) is the contract; Tier (b) is the cross-check.
7. **Cross-reference** — the methods-note reproducibility section (where the regime-change paragraph lives — see `docs/methods_notes/reconstructive_harmonization.md` §6) points back to this scoping doc §2(d.2) for the mechanism, and §2(e) for the regime-change framing. The sidecar YAMLs cross-reference the methods note.

The verification spike is `etl/spikes/panel_anchor_verify.py`; the report is `validation/reports/panel_anchor_reconciliation.md`. Both follow the personnel sibling's pattern, with the per-spot-year anchor-source table in §2(b) telling the spike which path (PDF vs. CSV snapshot) to consume per cell.

### 2(e) Publication-regime stability caveat — NEW (locked 2026-05-10)

Operational data publication regimes drift independently of the underlying data. NCSES contracted the FY 2024 HERD DST publication from 86 PDFs to 55 and pushed Tables 28–54 (engineering subfield rankings, agency-specific rankings) to Table-Builder-only at HD 2.4.a Round 1. The data scope was unchanged; the static-anchor architecture wasn't. The verification-anchor selection has to account for **regime stability**, not just data availability — the DST tables that anchored the original §2(b) Branch A grid in PDF form during the scoping pass do not all exist as PDFs in the FY 2024 publication.

The deposit's response is a **hybrid anchor architecture**: static PDFs where the regime supports them (§2(d.1)), Table Builder CSV snapshots where it does not (§2(d.2)), with the per-spot-year anchor source documented per cell (§2(b) anchor-source table). The hybrid is documented as part of the methods note's reproducibility contract — see `docs/methods_notes/reconstructive_harmonization.md` §6 regime-change paragraph for the framing and `seeds/research-seeds.md` Part 1 entry dated 2026-05-10 ("Publication-regime stability as a Reconstructive Harmonization axis") for the seed-level claim that this is a fourth axis of operational-data discontinuity.

**Why this is methods, not apology.** Reconstructive Harmonization clause (a) says reconstruct what each era can support on its own terms (CLAUDE.md §1; methods note §7). Extending clause (a) to the verification-anchor layer says: reconstruct the verification grid against whatever publication regime each spot year supports on its own terms — PDF cells where the publication is in PDF, Table Builder CSV cells where it isn't — with per-cell anchor provenance documented. The regime change is methodologically interesting in its own right, not a defect to apologize for. The seed (`seeds/research-seeds.md` 2026-05-10) tracks it as the fourth axis of operational-data discontinuity alongside taxonomy redesign, encoding pipeline drift, and back-applied universe filters; if the seed graduates at the mid-June quarter-boundary panel review, CLAUDE.md §6 picks up "publication-regime stability" as a named methodological commitment.

**HD 2.4.a Round 2 sub-action (in flight).** Vision's caveat: if the FY 2024 Table Builder query for the institution × discipline × source-class matrix is *not actually exportable as CSV reproducibly by a cold reader using the same query parameters*, Option (b) collapses to (c) and the panel reconvenes. HD 2.4.a Round 2 verifies the export reproducibility before HD 2.4.g entry. Until Round 2 passes, HD 2.4.g does not start.

---

## 3. Era-A coverage (Q3)

### 3(a) 1972 disposition + FY 1973–1974 codeset carve-out (revised 2026-05-10)

**1972 exclusion (original lock).** 1972 carries no `Expenditures by S&E field` question per FY 2024 Guide page 16 §2.1.5; the question first appears in 1973. The 1972 file is preserved in the deposit (raw zip stays in `data/raw/herd/`) but produces zero rows in `herd_panel.parquet`. Rationale: a row at `(year=1972, discipline_fine=NULL, source_class='all_source', value=NULL)` adds no signal and invites confusion — a cold reader filtering by year=1972 sees a NULL row and cannot tell whether the institution didn't report or the question didn't exist. The methods note (`reconstructive_harmonization.md` §6) already documents the 1972 exclusion explicitly; the parquet reflects that. The 1972 institution-year roster is not lost — `data/raw/herd/higher_education_r_and_d_1972.zip` ships in the deposit, and the `etl/_load.py` loader can read it for any consumer who wants to inspect what the 1972 instrument did carry (the `Capital expenditures by area` and `Source` questions per CLAUDE.md §6).

**FY 1973–1974 codeset carve-out (locked 2026-05-10, HD 2.4.b round 1).** HD 2.4.b round 1's first Stage 4 smoke test pass surfaced two empirical findings outside the locked W4 codeset (`validation/reports/era_a_status_codeset_findings.md`): (1) FY 1973–1989 raw files emit status codes in mixed case (`'I'` / `'E'` alongside `'i'` / `'e'`), and (2) FY 1973–1974 emit a Guide-undocumented `status='c'` code on field-level `column='Total'` rows (13 affected cells across the two years; FY 1973: 5 cells, FY 1974: 8 cells; all positive numeric values). FY 1975–2009 carry no Guide-undocumented status codes.

Vision verdict 2026-05-10 locked the dispositions across three categories:

- **Category I — Case-sensitivity.** Mechanical fix: case-fold `UPPER(status) IN ('I','E','U')` in the Stage 3 CASE expression. Preserves the Guide-documented codeset's semantic intent exactly (the codeset specification is semantic, not lexical). No methodological dimension. Methods-note one-liner queued for HD 2.4.i: *"Pre-1990 raw files emit status codes in mixed case; the harmonized panel folds to lowercase."*
- **Category II — Guide-undocumented `'c'` / `'C'` codes.** **Option (a) carve-out.** FY 1973–1974 are excluded from the field-level harmonized panel. Raw zips (`data/raw/herd/higher_education_r_and_d_1973.zip`, `_1974.zip`) preserved as deposit artifacts. Coverage contracts from 52 years (1973–2024) to **50 years (1975–2024)**. Decision rationale parallel to the 1972 exclusion: rows that cannot be filed under the locked `quality_flag` codeset without methodological assumption do not enter the panel; the deposit's W4 NULL-handling lock integrity is preserved.
- **Category III — Pattern recognition.** The `'c'` finding is added as the fifth instance to the publication-regime stability axis in `seeds/research-seeds.md` (2026-05-10 entry), distinguishing it from the four already named because it sits at the **status-code grain rather than the question-structure grain**. No methods-note amendment beyond the carve-out footnote.

**Codeset-extension policy (locked CLAUDE.md §6, HD 2.4.b round 1).** Extensions to the locked four-value codeset require either (a) a Guide-documented semantic anchor, or (b) panel review at quarter-boundary with explicit documented semantic anchor and methods-note disclosure. Empirical surfacing alone is not sufficient grounds; default disposition for empirically-surfaced undocumented codes is exclude + footnote, pending panel review.

**HD 2.4.i absorbs.** Methods-note footnote on the FY 1973–1974 carve-out (parallel voice to the 1972 footnote). NCSES historical-publications documentation hunt (1-half-day budget, non-blocking) — if a documented semantic for `'c'` surfaces, quarter-boundary panel review (mid-June) revisits the disposition. If `'c'` maps cleanly onto an existing enum value, the carve-out becomes unnecessary and FY 1973–1974 enter the panel. If `'c'` is genuinely distinct, the W4 lock extends with reviewer cover.

**Coverage statement.** The **field-level harmonized panel covers 1975–2024 (50 years)**. Three exclusions audit trail:
- 1972: no field-level question (FY24 Guide page 16 §2.1.5).
- 1973–1974: Guide-undocumented `status='c'` code on field-level Total-column rows (HD 2.4.b round 1 / Vision verdict 2026-05-10 Category II option (a)).
- 1972 and 1973–1974 raw zips preserved in `data/raw/herd/` as deposit artifacts.

The build-side enforcement is `PANEL_FIRST_YEAR=1975` in `etl/build_herd_panel.py` plus a defensive `if year < PANEL_FIRST_YEAR: continue` floor inside `build_era_a_rows()` parallel to the existing `if year > ERA_A_LAST_YEAR: continue` ceiling.

### 3(b) 1975–2009 era-A handling (revised 2026-05-10)

Era-A field-level rows ship at `era='A'`, `source_class='all_source'`, `expenditure_type='r&d'` (or `'r&d_equipment'` for Item 3 rows, 1981–2009). The pre-1981 fingerprint variability documented in `docs/hd_2_1_open_items.md` ("Pre-1981 Guide field-list variability") does not affect row-level data — the harvest collapsed pre-1981 to two fingerprints (1973–1978, 1979–1983) and the data files do not reflect the Guide-narrative sub-period distinctions at the row-axis level. ETL treats 1975–1980 like 1981–2009 at the row-data level; the `discipline_fine.csv` crosswalk carries the era-A leaf rows at `year_range_start=1973` (e.g., `Engineering, all`) or `year_range_start=1979` (e.g., the Engineering leaves like `Engineering, aeronautical and astronautical` that first appear at the 1979–1983 fingerprint). The crosswalk's `year_range_start=1973` does not contradict the panel's 1975 start — the crosswalk describes label coverage (the era-A `'Engineering, all'` rollup label exists from 1973 onward), while the panel's coverage describes which years' rows enter the harmonized parquet (1975 onward, FY 1973–1974 carve-out per §3(a)).

ETL emits the era-A rows verbatim from the raw CSV after the discipline-fine crosswalk join. No synthetic 1972/1973/1974 rows; no synthetic per-year completion of leaves that the pre-1981 fingerprint doesn't carry. Pre-1981 fingerprint as observed in the harmonized panel: 1975–1978 emits only `*, all` rollup rows; 1979 onward emits leaves.

### 3(c) Era-A Item 3 equipment series

Era-A `Current fund research equipment expenditures by field` (Item 3, 1981–2009) ships at `expenditure_type='r&d_equipment'`, `source_class='all_source'`, joined on the same `discipline_fine` crosswalk. Coverage: 1981–2009 (29 years). The era-A equipment series alignment with era-B Q14 is the open spike question (Q6).

---

## 4. Q9 / Q11 spelling drift (Q4)

### 4(a) ETL applies `discipline_fine` crosswalk before reconstruction

The locked sequence: raw CSV row → row-label normalization via `discipline_fine.csv` (joins on `raw_row_label`) → era-B reconstruction (Q9 + Q11 sum on the canonical `discipline_fine` value). This protects the reconstruction rule from the seven Q9-vs.-Q11 spelling-drift labels documented in `docs/hd_2_1_open_items.md` ("Era-B Q9 vs. Q11 row-label punctuation/spelling drift 2010–2023") — Q9 carries `Engineering, aerospace, aeronautical, and astronautical` (Oxford comma) and Q11 carries `Engineering, aerospace, aeronautical and astronautical` (no Oxford comma); both crosswalk to the same canonical `discipline_fine='Engineering, aerospace, aeronautical, and astronautical'` (FY 2024 form, Q9 spelling); the reconstruction sum joins on canonical and never sees the raw spelling difference.

### 4(b) Defensive fail-loud assertion

The build script asserts that every raw row label in scope (era-A `Expenditures by S&E field` rows; era-B Q9 and Q11 rows; era-A Item 3 rows; era-B Q14 rows) has a matching crosswalk entry. If any raw row label fails the crosswalk lookup, the build raises `RuntimeError` with the row label, the year, and the question. This is the same loud-log discipline the personnel build uses for `UNKNOWN_personnel_function` (`etl/build_herd_personnel.py` lines 226–234) and parallels the W2 `InstitutionalFacultyAdapter`'s loud-log discipline mentioned in the dispatch.

The crosswalk currently has 96 rows of `discipline_fine` entries. The harvest covers 1973–2024 across all four scoped questions. A genuine new row label appearing in the raw data (e.g., a new FY 2025+ leaf when the deposit refreshes) is treated as a build-stop, not a silent-skip — the operator updates `discipline_fine.csv` first, then re-runs.

### 4(c) Non-S&E rows

Non-S&E (era-A 2003–2009 `Expenditures by non-S&E field`; era-B 2010–2024 Q9/Q11 Non-S&E rollups) ship in the panel but are flagged supporting-only (not gating). The crosswalk handles the era-A non-S&E rows from a separate question, and the era-B Non-S&E rollups from Q9/Q11; both crosswalk to the same `discipline_coarse='Non-S&E'`. Cross-era reconciliation of the Non-S&E series is out of scope for HD 2.4 — the era-A non-S&E question to era-B Non-S&E rows is a different question-mapping problem (`crosswalks/discipline_coarse.csv` row 16). The panel ships the rows; the methods note flags them as supporting cells.

---

## 5. Build / test infrastructure (Q5)

Parallel to the personnel sibling's pattern. Five artifacts:

1. **`etl/build_herd_panel.py`** — main build script. Reads raw zips via `etl/_load.py:read_herd_csv`, joins crosswalks, applies the era-B reconstruction rule, writes `data/harmonized/herd_panel.parquet`. Section 6 below specifies structure.
2. **`etl/spikes/panel_anchor_verify.py`** — DST verification grid. Reads the parquet, computes the spot-year × discipline × source-class grid, prints the verdict to stdout, optionally writes the grid as a fixture. Mirror of `etl/spikes/personnel_table26_verify.py`.
3. **`validation/reports/panel_anchor_reconciliation.md`** — the verification report. Cell-by-cell table, structural argument for any documented divergences, response-rate cross-check if Branch A applies. Mirror of `validation/reports/personnel_table26_reconciliation.md`.
4. **MANIFEST entry.** Add `data/harmonized/herd_panel.parquet` to `data/raw/MANIFEST.md` (or wherever harmonized-artifact SHA-256s land — verify this in the personnel parquet's MANIFEST treatment) with the SHA-256 of the locked build.
5. **README integration.** Update `docs/methods_notes/reconstructive_harmonization.md` §6 ("What the deposit ships") to reference the verification report. The methods note already names the parquet by path; the verification artifact is the new addition.

A sibling attribute parquet (Q4/Q5 carve-outs per §1(c)) ships as item 1.5: `data/harmonized/herd_panel_attributes.parquet`. Its MANIFEST entry pairs with the main panel's.

---

## 6. Build script structure

`etl/build_herd_panel.py`. Outline-level — the function signatures and responsibilities below are the lock; exact SQL and DuckDB syntax come at implementation time. Mirrors `etl/build_herd_personnel.py`'s structure where the parallel holds.

### 6.1 Module constants

- `ERA_A_FIELD_QUESTION = "Expenditures by S&E field"` — era-A direct read source. Question exists in raw HERD files 1973–2009; panel coverage 1975–2009 per the §3(a) carve-out.
- `ERA_A_EQUIPMENT_QUESTION = "Current fund research equipment expenditures by field"` — era-A Item 3, 1981–2009.
- `ERA_B_Q9 = "Federal expenditures by field and agency"` — era-B federal component, 2010–2024.
- `ERA_B_Q11 = "Nonfederal expenditures by field and source"` — era-B nonfederal component, 2010–2024.
- `ERA_B_Q14 = "Capitalized R&D equipment expenditures by field"` — era-B equipment series, 2010–2024 (FY24 Guide canonical).
- `ERA_B_Q14_RAW = "Capitalized equipment expenditures by field and source"` — Q14 raw-vs-canonical drift per crosswalk row 25 (locked at HD 2.4.a Track 2 qno suffix semantics spike, 2026-05-09; same drift pattern as Q5/Q15/Q16).
- `ERA_B_Q4 = "Medical school R&D expenditures"` — Q4 carve-out, attribute table only (FY24 Guide canonical).
- `ERA_B_Q4_RAW = "Medical school expenditures"` — Q4 raw-vs-canonical drift per crosswalk row 15 (locked at HD 2.4.a Track 2; surfaced at HD 2.4.a smoke test and confirmed cross-year stable FY 2017 + FY 2024).
- `ERA_B_Q5_CANONICAL = "Clinical trial R&D expenditures"`, `ERA_B_Q5_RAW = "Clinical trials"` — Q5 raw-vs-canonical drift per crosswalk row 16.
- `ERA_B_IN_SCOPE_QUESTIONS_CANONICAL = (ERA_B_Q4, ERA_B_Q5_CANONICAL, ERA_B_Q9, ERA_B_Q11, ERA_B_Q14)` — the canonical label set Stage 2 expands (canonical + raw) into the in-scope label table for the era-B label-based filter (HD 2.4.a Track 2 Option 2 lock, 2026-05-09). The build no longer filters on a `questionnaire_no` integer-prefix enumeration; the qno suffix is fidelity-only (`validation/reports/qno_suffix_semantics_findings.md`).
- `QUESTION_MAP_CSV = ROOT / "crosswalks" / "question_map.csv"` — anchor crosswalk for canonical-or-raw label join (HD 2.1.e raw-vs-canonical pattern; build joins on `raw_question_label` when populated, falling back to `question` canonical otherwise).
- Build joins on `raw_question_label` when populated, falling back to canonical, for all three drifted questions (Q4, Q5, Q14). Q9 and Q11 raw labels match canonical per `crosswalks/question_map.csv` rows 20 / 22.
- `PANEL_FIRST_YEAR = 1975` and `PANEL_YEARS = range(PANEL_FIRST_YEAR, 2025)` — 1975–2024 inclusive (50 years). 1972 excluded per §3(a) (no field-level question); 1973–1974 carved per §3(a) revised 2026-05-10 (Guide-undocumented `status='c'` code on field-level Total-column rows). The constant carries the audit trail in its docstring; `build_era_a_rows()` enforces the floor defensively at the function level.
- `OUT_PATH = ROOT / "data" / "harmonized" / "herd_panel.parquet"`.
- `ATTR_OUT_PATH = ROOT / "data" / "harmonized" / "herd_panel_attributes.parquet"`.

### 6.2 Stage decomposition

The build runs as named stages, each with explicit input/output. Each stage is a function returning a DuckDB relation or a parquet path.

**Stage 1: Raw ingestion.** `load_year(year, con) -> DuckDBPyRelation`. Wraps `etl._load.read_herd_csv(year, con)`. Returns the unified-schema long relation. No filtering yet.

**Stage 2: Question filtering.** `filter_in_scope_questions(rel, era, con) -> DuckDBPyRelation`. Filters to the in-scope questions for the era via canonical question label, joined against `crosswalks/question_map.csv` (HD 2.4.a Track 2 Option 2 lock, 2026-05-09):
- Era A: `question IN (ERA_A_FIELD_QUESTION, ERA_A_EQUIPMENT_QUESTION)` (era-A has no Q4/Q5 carve-outs).
- Era B: `question IN (SELECT label FROM _xwalk_question_map_in_scope WHERE era = 'B')`, where `_xwalk_question_map_in_scope` is the canonical-or-raw label set built by `_load_question_map_crosswalk()` from the canonical questions in `ERA_B_IN_SCOPE_QUESTIONS_CANONICAL` (Q4, Q5, Q9, Q11, Q14). The crosswalk-load helper expands canonical and raw labels into one `label` column so the filter is canonical/raw-aware via SEMI JOIN — Q4/Q5/Q14 raw-label drift is handled by the in-scope table's expand-then-union pattern, not by a separate code path.

The build does **not** filter on `questionnaire_no` enumeration. The qno suffix encodes question-family in the numeric prefix (`'04'`, `'05'`, `'09'`, `'11'`, `'14'`) and field-discipline in the alphabetic-plus-leaf-digit suffix (`'09B05'` = Question 9, Engineering family, electrical/electronic/communications leaf); empirically the bijection between qno suffix and `row` text (`validation/reports/qno_suffix_semantics_findings.md`) makes label-filtering and qno-prefix-filtering strictly redundant. We filter on the canonical question label rather than the qno prefix because the bijection between suffix and row text makes the two filters strictly redundant, and the label-keyed filter is more readable in code and methods-note prose. The qno suffix is preserved in raw rows as fidelity-only data; the primary panel does not consume it for routing decisions.

**Stage 3: Discipline normalization.** `normalize_discipline(rel) -> DuckDBPyRelation`. Joins on `crosswalks/discipline_fine.csv` against `raw_row_label` (the row column in raw HERD CSVs), populating `discipline_fine` and `discipline_coarse` from the crosswalk. Asserts no unmapped row labels per §4(b). Era-A: joins on `(era='A', raw_row_label=row)`. Era-B: joins on `(era='B', raw_row_label=row)`. The `*, all` rollup rows pass through with `discipline_fine='Engineering, all'` etc., distinguished from leaves at the consumer side.

**Stage 4: Era-A direct rows.** `build_era_a_rows(years, con) -> DuckDBPyRelation`. For each year in 1973–2009: load, filter to in-scope questions, normalize discipline, project to the panel schema with `era='A'`, `source_class='all_source'`, `expenditure_type='r&d'` (or `'r&d_equipment'` for Item 3 rows), `value_type='current'`, `unit='kUSD_current'`. Filters to `column='Total'` (the era-A all-source column). Populate `quality_flag` from raw `status`: blank → `'reported'`, `'i'` → `'imputed'`, `'e'` → `'estimated'`, `'u'` → `'unspecified_zero'`, anything else → build raises `RuntimeError` (loud-log per §4(b) discipline). UNION ALL across years.

**Stage 5: Era-B per-component rows.** `build_era_b_components(years, con) -> DuckDBPyRelation`. For each year in 2010–2024: load, filter to Q9/Q11/Q14, normalize discipline, filter to `column='Total'` (the rolled column), project to schema with `era='B'`, `source_class='federal'` (for Q9), `'nonfederal'` (for Q11), or `'all_source'` (for Q14, treated as direct), `expenditure_type='r&d'` (Q9/Q11) or `'r&d_equipment'` (Q14). Populate `quality_flag` from raw `status` per the Stage 4 mapping. UNION ALL.

**Stage 6: Era-B reconstruction.** `build_era_b_all_source(era_b_components_rel) -> DuckDBPyRelation`. Reads Stage 5's Q9 and Q11 rows, FULL OUTER JOINS them on `(institution_id, year, discipline_fine)` at `column='Total'`, computes `COALESCE(Q9.value, 0) + COALESCE(Q11.value, 0)` as the reconstructed `source_class='all_source'` value, and propagates a `quality_flag` per the W4-locked least-good-flag-wins rule.

**Row-absent-as-zero arithmetic (W4 lock, maintainer-greenlit).** Per FY24 Guide pages 8 and 23, raw HERD CSVs encode genuine zeros at leaf cells via row-absence (only nonzero responses produce a leaf row); total rows always emit. So the "Q9 NULL" case at the (institution, year, discipline_fine) leaf grain is operationally "Q9 row absent at this cell" — which IS the institution's documented-zero statement, not a missing-data signal. Cases:

- **Q9 row-absent + Q11 value present** → reconstructed all_source = Q11.value. Q11 was the federal-fragmentation question's nonfederal counterpart; Q9 row-absence is the documented zero. Empirically the dominant case (22.1% of joined cells at FY 2024 per `validation/reports/herd_null_characterization_findings.md`).
- **Q9 value present + Q11 row-absent** → reconstructed all_source = Q9.value. Mirror case (7.1% at FY 2024).
- **Both present** → reconstructed all_source = Q9.value + Q11.value (70.8% at FY 2024).
- **Both row-absent** → no reconstructed row emitted (the institution-discipline cell carries no R&D in either source class for that year).

The rule sums across the federal/nonfederal axis only; never across the discipline axis. The arithmetic implementation is COALESCE(Q9.value, 0) + COALESCE(Q11.value, 0) at the FULL OUTER JOIN with `WHERE Q9 IS NOT NULL OR Q11 IS NOT NULL`.

**`quality_flag` propagation rule (W4 lock; propagation ordering locked 2026-05-09).**

The reconstructed `all_source` row's `quality_flag` is the **least-good of the two component flags**, with **row-absence contributing nothing to the flag** (the row-absent side is the Guide-documented zero side; it does not poison the present side's flag, because row-absence is institution-reported provenance per FY24 Guide pages 8 / 23, not data degradation).

*Locked ordering* (maintainer-greenlit 2026-05-09; lives in `crosswalks/era_b_reconstruction_rule.yaml` under the `quality_flag_propagation` block) — worst → best:

```
unspecified_zero  <  estimated  <  imputed  <  reported
```

*Rationale by position:*

1. **`reported` at the top:** institution's own numeric statement, no NSF intervention. Highest provenance trust.
2. **`imputed` second:** NSF-imputed numeric value with documented methodology (FY24 Guide page 10, prior-year carryforward). Auditable methodology, NSF-sourced value. The numeric value has more methodological backing than `estimated` because the carryforward provenance is specific.
3. **`estimated` below `imputed`:** NSF-supplied numeric value (FY24 Guide page 25, era-A only) but with more diffuse methodological backing — "estimated by NCSES" without a named carryforward source. Effectively retired in practice (1 occurrence in the entire FY 2008 file, 0 at column='Total' in scope). Position below `imputed` reflects that `imputed` carries a more specific NSF methodological provenance.
4. **`unspecified_zero` at the bottom:** the fidelity flag for the FY 2017 status='u' rows (244 occurrences, non-Total columns, `data='0'` empirically, Guide-undocumented). Position lowest because the flag itself is **outside the FY24 Guide's documented codeset** — the value is empirically zero but the encoding is not auditable against the Guide. Less trustworthy than even `estimated` (which is at least a Guide-documented code, however retired).

*Semantic clarification — locked 2026-05-09 (the load-bearing distinction between flag-propagation and row-absence-arithmetic):*

- `unspecified_zero` is **reserved for the FY 2017 status='u' fidelity flag only.** It flags rows that emit with raw `status='u'` (244 occurrences, FY 2017, non-Total columns, all `data='0'` empirically, Guide-undocumented). It does **NOT** flag row-absence.
- **Row-absence is handled by COALESCE arithmetic, not flag propagation.** Per FY24 Guide pages 8 and 23, raw HERD CSVs encode genuine zeros at leaf cells via row-absence (only nonzero responses produce a leaf row; total rows always emit). Row-absence IS the institution's documented-zero statement, not a missing-data signal. Stage 6's FULL OUTER JOIN handles this with `COALESCE(value, 0)` on each side; row-absence contributes a zero to the value sum and contributes **no flag** to propagation.
- **Reconstructed rows inherit the present side's flag when one side is row-absent.** The present side's flag passes through unmodified — no degradation, no blending.

Worked example: Q9 row-absent + Q11 reported → reconstructed all_source carries `quality_flag='reported'` (not `'unspecified_zero'` nor any blended degraded flag). The semantic claim: this all_source value is the institution's reported nonfederal R&D plus an institution-documented zero federal R&D. The institution-reported character of the value survives the reconstruction.

Conversely: Q9 imputed + Q11 reported → reconstructed all_source carries `quality_flag='imputed'` (least-good of `imputed` and `reported` is `imputed`). The numeric value contains an NSF imputation; the flag says so.

**Lock state.** The ordering and semantic clarification live in `crosswalks/era_b_reconstruction_rule.yaml` under the `quality_flag_propagation` block (locked 2026-05-09, maintainer-greenlit), alongside the existing `federal + nonfederal = all_source` rule. The YAML carries the FY24 Guide pages 8 / 23 anchor for the row-absent-as-zero semantic and the FY24 Guide page 10 / 25 anchors for the `imputed` / `estimated` codes. This scoping doc and the YAML are co-authored sources of truth on the propagation rule; drift between them is a CI/test concern enforced by Stage 9 sanity assertions (see Stage 9 below).

**Stage 7: Schema assembly.** `assemble_panel(era_a_rel, era_b_components_rel, era_b_all_source_rel) -> DuckDBPyRelation`. UNION ALL of Stage 4 + Stage 5 + Stage 6 with the locked column order from §1.

**Stage 8: Attribute table.** `build_attribute_table(years, con) -> DuckDBPyRelation`. For each year in 2010–2024: load, filter to Q4/Q5, project to the attribute schema (institution_id, year, era='B', med_school_share, clinical_trials_share, med_school_value, clinical_trials_value, source_file). Q5 raw label drift handled per the canonical/raw column on `crosswalks/question_map.csv`. UNION ALL across years; pivot Q4 and Q5 onto the same row per institution-year. Era-A side: emit one row per (institution, year) with NULL attribute values for 1973–2009.

**Stage 9: Sanity assertions before write.** Mirroring `etl/build_herd_personnel.py` lines 217–234:
- Row count > 0.
- No `discipline_fine='UNMAPPED_*'` rows (the discipline-normalize stage already raised on unmapped, but assertion is defense-in-depth).
- Era flag is `'A'` for years ≤ 2009 and `'B'` for years ≥ 2010, no exceptions.
- `source_class` is one of `{all_source, federal, nonfederal}`, no `UNMAPPED`.
- `expenditure_type` is one of `{r&d, r&d_equipment}`.
- `quality_flag` is one of `{reported, imputed, estimated, unspecified_zero}`, no NULL, no other values.
- **`unspecified_zero` rows in the output parquet follow the three-tier corrected baseline** (locked 2026-05-10 PM revising the original 2026-05-09 lock; revision per Vision consultation 2026-05-10 PM, Option δ + γ-allow). The original "FY-2017-only / non-Total-only" assertion was based on the W4 NULL characterization spike's three-spot-year sample (FY 2008 / 2017 / 2024) and was empirically incorrect — HD 2.4.b round 1 surfaced 9 panel-emitting rows violating both clauses, and HD 2.4.d's full era-B characterization probe (`etl/spikes/probe_era_b_status_u_full.py`) extended the empirical baseline to era-B-wide 2010–2022 (~4,000 rows, 106 institutions, retired FY 2023+). The three-tier corrected drift-defense assertion replaces the original two-clause assertion:

  1. **Era-A `unspecified_zero` rows raise.** Era-A files do not emit `status='u'` (verified empirically across 1973–2009 at `etl/spikes/probe_status_c_codeset.py`). Any era-A panel row with `quality_flag='unspecified_zero'` is a build bug.

  2. **Era-B `unspecified_zero` rows in years outside 2010–2022 raise.** FY 2023 and FY 2024 raw HERD files contain zero `status='u'` rows (NSF retired the encoding without Guide documentation of the convention change; the retirement is itself a publication-regime discontinuity, the sixth instance in `seeds/research-seeds.md` 2026-05-10 entry). Resumption in FY 2025+ would be a publication-regime change that warrants panel reconvene.

  3. **Era-B 2010–2022 `unspecified_zero` rows are allowed.** Per the corrected baseline. The panel-emitting subset at HD 2.4.b round 1 build time is 9 rows at FY 2020 Q14 `column='Total'` / institution `'003446'` (South Carolina State University, an HBCU). The build is faithfully passing through what NSF emitted; the methods note documents the empirical scope explicitly. Per Vision verdict, allowing the 9 rows propagate is methodologically defensible (the values are positive numeric; carving an HBCU-specific exclusion footnote reads worse at deposit-audit time than acknowledging broader codeset scope).

  The assertion's failure message names the offending (year, era, institution_id, question, column, raw row label) tuple so the operator can disposition the surfaced drift (resumption case) or fix the build (era-A bug case). The codeset-extension vs. empirical-scope-adjustment distinction locked at `CLAUDE.md` §6 (codeset-extension policy) is the venue: empirical-scope adjustments to existing enum values update this documentation; new enum values require Guide-documented anchor or panel-touch.
- For every era-B (institution, year, discipline_fine) triple where Q9 and Q11 both have rows, there is exactly one `source_class='all_source'` row whose value equals `Q9.value + Q11.value` within rounding tolerance (the reconstruction rule's identity is preserved by construction; the assertion catches integration bugs).
- For every reconstructed era-B `source_class='all_source'` row, the propagated `quality_flag` matches the least-good of the present-side component flags per the §6.2 Stage 6 ordering (the propagation rule is preserved by construction; assertion catches integration bugs).

**Stage 10: Parquet write.** Use DuckDB's native parquet writer, no pyarrow dependency (per personnel sibling's pattern — `etl/build_herd_personnel.py` line 238).

### 6.3 Sanity report

`sanity_report(parquet_path)` mirrors `etl/build_herd_personnel.py:sanity_report`:
- Total rows.
- Column types and order.
- Row counts by `(year, era, source_class, expenditure_type)`.
- Distinct `discipline_coarse` and `discipline_fine` values.
- Identifier coverage by era (era-A: `fice` populated, `ncses_inst_id`/`ipeds_unitid` NULL; era-B: all three populated).
- `value` column NULL/zero summary by era and `source_class`.
- `quality_flag` distribution by era and `source_class` (expected: ~95%+ `reported`, ~3–7% `imputed`, ~0% `estimated` and `unspecified_zero` — see `validation/reports/herd_null_characterization_findings.md` for the empirical baseline).
- Free-sum totals by year × source-class (cross-check against published HERD national totals — this is the back-of-envelope read; the formal verification is `panel_anchor_verify.py`).
- Era-B reconstruction identity check: median absolute residual of `(reconstructed_all_source) − (Q9 + Q11)` per (institution, year, discipline_fine), expected ~0.

The sanity report is verbose by intent — same discipline as the personnel sibling. It runs on every build and prints to stdout; the maintainer reads it as the immediate sanity check before the formal verification spike runs.

### 6.4 `main()`

```
def main():
    out = build_panel()
    print(f"Wrote {out} ...")
    out_attr = build_attribute_table_to_parquet()
    print(f"Wrote {out_attr} ...")
    sanity_report(out)
    return 0
```

Same shape as `etl/build_herd_personnel.py:main`.

---

## 7. Verification spike structure (`etl/spikes/panel_anchor_verify.py`)

Mirror of `etl/spikes/personnel_table26_verify.py`. Outline-level:

### 7.1 Module constants

- `PARQUET = ROOT / "data" / "harmonized" / "herd_panel.parquet"`.
- `DST_ANCHORS` — dict of spot-year → discipline → source-class → published value, from the DST PDF(s). Populated post-DST-scope verification (Q2(a)).
- Standard-form-population filter logic — locked from DST's published criterion.

### 7.2 Branches

The script is dual-branched per Q2:

**Branch A path:** `verify_per_discipline()`. For each spot year, each coarse bucket, each source-class:
- Filter parquet to standard-form-population subset (per DST's filter criterion, applied at the parquet side).
- Free-sum value at the bucket × source-class grain.
- Compare against the DST anchor.
- Print per-cell delta, percentage, and flag (`EXACT`, `WITHIN_ROUNDING`, `DIVERGE`).

**Branch B path:** `verify_institution_total()` (B1) or `verify_national_pool()` (B2). Same shape, narrower grid.

### 7.3 Output

Stdout-only at spike runtime. The formal report — `validation/reports/panel_anchor_reconciliation.md` — is hand-authored from the spike's printed grid plus the structural argument for any documented divergences. Mirror of the personnel reconciliation report (`validation/reports/personnel_table26_reconciliation.md`).

---

## 8. Q14 era-boundary spike (Q6)

The methods note (`reconstructive_harmonization.md` §4) ships Q14 as a parallel `expenditure_type='r&d_equipment'` row paralleling era-A Item 3, without an analogous boundary decomposition. Whether the era-A Item 3 series and the era-B Q14 series align as a continuous equipment series is empirically untested.

### 8.1 Spike target

`etl/spikes/spike_equipment_era_boundary.py` (~2 hour budget, throwaway). Outline:

1. Load FY 2008, 2009, 2010, 2011 raw HERD via `etl/_load.read_herd_csv`.
2. Filter to era-A Item 3 (`Current fund research equipment expenditures by field`) for FY 2008/2009.
3. Filter to era-B Q14 (`Capitalized R&D equipment expenditures by field`) for FY 2010/2011.
4. Subset to the top-10-by-FY-2008-R&D cohort (same cohort as `validation/reports/era_reconciliation_2008_2011.md`).
5. Aggregate to institution × year × coarse-bucket grain.
6. Compute the year-pair residuals: 2008→2011 long-gap, 2009→2010 adjacent, parallel to the existing residual analysis.
7. Print median bucket residuals, max-abs cells, sign-consistency.

### 8.2 Threshold ladder

Borrow the HD 1.4 / HD 2.1.b threshold structure (~5% bucket median, 15% per-cell extremity), recognizing equipment series may be noisier (lumpy capital expenditure):

- **Sign-consistent and magnitude-stable** (median bucket residual within ±10%, no per-cell residual >25%): equipment series alignment holds, methods-note assumption survives without footnote. The wider band reflects equipment's inherent year-to-year lumpiness.
- **Sign-divergent or magnitude-unstable**: the equipment series does *not* align as a continuous series. Methods note needs a Q14-specific footnote naming the discontinuity, parallel to the (b₂) decomposition. HD 2.4 still ships the parallel rows as planned (the rows are direct reads of each era's equipment question; the question is what the consumer can do with them, not whether the rows are emitted). The footnote names the limit.

### 8.3 Sequencing — **Option 2 CONFIRMED (W4 round, item 2)**

The spike runs DURING HD 2.4 implementation as sub-task **HD 2.4.f**, after scoping locks and after the Stage 5 era-B Q14 rows are in the parquet. Maintainer confirmed Option 2 in the W4 review round.

Rationale (preserved): the schema decision (parallel Q14 rows at `expenditure_type='r&d_equipment'`, `source_class='all_source'`) is independent of the spike outcome — the rows ship regardless. The spike answers a methods-note framing question (does era-A Item 3 align with era-B Q14 as a continuous equipment series, or does the methods note need a Q14-specific drift footnote), not a schema question. Running it during implementation keeps the scoping pass focused on schema and validation contract; the methods-note footnote, if needed, is a small write at HD 2.4.i close.

### 8.4 Spike kill condition

Budget 2 hours. If the residual computation runs cleanly in <1 hour, spend the second hour on cell-level inspection; if the spike hits a data-loading or schema issue, stop and surface (no rabbit-hole; the methods-note default is "we ship the parallel rows; consumers verify alignment empirically").

---

## 9. Short-form vs. standard-form (Q7)

### 9.1 Short-form rows in the panel

Short-form Q2 (`Short form: R&D expenditures by major R&D field`, FY 2012–2024) is the only short-form question with field-level disaggregation. Per CLAUDE.md §6 Table 26 standard-form-population constraint, short-form rows are outside the standard-form reconciliation universe — they cover institutions below the $1M threshold that file the reduced-question survey.

**Decision: include short-form rows in the panel with a `form_type` column flag.** `form_type` is one of the 20 schema columns per §1 (the column was inlined into the schema lock at §1 in the W4 round; this section retains the rationale):

```
form_type                   VARCHAR  ('standard' or 'short')
```

Short-form Q2 rows ship at `form_type='short'`, `era='B'`, `source_class='all_source'` directly (Short Form Q2 is the all-source field-level value for short-form respondents — no Q9/Q11 fragmentation to reconstruct), `expenditure_type='r&d'`, `value_type='current'`. Standard-form rows ship at `form_type='standard'` (the default for all era-A rows and for era-B Q9/Q11/Q14 rows).

Rationale: parallels the personnel sibling's Phase 1 design choice — keep the parquet filter-free, apply the population filter at reconciliation time only. A consumer who wants Table-26-style alignment filters `form_type='standard'`; a consumer who wants the all-respondents view reads everything. Excluding short-form would lose the all-respondents view that the personnel sibling explicitly preserves.

### 9.2 Short Form Q2 raw structure verification

The exact raw-CSV structure of Short Form Q2 (column names, row labels, whether it carries `column='Total'` or a different rolled column) is not directly verified against the data files in this scoping pass. The HD 2.4 implementation should verify this empirically before committing to the projection — a small probe spike at Stage 1, parallel to `etl/spikes/probe_q15_q16_structure.py` for the personnel sibling.

If Short Form Q2 carries the same `(question, row, column)` structure as standard-form Q9/Q11 (with a `column='Total'` rolled value), the projection is straightforward. If the short-form file's raw structure differs (e.g., column-axis carries source-of-funds rather than discipline; or the rolled column has a different name), the projection adapts. The schema decision (`form_type='short'`, `source_class='all_source'`) does not depend on the answer; only the projection SQL does.

This is flagged as an HD 2.4.b implementation-time verification, not a scoping blocker.

### 9.3 Other short-form rows

Short Form Q1 (R&D by source of funds), Q1.1 (types of expenditures), Q3, Q4, Q5 (subrecipient flows, fiscal year) are not field-level — they ship as institution-year attributes (Q3/Q4 to the attribute table per §1(c) if relevant, the rest excluded). Short-form Q1 is parallel to standard-form Q1 (`Academic R&D expenditures by source of funds`); neither standard-form Q1 nor short-form Q1 ships in `herd_panel.parquet` because they are institution-year-level by-source attributes, not field-level rows. They sit in the attribute parquet only if the maintainer wants them; default is exclude.

---

## 10. Implementation timeline

HD 2.4 sub-task decomposition. Half-day units, parallel to HD 2.1's 10.5 half-day actual against 10.75 estimated.

**Note on CLOSED stamps.** Inline CLOSED dates mark sub-tasks that carried a distinct disposition (e.g., `CLOSED-DIVERGENT`, scope re-shapes, verification gates). The core build-pipeline sub-tasks (HD 2.4.a–d) closed as planned with the shipping panel (commit `079f6f4`) and are not individually stamped; their closure is implied by the build artifact rather than recorded inline. This convention — inline stamps for distinct-disposition sub-tasks, implied closure for routine pipeline rows — applies to future HD x.y.z sub-tasks.

| Sub-task | Deliverable | Estimate |
|---|---|---:|
| **HD 2.4.a — Stage 1–3 + scaffolding + DST staging + `quality_flag` plumbing** | `etl/build_herd_panel.py` skeleton; `load_year`, `filter_in_scope_questions`, `normalize_discipline` functions; defensive crosswalk-coverage assertion live; `quality_flag` derivation from raw `status` plumbed through Stages 1–3 with the four-value enum and the loud-log on unknown codes; DST PDFs staged at `data/reference/` (FY 2024 plus FY 2008/2010/2017 if available); smoke-test on FY 2008 era-A and FY 2024 era-B to confirm row counts and `quality_flag` distribution against the W4 spike baseline | 2.25 |
| **HD 2.4.b — Stage 4 + Stage 5** | Era-A direct rows + era-B per-component rows assembled; FY 1975–2024 panel scan succeeds (FY 1972/1973/1974 carved per §3(a)); `form_type='short'` rows added (probe Short Form Q2 raw structure as part of this sub-task); `quality_flag` populated on every row | 1.5 |
| **HD 2.4.c — Stage 6 reconstruction** | Era-B `source_class='all_source'` rows reconstructed via FULL OUTER JOIN + COALESCE-to-zero arithmetic; least-good-flag-wins propagation per W4-locked ordering; identity check passes (median residual ~0); flag-propagation assertion passes | 1.0 |
| **HD 2.4.d — Stage 7–10** | Schema assembly + sanity assertions (incl. `quality_flag` enum check) + parquet write + `sanity_report` runs end-to-end (incl. flag-distribution summary) | 1.0 |
| **HD 2.4.e — Attribute table** | `herd_panel_attributes.parquet` builds; Q4/Q5 carve-outs joined; Q5 raw-vs-canonical drift handled. **CLOSED-AT-HD-2.4.d 2026-05-10.** Stage 8 shipped the attribute table inline at HD 2.4.d; five-check verification spike (`etl/spikes/verify_attribute_table_hd_2_4_e.py`) confirmed §1(c) schema match, `(institution_id, year)` uniqueness, era-A NULL discipline, era-B share in [0, 1] band, Q5 coverage every era-B year. No separate ETL cycle needed. | 1.0 |
| **HD 2.4.f — Q14 era-boundary spike** | `etl/spikes/spike_equipment_era_boundary.py` runs; equipment-series alignment verdict. **CLOSED-DIVERGENT 2026-05-10.** Sign-consistent PASS (40/40); magnitude-stable FAIL (9/10) with UPenn FY 2010 2.56× outlier reverting at FY 2011; cohort-aggregate boundary ratio 1.19; median institution boundary ratio 1.14. Categorical accounting-framing change (current-fund era-A vs. capitalized era-B). Methods-note equipment-series footnote queued for HD 2.4.i per RH clause (b) discipline. Findings at `validation/reports/equipment_era_boundary_findings.md`. | 1.0 |
| **HD 2.4.g — DST verification spike** | `etl/spikes/panel_anchor_verify.py` runs end-to-end on the FY 2024 era-B-internal cohort-anchored verification grid; cell-by-cell grid printed; structural argument drafted for any divergences. **CLOSED 2026-05-24 (Branch III adopted).** The pre-Branch-III 240-cell nominal grid (+ optional 120 reconciliation cells) was retired for the 58-substantive-cell FY 2024 grid (UCSF Engineering structurally absent — 2 cells); verdict 58/58 PASS at +0.000%. Historical-vintage anchors (FY 2008 / 2010 / 2017, precondition (ii) below) deferred per Branch III — the cross-era surface is the HD 2.1.b decomposition (`validation/reports/era_reconciliation_2008_2011.md`), not a per-spot-year grid. See PANEL_SKIPPER §8 (2026-05-24) and `validation/reports/panel_anchor_reconciliation.md` (HD 2.4.h). **Preconditions (locked 2026-05-10):** (i) HD 2.4.a Round 2 passes — FY 2024 Table Builder export reproducibility verified by a cold reader using the staged YAML query parameters; if Round 2 fails, Option (b) collapses to (c) and panel reconvenes (no HD 2.4.g start). (ii) Historical-vintage (FY 2008 / FY 2010 / FY 2017) DST publication regime verified at HD 2.4.g entry — PDFs staged where available, Table Builder CSV snapshots staged with the §2(d.2) seven-item discipline where not. (iii) Per-spot-year anchor source (§2(b) anchor-source table) finalized before the spike runs. | 1.5 |
| **HD 2.4.h — Verification report** | `validation/reports/panel_anchor_reconciliation.md` authored; methods-note §6 ("What the deposit ships") updated to reference. **CLOSED 2026-05-24.** Report landed (commit 8b2d6c1); the methods-note §6 cross-reference landed with the HD 2.4.i transplant (commit e96c920). | 1.0 |
| **HD 2.4.i — Methods-note integration + close** | NULL-convention paragraph added to `reconstructive_harmonization.md` §6 with FY24 Guide pages 8 / 23 / 10 / 25 anchors; rollup-vs-leaf double-counting paragraph added; pre-1981 fingerprint footnote added; equipment-series asymmetry note added; **equipment-series Q14 era-boundary footnote (HD 2.4.f-confirmed): names the categorical accounting-framing change (current-fund era-A Item 3 vs. capitalized era-B Q14) and carries the spike's empirical magnitudes — median institution boundary ratio 1.14, 9/10 in [0.5, 2.0] with UPenn FY 2010 outlier at 2.56× reverting at FY 2011, cohort-aggregate boundary ratio 1.19. Active-voice methodology framing (locked at HD 2.4.f close): "we ship both as `expenditure_type='r&d_equipment'` rows with this footnote naming the discontinuity"; cites `validation/reports/equipment_era_boundary_findings.md` and the spike**; cross-references audit; maintainer review close. **CLOSED 2026-05-25.** Five methods-note surfaces (rollup-grain, NULL-convention, pre-1981 footnote, equipment `all_source` + Q14 era-boundary footnote, mixed-case status-fold) + `status='c'` carve-out footnote + era-A year-range reconciliation landed in `reconstructive_harmonization.md` (commit e96c920); Vision-assessed COMPLETE. | 0.75 |
| **Buffer** | — | 0.5 |
| **Total** | — | **11.5 half-days** |

The estimate revisions vs. the prior round (11.0 → 11.5):

- **HD 2.4.a +0.25** for `quality_flag` plumbing through Stages 1–3 (raw-status → enum mapping, loud-log on unknown codes, smoke-test that flag distribution matches the spike baseline) and DST PDF staging at `data/reference/`. The DST scope is now locked (Branch A, 240-cell grid) so the staging is mechanical, not exploratory.
- **HD 2.4.i +0.25** for the methods-note NULL convention paragraph with FY24 Guide pages 8 / 23 / 10 / 25 anchors. The §14.2 / §14.3 / §14.4 / §14.5 surfaces all land in HD 2.4.i; the NULL paragraph is the most substantive write of the four.

11.5 half-days is tighter than HD 2.1's 10.5 not because the work is smaller but because the methodology and crosswalks are locked entering HD 2.4 — no spike-driven taxonomy decisions, no per-bucket residual ladder calibration, no W1-class question-mapping crosswalk authoring. The work is build, verify, document. The W4 round's `quality_flag` plumbing is one schema column, four enum values, one propagation rule — small in lines of code, larger in cold-reader semantic value.

---

## 11. Out-of-scope boundaries

What HD 2.4 does **not** cover:

- **HD 2.5 — BEA GDP price index for R&D deflation.** The `value_type='constant'` rows are not produced at HD 2.4. The schema reserves the column; HD 2.5 fills it.
- **HD 2.6 — Methods note publication-grade revision.** The methods note exists; HD 2.6 may polish it for deposit submission and add the Q14 footnote if the spike (§8) surfaces drift.
- **HD 2.7 — Standard-form-population reconciliation.** The personnel sibling's Table-26 framework applied to the financial panel. The DST verification (§7) gives the all-respondents anchor; the standard-form-only reconciliation is a separate task that filters the parquet to the standard-form universe and reconciles against any standard-form-restricted DST tables.
- **Per-agency Q9 disaggregation.** Q9's seven federal agency columns (DOD, DOE, HHS, NASA, NSF, USDA, Other agencies) are out of scope. The reconstruction rule uses `column='Total'`; agency-level rows are not emitted to `herd_panel.parquet`. Agency-level reconstruction is a separate methods-note section (per `crosswalks/era_b_reconstruction_rule.yaml` `dispositions.W4_federal_column_total.panel_disposition`).
- **ARRA reopen.** `docs/hd_2_1_scoping.md` may carry ARRA reopening notes; the build assumption is case-(a) within-federal per CLAUDE.md §6 disposition W3, locked at HD 2.1.b. If a residual surfaces that traces to ARRA, that's a separate disposition reopen, not an HD 2.4 task.
- **OpenAlex / NIH RePORTER / NSF Award Search joins.** The training-grants-component-of-definitional-drift residual is HERD-unmeasurable per `reconstructive_harmonization.md` §5. Closing it requires external data; out of HD 2.4 scope.

---

## 12. Reproducibility contract

A cold reader with the lockfile (`uv.lock`), the raw zips in `data/raw/herd/`, and these scripts reaches the same harmonized parquet and the same verification grid:

```bash
# Build the financial panel and the attribute sibling:
uv run python etl/build_herd_panel.py

# Regenerate the DST verification grid:
uv run python etl/spikes/panel_anchor_verify.py

# (Optional) Regenerate the equipment-boundary spike:
uv run python etl/spikes/spike_equipment_era_boundary.py
```

Inputs:
- `data/raw/herd/higher_education_r_and_d_{1972..2024}.zip` (53 zips; SHA-256s in `data/raw/MANIFEST.md`).
- `crosswalks/question_map.csv`, `crosswalks/discipline_coarse.csv`, `crosswalks/discipline_fine.csv`, `crosswalks/era_b_reconstruction_rule.yaml` (with the W4 propagation-ordering clause once greenlit).
- `data/reference/` verification anchors — **hybrid anchor architecture per §2(d) split (locked 2026-05-10).** Static-PDF anchors per §2(d.1) (FY 2024 Tables 10/11/15 staged in HD 2.4.a Round 1; FY 2008/2010/2017 PDFs at HD 2.4.g entry where the publication regime supports them). Table Builder CSV snapshots per §2(d.2) (FY 2024 Tables 28–54 surface; potentially analogous historical-vintage cells subject to HD 2.4.g entry verification), each paired with a `dst-table-builder-FY{year}-query.yaml` query-parameter sidecar.

Outputs:
- `data/harmonized/herd_panel.parquet` (~1.4M rows estimated: 50 years × ~600 institutions × ~10 disciplines × ~3 source-class rows for era B; rough order of magnitude. FY 1972/1973/1974 carved per §3(a)).
- `data/harmonized/herd_panel_attributes.parquet` (~13K rows estimated: ~900 institutions × 15 era-B years).
- `validation/reports/panel_anchor_reconciliation.md`.

### MANIFEST treatment for harmonized artifacts (W4 round, item 9 lookup)

Lookup result: the personnel sibling does **NOT** carry a SHA-256 entry for `data/harmonized/herd_personnel.parquet` in any MANIFEST. `data/harmonized/MANIFEST.md` does not exist. The personnel README (`docs/methods_notes/herd_personnel_README.md` lines 111–120) lists only the **input** raw-zip SHA-256s (which live in `data/raw/MANIFEST.md`) and treats the harmonized parquet as a **regenerable artifact** — a cold reader with the lockfile, the raw zips, and the build script regenerates the parquet bit-equivalently (modulo parquet writer determinism, which DuckDB's native writer respects on a fixed input-and-code-version pair).

**Pattern locked for `herd_panel.parquet` and `herd_panel_attributes.parquet`:** match the personnel sibling. Both parquets ship as regenerable artifacts. The deposit README lists their **input** SHA-256s (the 53 raw HERD zips, the locked `uv.lock`, the locked crosswalks, the locked `era_b_reconstruction_rule.yaml`, the staged DST PDFs at `data/reference/`) plus the build script paths. No `data/harmonized/MANIFEST.md` is created. If a future deposit-packaging session at W6/W7 decides the harmonized parquet needs its own SHA-256 (e.g., for Zenodo deposit citation), that decision is made at deposit-packaging time and is consistent with the personnel sibling treatment whichever way it goes.

**Updated at Stage 2 deposit packaging (Decision A, 2026-05-25).** The deposit-packaging session exercised the option this section reserved: a `data/harmonized/MANIFEST.md` now ships, pinning the SHA-256s of all three harmonized parquets (`herd_panel.parquet`, `herd_personnel.parquet`, `herd_panel_attributes.parquet`). This is a **packaging artifact, not a build artifact** — the build still treats the parquets as regenerable (the raw-zip + crosswalk + `uv.lock` input SHAs plus the code reproduce them bit-equivalently; `etl/build_herd_panel.py` imposes a deterministic `ORDER BY` before the parquet `COPY`, so the bytes are stable across rebuilds). The MANIFEST lets a deposit consumer verify a downloaded parquet's integrity and confirm a rebuild matches the deposit. No methodology, crosswalk, or build-logic change — the regenerable-artifact framing above holds for the build; the MANIFEST is the citation layer on top.

### Cross-sibling `quality_flag` asymmetry (deposit README language)

The financial sibling carries a `quality_flag` column (W4 lock); the personnel sibling does not. To be added to the W9–10 deposit README in the cross-sibling-comparison section:

> *Personnel sibling carries reported values without imputation flag (consideration deferred to follow-up); financial sibling carries `quality_flag` per HD 2.4 scoping decision.*

This is a documented methodological asymmetry, not a defect — the financial value axis (dollars, NSF-imputed at ~3% of rows per `validation/reports/herd_null_characterization_findings.md`) carries imputation provenance that the headcount/FTE personnel value axis was not characterized for at deposit time. Personnel-sibling `quality_flag` parity is tracked as a post-W9–10 follow-up consideration (see §14.8 for the deferred-investigation entry).

Same install path as the personnel sibling — runtime deps only (`duckdb`, `pypdf`) per CLAUDE.md §6 reproducibility contract; the `charts` group is required only for figure regeneration in HD 2.6.

---

## 13. Action items before scoping locks

### Resolved in W4 round 2026-05-09

1. ~~**DST scope verification (Q2).**~~ **RESOLVED (item 1).** Maintainer verified DST publishes per-institution per-discipline per-funding-source per-year. Branch A locked at the 240-cell grid (10 institutions × 4 spot years × 3 disciplines × 2 source classes). Branch B marked not applicable. Sub-action added: DST PDFs staged at HD 2.4.a (FY 2024 plus FY 2008/2010/2017 where available). See §2.
2. ~~**Q14 spike sequencing (Q6 / §8.3).**~~ **RESOLVED (item 2).** Option 2 confirmed: spike runs at HD 2.4.f, during HD 2.4 implementation, after scoping locks. See §8.3.
3. **Sibling parquet for Q4/Q5 attributes (item 3).** **RESOLVED.** `herd_panel_attributes.parquet` confirmed as separate artifact alongside the main panel. See §1(c).
4. **Methods-note paragraphs at HD 2.4.i (items 5, 6, 7).** **RESOLVED — landed at HD 2.4.i (2026-05-25, commit e96c920).** All three surfaces are in `reconstructive_harmonization.md`: rollup-vs-leaf double-counting paragraph (item 5 / §14.3, in §6); pre-1981 fingerprint footnote (item 6 / §14.4, `[^pre1981]`); equipment-series `source_class='all_source'` asymmetry note (item 7 / §14.5, in §4) with the Q14 era-boundary footnote (`[^equip-boundary]`).
5. **1972 row in attribute parquet (item 8).** **RESOLVED.** Excluded from `herd_panel_attributes.parquet`, consistent with main-panel exclusion. See §14.6.
6. **MANIFEST treatment of harmonized artifacts (item 9).** **RESOLVED.** Looked up the personnel sibling's actual treatment: no SHA-256 entry for the harmonized parquet in any MANIFEST; `data/harmonized/MANIFEST.md` does not exist; the parquet ships as a regenerable artifact and the README lists only input-zip and crosswalk SHA-256s. Pattern matched for `herd_panel.parquet` and `herd_panel_attributes.parquet` — both ship as regenerable artifacts. **Superseded at Stage 2 (Decision A, 2026-05-25):** the deposit-packaging session decided the harmonized parquets need their own SHA-256 anchor for Zenodo citation; `data/harmonized/MANIFEST.md` now ships pinning all three. The regenerable-artifact framing holds for the build; the MANIFEST is a packaging layer. See §12 "MANIFEST treatment for harmonized artifacts."
7. **NULL handling lock (item 4).** **RESOLVED, all four sub-locks applied.** Four NULL greenlights applied:
   - `quality_flag` column added as 20th panel column with the four-value enum, position contiguous with the value-axis block. See §1.
   - Row-absent-as-zero framing locked with FY24 Guide pages 8 / 23 anchors. See §6.2 Stage 6.
   - Least-good-flag-wins propagation locked. **Propagation ordering `unspecified_zero < estimated < imputed < reported` maintainer-greenlit 2026-05-09 and locked into `crosswalks/era_b_reconstruction_rule.yaml` under the `quality_flag_propagation` block.** See §6.2 Stage 6 and §14.2.
   - Personnel sibling parallel update deferred; cross-sibling asymmetry documented in deposit README. See §12.

### Implementation-time verification, not pre-lock

8. **Short Form Q2 raw structure verification (§9.2).** Acknowledged as an HD 2.4.b implementation-time verification, not a pre-lock action item.

### Resolved in final lock round 2026-05-09

9. ~~**`quality_flag` propagation ordering**~~ **RESOLVED 2026-05-09.** Maintainer-greenlit ordering `unspecified_zero < estimated < imputed < reported` (worst → best), with the semantic clarification that `unspecified_zero` is reserved for the FY 2017 status='u' fidelity flag only and does NOT flag row-absence. Locked into `crosswalks/era_b_reconstruction_rule.yaml` under the `quality_flag_propagation` block alongside the existing `federal + nonfederal = all_source` rule. See §6.2 Stage 6, §14.2.
10. ~~**The revised scoping document as a whole.**~~ **RESOLVED 2026-05-09. Scoping document locked 2026-05-09.** This document is the implementation contract for HD 2.4. HD 2.4.a starts on the next personal deep-block session.

### Final lock round additions 2026-05-09

11. **Stage 9 FY-2017-only / non-Total-only sanity assertion (locked 2026-05-09).** Added to §6.2 Stage 9's existing assertion list. The assertion enforces that `unspecified_zero` rows in the output parquet are FY-2017-only and non-Total-only; if a future raw HERD file emits status='u' outside this scope, the build fails loud. This is the build-side enforcement of the semantic clarification locked above. Lands in HD 2.4.a's defensive assertions naturally per the §10 timeline.

### §2 amendment-lock 2026-05-10 (DST publication-regime contraction)

12. **§2 amendment-lock applied 2026-05-10.** Reason: *FY 2024 DST publication regime contracted from 86 PDFs to 55; Tables 28–54 (engineering subfield rankings, agency-specific rankings) Table-Builder-only.* Surfaced at HD 2.4.a Round 1 when staging the FY 2024 DST anchor surface for the §2(b) Branch A 240-cell verification grid; Vision consulted; verdict SHIP with seven-item discipline.

    **Disposition:** Option (b) Table-Builder-CSV-snapshot accepted with seven-item discipline (access date, SHA-256, cold-reader instruction, query-parameter YAML sidecar pattern, tool-interface stability disclaimer, two-tier re-verification path, methods-note cross-reference). §2 amendments applied:
    - §2(b) clarified — 240-cell composition unchanged; per-spot-year anchor-source table added (FY 2024 = Table Builder CSV snapshot for the institution × discipline × source-class matrix; FY 2008/2010/2017 = static PDF or Table Builder CSV snapshot, regime-stability verified at HD 2.4.g entry).
    - §2(d) split into §2(d.1) "Static-PDF anchors" and §2(d.2) "Table Builder CSV snapshots" carrying the seven-item staging discipline as locked staging procedure. §2(d.2) documents the YAML sidecar schema/template; per-year sidecar files (`data/reference/dst-table-builder-FY{year}-query.yaml`) NOT created at this round — they materialize at HD 2.4.g.
    - §2(e) NEW "Publication-regime stability caveat" — names the regime change explicitly; cross-references the methods-note regime-change paragraph in `docs/methods_notes/reconstructive_harmonization.md` §6 and the seed in `seeds/research-seeds.md` 2026-05-10.
    - §10 timeline HD 2.4.g preconditions amended — Table Builder export reproducibility (Round 2 sub-action of HD 2.4.a, currently in flight) and historical-vintage regime stability gate HD 2.4.g entry. If Round 2 fails, Option (b) collapses to (c) and panel reconvenes.
    - §12 reproducibility-contract Inputs list updated to reflect the hybrid anchor architecture.

    **Companion artifacts:**
    - Methods note: regime-change paragraph added to `docs/methods_notes/reconstructive_harmonization.md` §6 ("What the deposit ships").
    - Research seeds: Part 1 entry dated 2026-05-10 added at `seeds/research-seeds.md` ("Publication-regime stability as a Reconstructive Harmonization axis"); flagged as fourth axis of operational-data discontinuity.
    - Locked-decisions log: parallel entry recorded at `PANEL_SKIPPER.md` §8.
    - Citations: FY 2024 DST PDFs already added at HD 2.4.a Round 1 with access date 2026-05-10. Forthcoming Table Builder CSV snapshots reserved for HD 2.4.g (placeholder language added to `docs/source_documents/citations.md`).

    **CLAUDE.md not amended this round.** Per Vision's call: the receipt/headline split (CLAUDE.md §6 methods-note voice) already handles the regime-change paragraph correctly. CLAUDE.md picks up "publication-regime stability" as a named methodological commitment only if the seed graduates at the mid-June quarter-boundary panel review.

### §2(b) re-shape pass — Branch III two-row anchor table (locked 2026-05-21)

13. **§2(b) re-anchored to Branch III two-row shape 2026-05-21.** Reason: Vision verdict 2026-05-21 (HD 2.4.g re-shape pass, Q1 = Branch III adopted; Q2 = disposition (a) methods-note feature with Finding 3 receipt-only; Q3 = kill-criteria pre-commit locked). Maintainer authorized 2026-05-21. The pre-existing four-spot-year anchor table (FY 2024 + FY 2017 + FY 2010 + FY 2008, with the historical-vintage triplet posture "Static PDF if available; else Table Builder CSV snapshot") contracted to two anchor rows: FY 2024 era-B-internal cohort-anchored verification grid + cross-era verification (`validation/reports/era_reconciliation_2008_2011.md`, inheriting the HD 2.1.b residual gate as the cross-era verification surface).

    **Disposition:** at the current verification-anchor scope, FY 2024 era-B-internal verification (anchor row 1) plus HD 2.1.b cross-era boundary characterization (anchor row 2) together discharge the era-B reconstruction-rule and era-boundary-discontinuity verification responsibilities the deposit owes a cold reader. Multiplying spot-year anchors across the historical-vintage triplet does not earn its complexity at the current scope; the FY 2017 / FY 2010 / FY 2008 anchors move to a caveat block beneath the contracted table.

    **Branch A sub-grid rename.** The Branch A 60-nominal / 58-substantive grid is renamed "FY 2024 era-B-internal cohort-anchored verification grid" to make the era-B-internal-anchored framing explicit. The verb stays "verify"; the surface stays the Table Builder CSV snapshot per §2(d.2); the rename clarifies the grain (era-B-internal cohort-anchored at FY 2024, not cross-era).

    **Expansion triggers** (locked at the §2(b) caveat block; carried verbatim here for the §13 audit trail): (i) HD 2.4.i NCSES historical-publications hunt produces a credible static-PDF anchor at the 3-D matrix at cohort grain for any of the three historical vintages; (ii) a Q2 surface produces the same; (iii) a journal reviewer at the Q2 / Q3 publication arc cites verification scope as defect. Until one of the three triggers fires, the historical-vintage anchors remain deferred and the two-row anchor table is the locked Branch A verification surface.

    **§2 amendments applied this lock.**
    - §2(b) per-spot-year anchor table contracted to two rows (FY 2024 era-B-internal cohort-anchored verification grid + cross-era verification at `validation/reports/era_reconciliation_2008_2011.md`).
    - §2(b) caveat block added beneath the contracted table carrying the Branch III rationale and the three expansion triggers (locked verbatim).
    - Branch A sub-grid renamed "FY 2024 era-B-internal cohort-anchored verification grid" inside §2(b).
    - §2(b) lock-entry reference added to this §13 entry (this row).

    **Companion artifacts updated this lock.**
    - YAML sidecar at `data/reference/dst-table-builder-FY2024-query.yaml` (filename aligned to the §2(d.2):190 convention via `git mv` 2026-05-21; the earlier divergent filename `dst-table-builder-FY2024.yaml` retired in the same pass) — `cold_reader_instruction` block added receipting the UI-navigation-hazard finding (PANEL_SKIPPER §8 entry 2026-05-21 Finding 1; receipt-level only per the receipt/headline split, CLAUDE.md §6 methods-note voice lock 2026-05-01).
    - `docs/methods_notes/reconstructive_harmonization.md` §6 — footnote added cross-referencing the YAML sidecar's `cold_reader_instruction` block (Finding 3 / UI-nav-hazard fails the §6 voice "surprise + number" test → receipt-only, not headline-level).
    - `seeds/research-seeds.md` 2026-05-10 entry — sixth instance added beneath the existing five (UCSF Engineering structural absence at the FY 2024 verification grid; cohort-substrate-heterogeneity grain, parallel to FY 1973–1974 status='c' codeset retirement at status-codeset grain). "Cohort heterogeneity" and "tool-architecture-as-constraint" remain instances under the publication-regime / operational-data discontinuity umbrella; quarter-boundary review (mid-June) gates any graduation to separate parallel axes.
    - `data/reference/MANIFEST.md`, `docs/source_documents/citations.md`, `PANEL_SKIPPER.md` 2026-05-21 entry, `data/reference/dst-table-builder-FY2024-query.yaml` preamble — all updated to reference the renamed sidecar filename. Repo-wide stale-reference sweep run in the same pass.

    **Posture.** The two-row anchor table is the locked Branch A verification surface as of 2026-05-21. Branch A spike clearance is the next discrete action (re-shape pass step 4) — NOT in scope for the step-2 re-shape work; maintainer greenlights commit (step 3) and spike clearance (step 4) separately.

---

## 14. Surfaces flagged during drafting

Methodologically loaded surfaces that emerged during scoping but were not in the original Q1–Q7. Flagged for maintainer awareness; some may need explicit panel-level disposition before HD 2.4 implementation.

### 14.1 Attribute sibling parquet vs. inline columns (§1(c)) — **CONFIRMED W4 round (item 3)**

The sibling-parquet treatment (`herd_panel_attributes.parquet` shipping alongside the main panel as a separate artifact) is **confirmed by the maintainer in the W4 review round.** Two artifacts in the financial half of the deposit; cleaner separation; queries that join the carve-out attributes back to the main panel pay one join cost rather than carrying replicated values per discipline row. Implementation lands at HD 2.4.e per §10 timeline.

### 14.2 NULL handling in the era-B reconstruction — **LOCKED W4 round (item 4)**

The W4 NULL characterization spike (`etl/spikes/spike_herd_null_characterization.py`, findings at `validation/reports/herd_null_characterization_findings.md`) reframed the question. The original §14.2 framing assumed `value` would routinely be NULL in raw rows; the spike showed there are zero NULL `value` cells in `column='Total'` rows across the three spot years (FY 2008 / 2017 / 2024, 65,609 in-scope rows). The "NULL" in the era-B reconstruction is not a NULL inside the row — it is a row that does not exist at the (institution, year, discipline_fine, source_class) cell, and per FY24 Guide pages 8 and 23, row-absence is the documented encoding for genuine zero R&D in that cell.

**Locked W4:**

- **Row-absent-as-zero framing.** The reconstruction rule `Q9 row-absent + Q11 value = Q11 value` survives, with the semantic clarification that row-absence at a leaf cell IS the institution-reported zero (per FY24 Guide pages 8 / 23), not a missing-data signal. Implementation: FULL OUTER JOIN at (institution, year, discipline_fine, column='Total') with COALESCE(value, 0) on each side. See §6.2 Stage 6.
- **Methods note NULL convention paragraph at HD 2.4.i.** Cites FY24 Guide pages 8 / 23 (row-presence-only-when-nonzero) and pages 10 / 25 (status-code documentation for `i` / `n` / `e`) explicitly. Same audit-trail discipline as the rest of the methods note. Draft paragraph already in `validation/reports/herd_null_characterization_findings.md` §7.
- **`quality_flag` column added** as 20th panel column with four-value enum (`reported / imputed / estimated / unspecified_zero`) per §1 and §6.2 Stages 4–6.
- **Least-good-flag-wins propagation locked, ordering locked 2026-05-09.** Propagation ordering `unspecified_zero < estimated < imputed < reported` (worst → best) is **maintainer-greenlit 2026-05-09** and lives in `crosswalks/era_b_reconstruction_rule.yaml` under the `quality_flag_propagation` block, alongside the existing `federal + nonfederal = all_source` rule. Rationale-by-position is in §6.2 Stage 6.
- **Semantic clarification locked 2026-05-09.** `unspecified_zero` is reserved for the FY 2017 status='u' fidelity flag only; it does NOT flag row-absence. Row-absence at the (institution, year, discipline_fine, source_class) leaf grain is handled by `COALESCE(value, 0)` arithmetic in the FULL OUTER JOIN at Stage 6; row-absence contributes a zero to the value sum and contributes no flag to propagation. Reconstructed rows inherit the present side's flag unmodified when one side is row-absent. This separation is documented in §6.2 Stage 6 (worked examples) and in the YAML's `quality_flag_propagation.semantic_clarification` block. Stage 9's sanity assertion (FY-2017-only / non-Total-only) is the build-side enforcement of the same boundary.

The original Option B (NULL-propagating) framing is dropped — empirically there are no within-row NULLs to propagate at column='Total'; the question was only ever about row-absence semantics, which the FY24 Guide pages 8 / 23 framing settles in favor of "row-absent IS zero."

### 14.3 The `*, all` rollup vs. leaf double-counting — **CONFIRMED W4 round (item 5)**

Methods-note paragraph at HD 2.4.i confirmed by maintainer in the W4 review round. Convention to be spelled out in `reconstructive_harmonization.md` §6 ("What the deposit ships"): when computing bucket totals, prefer the `*, all` rollup; when computing leaf-level aggregates, exclude rollups.

(Background preserved.) Era-A `Expenditures by S&E field` carries both rolled rows (`row='Engineering, all'`) and leaf rows (`row='Engineering, civil'`, etc.). Era-B Q9/Q11 carry the same structure. The schema ships both rolled and leaf rows because both carry signal (the rollup is the canonical bucket total; the leaves are the disaggregation). The personnel sibling has the analogous issue at `personnel_function='total'`; the personnel verify spike filters `personnel_function='total'` for the Table 26 reconciliation (`etl/spikes/personnel_table26_verify.py` line 73). The financial verify spike does the same — filter to rolled rows (`discipline_fine LIKE '%, all'`) for bucket-level reconciliation.

### 14.4 Pre-1981 fingerprint in the panel — **CONFIRMED W4 round (item 6)**

Methods-note footnote at HD 2.4.i confirmed by maintainer. Footnote to be added to `reconstructive_harmonization.md` §6 alongside the existing 1972-exclusion footnote and the new FY 1973–1974 carve-out footnote (per §3(a) revised 2026-05-10). The pre-1981 fingerprint footnote names: panel-visible window 1975–1978 emits only the `*, all`-style rollup rows; per-leaf series start in 1979. Cold-reader clarity issue, not a build issue.

(Background preserved.) The harvest collapsed pre-1981 to two fingerprints (1973–1978, 1979–1983); pre-1981 era-A rows are emitted with the discipline_fine values their fingerprint carries (e.g., 1973–1978 emits `Engineering, all` only; 1979 onward emits the leaves). The panel-visible window of the pre-leaf fingerprint is 1975–1978 because FY 1973–1974 are carved per §3(a). The panel reflects the data faithfully; the footnote clarifies what the cold reader sees when filtering to per-leaf series in the pre-1979 window.

### 14.5 Equipment series ships at `source_class='all_source'` only — **CONFIRMED W4 round (item 7)**

Methods-note paragraph at HD 2.4.i confirmed by maintainer. One-sentence add to `reconstructive_harmonization.md` §4 (the equipment-series paragraph): equipment rows ship at `source_class='all_source'` only; neither era-A Item 3 nor era-B Q14 carries a federal/nonfederal split at the field-level grain.

(Background preserved.) A consumer filtering `expenditure_type='r&d_equipment' AND source_class='federal'` gets zero rows by construction, which is correct but may surprise someone who expects symmetric handling between R&D and equipment.

### 14.6 1972 row in attribute parquet — **CONFIRMED W4 round (item 8)**

1972 excluded from `herd_panel_attributes.parquet`, consistent with main-panel exclusion per §3(a). Confirmed by maintainer in the W4 review round. No rows emit for 1972 in either harmonized parquet.

### 14.7 The "value column as INTEGER vs. DOUBLE" precision concern

Raw HERD CSVs carry `data` as text (per `etl/_load.py` line 437: `TRY_CAST(data AS DOUBLE) AS value`). The schema specifies `value DOUBLE` (kUSD_current, thousands of dollars). DuckDB DOUBLE is sufficient for HERD's value range (max institution-year R&D ~$2B, expressed in thousands so ~$2M kUSD, well within DOUBLE precision). No surface here — flagging only because the raw data is text and deposit consumers may ask. The personnel sibling uses DOUBLE for the same reason.

### 14.8 Personnel sibling `quality_flag` parity — deferred to post-W9–10

W4 round maintainer disposition: the personnel sibling does **not** retroactively gain a `quality_flag` column at this pass. Three reasons documented:

1. Retroactively updating the personnel sibling's shipped schema has audit-trail implications — `data/harmonized/herd_personnel.parquet` SHA-256 changes if the parquet is regenerated, and the reconciliation report headline (`validation/reports/personnel_table26_reconciliation.md`) may shift if the imputation flag changes how the standard-form filter interacts with imputed rows.
2. Personnel imputation patterns may differ from financial. Q15/Q16 microdata's `status` distribution was not characterized by the W4 spike (out of scope). A characterization spike on Q15/Q16 would be separate work, parallel to `etl/spikes/spike_herd_null_characterization.py` but on the personnel question set.
3. The W9–10 paired Zenodo deposit can document the cross-sibling asymmetry as a methodological choice, not a flaw — see §12 deposit README language.

Tracked as a post-W9–10 follow-up consideration. Does not gate HD 2.4 close.

### 14.9 W4 deferred investigations — tracked in `docs/hd_2_1_open_items.md`

Two methodologically interesting findings from the W4 NULL characterization spike that are not actionable at HD 2.4 but worth preserving for downstream attention. Per maintainer direction, tracked in the HERD-side parallel to PANEL_SKIPPER §8 — which is `docs/hd_2_1_open_items.md` (already carries pre-1981 variability, Q9/Q11 spelling drift, FY 2017 expansions, canonical-vs-raw label gap).

Two new entries added to `docs/hd_2_1_open_items.md` (W4 round, 2026-05-09):

1. **Status `u` in FY 2017** — 244 rows, non-Total columns only, all `data='0'`, FY24-Guide-undocumented. Methods-note drift footnote candidate. Preserved in raw and in the spike artifact. No HD 2.4 build impact (column='Total' is unaffected); appears in the panel only as the `quality_flag='unspecified_zero'` value on the rare rows that emit with this status. Investigation deferred — would need NCSES historical-codeset documentation to resolve the encoding.

2. **Q9/Q11 row-absence asymmetry at FY 2024** — 22.1% Q9-absent + Q11-present vs. 7.1% inverse at the (institution, discipline) grain. Federal R&D more concentrated than nonfederal. Methodologically interesting; worth a paragraph in the methods note's reconstruction-rule discussion eventually, framed as "the asymmetry is consistent with federal funding being concentrated in fewer disciplines than nonfederal funding for the marginal institution." Not for HD 2.4 to resolve — the era-B reconstruction rule already handles row-absence correctly per the W4 lock.

---

## 15. Cross-references

- Locked methodology: `docs/methods_notes/reconstructive_harmonization.md` (especially §4 era-B reconstruction rule, §6 what the deposit ships, §7 the (a)/(b)/(c) framing).
- Era-B reconstruction rule (consumer-facing YAML): `crosswalks/era_b_reconstruction_rule.yaml`.
- Question-level dispositions: `crosswalks/question_map.csv` (37 rows; raw-vs-canonical drift entries in rows 16, 26, 27).
- Discipline crosswalks: `crosswalks/discipline_coarse.csv` (18 rows), `crosswalks/discipline_fine.csv` (96 rows).
- Personnel sibling pattern: `etl/build_herd_personnel.py`, `etl/spikes/personnel_table26_verify.py`, `validation/reports/personnel_table26_reconciliation.md`, `docs/methods_notes/herd_personnel_README.md`.
- Era-A loader: `etl/_load.py` (`read_herd_csv`, `UNIFIED_COLS`, the era-A vs. era-B projection logic).
- HD 2.1.b residual analysis: `validation/reports/era_reconciliation_2008_2011.md` and three diagnostic reports.
- Open items: `docs/hd_2_1_open_items.md` (pre-1981 variability, Q9/Q11 spelling drift, FY 2017 expansions, canonical-vs-raw label gap).
- HD 2.1 scoping (predecessor): `docs/hd_2_1_scoping.md`.
- Repo conventions: CLAUDE.md §6 (Q1 HERD harmonization), §10 (kill criteria), §12 (repo conventions).
