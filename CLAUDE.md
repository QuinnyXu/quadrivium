# quadrivium — Project Anchors

This file is auto-loaded by Claude Code at session start. It carries the locked decisions for the quadrivium open-source data infrastructure project. The agents (`skipper`, `vision`) are portable across projects; the project-specific anchors live here.

When an agent invokes, treat everything below as background context they share. Agents should reference these anchors by section name when defending a decision (e.g., *"per CLAUDE.md §4 codeset-extension policy, empirically-surfaced undocumented codes default to exclude + footnote"*).

---

## 0. Agent team — scales with project stage

Quadrivium uses a stage-scaled agent team. The current team is intentionally lean; lenses are added when their concern earns a slot.

- **Stage 1 (current — open datasets):** Skipper (engineering) + Vision (strategy). Audience is the self-selecting cold reader (data journalist, IR director, scholar) who arrives at the deposit via search or citation — README clarity and methods-note voice are owned by the Maintainer at this stage with Skipper / Vision review.
- **Stage 2 (planned — platform):** + audience-design agent. When quadrivium becomes a platform with users (e.g., a public query interface or dashboard), the audience-design problem becomes genuine and earns a dedicated lens.
- **Stage 3 (planned — commercial analytics):** + possible additional lens (product / customer-development) if the commercial surface requires it. TBD when Stage 3 work earns the slot.

Agent definitions live under `.claude/agents/` and are gitignored as personal working tools (see §10).

---

## 1. Project mission

Quadrivium harmonizes U.S. higher-education survey data into reproducible analytical panels that a cold reader can use without misreading the methodological discontinuities in the underlying data.

**Current scope.** NSF HERD (Higher Education Research and Development survey), FY 1972–2024. The financial panel (`data/harmonized/herd_panel.parquet`) covers FY 1975–2024 field-level R&D expenditure data across the 2010 instrument redesign; the personnel sibling (`data/harmonized/herd_personnel.parquet`) covers Q15 headcount + Q16 FTE for FY 2022–2024; the Q4/Q5 attribute sibling (`data/harmonized/herd_panel_attributes.parquet`) carries medical-school and clinical-trials share / value columns.

**Roadmap.** IPEDS (Integrated Postsecondary Education Data System), NSF GSS (Survey of Graduate Students and Postdoctorates in Science and Engineering), and other NCSES surveys as the contribution-process matures. Each migration applies the Reconstructive Harmonization methodology to that survey's discontinuities; the schema and validation patterns adapt to the survey's structure, the methodology does not.

**Three-stage trajectory.** Stage 1 (current) is open-source harmonization of survey datasets. Stage 2 is a platform on top of the harmonized data (interactive query, comparative panels). Stage 3 is commercial analytics built on the platform. Stages 2 and 3 are not built now; they are the durable framing of where the project goes, recorded here so scope decisions can be evaluated against the trajectory rather than the current step alone.

## 2. Methodology — Reconstructive Harmonization

Quadrivium's methodological signature, owned-term:

> "Reconstructive Harmonization is the methodological signature of this program. We take operational data that has methodological discontinuities — era boundaries in survey instruments, encoding shifts, taxonomy redesigns, infrastructure changes — and:
>
> (a) reconstruct what each era can support on its own terms (rules, crosswalks, validated reconstructions);
>
> (b) decompose what crossing the discontinuity actually involves into named, quantified components (real growth, definitional change, population expansion, residual unmeasurables);
>
> (c) publish both the reconstruction and the decomposition with sufficient documentation that a cold reader can use either without misreading the discontinuity.
>
> Reconstructive Harmonization is not a bridge. It is the discipline of making operational data legible across discontinuities by being precise about what is reconstructible, what is decomposable, and what remains unmeasurable."

The HERD methods note (`docs/methods_notes/reconstructive_harmonization.md`) applies the methodology to the 2010 HERD era boundary. The era-B reconstruction rule (clause (a)) lives in `crosswalks/era_b_reconstruction_rule.yaml`. The four-driver decomposition of the 2008→2011 institution-total residual (clause (b)) is in `validation/reports/era_reconciliation_2008_2011.md` plus the three diagnostic reports. Future dataset migrations carry the same methodology forward.

## 3. Technical stack and reproducibility contract

- **Python 3.12.10 + DuckDB + Parquet.** `uv` 0.11.8 with `pyproject.toml` + committed `uv.lock`.
- **Runtime deps** (exact only): `duckdb==1.5.2`, `pypdf==6.10.2`.
- **Dev group `charts`** (exact only): `matplotlib==3.9.2`. For methods-note figures, not deposit runtime.
- **Dev group `dev`** (exact only): `pytest==8.3.3`. For test runs when tests exist.
- Lockfile covers all groups and is a deposit artifact.

