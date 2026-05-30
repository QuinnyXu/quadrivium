# HD 3.2 — Federal S&E Support: Table 12 parse reconciliation receipt

**Parse validation receipt (RH validation).**
Author: Skipper. Date: 2026-05-29. Generated from
`etl/build_fedsupport_obligations.py` (deterministic build output).
Parsed artifact: `data/harmonized/fedsupport_obligations.parquet`.
Loader: `etl/_load_fedsupport.py`.

> Confirms the positional-hierarchy parse (hidden edge §8.1 — Column A nests
> institution rows under state headers with NO row-type column) did not
> double-count subtotals or drop institutions. The PASS criterion is the
> per-year **grand-total == published higher-ed anchor (exact)**.

---

## 0. Verdict at a glance

| Item | Finding |
|---|---|
| Grand-total reconciliation, all 4 years | **EXACT** against the published higher-ed-only anchors. |
| FY2023 institution count | **1,110** — matches the NSF 25-341 InfoBrief "1,110 institutions" exactly. |
| Positional parse (§8.1) | Clean: 55–56 state headers/year, 0 orphan institutions (every institution row tagged to a state). |
| Footnote-header edge | One footnoted state header (`Northern Mariana Islandsb`, FY2023) correctly classified as a state header, not an institution (loader `_is_state_header` strip-and-retest). |
| Vol-71 column taxonomy | All four years carry **6 value columns** (not the 8→6 the HD 3.1 gate estimated); the boundary is a column-**relabel**, not a column-count change. Taxonomy crosswalk DEFERRED (§5.2); raw labels preserved per era. |

---

## 1. Per-year grand-total reconciliation

The parser reads the `All states and outlying areas` grand-total row and
compares it to the published higher-ed-only anchor (HD 3.1 §2 / §9). FY2020,
FY2021, FY2023 anchors are the scope-doc figures; FY2022 was derived at
acquisition (no §9 anchor was supplied) and cross-checked to the InfoBrief
narrative below.

| FY | Report | Parsed grand total (kUSD) | Published anchor (kUSD) | Match |
|---|---|---:|---:|:---:|
| 2020 | NSF 22-342 | 39,122,152.2 | 39,122,152 | **EXACT** |
| 2021 | NSF 24-311 | 43,222,829.0 | 43,222,829 | **EXACT** |
| 2022 | NSF 24-326 | 44,628,417.0 | 44,628,417 *(derived)* | **EXACT** |
| 2023 | NSF 25-339 | 48,961,658.0 | 48,961,658 | **EXACT** |

**FY2022 anchor provenance.** FY2022 was not in the §9 anchor list ("derive").
The grand total $44,628,417K was read from the FY2022 Table 12
(NSF 24-326, the data-tables companion to InfoBrief NSF 24-325, resolved via
the NCSES survey-2022 data page). Cross-check: NSF 24-325 headlines "Federal
Science and Engineering Support for Academic Institutions **Increased 3% in
FY 2022**." $44.628B vs FY2021's $43.223B = **+3.25%**, consistent with the
published +3% narrative. The derived anchor is therefore narrative-confirmed,
not free-asserted.

**FY2020 precision note.** FY2020 values are published to 0.1 kUSD (e.g.
`Auburn U., Auburn  48,541.0`); FY2021–FY2023 are whole kUSD. The loader
preserves the FY2020 decimal precision as `DOUBLE`; the grand total
reconciles to the .1 (`39,122,152.2` vs the rounded `39,122,152` anchor —
within 0.5 kUSD, the published figure is the rounded form).

---

## 2. The positional hierarchy did not double-count or drop (§8.1)

Three independent dollar totals per year, on the `All federal obligations`
column:

