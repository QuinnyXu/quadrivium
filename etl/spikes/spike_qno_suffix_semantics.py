"""HD 2.4.a Track 2 — qno suffix semantics verification spike.

Throwaway. Stops at evidence. Does not amend spec or build code.

Purpose
-------
Stage 2 spec defect surfaced in the HD 2.4.a smoke test: the era-B filter
``questionnaire_no IN ('4','5','9','11','14')`` matched zero rows in
FY 2024 because the raw qno is encoded as zero-padded compound forms
(`'09A'`, `'09B01'..'09K'`, `'09D06'`, `'11A'`, `'14A'..'14K'`,
`'04'`, `'05'`).

Question for the spike: does the qno suffix carry source-class semantic
load, or is the question label sufficient on its own? Inspect FY 2017
and FY 2024 (era-B years where compound forms appear) to characterize
the suffix and check cross-year stability.

Outputs
-------
Per qno form:
  - example raw_row_label, example column, example value, example status
  - distinct count of (row, column) pairs
  - distinct count of question labels (should be 1 per qno form if
    suffix is structural to one question)
  - cross-year match: same qno form FY 2017 vs. FY 2024

Evidence is dumped to stdout; the findings doc walks through the print
output.
"""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from etl._load import read_herd_csv  # noqa: E402


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def banner(s: str) -> None:
    print()
    print("=" * 78)
    print(s)
    print("=" * 78)


def section(s: str) -> None:
    print()
    print(f"--- {s} ---")


def enumerate_compound_qno_forms(
    con: duckdb.DuckDBPyConnection, rel: duckdb.DuckDBPyRelation, year: int
) -> list[tuple[str, int, int, int, str]]:
    """Return [(qno, n_rows, n_distinct_questions, n_distinct_row_col_pairs, sample_question), ...]
    for every distinct qno value that maps to a Q4/Q5/Q9/Q11/Q14 family
    (numeric prefix in {'04','05','09','11','14','4','5','9'}).

    We only enumerate qno forms tied to the questions the Stage 2 spec is
    trying to filter on; we do not enumerate every qno in the file.
    """
    sql = f"""
        SELECT
            questionnaire_no,
            COUNT(*) AS n,
            COUNT(DISTINCT question) AS n_distinct_questions,
            COUNT(DISTINCT ("row" || '||' || "column")) AS n_distinct_row_col_pairs,
            ANY_VALUE(question) AS sample_question
        FROM ({rel.sql_query()})
        WHERE
            questionnaire_no LIKE '04%' OR questionnaire_no LIKE '4%' OR
            questionnaire_no LIKE '05%' OR questionnaire_no LIKE '5%' OR
            questionnaire_no LIKE '09%' OR questionnaire_no LIKE '9%' OR
            questionnaire_no LIKE '11%' OR
            questionnaire_no LIKE '14%' OR
            questionnaire_no IN ('4','5','9','11','14','04','05','09')
        GROUP BY questionnaire_no
        ORDER BY questionnaire_no
    """
    return con.sql(sql).fetchall()


def sample_rows_for_qno(
    con: duckdb.DuckDBPyConnection,
    rel: duckdb.DuckDBPyRelation,
    qno: str,
    year: int,
    n_samples: int = 5,
) -> list[tuple]:
    """Pull n_samples representative rows for a qno value to characterize
    what the suffix indexes on.
    """
    sql = f"""
        SELECT
            questionnaire_no,
            question,
            "row",
            "column",
            data,
            status,
            standardized_agency_names
        FROM ({rel.sql_query()})
        WHERE questionnaire_no = '{qno.replace("'", "''")}'
        ORDER BY "row", "column"
        LIMIT {n_samples}
    """
    return con.sql(sql).fetchall()


def distinct_columns_for_qno(
    con: duckdb.DuckDBPyConnection,
    rel: duckdb.DuckDBPyRelation,
    qno: str,
) -> list[tuple[str, int]]:
    """Distinct `column` values present for a given qno, with row counts.
    Important for understanding what the suffix indexes — agency? source?
    field-vs-total split?
    """
    sql = f"""
        SELECT "column", COUNT(*) AS n
        FROM ({rel.sql_query()})
        WHERE questionnaire_no = '{qno.replace("'", "''")}'
        GROUP BY "column"
        ORDER BY n DESC
        LIMIT 20
    """
    return con.sql(sql).fetchall()


