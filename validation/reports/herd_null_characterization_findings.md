# HERD NULL Characterization — Spike Findings (HD 2.4)

**Authored by:** Skipper, 2026-05-09 (HD 2.4 NULL handling spike).
**Revised:** 2026-05-10 PM (HD 2.4.d Stage 9 disposition probe; Vision verdict δ + γ-allow). The original three-spot-year characterization (FY 2008 / 2017 / 2024) is preserved below as the **Initial characterization** section. The corrected era-B-wide empirical baseline is locked in §7 (**Corrected era-B-wide baseline (locked 2026-05-10 PM)**).
**Spike:** `etl/spikes/spike_herd_null_characterization.py` (throwaway, not promoted).
**Re-characterization probe:** `etl/spikes/probe_era_b_status_u_full.py` + `_output.txt` (HD 2.4.d round 1, 2026-05-10 PM).
**Status:** Corrected baseline locked. Initial characterization preserved for audit-trail consistency with the HD 2.4 W4 NULL-handling lock evolution.
**Anchor it amends:** `docs/methods_notes/herd_panel_etl_scoping.md` §1 `quality_flag` value semantics (revised 2026-05-10 PM per the corrected baseline) + §6.2 Stage 9 sanity assertion (redesigned to defend the three-tier corrected baseline).

## Revision summary (2026-05-10 PM)

**The 2026-05-09 spike sampled three spot years (FY 2008, FY 2017, FY 2024) and concluded `status='u'` was FY-2017-only / non-Total-only. The 2026-05-10 PM HD 2.4.d Stage 9 disposition probe extended scope to all era-B years 2010–2024 (standard-form + short-form) and revealed the original conclusion was a sampling artifact: `status='u'` is routine across era-B 2010–2022 (~4,000 rows, 106 institutions), retired FY 2023+, with institution-specific emission patterns. The locked baseline is revised to reflect the full empirical reality.**

That original conclusion locked into the W4 NULL-handling lock as the empirical baseline and into `etl/build_herd_panel.py` Stage 9's "drift-defense" sanity assertion. HD 2.4.b round 1 (2026-05-10 morning) surfaced 9 `unspecified_zero` rows at FY 2020 Q14 `column='Total'` violating both clauses of that baseline. HD 2.4.d ran a full era-B characterization probe (`etl/spikes/probe_era_b_status_u_full.py`) extending scope from three spot years to all 15 era-B years 2010–2024 plus short-form. The probe's specific findings:

- **~4,000 `status='u'` rows** across era-B 2010–2022 (not FY-2017-only).
- **106 distinct institutions** emit it; 56 emit across multiple years; several emit consistently for 10+ consecutive years.
- **FY 2023 and FY 2024 contain zero `status='u'` rows** — the encoding is retired by NSF without Guide documentation of the convention change.
- **Panel impact** is small (9 rows at FY 2020 Q14 `column='Total'`, all at institution `'003446'` = South Carolina State University, an HBCU) because Stage 5's `column='Total'` filter excludes the dominant non-Total occurrences.

The sampling-artifact diagnosis is the load-bearing claim: three spot years missed FY 2010, 2011, 2012, 2013, 2014, 2015, 2016, 2018, 2019, 2020, 2021, 2022 — 12 of the 15 era-B years — which together carry the vast majority of `status='u'` rows. The sampling-methodology lesson generalizes beyond `status='u'`: three-spot-year sampling for cross-temporal NCSES encoding patterns can produce baselines that don't survive era-wide scrutiny. Locked at `PANEL_SKIPPER.md` §8 (sampling methodology entry, 2026-05-10 PM); CLAUDE.md inclusion deferred to mid-June quarter-boundary review per §13 override discipline.

**Vision consultation 2026-05-10 PM verdict:** Option δ (re-characterize the W4 baseline) + Option γ-allow (let the 9 panel rows propagate). Rationale: `unspecified_zero` is already in the locked codeset — what's being adjusted is the empirical scope, not the enum. Per Reconstructive Harmonization clause (a) doctrine ("reconstruct what each era can support on its own terms"), the W4 baseline must reflect what era B actually emits, not what three spot years suggested. The Guide-citation discipline survives but the methods-note framing updates: *"The FY24 Guide documents `'u'` as a valid status code; the empirical scope of its emission across era-B 2010–2022 (~4,000 rows, 106 institutions, retired FY 2023+) is documented in this deposit's quality-flag characterization."*

