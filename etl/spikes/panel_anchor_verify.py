"""
etl/spikes/panel_anchor_verify.py — HD 2.4.g Branch A MVP verification spike.

Purpose
-------
Reconcile the harmonized HERD panel (`data/harmonized/herd_panel.parquet`)
against the FY 2024 NCSES Table Builder anchor cohort × broad-field ×
source-class grid. Surfaces per-cell PASS/REVIEW/FAIL/STRUCTURAL_ABSENT
dispositions, the systematic-direction divergence diagnostic, and a tidy
per-cell parquet at `etl/spikes/_out/panel_anchor_verify_FY2024.parquet`
plus a console summary.

Throwaway spike. Production hardening (deposit-quality report at
`validation/reports/panel_anchor_reconciliation.md`, methods-note voice
prose) lands at HD 2.4.h as a separate sub-action.

Kill condition (non-zero exit on either)
----------------------------------------
1. Any cell carries `disposition='FAIL'` (`|pct_diff| > 2%`).
2. Any STRUCTURAL_ABSENT cell carries a non-null AND non-zero panel value
   (UCSF Engineering should be structurally empty per the FY 2024 grid;
   a populated panel cell there is a substrate-shape kill signal).

Tolerance bands (locked, principal authorization 2026-05-24)
------------------------------------------------------------
- PASS:                 |pct_diff| <= 0.5%
- REVIEW:    0.5% <     |pct_diff| <= 2%
- FAIL:                 |pct_diff| > 2%
- STRUCTURAL_ABSENT: disposition does NOT fold into FAIL counts.

Locked scoping references
-------------------------
- CLAUDE.md §8 HD 2.4.g substrate-shape lock (FY 2024 era-B-internal
  cohort-anchored verification grid; 58 substantive cells, not 60 nominal).
- `docs/methods_notes/herd_panel_etl_scoping.md` §2(b) cohort + per-spot-year
  anchor table; §13 re-shape entry 2026-05-21.
- PANEL_SKIPPER.md §8 entry dated 2026-05-21 (HD 2.4.g entry continuation).
- Vision Branch III verdict 2026-05-21 (substrate-shape lock; historical-
  vintage anchors deferred; era-boundary characterization absorbed into
  HD 2.1.b decomposition).
- CLAUDE.md §8 W4 NULL-handling lock — least-good-flag-wins propagation
  ordering: `unspecified_zero < estimated < imputed < reported`.

Cohort + structural absences: source of truth
---------------------------------------------
`data/reference/dst-table-builder-FY2024-query.yaml`. The 10 NCSES inst_ids
and the UCSF Engineering structural-absence pair are hardcoded below from
the sidecar's `query_parameters.institutions` and
`notes.empirical_grid_composition` blocks. The spike does NOT re-derive the
cohort from a top-10 query; the cohort is preserved per scoping doc §2(b)
(Branch A "the same cohort established at HD 2.1.b for
`validation/reports/era_reconciliation_2008_2011.md`") with Stanford and MIT
substituted for the four UMich/UWash/PennState/UMinnesota institutions that
dropped due to missing era-B 2009-2011 rows.

Inputs
------
- Anchor CSV:   data/reference/dst-table-builder/dst-table-builder-FY2024.csv
                (SHA-256 e0fc1f7b08f32f8963463ba591e18a188fbfc9d9f4584f2ffc50778ef46738a6)
- Sidecar YAML: data/reference/dst-table-builder-FY2024-query.yaml
                (cohort + structural-absence source of truth)
- Panel:        data/harmonized/herd_panel.parquet

Output
------
- Parquet:      etl/spikes/_out/panel_anchor_verify_FY2024.parquet (tidy per-cell)
- Console:      summary table + disposition counts + kill verdict

Per-cell schema
---------------
institution_id, institution_name, discipline_coarse, source_class,
anchor_value, panel_value, abs_diff, pct_diff, quality_flag, disposition.

Author: Skipper, 2026-05-24 (HD 2.4.g Branch A MVP).
"""

from __future__ import annotations

import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent.parent
ANCHOR_CSV = ROOT / "data" / "reference" / "dst-table-builder" / "dst-table-builder-FY2024.csv"
SIDECAR_YAML = ROOT / "data" / "reference" / "dst-table-builder-FY2024-query.yaml"
PANEL_PARQUET = ROOT / "data" / "harmonized" / "herd_panel.parquet"
OUT_DIR = Path(__file__).resolve().parent / "_out"
OUT_PARQUET = OUT_DIR / "panel_anchor_verify_FY2024.parquet"

