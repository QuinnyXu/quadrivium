# HD 3.2 — Federal S&E Support: name-match de-risking spike findings

**Sanity-receipt / spike findings report.**
Author: Skipper. Date: 2026-05-29.
Spike (throwaway): `etl/spikes/spike_fedsupport_name_match.py`.
Authorized by principal 2026-05-29 as the first execution step of HD 3.2
(`docs/fedsupport/hd_3_2_scoping.md` §11). Budget 3 half-days, kill at 3.

> This is a spike report, not a build. Per HD 3.1 gate discipline the spike
> was pointed at ONE number (the RAW normalized-match yield) + ONE edge (the
> city disambiguator, §8.2), and stopped at the finding. No `data/raw/`
> staging, no production `crosswalks/fedsupport/` or `crosswalks/_shared/`
> subtree was created. This is the surface-to-Vision-via-principal.

---

## 0. Verdict at a glance

| Item | Finding |
|---|---|
| Parse — institution rows isolated | **1,111** (positional hierarchy, §8.1) — sanity-clean vs the ~1,110 anchor. |
| Parse — grand-total reconciliation | **48,961,658 kUSD** read from the "All states and outlying areas" row = the HD 3.1 §2 higher-ed anchor exactly. |
| **RAW first-pass institution match** | **389 / 1,111 = 35.0%** (29 exact, 360 normalized). |
| **RAW first-pass dollar match** (thread-critical) | **$15,842,772K / $48,961,658K = 32.4%**. |
| **Second-pass mechanical match** (no manual resolution) | **527 / 1,111 = 47.4% institutions; $29,538,036K = 60.3% dollars.** |
| City-disambiguator edge (§8.2) | **NO COLLAPSES.** 36 same-name-different-city groups; every distinct city → distinct normalized key → distinct UNITID. City preservation works. |
| Collision hazard | First pass: 0 keys → >1 UNITID. Second pass: **2** token-set keys → >1 UNITID (watch-list, not a collapse). |
| Branch condition fired | RAW first-pass 35.0% **< 60% floor** → nominal **SURFACE TO VISION**. **But see §4 — the 60% floor is a *dollar* floor and the mechanical second pass already clears it (60.3%).** |
| Disposition | **SURFACE TO VISION with a recoverability finding.** The 35% is a thin-first-pass-normalizer floor, not a ceiling; a single mechanical word-order rule lifts the dollar rate to the floor. Vision call: proceed-to-MVP-sized-to-yield vs. reopen worth-vs-cost. |

---

## 1. Parse — the positional hierarchy resolved cleanly (§8.1)

The principal-flagged loader difficulty (Column A nests institution rows
under state headers with a grand-total row, no row-type column) parsed
cleanly with a positional heuristic:

- Locate the value-column index from the header band
  (`State, outlying area, and institution` row).
- Grand-total row = literal `All states and outlying areas` → 48,961,658 kUSD.
- State-header rows = labelA ∈ a fixed 60-name state/outlying-area set
  (55 state headers seen).
- Institution rows = everything else carrying a numeric "All federal
  obligations" value, tagged with the most-recent state header above it.

Result: **1,111 institution rows** — sanity-clean against the ~1,110 anchor.
The sum of institution-row obligations (48,975,123 kUSD) runs ~0.03% over
the grand total because a handful of system-office rows (e.g.
`California State U., system office`) sum alongside their campuses; this is
expected double-attribution at the system grain, a parse-disposition
question for MVP, **not** a parse bug.

### Acquisition / read finding (spike-surfaced, MVP-relevant)

The FY2023 xlsx was re-fetched from the HD 3.1 §7 URL and verified
SHA-256 == `dea92dce…b73c7` (gate-recorded hash — same artifact).

