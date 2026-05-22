# Era-A `status` codeset findings — surfaced at HD 2.4.b Stage 4 smoke test

**Authored:** 2026-05-10 (HD 2.4.b round 1, Surface 1).
**Status:** SURFACE — blocks HD 2.4.b Stage 4 panel build for FY 1973–1989. Awaits maintainer disposition.

## What surfaced

When `etl/build_herd_panel.py:smoke_test_stage_4` ran the locked Stage 1→2→3→4 pipeline across the era-A range (1973–2009), Stage 3's loud-fail assertion (the `UNKNOWN_<status>` defensive check at `etl/build_herd_panel.py:644-655`) raised on FY 1973:

```
RuntimeError: Stage 3: encountered raw `status` values outside the documented
codeset {blank, 'i', 'e', 'u'}.
First 1 offending tuples:
  year=1973 status='c' question='Expenditures by S&E field' row='All'
```

The assertion is operating exactly as designed: it caught a raw-CSV `status` code outside the FY24 Guide documented codeset (`validation/reports/herd_null_characterization_findings.md`) and refused to silently map it. HD 2.4.a only smoke-tested FY 2008 (era-A representative) and FY 2024 (era-B representative); neither year carries the codes this surface reveals.

## Empirical characterization (probe — `etl/spikes/probe_status_c_codeset.py`)

The probe scanned all 37 era-A years (1973–2009) for `status` values outside `{'', 'i', 'e', 'u'}`. Three findings:

### Finding 1 — `status='c'` (lowercase) appears FY 1973–1974 only

| FY | Total `c` rows | At `column='Total'` | Of which Stage-4-in-scope-question | `data` values |
|---|---:|---:|---:|---|
| 1973 | 10 | 5 | 5 (`Expenditures by S&E field`) | all positive numeric |
| 1974 | 19 | 8 | 8 (`Expenditures by S&E field`) | all positive numeric |

Breakdown by (question, column):

```
FY 1973 (10 rows):
   5  question='Source'                       column=None
   5  question='Expenditures by S&E field'    column='Total'

FY 1974 (19 rows):
   8  question='Expenditures by S&E field'    column='Total'
   7  question='Expenditures by S&E field'    column='Federal'
   4  question='Source'                       column=None
```

13 of the 29 `c`/`C` rows sit at `column='Total'` on the Stage 4 in-scope question (`Expenditures by S&E field`); these are panel-row-affecting. The rest sit on era-A-attribute questions or non-Total columns, where Stage 4 does not project them.

### Finding 2 — Uppercase `'I'` and `'E'` codes appear FY 1973–1989

The Stage 3 CASE expression maps lowercase `'i'` → `imputed` and `'e'` → `estimated`, but pre-1990 era-A files emit both case forms freely interleaved within the same file. Pre-1990 totals in the "other" (non-codeset) bucket:

| FY | Total | blank | `'i'` | `'e'` | `'I'` | `'E'` | `'c'`+`'C'` |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1973 | 20,196 | 15,821 | 2,739 | 933 | 586 | 107 | 10 |
| 1974 | 18,839 | 16,697 | 1,138 | 541 | 259 | 179 | 25 (`19+6`) |
| 1975 | 17,508 | 16,575 | 412 | 277 | 131 | 113 | 0 |
| 1976 | 18,072 | 15,883 | 1,240 | 313 | 580 | 56 | 0 |
| 1977 | 17,514 | 15,785 | 932 | 261 | 509 | 27 | 0 |
| 1978 | 7,602 | 6,665 | 535 | 402 | 0 | 0 | 0 |
| 1979 | 22,307 | 15,580 | 3,728 | 1,872 | 1,060 | 67 | 0 |
| 1980 | 29,140 | 15,059 | 5,885 | 6,772 | 1,149 | 275 | 0 |
| 1981 | 49,474 | 22,137 | 19,314 | 6,631 | 1,315 | 77 | 0 |
| 1982 | 48,363 | 21,641 | 20,400 | 4,807 | 1,447 | 68 | 0 |
| 1983 | 48,717 | 20,954 | 21,916 | 4,362 | 1,372 | 113 | 0 |
| 1984 | 56,658 | 18,374 | 34,770 | 2,418 | 1,053 | 43 | 0 |
| 1985 | 58,586 | 18,653 | 36,132 | 2,809 | 952 | 40 | 0 |
| 1986 | 60,658 | 18,157 | 39,333 | 2,046 | 1,070 | 52 | 0 |
| 1987 | 52,106 | 22,398 | 27,349 | 1,610 | 722 | 27 | 0 |
| 1988 | 36,852 | 27,922 | 5,722 | 2,344 | 807 | 57 | 0 |
| 1989 | 48,881 | 25,159 | 20,650 | 1,690 | 753 | 629 | 0 |

Both case forms coexist within the same year. FY 1990–2009 carry no uppercase codes — the case anomaly is pre-1990 only.

The volume is non-trivial: ~13K–14K rows total of `'I'`/`'E'` across 1973–1989; ~2K of those sit at `column='Total'` on Stage-4-in-scope questions (rough estimate from the per-year non-codeset bucket sizes).