ANCHOR_YEAR = 2024

# --- Tolerance bands (principal-authorized 2026-05-24) ----------------------
PASS_PCT = 0.5    # |pct_diff| <= 0.5% -> PASS
REVIEW_PCT = 2.0  # 0.5% < |pct_diff| <= 2.0% -> REVIEW; > 2.0% -> FAIL

# --- Cohort: hardcoded from sidecar query_parameters.institutions -----------
# (institution_id is the NCSES inst_id, matching panel-side `institution_id`
# per build_herd_panel.py:834 `CAST(inst_id AS VARCHAR) AS institution_id`.)
# The `anchor_name` column carries the abbreviated Table Builder rendering;
# the join with the anchor CSV is on `anchor_name`.
COHORT = [
    {"institution_id": "029977", "name_full": "Johns Hopkins University",                    "anchor_name": "Johns Hopkins U."},
    {"institution_id": "001319", "name_full": "University of California, San Francisco",      "anchor_name": "U. California, San Francisco"},
    {"institution_id": "003895", "name_full": "University of Wisconsin Madison",              "anchor_name": "U. Wisconsin-Madison"},
    {"institution_id": "001315", "name_full": "University of California, Los Angeles",        "anchor_name": "U. California, Los Angeles"},
    {"institution_id": "001317", "name_full": "University of California, San Diego",          "anchor_name": "U. California, San Diego"},
    {"institution_id": "002920", "name_full": "Duke University",                              "anchor_name": "Duke U."},
    {"institution_id": "003378", "name_full": "University of Pennsylvania",                   "anchor_name": "U. Pennsylvania"},
    {"institution_id": "008802", "name_full": "Ohio State University all campuses",           "anchor_name": "Ohio State U."},
    {"institution_id": "001305", "name_full": "Stanford University",                          "anchor_name": "Stanford U."},
    {"institution_id": "002178", "name_full": "Massachusetts Institute of Technology",        "anchor_name": "Massachusetts Institute of Technology"},
]

# --- Structural absences: hardcoded from sidecar notes.empirical_grid_composition ---
# UCSF (inst_id 001319) is missing both Engineering cells (federal + nonfederal).
# Diagnosis: UCSF is health-sciences-only with no Engineering school. UC system
# Engineering R&D lives at Berkeley/SD/LA/Irvine/Davis, not San Francisco.
STRUCTURAL_ABSENT = [
    {"institution_id": "001319", "discipline_coarse": "Engineering", "source_class": "federal"},
    {"institution_id": "001319", "discipline_coarse": "Engineering", "source_class": "nonfederal"},
]

# --- Broad-field axis (matches anchor CSV `Broad Field` column) -------------
DISCIPLINES = ["Engineering", "Life sciences", "Physical sciences"]

# --- Panel-side rollup-row labels per coarse bucket --------------------------
# Per discipline_fine.csv: each coarse bucket carries a `<bucket>, all`
# rollup row (e.g., "Engineering, all"). Filtering panel rows by
# discipline_coarse alone double-counts (picks up both the rollup AND
# underlying fine leaves); the anchor reports the rollup, so we filter
# panel rows on discipline_fine to the rollup label.
DISCIPLINE_ROLLUP_LABELS = {
    "Engineering": "Engineering, all",
    "Life sciences": "Life sciences, all",
    "Physical sciences": "Physical sciences, all",
}

# --- W4 quality_flag propagation ordering (least-good-wins, worst -> best) --
# Mirrors `crosswalks/era_b_reconstruction_rule.yaml`
# `quality_flag_propagation.ordering`. The spike applies the rule to the
# (Q9 federal, Q11 nonfederal) cells per the cohort × discipline × source
# join; least-good-flag-wins is unary per cell (one source-class component
# per cell) — the propagation rule's two-input form only fires when we'd
# sum federal+nonfederal into all_source, which is NOT what this spike
# verifies. The flag column passes through verbatim from the panel cell.
QUALITY_FLAG_ORDER = ("unspecified_zero", "estimated", "imputed", "reported")