**Reproducibility contract.** A deposit consumer reproducing the harmonized panel installs runtime deps only (`uv sync`). A consumer reproducing the methods-note figures installs the `charts` group additionally (`uv sync --group charts`). A consumer running tests installs the `dev` group.

```bash
uv sync
uv run python etl/build_herd_panel.py        # rebuild financial + attribute parquets
uv run python etl/build_herd_personnel.py    # rebuild personnel parquet
```

Raw NSF HERD zips live in `data/raw/herd/` (gitignored, SHA-256s tracked in `data/raw/MANIFEST.md`). The loader extracts on read. Harmonized outputs land in `data/harmonized/`. NCSES reference PDFs in `data/reference/` carry their own MANIFEST.

**Cold-reader contract.** A reader with the lockfile, the raw zips named in `data/raw/MANIFEST.md`, and the NCSES reference PDFs in `data/reference/` reaches the same harmonized parquet bit-equivalently (modulo parquet writer determinism on a fixed input-and-code-version pair).

## 4. Schema and era-handling locks

### Long-format schema
```
institution_id, institution_name, ncses_inst_id, ipeds_unitid, inst_name_long,
year, era,
discipline_coarse, discipline_fine,
expenditure_type, source_class, form_type,
value, unit, value_type,
quality_flag, source_questionnaire_no, source_file, notes
```

See `docs/methods_notes/herd_panel_etl_scoping.md` §1 for the full column-by-column spec.

### Era handling
- **Era A** (1972–2009): 20-column raw schema, `fice` ID only, no IPEDS UNITID. Era-B-only columns NULL.
- **Era B** (2010–2024): 23-column raw schema, adds `inst_id` + `ncses_inst_id` + `ipeds_unitid`.
- **Era boundary at 2010**, data-validated against the per-year question-structure profile in `docs/herd_question_structure_by_year.csv`. No transitional years observed.
- **Field-level longitudinal panel: 1975–2024 (50 years).** 1972 carries only Capital expenditures and Source questions; 1973–1974 emit a Guide-undocumented `status='c'` code on field-level `column='Total'` rows (see §4 codeset-extension policy). 1972–1974 are preserved in raw deposit artifacts but excluded from field-level analyses via the `PANEL_FIRST_YEAR=1975` floor in `etl/build_herd_panel.py`.

### Era-B-internal reconstruction rule
The 2010 redesign fragmented era-A's single field-level question into multiple era-B source-class questions (Q9 federal + Q11 nonfederal). The reconstruction primitive:

```
all_source_total(field, year) = Q9.Total(field, year) + Q11.Total(field, year)
for every year 2010–2024
```

The rule is era-B-internal (it recovers era-B all-source totals within era B). It is NOT a bridge across the era boundary. The full rule with FY24 Guide anchors lives in `crosswalks/era_b_reconstruction_rule.yaml`.

### 2010 era-boundary decomposition (clause (b))
The deposit ships two parallel reconstructed series (era-A 1975–2009 direct, era-B-reconstructed 2010–2024 via the rule above) plus the methods-note decomposition characterizing the boundary itself. The 2008→2011 institution-total residual decomposes into:

- **Real growth** (~26% national, FY2008→FY2011, current dollars; diagnostic 3).
- **Definitional change at the boundary** — era-B totals include items era-A totals didn't (FY24 Guide page 14 names clinical trials and training grants).
- **Cohort expansion** — the all-institutions national pool grew from 690 → 896 institutions FY2008→FY2011.
- **Bounded unmeasurable residual** — training-grants dollars are HERD-unmeasurable as a separable component.

See `validation/reports/era_reconciliation_2008_2011.md` and the three diagnostic reports for the full decomposition.

### Codeset-extension policy (locked)

The W4 NULL-handling lock defines a four-value `quality_flag` enum (`reported`, `imputed`, `estimated`, `unspecified_zero`) anchored to FY24 Guide pages 8 / 10 / 23 / 25. Extensions to the codeset require either (a) a Guide-documented semantic anchor (FY24 Guide or a cited NCSES methodology document), or (b) panel review with explicit documented semantic anchor. Empirical surfacing of an undocumented status code in raw HERD data is not, by itself, sufficient grounds for codeset extension; the disposition default for empirically-surfaced undocumented codes is exclusion of affected rows from the harmonized panel with methods-note footnote, pending review.

