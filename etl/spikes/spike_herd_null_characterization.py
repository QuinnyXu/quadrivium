"""
spike_herd_null_characterization.py — HD 2.4 NULL semantics spike (throwaway).

Budget: 30–60 minutes. Deliverable is `validation/reports/herd_null_characterization_findings.md`,
not promoted code. Author: Skipper, 2026-05-09.

Why
---
The HD 2.4 scoping document (§14.2) currently recommends Option A (NULL-as-zero) for the era-B
reconstruction `Q9 NULL + Q11 value = Q11 value`. That recommendation conflates three semantic
cases identified during maintainer review:
  (a) genuine zero — institution had no R&D in that category;
  (b) NSF-imputed value — possibly flagged in raw CSV;
  (c) NSF-labeled "didn't report" — possibly flagged in raw CSV.

The FY24 Guide (`data/raw/herd/Guide To Herd Data Files FY24.pdf`) §1.2, §1.3.1, §2.2, §2.3
documents that:
  - the `status` column is the flag column,
  - era B uses {Blank=Normal, i=Imputed, n=Data not available} (page 10),
  - era A adds a fourth code: e=Estimated by NCSES (page 25),
  - "for each data line ... to which a non-zero response has been received, a data record is
    present" (page 8 / page 23) — i.e. genuine-zero leaves carry NO ROW AT ALL,
  - "for total rows ... a data record is present regardless of whether a zero or non-zero
    response has been received" — i.e. total rows always carry a record (even if zero).

So the original three-case framing is incomplete: case (d) "row simply not present in the raw CSV"
is the dominant disposition for genuine zeros, distinct from case (c) "row present with status='n'".

This spike characterizes the empirical NULL/flag distribution per spot year (FY 2008, FY 2017,
FY 2024) so the maintainer can lock NULL handling on evidence rather than on the schema doc's
default Option A.

What it does
------------
For each spot year, for the in-scope questions:

  - FY 2008 (era A): question='Expenditures by S&E field'
  - FY 2017 (era B): Q9='Federal expenditures by field and agency',
                     Q11='Nonfederal expenditures by field and source'
  - FY 2024 (era B): same Q9/Q11

reports:

  1. Total row count and overall data/value/status NULL-rate.
  2. Status code distribution (Blank / i / n / e / other) on rows scoped to the relevant
     question and `column='Total'` (the all-source / Q9-Total / Q11-Total cells).
  3. Cross-tab of `data IS NULL` × `status` to characterize each NULL cell type.
  4. Institution-grade roll-up: how many institutions have ALL Total cells flagged i / n /
     blank / mixed?
  5. Era-B only (FY 2017, FY 2024): cross-question NULL correlation at (inst, discipline_fine,
     column='Total') — does an institution with NULL Q9.Total have NULL Q11.Total too, or only
     one side?

Stops at findings. Does not write to crosswalks; does not modify the loader; does not run
recommendations.
"""

from __future__ import annotations

import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from etl._load import read_herd_csv  # noqa: E402

ERA_A_FIELD_QUESTION = "Expenditures by S&E field"
ERA_B_Q9 = "Federal expenditures by field and agency"
ERA_B_Q11 = "Nonfederal expenditures by field and source"


def _print_header(title: str) -> None:
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def _q_inscope_clause(year: int) -> str:
    """SQL fragment: rows in scope for this spot year."""
    if year <= 2009:
        return f"question = '{ERA_A_FIELD_QUESTION}'"
    return (
        f"question IN ('{ERA_B_Q9}', '{ERA_B_Q11}')"
    )