def _load_anchor_grid(con: duckdb.DuckDBPyConnection) -> duckdb.DuckDBPyRelation:
    """Load the FY 2024 Table Builder CSV into a per-cell relation.

    Schema: institution_id, anchor_name, discipline_coarse, source_class,
    anchor_value (kUSD, matching panel-side `unit='kUSD_current'`).

    The CSV's `Federal and Nonfederal` column is the source class; we
    lowercase to match panel-side `source_class IN ('federal','nonfederal')`.
    The CSV's `Broad Field` column matches the `discipline_coarse` axis
    directly (Engineering, Life sciences, Physical sciences).
    """
    # Build a temp cohort table for the inst_id <-> anchor_name join.
    cohort_values = ",\n      ".join(
        f"('{c['institution_id']}', '{c['name_full'].replace(chr(39), chr(39)*2)}', "
        f"'{c['anchor_name'].replace(chr(39), chr(39)*2)}')"
        for c in COHORT
    )
    con.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE _cohort AS
        SELECT * FROM (VALUES
          {cohort_values}
        ) AS t(institution_id, name_full, anchor_name)
        """
    )
    con.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE _anchor AS
        SELECT
            c.institution_id                         AS institution_id,
            c.name_full                              AS institution_name,
            r."Broad Field"                          AS discipline_coarse,
            LOWER(r."Federal and Nonfederal")        AS source_class,
            CAST(r."R&D Expenditures by Broad Field and Fed and Nonfed Sources"
                 AS DOUBLE)                          AS anchor_value
        FROM read_csv_auto('{ANCHOR_CSV.as_posix()}', header=True) AS r
        JOIN _cohort AS c ON c.anchor_name = r."Institution Name"
        WHERE CAST(r."Fiscal Year" AS INTEGER) = {ANCHOR_YEAR}
          AND r."Broad Field" IN ('Engineering', 'Life sciences', 'Physical sciences')
          AND LOWER(r."Federal and Nonfederal") IN ('federal', 'nonfederal')
        """
    )
    return con.table("_anchor")


