# HD 4.2 — GSS build scope (Support-first MVP)

**Status:** scope memo for maintainer review **before** the loader is coded and
the first GSS dataset is committed (the gate I committed to at acquisition).
Mirrors the HD 3.1 → HD 3.2 gate → scope → build cadence. **Date:** 2026-06-02.

**Authorized shape (2026-06-02):** HERD-style **sibling parquets**; **Support-first
MVP** (build the funding face first, then Race + PD_NFR). Gate evidence:
`docs/gss/hd_4_1_gate_findings.md`. Acquisition done (`12bb69f`): 53 years × 3
sheets converted to gitignored UTF-8/LF CSVs by `etl/acquire_gss.py`; zips
SHA-pinned in `data/raw/MANIFEST.md`.

---

## 1. Output shape — three sibling parquets

Each GSS source sheet harmonizes to its own long-format parquet at the sheet's
natural grain (the `gss_` filename-prefix namespace, §10):

| Parquet | Source sheet | Grain | Status |
|---|---|---|---|
| **`gss_support.parquet`** | Support | unitid × year × field × gender × **mechanism × source-class × agency** | **THIS MVP** |
| `gss_enrollment.parquet` | Race | unitid × year × field × enrollment-status × **race × gender** | deferred (next increment) |
| `gss_postdoc.parquet` | PD_NFR | unitid × year × field × postdoc/NFR × support/degree/citizenship | deferred |

This mirrors `herd_panel` / `herd_personnel` / `herd_panel_attributes` — clean
per-sheet grain, independently validatable, joinable on `unitid × year × field`.

## 2. `gss_support.parquet` — long-format schema

Wide → long collapse of the Support sheet (119 cols pre-2017 → 365 post-2017),
following the HERD §4 long schema convention:

```
unitid, institution_name, gss_school_id, gss_code, hdg_code,
field_coarse, field_fine,            # field taxonomy (crosswalk §4)
state, hbcu_flag, land_grant_flag,
year, era,                           # era ∈ {pre2017, post2017} at the 2017 redesign
enrollment_status,                   # full_time  (Support is FT-only by instrument)
degree_level,                        # all_grad (continuous) | masters | doctoral
                                     #   ma_/dr_ split is POST-2017-only; all_grad = pre-2017 ft_ AND post-2017 ft_
gender,                              # all | total | men | women
                                     #   gender crossing is PRE-2017-only in Support; post-2017 Support gender = all
support_mechanism,                   # all | fellowship | traineeship |
                                     #   research_assistant | teaching_assistant | other | self_support
source_class,                        # all_sources | federal | nonfederal | self_support
funding_agency,                      # all | DOD | NIH | HHS_other | NSF | USDA | NASA | DOE |
                                     #   other_federal | nonfed_institutional | nonfed_other_us | nonfed_foreign
value, unit, value_type,             # headcount, count, reported
quality_flag, source_sheet, source_file, notes
```

The native id columns (`unitid`, `gss_code`, `hdg_code`, Carnegie vintages,
`hbcu_flag`, `land_grant_flag`) are carried verbatim from the source; `unitid` is
the §4 canonical join key (campus-grained — Check 4).

## 3. The support-taxonomy crosswalk (the methods-note core)