def overall_counts(con: duckdb.DuckDBPyConnection, rel_name: str, year: int) -> None:
    """Headline counts for in-scope rows: total, data NULL, value NULL, status."""
    _print_header(f"FY {year} — overall counts (in-scope question rows)")
    inscope = _q_inscope_clause(year)

    n_total = con.sql(
        f"SELECT COUNT(*) FROM {rel_name} WHERE {inscope}"
    ).fetchone()[0]
    print(f"  rows in-scope (any column):        {n_total:,}")

    # Restrict to column='Total' rows (the cells that feed the all-source rule for era B,
    # and the all-source value for era A). For era B, this is the Total column on Q9/Q11.
    n_total_col = con.sql(
        f"SELECT COUNT(*) FROM {rel_name} WHERE {inscope} AND \"column\" = 'Total'"
    ).fetchone()[0]
    print(f"  rows with column='Total':          {n_total_col:,}")

    # Of column='Total' rows, how many have:
    #   data NULL or empty, value (cast) NULL, status non-blank
    breakdown = con.sql(
        f"""
        SELECT
            COUNT(*)                                                 AS n_rows,
            COUNT(*) FILTER (WHERE data IS NULL OR data = '')        AS data_null_or_empty,
            COUNT(*) FILTER (WHERE value IS NULL)                    AS value_null,
            COUNT(*) FILTER (WHERE status IS NOT NULL
                              AND status <> '')                      AS status_non_blank
        FROM {rel_name}
        WHERE {inscope} AND "column" = 'Total'
        """
    ).fetchone()
    n_rows, data_null, value_null, status_nb = breakdown
    pct = lambda n: (n / n_rows * 100) if n_rows else 0.0
    print(f"  of column='Total' rows ({n_rows:,}):")
    print(f"    data NULL or empty:            {data_null:,} ({pct(data_null):.2f}%)")
    print(f"    value (TRY_CAST) NULL:         {value_null:,} ({pct(value_null):.2f}%)")
    print(f"    status non-blank:              {status_nb:,} ({pct(status_nb):.2f}%)")


def status_distribution(con: duckdb.DuckDBPyConnection, rel_name: str, year: int) -> None:
    """Status code distribution on column='Total' rows."""
    _print_header(f"FY {year} — status code distribution (column='Total')")
    inscope = _q_inscope_clause(year)
    rows = con.sql(
        f"""
        SELECT
            COALESCE(NULLIF(status, ''), '<blank>') AS status_norm,
            COUNT(*) AS n
        FROM {rel_name}
        WHERE {inscope} AND "column" = 'Total'
        GROUP BY 1
        ORDER BY n DESC
        """
    ).fetchall()
    n_total = sum(n for _, n in rows)
    print(f"  total Total-column rows: {n_total:,}")
    for status_norm, n in rows:
        pct = (n / n_total * 100) if n_total else 0.0
        print(f"    status={status_norm!r:>12}  n={n:>6,}  ({pct:5.2f}%)")


def crosstab_data_status(con: duckdb.DuckDBPyConnection, rel_name: str, year: int) -> None:
    """Cross-tab: (data IS NULL/empty) × status, on column='Total' rows."""
    _print_header(f"FY {year} — cross-tab (data state × status), column='Total'")
    inscope = _q_inscope_clause(year)
    rows = con.sql(
        f"""
        SELECT
            CASE
                WHEN data IS NULL OR data = '' THEN 'data_null_or_empty'
                WHEN TRY_CAST(data AS DOUBLE) IS NOT NULL THEN 'data_numeric'
                ELSE 'data_non_numeric_text'
            END                                       AS data_state,
            COALESCE(NULLIF(status, ''), '<blank>')   AS status_norm,
            COUNT(*)                                  AS n
        FROM {rel_name}
        WHERE {inscope} AND "column" = 'Total'
        GROUP BY 1, 2
        ORDER BY 1, n DESC
        """
    ).fetchall()
    print(f"  {'data_state':<24} {'status':<12} {'n':>8}")
    for data_state, status_norm, n in rows:
        print(f"  {data_state:<24} {status_norm:<12} {n:>8,}")


