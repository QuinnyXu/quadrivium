# HD 2.4.a Track 2 — qno suffix semantics findings

**Author:** Skipper.
**Spike:** `etl/spikes/spike_qno_suffix_semantics.py` (throwaway).
**Spike output (verbatim):** `etl/spikes/spike_qno_suffix_semantics_output.txt`.
**Status:** evidence assembled. Stops at findings — no spec amendment, no build-code change.

## 1. Spike scope

- **Years:** FY 2017 and FY 2024 (era B; both years carry the compound qno
  encoding observed in the smoke-test). Two-year sample is intentionally
  narrow — Round 2 already established that compound qno is FY 2024
  reality; the second year confirms cross-year stability or surfaces
  drift.
- **Question families:** Q4, Q5, Q9, Q11, Q14 (the families the Stage 2
  filter spec was trying to scope). Q5/Q15/Q16 raw-vs-canonical drift is
  already handled at `crosswalks/question_map.csv` rows 16, 26, 27.
- **Sampling per qno form:** for every distinct qno value in those
  families, the spike pulled (a) row count, (b) distinct-question count,
  (c) distinct (`row`, `column`) pair count, (d) 5 sample rows showing
  raw `question` / `row` / `column` / `data` / `status` /
  `standardized_agency_names`, plus (e) full distinct-`column` and
  distinct-`row` lists.

## 2. Per-qno-form characterization

Every qno form ties to **exactly one `question` label** (column
`n_distinct_questions = 1` for every form). The suffix does not
differentiate questions; it differentiates **rows within a question**.

### 2.1 Q4 family

| qno   | n_rows (FY24) | distinct rows | distinct columns | example raw question label                |
|-------|---------------|---------------|------------------|-------------------------------------------|
| `'04'`| 144 (FY17 155)| `Total`       | `NULL`           | `'Medical school expenditures'`           |

Single-axis. Single row label `'Total'`, no column. Suffix carries no
sub-structure — Q4 is a single institution-year scalar.

### 2.2 Q5 family

| qno   | n_rows | distinct rows                       | distinct columns | example raw question label |
|-------|--------|-------------------------------------|------------------|----------------------------|
| `'05'`| ~489   | `Total`, `Federal`, `Nonfederal`    | `NULL`           | `'Clinical trials'`        |

Single-qno, three-row encoding (the carve-out is sliced into federal /
nonfederal / total via `row`, not via `column`). Suffix carries no
sub-structure.

### 2.3 Q9 family — `'09A'` through `'09K'`

48 distinct qno values in FY 2017, identical 48 in FY 2024.

- **Letter (A..K)** → coarse-discipline family.
- **Trailing two-digit number (01..09)** → leaf-discipline within the
  family. Final `*10` (where present) is the family `'*, all'` rollup.
- **No-numeric-suffix forms (`'09A'`, `'09E'`, `'09G'`, `'09I'`, `'09K'`)**
  are coarse families that have no leaf decomposition — they each map to
  a single `'*, all'` row.
- **`column`** carries the federal-agency axis: 8 distinct columns (`USDA`,
  `DOD`, `DOE`, `HHS`, `NASA`, `NSF`, `Other agencies`, `Total`).

