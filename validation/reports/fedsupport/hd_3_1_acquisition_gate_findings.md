# HD 3.1 — Federal S&E Support module: acquisition de-risking gate findings

**Sanity-receipt / gate findings report.**
Author: Skipper. Date: 2026-05-29.
Spike (throwaway): `etl/spikes/spike_fedsupport_acquisition_probe.py`.
Dataset #2: NSF *Survey of Federal Science and Engineering Support to
Universities, Colleges, and Nonprofit Institutions* (Federal S&E Support
Survey). Anchor year FY 2023.

> This is a gate report, not a harmonization. Per
> `[[feedback-etl-spike-scoping]]` the spike was pointed at two gate
> questions + three kill conditions and stopped there. **K1 FIRED**
> (see §3). Per the stop conditions, HD 3.0 was **NOT** finalized; no
> artifact was staged into `data/raw/`. This report is the surface to
> Vision-via-principal.

---

## 0. Verdict at a glance

| Gate item | Finding |
|---|---|
| (i) Acquisition artifact | **Published data tables** (XLSX + PDF + ZIP), **NOT** a microdata PUF. Tables-not-PUF hypothesis CONFIRMED. |
| (ii) Institution identifier | **name + state only.** No UNITID, no `ncses_inst_id`, no NCSES internal ID — **same on both sides** of the vol-71 boundary. |
| $49B anchor composition | **Higher-ed-ONLY** (NOT all-performer). $49.0B / 1,110 institutions is the correct reconciliation target. No substrate trap. |
| K1 (name+state-only id) | **FIRED.** Forces a name-reconciliation crosswalk; moves join-key decision + budget. |
| K2 (artifact moves budget) | **PARTIAL.** XLSX-only native format (new-dep flag, resolved without a dep); column-taxonomy redesign at vol-71. Stable download URLs exist (provenance model holds). |
| K3 (boundary worse than 2010-HERD) | **DID NOT fire** on the identifier axis (scheme unchanged across boundary). A *column-taxonomy* discontinuity exists but is Reconstructive-Harmonization-native. |
| HD 3.0 branch | **Table-parse branch** (the Table-Builder/published-table acquisition branch), NOT the PUF-download branch. |
| Disposition | **STOP at gate. Surface to Vision.** Do not finalize HD 3.0. |

---

## 1. Gate question (i) — acquisition artifact: TABLES, not PUF

**Confirmed: published data tables requiring a parse. No microdata PUF.**

Evidence:

- The survey is **absent** from the NCSES microdata-PUF list
  (`https://ncses.nsf.gov/explore-data/microdata`). That list carries
  FFRDC, HERD, NSCG, NSRCG, NTEWS, SDR, GSS, S&E Research Facilities, and
  SESTAT — **not** Federal S&E Support. (Matches the prompt's leading
  hypothesis.)
- The FY 2023 data product is a **data-tables report, NSF 25-339** (the
  tables companion to the **NSF 25-341** InfoBrief). Tables ship as:
  - per-table **XLSX** (`.../tables/nsf25339-tabNNN.xlsx`)
  - per-table **PDF** (`.../tables/nsf25339-tabNNN.pdf`)
  - bulk **ZIP** (`nsf25339-data-tables-tables.zip`, "All Formats")
- An interactive **Table Builder** / IDS tool also exists
  (`https://ncsesdata.nsf.gov/ids/`), but the static per-table downloads
  carry **stable, predictable URLs** (verified by direct GET on three
  vintages). So unlike HERD's DST Table Builder (HD 2.4.g UI-navigation
  hazard), this survey gives a stable download-URL provenance model — the
  K2 "no stable download URL" sub-condition does **NOT** fire.

