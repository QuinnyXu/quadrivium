"""
etl/spikes/probe_era_a_item_3_label.py — empirical verification of the
era-A Item 3 (Current fund research equipment expenditures by field)
question label and column structure.

Surfaced 2026-05-10 by HD 2.4.b Stage 4 smoke test, when the panel build
returned zero r&d_equipment rows despite Item 3 being expected to ship
1981-2009. The Stage 2 filter uses the FY24 Guide canonical label
'Current fund research equipment expenditures by field' (per scoping
doc §6.1 / question_map.csv row 8). If the raw HERD CSVs use a
different label, Stage 2 silently drops Item 3 rows.

Probe scope: scan FY 1981, 1995, 2009 (representative across the
1981-2009 Item 3 coverage) for any question label containing
'equipment' to surface any raw-vs-canonical drift.

Output prints to stdout. No artifact written.

Author: probe spike at HD 2.4.b round 1.
"""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from etl._load import read_herd_csv  # noqa: E402

PROBE_YEARS = (1981, 1995, 2009)


def main() -> int:
    con = duckdb.connect()

    print("=" * 78)
    print("probe_era_a_item_3_label — Item 3 raw vs canonical label scan")
    print("=" * 78)

    for year in PROBE_YEARS:
        rel = read_herd_csv(year, con=con)
        print(f"\n--- FY {year} ---")

        # Pass 1: any question label containing 'equipment'.
        print("\n  Question labels containing 'equipment':")
        rows = con.execute(
            f"""
            SELECT question, COUNT(*) AS n
            FROM ({rel.sql_query()})
            WHERE question ILIKE '%equipment%'
            GROUP BY question
            ORDER BY n DESC
            """
        ).fetchall()
        if not rows:
            print("    (none)")
        for (q, n) in rows:
            print(f"    n={n:>6,}  question={q!r}")

        # Pass 2: for any equipment-containing question, show distinct columns.
        print("\n  Distinct columns per equipment-containing question:")
        cols = con.execute(
            f"""
            SELECT question, "column", COUNT(*) AS n
            FROM ({rel.sql_query()})
            WHERE question ILIKE '%equipment%'
            GROUP BY question, "column"
            ORDER BY question, "column"
            """
        ).fetchall()
        if not cols:
            print("    (none)")
        for (q, c, n) in cols:
            print(f"    q={q[:50]!r:<52s} col={c!r:<15s} n={n:>6,}")

        # Pass 3: 5 example rows for each equipment-containing question.
        print("\n  Example rows (5 per equipment question, column='Total' if it exists):")
        examples = con.execute(
            f"""
            WITH ranked AS (
                SELECT
                    question,
                    questionnaire_no,
                    "row",
                    "column",
                    data,
                    status,
                    ROW_NUMBER() OVER (
                        PARTITION BY question
                        ORDER BY ("column" = 'Total') DESC, "column", "row"
                    ) AS rn
                FROM ({rel.sql_query()})
                WHERE question ILIKE '%equipment%'
            )
            SELECT question, questionnaire_no, "row", "column", data, status
            FROM ranked WHERE rn <= 5
            ORDER BY question, rn
            """
        ).fetchall()
        for (q, qno, r, c, d, s) in examples:
            print(f"    q={q[:40]!r:<42s} qno={qno!r:<6s} "
                  f"row={(r or '')[:35]!r:<37s} col={c!r:<15s} "
                  f"data={d!r:<10s} status={s!r}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