| qno     | distinct row (one per qno)                                       | column axis (8 values) |
|---------|------------------------------------------------------------------|------------------------|
| `'09A'` | `Computer and information sciences, all`                         | `USDA..Total`          |
| `'09B01'`| `Engineering, aerospace, aeronautical, and astronautical`       | `USDA..Total`          |
| `'09B02'`| `Engineering, bioengineering and biomedical engineering`        | `USDA..Total`          |
| `'09B03'`| `Engineering, chemical`                                          | `USDA..Total`          |
| `'09B04'`| `Engineering, civil`                                             | `USDA..Total`          |
| `'09B05'`| `Engineering, electrical, electronic, and communications`        | `USDA..Total`          |
| `'09B06'`| `Engineering, industrial and manufacturing`                      | `USDA..Total`          |
| `'09B07'`| `Engineering, mechanical`                                        | `USDA..Total`          |
| `'09B08'`| `Engineering, metallurgical and materials`                       | `USDA..Total`          |
| `'09B09'`| `Engineering, other`                                             | `USDA..Total`          |
| `'09B10'`| `Engineering, all`                                               | `USDA..Total`          |
| `'09C01'..'09C05'`| Geosciences leaves + `'all'`                           | `USDA..Total`          |
| `'09D01'..'09D06'`| Life sciences leaves + `'all'`                          | `USDA..Total`          |
| `'09E'`  | `Mathematics and statistics, all`                               | `USDA..Total`          |
| `'09F01'..'09F06'`| Physical sciences leaves + `'all'`                      | `USDA..Total`          |
| `'09G'`  | `Psychology, all`                                                | `USDA..Total`          |
| `'09H01'..'09H06'`| Social sciences leaves + `'all'`                        | `USDA..Total`          |
| `'09I'`  | `Other sciences, all`                                            | `USDA..Total`          |
| `'09J01'..'09J09'`| Non-S&E leaves + `'all'`                                | `USDA..Total`          |
| `'09K'`  | `'All'` (grand total)                                            | `USDA..Total`          |

### 2.4 Q11 family — `'11A'` through `'11K'`

48 distinct qno values, identical schema to Q9 except the column axis
carries **6 distinct columns** instead of 8 (the nonfederal source axis):
`State and local government`, `Business`, `Nonprofit organization`,
`Institution funds`, `All other sources`, `Total`. Same letter-and-leaf
field encoding as Q9.

### 2.5 Q14 family — `'14A'` through `'14K'`

48 distinct qno values, identical letter-and-leaf field encoding to Q9
and Q11. Column axis carries **3 distinct columns**: `Federal`,
`Nonfederal`, `Total`. Raw question label is
`'Capitalized equipment expenditures by field and source'` (note: not
`'Capitalized R&D equipment expenditures by field'` as recorded canonical
in `crosswalks/question_map.csv` row 25). Same raw-vs-canonical drift
pattern as Q5/Q15/Q16.

## 3. Source-class semantic verdict

**The qno suffix carries field-encoding load, not source-class load.**

For Q9/Q11/Q14, the source-class axis (federal-agency, nonfederal-source,
or federal/nonfederal split for capitalized equipment) lives in the
**`column`** field, not in the qno suffix. The qno suffix is a
field-decomposition index — coarse letter for discipline family, optional
trailing two-digit number for leaf within family.

The original three-option framing assumed the suffix might encode
source-class (which would have made it a Stage-5+ derivation primitive
for `source_class`). Empirically it does not. `source_class` should be
derived from the `question` label (Q9 → federal, Q11 → nonfederal, Q14 →
capitalized) plus the `column` value (specific agency / specific source
within that source-class umbrella) — both of which are already in the
unified-schema relation independently of qno.

That said, the qno suffix **does** carry information that is otherwise
recoverable only from the `row` text:

- **It is a stable, machine-readable field code.** `row` is free-text
  ("Engineering, electrical, electronic, and communications") and is the
  exact surface where era-A→era-B taxonomy renames (HD 2.1.b
  Environmental→Geosciences canonical) and within-era-B FY2016 field
  revisions live. The qno suffix (`'09B05'`) is more stable than the
  `row` label and more compact than free-text matching.
- **It is structurally redundant with `row` within era B.** Each qno
  suffix maps to exactly one `row` value in both FY 2017 and FY 2024.
  The mapping is not many-to-one or one-to-many — strict bijection from
  suffix to row within era B.

So the suffix is **fidelity-only at Stage 2** (filtering Stage 2 on
question label is sufficient), but it is a **viable derivation primitive
at Stage 4** (`discipline_coarse` / `discipline_fine` derivation could
key off the qno letter / leaf-digit instead of the free-text `row`, with
crosswalk row counts checked for parity). That choice is not on the
table for this spike — surfacing it here so HD 2.4.f / HD 2.4.g can
revisit when the discipline crosswalks are wired.

## 4. Cross-year consistency verdict

**Stable.** Every qno form present in FY 2017 is also present in FY 2024,
and vice versa. The spike's `Cross-year consistency` block reports:

```
FY 2017 only: []
FY 2024 only: []
```