The higher-ed institution-level slice is **Table 12** ("...universities and
colleges, by state, outlying area, institution, and type of activity") and
**Table 13** (...by institution and agency). Nonprofit institution-level
data lives in separate tables (Table 32/33) — the higher-ed slice is
cleanly separable from the nonprofit and agency-grain data, so the K2
"higher-ed slice not separable" sub-condition does **NOT** fire.

### Runtime-format flag (new-dep, resolved without a dep)

The native institution-table format is **XLSX**, which the locked runtime
(`duckdb==1.5.2` + `pypdf==6.10.2`, CLAUDE.md §3 exact-only) does not parse
out of the box. Two no-new-pip-dep paths were verified working in this spike:

1. **DuckDB `excel` extension.** `INSTALL excel; LOAD excel;
   read_xlsx(...)` works on this machine with duckdb 1.5.2 and reads the
   Table 12 sheets correctly (label column A + ~6 numeric value columns).
   This is a DuckDB-managed extension, **not** a new `pyproject.toml`
   dependency. Caveat for the deposit cold-reader contract: the extension
   is fetched by DuckDB at runtime, which introduces a network dependency
   at build time and a DuckDB-extension-version surface that the lockfile
   does not pin.
2. **pypdf on the PDF sibling** (locked dep; Table-26 precedent in
   `data/reference/`). The PDF extracts cleanly — first-page text gave the
   full column header + institution rows verbatim (see §4 raw evidence).

**Recommendation (SURFACED, not decided):** for the eventual build, prefer
a **one-time xlsx→csv conversion at acquisition** (the staged raw artifact
becomes a CSV checksummed in `data/raw/`, loader uses `read_csv_auto` — the
existing `etl/_load.py` pattern, no new dep, no runtime extension fetch)
over either a runtime XLSX reader dep or a runtime `excel`-extension fetch.
The PDF is the provenance/audit sibling (mirrors the FY24 Guide PDF in
`data/raw/herd/` and the Table-26 anchors in `data/reference/`). This keeps
the cold-reader reproducibility contract (§3) intact. **This is a Vision /
principal-level acquisition-format call, not a coding question** — flagged
here, not silently chosen.

---

## 2. $49B anchor composition (methodological hold #1) — CONFIRMED higher-ed-ONLY

**The $49B / 1,110-institution anchor is higher-education-ONLY. It is the
correct reconciliation target. The HERD standard-form-vs-all-respondents
substrate trap does NOT recur here.**

Evidence (NSF 25-341 InfoBrief, verbatim):

- *"Federal agency obligations to higher education institutions for support
  of science and engineering (S&E) activities totaled **$49.0 billion** in
  FY 2023."*
- *"federal agencies obligated S&E funding to **1,110 institutions of higher
  education** in the United States."*
- The nonprofit universe is reported **separately**: *"total federal
  obligations to all nonprofit organizations for R&D and R&D plant totaled
  **$11.6 billion**"* (the "$12 billion" in the headline is the rounded
  nonprofit figure — a **different universe**, not part of the $49B).

Cross-check against the table itself (NSF 25-339 Table 12, "All states and
outlying areas" row, FY 2023): **All federal obligations = 48,961,658**
(dollars in thousands) = **$48.96B ≈ $49.0B**. The Table 12 grand total
reconciles to the InfoBrief higher-ed headline. The higher-ed slice is the
self-contained universe — no all-performer contamination.

So when HD 3.2 builds the reconciliation, the anchor is **$48,961,658
thousand across the FY2023 higher-ed institution rows of Table 12**, filtered
to higher-ed (Table 12 already is higher-ed-only). Do NOT free-sum across
higher-ed + nonprofit tables.

---

## 3. Gate question (ii) — institution identifier: name+state only, PER SIDE

**Reported per side of the volume-71 (FY2021–FY2022 redesign) boundary, per
methodological hold #2.**

The survey's "volume 71" redesign covers **FY 2021 + FY 2022** (the
web-based data-collection system was redesigned for volume 71). I sampled
three vintages spanning the boundary:

| Side | FY | Report | Table 12 grand-total ("All states") $000 |
|---|---|---|---|
| **PRE-redesign** | 2020 | NSF 22-342 | 39,122,152 |
| **boundary (vol-71 yr 1)** | 2021 | NSF 24-311 | 43,222,829 |
| **POST / ANCHOR** | 2023 | NSF 25-339 | 48,961,658 |

### Identifier finding — IDENTICAL on both sides

On **all three** vintages the institution-level row carries **only the
institution NAME, nested under a STATE header**. There is **no identifier
column of any kind**:

- Column A = `State, outlying area, and institution` (a hierarchical text
  label: a state row, e.g. `Alabama`, then indented institution rows, e.g.
  `Alabama A&M U.`, `Auburn U., Auburn`, `U. Alabama, The, Birmingham`).
- Columns B–H = **all dollar amounts** (type-of-activity breakdown).
- **No UNITID. No `ncses_inst_id`. No NCSES internal institution ID. No
  FICE.** The only join key available is the **abbreviated institution name
  + the state grouping**.

