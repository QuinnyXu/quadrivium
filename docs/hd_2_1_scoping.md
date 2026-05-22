# HD 2.1 Scoping Pass — Reconstructive Harmonization Crosswalk

**Status:** scoping draft. No code shipped from this document. Panel review the
scoping pass before HD 2.1's build phase begins.

**Authored by:** Skipper, 2026-05-01.

**Inputs grounded in:** `CLAUDE.md` §6 (HD 1.4 outcome locked 2026-04-30 as
*Reconstructive Harmonization*); `PANEL_SKIPPER.md` §7 Round 4b (HD 1.4
close-out) and §7 Round 5 (HD 1.5 per-year profile findings);
`docs/herd_question_structure_by_year.csv` (53-year question-structure
profile); `docs/source_documents/herd_fy24_guide.txt` (FY24 Guide, extracted
2026-04-29 via `pypdf==6.10.2`); `etl/spikes/spike_discipline_rename_2009_2010.py`
(throwaway spike, surfaced era-B fragmentation finding);
`seeds/research-seeds.md` 2026-04-30 (three-artifact deposit pattern; scoping-pass-
before-build process seed).

---

## 1. Deliverables list

HD 2.1 ships the **canonical question-mapping crosswalk + cross-question
summation rule + discipline-fine crosswalk** that reconstructs era-A-equivalent
field-level all-source totals from era-B's fragmented federal / nonfederal
source-class questions. The locked CLAUDE.md §6 framing is *Reconstructive
Harmonization*; this is the build phase that produces the canonical artifact.

The three-artifact pattern observed in HD 1.5 (compact summary +
long-format detail + prose narrative — `seeds/research-seeds.md`
2026-04-30) is applied where it fits.