For every qno in both years, the sample-row `question` label is
identical (`YES` for all entries — no `DRIFT`). FY 2017 and FY 2024 use
the same compound-qno encoding scheme, the same letter-and-leaf
discipline mapping, and the same raw question labels.

This means:

- The compound-qno encoding is a stable era-B convention, not a FY 2024
  one-off.
- Q4/Q5/Q14 raw-vs-canonical Guide drift is a stable era-B-wide
  drift, not a year-specific drift. Q4/Q14 should be added to
  `crosswalks/question_map.csv` `raw_question_label` following the
  Q5/Q15/Q16 pattern locked in row 16 / 26 / 27.

The spike did **not** sample FY 2010–FY 2016 or FY 2018–FY 2023; the
two-year evidence does not establish stability across all 15 era-B years.
HD 2.4.b's full era-B materialization will surface any silent drift in
the intermediate years; if the qno-form set or row-mapping shifts, that
emerges then. For Stage 2 spec purposes, two-year stability is sufficient
because the Stage 2 spec switches to label-only filtering (see §6) and
becomes insensitive to the qno-form set.

## 5. FY24 Guide documentation status

**Partially documented.**

- The Guide's question-overview prose (page 5–6 in
  `docs/source_documents/herd_fy24_guide.txt`) explicitly names
  "Question 9A–K", "Question 11A–K", "Question 14A–K". The
  letter-suffix-as-field-family convention is named in prose.
- The Guide's data-dictionary entry for `questionnaire_no` (page 10,
  page 12) is the bare string "Survey Questionnaire Number". The Guide
  does **not** document:
  - the zero-padded numeric prefix (`'04'`, `'05'`, `'09*'`, `'14*'`);
  - the trailing two-digit leaf number (`'09B05'`);
  - the bijection between qno suffix and `row` text;
  - the lack of suffix on coarse families (`'09A'`, `'09E'`, `'09G'`,
    `'09I'`, `'09K'`).

For methods-note purposes this is a **Guide-partially-documented** tag.
Letter convention has Guide cover; the digital encoding (zero-pad,
leaf-digit) is microdata convention, Guide-undocumented (parallel to the
status=`u` finding from the NULL spike).

## 6. Recommendation for Stage 2 spec amendment

**Option 2 — filter on question label, ignore qno suffix.**

Empirical proportions:

- Question label and qno suffix are **strictly redundant** at the
  question-membership grain in era B. Every qno value in
  `'04'/'05'/'09*'/'11*'/'14*'` maps to exactly one question, and every
  in-scope question carries exactly the qno values listed.
- Filtering on `question IN (canonical-list)` matches the **same row set**
  that filtering on a hypothetical broadened qno-prefix filter would. No
  rows are gained or lost by switching from qno-prefix to label.