def institution_grade_rollup(
    con: duckdb.DuckDBPyConnection, rel_name: str, year: int
) -> None:
    """Per-institution: count of Total cells that are blank-status / i / n / other.

    Bucket institutions by 'pattern':
      - all_blank: every Total cell in scope has blank status (fully reported)
      - all_i:     every Total cell is imputed
      - all_n:     every Total cell is 'data not available'
      - any_e:     at least one cell with status='e' (era-A only)
      - mixed:     mix of blank + flagged
    """
    _print_header(f"FY {year} — institution-grade rollup (column='Total' cells per inst)")
    inscope = _q_inscope_clause(year)
    # Use the era-appropriate institution identifier. Era A: fice; era B: inst_id.
    # `read_herd_csv` already mirrors fice into inst_id for era A, so inst_id works either way.
    rows = con.sql(
        f"""
        WITH per_inst AS (
            SELECT
                inst_id,
                COUNT(*) AS n_cells,
                COUNT(*) FILTER (WHERE status IS NULL OR status = '')   AS n_blank,
                COUNT(*) FILTER (WHERE status = 'i')                    AS n_imp,
                COUNT(*) FILTER (WHERE status = 'n')                    AS n_unavail,
                COUNT(*) FILTER (WHERE status = 'e')                    AS n_estim,
                COUNT(*) FILTER (WHERE status NOT IN ('', 'i', 'n', 'e')
                                  AND status IS NOT NULL)               AS n_other
            FROM {rel_name}
            WHERE {inscope} AND "column" = 'Total'
            GROUP BY inst_id
        )
        SELECT
            CASE
                WHEN n_blank = n_cells                THEN 'all_blank (fully reported)'
                WHEN n_imp   = n_cells                THEN 'all_imputed'
                WHEN n_unavail = n_cells              THEN 'all_data_not_available'
                WHEN n_estim > 0 AND n_blank + n_estim = n_cells
                                                       THEN 'estimated_only_or_estimated_plus_blank'
                WHEN n_imp + n_blank = n_cells AND n_imp > 0
                                                       THEN 'mixed_blank_plus_imputed'
                WHEN n_unavail + n_blank = n_cells AND n_unavail > 0
                                                       THEN 'mixed_blank_plus_data_not_available'
                ELSE                                       'other_mix'
            END AS pattern,
            COUNT(*) AS n_inst
        FROM per_inst
        GROUP BY 1
        ORDER BY n_inst DESC
        """
    ).fetchall()
    n_inst_total = sum(n for _, n in rows)
    print(f"  total institutions in scope: {n_inst_total:,}")
    for pattern, n in rows:
        pct = (n / n_inst_total * 100) if n_inst_total else 0.0
        print(f"    {pattern:<48}  n={n:>5,}  ({pct:5.2f}%)")


def cross_question_null_correlation(
    con: duckdb.DuckDBPyConnection, rel_name: str, year: int
) -> None:
    """Era B only: cross-question NULL correlation at (inst, discipline, column='Total')."""
    if year <= 2009:
        return
    _print_header(
        f"FY {year} — Q9/Q11 cross-question NULL correlation at (inst, row, column='Total')"
    )
    rows = con.sql(
        f"""
        WITH q9 AS (
            SELECT inst_id, "row" AS discipline_raw,
                   data, status, value
            FROM {rel_name}
            WHERE question = '{ERA_B_Q9}' AND "column" = 'Total'
        ),
        q11 AS (
            SELECT inst_id, "row" AS discipline_raw,
                   data, status, value
            FROM {rel_name}
            WHERE question = '{ERA_B_Q11}' AND "column" = 'Total'
        ),
        joined AS (
            SELECT
                COALESCE(q9.inst_id, q11.inst_id)                    AS inst_id,
                COALESCE(q9.discipline_raw, q11.discipline_raw)      AS discipline_raw,
                q9.data        AS q9_data,
                q9.value       AS q9_value,
                COALESCE(NULLIF(q9.status, ''), '<blank>')   AS q9_status,
                q11.data       AS q11_data,
                q11.value      AS q11_value,
                COALESCE(NULLIF(q11.status, ''), '<blank>')  AS q11_status,
                CASE WHEN q9.inst_id IS NULL THEN 'q9_row_absent'
                     WHEN q9.value IS NULL THEN 'q9_value_null'
                     ELSE 'q9_value_present' END             AS q9_state,
                CASE WHEN q11.inst_id IS NULL THEN 'q11_row_absent'
                     WHEN q11.value IS NULL THEN 'q11_value_null'
                     ELSE 'q11_value_present' END            AS q11_state
            FROM q9
            FULL OUTER JOIN q11
              ON q9.inst_id = q11.inst_id
             AND q9.discipline_raw = q11.discipline_raw
        )
        SELECT q9_state, q11_state, COUNT(*) AS n
        FROM joined
        GROUP BY 1, 2
        ORDER BY 1, 2
        """
    ).fetchall()
    n_total = sum(n for _, _, n in rows)
    print(f"  total (inst, row='discipline_raw') joined cells: {n_total:,}")
    print(f"  {'q9_state':<22} {'q11_state':<22} {'n':>8}")
    for q9s, q11s, n in rows:
        pct = (n / n_total * 100) if n_total else 0.0
        print(f"  {q9s:<22} {q11s:<22} {n:>8,}  ({pct:5.2f}%)")