**The DuckDB `excel` extension drops every value column unless an explicit
`range` is passed.** Because A1 holds a one-cell title band, the extension
auto-infers a 1-column sheet and reads only Column A. The spike works around
this with `range='A1:G1200', stop_at_empty=false`. This is a **spike-only**
read path (the §3 no-runtime-extension lock binds the deposit build, not the
spike) — but it confirms the HD 3.1 §1 recommendation: **convert xlsx→CSV
once at acquisition** and have the loader read CSV via `read_csv_auto`. The
range-auto-detect fragility is a concrete reason not to read xlsx at build
time.

---

## 2. The RAW number (ADDITION 1) — first pass 35.0% / 32.4%

The mandated raw, pre-manual-resolution yield:

| Grain | Matched | Total | Rate |
|---|---:|---:|---:|
| Institutions | 389 | 1,111 | **35.0%** (exact 29, normalized 360) |
| Dollars (thread-critical) | $15,842,772K | $48,961,658K | **32.4%** |

The dollar rate sits *below* the institution rate — meaning the unmatched
tail is dollar-heavy, not a long thin tail of small institutions. That is
the dangerous direction (§9), and it is explained entirely by §3 below.

---

## 3. The miss is word-order, not a ceiling (the load-bearing diagnostic)

The unmatched set is dominated by the large public university SYSTEMS — the
exact institutions that carry the most dollars. The cause is mechanical and
single-rooted: **NSF house style drops the "of".**

| FedSupport (NSF style) | first-pass norm | HERD `inst_name_long` | first-pass norm |
|---|---|---|---|
| `U. Alabama, The, Tuscaloosa` | `university alabama｜tuscaloosa` | `University of Alabama, The, Tuscaloosa` | `university of alabama｜tuscaloosa` |
| `U. California, Berkeley` | `university california｜berkeley` | `University of California, Berkeley` | `university of california｜berkeley` |
| `U. Texas, The, Austin` | `university texas｜austin` | `University of Texas at Austin, The` | `university of texas at austin` |

The **city token is identical on both sides** (`tuscaloosa`, `berkeley`,
`austin`). Only the head differs, and only by the stopword `of` (plus
occasional `at`/`in` word-order). The first-pass exact-string key cannot
bridge it; a token-set head match can.

### Second-pass (still mechanical — no manual resolution)

Matching on a **token-set head** (drop stopwords `{of, the, at, in, and}`,
keep the city token) lifts the yield:

| Grain | First pass | Second pass (mechanical) |
|---|---:|---:|
| Institutions | 35.0% (389) | **47.4% (527)** |
| Dollars | 32.4% | **60.3% ($29,538,036K)** |