**In practice.**

- **Case-folding inside the locked codeset is mechanical, not extension.** Pre-1990 raw files emit status codes in mixed case (`'I'` / `'E'` alongside `'i'` / `'e'`); the build's CASE expression uses `UPPER(status) IN ('I','E','U')`. Methods-note one-liner discloses the fold.
- **Genuinely-new status codes default to exclude + footnote.** FY 1973–1974 `status='c'` rows are excluded from the field-level panel via the `PANEL_FIRST_YEAR=1975` floor. Raw zips remain in `data/raw/herd/` as deposit artifacts.
- **Empirical scope adjustments to existing enum values do NOT require codeset extension treatment.** The era-B `status='u'` characterization (~4,000 rows, 106 institutions, retired FY 2023+) is documented as empirical scope, not as a codeset change.

See `validation/reports/era_a_status_codeset_findings.md` and `validation/reports/herd_null_characterization_findings.md` for the empirical anchors.

## 5. Validation ground truth

- NSF HERD published all-institution totals.
- **NCSES Data Table 26 (NSF 26-304)** — single-cell anchor for personnel reconciliation. FY2024 headcount = 1,086,850; FTEs = 525,960. Constraint: Table 26 covers only standard-form population ($1M+ FY23 R&D). Reconciliation filters to that population, not free-sum across all rows.
- NSF Science & Engineering Indicators for engineering subsets.
- ASEE *Engineering by the Numbers* for engineering-specific cross-checks.

Validation reports live in `validation/reports/`. Every harmonized artifact ships with a validation report against at least one published-ground-truth anchor.

## 6. Crosswalks are most of the methods note

- `crosswalks/discipline_coarse.csv`, `discipline_fine.csv` — discipline taxonomy crosswalks (era-A row labels → coarse buckets; era-B row labels → coarse and fine).
- `crosswalks/question_map.csv` — era × questionnaire_no × question text → canonical question label crosswalk.
- `crosswalks/era_b_reconstruction_rule.yaml` — the era-B-internal reconstruction rule + quality-flag propagation ordering + Stage 9 consumer contract.
- `crosswalks/_harvest/era_a_row_labels.csv`, `era_b_row_labels.csv` — verbatim raw-label harvest, the empirical anchor for the discipline crosswalks.

Every crosswalk row carries a `decision_rationale` column. Treat each row as a methods-note sentence.

## 7. HD 2.1 dispositions (locked)

Six methodological locks for the canonical question-mapping crosswalk + reconstruction-rule build (`docs/hd_2_1_scoping.md`):

1. **Q14 (capitalized R&D equipment) excluded from the all-source summation rule.** Maps to a parallel `expenditure_type='r&d_equipment'` row, mirroring era-A Item 3. FY24 Guide page 6 ("the *portion of* their federal and nonfederal R&D expenditures...") is dispositive — Q14 is a slice of Q9+Q11 dollars; including it double-counts.
2. **Q4 (medical school) and Q5 (clinical trials) excluded as carve-outs.** Travel as institution-year attribute flags (`med_school_share`, `clinical_trials_share`) in `data/harmonized/herd_panel_attributes.parquet`, not separate rows in the main panel.
3. **ARRA build assumption: case (a) within-federal.** The FY24 Guide's "removed and all subsequent questions were renumbered" phrasing (page 4) is consistent with case (a) within-federal breakdown.
4. **HD 2.1.b residual test — shape and thresholds.** Top-10 institutions (by FY 2008 R&D volume) × 7 coarse buckets, FY 2009 era-A direct vs. FY 2010 era-B reconstructed. Reopen triggers: median residual >5% on any bucket OR any single cell >15%. Pre-documented W5-class definitional-drift cells (Environmental→Geosciences canonical) footnoted as known drift.
5. **Residual band sourcing — Path B (empirical / descriptive).** Methods note treats the band as descriptive: "we built the rule, here are the residuals, here is the acceptance band and why." Path A (external referent) would activate if a published NSF/NCSES residual tolerance surfaces post-deposit.
6. **HD 2.1.b hard sequencing gate.** Downstream HD 2.1 sub-tasks do not lock until 2.1.b passes. The verdict was REOPEN; the four-bar decomposition (clause (b)) is the resolution.

## 8. HD 2.4 dispositions (locked)

Selected locks from the HD 2.4 sub-action sprint (full audit trail in `PANEL_SKIPPER.md` §8):