Audit trail recorded at `PANEL_SKIPPER.md` §8 (W4 amendment entry, 2026-05-10 PM).

The Initial characterization (§§1–5 below) remains a faithful record of what the three-spot-year spike found. It is the empirical record of the W4 lock's *initial state* — useful for the audit trail and for the methodology lesson (the sampling-coverage problem this report surfaces is itself a process seed; see PANEL_SKIPPER.md §8 sampling methodology entry). The locked baseline for downstream consumers is §7.

---

# Initial characterization (revised 2026-05-10)

## 1. What this spike asked

The HD 2.4 scoping document's §14.2 recommends Option A (NULL-as-zero) for the era-B reconstruction rule's NULL semantics: `Q9 NULL + Q11 value = Q11 value`. Maintainer review surfaced that NULLs in raw HERD data are not interchangeable; three semantic cases were named:
- **(a)** genuine zero — institution had no R&D in that category;
- **(b)** NSF-imputed value — possibly flagged in raw CSV;
- **(c)** NSF-labeled "didn't report" — possibly flagged in raw CSV.

The spike characterizes the raw HERD CSV NULL/flag distribution at three spot years (FY 2008 / FY 2017 / FY 2024) so the NULL handling decision rests on the data, not on the schema doc's default.

## 2. Spike scope

| Spot year | Era | In-scope question(s) |
|---:|:---:|:---|
| FY 2008 | A | `'Expenditures by S&E field'` |
| FY 2017 | B | Q9 `'Federal expenditures by field and agency'`, Q11 `'Nonfederal expenditures by field and source'` |
| FY 2024 | B | same Q9 / Q11 |