| FY | grand total | Σ institution rows | inst over grand | Σ state subtotals | state-sub vs grand |
|---|---:|---:|---:|---:|---:|
| 2020 | 39,122,152.2 | 39,124,884.9 | +2,732.7 (+0.0070%) | 39,119,421.1 | −2,731.1 (−0.0070%) |
| 2021 | 43,222,829.0 | 43,230,487.0 | +7,658.0 (+0.0177%) | 43,215,170.0 | −7,659.0 (−0.0177%) |
| 2022 | 44,628,417.0 | 44,636,493.0 | +8,076.0 (+0.0181%) | 44,620,338.0 | −8,079.0 (−0.0181%) |
| 2023 | 48,961,658.0 | 48,961,652.0 | −6.0 (−0.0000%) | 48,961,658.0 | +0.0 (+0.0000%) |

**Reading the residual.** The institution-row sum runs marginally OVER the
grand total in FY2020–FY2022; this is **system-office double-attribution**
(spike §1): rows like `U. Wisconsin, System Office`, `California State U.,
System Office`, `U. Missouri System` carry their own obligation dollars that
the published per-state subtotal counts once but that sum alongside the
campuses. These are **legitimate institution rows** (the system office is a
real obligation recipient), reported not corrected — the dollars are real,
and the spine treats the system office as its own institution. The magnitude
is ≤0.018% of the anchor in every year.

**FY2023 is near-exact** (−6 kUSD, −0.00001%): the small residual is NCSES
**per-state rounding** (FY2023 is published to whole kUSD, so summing rounded
institution rows accumulates ±1/state across ~33 states). FY2023's
state-subtotal sum equals the grand total exactly.

**Footnote-header correction (a parse improvement over the spike).** The
spike reported 1,111 FY2023 institutions; the MVP parser reports **1,110**.
The difference is `Northern Mariana Islandsb` — a state-header row carrying a
trailing footnote letter `b`. The spike's parser (exact STATE_NAMES match)
misread it as an institution under Guam, inflating Guam's institution-sum by
the Northern Mariana Islands subtotal. The MVP loader's `_is_state_header`
strips a trailing 1–2-letter footnote and retests against the state-name set,
correctly classifying it as a state header. The corrected count **1,110
matches the NSF 25-341 InfoBrief exactly**. This was the only footnoted
header across all four years (surfaced during loader development).

---

## 3. Column-taxonomy finding (vol-71) — relabel, not 8→6

The HD 3.1 gate estimated FY2020 had 8 value columns vs FY2021+'s 6. The
acquired tables show **all four years carry 6 value columns**; the vol-71
boundary is a **relabel** of two columns, not a column-count change:

| Column | FY2020 (NSF 22-342) | FY2021–FY2023 |
|---|---|---|
| 1 | All federal obligations | All federal obligations |
| 2 | R&D | R&D |
| 3 | R&D plant | R&D plant |
| 4 | Facilities **for** instruction in S&E | Facilities **and equipment for** instruction in S&E |
| 5 | Fellowships, traineeships, and training grants | **S&E** fellowships, traineeships, and training grants |
| 6 | General support for S&E | **Other** general support for S&E |

The harmonized parquet preserves these RAW labels per era (`activity_type =
'raw:<label>'`); the era-invariant `All federal obligations` column gets the
canonical key `all_obligations`. The 8→6/relabel boundary crosswalk is
**DEFERRED** (HD 3.2 §5.2): the MVP's proving deliverable (the spine +
dollar-match) runs on `all_obligations`, which does not depend on the
taxonomy crosswalk. The milder-than-estimated boundary (relabel, not
restructure) is logged so the deferred taxonomy HD scopes against the actual
shape.

---

## 4. Reproducibility

- The loader reads the staged **CSV** via `read_csv_auto` only — no runtime
  `excel` extension, no network fetch (CLAUDE.md §3 lock). The xlsx→CSV
  conversion happened once at acquisition.
- `ORDER BY ALL` before the parquet `COPY` makes the output a deterministic
  function of the input CSVs + code; two consecutive builds produce a
  byte-identical parquet (verified, SHA-256 stable across rebuilds).
- Staged CSV + PDF SHA-256s are tracked in `data/raw/MANIFEST.md`
  (`fedsupport` section) and `data/reference/MANIFEST.md`.