A `crosswalks/gss/support_column_map.csv` mapping **every** Support wide-column
name → its canonical tuple `(population, gender, support_mechanism, source_class,
funding_agency)`, one `decision_rationale` per row (a methods-note sentence each).
Two era-blocks, harvested verbatim (à la HERD's `_harvest/`):

- **Pre-2017** (`ft_<gender>_<source>_v`, `ft_<mech>_<source>_v`): e.g.
  `ft_tot_fed_nsf_v` → (grad_student, total, all, federal, NSF);
  `ft_felshp_fed_hhs_nih_v` → (grad_student, all-gender, fellowship, federal, NIH).
- **Post-2017** (`[<deg>_]ft_<mech>_<source>_v`, deg ∈ {∅ = all_grad, `ma` =
  masters, `dr` = doctoral} — verified in the converted headers: `ft` / `ma` /
  `dr` each carry the same 114-column mechanism×source block): e.g.
  `ft_fel_fed_nsf_v` → (all_grad, gender=all, fellowship, federal, NSF);
  `dr_ft_ra_fed_nih_v` → (doctoral, gender=all, research_assistant, federal, NIH).

**2017 boundary as a Reconstructive Harmonization object.** The recode is
clause-(a) reconstructible (each era's columns map cleanly to canonical tuples)
and clause-(b) decomposable. Named components: (i) **secondary-axis swap** — the
Support sheet's secondary disaggregation changes from **gender** (pre-2017:
`ft_tot`/`ft_men`/`ft_wmen`) to **degree-level** (post-2017: all-grad `ft_` +
`ma_`/`dr_`). Gender detail is therefore **pre-2017-only** in Support (gender
lives in the Race sheet throughout), and degree-level detail is **post-2017-only**;
(ii) **agency relabel** `hhs_nih` / `hhs_oth` → `nih` / `hhs` (continuous);
(iii) **mechanism abbreviations** `felshp/rsch_asst/tchg_asst` → `fel/ra/ta`.
**The continuous bridge** is the all-gender / all-degree core: the canonical
tuple *(all_grad, gender=all, ⟨mechanism⟩, ⟨source⟩, ⟨agency⟩)* maps pre-2017
`ft_tot_⟨source⟩_v` / `ft_⟨mech⟩_⟨source⟩_v` ↔ post-2017 `ft_⟨mech⟩_⟨source⟩_v`
and must form a continuous 2016→2017 series (the build's continuity receipt; any
tuple that does not is footnoted as era-bounded). This is the GSS analogue of
HERD's era-B reconstruction rule + 2008→2011 decomposition: the funding face is
continuous at the all-grad core, with the gender axis (pre) and the degree axis
(post) as the named, era-bounded components.

A `crosswalks/gss/field_taxonomy.csv` (`gss_code`/`hdg_code` → `field_coarse`/
`field_fine`) is the second crosswalk; the field grain sits below `unitid` and
does **not** touch identity (Check 4).

## 4. Validation plan (ships with the parquet, §5)

1. **Two-number spine receipt** vs `crosswalks/_shared/institution_identity.csv`:
   institution-match AND **count-weighted** match (the gate measured 97–99% /
   93–99.7%); publish the unmatched residual; the spine expands by the ~19
   GSS-only institutions (Check 2).
2. **Cross-sheet reconciliation:** Support all-sources FT total == Race FT total
   per institution-year (gate confirmed exact: 1975 = 219,648; 2008 = 449,613).
3. **Published-total anchor:** the across-field FT+PT national total reproduces
   the NCSES GSS published enrollment (2023 = 818,095; 2022 = 798,534) — to be
   pinned against the NCSES GSS 2023 data table at build time.
4. **2017 boundary decomposition** (clause-b): the named recode components above,
   sized — the methods-note slot-2 contribution figure.
5. v3.0 deposit hygiene throughout: generator UTF-8/LF, A1 two-build SHA, A1b
   index-blob validity, provenance==MANIFEST.

## 5. Increment boundary

This memo + the two crosswalks + the `gss_support` loader + its validation report
are the MVP increment. **The loader and the first `gss_support.parquet` dataset
commit are NOT made until this scope is signed off.** Race + PD_NFR siblings, the
full methods note, and any spine-expansion commit follow as separate increments.

**Open decisions for sign-off:**
- (a) the canonical `funding_agency` / `support_mechanism` value sets above —
  accept as the controlled vocabulary, or adjust?
- (b) the post-2017 degree-level split (`ma_` masters / `dr_` doctoral, with the
  `ft_` all-grad core continuous across 2017) — carry the full `degree_level`
  dimension now, or ship the all-grad (`ft_`) continuous core first and defer the
  masters/doctoral rows to a later increment? (The pre-2017 gender axis is carried
  regardless — it is Support's only disaggregation there.)
- (c) crosswalk home — land `crosswalks/gss/` per the §10 per-survey subtree
  (clean, no HERD impact). **Note:** the §10-planned HERD flat-`crosswalks/*.csv`
  → `crosswalks/herd/` migration did **not** fire at FedSupport (HERD crosswalks
  are still flat at the root; `crosswalks/fedsupport/` exists). §10 says to tie
  that move to a moment `etl/build_herd_panel.py`'s read paths are already being
  touched — which GSS does **not** do — so the recommendation is to land
  `crosswalks/gss/` now and keep the HERD migration deferred to its next
  read-path touch (flagged here so it is not lost again). Confirm, or fold the
  HERD migration in now as a standalone move?