Restriction to `column='Total'` rows (the cells the era-B reconstruction rule consumes; era-A's all-source value).

Loaded via `etl/_load.py:read_herd_csv` (the unified-schema loader); no Excel; no manual extraction.

## 3. The NULL story is not what §14.2 assumed

The §14.2 framing assumed `value` would routinely be NULL in raw rows and the question was how to handle it. The spike revealed something different.

> **There are no NULL `value` cells in `column='Total'` rows. Zero. Across all three spot years, all 65,609 in-scope Total-column rows carry a numeric `value` (cast from `data`).**

The "NULL" in the era-B reconstruction is not a NULL inside the row — it is a **row that does not exist** at the (institution, year, discipline_fine) cell. That changes the semantic question.

Per FY24 Guide page 8 (era B) and page 23 (era A): *"For each data line on the questionnaire to which a non-zero response has been received, a data record is present. For total rows in each survey question, a data record is present regardless of whether a zero or non-zero response has been received."*

Translation: the raw CSV is sparse by construction. A leaf cell with a true zero produces no row at all; only nonzero leaf cells and total rows produce rows. So the original three-case framing needs a fourth, dominant case:

- **(d)** **row absent at this (inst, discipline) cell** — institution emitted no R&D for this discipline in this question. This is the dominant case for era-B Q9 vs. Q11 asymmetry.

## 4. Empirical NULL/flag distribution

### 4.1 Headline status distribution at `column='Total'`

| Year | Total-col rows | reported (status blank) | imputed (`i`) | data not avail (`n`) | estimated (`e`) | unflagged-NULL value |
|---:|---:|---:|---:|---:|---:|---:|
| FY 2008 | 11,321 | 10,544 (93.14%) | 777 (6.86%) | 0 (0.00%) | 0 (0.00%)\* | 0 (0.00%) |
| FY 2017 | 25,829 | 24,983 (96.72%) | 846 (3.28%) | 0 (0.00%) | n/a (era B) | 0 (0.00%) |
| FY 2024 | 28,459 | 27,657 (97.18%) | 802 (2.82%) | 0 (0.00%) | n/a (era B) | 0 (0.00%) |

\* Era A's `e=Estimated by NCSES` (FY24 Guide page 25) appears **once** in the entire FY 2008 file across all questions and columns; **zero times** at `column='Total'` for the in-scope question. Effectively retired in practice.

The maintainer's prior knowledge of "~4–5% incomplete reporting" matches the imputed share (`i`): 6.9% in 2008, 3.3% in 2017, 2.8% in 2024 — declining over time, sitting in the right neighborhood.

### 4.2 Status distribution across the entire file (any question, any column)

| Year | total rows | blank | `i` (imputed) | `e` (estimated) | `u` (undocumented) |
|---:|---:|---:|---:|---:|---:|
| FY 2008 | 76,136 | 72,402 (95.10%) | 3,733 (4.90%) | 1 (0.00%) | 0 |
| FY 2017 | 238,032 | 228,714 (96.09%) | 9,074 (3.81%) | n/a | 244 (0.10%) |
| FY 2024 | 264,321 | 255,087 (96.51%) | 9,234 (3.49%) | n/a | 0 |

**Surface beyond original framing — undocumented `status='u'` in FY 2017.** 244 rows carry `status='u'`, which is not in the FY24 Guide's documented set {Blank, `i`, `n`, `e`}. All 244 occur on per-source-class detail columns (`Institution funds` / `Nonprofit organziations` [sic — spelling preserved] / `Business` / `Nonfederal`), **never on `column='Total'`**, and inspection of sample rows shows `data='0'` consistently. Plausible reading: a respondent-marked "unspecified zero" or "user-confirmed zero" code that NCSES introduced and later retired (zero occurrences in FY 2024). Does not affect the era-B reconstruction rule, which consumes `column='Total'` only.

### 4.3 Institution-grade rollup at `column='Total'`

Each institution's Total-column cells in scope, classified:

| Year | n inst | all blank (fully reported) | all imputed | mixed blank+imputed |
|---:|---:|---:|---:|---:|
| FY 2008 | 690 | 664 (96.23%) | 11 (1.59%) | 15 (2.17%) |
| FY 2017 | 643 | 609 (94.71%) | 22 (3.42%) | 12 (1.87%) |
| FY 2024 | 681 | 648 (95.15%) | 21 (3.08%) | 12 (1.76%) |

Zero institutions in any of the three years carry `all_data_not_available` (status=`n`) or any pattern involving status=`n`. The "didn't report" code that the original three-case framing anticipated as a separate bucket from imputation does not appear at `column='Total'` cells.

### 4.4 Era-B Q9/Q11 cross-question NULL correlation at (inst, row, column='Total')

FULL OUTER JOIN of Q9 Total-column rows against Q11 Total-column rows on (inst_id, row), where `q9_state` / `q11_state` distinguish row-absent vs. value-present (no value-NULL cases observed; see §4.1):

| Year | total joined cells | Q9 row absent / Q11 value present | Q9 value present / Q11 row absent | both present |
|---:|---:|---:|---:|---:|
| FY 2017 | 16,351 | 4,592 (28.08%) | 2,281 (13.95%) | 9,478 (57.97%) |
| FY 2024 | 16,660 | 3,684 (22.11%) | 1,177 (7.06%) | 11,799 (70.82%) |

Reading: at the (institution, discipline) grain, **22–28% of cells have nonfederal R&D but no federal R&D, and 7–14% have federal but no nonfederal**. The asymmetry is large and persistent; it is the dominant NULL pattern on the era-B reconstruction's input side.

### 4.5 Total-row completeness sanity check

For both Q9 and Q11, both spot years: every distinct (inst_id, row) pair that has any column also has the `column='Total'` row (zero exceptions across 4 question×year combinations, 54,288 total cells). FY24 Guide page 8's "data record present for total rows regardless" claim is empirically true at the per-question total grain.

Every era-B institution that emits any Q9/Q11 Total-column row also emits the `row='All'` institution-level rollup (100% across both spot years). The "row absent at (inst, discipline)" case is genuinely about *that discipline*, not about the institution skipping the question entirely.

## 5. Recommendation

> **Option A (NULL-as-zero) is empirically correct for the row-absent case at the cell grain — but the methods note must say so as "row-absent-as-zero," and Skipper recommends adding a `quality_flag` column to the schema to preserve the imputation flag for the ~3% imputed rows.**

The recommendation has three parts:

### 5.1 Reconstruction rule semantics

The rule `Q9 NULL + Q11 value = Q11 value` survives, with the semantic clarification that "Q9 NULL" means "Q9 row absent at this (inst, discipline) cell" — not "Q9 row present with a NULL value." The Guide's row-presence-only-when-nonzero rule (page 8 / page 23) means row-absent IS the genuine-zero signal. Cases (a) and (d) merge: row-absence at a leaf cell IS the genuine-zero encoding. Imputation does not produce row-absences; it produces rows with status=`i` and a numeric value.

A FULL OUTER JOIN at (inst_id, year, raw_row_label, column='Total') with COALESCE(value, 0) on each side is the correct reconstruction primitive. This matches §14.2 Option A in arithmetic, but the methods note framing changes from "treat NULL as 0" to "row-absence at a leaf is the Guide-documented encoding for zero."

### 5.2 Add a `quality_flag` column to the schema

Currently §1 of the scoping doc lists 18 columns plus `form_type` (19th) added at §9.1 short-form handling. **Recommendation: add `quality_flag VARCHAR` as the 20th column.**

Values:
- `'reported'` — status blank in raw (the dominant case, ~93–97% of rows).
- `'imputed'` — status `i` in raw (the ~3–7% NSF-imputed share).
- `'estimated'` — status `e` (era-A only; ~0.00% in practice; preserved for completeness).
- `'unspecified_zero'` — status `u` (FY 2017 only, on non-Total columns only; preserved for fidelity).

Cost: one extra VARCHAR column on every row of the panel. ~20 bytes per row × ~1.5M rows estimated = ~30 MB uncompressed; parquet compression brings it to a few hundred kB given the 4-value cardinality.

Benefit: a deposit consumer who wants to filter to *only reported values* can do so trivially. Without the column, the imputation signal is lost at parquet-write time and the deposit ships ~3% imputed-but-unflagged values that look identical to reported values. That's a methodologically loaded silent-treatment choice the deposit should not make on a 4–5% mass.

A consumer who doesn't care reads through; a consumer who does (a researcher recomputing institution-level R&D excluding NCSES imputations, a journalist asking "are these the institution's own numbers?") gets a clean filter.

### 5.3 Reconstruction rule's `quality_flag` propagation

When a reconstructed `source_class='all_source'` row is written for era B, its `quality_flag` propagates as the **least-good of the two component flags** with the four-step ladder:

1. If both Q9 and Q11 carry `'reported'` → `'reported'`.
2. If either carries `'imputed'` → `'imputed'`.
3. If either carries `'estimated'` → `'estimated'`.
4. Row-absent contributes nothing to the flag (the row-absent side is the documented-zero side; it does not poison the present side's quality flag).

Rationale: if Q9 is reported and Q11 is imputed, the reconstructed all-source value is partially imputed; the flag should say so. The reconstruction rule documentation in `crosswalks/era_b_reconstruction_rule.yaml` carries the canonical statement; the methods note translates.

---

# Corrected era-B-wide baseline (locked 2026-05-10 PM)

**Authored:** Skipper, 2026-05-10 PM (HD 2.4.d Stage 9 disposition probe; Vision verdict δ + γ-allow).
**Probe:** `etl/spikes/probe_era_b_status_u_full.py` + `_output.txt`.
**Scope:** All era-B years (FY 2010–2024), all questions, all columns, standard-form + short-form. Coverage breadth chosen to match what the W4 lock's "FY-2017-only / non-Total-only" empirical claim would actually defend; the original three-spot-year sample (FY 2008 / 2017 / 2024) was empirically insufficient.

## 6. Why the baseline was revised

The initial characterization (§§1–5 above) concluded `status='u'` was "FY 2017 only, non-Total columns only, 244 occurrences." HD 2.4.b round 1 surfaced 9 panel-emitting rows at FY 2020 Q14 `column='Total'` violating both clauses. The HD 2.4.d disposition probe extended scope from three spot years to all 15 era-B years + short-form, and the findings disproved the original conclusion on every axis:

- The sampling missed FY 2010, 2011, 2012, 2013, 2014, 2015, 2016, 2018, 2019, 2020, 2021, 2022 (12 of the 15 era-B years).
- `status='u'` is a routine NCSES code emitted across 13 of 15 era-B years (2010–2022); FY 2023+ retires it.
- 106 distinct institutions emit it; 56 emit across multiple years; the dominant emission location is `column='Institution funds'` on `Nonfederal expenditures by field and source` (Q11), but Q14 column='Total' emerges in FY 2020+.
- The 9 panel-emitting rows are a real institution-specific encoding pattern at one HBCU (institution `'003446'` = South Carolina State University, Orangeburg, SC).

The original conclusion was a **sampling artifact**, not a methodological commitment. The methodology lesson — three-spot-year sampling for cross-temporal NCSES encoding patterns produces wrong baselines — is recorded as a process seed candidate at `seeds/research-seeds.md` Part 2 (2026-05-10) and as a locked-decisions entry at `PANEL_SKIPPER.md` §8 (sampling methodology entry, 2026-05-10 PM).

## 7. Corrected empirical baseline

### 7.1 Per-year `status='u'` counts (standard-form HERD CSVs)

| Year | Total raw rows | `status='u'` rows | Share |
|---:|---:|---:|---:|
| FY 2010 | 231,499 | 411 | 0.18% |
| FY 2011 | 264,087 | 874 | 0.33% |
| FY 2012 | 231,425 | 643 | 0.28% |
| FY 2013 | 226,394 | 521 | 0.23% |
| FY 2014 | 226,063 | 407 | 0.18% |
| FY 2015 | 227,533 | 269 | 0.12% |
| FY 2016 | 230,494 | 266 | 0.12% |
| FY 2017 | 238,032 | 244 | 0.10% |
| FY 2018 | 237,620 | 117 | 0.05% |
| FY 2019 | 240,447 | 131 | 0.05% |
| FY 2020 | 242,031 | 198 | 0.08% |
| FY 2021 | 241,265 | 200 | 0.08% |
| FY 2022 | 248,578 | 188 | 0.08% |
| **FY 2023** | 258,843 | **0** | **retired** |
| **FY 2024** | 264,321 | **0** | **retired** |
| **Total era-B** | 3,608,632 | **~4,469** | **~0.124%** |

`status='u'` rises through FY 2011, declines through FY 2018–2019, stabilizes ~200/year FY 2020–2022, then retires. The pattern reads as a NCSES-managed code with a non-trivial usage history.

### 7.2 Where `status='u'` appears (breakdown by question / column, panel-relevant subset)

The vast majority of `status='u'` rows sit on per-source-class columns on Q11 (`Nonfederal expenditures by field and source`) — `column='Institution funds'`, `'All other sources'`, `'Nonprofit organziations'` [sic — spelling preserved in raw], `'Business'`, `'State and local government'`. Stage 5's `column='Total'` filter excludes all of these from the panel by construction.

The panel-relevant subset (rows surviving Stage 5's filter to enter `herd_panel.parquet`) is:

| Year | Question | Column | Rows | Institutions |
|---:|:---|:---|---:|---:|
| FY 2020 | `Capitalized equipment expenditures by field and source` (Q14) | `Total` | 9 | 1 (SCSU) |

That is **the entire panel impact** of the revised baseline: 9 rows at one institution in one year on the Q14 path. The other ~4,460 era-B `status='u'` rows sit on non-Total columns that Stage 5 excludes.

### 7.3 Institution-level emission pattern

106 distinct institutions emit `status='u'` across era-B 2010–2022. 56 emit across multiple years. Several emit consistently for 10+ consecutive years (Occidental College, Santa Clara University, University of the Pacific, James Madison University, University of Alaska Fairbanks, others). Pattern is predominantly smaller / less-research-intensive institutions and HBCUs — the population for which `status='u'` is a routine encoding, not an anomaly.

Institution `'003446'` = **South Carolina State University** (Orangeburg, SC; `hbcu_flag='1'`; PhD-granting public HBCU). SCSU emits `status='u'` across FY 2010, 2011, 2012, 2019, 2020, 2021, 2022 (7 years). Only FY 2020 has rows at `column='Total'` for Q14 specifically. The pattern is not anomalous to SCSU; it's anomalous to "Q14 `column='Total'`" — most institutions that emit `status='u'` do so on Q11 non-Total source columns, but SCSU in FY 2020 emitted it on Q14 Total.

### 7.4 Short-form

FY 2012–2022 short-form CSVs: zero `status='u'` rows. FY 2023 short-form: 3 `status='u'` rows (which column not yet characterized; not panel-affecting per Stage 5's filter discipline). FY 2024 short-form: zero. Short-form behavior is broadly parallel to standard-form's retirement pattern (FY 2023+ retired) with one residual occurrence in FY 2023.

### 7.5 FY 2023+ retirement

Both FY 2023 and FY 2024 raw HERD files contain zero `status='u'` rows in standard form. FY 2023 short-form has 3 residual rows. FY 2024 short-form is clean.

The FY24 Guide documents `status='u'` as a valid code (pages 10/25) but the raw data emits zero instances in 2023–2024. NSF appears to have changed the encoding convention without Guide documentation of the convention change. This is itself a publication-regime discontinuity (the sixth instance per `seeds/research-seeds.md` 2026-05-10 entry); cataloged as a methodologically interesting finding but not a build-blocker (the retirement is observable in the data; the assertion defends against resumption).

## 8. Locked baseline + Stage 9 assertion design

### 8.1 `quality_flag` value semantics (locked 2026-05-10 PM)

The `unspecified_zero` enum value's locked semantic per the corrected baseline:

> `unspecified_zero` — raw `status='u'` (case-folded via `UPPER(status)='U'` per HD 2.4.b round 1). The FY24 Guide documents `'u'` as a valid status code; the empirical scope of its emission across era-B 2010–2022 (~4,000 rows, 106 institutions, retired FY 2023+) is documented in this deposit's quality-flag characterization. The panel-emitting subset (rows surviving Stage 5's `column='Total'` filter) is 9 rows at FY 2020 Q14 / institution `'003446'` (South Carolina State University). Era-A does not emit `status='u'` (the case-fold catches both lowercase and uppercase; the empirical evidence is zero era-A occurrences across the full 1973–2009 scan at `etl/spikes/probe_status_c_codeset.py`).

### 8.2 Stage 9 assertion (locked 2026-05-10 PM)

The three-tier corrected baseline drift-defense assertion replaces the original "FY-2017-only / non-Total-only" assertion. Loud-fail conditions:

1. **Era-A `unspecified_zero` rows raise.** Era-A files do not emit `status='u'` (verified across 1973–2009). Any era-A panel row with `quality_flag='unspecified_zero'` is a build bug.
2. **Era-B `unspecified_zero` rows in years outside 2010–2022 raise.** FY 2023+ retired the encoding; resumption is a publication-regime change that warrants panel reconvene.
3. **Era-B 2010–2022 `unspecified_zero` rows are allowed.** Per the corrected baseline.

The assertion's failure message names the offending (year, institution_id, question, column, raw row label) tuple so the operator can disposition.

### 8.3 Kill condition for the revised baseline (Vision-locked)

External reviewer at deposit time (month 3 sponsor-ring touch) reads the revised W4 lock + methods-note characterization and either (a) flags the broader status='u' acknowledgment as overclaim against NCSES guidance, or (b) surfaces a published NCSES codeset-history document that resolves the `'u'` semantic differently than this characterization assumes. Either signal triggers panel reconvene on the lock framing.

### 8.4 Cross-references

- `PANEL_SKIPPER.md` §8 W4 amendment entry (2026-05-10 PM) — locked-decisions log entry recording the amendment and Vision verdict.
- `PANEL_SKIPPER.md` §8 sampling methodology entry (2026-05-10 PM) — process seed for AI-moat publication candidacy.
- `docs/methods_notes/herd_panel_etl_scoping.md` §1 `quality_flag` value semantics (revised 2026-05-10 PM).
- `docs/methods_notes/herd_panel_etl_scoping.md` §6.2 Stage 9 sanity assertion text (revised 2026-05-10 PM).
- `crosswalks/era_b_reconstruction_rule.yaml` `quality_flag_propagation.consumer_contract` (revised 2026-05-10 PM).
- `docs/hd_2_1_open_items.md` "FY 2020 status='u' on Q14 column='Total'" entry (disposition recorded).
- `seeds/research-seeds.md` Part 1 2026-05-10 entry (sixth-instance addition for publication-regime stability pattern); Part 2 2026-05-10 entry (sampling methodology lesson).
- `CLAUDE.md` §6 codeset-extension policy (codeset-extension vs. empirical-scope-adjustment distinction).

## 6. Schema implication

**One column added (`quality_flag VARCHAR`).** §1 of the scoping doc moves from 19 columns (post-`form_type` add at §9.1) to 20 columns. Position recommendation: between `value_type` and `source_questionnaire_no` so the value-axis columns (`value, unit, value_type, quality_flag`) are contiguous.

Schema migration cost relative to the current §1 lock: zero — the column is added before HD 2.4.a starts, not retroactively.

The personnel sibling does **not** retroactively gain a `quality_flag` column at this scoping pass. Q15/Q16 microdata's `status` distribution was not characterized in this spike (out of scope; the spike's questions are Q9/Q11/era-A field). Personnel sibling parity is a HD 2.4.i methods-note touch-up if the imputation rate on Q15/Q16 is materially nonzero — flagged for the maintainer's downstream consideration but not gated by this finding.

## 7. Methods-note implication (HD 2.4.i)

One paragraph for §6 ("What the deposit ships") of `docs/methods_notes/reconstructive_harmonization.md`, draft:

> **NULL semantics in the harmonized panel.** HERD's raw CSVs encode missing-value semantics through a combination of row-presence and a `status` column. Per the FY24 Guide (pages 8 and 23), a leaf-level row appears only when the institution's reported value is nonzero; row-absence at a (institution, discipline, source-class) cell is therefore the documented encoding for zero R&D in that cell, not a missing-data signal. Total rows always emit a record. NCSES imputation produces present rows with `status='i'`; era A additionally documents `status='e'` (estimated) and both eras document `status='n'` (data not available). At the three spot years probed (FY 2008, FY 2017, FY 2024), `status='n'` does not appear at any in-scope cell, `status='e'` appears once in FY 2008 and never elsewhere, and `status='i'` covers ~3% of FY 2024 Total-column cells. The harmonized panel preserves this provenance through the `quality_flag` column on every row: `'reported'` for blank-status rows, `'imputed'` for status='i', `'estimated'` for status='e', `'unspecified_zero'` for the FY 2017 `status='u'` rows on non-Total columns. The era-B reconstruction rule (Q9 + Q11) propagates the least-good of the two component flags onto the reconstructed all-source row. Consumers filtering to institution-reported values only can subset on `quality_flag='reported'`; the default deposit view includes imputed values consistent with NSF's published national totals.

## 8. Methodologically loaded surfaces beyond the original three-case framing

1. **Case (d) "row absent" is the dominant null pattern, not in the original (a)/(b)/(c) trio.** The spike's empirical data reframed the question.
2. **Status `u` in FY 2017 is undocumented in the FY24 Guide** but appears 244 times on non-Total columns. Preserved as a fourth `quality_flag` value for fidelity. Disposition: include in the deposit; flag the discrepancy in the methods note as a Guide-vs-data drift; do not block on it (no Total-column impact).
3. **The "NSF-labeled didn't report" case (`status='n'`) does not appear at all** at in-scope cells. The maintainer's case (c) is documented but not in use at the field-level grain; row-absence (case d) is how unavailability is operationally encoded.
4. **Era A's `e` (estimated) code is effectively retired by FY 2008** (one occurrence in the entire file). Preserved in the schema for completeness back to 1972, but methodologically it is a Guide-documented code that NCSES ceased exercising. The methods-note paragraph names it but does not lead with it.
5. **The Q9/Q11 row-absence asymmetry (22–28% Q9-absent vs. 7–14% Q11-absent at FY 2017/2024)** is itself methodologically interesting — institutions emit Q11 rows for disciplines where they have *only* nonfederal funding more than twice as often as the inverse. This is consistent with federal funding being concentrated in fewer disciplines than nonfederal funding for the marginal institution. Surface for downstream attention, not for HD 2.4 to resolve.

## 9. Cross-references

- Spike: `etl/spikes/spike_herd_null_characterization.py` (throwaway, not promoted).
- FY24 Guide §1.2 / §1.3.1 / §2.2 / §2.3: `data/raw/herd/Guide To Herd Data Files FY24.pdf`; text mirror at `docs/source_documents/herd_fy24_guide.txt`.
- ETL contract: `docs/methods_notes/herd_panel_etl_scoping.md` §14.2 (the framing this spike amends), §1 (schema column count to update), §6.2 Stage 6 (reconstruction rule semantics).
- Era-B reconstruction rule: `crosswalks/era_b_reconstruction_rule.yaml`.
- Loader: `etl/_load.py` (lines 437/471 — `TRY_CAST(data AS DOUBLE) AS value`; `status` preserved verbatim).
- Personnel sibling pattern (no `quality_flag` column at deposit time): `etl/build_herd_personnel.py`. Personnel-side imputation characterization is a separate HD 2.4.i touch-up if downstream consumers ask.