Per-side summary:

| | PRE (FY2020) | boundary (FY2021) | POST (FY2023) |
|---|---|---|---|
| Identifier present | name + state only | name + state only | name + state only |
| UNITID / ncses_inst_id / internal ID | none | none | none |

**The identifier scheme did NOT change across the volume-71 boundary** — it
was name+state on both sides. This is the single most important input to the
deferred §4 canonical-key decision.

### Name format is NSF-abbreviated (the real join cost)

The names are **NSF house-style abbreviations**, not IPEDS-canonical names:
`Auburn U., Auburn`, `U. Alabama, The, Birmingham`, `U. Alabama, The,
Tuscaloosa`, `Marine Environmental Sciences Consortium`. These will NOT
string-match IPEDS or HERD `inst_name_long` cleanly. A
name+state→UNITID/ncses_inst_id reconciliation crosswalk is required to join
this survey to HERD or IPEDS. That crosswalk is the dominant cost this gate
surfaces.

---

## 4. Raw evidence (PDF extract, FY2023 NSF 25-339 Table 12, page 1)

```
TABLE 12
Federal obligations for science and engineering to universities and colleges, by state, ou...
(Dollars in thousands)
State, outlying area, and institution | All federal obligations | R&D | R&D plant | Facilities and... | ...
All states and outlying areas 48,961,658 45,008,768 458,139 65,456 2,456,890 972,405
Alabama 879,493 637,770 9,937 0 81,378 150,408
Alabama A&M U. 16,751 12,480 0 0 3,550 720
Auburn U., Auburn 114,458 99,151 954 0 9,225 5,128
U. Alabama, The, Birmingham 394,162 364,699 0 0 26,319 3,143
```

The XLSX confirms the same shape (label col A + value cols B–G), verified via
DuckDB `read_xlsx` range read `A1:J30`.

### Column-taxonomy redesign at vol-71 (a real, RH-native discontinuity)

The **type-of-activity column set changed** across the redesign — a
discontinuity HD 3.2 must decompose, but **not** an identifier problem:

- **FY2020 (pre, 8 value cols):** All federal obligations | R&D | R&D plant |
  Facilities for instruction... | Fellowships, traineeships... | General
  support for S&E | Other S&E activities
- **FY2021 / FY2023 (post, 6 value cols):** All federal obligations | R&D |
  R&D plant | Facilities and equipment | S&E fellowships, traineeships... |
  Other general support

This is a column/measure taxonomy redesign at the vol-71 boundary — the
Federal S&E Support analog of the HERD-2010 instrument redesign. It is
**Reconstructive-Harmonization-native** (era-A vs era-B column crosswalk +
boundary decomposition) and is the kind of discontinuity this project
exists to handle. It is reported here so the deferred §4 addendum + the HD
3.2 scope budget anticipate it; it does **not** by itself block the gate.

---

## 5. Kill / surface conditions

### K1 — name+state-only identifier: **FIRED**

No UNITID / ncses_inst_id / NCSES internal ID on either side of the
boundary. Forces a name+state→canonical-id reconciliation crosswalk before
this survey can join to HERD/IPEDS. **Moves the join-key decision and the
budget.** This is the gate's headline finding and the reason HD 3.0 was not
finalized. **SURFACE to Vision.**

### K2 — acquisition artifact moves budget: **PARTIAL**

- Stable download URLs exist → provenance model holds (NOT fired).
- Higher-ed slice cleanly separable from nonprofit + agency-grain (NOT
  fired).
- **XLSX-only native format** → new-dep flag. Resolved without a new pip
  dep (DuckDB `excel` extension works; recommend one-time xlsx→csv at
  acquisition). This is a real acquisition-format decision that touches the
  cold-reader reproducibility contract → **SURFACE** the format choice.

### K3 — boundary structurally worse than 2010-HERD analog: **DID NOT fire**

The identifier scheme did **not** change across vol-71 (name+state both
sides), so cross-boundary institution linkage is no harder than within a
side — both sides need the same name-reconciliation crosswalk. The
column-taxonomy redesign (§4) is RH-native, comparable to (arguably milder
than) the HERD 2010 redesign. The boundary is **not** structurally worse
than the 2010-HERD analog.

---

## 6. Which HD 3.0 branch matches