### Finding 3 — `status='C'` (uppercase, FY 1974 only)

Same characterization as `'c'` lowercase: 6 rows in FY 1974, parallel to the 19 lowercase `'c'` rows. Likely the case-form sibling of `'c'` (whatever `'c'` means).

## What this means for the build

- **FY 1990–2009 (20 years):** Stage 3 codeset is correct; Stage 4 builds cleanly.
- **FY 1973–1989 (17 years):** Stage 3's defensive assertion blocks the build until the codeset is extended or the case-insensitivity question is resolved.

## Disposition options (for maintainer)

The W2 surface-don't-patch discipline says the build stops here; I do not extend `QUALITY_FLAG_MAP` unilaterally. Three plausible dispositions:

### Option A — case-insensitive `i`/`e`/`u`/`c` mapping; map `c` as a documented code

Treat the CASE expression as case-insensitive (`UPPER(status) IN ('I', 'E', 'U', 'C')`) and extend `QUALITY_FLAG_MAP` with a mapping for `c`. Requires a semantic decision on what `c` means.

Plausible interpretations of `c`:
- **`'corrected'`** — common NCSES/federal convention for a value that was revised post-collection. Would map to a new fifth `quality_flag` enum value `'corrected'`. Schema migration cost: extend `QUALITY_FLAG_ENUM` to five values; update Stage 9 enum-membership assertion; update YAML `quality_flag_propagation.ordering` (where does `corrected` fit in the worst→best order?); update scoping doc §1 `quality_flag` semantics with the FY 1973–1974 `'c'` provenance.
- **`'computed'`** — alternative reading. Less common in NCSES conventions.
- **Some 1970s vintage code retired by 1975** — given that `'c'` only appears in FY 1973–1974, the simplest framing.

This option requires a documentation-anchor search: does any NCSES historical-publications PDF (Academic R&D Expenditures Survey methodology notes from the 1970s) document the `'c'` code? The FY24 Guide is silent (it documents the FY 2024 codeset, which doesn't include `'c'`).

### Option B — case-insensitive `i`/`e`/`u` only; treat `c`/`C` as build-blocker

Resolve the case-insensitivity issue (which has clear semantic intent — `'I'` is `'i'`) and stop the build on `'c'`/`'C'` until the documentation question is answered. FY 1973–1974 don't enter the panel until the disposition lands.

This option preserves the surface as a real disposition decision rather than absorbing it into a quick code fix. The cost is FY 1973–1974 sit out of the panel until the question resolves; FY 1975–1989 build clean once the case-sensitivity fix lands.

### Option C — extended NULL-characterization spike before any disposition

Treat HD 2.4.a's W4 NULL characterization as scoped to era-B only (the W4 lock context was the era-B reconstruction rule's NULL handling) and explicitly run the era-A equivalent: a full era-A spike that characterizes every `status` value across 1973–2009 against any historical NCSES methodology documentation that survives. Defer the Stage 3 codeset extension until the spike closes.

This is the most thorough option. Cost: roughly 2 half-days for the spike + documentation hunt + writing the era-A NULL-characterization report. Returns: a clean lock that survives the deposit's reproducibility contract.

## What I recommend to the maintainer

The surface is real and the W2 discipline says I do not pick a disposition unilaterally. My read on the trade-offs:

- **Option A** is fast but commits to a semantic interpretation (`'c'` = `'corrected'`) without a documentation anchor.
- **Option B** preserves correctness for the panel that builds (FY 1990–2009 plus FY 1975–1989 once case-sensitivity lands) and treats FY 1973–1974 as a pending sub-decision. The deposit ships 50 of 52 panel-relevant years on the locked codeset; the 2 affected years are a small carve-out the methods note can footnote.
- **Option C** is the deposit-grade thorough path. If the deposit is shipping at W9–10 and the methods note has to defend the codeset to a cold reader, this is the right path.

The combination I'd point to: Option B for the immediate Stage 4 unblock (case-insensitive mapping, FY 1973–1974 carved out pending disposition), plus the era-A NULL-characterization spike from Option C scoped as an HD 2.4.a addendum running in parallel with HD 2.4.c–.d. The carve-out is small enough that it doesn't block the parallel timeline; the spike grounds the eventual disposition in documentation.

## Probe output

Full probe output: `etl/spikes/probe_status_c_codeset_output.txt` (preserved as artifact; SHA the build pinned at HD 2.4.b round 1).
Probe script: `etl/spikes/probe_status_c_codeset.py`.

## Cross-references

- Stage 3 loud-fail assertion: `etl/build_herd_panel.py:644-655`.
- Locked codeset (W4 round, era-B-grounded): `validation/reports/herd_null_characterization_findings.md`.
- Scoping doc §1 `quality_flag` value semantics: `docs/methods_notes/herd_panel_etl_scoping.md` lines 53–62.
- HD 2.4.a Track 2 qno suffix semantics (parallel surface methodology): `validation/reports/qno_suffix_semantics_findings.md`.
