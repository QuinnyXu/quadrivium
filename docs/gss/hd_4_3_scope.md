# HD 4.3 — GSS data-layer completion scope (Phase A surface)

**Status:** scope-first surface for maintainer sign-off **before** the Phase-B
build. Names the §5 published-ground-truth anchors, the field-code reference, and
the Race + PD_NFR schemas; states what the maintainer must stage. **Date:**
2026-06-02. Per the deliberate gate→build checkpoint discipline — do not collapse
it.

**This increment:** close the three open gaps in the GSS data layer — (1) no §5
published anchor yet, (2) Race + PD_NFR not built, (3) `field_coarse/fine` NULL.
**Deferred to the next increment (do NOT start):** the GSS methods note, the RH
boundary decompositions, the v4 tag / Zenodo re-mint.

---

## 1. §5 published-ground-truth anchors — the NCSES GSS 2023 report (NSF 25-317)

Source report: **NSF 25-317**, *Survey of Graduate Students and Postdoctorates in
Science and Engineering 2023* (ncses.nsf.gov/pubs/nsf25317). Detailed tables are
published per-table at `ncses.nsf.gov/pubs/nsf25317/table/{N}` (Excel + PDF
download). **The sandbox cannot reach NSF to stage these — the maintainer stages
them** (as with HERD Table 26 and FedSupport Table 12). The longitudinal tables
(1975–2023 / 1977–2023) are ideal: they anchor every year of our panel, not just
2023.

**Support panel (`gss_support.parquet`, already built — anchored FIRST in Phase B):**
| Anchor table | Title | Reconciles our | Our 2023 value to match |
|---|---|---|---|
| **Table 1-6** | Primary source of support for FT grad students in SEH: 1975–2023 | source_class split | federal 82,764 / nonfederal 261,737 / self 254,087 (= 598,588) |
| **Table 1-7** | Detailed primary source of **federal** support, FT grad: 1975–2023 | funding_agency split | NIH 23,172 · NSF 21,209 · DOD 9,171 · DOE 5,757 · USDA 3,332 · NASA 2,178 · HHS-other 3,314 · other-fed 14,631 (= 82,764 federal) |
| **Table 1-8** | Primary mechanism of support, FT grad: 1975–2023 | support_mechanism split | fellowship / traineeship / RA / TA / other (to compute in Phase B) |

(GSS support is **primary-source** — each FT student counted once; our fed+nonfed+self
sum to the FT total exactly, confirming the semantics. So 1-6/1-7/1-8 are exact
anchors, longitudinal.)

**Race / enrollment panel (`gss_race.parquet`):**
| Anchor table | Title | Reconciles |
|---|---|---|
| **Table 1-2a** | Sex of graduate students / postdocs / NFRs: 1977–2023 | total grad by sex, longitudinal |
| **Table 4-3** | Master's & doctoral students by enrollment intensity: 2023 | FT vs PT total (our 598,588 FT / 219,507 PT = 818,095) |
| **Table 1-11a / 1-11b** | Master's / doctoral enrollment by detailed field: 2017–23 | degree_level × field (post-2017) |
| **Table 2-4** | Grad students by degree program, citizenship, ethnicity, race: 2023 | race × gender |

**PD_NFR panel (`gss_pd_nfr.parquet`):**
| Anchor table | Title | Reconciles |
|---|---|---|
| **Table 1-9b** | Postdoctoral appointees in science broad fields: 1979–2023 | postdoc total, longitudinal (our 2023 postdocs = 65,850) |
| **Table 3-2 / 3-4** | Source / detailed federal source of support for postdocs, by broad field: 2023 | postdoc support × agency |
| **Table 1-2a** | (above) | NFR total by sex |

**Staging ask (maintainer):** the Excel/PDF for the tables above from NSF 25-317.
Minimum to unblock Phase-B item 1 (the existing Support panel): **Tables 1-6,
1-7, 1-8.** Race + PD_NFR anchors stage alongside their builds.

## 2. Field-code reference — gss_code → field_coarse / field_fine

GSS fields use **NCSES's Taxonomy of Disciplines (TOD)**, mapped to **IPEDS CIP
codes**; in 2020 the GSS-eligible CIP list was revised (TOD update; data-science
and medical-clinical-sciences codes added). The `gss_code` → field-name + broad-field
crosswalk lives in the GSS **technical notes** — specifically the field-code
tables (the 2020 cycle published these as **A-17 / A-18a / A-18b**), and/or the
**GSS PUF codebook / user guide**. This is the GSS analogue of HERD's
`discipline_coarse.csv` / `discipline_fine.csv`.

