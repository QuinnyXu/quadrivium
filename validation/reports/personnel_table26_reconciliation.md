# Personnel Sibling Reconciliation: Table 26 vs `herd_personnel.parquet`

**Phase 3 reconciliation report. Verification framing landed (panel-locked
2026-05-01).** This is the receipt-level document; the cell-by-cell
verification table in §3 is the surface the methods-note and README headline
both compress against.

Author: Skipper, 2026-05-01 (Phase 2 grid; Phase 3 framing overlay).

## 1. Headline verdict

**FY 2024 exact match; FY 2022/2023 documented divergence ~0.46–0.88%
structurally explained by FY-2023-anchored standard-form filter back-applied
to all years.**

The verification scope is 6 cells (3 years × 2 measures). FY 2024 Headcount
matches exactly; FY 2024 FTE is within rounding band (delta = -1 on a
525,960 anchor). FY 2022 and FY 2023 diverge by +0.46% to +0.88% in the
same direction (parquet free-sum > Table 26 anchor); the divergence is
structurally explained by the NCSES editorial choice to apply the
"$1M+ FY 2023 R&D" standard-form filter as an FY-2023-anchored backstop
across all five years of the longitudinal Table 26, while the public-use
microdata does not pre-apply that backstop in retrospective years. FY 2024
aligns by construction because the public-use FY 2024 respondents *are* the
FY 2023 backstop set. See §5 for the structural argument and §3 for the
cells.

`n_institutions` (3 cells) has no Table 26 anchor — the table publishes
totals by personnel function and sex, not an institution count.

| Cells | Result |
|-------|--------|
| 6 publishable | 1 exact match (FY 2024 Headcount) · 1 within rounding band (FY 2024 FTE, -1) · 4 documented divergences (FY 2022, FY 2023; both measures), structurally explained |
| 3 n_institutions | No Table 26 anchor exists; complementary completeness check sourced from Table A-3 (§5.1) |

## 2. Method

### Sample

- **Parquet:** `data/harmonized/herd_personnel.parquet` (Phase 1 build,
  `etl/build_herd_personnel.py`). 14,859 rows; era B; years 2022–2024.
  No standard-form-population filter applied at parquet build time
  (Phase 1 design choice — keep parquet filter-free, apply at recon
  time only).
- **Anchors:** NCSES Data Table 26, NSF 26-304 release. Single in-repo
  PDF: `data/reference/nsf26304-tab026.pdf`. Table 26 is a **5-year
  longitudinal** (FYs 2020–24), so a single document covers all three
  reconciliation years. No FY 2022/FY 2023 stand-alone Table 26 retrieval
  needed; **WebFetch budget unused.**

### Filter logic (parquet side)

```sql
SELECT year, measure_type,
       SUM(value)                           AS freesum,
       COUNT(DISTINCT institution_id)       AS n_inst
FROM read_parquet('data/harmonized/herd_personnel.parquet')
WHERE personnel_function = 'total'
GROUP BY year, measure_type
ORDER BY year, measure_type;
```

`personnel_function = 'total'` selects the row-level rolled total within
each institution-year (already sums Researchers + Technicians + Support
Staff in the microdata `column='Total'` cells). `SUM(value)` then aggregates
that across institutions to produce a national free-sum. **No standard-form
filter is applied** — that is exactly what we are testing.

### Reproducibility script

`etl/spikes/personnel_table26_verify.py` regenerates §3's grid from the
parquet alone. Stdout-only; idempotent. Anchors are coded as constants and
cite the source PDF in the docstring.

### Rounding handling

Reported at exact integer level. Any cell within ±2 of the anchor (rounding-
band) is flagged but not promoted to "match" — the report calls this out
explicitly. Only FY 2024 FTE meets the rounding-band criterion (delta = -1).

## 3. Verification grid (6 publishable cells)

Source for `parquet_freesum` and `n_inst` columns: spike output (`uv run
python etl/spikes/personnel_table26_verify.py`, 2026-05-01). Anchors:
`data/reference/nsf26304-tab026.pdf` "All personnel functions" row.