def _load_panel_cells(con: duckdb.DuckDBPyConnection) -> duckdb.DuckDBPyRelation:
    """Load FY 2024 era-B Q9/Q11 standard-form rollup-grain cells from the panel.

    Filter triple matches the anchor grain exactly:
      - year = ANCHOR_YEAR
      - era = 'B'
      - form_type = 'standard'
      - expenditure_type = 'r&d' (excludes Q14 r&d_equipment)
      - source_class IN ('federal','nonfederal')
      - discipline_fine IN ('Engineering, all', 'Life sciences, all',
        'Physical sciences, all')  -- the rollup row per coarse bucket
      - institution_id IN COHORT

    Why discipline_fine, not discipline_coarse: the panel carries both the
    rollup row (`Engineering, all`) AND underlying fine leaves
    (`Engineering, mechanical`, etc.) for every coarse bucket. Filtering on
    `discipline_coarse='Engineering'` would double-count (rollup + leaves).
    The Table Builder anchor reports the rollup; we filter to the rollup
    row via discipline_fine.
    """
    cohort_ids = ", ".join(f"'{c['institution_id']}'" for c in COHORT)
    rollup_labels = ", ".join(f"'{v}'" for v in DISCIPLINE_ROLLUP_LABELS.values())
    con.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE _panel AS
        SELECT
            institution_id,
            year,
            era,
            form_type,
            expenditure_type,
            source_class,
            discipline_coarse,
            discipline_fine,
            value,
            unit,
            quality_flag
        FROM read_parquet('{PANEL_PARQUET.as_posix()}')
        WHERE year = {ANCHOR_YEAR}
          AND era = 'B'
          AND form_type = 'standard'
          AND expenditure_type = 'r&d'
          AND source_class IN ('federal', 'nonfederal')
          AND discipline_fine IN ({rollup_labels})
          AND institution_id IN ({cohort_ids})
        """
    )
    return con.table("_panel")


def _assert_unit_alignment(con: duckdb.DuckDBPyConnection) -> None:
    """Verify panel-side `unit` matches anchor convention (thousands USD).

    Anchor CSV values are in thousands of USD (Table Builder convention).
    Panel-side `unit='kUSD_current'` is the same scale -> direct compare.
    Panel-side `unit='usd'` would require ×1000 on the panel side (not
    expected per build_herd_panel.py:985 hardcoded literal, but the
    assertion is drift defense for future-self).

    Fails loud on any unit value other than 'kUSD_current' or 'usd'.
    """
    units = con.execute(
        "SELECT DISTINCT unit FROM _panel ORDER BY unit"
    ).fetchall()
    unit_set = {u[0] for u in units}
    if not unit_set:
        raise RuntimeError(
            "Unit-alignment assertion: panel filter returned zero rows; "
            "cannot verify unit. Check cohort / discipline / year filters."
        )
    if unit_set == {"kUSD_current"}:
        return  # direct compare, no scaling needed
    if unit_set == {"usd"}:
        # Future-self path: rescale panel value by /1000 before compare.
        # Not expected in current build; would require code change below
        # at the diff computation. Surface and fail rather than silently
        # scale.
        raise RuntimeError(
            "Unit-alignment assertion: panel `unit='usd'` detected; spike "
            "currently expects 'kUSD_current' (direct compare with Table "
            "Builder anchor). To proceed, add a CASE in the join SQL to "
            "scale panel_value by /1000 when unit='usd'. Surfacing rather "
            "than silently scaling — verify upstream build did not regress."
        )
    raise RuntimeError(
        f"Unit-alignment assertion: panel carries unexpected unit value(s) "
        f"{sorted(unit_set)!r}. Expected {{'kUSD_current'}} (or {{'usd'}} "
        "with rescaling). Surface to maintainer; do not silently compare "
        "across unit conventions."
    )


def _build_disposition_grid(con: duckdb.DuckDBPyConnection) -> duckdb.DuckDBPyRelation:
    """Join anchor × panel on (institution_id, discipline_coarse, source_class).

    LEFT JOIN from anchor side so all 58 substantive anchor cells survive
    even if the panel is missing a cell (panel_value = NULL -> diff = NULL
    -> the disposition CASE handles it).

    Map anchor discipline_coarse to panel rollup label via a per-discipline
    CASE; the panel row that joins is the `<bucket>, all` rollup row.
    """
    # Map anchor.discipline_coarse to panel.discipline_fine rollup label.
    rollup_case_when = "\n               ".join(
        f"WHEN '{k}' THEN '{v}'"
        for k, v in DISCIPLINE_ROLLUP_LABELS.items()
    )
    con.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE _joined AS
        SELECT
            a.institution_id,
            a.institution_name,
            a.discipline_coarse,
            a.source_class,
            a.anchor_value,
            p.value           AS panel_value,
            p.quality_flag    AS quality_flag,
            ABS(a.anchor_value - p.value)                       AS abs_diff,
            CASE
                WHEN a.anchor_value IS NULL OR a.anchor_value = 0 THEN NULL
                ELSE 100.0 * (p.value - a.anchor_value) / a.anchor_value
            END                                                 AS pct_diff
        FROM _anchor AS a
        LEFT JOIN _panel AS p
          ON p.institution_id = a.institution_id
         AND p.source_class   = a.source_class
         AND p.discipline_fine = (
             CASE a.discipline_coarse
               {rollup_case_when}
             END
         )
        """
    )

    # Append the structural-absent cells as a separate slot. These are
    # never expected in the anchor (UCSF Engineering not in the FY 2024
    # export) and we assert the panel side is null/zero.
    sa_values = ",\n      ".join(
        f"('{sa['institution_id']}', '{sa['discipline_coarse']}', '{sa['source_class']}')"
        for sa in STRUCTURAL_ABSENT
    )
    cohort_lookup_case = "\n               ".join(
        f"WHEN '{c['institution_id']}' THEN '{c['name_full'].replace(chr(39), chr(39)*2)}'"
        for c in COHORT
    )
    rollup_case_when_sa = "\n               ".join(
        f"WHEN '{k}' THEN '{v}'"
        for k, v in DISCIPLINE_ROLLUP_LABELS.items()
    )
    con.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE _structural_absent AS
        WITH sa AS (
            SELECT * FROM (VALUES {sa_values})
                AS t(institution_id, discipline_coarse, source_class)
        )
        SELECT
            sa.institution_id,
            CASE sa.institution_id
              {cohort_lookup_case}
            END                                                 AS institution_name,
            sa.discipline_coarse,
            sa.source_class,
            CAST(NULL AS DOUBLE)                                AS anchor_value,
            p.value                                             AS panel_value,
            p.quality_flag                                      AS quality_flag,
            CAST(NULL AS DOUBLE)                                AS abs_diff,
            CAST(NULL AS DOUBLE)                                AS pct_diff
        FROM sa
        LEFT JOIN _panel AS p
          ON p.institution_id = sa.institution_id
         AND p.source_class   = sa.source_class
         AND p.discipline_fine = (
             CASE sa.discipline_coarse
               {rollup_case_when_sa}
             END
         )
        """
    )

    # Union the 58 substantive cells + 2 structural-absent cells; tag with
    # disposition. Substantive cell with NULL panel_value -> FAIL
    # (missing-from-panel surface). Structural-absent with null/zero panel
    # value -> STRUCTURAL_ABSENT; with populated panel value -> kill signal
    # (handled in main()).
    con.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE _grid AS
        SELECT
            institution_id,
            institution_name,
            discipline_coarse,
            source_class,
            anchor_value,
            panel_value,
            abs_diff,
            pct_diff,
            quality_flag,
            CASE
                WHEN panel_value IS NULL THEN 'FAIL'
                WHEN pct_diff IS NULL    THEN 'FAIL'
                WHEN ABS(pct_diff) <= {PASS_PCT}   THEN 'PASS'
                WHEN ABS(pct_diff) <= {REVIEW_PCT} THEN 'REVIEW'
                ELSE 'FAIL'
            END AS disposition
        FROM _joined

        UNION ALL

        SELECT
            institution_id,
            institution_name,
            discipline_coarse,
            source_class,
            anchor_value,
            panel_value,
            abs_diff,
            pct_diff,
            quality_flag,
            'STRUCTURAL_ABSENT' AS disposition
        FROM _structural_absent
        """
    )
    return con.table("_grid")