| # | Artifact | Path | Pattern role | Notes |
|---|---|---|---|---|
| 1 | `crosswalks/question_map.csv` | `crosswalks/question_map.csv` | **long-format detail** | Maps `(era, year_range, question)` → `(era_role, contributes_to_all_source_total, allowed_columns, allowed_rows_pattern, decision_rationale)`. One row per era × question × era-role triple. The crosswalk *is* the summation rule expressed as data. See §2 and §5. |
| 2 | `crosswalks/discipline_fine.csv` | `crosswalks/discipline_fine.csv` | **long-format detail** | Maps `(era, year_range, raw_row_label)` → `(discipline_coarse, discipline_fine, decision_rationale, source_doc_anchor)`. Era-A row labels harvested from 1973–2009 row values; era-B row labels from 2010–2024 row values. ~80–110 rows total estimated; see §4. |
| 3 | `crosswalks/discipline_coarse.csv` | `crosswalks/discipline_coarse.csv` | **compact summary** | The 7-bucket stable rollup that survives 1973–2024 (Engineering / Life sciences / Physical sciences / Math & CS / Geosciences (Environmental sciences pre-2010) / Psychology / Social sciences / Non-S&E / Other sciences nec). One row per coarse bucket × era × year_range. Drives most charts. |
| 4 | `crosswalks/era_b_reconstruction_rule.yaml` | `crosswalks/era_b_reconstruction_rule.yaml` | **prose narrative (config-shaped)** | Human-readable expression of the **era-B-internal** reconstruction rule: which era-B questions contribute to `all_source_total(field, year)` *within era B*, which to `federal_only`, which are carve-outs (medical school, clinical trials), how rows aggregate. **Non-bridge clause (locked 2026-05-01):** the rule is era-B-internal — it reconstructs era-B all-source field-level totals from Q9+Q11 fragments for years 2010–2024. It does **not** bridge era-A direct totals to era-B reconstructed totals. The era boundary is characterized as **decomposed**, not bridged — see CLAUDE.md §6 HD 2.1.b outcome and the methods-note slot 2 four-bar decomposition (artifact #6). Filename renamed 2026-05-01 from `summation_rule.yaml` to remove the bridge connotation. Sibling to `question_map.csv`; the YAML is the methods-note prose source, the CSV is the machine-readable form. See §2 and §5 for why two artifacts here, not one. |
| 5 | `validation/reports/era_reconciliation_2008_2011.md` | `validation/reports/era_reconciliation_2008_2011.md` | **prose narrative** | Residual analysis at the era boundary. Per-discipline reconstructed-vs-published ratios for top 10 institutions, FY 2008/2009 vs. FY 2010/2011. See §3. Outcome (locked 2026-05-01): REOPEN; resolved at (b₂) decomposition sub-framing per CLAUDE.md §6 HD 2.1.b outcome. Three diagnostic reports ship as siblings (`*_diagnostic_1_institution_total.md`, `*_diagnostic_2_q5_share.md`, `*_diagnostic_3_growth.md`) and become methods-note appendices E/F/G. |
| 6 | `docs/methods_notes/reconstructive_harmonization.md` | `docs/methods_notes/reconstructive_harmonization.md` | **prose narrative** | Methods-note section that frames the contribution for the deposit reader. **Filename retained per (β) lock 2026-05-01** — Reconstructive Harmonization survives as the program's methodological owned term (CLAUDE.md §1, redefined to mean the *methodological signature*: reconstruct + decompose + publish-both). **Opening anchor:** the question-count cliff chart (slot 1, problem-viz). **Contribution slot 2:** the four-bar decomposition (real growth ~26% / definitional change ~6–8pp incl. Q5 ~8pp / cohort expansion 690→896 / bounded unmeasurable residual) — *contribution-decomposition*, not contribution-equation, per the methods-note voice update locked 2026-05-01 (CLAUDE.md §6). **Validation receipt slot 3:** the residual analysis result and the three diagnostics. Cites artifacts 1–5 by path; lifts the FY24 Guide language from `docs/source_documents/herd_fy24_guide.txt` for each rule. This is the document the dean / journalist reads. |

**Where the three-artifact pattern doesn't fit:**

- The **era-B reconstruction rule** itself is two artifacts (`question_map.csv` +
  `era_b_reconstruction_rule.yaml`, renamed 2026-05-01 from `summation_rule.yaml`), not three. *Why:* the rule's "compact summary" is
  the YAML — humans read the rule as prose, machines consume the CSV. Adding a
  third compact-CSV artifact would just restate the YAML in tabular form
  without earning its keep. Pattern doesn't generalize when the prose
  *is* the compact form.
- The **discipline-coarse crosswalk** stands alone (no long-format
  sibling) because the coarse taxonomy *is* the compact form by
  construction (~7 rows × era boundary). Building a long-format detail
  here would invert the asymmetry the pattern is designed for.
- The **residual analysis report** is prose-only. The underlying
  reconstructed values live in `data/harmonized/herd_panel.parquet`
  (which HD 2.4 builds, not HD 2.1) — duplicating them as a long-format
  CSV here would create a stale-snapshot risk. Pattern requires the
  long-format substrate to live somewhere durable; here it lives in the
  panel parquet itself.

---

## 2. The summation rule — first draft

**Verification source:** `docs/source_documents/herd_fy24_guide.txt`, the
extracted FY24 Guide PDF. Sections cited inline. The Guide IS in the repo
(`data/raw/herd/Guide To Herd Data Files FY24.pdf`, extracted to text by
`etl/extract_herd_fy24_guide.py`); §2 below cites page-anchored extracts
verbatim, not from memory.

### 2.1 First-draft rule

For era B (2010–2024), the reconstructed era-A-equivalent field-level
all-source total is:

```
all_source_total(field, year) =
    federal_total(field, year, all-agencies)        -- from Question 9
  + nonfederal_total(field, year, all-sources)      -- from Question 11
```

In raw `(question, column)` terms:

```
all_source_total(field, year) =
    SUM(value WHERE question='Federal expenditures by field and agency'
              AND row=field AND column='Total')
  + SUM(value WHERE question='Nonfederal expenditures by field and source'
              AND row=field AND column='Total')
```

The era-A direct value (1973–2009) is:

```
all_source_total(field, year) =
    value WHERE question='Expenditures by S&E field'
          AND row=field AND column='Total'
```

### 2.2 FY24 Guide language anchoring the rule

The FY24 Guide describes the era-B questionnaire structure as follows (verbatim
from `docs/source_documents/herd_fy24_guide.txt`, pages 5–6):

> "Question 9A–K requested that institutions report the amount of their R&D
> expenditures by field that was funded by federal agency sources (i.e., the
> U.S. Departments of Agriculture, Defense, Energy, and Health and Human
> Services; the National Aeronautics and Space Administration [NASA]; NSF;
> and all other federal agencies)."

> "Question 11A–K requested that institutions report the amount of their R&D
> expenditures by field that were funded by nonfederal agency sources (i.e.,
> state and local governments, businesses, nonprofit organizations,
> institutional funds, and other)."

Question 9 totals are the era-B source for federal field-level R&D; Question 11
totals are the era-B source for nonfederal field-level R&D. Together they
reconstruct era-A's single `'Expenditures by S&E field'` total. The Guide
does not state this reconstruction equation explicitly — that is HD 2.1's
contribution, and it is the methods-note headline.

### 2.3 Wrinkles surfaced — Vision-level methodological calls

#### W1. Capitalized R&D equipment — Question 14 (era B) vs. Item 3 (era A)

FY24 Guide page 6 (era B):

> "Question 14A–K requested that institutions report the portion of their
> federal and nonfederal R&D expenditures by field that went toward the
> purchase of capitalized R&D equipment."

FY24 Guide page 21 (era A): Item 3 ("Current Fund Research Equipment
Expenditures by Field") covers FY 1981–2009.

**Wrinkle:** Question 14 is a **subset** of Question 9+11, not a separate
component. Question 14 reports the *equipment portion* of the same R&D
expenditures. Including Question 14 in the summation rule would
double-count.

**Decision — locked at panel review (2026-05-01):** Question 14 is
**out** of the all-source reconstruction rule. It maps to a separate
`expenditure_type = 'r&d_equipment'` row in the harmonized panel,
parallel to era-A Item 3. The summation rule applies to total R&D, not
to equipment R&D.

#### W2. Medical school R&D (Question 4) and clinical trials (Question 5)

FY24 Guide page 5 (era B):

> "Question 4 asked how much of the total R&D expenditures was expended for
> R&D projects in the institution's medical school."
>
> "Question 5 asked how much of the total R&D expenditures was expended for
> clinical trial R&D."

**Wrinkle:** Both are **carve-outs** from total R&D ("how much *of* the
total"), not separate components. Including them in the summation rule
would double-count. They map to attribute flags (e.g., `med_school_share`,
`clinical_trials_share`) on the institution-year, not to separate rows.

**Decision — locked at panel review (2026-05-01):** Out of the
all-source reconstruction rule. They travel with the panel as
**institution-year attribute flags** (e.g., `med_school_share`,
`clinical_trials_share` columns at the institution-year grain), not as
parallel rows. The era-B fragmentation finding from
`etl/spikes/spike_discipline_rename_2009_2010.py` called these out as
"capitalization/clinical-trials variants" — verified here against the
Guide as carve-outs, not components.

#### W3. ARRA (American Recovery and Reinvestment Act) funds 2009–2014

FY24 Guide page 4:

> "In FY 2015, the question asking for information about federally financed
> R&D expenditures from American Recovery and Reinvestment Act (ARRA) funds
> was removed, and all subsequent questions were renumbered."

**Wrinkle:** ARRA funds are a federal sub-stream. The Guide says they
were a separate question removed in FY 2015. The risk is that ARRA was
either (a) double-counted in Question 9 federal totals (then ARRA-as-
separate-question is a within-federal breakdown, harmless to the
all-source rule), or (b) reported separately and not rolled into Question 9
(then federal totals 2010–2014 are understated unless we explicitly add
ARRA). The Guide's "removed, and all subsequent questions were
renumbered" phrasing strongly suggests (a) — ARRA was a within-federal
detail question, not a parallel federal stream. Verification: when the
spike or HD 1.5 profile of 2010–2014 question inventory is checked
against post-2015, the question-count reduction in 2015 should equal
1 (the ARRA question removal); §3 residual analysis confirms by
checking whether 2010–2014 federal totals match published NSF aggregates
without an ARRA add.

**Decision — locked at panel review (2026-05-01):** ARRA is
within-federal (case a), not a parallel component. **Build under
case-a assumption.** No ARRA add to the summation rule. The §3
residual analysis is the empirical check; if residuals reveal case-b
behavior on a non-pre-documented bucket, the residual reopen path
(§3.3) fires and the rule revisits ARRA. Locked as build assumption,
residual-reopen as the kill condition.

#### W4. Era-A `Federal` vs. era-B agency-summed Federal

`PANEL_SKIPPER.md` §3 hidden edge 4 already flagged this: era A has a
rolled-up `column = 'Federal'`; era B replaces it with seven agency
columns (`DOD`, `DOE`, `HHS`, `NASA`, `NSF`, `USDA`, `Other agencies`)
plus `Total`. **For the all-source rule we use `column = 'Total'` from
both Questions 9 and 11**, which sidesteps the agency-rollup question
entirely. The agency-rollup matters for federal-only time series
(separate methods-note section), not for all-source reconstruction.

#### W5. Era-A fields without era-B counterparts (or vice versa)

The spike (`etl/spikes/spike_discipline_rename_2009_2010.py`) flagged
seven 2009 leaves as unmapped in its best-effort RENAME map. **HD 2.1.e
resolved all seven as mappable** against the era-B harvest (see §4.2);
the spike's heuristic was tuned for engineering-style label expansions
and missed the social/physical-sciences expansion patterns. The
following are the residual W5-class cases that genuinely cross the era
boundary with definitional drift or have no era-A counterpart:

- **W5 canonical drift cell:** `Environmental sciences` (era A) →
  `Geosciences, atmospheric sciences, and ocean sciences` (era B).
  Definitional rename + scope expansion (Guide page 18 Item 2 lines
  1430–1434 vs. INVENTORY §5.2). Pre-doc'd in §3.6 as the **one**
  canonical drift cell in the residual gate. Methods note carries the
  W5 footnote inline.
- **Genuinely era-B-only fields** (no era-A counterpart at the fine-leaf
  grain): the four FY 2017 micro-expansions surfaced at HD 2.1.d —
  `Engineering, industrial and manufacturing`, `Life sciences, natural
  resources and conservation`, `Physical sciences, materials science`,
  `Social sciences, anthropology`. First-positive-year is 2016 in the
  era-B harvest. Plus the ARRA within-federal exclusion (W3, removed
  FY 2015). These are flagged for per-row decision-rationale in
  `crosswalks/discipline_fine.csv` and for the methods-note's "fields
  whose definition shifts across the era boundary" subsection.

The seven leaves originally listed here as "unmapped in spike RENAME"
(physical-sciences chemistry/physics/other; social-sciences economics/
political-science/sociology/other) are no longer W5-class — they are
mapped rows in `crosswalks/discipline_fine.csv` with explicit
heuristic-miss rationale.

#### W6. Survey-population scope shift at 2010

FY24 Guide page 4: era A's population threshold was "$150,000 or more in
S&E R&D"; era B's became "$150,000 in separately budgeted R&D
expenditures during the institution's fiscal year, [and] geographically
separate campuses headed by a president or chancellor." The reporting
universe shifted at the era boundary (711 → 744 institutions FY 2009 →
FY 2010 per Guide page 4).

**Implication for the summation rule:** the rule itself doesn't change,
but a perfect reconstruction match across the boundary is impossible
because the underlying institution set differs. §3 residual analysis
filters to institutions present in both 2009 and 2010 to control for
this.

### 2.4 No source-doc blockers

The FY24 Guide is in the repo and extracted. The FY 2009 Methodology
Report referenced in Guide page 14 (FY 2009 Pilot Survey details) is
**not** in the repo and is "available upon request from the NCSES
project manager." This is **not a blocker for HD 2.1** — the FY24 Guide
covers both era-A and era-B questionnaires in section 2.1 (pages 13–22),
which is sufficient for the summation rule. Flag for Q2 if methodology-
report-level detail becomes load-bearing for a downstream piece.

---

## 3. Residual analysis plan

### 3.1 Sample

- **Years:** FY 2008, FY 2009, FY 2010, FY 2011 (two pre-boundary, two
  post-boundary).
- **Institutions:** top 10 by FY 2008 total R&D expenditures (proxy for
  largest reporters; published in NSF FY 2008 InfoBriefs and recoverable
  from `crosswalks/institution_id.csv` once HD 1.7 has authored it). If
  HD 1.7's institution-ID crosswalk isn't shipped before HD 2.1 build,
  fall back to the top-10 by FY 2009 reported `row='All', column='Total'`
  in our own loader output (`read_herd_csv(2009)`) — same population
  modulo trivial rank shifts.
- **Disciplines:** all 7 coarse buckets per the stable rollup
  (Engineering / Life sciences / Physical sciences / Math & CS /
  Geosciences (era B) ≡ Environmental sciences (era A) / Psychology /
  Social sciences). Other sciences nec and Non-S&E sit outside the
  primary 7 and are reported as supporting cells, not gating cells.

**Test shape — locked at panel review (2026-05-01):** top-10
institutions × 7 coarse buckets, year-pair 2009→2010. Engineering-coarse-
only single-cell pre-check is **superseded** by this broader shape;
Vision-broad won the call on test breadth.

### 3.2 Metric

For each (institution, discipline, year) cell:

```
era_a_value(disc, 2008) = Item 2 'Total' value (era-A direct read)
era_b_reconstructed_value(disc, 2010) =
    Q9 'Total' value(disc) + Q11 'Total' value(disc)
                                                (era-B reconstructed)

residual_pct(disc, year_pair) =
    (era_a_value(disc, 2009) - era_b_reconstructed(disc, 2010))
    / era_a_value(disc, 2009)
```

### 3.3 Acceptable magnitude — locked thresholds (2026-05-01)

**Locked at panel review:**

- **Reopen trigger A (bucket-level):** median residual >5% on any of
  the 7 coarse buckets across the top-10 institutions × year-pair
  2009→2010. *Median, not mean*: robust to a single institution's
  reporting quirk.
- **Reopen trigger B (cell-level):** any single (institution × bucket)
  cell with residual >15% in absolute value.
- **Pre-documented exception clause:** a cell or bucket pre-listed in
  §3.6 ("Pre-documented expected-residual cells") that fails a
  threshold is **footnoted as W5-class definitional drift, not a rule
  failure.** A non-pre-documented cell that fails reopens. The
  pre-doc list is fixed *before* the test runs; cells discovered to
  drift after the fact do not retroactively earn the exception.
- **Methods-note language under each outcome:**
  - All buckets within band, no pre-doc-class footnotes triggered:
    "we validated reconstruction at the institution-year level;
    residuals are within reporting noise."
  - Pre-doc-class buckets footnoted, all others within band:
    "validated reconstruction with documented definitional-drift
    footnotes for [bucket(s)]." Methods-note carries the W5 footnote
    text inline.
  - Reopen trigger fires on a non-pre-doc bucket / cell: HD 2.1.b
    halts; back to the panel. Either (a) the summation rule is missing
    a component (e.g., ARRA was case-b not case-a), (b) the era-B
    fragmentation has more than 2 components, or (c) the pre-doc list
    is incomplete and a previously-unflagged bucket carries
    definitional drift the scoping pass missed.

**Residual band sourcing — Path B locked (2026-05-01).** The 5% / 15%
magnitudes are **empirically/descriptively grounded** — chosen against
the practitioner literature on cross-survey reconciliation tolerances
and our own reporting-noise priors. HD 2.1.b includes a **1-half-day
external-referent search budget** to surface NSF / NCSES / ASEE
published tolerance surfaces (e.g., NSF InfoBrief reconciliation
appendices, NCSES Methodology Reports' published reconciliation
tables, ASEE *Engineering by the Numbers* method notes). If a
published tolerance surface is found, switch to **Path A**
(authority-grounded thresholds) and log the override in
`seeds/overrides.md`. If none surfaces within the half-day budget,
Path B holds and the methods note carries a footnote: "thresholds set
descriptively against practitioner reporting-noise priors; no
published NSF/NCSES tolerance surface found at HD 2.1.b external
search."

### 3.4 What a non-zero residual tells us

Five non-mutually-exclusive causes, ranked by likelihood:

1. **Population-scope shift at 2010 (W6).** Some institutions enter or
   leave the universe. *Mitigation:* filter to institutions present in
   both FY 2009 and FY 2010.
2. **Definition drift in carve-outs.** FY24 Guide page 14: "expenditures
   for clinical trials and research training grants were explicitly
   requested on the HERD survey but not the Academic R&D Expenditures
   Survey." Era B's totals include items era A's totals didn't. This
   is a real (not noise) residual, traceable, footnote-worthy.
3. **ARRA timing / federal-stream accounting (W3).** Confirmed only by
   running 2010–2014 reconciliation against published NSF federal
   totals. If the rule reconstructs federal totals cleanly without an
   ARRA add, case (a) holds.
4. **Field-definition drift across the boundary (W5).** "Environmental
   sciences" vs. "Geosciences, atmospheric sciences, and ocean sciences"
   is the loudest example. *Mitigation:* compare at the coarse-bucket
   level first; only drill into fines once coarse buckets reconcile.
5. **Imputation differences between eras.** Guide page 14 (era A) vs.
   pages 5–6 (era B) describe different imputation procedures; some
   small residual is irreducible.

### 3.5 Output

`validation/reports/era_reconciliation_2008_2011.md` — prose narrative
plus a residual table:

| discipline_coarse | era_a_2009_kusd | era_b_recon_2010_kusd | residual_pct | likely_cause | pre_doc_class |

The `pre_doc_class` column tags cells that match the §3.6 pre-doc list;
the residual report writes those cells as W5-class drift footnotes
rather than rule failures.

This is **not** a Great Expectations suite (HD 2.6 owns those). This is
a one-time methodological check that gates the methods-note framing.

### 3.6 Pre-documented expected-residual cells

The maintainer's tightening (locked 2026-05-01): name the cells where
the residual test is *expected* to fail thresholds because of known
definitional drift across the era boundary. **A pre-documented cell that
fails a threshold is footnoted as W5-class drift, not a rule failure.
A non-pre-documented cell that fails reopens HD 2.1.b.**

The list is fixed at scoping; cells discovered to drift after the test
runs do not retroactively earn the exception.

| coarse_bucket (era A → era B) | year_pair | expected_drift_cause | source_anchor | priors |
|---|---|---|---|---|
| **Environmental sciences → Geosciences, atmospheric sciences, and ocean sciences** | 2009→2010 | Definitional rename + scope expansion. Era A's `Environmental sciences` carried `1431 Atmospheric sciences`, `1432 Earth sciences`, `1433 Oceanography`, `1434 Other` (Guide page 18 Item 2 lines 1430–1434). Era B's `Geosciences, atmospheric sciences, and ocean sciences` (INVENTORY §5.2) is a wider umbrella — earth sciences and atmospheric/ocean sciences are unified under one fine-rolled label, and the umbrella may absorb fields era A reported under Other or Life sciences. The rename is **not** label-only; the field-content footprint shifts. | FY24 Guide page 18 Item 2 lines 1430–1434; INVENTORY §5.2 era-A→era-B rename map (`Environmental sciences` → `Geosciences, atmospheric sciences, and ocean sciences`). | **Expect bucket-level residual >5%.** This is the canonical W5 example named throughout the scoping doc. |

**Verified-clean buckets at the era boundary (NOT pre-documented as drift):**

| coarse_bucket | rationale | source_anchor |
|---|---|---|
| **Engineering** | INVENTORY §5.2 lists three era-A→era-B engineering renames (`Engineering, aeronautical and astronautical` → `Engineering, aerospace, aeronautical, and astronautical`; `Engineering, electrical` → `Engineering, electrical, electronic, and communications`; `Engineering, bioengineering and biomedical` → `Engineering, bioengineering and biomedical engineering`) — all label-level, no scope shift. The fine-leaf addition `Engineering, industrial and manufacturing` arrives FY 2017, **not** at the 2010 boundary, so it does not contaminate the 2009→2010 pair. Coarse total expected within band. | INVENTORY §5.2 row 2010-2016; INVENTORY §5.2 row 2017-2024; FY24 Guide page 18 Item 2 lines 1410–1418. |
| **Life sciences** | Era A carries 1450 Life sciences (total) with leaves 1451 Agricultural / 1452 Biological / 1453 Medical / 1454 Other. Era B 2010 renames `Life sciences, biological sciences` → `Life sciences, biological and biomedical sciences` and `Life sciences, medical sciences` → `Life sciences, health sciences` — label-level. The `Life sciences, natural resources and conservation` addition arrives FY 2017, not at the 2010 boundary. Coarse total expected within band at 2009→2010. | INVENTORY §5.2 row 2010-2016; INVENTORY §5.2 row 2017-2024; FY24 Guide page 19 Item 2 lines 1450–1454. |
| **Math & CS** | Era A carries 1441 Mathematical sciences + 1442 Computer sciences as separate leaves rolling to a Math&CS coarse. Era B renames `Computer sciences` → `Computer and information sciences` and `Mathematical sciences` → `Mathematics and statistics`. Both renames are label-level at the 2010 boundary. CS reorganized further inside era B (per maintainer's note), but the era-boundary itself is clean. Coarse total expected within band. | INVENTORY §5.2 row 2010-2016; FY24 Guide page 18 Item 2 lines 1441–1442. |
| **Physical sciences** | Era A carries 1420 Physical sciences (total) with leaves 1421 Astronomy / 1422 Chemistry / 1423 Physics / 1424 Other. The three Physical sciences leaves originally flagged by the HD 1.4 spike RENAME heuristic as unmapped (chemistry, physics, other) were resolved at HD 2.1.e as identical-label era-B counterparts — heuristic miss, not a real boundary trigger (§4.2). Coarse total expected within band; the era-B-only `Physical sciences, materials science` (FY 2017+) is a fine-leaf addition that does not contaminate the 2009→2010 coarse comparison. | FY24 Guide page 18 Item 2 lines 1420–1424; §4.2 heuristic-miss resolution; INVENTORY §5.2. |
| **Psychology** | Resolved verified-clean at HD 2.1.d (2026-05-01). Era B preserves `Psychology, all` as a top-level coarse bucket present in both Q9 and Q11 every year 2010–2024 (`crosswalks/_harvest/era_b_row_labels.csv`). Era-A `1460 Psychology (total)` maps cleanly to era-B `Psychology, all` at the coarse level. No merger into Social sciences. Coarse total expected within band. | `crosswalks/_harvest/era_b_row_labels.csv` rows for `Psychology, all` (present_in_q9=1, present_in_q11=1, all year-buckets); INVENTORY §5.2 silence on Psychology rename (negative confirmation); FY24 Guide page 19 Item 2 line 1460. |
| **Social sciences** | Resolved verified-clean at HD 2.1.d (2026-05-01). Era B preserves `Social sciences, all` as a top-level coarse bucket; mirror of the Psychology resolution. Era-A 1470-series Social sciences leaves (economics, political science, sociology, other) map to era-B Social sciences leaves (economics, political science and government, sociology demography and population studies, other) — label drift, scope-preserving. Coarse total expected within band. | `crosswalks/_harvest/era_b_row_labels.csv` rows for `Social sciences, *`; FY24 Guide page 19 Item 2 lines 1470–1474. |

**Cells outside the gating 7-bucket × top-10 frame:**

- **Other sciences nec** and **Non-S&E** are reported in the residual
  table as supporting cells but are not gating cells. Other sciences
  nec is era A's catch-all (Guide page 19 Item 2 line 1480); HD 2.1.d
  resolved it as preserved at era-B `Other sciences, all` — directly
  mappable, not era-B-only. Non-S&E only enters the panel
  in 2003, exists in era A 2003–2009 and era B 2010+, and may carry
  definitional differences orthogonal to the era boundary; flagging
  needs separate scoping that HD 2.1 does not own.

**Pre-doc list summary for HD 2.1.b residual report:**
1. Environmental → Geosciences (W5 canonical) — **expect drift, footnote**.

Resolution at HD 2.1.d (2026-05-01): the era-B row-label harvest
confirmed both `Psychology, all` and `Social sciences, all` are
preserved as top-level coarse buckets across all years 2010–2024 in
both Q9 and Q11. Both former conditional pre-doc rows drop and those
cells are regular gating cells in the HD 2.1.b residual test. The
canonical drift cell list is **one** entry: Environmental→Geosciences.

---

## 4. Discipline-fine crosswalk scope

### 4.1 Row-count target

`crosswalks/discipline_fine.csv` will carry approximately 80–110 rows.

- **Era A leaves and rollups, 1973–2009:** ~34 row labels per the HD 1.4
  cell-count anchor (CLAUDE.md §6 / locked 2026-04-29). The fine
  taxonomy is stable across most of era A; sub-period decision_rationale
  rows are added only where the source CSV's row labels actually
  differ (e.g., bioengineering arrives in 1997 per Guide page 14;
  metallurgical+materials arrives in 1990 per Guide page 14).
- **Era B leaves and rollups, 2010–2024:** ~30–35 row labels per the
  spike's 2010 inventory. Sub-period rows added at FY 2017 (industrial-
  and-manufacturing engineering, life-sciences-natural-resources-and-
  conservation per `INVENTORY.md` §6) and FY 2020 (any further
  reorganizations).
- **Year-range column:** each row is keyed by `(era, year_range_start,
  year_range_end, raw_row_label)`. A label that's stable 1980–2009 is
  one row, not 30; a label that exists 1990–2009 only is one row with
  the appropriate range.

### 4.2 The seven 2009 leaves initially flagged as unmapped — heuristic miss, resolved at HD 2.1.e

The spike's RENAME map (`etl/spikes/spike_discipline_rename_2009_2010.py`)
flagged these era-A leaves as unmapped under its best-effort heuristic
(cross-checked against FY24 Guide page 18 Item 2). The HD 2.1.e build
phase row-by-row authored against the era-B harvest
(`crosswalks/_harvest/era_b_row_labels.csv`) and **resolved all seven
as mappable** — three to era-B labels identical to era-A, four to era-B
labels with scope-preserving expansions.

The HD 1.4 spike's RENAME heuristic was tuned for engineering-style
label expansions and missed the social/physical-sciences expansion
patterns; HD 2.1.e row-by-row authoring against the era-B harvest
resolved all seven.

| # | Era-A 2009 leaf | Era-A line | Era-B counterpart | Mapping type |
|---|---|---|---|---|
| 1 | Physical sciences, chemistry | 1422 | Physical sciences, chemistry | Identical label |
| 2 | Physical sciences, physics | 1423 | Physical sciences, physics | Identical label |
| 3 | Physical sciences, other | 1424 | Physical sciences, other | Identical label |
| 4 | Social sciences, economics | 1471 | Social sciences, economics | Identical label |
| 5 | Social sciences, political science | 1472 | Social sciences, political science and government | Label expansion (government/public-administration coverage made explicit; scope-preserving) |
| 6 | Social sciences, sociology | 1473 | Social sciences, sociology, demography, and population studies | Label expansion (demography and population studies coverage made explicit; scope-preserving) |
| 7 | Social sciences, other | 1474 | Social sciences, other | Identical label |

The two "likely unmapped" rollups previously flagged here also resolved
at the HD 2.1.d era-B row-label harvest:

- **Psychology, all** (era-A line 1460) — era B preserves an identical
  top-level coarse bucket (`Psychology, all`) present in both Q9 and Q11
  every year 2010–2024. Verified-clean.
- **Other sciences nec** (era-A line 1480) — era B preserves
  `Other sciences, all`. Maps directly; sits outside the gating 7-bucket
  frame as a supporting cell.

**Where the genuine era-B-only fine-leaf additions live.** The cases
that *truly* lack era-A counterparts are the four FY 2017 micro-
expansions surfaced at HD 2.1.d:

1. `Engineering, industrial and manufacturing` (FY 2017+, FY24 Guide page 4 FY 2016 revisions)
2. `Life sciences, natural resources and conservation` (FY 2017+, INVENTORY §5.2)
3. `Physical sciences, materials science` (FY 2017+, undocumented per `docs/hd_2_1_open_items.md` FY 2017 expansion entry)
4. `Social sciences, anthropology` (FY 2017+, era-A reported under `Social sciences, other`; undocumented per `docs/hd_2_1_open_items.md`)

Plus the **ARRA exclusion** (W3, removed FY 2015 per FY24 Guide page 4)
as a within-federal sub-stream that does not roll into the all-source
rule. These are the cells that genuinely lack era-A counterparts; the
seven listed at the top of this section were heuristic misses, not real
boundary triggers.

### 4.3 Handling genuinely era-B-only fields (FY 2017 micro-expansions, ARRA exclusion)

Per CLAUDE.md §6 schema lock and PANEL_SKIPPER §7 Round 2 verdict (Vision
locked 2026-04-29): **the crosswalk is the audit trail, not a hidden
global rule.** The fields that genuinely lack an era-A counterpart (the
four FY 2017 micro-expansions surfaced at HD 2.1.d, plus the ARRA
within-federal exclusion) get a row in `crosswalks/discipline_fine.csv`
with:

- `era = 'B'`, `year_range = '2016–2024'` (FY 2017 micro-expansions
  first appear with positive values in 2016).
- `raw_row_label = 'Physical sciences, materials science'` (or similar,
  exact string from era-B harvest).
- `discipline_coarse = 'Physical sciences'`.
- `discipline_fine = 'Physical sciences, materials science'` (era-B native).
- `era_b_counterpart` left blank (the row IS the era-B record).
- `decision_rationale` per row, anchored to FY24 Guide page 4 (FY 2016
  revisions) and the era-B harvest first-positive-year, with explicit
  note that the field has no era-A counterpart at the fine-leaf grain.

This is a **finding to surface**, not a row to force. The methods note's
"fields reorganized across the era boundary" subsection lists the four
FY 2017 micro-expansions plus the ARRA exclusion with rationale — the
subsection IS the contribution for these fields, not a defect.

The seven era-A leaves originally flagged as unmapped (§4.2) get rows in
the era-A block of the crosswalk with `era_b_counterpart` populated to
their resolved era-B label per HD 2.1.e. They are not "unmapped findings"
— they are mapped rows.

### 4.4 Reused vs. new

- **Reuse:** the spike's RENAME dict is the seed for the engineering
  and life-sciences chunks of the crosswalk. About 17 rows lift directly
  with rationale added.
- **Resolved at HD 2.1.e:** the seven era-A leaves §4.2 listed as
  unmapped (heuristic miss) plus the two likely unmapped rollups (Psychology
  and Other sciences nec) — all mapped against the era-B harvest with
  inline rationale.
- **New (genuinely era-B-only):** the four FY 2017 micro-expansions
  (industrial-and-manufacturing engineering, life-sciences-natural-
  resources-and-conservation, physical-sciences-materials-science,
  social-sciences-anthropology); the ARRA within-federal exclusion (W3);
  W5 canonical drift cell (Environmental→Geosciences) handling; year-range
  edge labels for Q9/Q11 spelling drift (Oxford-comma vs. no-Oxford-
  comma renderings, 2010–2015 / 2016–2023 fingerprints).

---

## 5. Decision rationale discipline

### 5.1 Per-row rationale lives inline in the CSV

Per CLAUDE.md §6 ("crosswalks are most of the methods note") and
`PANEL_SKIPPER.md` §7 Round 2 (locked 2026-04-29):

- `crosswalks/discipline_fine.csv` carries `decision_rationale` as a
  CSV column. One row, one rationale sentence. The crosswalk file
  itself is methods-note in seed form.
- `crosswalks/discipline_coarse.csv` same pattern.

### 5.2 Per-rule rationale for the summation rule lives in YAML

The summation rule is **not** a per-row decision; it's a one-rule-many-
applications structure. Inline `decision_rationale` per `question_map.csv`
row covers the question-level decisions ("Question 14 is excluded
because it is a subset of Q9+Q11, not a component"), but the rule's
overall narrative — *why we sum federal+nonfederal, why we exclude
carve-outs, what the FY24 Guide language anchors it to* — belongs in
prose.

**Proposed structure:**

- `crosswalks/question_map.csv` — one row per (era, year_range,
  question), columns: `era_role` (era-A direct / era-B all-source-
  component / era-B subset-of-Q9+Q11 / era-B carve-out / era-B
  attribute), `contributes_to_all_source_total` (boolean), `column_used`
  (e.g., `'Total'`), `decision_rationale` (one-sentence inline).
- `crosswalks/era_b_reconstruction_rule.yaml` (renamed 2026-05-01 from
  `summation_rule.yaml`) — sibling YAML carrying the rule's
  overall narrative, FY24 Guide page anchors, the four wrinkles (W1–W4)
  with the proposed disposition for each, and the **non-bridge clause**
  (locked 2026-05-01): the rule is era-B-internal — it reconstructs era-B
  all-source field-level totals from Q9+Q11 fragments for years 2010–2024;
  it does not bridge era-A direct totals to era-B reconstructed totals;
  the era boundary is characterized as decomposed (per CLAUDE.md §6
  HD 2.1.b outcome and methods-note artifact #6 slot 2 four-bar
  decomposition). The YAML is read by `etl/build_herd_panel.py` (HD 2.4) to
  parameterize the summation; the YAML is also lifted verbatim into
  `docs/methods_notes/reconstructive_harmonization.md` (artifact #6) as
  Appendix B. **One source of truth for the rule, two
  consumers** — code and methods note.

### 5.3 Methods-note voice — locked at panel review (2026-05-01)

**The methods-note body translates the YAML into prose; it does not
lift the YAML verbatim.** Voice locked at panel review:

- **Prose body**: human-readable narrative of the era-B reconstruction rule,
  templated regeneration from `era_b_reconstruction_rule.yaml` (the YAML stays
  the source of truth, the prose is generated *from* the YAML during
  the build).
- **Inline pseudo-code**: lifts the equation form already drafted at
  scoping §2.1 (the `all_source_total(field, year) = federal_total +
  nonfederal_total` block). One inline equation per rule wrinkle, in
  the body.
- **Appendix B**: the verbatim `era_b_reconstruction_rule.yaml` (renamed
  2026-05-01 from `summation_rule.yaml`) for readers who
  want machine-readable form. Auto-generated wrap.

**Why this voice and not verbatim-YAML body:** verbatim YAML in the
body asks the dean / journalist to read configuration syntax. Prose
body + equation form keeps the door open to those readers; YAML in
Appendix B keeps the door open to the cold-reader engineer who wants
to verify the build code consumes the same rule the prose describes.
Same one-source-of-truth discipline as the YAML-only proposal — the
prose is templated *from* the YAML, drift between body and code is
mechanically prevented at build time.

**Why YAML at all (vs. methods-note md alone):** if the rule lives
only in `docs/methods_notes/reconstructive_harmonization.md`, the
build pipeline either (a) hard-codes the rule in Python (drift risk
between methods-note prose and build code) or (b) parses prose
markdown for parameters (fragile). YAML is the structural form the
build code consumes; the methods-note md is generated *from* the YAML
during the build. The new voice (prose body + Appendix B YAML)
preserves this one-source-of-truth property — the prose is the
templated translation, not the source.

**Cost:** voice change adds **0.25 half-days** to HD 2.1.i (now 1.25
half-days, was 1.0). Updated in §7 estimate table.

### 5.4 Methods-note appendix — updated for §5.3 voice

The deposit's `docs/methods_notes/reconstructive_harmonization.md` (artifact #6)
opens with the rule's prose narrative (templated from the YAML, with
inline pseudo-code per §5.3), then includes:

- **Appendix A** — auto-generated from `crosswalks/question_map.csv`,
  table of every question and its era-role.
- **Appendix B** — verbatim `crosswalks/era_b_reconstruction_rule.yaml` for the
  cold-reader engineer. *Voice change 2026-05-01: YAML moves from
  body-verbatim to Appendix B; prose body translates the rule.* *Filename
  rename 2026-05-01: `summation_rule.yaml` → `era_b_reconstruction_rule.yaml`
  per (β) lock; the YAML carries the non-bridge clause in its preamble.*
- **Appendix C** — auto-generated from `crosswalks/discipline_fine.csv`,
  the per-row rationale table.
- **Appendix D** — the residual analysis report (`validation/reports/
  era_reconciliation_2008_2011.md`) summarized.

The methods note IS the crosswalks' inline rationale, expanded with
narrative framing.

---

## 6. Threshold ladder application

CLAUDE.md §6 ("HD 1.4 kill condition — threshold ladder") locks the
ladder against the cell count of distinct 2009 row-labels in
`question = 'Expenditures by S&E field'`:

> Anchored to that N; recalibrate proportionally if HD 1.4 reports N
> outside [30, 40].

The HD 1.4 spike verified N = 34 (24 leaves + 9 rollups + 1 grand
'All') for 2009.

### 6.1 Does era-B reconstruction change the cell population?

**Mostly no, with one nuance.**

The ladder fires against **per-discipline reconstructed ratios** —
era-A `value(disc, 2009)` vs. reconstructed era-B `value(disc, 2010)`,
one ratio per discipline. The unit is the **2009 cell**, not the
era-B cell. Because the 2009 anchor is the ratio's denominator and the
2009 row labels are the ratio's keys, the cell count remains 34 (24
leaves + 9 rollups + 1 grand 'All') for any reconstruction-based
ratio whose denominator is era-A 2009.

**The nuance — heuristic-miss correction (2026-05-01).** The HD 1.4
spike's RENAME heuristic flagged seven era-A leaves as unmapped, which
under a literal reading of the threshold ladder ("any 2009 cell with
no 2010 mapping or many-to-one collapse") would have tripped the
structural verdict on no-mapping grounds. **HD 2.1.e build resolved
all seven as mappable** (§4.2): three to identical era-B labels, four
to scope-preserving label expansions. The HD 1.4 spike's RENAME
heuristic was tuned for engineering-style label expansions and missed
the social/physical-sciences expansion patterns; HD 2.1.e row-by-row
authoring against the era-B harvest resolved all seven. **They are not
structural-verdict triggers — they were heuristic misses in the spike's
best-effort RENAME map, not real no-mapping cells.**

The 2009→2010 break is still structural — but on **question-model
fragmentation** (era-A's single `Expenditures by S&E field` question
splits into era-B's Q9 federal + Q11 nonfederal, plus carve-outs and
within-federal sub-streams), not on no-mapping leaves. CLAUDE.md §6's
HD 1.4 outcome correctly named the question-model finding as the
structural trigger; HD 1.4 was already locked to *Reconstructive
Harmonization* framing on 2026-04-30 on that basis. The threshold
ladder, applied here, would re-confirm that verdict via the
question-fragmentation path, not via the seven-unmapped-leaves path.

The cells that genuinely lack era-A counterparts are the four FY 2017
micro-expansions (industrial-and-manufacturing engineering, natural-
resources-and-conservation, materials-science, anthropology) plus the
ARRA exclusion — those are era-B-only fields whose first-positive-year
is 2016, not 2009 leaves with no 2010 mapping. They do not affect the
2009→2010 ladder cell count.

### 6.2 What HD 2.1 does with the ladder

The ladder is **applied as documentation**, not as a fresh kill
condition. CLAUDE.md §6's HD 1.4 outcome is locked:

> The threshold ladder remains correctly specified for the case it
> models; HD 1.4 simply revealed that this case is not the one in
> front of us.

HD 2.1 runs the ladder against the reconstructed ratios for the §3
residual-analysis sample (4 years × top 10 institutions × 34 cells)
and reports the count in each band. The result is a **byproduct** of
§3 residual analysis, not a separate verdict — and it does **not**
re-trigger a methods-note framing change. CLAUDE.md §6's lock holds:
the methods-note framing is *Reconstructive Harmonization* regardless
of how the ladder cells distribute. See §8.

### 6.3 Recalibration check

N = 34 falls inside [30, 40], the recalibration band CLAUDE.md §6
specifies. No recalibration needed for HD 2.1.

---

## 7. Estimate

Assumes 8 half-days per week. Effort categorized as **clean**
(mechanical), **ambiguous** (defensible-either-way decisions that need
panel touch), or **spike** (genuinely unknown; needs throwaway code
before scoping further).

| HD | Task | Half-days | Bucket |
|---|---|---:|---|
| 2.1.a | Author `crosswalks/question_map.csv` from FY24 Guide pages 5–6 (era-B Q1–Q17) and pages 13–22 (era-A Items 1–4). Lift FY24 Guide page anchors as `decision_rationale`. ~30 rows. | 1 | clean |
| 2.1.b | Author `crosswalks/era_b_reconstruction_rule.yaml` (renamed 2026-05-01); W1–W4 dispositions locked at panel review (W1 r&d_equipment parallel row; W2 institution-year attribute flags; W3 case-a build assumption with residual reopen; W4 column='Total' both eras — see §2.3 lock entries). **Run the §3 residual test (top-10 × 7 buckets, 2009→2010) against §3.3 thresholds with §3.6 pre-doc exception clause.** Includes 1-half-day external-referent search for NSF/NCSES/ASEE published tolerance surfaces (Path B → Path A switch path, log to `seeds/overrides.md` if surface found). Pre-doc cell list (§3.6) folded in (≤30 min). **Outcome locked 2026-05-01 — REOPEN; resolved at (b₂) decomposition sub-framing.** Six of seven gating buckets failed median residual >5%; Social sciences sign-flip; institution-total residual median −22.5% (Diagnostic 1). Sub-framing locked at (b₂) decomposition per CLAUDE.md §6 HD 2.1.b outcome: real growth + definitional change + cohort expansion + bounded unmeasurable residual. **Sequencing gate disposition:** the era-B-internal rule is correct as specified (sequencing gate **passes** for the rule itself); the residual gate reopened the *bridge claim*, which (b₂) drops. Tasks c–.i locked under (b₂) framing. | 1.5 | ambiguous outcome resolved (b₂); commentary updated |
| 2.1.b-yaml | Author `crosswalks/era_b_reconstruction_rule.yaml` final form: rename from `summation_rule.yaml`, add **non-bridge clause** in the YAML preamble (the rule is era-B-internal; era-A↔era-B is decomposed not bridged), insert cross-doc pointer to the methods-note decomposition section (artifact #6 §[decomposition]). | 0.5 | clean |
| 2.1.c | Harvest era-A row labels 1973–2009 from `read_herd_csv(year)` row values. Group by year_range where labels stable. | 0.5 | clean |
| 2.1.d | Harvest era-B row labels 2010–2024 same way. | 0.5 | clean |
| 2.1.e | Author `crosswalks/discipline_fine.csv`. Lift the spike's RENAME map for the ~17 mapped rows; add the seven unmapped 2009 leaves (§4.2) as `era_b_counterpart=NULL` rows with `decision_rationale` per row; add era-B-only / FY 2017 micro-expansions (industrial-and-manufacturing engineering, life-sciences-natural-resources-and-conservation, physical-sciences-materials-science, social-sciences-anthropology); apply canonical-spelling = FY 2024 form per `docs/hd_2_1_open_items.md`. **+0.25 — fold in `raw_question_label` field on `crosswalks/question_map.csv` for the canonical-vs-raw join gap surfaced at HD 2.1.b Diagnostic 2.** ~80–110 rows. | 2.25 | mostly clean; 0.5 ambiguous on collapse-vs-preserve calls for the unmapped leaves; +0.25 raw_question_label fold-in |
| 2.1.f | Author `crosswalks/discipline_coarse.csv`. ~14 rows (7 buckets × 2 eras). | 0.5 | clean |
| 2.1.g | ~~Run the residual analysis (§3)~~ **Already shipped via HD 2.1.b residual report + three diagnostics.** Output lives in `validation/reports/era_reconciliation_2008_2011.md` plus `_diagnostic_1_institution_total.md`, `_diagnostic_2_q5_share.md`, `_diagnostic_3_growth.md`. Drop from the estimate. | 0 | done (folded into 2.1.b) |
| 2.1.h | Apply the locked threshold ladder against the reconstructed ratios; report cell distribution as a byproduct (does NOT trigger framing changes, per §8). | 0.25 | clean |
| 2.1.i | Author `docs/methods_notes/reconstructive_harmonization.md`. **Voice locked at panel review (§5.3) + decomposition-framing extension (locked 2026-05-01, CLAUDE.md §6 voice subsection update).** Translate `era_b_reconstruction_rule.yaml` into prose body via templated regeneration; lift inline pseudo-code from §2.1 equation form for the era-B-internal rule; YAML lifted verbatim into Appendix B (not body). **+1.75 over original — decomposition prose + multi-component figure (slot 2 four-bar) prose anchor + three diagnostic-report appendices E/F/G + receipt/headline voice work** (headline-level claims trim of caveats; receipts pushed to body + appendix per the receipt/headline split). Auto-generate Appendix A from `question_map.csv`; Appendix C from `discipline_fine.csv`; summarize Appendix D from the residual report; lift Appendices E/F/G from the three diagnostic reports. | 3.0 | clean structure; ambiguous prose on the bounded-unmeasurable framing |
| 2.1.j | Buffer / catch-up. | 0.75 | — |
| **Total** | | **10.75** | (~1.35 weeks; +1.5 over the 9.25 prior = +0.5 yaml rename / non-bridge clause + +0.25 raw_question_label fold-in + +1.75 expanded 2.1.i decomposition prose + −1.0 absorbed 2.1.g) |

**Sequencing-gate disposition (locked 2026-05-01).** The HD 2.1.b hard sequencing gate (c–.i don't lock until .b passes) was specified against the *era-A↔era-B bridge* claim that the rule was originally framed to make. HD 2.1.b ran the residual gate, the bridge claim failed (REOPEN), and the panel resolved the failure at sub-framing (b₂) decomposition. Under (b₂), the rule is recast as **era-B-internal**: it reconstructs era-B all-source field-level totals from Q9+Q11 fragments. In that narrower scope, the rule is correct as specified — Q9 + Q11 = era-B all-source field total is the era-B-internal identity, anchored by FY24 Guide pages 5–6, and is consumed by the harmonized panel build (HD 2.4) without modification. **The sequencing gate passes once (b₂) locks.** Tasks c, d, e, f, h, i unblock. The methods-note framing (artifact #6) shifts from contribution-equation to contribution-decomposition (per the CLAUDE.md §6 voice subsection update locked 2026-05-01); the rule survives as the canonical era-B reconstruction primitive that feeds the era-B series; the deposit ships two parallel reconstructed series plus the methods note's four-bar decomposition characterizing the boundary. The +1.5 half-day delta vs. the prior estimate stays inside the W3 personnel-sibling and W9–10 paired-deposit timeline because 2.1.j buffer (0.75) was unspent and the (b₂) framing did not require a new spike — the three diagnostics had already been authored at HD 2.1.b reopen.

### Honest unknowns

1. **§3 residual magnitude.** Signal on whether the simple Q9+Q11 sum
   hits within band at the era boundary is still unknown until 2.1.b
   runs. *Test shape locked at panel review (2026-05-01)*: top-10
   institutions × 7 coarse buckets, year-pair 2009→2010 (replaces the
   Engineering-only single-cell pre-check). Thresholds locked: median
   residual >5% on any bucket OR any single cell >15% triggers
   reopen, with §3.6 pre-doc exception clause for known
   definitional-drift cells. Path B residual band sourcing locked,
   1-half-day external-referent search included in 2.1.b for the
   Path A override path.
2. **Whether era-B 2010+ has a `Psychology` rollup or merges
   psychology into `Social sciences`.** Spike RENAME map didn't cover
   this; needs HD 2.1.d row-label harvest to resolve. *Disposition:*
   resolves itself during 2.1.d; if surprise, escalate. **Pre-doc
   list §3.6 carries Psychology and Social sciences as conditional
   pre-doc rows** until 2.1.d settles the question.
3. **Whether the pre-1981 era (1973–1980) had a different field
   taxonomy.** FY24 Guide page 14: "From FY 1979 to FY 1989, the
   survey requested data on capital expenditures..."; FY24 Guide page
   18 Item 2 shows different field availability for 1973–74, 1975–77,
   1978, 1979, 1980–89. *Disposition:* the discipline-fine crosswalk's
   year_range column handles this — multiple rows per leaf with
   different year ranges. Adds rows but not ambiguity.

### Spike trigger

If the HD 2.1.b residual test (top-10 × 7 buckets, 2009→2010
reconstructed) exceeds the locked thresholds (median bucket residual
>5% OR any single cell >15%) on a **non-pre-documented** cell or
bucket, **stop HD 2.1 build at the c–.i hard sequencing gate**, write
a 2-hour `etl/spikes/spike_summation_rule_residual.py` to widen the
rule candidates (federal+nonfederal+ARRA explicit,
federal+nonfederal+Q14 deduplicated, etc.), and panel before resuming.
Mark as a kill condition, not a default path. Pre-documented cells
that fail are footnoted as W5-class drift per §3.6, not reopens.
Median-based bucket trigger distinguishes "rule wrong" (≥6 of 10
institutions breach the bucket median) from "one institution weird"
(1–2 breach with median clean); cell-level >15% catches single
catastrophic blowups regardless of bucket median.

---

## 8. What HD 2.1 does NOT do

Explicit out-of-scope. Surfaces the boundary so subsequent panel
reviews don't slip new asks into HD 2.1's quote.

1. **HD 2.1 does NOT trigger methods-note framing changes** based on
   the threshold ladder result. CLAUDE.md §6's lock is in force —
   *Reconstructive Harmonization* is the framing regardless of how
   the §6.2 byproduct cell distribution comes out. If a future panel
   wants to reopen the framing, that's a Vision call against
   §6 lock, not an HD 2.1 deliverable.

2. **HD 2.1 does NOT build `data/harmonized/herd_panel.parquet`.** That
   is HD 2.4 (per `PANEL_SKIPPER.md` §2 Week 2 plan). HD 2.1 ships the
   crosswalks + summation rule + residual report; HD 2.4 composes them
   into the panel parquet.

3. **HD 2.1 does NOT touch the personnel sibling**
   (`crosswalks/personnel_*.csv`, `data/harmonized/herd_personnel.parquet`).
   Personnel is W3 work per CLAUDE.md §6 paired-deposit lock.

4. **HD 2.1 does NOT populate the encoding-substitutions log.** The
   2014–2017 contamination cluster (149/158/159/308 substitutions) is
   already a separate panel-decision-queued item per
   `PANEL_SKIPPER.md` §7 Round 5 panel decisions queued, item (a). HD
   2.1 reads CSVs through the existing `read_herd_csv` (which handles
   encoding fallback transparently); the per-byte log audit is HD 2.x
   work, deferred until Vision rules on standalone-vs-footnote framing
   for the encoding seed.

5. **HD 2.1 does NOT build Great Expectations suites** for the
   crosswalks. That is HD 2.6. Validation in HD 2.1 is the §3
   residual analysis only — a one-time methodological check.

6. **HD 2.1 does NOT reconcile against NSF published all-institution
   totals.** That is HD 2.7 (`validation/reports/herd_reconciliation_v1.md`,
   per `PANEL_SKIPPER.md` §4). The §3 residual analysis here is a
   different artifact: institution-year reconstruction within our own
   harmonized data, *not* against NSF aggregates. HD 2.7 is the
   external reconciliation; HD 2.1's §3 is the internal consistency
   check.

7. **HD 2.1 does NOT touch the BEA deflator.** That is HD 2.5.
   Reconstructed values stay in current dollars throughout HD 2.1.

8. **HD 2.1 does NOT propose a new era-boundary scheme.** CLAUDE.md
   §6 locks 2010 boundary; PANEL_SKIPPER §7 Round 5 Finding 1 (HD 1.5)
   validated the boundary against the data. Multi-break consideration
   is a Vision-level reopen, not HD 2.1.

---

## Open questions for the panel before build phase begins

### Resolved at panel review 2026-05-01 (closed)

1. ~~**Vision (W1 disposition):**~~ **Locked.** Q14 r&d_equipment maps to
   a parallel `expenditure_type='r&d_equipment'` row, out of the
   summation rule. (§2.3 W1, §7 task 2.1.b commentary.)
2. ~~**Vision (W2 disposition):**~~ **Locked.** Q4 (medical school) and
   Q5 (clinical trials) become institution-year attribute flags, not
   parallel rows. (§2.3 W2.)
3. ~~**Vision (W3 disposition):**~~ **Locked.** Build under case-a
   assumption (ARRA within-federal); residual analysis is empirical
   check, residual-reopen as kill condition. (§2.3 W3.)
4. ~~**Vision (§3 acceptable residual):**~~ **Locked.** Median bucket
   residual >5% OR any single cell >15% triggers reopen, with §3.6
   pre-doc exception clause for known definitional-drift cells.
   (§3.3.)
5. ~~**Vision (residual band sourcing):**~~ **Locked, Path B.**
   Empirical/descriptive thresholds with 1-half-day external-referent
   search at HD 2.1.b. Path A switch path defined; override logged to
   `seeds/overrides.md` if a published NSF/NCSES/ASEE tolerance
   surface is found. (§3.3.)
6. ~~**Vision (test shape):**~~ **Locked.** Top-10 institutions × 7
   coarse buckets at HD 2.1.b. Engineering-only single-cell pre-check
   superseded. (§3.1.)
7. ~~**Vision (HD 2.1.b sequencing gate):**~~ **Locked.** Tasks c–.i do
   not lock until .b passes. (§7 task 2.1.b commentary, spike
   trigger.)
8. ~~**Sophia (artifact #6 voice):**~~ **Locked.** Translated prose body
   + inline pseudo-code (lifts §2.1 equation form) + YAML in Appendix
   B. Not verbatim YAML body. +0.25 half-days to 2.1.i. (§5.3.)
9. ~~**Sophia (lead anchor):**~~ **Locked.** Question-count cliff chart
   with Sophia-drafted headline sentence. (Per panel review locks;
   anchor lives in the methods-note draft, not in this scoping doc.)

### Genuinely still open

1. **Psychology era-B disposition (informational, not a build blocker).**
   Whether era B preserves Psychology as a top-level coarse bucket or
   merges it into Social sciences resolves at HD 2.1.d (era-B row-label
   harvest), not at panel review. §3.6 pre-doc list carries Psychology
   and Social sciences as **conditional** pre-doc rows that drop if
   HD 2.1.d confirms preservation. INVENTORY §5.2 silence on a
   Psychology rename suggests preservation; the row-label harvest
   confirms or escalates. *Disposition path locked; outcome pending
   data.*

These are the items the panel resolves before HD 2.1 build phase
greenlights — the resolved items are recorded above, not relitigated.