- **W1 — Q14 era-boundary spike.** Equipment-series footnote queued for the methods note; sign-consistent (40/40 populated cells > 0), magnitude-stable (9/10 institutions in [0.5, 2.0] ratio band; Pennsylvania outlier at 2.56× reverting). Documented at `validation/reports/equipment_era_boundary_findings.md`.
- **W4 NULL-handling lock (empirical re-characterization 2026-05-10 PM).** Four-value `quality_flag` enum locked; least-good-flag-wins propagation ordering (`unspecified_zero < estimated < imputed < reported`); three-tier corrected baseline for `status='u'` assertion (era-A NOT expected; era-B 2010–2022 allowed per ~4,000-row characterization; era-B 2023+ NOT expected per FY 2023+ retirement evidence). See `validation/reports/herd_null_characterization_findings.md`.
- **HD 2.4.g substrate-shape lock (Vision Branch III verdict 2026-05-21).** FY 2024 era-B-internal cohort-anchored verification grid (58 substantive cells, not 60 nominal — UCSF Engineering structurally absent) replaces the original 240-cell four-spot-year nominal grid. Historical-vintage anchors (FY 2017 / FY 2010 / FY 2008) deferred per the Branch III scope-shape resolution; era-boundary characterization absorbed entirely into the HD 2.1.b decomposition.
- **HD 2.4 sampling methodology lesson (locked 2026-05-10 PM).** Spike sampling for empirical characterization of cross-temporal NCSES encoding patterns defaults to era-wide coverage; three-spot-year sampling is reserved for spikes whose kill condition does not depend on cross-temporal completeness.

## 9. Methods-note voice (locked)

Methods notes are written for the cold deposit reader (journalist, scholar, senior administrator), not the build-side reader. Machine-readable artifacts (YAML, CSVs) are sources of truth and live in appendices; the prose body translates into reader-native language.

**Lead-anchor convention.**
1. Problem visualization (e.g., the question-count cliff chart from HD 1.5).
2. Contribution equation OR contribution-decomposition (named, sized components — e.g., the four-bar decomposition of the 2008→2011 institution-total residual). The form adapts to what the contribution is.
3. Validation receipt (e.g., the residual analysis result).

**Cold-reader test for slot 2.** The chart's caption sentence must contain the surprise and at least one number. *"We decomposed it"* without a number fails. Captions that lead with the finding and let the methodology trail in the body pass.

**Receipt/headline split.** Headline-level claims lead with the surprise and a number, no caveats. Receipt-level defense (additivity caveats, fixed-cohort vs. national-pool distinctions, methodological footnotes, citations) lives in the methods-note body and appendices.

## 10. Repo conventions

```
quadrivium/
├── CLAUDE.md                    # this file
├── README.md                    # public-facing entry point
├── LICENSE                      # MIT (code)
├── LICENSE-DATA.md              # CC-BY-4.0 (data)
├── data/
│   ├── raw/                     # gitignored; MANIFEST.md tracked, SHA-256s
│   ├── harmonized/              # canonical parquets
│   └── reference/               # NSF / NCSES source PDFs; MANIFEST.md tracked
├── crosswalks/                  # CSVs and YAML with decision_rationale columns
├── etl/                         # loaders, builders, spikes/
├── docs/                        # methods notes, scoping, source_documents/
├── validation/                  # reports/, profile/
├── seeds/
│   ├── research-seeds.md        # HD-relevant research seeds; methodology continuity
│   └── overrides.md             # override log
├── PANEL_*.md                   # panel review outputs by topic
└── MEMORY.md                    # auto-memory index (accumulates across sessions)
```

Agent definitions, local Claude Code state, and personal working files live under `.claude/` and are gitignored. Raw HERD zips, `__pycache__/`, `.venv/`, IDE configs, and `*.duckdb` are also gitignored. The repo carries deposit-quality artifacts; personal working-environment configuration is not tracked.

## 11. License posture

- **Code:** MIT (see `LICENSE`).
- **Data:** CC-BY-4.0 (see `LICENSE-DATA.md`).

External contributors who want to propose a crosswalk amendment or methodology extension should open a GitHub issue with the proposed change, the empirical anchor (which raw HERD year and file, or which published NSF document), and the `decision_rationale` they would add. A CONTRIBUTING.md will land at Stage 2 when external contribution becomes a real flow; until then, the issue-based proposal is the path.

## 12. Override log

When the Maintainer overrides an agent verdict, log it in `seeds/overrides.md` with one paragraph: what was proposed, what was overridden, the reasoning, and the kill condition that would prove the override wrong. Periodic panel reviews check overrides against outcomes.