def _print_console_summary(con: duckdb.DuckDBPyConnection) -> dict:
    """Print the disposition counts + per-cell table to stdout.

    Returns a dict with the counts + kill-signal data for main()'s exit-code
    determination.
    """
    print("=" * 90)
    print(f"HD 2.4.g Branch A: panel <-> FY {ANCHOR_YEAR} Table Builder anchor reconciliation")
    print("=" * 90)
    print(f"Tolerance bands: PASS |pct| <= {PASS_PCT}%, "
          f"REVIEW {PASS_PCT}% < |pct| <= {REVIEW_PCT}%, "
          f"FAIL |pct| > {REVIEW_PCT}%")
    print(f"Cohort: {len(COHORT)} institutions; structural absences: "
          f"{len(STRUCTURAL_ABSENT)} (UCSF Engineering federal + nonfederal)")
    print()

    # Per-cell table
    print(f"{'inst_id':<8}  {'institution':<42}  {'discipline':<18}  "
          f"{'src':<10}  {'anchor':>12}  {'panel':>12}  {'pct_diff':>8}  "
          f"{'qflag':<16}  disposition")
    print("-" * 142)
    rows = con.execute(
        """
        SELECT
            institution_id, institution_name, discipline_coarse, source_class,
            anchor_value, panel_value, pct_diff, quality_flag, disposition
        FROM _grid
        ORDER BY institution_id, discipline_coarse, source_class
        """
    ).fetchall()
    for r in rows:
        inst_id, inst_name, disc, src, anchor, panel, pct, qflag, disp = r
        anchor_s = f"{anchor:>12,.0f}" if anchor is not None else f"{'(absent)':>12}"
        panel_s = f"{panel:>12,.0f}"   if panel is not None  else f"{'(null)':>12}"
        pct_s = f"{pct:>+7.3f}%"       if pct is not None    else f"{'(n/a)':>8}"
        qflag_s = qflag if qflag is not None else "(null)"
        print(f"{inst_id:<8}  {inst_name[:42]:<42}  {disc[:18]:<18}  "
              f"{src:<10}  {anchor_s}  {panel_s}  {pct_s}  "
              f"{qflag_s[:16]:<16}  {disp}")
    print()

    # Disposition counts
    counts = dict(con.execute(
        "SELECT disposition, COUNT(*) FROM _grid GROUP BY disposition ORDER BY disposition"
    ).fetchall())
    total = sum(counts.values())
    print("Disposition counts:")
    for disp in ("PASS", "REVIEW", "FAIL", "STRUCTURAL_ABSENT"):
        n = counts.get(disp, 0)
        print(f"  {disp:<18}  {n:>3} / {total}")
    print()

    # Systematic-divergence diagnostic (Skipper scoping hidden-edge #6).
    # If all 58 substantive cells diverge in the same direction with median
    # |pct_diff| > 0.5%, the staged CSV may have been standard-form-only
    # despite the sidecar declaring all-respondents -> CSV re-export needed,
    # not a panel issue.
    div_row = con.execute(
        f"""
        WITH s AS (
            SELECT pct_diff
            FROM _grid
            WHERE disposition <> 'STRUCTURAL_ABSENT'
              AND pct_diff IS NOT NULL
        )
        SELECT
            COUNT(*)                                            AS n_cells,
            SUM(CASE WHEN pct_diff > 0 THEN 1 ELSE 0 END)       AS n_positive,
            SUM(CASE WHEN pct_diff < 0 THEN 1 ELSE 0 END)       AS n_negative,
            MEDIAN(ABS(pct_diff))                               AS median_abs_pct
        FROM s
        """
    ).fetchone()
    n_cells, n_pos, n_neg, median_abs_pct = div_row
    if n_cells and (n_pos == n_cells or n_neg == n_cells) and median_abs_pct is not None and median_abs_pct > 0.5:
        direction = "positive" if n_pos == n_cells else "negative"
        print(f"WARNING: systematic-divergence surface — all {n_cells} substantive cells "
              f"diverge in the same ({direction}) direction with median "
              f"|pct_diff| = {median_abs_pct:.3f}%. Skipper hidden-edge #6: staged "
              f"CSV may have been standard-form-only despite sidecar declaring "
              f"all-respondents. Investigate Table Builder export, not panel.")
        print()

    # Kill-signal check: STRUCTURAL_ABSENT cells with non-null AND non-zero
    # panel value.
    sa_kill_rows = con.execute(
        """
        SELECT institution_id, institution_name, discipline_coarse, source_class, panel_value
        FROM _grid
        WHERE disposition = 'STRUCTURAL_ABSENT'
          AND panel_value IS NOT NULL
          AND panel_value <> 0
        """
    ).fetchall()

    fail_count = counts.get("FAIL", 0)
    return {
        "counts": counts,
        "total": total,
        "fail_count": fail_count,
        "sa_kill_rows": sa_kill_rows,
    }