**The table-parse acquisition branch** (published per-table downloads with
a one-time conversion), **NOT** the PUF-download branch. Concretely:

- Acquire per-table XLSX (or the bulk ZIP) at stable NSF URLs.
- Convert XLSX→CSV once at acquisition; checksum the CSV into
  `data/raw/MANIFEST.md` (mirrors the HERD zip-provenance model).
- Stage the PDF sibling into `data/reference/` as the human-readable audit
  anchor (mirrors the Table-26 / FY24-Guide PDFs).
- Loader mirrors `etl/_load.py` extract-on-read → `read_csv_auto` → unified
  long relation.

This branch is **blocked** behind the K1 resolution (the canonical-key
decision) and the §4 CLAUDE.md addendum, both of which are
Vision/principal-territory.

---

## 7. What was done vs. what is held

**Done (this gate):**
- Classified the artifact (tables, not PUF) and the identifier (name+state,
  per side) with direct evidence from three vintages spanning vol-71.
- Confirmed the $49B anchor is higher-ed-only and reconciled it to Table 12.
- Wrote this sanity-receipt.

**Held for next authorization (NOT done — per stop conditions):**
- **HD 3.0 was NOT finalized.** Because K1 fired, no FY2023 artifact was
  staged into `data/raw/`, no MANIFEST entry was written, no loader stub
  landed, no reference doc was staged into `data/reference/`.
- No `data/harmonized/fedsupport_*` or `crosswalks/fedsupport/` production
  subtrees were created (correctly gated behind the §4 addendum regardless).
- No era-wide acquisition. The three gate-slice downloads were
  throwaway-scoped and are **not** staged as deposit artifacts (they live
  under `etl/spikes/_fedsupport_scratch/`, gitignored spike territory).

**Gate-slice artifacts inspected (provenance record only — NOT staged):**

| SHA-256 | Bytes | File | Source URL |
|---|---|---|---|
| `e4fb34bff7a0b78d9531d08f507112159e7cdd56bfa3229685a8055d68503663` | 77,170 | `nsf22342-tab012-FY2020.xlsx` | `https://ncses.nsf.gov/pubs/nsf22342/assets/data-tables/tables/nsf22342-tab012.xlsx` |
| `364f0f85d7af1f083db67d16bc00096847c1b5f9160b22c25f531d65523140e8` | 77,318 | `nsf24311-tab012-FY2021.xlsx` | `https://ncses.nsf.gov/pubs/nsf24311/assets/data-tables/tables/nsf24311-tab012.xlsx` |
| `dea92dcecb94ba72333c5dd39b6a8b4c0046124b9e135bea01a30ac94c5b73c7` | 79,443 | `nsf25339-tab012-FY2023.xlsx` | `https://ncses.nsf.gov/pubs/nsf25339/assets/data-tables/tables/nsf25339-tab012.xlsx` |
| `762e9a8e9f7f790c467009735cd99fbc5217d8b349b08fba4a1c161031d9fb9d` | 513,299 | `nsf25339-tab012-FY2023.pdf` | `https://ncses.nsf.gov/pubs/nsf25339/assets/data-tables/tables/nsf25339-tab012.pdf` |

These hashes are recorded so a future session can re-fetch and confirm it is
inspecting the same artifacts this gate read. They are **not** a deposit
MANIFEST entry.

---

## 8. The decision this gate hands to Vision

K1 fired. The Federal S&E Support module can only be joined to the existing
HERD panel (and to IPEDS later) through a **name+state → canonical-id
reconciliation crosswalk**. That crosswalk is the dominant cost of this
dataset, and the canonical-key choice (build an
NSF-name→UNITID/ncses_inst_id map; reuse an existing NCSES Academic
Institution Profiles / IPEDS dictionary; or carry name+state as the native
key with a documented match-rate) is the deferred CLAUDE.md §4 addendum
lock. **That is a worth-vs-cost call for Vision + principal, not an
engineering pick.** The engineering reality this gate establishes:

- Acquisition is cheap (stable URLs, one-time xlsx→csv, no new dep).
- The column-taxonomy redesign at vol-71 is RH-native and in-scope.
- The **name-reconciliation crosswalk is the real cost**, and per
  `[[feedback-hd-entry-phase-budget]]` it crosses a known discontinuity
  surface (cross-source institution linkage with no shared key) — budget
  ~2× a mechanical-crosswalk baseline.