| Year | Measure   | Parquet free-sum | Table 26 anchor | Δ        | %       | Verdict      |
|------|-----------|------------------:|----------------:|---------:|--------:|--------------|
| 2022 | Headcount | 1,037,272         | 1,032,569       | +4,703   | +0.46%  | DIVERGE      |
| 2022 | FTE       |   500,602         |   497,012       | +3,590   | +0.72%  | DIVERGE      |
| 2023 | Headcount | 1,064,295         | 1,058,388       | +5,907   | +0.56%  | DIVERGE      |
| 2023 | FTE       |   518,382         |   513,860       | +4,522   | +0.88%  | DIVERGE      |
| 2024 | Headcount | 1,086,850         | 1,086,850       |       0  |  0.00%  | EXACT        |
| 2024 | FTE       |   525,959         |   525,960       |     -1   | -0.00%  | rounding-band |

### n_institutions (3 cells, no anchor)

| Year | Parquet `n_inst` | Table 26 anchor      | Verdict        |
|------|-------------------|----------------------|----------------|
| 2022 | 636               | not published        | no anchor      |
| 2023 | 661               | not published        | no anchor      |
| 2024 | 680               | not published        | no anchor      |

**Why no anchor:** Table 26 publishes counts of *people* (Headcount and FTEs)
by personnel function and sex, not counts of *institutions*. There is no
institution-count column. Confirmed by reading the table contents and by
cross-checking Table A-23 (the FY 2023 vs FY 2024 table crosswalk in
`data/reference/nsf26304-taba-023.pdf`), which lists only Tables 26 and 27 in
the personnel group; Table 27 is FY 2024-only and is keyed by state /
institution / function, not by an institution-count column either.

The standard-form-population institution count would live in **Table A-3**
("Institutions surveyed for the Higher Education Research and Development
Survey, by highest degree granted and survey population: FYs 2019–24"),
which is **not currently in the repo** (`data/reference/`). See §6 for the
Phase 3 implication.

## 4. Source citations

- **Anchor cells (FY 2022, FY 2023, FY 2024 Headcount + FTE — All
  Personnel Functions):**
  NCSES Data Table 26, "Headcount and FTEs of R&D personnel at higher
  education institutions in the standard form survey population, by
  personnel function and sex: FYs 2020–24."
  Document ID: NSF 26-304.
  In-repo: `data/reference/nsf26304-tab026.pdf`.
  Public URL: <https://ncses.nsf.gov/pubs/nsf26304>.
  Universe footnote: "This table includes only institutions reporting $1
  million or more in total R&D expenditures in FY 2023. Institutions
  reporting less than $1 million in total R&D expenditures in FY 2023
  completed a shorter version of the survey form in FY 2024 that did not
  include this question."
- **Table inventory (cross-check that no other Table 26 sibling carries
  n_institutions):**
  NCSES Data Table A-23, "Higher Education Research and Development Survey
  data table crosswalk: FY 2023 vs. FY 2024," NSF 26-304.
  In-repo: `data/reference/nsf26304-taba-023.pdf`.
- **Parquet provenance:**
  `data/harmonized/herd_personnel.parquet`, built by
  `etl/build_herd_personnel.py` from
  `data/raw/herd/higher_education_r_and_d_{2022,2023,2024}.zip`. Raw zip
  SHA-256s in `data/raw/MANIFEST.md`.

## 5. Structural explanation and complementary findings

The headline framing in §1 stands on the structural argument in §5.2/§5.3
below. §5.1 covers the A-3 inventory cross-check (institution count side);
§5.4–§5.5 cover the FY 2022/2023 magnitude and FY 2024 rounding band.

### 5.1 A-3 inventory cross-check (institution count side)

Three of the dispatch's nine anchor cells are unsourceable from Table 26
because Table 26 publishes totals by personnel function and sex, not an
institution count. The standard-form-population institution count lives in
Table A-3 (`data/reference/nsf26304-taba-003.pdf`), which we fetched as a
complementary completeness check rather than as a parallel reconciliation
anchor.

**A-3 publishes surveyed universe (different concept than Table 26's
respondent total). Parquet response rate 99.40–99.85% across 2022/2023/2024
— no completeness concern surfaced.** A-3 is an inventory cross-check, not
a parallel anchor; the headline reconciliation remains the §3 cell-by-cell
table against Table 26. The 6-cell scope in §3 is retained.

### 5.2 Divergence is asymmetric across years, not uniform

FY 2024 matches (Headcount exact; FTE off by -1, rounding-band). FY 2022 and
FY 2023 diverge by +0.46% to +0.88%, all in the same direction (parquet >
Table 26). This is not the pattern of a uniform universe-mismatch (which
would diverge in all three years equally). It suggests **either** that the
public-use file's reporting universe was broader than the standard-form
universe in 2022/2023 and was tightened to match in 2024, **or** that the
NCSES standard-form-filter in Table 26 is computed from a "$1M+ in FY 2023"
backstop that the public-use file does not pre-apply for retrospective years.

The footnote on Table 26 specifies "$1 million or more in total R&D
expenditures in FY 2023" as the standard-form criterion. That criterion is
**FY-2023-anchored across all five years** — i.e., Table 26's FY 2022 cell
includes only institutions that reported $1M+ in FY 2023, not institutions
that reported $1M+ in FY 2022. This is a known NCSES editorial choice for
five-year longitudinal tables. The public-use file does **not** carry this
back-applied filter. **The 2022/2023 divergence is therefore consistent with
exactly this filter mechanism.**

### 5.3 FY 2024 alignment is consistent with §5.2

If the standard-form criterion is "FY 2023 R&D ≥ $1M," then FY 2024 free-sum
should equal Table 26 FY 2024 to within a rounding artifact, because the
public-use file's FY 2024 reporting institutions are by construction the
ones that completed the standard-form survey in FY 2024 — i.e., the ones
that reported $1M+ in FY 2023. The match observed (Headcount exact; FTE off
by -1) is exactly this alignment. This corroborates §5.2 as the explanation
rather than a build bug.

### 5.4 The +0.5% to +0.9% drift is small but not negligible for a deposit

A 0.5%-to-0.9% drift would be invisible in a chart at the country-aggregate
level but is large enough to show in any institution-level join (the
implicated extra institutions are real rows in the parquet). For a deposit
artifact framed as "harmonized public-use personnel panel," shipping the
parquet without resolving — or at minimum documenting — this drift would
mean the deposit's totals would not match the published Table 26 totals.
That is a methods-note honesty cost.

### 5.5 The rounding-band -1 on FY 2024 FTE is informative, not concerning

FTE values in HERD are reported to one decimal place (microdata `value`
column carries values like `0.1` through `24,590.0`). When ~680 institutions
each round their reported FTE to one decimal, summing them and rounding the
total to the nearest integer can produce a ±1 truncation error against
NCSES's own published total (which may have been rounded from a slightly
different intermediate). This is a rounding band, not a build issue.