def distinct_rows_for_qno(
    con: duckdb.DuckDBPyConnection,
    rel: duckdb.DuckDBPyRelation,
    qno: str,
) -> list[tuple[str, int]]:
    """Distinct `row` values present for a given qno, with row counts."""
    sql = f"""
        SELECT "row", COUNT(*) AS n
        FROM ({rel.sql_query()})
        WHERE questionnaire_no = '{qno.replace("'", "''")}'
        GROUP BY "row"
        ORDER BY n DESC
        LIMIT 20
    """
    return con.sql(sql).fetchall()


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #


def inspect_year(year: int) -> dict[str, list[tuple]]:
    """Run the full inspection battery for one year. Return {qno: rows}
    sample dict for cross-year comparison.
    """
    banner(f"FY {year} (era B) — qno suffix semantics")

    con = duckdb.connect()
    rel = read_herd_csv(year, con=con)

    section("All compound qno forms tied to Q4/Q5/Q9/Q11/Q14 families")
    forms = enumerate_compound_qno_forms(con, rel, year)
    print(f"  {'qno':>10s}  {'n_rows':>10s}  {'n_distinct_q':>12s}  "
          f"{'n_dist_rowcol':>13s}  sample_question")
    for qno, n, ndq, nrc, sq in forms:
        print(f"  {qno!r:>10s}  {n:>10,}  {ndq:>12d}  {nrc:>13d}  {sq!r}")

    sample_dict: dict[str, list[tuple]] = {}

    # For each qno form, dump 5 sample rows and the distinct columns/rows.
    for qno, _, _, _, _ in forms:
        section(f"qno {qno!r}: sample rows + distinct columns + distinct rows")

        samples = sample_rows_for_qno(con, rel, qno, year, n_samples=5)
        sample_dict[qno] = samples
        print(f"  {'qno':>8s}  {'question':<48s}  {'row':<28s}  "
              f"{'column':<22s}  {'data':>14s}  {'status':>6s}  "
              f"std_agency_name")
        for s in samples:
            qno_v, q_v, row_v, col_v, data_v, status_v, std_v = s
            print(
                f"  {qno_v!r:>8s}  "
                f"{(q_v or '')[:46]!r:<48s}  "
                f"{(row_v or '')[:26]!r:<28s}  "
                f"{(col_v or '')[:20]!r:<22s}  "
                f"{(data_v or '')[:12]!r:>14s}  "
                f"{(status_v or '')[:4]!r:>6s}  "
                f"{(std_v or '')!r}"
            )

        cols = distinct_columns_for_qno(con, rel, qno)
        print(f"    distinct columns ({len(cols)} shown):")
        for c, n in cols:
            print(f"      column={c!r:35s}  n={n:,}")

        rows = distinct_rows_for_qno(con, rel, qno)
        print(f"    distinct rows ({len(rows)} shown):")
        for r, n in rows:
            print(f"      row={r!r:35s}  n={n:,}")

    return sample_dict


def cross_year_consistency(
    fy17: dict[str, list[tuple]], fy24: dict[str, list[tuple]]
) -> None:
    banner("Cross-year consistency: FY 2017 vs FY 2024")
    section("qno values present in each year")
    keys_17 = set(fy17)
    keys_24 = set(fy24)
    in_both = sorted(keys_17 & keys_24)
    only_17 = sorted(keys_17 - keys_24)
    only_24 = sorted(keys_24 - keys_17)
    print(f"  In both years: {in_both}")
    print(f"  FY 2017 only:  {only_17}")
    print(f"  FY 2024 only:  {only_24}")

    section("For each qno in both years, compare sample-row question label")
    print(f"  {'qno':>8s}  {'FY17 sample question':<50s}  "
          f"{'FY24 sample question':<50s}  match?")
    for qno in in_both:
        q17 = fy17[qno][0][1] if fy17[qno] else None
        q24 = fy24[qno][0][1] if fy24[qno] else None
        match = "YES" if q17 == q24 else "DRIFT"
        print(
            f"  {qno!r:>8s}  "
            f"{(q17 or '')[:48]!r:<50s}  "
            f"{(q24 or '')[:48]!r:<50s}  {match}"
        )


def main() -> None:
    fy17 = inspect_year(2017)
    fy24 = inspect_year(2024)
    cross_year_consistency(fy17, fy24)
    print()
    print("=" * 78)
    print(" Spike complete. See validation/reports/qno_suffix_semantics_findings.md")
    print("=" * 78)


if __name__ == "__main__":
    main()