def total_row_completeness(
    con: duckdb.DuckDBPyConnection, rel_name: str, year: int
) -> None:
    """For era B: confirm that every (inst, discipline) with ANY Q9/Q11 row also
    carries a column='Total' row. Per FY24 Guide page 8, total rows are
    always emitted; this is a sanity check against that claim.
    """
    if year <= 2009:
        return
    _print_header(
        f"FY {year} — Total-row completeness sanity check (Q9 and Q11)"
    )
    for q in (ERA_B_Q9, ERA_B_Q11):
        rows = con.sql(
            f"""
            WITH any_row AS (
                SELECT inst_id, "row" AS discipline_raw
                FROM {rel_name}
                WHERE question = '{q}'
                GROUP BY inst_id, "row"
            ),
            total_row AS (
                SELECT inst_id, "row" AS discipline_raw
                FROM {rel_name}
                WHERE question = '{q}' AND "column" = 'Total'
                GROUP BY inst_id, "row"
            )
            SELECT
                (SELECT COUNT(*) FROM any_row)                       AS n_any,
                (SELECT COUNT(*) FROM total_row)                     AS n_total,
                (SELECT COUNT(*) FROM any_row a
                 LEFT JOIN total_row t USING (inst_id, discipline_raw)
                 WHERE t.inst_id IS NULL)                            AS n_any_without_total
            """
        ).fetchone()
        n_any, n_total, n_any_no_total = rows
        print(
            f"  question={q!r}\n"
            f"    distinct (inst, row) with ANY column:    {n_any:>6,}\n"
            f"    distinct (inst, row) with column='Total':{n_total:>6,}\n"
            f"    (inst, row) with any column but no Total:{n_any_no_total:>6,}"
        )


def row_absence_means_zero_check(
    con: duckdb.DuckDBPyConnection, rel_name: str, year: int
) -> None:
    """For era B: at the Total-row grain, how many institutions emit a Q9 Total
    row for the 'All' discipline-rollup row but have no Q9 leaf rows
    (suggesting genuine zero federal R&D in those leaves), vs. how many
    have leaves but skip the 'All' row?

    This probes whether 'row absent' at a (inst, discipline) cell means
    'genuine zero' or whether it might mean 'institution didn't fill out Q9
    at all'.
    """
    if year <= 2009:
        return
    _print_header(
        f"FY {year} — Q9 institution-level coverage (any vs. only-All vs. with-leaves)"
    )
    for q in (ERA_B_Q9, ERA_B_Q11):
        # Per institution, count Total-column rows for question q at:
        #   (a) row='All' (the all-fields rollup)
        #   (b) any other row (S&E or non-S&E leaf or *, all rollup)
        rows = con.sql(
            f"""
            WITH per_inst AS (
                SELECT
                    inst_id,
                    COUNT(*) FILTER (WHERE "row" = 'All')                       AS n_all_row,
                    COUNT(*) FILTER (WHERE "row" <> 'All')                      AS n_other_rows
                FROM {rel_name}
                WHERE question = '{q}' AND "column" = 'Total'
                GROUP BY inst_id
            )
            SELECT
                CASE
                    WHEN n_all_row >  0 AND n_other_rows >  0 THEN 'has_All_and_other'
                    WHEN n_all_row >  0 AND n_other_rows =  0 THEN 'has_only_All_row'
                    WHEN n_all_row =  0 AND n_other_rows >  0 THEN 'has_only_other_rows'
                    ELSE                                          'has_no_rows_at_all'
                END AS pattern,
                COUNT(*) AS n_inst
            FROM per_inst
            GROUP BY 1
            ORDER BY n_inst DESC
            """
        ).fetchall()
        n_inst = sum(n for _, n in rows)
        print(f"  question={q!r}  institutions emitting any Total-column row: {n_inst:,}")
        for pattern, n in rows:
            pct = (n / n_inst * 100) if n_inst else 0.0
            print(f"    {pattern:<32}  n={n:>5,}  ({pct:5.2f}%)")