**The dollar rate crosses the 60% floor on a purely mechanical second pass**
— because the second pass is exactly what recovers the big-dollar systems
(UC, Texas, Maryland, Tennessee, …). This is the decisive finding: the 35%
first-pass number is a **thin-normalizer artifact, not the spine's ceiling.**
The ~2× manual tail (HD 3.2 §3, artifact #5's 3.0-half-day core) sits on top
of the *second-pass* baseline, not the first-pass one.

The second pass introduces **2** token-set keys that map to >1 UNITID
(collision hazard) — small, enumerable, and resolved by the city token in
the first pass. They go on the MVP watch-list, not the kill list.

---

## 4. City-disambiguator edge (ADDITION 2, §8.2) — NO COLLAPSES

The most dangerous catch did **not** fire. The spike scanned all 36
same-name-different-city groups in the FY2023 set and ran the explicit
U. Alabama probe:

```
U. Alabama, The, Birmingham   -> norm 'university alabama|birmingham'   (distinct key)
U. Alabama, The, Huntsville   -> norm 'university alabama|huntsville'   (distinct key)
U. Alabama, The, Tuscaloosa   -> norm 'university alabama|tuscaloosa'   (distinct key)
```

Every multi-campus group (the full UC system, CSU's 23 campuses, Texas A&M,
SUNY/CUNY, Puerto Rico, etc.) resolved each distinct city to a **distinct
normalized key**, and — where matched — a **distinct UNITID**. The
city-preserving normalizer (city token kept as the trailing `head｜city`
segment) does its job: **zero silent merges.**

This is the validation-survivable failure mode the spike existed to rule
out, and it is ruled out *for the normalizer design*. The MVP must keep the
city token first-class in the spine key — a later normalizer that collapses
it would reintroduce the hazard silently.

---

## 5. Which kill / branch condition fired

- **Kill at 3 half-days:** not reached. Spike completed inside budget
  (parse + first-pass + second-pass diagnostic + city-edge scan).
- **RAW first-pass < ~60% → SURFACE TO VISION:** **FIRED** on the literal
  first-pass institution number (35.0%). This is why this report goes to
  Vision.
- **BUT the 60% floor is defined on the *dollar* axis** (§9: the dollar-match
  rate is "the thread-critical one"), and the **mechanical second pass
  already reaches 60.3% dollars** with zero manual resolution. So the spike
  fired the surface condition on the rawest possible reading while
  simultaneously showing the floor is mechanically recoverable.

---

## 6. The decision this spike hands back (one paragraph)

The FY2023 Table 12 parse is clean (1,111 institutions, grand total
reconciles to the $48,961,658K anchor) and the city-disambiguator edge — the
most dangerous of the three catches — does **not** fire: every distinct-city
campus resolves to a distinct UNITID, no silent merges. The raw first-pass
normalized match is 35.0% institutions / 32.4% dollars, which trips the
<60% surface-to-Vision condition on its literal reading. **However, the miss
is single-rooted and mechanical** — NSF drops the "of" (`U. California` vs
`University of California`) and shuffles `at`/`in` word order, while the
city token (the disambiguator) is already identical on both sides. A
second-pass token-set normalizer, still fully mechanical with no manual
resolution, lifts the yield to 47.4% institutions / **60.3% dollars** — the
dollar floor, cleared, before the ~2× manual tail is even spent. The
engineering read is therefore **not** "the spine costs more than the ~2×
budget assumed"; it is "the spine's *mechanical* baseline is ~60% dollars
and the ~2× manual tail builds on top of that, which is the budget working
as designed (§3 of the scope)." This is a **Vision worth-vs-cost call**: the
literal spike condition says SURFACE, and the recoverability finding says
the MVP is viable sized to the *second-pass* yield rather than reopened. My
engineering recommendation, offered to Vision not asserted over her: **MVP
greenlights, sized to the ~60% dollar / ~47% institution mechanical baseline
+ the named manual tail; promote the `of`-insertion / token-set rule into the
MVP normalizer (artifact #5) and keep the city token first-class.**

---

## 7. What was done vs. what is held

**Done (this spike, throwaway):**
- Re-fetched + SHA-verified FY2023 Table 12; parsed 1,111 institution rows;
  reconciled the grand total to the $48,961,658K anchor.
- Reported the raw first-pass match (35.0% / 32.4%) and the mechanical
  second-pass match (47.4% / 60.3%).
- Scanned all 36 same-name-different-city groups; confirmed no collapses.

**Held (NOT done — gated behind this report's Vision read):**
- No HD 3.2 MVP build. No `data/raw/fedsupport/` staging, no MANIFEST entry,
  no loader, no `crosswalks/fedsupport/` or `crosswalks/_shared/` subtree.
- No HERD-crosswalk path-move. No vol-71 taxonomy crosswalk.
- The spike code does **not** promote; the MVP normalizer is a fresh
  production artifact that reuses the spike's *findings* (the `of`-insertion
  rule, the city-token-first-class key, the 2 collision-hazard keys).

**Spike artifacts (throwaway, gitignored scratch):**
- `etl/spikes/spike_fedsupport_name_match.py` (the spike).
- `etl/spikes/_fedsupport_scratch/nsf25339-tab012-FY2023.xlsx` (re-fetched,
  SHA `dea92dce…b73c7` — same artifact as the HD 3.1 gate slice).