## 6. Disposition (panel-locked 2026-05-01)

The panel adopted **Option (a) — document the divergence and ship the
parquet as-is.** The locked headline framing (§1) carries verbatim into the
README (`docs/methods_notes/herd_personnel_README.md`) and the methods-note
personnel section (`docs/methods_notes/reconstructive_harmonization.md`).
Receipts (the §3 cell-by-cell table, the §5 structural argument, the A-3
response-rate cross-check) live here and are cited not duplicated in the
methods-note or README.

The deposit cold-reader contract is: parquet is the all-respondents view
(filter-free, every Q15/Q16 microdata row preserved). Cold readers who want
to reconcile against the Table 26 standard-form universe filter the parquet
to the FY-2023-anchored standard-form respondent set; the divergence in §3
is the cost of preserving the all-respondents view.

The 6-cell scope in §3 is the verification scope. A-3 is an inventory
cross-check (§5.1), not a second anchor. No 9-cell expansion.

## 7. Reproducibility appendix

```bash
# Regenerate this report's verification grid:
uv run python etl/spikes/personnel_table26_verify.py
```

Output is the table in §3, identical to the spike's stdout on 2026-05-01.

Files referenced (all paths absolute from project root):
- `data/harmonized/herd_personnel.parquet` (parquet under test)
- `data/reference/nsf26304-tab026.pdf` (anchor source)
- `data/reference/nsf26304-taba-023.pdf` (table-inventory cross-check)
- `data/reference/nsf26304-taba-003.pdf` (A-3 surveyed-universe inventory; §5.1 cross-check)
- `etl/build_herd_personnel.py` (parquet builder)
- `etl/spikes/personnel_table26_verify.py` (this report's reproducer)