**Staging ask (maintainer):** the GSS field-code/TOD reference — either the
technical-notes field tables (A-17/A-18a/A-18b, current cycle) or the PUF
codebook carrying the numeric `gss_code` → field-name + broad-field mapping.
(Auto-fetch failed: the 2021 PUF user-guide PDF returned corrupt over the wire;
the maintainer's staged copy is the reliable source.)

**Gating rule (per the task):** if the field-code reference can't be staged
promptly, build the parquets with `field_coarse/fine` still NULL and slip **only**
the field-code crosswalk — it must not block §5 reconciliation or the Race/PD_NFR
builds (items 1–2).

## 3. Race + PD_NFR schemas (long-format, sibling parquets)

Same pattern as `gss_support`: column crosswalk → long, native-UNITID-keyed,
non-zero grain (omitted = structural zero), `degree_level` carried.

**`gss_race.parquet`** — enrollment/demographic. Source: Race sheet (122 pre /
293 post cols; post-2017 prefixes pt=30, ft=60, ma=90, dr=90). Canonical tuple:
```
… ids …, year, era, enrollment_status, degree_level, gender, race, value, …
  enrollment_status ∈ {part_time, full_time, full_time_first_year}   # pt/ft/ft_frst
  degree_level      ∈ {all_grad, masters, doctoral}                   # ft/ma/dr
  gender            ∈ {total, men, women}
  race              ∈ {all_races, white, black, hispanic, asian, pacific,
                       american_indian, multiracial, foreign, unknown}
```
Crosswalk `crosswalks/gss/race_column_map.csv`. The race taxonomy is **pre-bridged
by NCSES** (legacy `asian_pi_98`/`other_98` run parallel to OMB-1997 categories
1972–2016, retired losslessly at 2017 — HD 4.1 Check 3); the crosswalk maps the
legacy columns to a documented `race=*_legacy` value (kept, not dropped, per §4).

**`gss_pd_nfr.parquet`** — postdoc + non-faculty-researcher. Source: PD_NFR sheet
(207 pre / 191 post cols; post-2017 prefixes pd=153, nfr=15 — itself recoded at
2017). Two populations:
```
  population ∈ {postdoc, nonfaculty_researcher}
  postdoc crossings: race × gender; support_mechanism × source_class × funding_agency;
                     degree_type (medical/nonmedical/dual) × citizenship
  nfr crossings:     degree_type × gender
```
Crosswalk `crosswalks/gss/pd_nfr_column_map.csv` (the largest — the postdoc
support axis reuses the Support panel's mechanism/agency vocabulary, so the
controlled vocabulary is shared).

## 4. SAS↔XLSX provenance cross-check — disposition

**Recommendation: the §5 published-total anchor SUPERSEDES the SAS↔XLSX
byte-reconciliation; no `pyreadstat`, not even one-time.** Rationale: once each
panel reconciles to the published NCSES GSS national totals (the authoritative
ground truth, §5), the SAS-vs-XLSX internal cross-check is redundant — both are
NCSES renderings of the same data, and the published table is the higher anchor
than either. This keeps the toolchain `pyreadstat`-free at every stage
(acquisition included), strictly cleaner than a one-time acquisition dependency.
The `sas7bdat` remains the unread provenance sibling (a valid file; HD 4.1).
*(Alternative on request: a one-time acquisition-only `pyreadstat` row-count
cross-check — but the published anchor makes it unnecessary.)*

## 5. Phase-B build order (on authorization + staged refs)

1. **§5 anchor on the existing `gss_support.parquet` first** — reconcile to Tables
   1-6/1-7/1-8; add the external-anchor section to
   `validation/reports/gss/gss_support_validation.md`. Closes the MVP's open gap.
2. **Race + PD_NFR parquets** — crosswalk → long; two-number spine receipt + §5
   anchor per panel; 3-build determinism; MANIFEST pins.
3. **Field-code crosswalk** → fill `field_coarse/fine` across all three parquets
   (gated on the staged reference; slips alone if unstaged).
4. Hygiene gates throughout (generator UTF-8/LF, provenance `-text`, index-blob
   zero-NUL, provenance==MANIFEST).

The §5-anchor + field-code + SAS-disposition decisions are logged to
`seeds/overrides.md` §12 at authorization.

**STOP — awaiting maintainer staging of the reference docs + Phase-B authorization
(live OK).**