def status_n_check_anywhere(
    con: duckdb.DuckDBPyConnection, rel_name: str, year: int
) -> None:
    """Confirm whether status='n' (Data not available) ever appears in this year,
    regardless of question or column. The Guide documents 'n' as a valid code;
    the column='Total' scan above showed zero. Check the rest of the file.
    """
    _print_header(f"FY {year} — status='n' presence anywhere in the file")
    rows = con.sql(
        f"""
        SELECT
            COALESCE(NULLIF(status, ''), '<blank>') AS status_norm,
            COUNT(*) AS n
        FROM {rel_name}
        GROUP BY 1
        ORDER BY n DESC
        """
    ).fetchall()
    n_total = sum(n for _, n in rows)
    print(f"  total rows (any question, any column): {n_total:,}")
    for status_norm, n in rows:
        pct = (n / n_total * 100) if n_total else 0.0
        print(f"    status={status_norm!r:>12}  n={n:>8,}  ({pct:5.2f}%)")


def headline_proportions(
    con: duckdb.DuckDBPyConnection, rel_name: str, year: int
) -> dict:
    """Compute the four headline proportions on column='Total' rows.

    Returns a dict so the findings doc can quote them.
    """
    inscope = _q_inscope_clause(year)
    row = con.sql(
        f"""
        SELECT
            COUNT(*) AS n,
            COUNT(*) FILTER (WHERE (status IS NULL OR status = '')
                              AND value IS NOT NULL)            AS reported_value,
            COUNT(*) FILTER (WHERE status = 'i')                 AS imputed,
            COUNT(*) FILTER (WHERE status = 'n')                 AS data_not_available,
            COUNT(*) FILTER (WHERE status = 'e')                 AS estimated,
            COUNT(*) FILTER (WHERE (status IS NULL OR status = '')
                              AND value IS NULL)                 AS unflagged_null
        FROM {rel_name}
        WHERE {inscope} AND "column" = 'Total'
        """
    ).fetchone()
    n, reported, imp, unavail, estim, unflagged = row
    return {
        "n": n,
        "reported_value": reported,
        "imputed": imp,
        "data_not_available": unavail,
        "estimated": estim,
        "unflagged_null": unflagged,
    }


def run_year(year: int) -> dict:
    print()
    print("#" * 78)
    print(f"# FY {year}")
    print("#" * 78)

    con = duckdb.connect()
    rel = read_herd_csv(year, con=con)
    # Persist to a named relation so SQL queries below don't have to keep
    # re-evaluating the projection. Materialize into a temp table.
    con.execute("CREATE OR REPLACE TEMP TABLE r AS SELECT * FROM rel")  # type: ignore[arg-type]
    # The rel object isn't named in con's namespace by default; bind it explicitly.
    con.register("rel_view", rel)
    con.execute("CREATE OR REPLACE TEMP TABLE r AS SELECT * FROM rel_view")

    overall_counts(con, "r", year)
    status_distribution(con, "r", year)
    crosstab_data_status(con, "r", year)
    institution_grade_rollup(con, "r", year)
    cross_question_null_correlation(con, "r", year)
    total_row_completeness(con, "r", year)
    row_absence_means_zero_check(con, "r", year)
    status_n_check_anywhere(con, "r", year)
    return headline_proportions(con, "r", year)


def main() -> int:
    summary: dict[int, dict] = {}
    for year in (2008, 2017, 2024):
        summary[year] = run_year(year)

    print()
    print("=" * 78)
    print("HEADLINE SUMMARY — column='Total' rows in scope")
    print("=" * 78)
    print(
        f"  {'year':>5}  {'n':>7}  "
        f"{'reported':>10}  {'imputed':>9}  {'unavail':>9}  "
        f"{'estim':>7}  {'unflag_null':>12}"
    )
    for year, p in summary.items():
        n = p["n"] or 1  # avoid /0 on display
        print(
            f"  {year:>5}  {p['n']:>7,}  "
            f"{p['reported_value']:>5,} "
            f"({p['reported_value']/n*100:>4.1f}%)  "
            f"{p['imputed']:>4,} "
            f"({p['imputed']/n*100:>4.1f}%)  "
            f"{p['data_not_available']:>4,} "
            f"({p['data_not_available']/n*100:>4.1f}%)  "
            f"{p['estimated']:>3,} "
            f"({p['estimated']/n*100:>4.1f}%)  "
            f"{p['unflagged_null']:>5,} "
            f"({p['unflagged_null']/n*100:>4.1f}%)"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
