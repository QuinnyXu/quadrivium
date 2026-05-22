"""
etl/spikes/probe_status_c_codeset.py — empirical characterization of the
era-A `status='c'` raw code surfaced at HD 2.4.b Stage 4 smoke test.

Surfaced 2026-05-10 by the HD 2.4.b round 1 Stage 4 smoke test, when
Stage 3's loud-fail assertion ran across 1973-2009 (HD 2.4.a smoke only
covered FY 2008 / FY 2024 — `status='c'` was not in either of those
years). The Stage 3 assertion is operating exactly as designed: it
caught a raw-CSV status code outside the FY24 Guide documented codeset
{blank, 'i', 'e', 'u'} and refused to silently map it.

This probe characterizes the finding without committing to a resolution:

  - Which era-A years carry `status='c'` rows?
  - In which questions / columns / row labels does it appear?
  - What is the `data` value distribution on those rows?
  - Per-year row counts at column='Total' (the Stage 4 filter scope)
    vs. non-Total columns?

Output prints to stdout. No artifact written. Spike discipline: stop
at findings, do not patch QUALITY_FLAG_MAP unilaterally.

Author: probe spike at HD 2.4.b round 1.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from etl._load import read_herd_csv  # noqa: E402

ERA_A_YEARS = range(1973, 2010)


def main() -> int:
    con = duckdb.connect()
    t0 = time.perf_counter()

    print("=" * 78)
    print("probe_status_c_codeset — era-A status='c' characterization")
    print("=" * 78)

    # ------------------------------------------------------------------ #
    # Pass 1: per-year `status` value counts across era-A
    # ------------------------------------------------------------------ #
    print("\n--- Pass 1: per-year `status` value distribution (era-A) ---")
    print("  year   total       blank     'i'      'e'      'u'      'c'      other")
    per_year_summary: list[tuple] = []
    for year in ERA_A_YEARS:
        rel = read_herd_csv(year, con=con)
        row = con.execute(
            f"""
            SELECT
                COUNT(*),
                COUNT(*) FILTER (WHERE status IS NULL OR status = ''),
                COUNT(*) FILTER (WHERE status = 'i'),
                COUNT(*) FILTER (WHERE status = 'e'),
                COUNT(*) FILTER (WHERE status = 'u'),
                COUNT(*) FILTER (WHERE status = 'c'),
                COUNT(*) FILTER (WHERE status NOT IN ('', 'i', 'e', 'u', 'c')
                                  AND status IS NOT NULL)
            FROM ({rel.sql_query()})
            """
        ).fetchone()
        total, blank, i_n, e_n, u_n, c_n, other = row
        per_year_summary.append((year, total, blank, i_n, e_n, u_n, c_n, other))
        flag = ""
        if c_n > 0:
            flag = "  <-- status='c' present"
        if other > 0:
            flag += "  <-- other non-codeset present"
        print(f"  {year}  {total:>9,}  {blank:>9,}  {i_n:>5,}   {e_n:>5,}   "
              f"{u_n:>5,}   {c_n:>5,}   {other:>5,}{flag}")

    # ------------------------------------------------------------------ #
    # Pass 2: where does status='c' appear? Question / column / row text
    # ------------------------------------------------------------------ #
    print("\n--- Pass 2: status='c' breakdown by (question, column) ---")
    for (year, total, blank, i_n, e_n, u_n, c_n, other) in per_year_summary:
        if c_n == 0:
            continue
        rel = read_herd_csv(year, con=con)
        per_qc = con.execute(
            f"""
            SELECT question, "column", COUNT(*) AS n
            FROM ({rel.sql_query()})
            WHERE status = 'c'
            GROUP BY question, "column"
            ORDER BY n DESC
            """
        ).fetchall()
        print(f"\n  FY {year}: {c_n:,} rows with status='c'")
        for (q, col, n) in per_qc:
            print(f"    n={n:>6,}  question={q!r:<60s}  column={col!r}")

    # ------------------------------------------------------------------ #
    # Pass 3: status='c' at column='Total' specifically (Stage 4 scope)
    # ------------------------------------------------------------------ #
    print("\n--- Pass 3: status='c' at column='Total' (Stage 4 filter scope) ---")
    total_at_total = 0
    for (year, total, blank, i_n, e_n, u_n, c_n, other) in per_year_summary:
        if c_n == 0:
            continue
        rel = read_herd_csv(year, con=con)
        n_at_total = con.execute(
            f"""
            SELECT COUNT(*)
            FROM ({rel.sql_query()})
            WHERE status = 'c' AND "column" = 'Total'
            """
        ).fetchone()[0]
        # In-scope Stage 4 questions only (era-A field + Item 3).
        n_at_total_in_scope = con.execute(
            f"""
            SELECT COUNT(*)
            FROM ({rel.sql_query()})
            WHERE status = 'c'
              AND "column" = 'Total'
              AND question IN (
                  'Expenditures by S&E field',
                  'Current fund research equipment expenditures by field'
              )
            """
        ).fetchone()[0]
        total_at_total += n_at_total
        print(f"  FY {year}: status='c' at column='Total' n={n_at_total:,} "
              f"(of which Stage-4-in-scope-question n={n_at_total_in_scope:,})")
    print(f"\n  Era-A total status='c' at column='Total': {total_at_total:,}")

    # ------------------------------------------------------------------ #
    # Pass 4: data value distribution for status='c' rows
    # ------------------------------------------------------------------ #
    print("\n--- Pass 4: `data` value distribution on status='c' rows ---")
    for (year, total, blank, i_n, e_n, u_n, c_n, other) in per_year_summary:
        if c_n == 0:
            continue
        rel = read_herd_csv(year, con=con)
        # Data summary: how many are blank/NULL, '0', or numeric?
        summary = con.execute(
            f"""
            SELECT
                COUNT(*) FILTER (WHERE data IS NULL OR data = ''),
                COUNT(*) FILTER (WHERE data = '0'),
                COUNT(*) FILTER (WHERE TRY_CAST(data AS DOUBLE) IS NOT NULL
                                 AND TRY_CAST(data AS DOUBLE) > 0),
                COUNT(*) FILTER (WHERE data IS NOT NULL
                                 AND data != ''
                                 AND TRY_CAST(data AS DOUBLE) IS NULL)
            FROM ({rel.sql_query()})
            WHERE status = 'c'
            """
        ).fetchone()
        blank_d, zero_d, pos_d, nonnumeric_d = summary
        print(f"  FY {year}: status='c' data values — "
              f"blank/NULL={blank_d:,}, '0'={zero_d:,}, "
              f"positive_numeric={pos_d:,}, non-numeric={nonnumeric_d:,}")

    # ------------------------------------------------------------------ #
    # Pass 5: any other non-codeset status values across era-A
    # ------------------------------------------------------------------ #
    print("\n--- Pass 5: other non-codeset status values (anywhere in era-A) ---")
    any_other = False
    for (year, total, blank, i_n, e_n, u_n, c_n, other) in per_year_summary:
        if other == 0:
            continue
        any_other = True
        rel = read_herd_csv(year, con=con)
        per_status = con.execute(
            f"""
            SELECT status, COUNT(*) AS n
            FROM ({rel.sql_query()})
            WHERE status NOT IN ('', 'i', 'e', 'u', 'c')
              AND status IS NOT NULL
            GROUP BY status
            ORDER BY n DESC
            """
        ).fetchall()
        print(f"  FY {year}: {other:,} rows with non-codeset status:")
        for (st, n) in per_status:
            print(f"    status={st!r:<10s} n={n:>6,}")
    if not any_other:
        print("  None. status='c' is the only non-codeset value across era-A.")

    elapsed = time.perf_counter() - t0
    print(f"\nWall time: {elapsed:.2f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