def main() -> int:
    if not ANCHOR_CSV.exists():
        print(f"ERROR: anchor CSV not found at {ANCHOR_CSV}", file=sys.stderr)
        return 2
    if not SIDECAR_YAML.exists():
        print(f"ERROR: sidecar YAML not found at {SIDECAR_YAML}", file=sys.stderr)
        return 2
    if not PANEL_PARQUET.exists():
        print(
            f"ERROR: panel parquet not found at {PANEL_PARQUET}. "
            "Run `uv run python etl/build_herd_panel.py` first.",
            file=sys.stderr,
        )
        return 2

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect()

    # Stage 1: load inputs into temp tables.
    _load_anchor_grid(con)
    _load_panel_cells(con)

    # Stage 2: runtime assertion on unit alignment (drift defense).
    _assert_unit_alignment(con)

    # Stage 3: build the 60-row disposition grid (58 substantive + 2 SA).
    grid = _build_disposition_grid(con)

    # Stage 4: write tidy per-cell parquet.
    con.execute(
        f"""
        COPY (
            SELECT * FROM _grid
            ORDER BY institution_id, discipline_coarse, source_class
        ) TO '{OUT_PARQUET.as_posix()}' (FORMAT 'parquet')
        """
    )
    print(f"Wrote per-cell parquet -> {OUT_PARQUET}")
    print()

    # Stage 5: console summary + collect kill-signal data.
    summary = _print_console_summary(con)

    # Stage 6: kill-condition verdict + exit code.
    print("=" * 90)
    print("Kill-condition verdict")
    print("=" * 90)
    kill = False

    if summary["fail_count"] > 0:
        print(f"FAIL: {summary['fail_count']} cell(s) carry disposition='FAIL' "
              f"(|pct_diff| > {REVIEW_PCT}% or missing-from-panel).")
        kill = True
    else:
        print(f"PASS: 0 cells carry disposition='FAIL'.")

    if summary["sa_kill_rows"]:
        print(f"FAIL: {len(summary['sa_kill_rows'])} STRUCTURAL_ABSENT cell(s) "
              f"carry non-null, non-zero panel value (substrate-shape kill signal):")
        for r in summary["sa_kill_rows"]:
            inst_id, inst_name, disc, src, val = r
            print(f"  inst_id={inst_id} ({inst_name}) "
                  f"discipline={disc} source_class={src} panel_value={val!r}")
        kill = True
    else:
        n_sa = summary["counts"].get("STRUCTURAL_ABSENT", 0)
        print(f"PASS: all {n_sa} STRUCTURAL_ABSENT cell(s) have null/zero panel value.")

    print()
    if kill:
        print("VERDICT: KILL — see FAIL lines above. Exit code 1.")
        return 1
    print("VERDICT: OK — spike-side checks clear. Exit code 0.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