- Filtering on `question` is **simpler** (one literal string list, no
  prefix-match regex), **more readable** (the spec sentence reads "rows
  where the question is one of these five questions" not "rows where
  the qno starts with one of these five number prefixes"), and **less
  brittle** (any future Guide change that renames a question forces a
  manual update either way; broadening the qno prefix would not protect
  against a renumbering, e.g., if NSF renumbered Q9→Q10).

The label-only branch carries one explicit dependency: the canonical
question-label list must include the **raw** labels, not the FY24 Guide
canonical labels. Per HD 2.1.e raw-vs-canonical pattern, build code joins
on `raw_question_label` when populated, falling back to canonical
otherwise. Q4 and Q14 raw labels need to be added to
`crosswalks/question_map.csv` rows 15 and 25:

| row | canonical (current)                                  | raw_question_label to add                                     |
|-----|------------------------------------------------------|---------------------------------------------------------------|
| 15  | `Medical school R&D expenditures`                    | `Medical school expenditures`                                 |
| 25  | `Capitalized R&D equipment expenditures by field`    | `Capitalized equipment expenditures by field and source`      |

This is the **same operation** Q5/Q15/Q16 already triggered. The
crosswalk amendment is in-pattern; no new methodological precedent is
needed.

**Option 1 (broaden qno filter) and Option 3 (both) are not recommended.**
Option 1 adds a regex filter that is functionally equivalent to the
label filter but harder to read and harder to verify. Option 3 doubles
the surface area without reducing risk — both filters reject the same
rows. The maintainer's three-option framing leaned toward Option 3 on
the assumption the suffix carried source-class load; that assumption did
not survive the empirical check.

## 7. Schema implication for Stage 5+

**Suffix is fidelity-only at Stages 2–4. Available as a derivation
primitive at Stages 5+ if needed.**

For the canonical `source_class` derivation (Stage 5+ work, not
greenlit yet):

- Q9 rows → `source_class = 'federal'`. Drive from question label.
- Q11 rows → `source_class = 'nonfederal'`. Drive from question label.
- Q14 rows → `source_class = 'capitalized_equipment'` (or excluded per
  CLAUDE.md §6 disposition W1, which is the current locked path).
  Drive from question label.

For the canonical `discipline_coarse` / `discipline_fine` derivation
(Stage 4 work):

- Current pattern: derive from `row` free-text + `crosswalks/discipline_*`.
- Available alternative: derive from qno letter (e.g., `09B*` → coarse
  `Engineering`) + qno leaf (e.g., `09B05` → fine
  `Engineering, electrical, electronic, and communications`). Faster,
  more stable, but requires a new crosswalk column anchoring the qno
  letter→discipline_coarse mapping for era B. Era A has no qno-letter
  encoding (era-A `questionnaire_no` is `'2'` for the field-level
  question, no field decomposition there — fields live in `row` only).
  So a qno-letter-keyed crosswalk is era-B-only and would need parallel
  era-A-row-keyed coverage anyway.

**Recommendation for Stage 4:** keep deriving discipline from `row`
(unified path across era A and era B). Stage 4 stays in the locked
spec. The qno suffix is preserved in the unified schema as raw-data
fidelity for downstream consumers who want a more stable field key
than free-text `row`, but the primary panel does not consume it.

## 8. Methods-note implication

One-sentence framing for the methods note (HD 2.4.i):

> *In era B, HERD's `questionnaire_no` field encodes question-family in
> the numeric prefix (`'04'`, `'05'`, `'09'`, `'11'`, `'14'`) and
> field-discipline in the alphabetic-plus-leaf-digit suffix (`'09B05'` =
> Question 9, Engineering family, electrical/electronic/communications
> leaf); we filter on the canonical question label rather than the qno
> prefix because the bijection between suffix and `row` text makes the
> two filters strictly redundant, and the label-keyed filter is more
> readable in code and methods-note prose.*

Parallel to the row-absent-as-zero framing in the existing methods-note
voice — name the convention, cite the Guide where it covers, tag the
Guide-undocumented portion explicitly.

## 9. Methodologically loaded surfaces beyond the maintainer's framing

Three surfaces emerged that the maintainer's three-option frame did not
ask about. Surfacing for awareness; none demand action this round.

1. **Q4 and Q14 raw-vs-canonical Guide drift.** Already known from the
   smoke test, but the spike confirms it is a stable era-B-wide pattern
   (FY 2017 and FY 2024 both carry the raw labels). Crosswalk amendment
   to `question_map.csv` rows 15 and 25 follows the Q5/Q15/Q16 pattern.
   Decision: maintainer greenlights the amendment when Stage 2 spec
   amendment is locked.
2. **Coarse-family qno values (`'09A'`, `'09E'`, `'09G'`, `'09I'`,
   `'09K'`) do not carry leaf-digit suffix.** This is a Guide-undocumented
   sub-convention of the alphabetic-plus-leaf encoding. Currently no
   build-code consequence (label filter is insensitive). Worth a
   methods-note line if the qno suffix becomes a Stage 4 derivation
   primitive in future.
3. **Q5 row-axis carries a Federal/Nonfederal/Total slicing not seen in
   Q4.** Q5 (`'Clinical trials'`) decomposes the carve-out into
   federal/nonfederal/total via `row`; Q4 (`'Medical school'`) is a
   single `'Total'` row. Under CLAUDE.md §6 W2 disposition both are
   excluded from the all-source rule and travel as institution-year
   attribute flags, but the flag derivation for Q5 needs to handle the
   three-row structure (likely sum-on-Total or pick-Total-row). Worth
   a flag-derivation note when the W2-lock attribute build hits Stage 6+.

These are notes for the panel, not asks. Stopping here.
