"""
etl/spikes/probe_q14_short_form_q2_structure.py — combined probe for
HD 2.4.b Surface 2 (Q14 column structure) and Surface 3 (Short Form
Q2 raw structure).

Surface 2 — Q14 column structure verification.
HD 2.4.a sample showed Q14 raw rows with col='Federal' axis (qno='14A'
row='Computer and information sciences, all' col='Federal'). Question
to resolve: does column='Total' exist as a rolled column for Q14, or
does Q14 require sum across columns to produce all-source value?
question_map.csv row 25 says column_used=NULL for Q14 (era-B-subset-of
-Q9+Q11, contributes_to_all_source_total=false), which is ambiguous.

Surface 3 — Short Form Q2 raw structure verification.
Per scoping doc §9.2: exact raw-CSV structure of Short Form Q2 not
verified at scoping time. Probe identifies:
  - The raw label HERD CSVs use for Short Form Q2 (canonical per
    question_map.csv row 34 is "Short form: R&D expenditures by
    major R&D field"; raw may differ).
  - Column structure (does column='Total' exist as a rolled column?).
  - Row labels (are these field-level labels parallel to standard-form
    Q9/Q11, or coarser?).

Probe scope:
  - Q14: scan FY 2010, 2017, 2024 (representative across era-B).
    Identify all Q14 raw labels (canonical + raw drift); enumerate
    distinct columns and their relative volumes; spot-check whether
    column='Total' carries plausible all-source values.
  - Short Form Q2: scan FY 2012, 2017, 2024 (Short Form Q2 added
    FY 2012 per question_map.csv row 34).

Output prints to stdout. Spike discipline: stop at findings, do not
patch projection logic until Skipper applies the verdict.

Author: HD 2.4.b round 1 Surface 2 + Surface 3 combined probe.
"""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from etl._load import read_herd_csv  # noqa: E402
from etl.build_herd_panel import (  # noqa: E402
    ERA_B_Q14,
    ERA_B_Q14_RAW,
)

Q14_PROBE_YEARS = (2010, 2017, 2024)
SHORT_FORM_Q2_PROBE_YEARS = (2012, 2017, 2024)


def probe_q14(con: duckdb.DuckDBPyConnection) -> None:
    print("=" * 78)
    print("Surface 2 — Q14 column structure verification")
    print("=" * 78)
    print(f"\nLooking for Q14 rows under canonical {ERA_B_Q14!r}")
    print(f"and raw {ERA_B_Q14_RAW!r}.")

    for year in Q14_PROBE_YEARS:
        rel = read_herd_csv(year, con=con)
        print(f"\n--- FY {year} ---")

        # Pass 1: distinct question labels matching canonical or raw,
        # plus any other label containing 'capitalized' or 'equipment'
        # that we might have missed.
        print("\n  Question labels matching Q14 canonical/raw or containing"
              " 'capitalized' / 'equipment':")
        rows = con.execute(
            f"""
            SELECT question, COUNT(*) AS n
            FROM ({rel.sql_query()})
            WHERE question IN ('{ERA_B_Q14}', '{ERA_B_Q14_RAW}')
               OR question ILIKE '%capitalized%'
               OR question ILIKE '%equipment%'
            GROUP BY question
            ORDER BY n DESC
            """
        ).fetchall()
        for (q, n) in rows:
            print(f"    n={n:>6,}  question={q!r}")

        # Pass 2: distinct columns observed for the Q14 question.
        print("\n  Distinct columns under Q14 raw label, with row counts:")
        cols = con.execute(
            f"""
            SELECT "column", COUNT(*) AS n
            FROM ({rel.sql_query()})
            WHERE question IN ('{ERA_B_Q14}', '{ERA_B_Q14_RAW}')
            GROUP BY "column"
            ORDER BY n DESC
            """
        ).fetchall()
        if not cols:
            print("    (no Q14 rows found under canonical or raw label)")
        for (c, n) in cols:
            print(f"    column={c!r:<25s} n={n:>6,}")

        # Pass 3: example rows at column='Total' (if any), to spot-check
        # whether values look plausible all-source.
        print("\n  Example rows at column='Total' for Q14 (top 5):")
        examples = con.execute(
            f"""
            SELECT inst_id, "row", data, status, questionnaire_no
            FROM ({rel.sql_query()})
            WHERE question IN ('{ERA_B_Q14}', '{ERA_B_Q14_RAW}')
              AND "column" = 'Total'
            ORDER BY inst_id, "row"
            LIMIT 5
            """
        ).fetchall()
        if not examples:
            print("    (no rows at column='Total' — need to sum across columns)")
        for (iid, r, d, s, qno) in examples:
            print(f"    inst={iid!r:<8s} row={(r or '')[:35]!r:<37s} "
                  f"qno={qno!r:<6s} data={d!r:<10s} status={s!r}")

        # Pass 4: spot-check whether sum-across-cols on a single inst-disc
        # produces something parallel to a Total. Use the largest-data
        # institution as a probe.
        print("\n  Spot-check: per-(inst_id, row) sum across columns "
              "(top 3 by row-count):")
        spot = con.execute(
            f"""
            SELECT inst_id, "row",
                   COUNT(*) AS n_cells,
                   STRING_AGG("column", ',' ORDER BY "column") AS cols_seen,
                   SUM(value) AS sum_values
            FROM ({rel.sql_query()})
            WHERE question IN ('{ERA_B_Q14}', '{ERA_B_Q14_RAW}')
              AND value IS NOT NULL
              AND "row" LIKE '%, all'
            GROUP BY inst_id, "row"
            ORDER BY sum_values DESC NULLS LAST
            LIMIT 3
            """
        ).fetchall()
        for (iid, r, n, cols_seen, sumv) in spot:
            print(f"    inst={iid!r:<8s} row={(r or '')[:35]!r:<37s} "
                  f"n_cells={n} cols_seen={cols_seen[:60]!r} sum={sumv}")


def probe_short_form_q2(con: duckdb.DuckDBPyConnection) -> None:
    print("\n" + "=" * 78)
    print("Surface 3 — Short Form Q2 raw structure verification")
    print("=" * 78)

    for year in SHORT_FORM_Q2_PROBE_YEARS:
        rel = read_herd_csv(year, con=con)
        print(f"\n--- FY {year} ---")

        # Pass 1: any question matching short-form patterns.
        # Try several plausible patterns since the canonical form is
        # 'Short form: R&D expenditures by major R&D field' but raw may
        # differ.
        print("\n  Question labels matching short-form patterns:")
        rows = con.execute(
            f"""
            SELECT question, COUNT(*) AS n
            FROM ({rel.sql_query()})
            WHERE question ILIKE '%short form%'
               OR question ILIKE '%short-form%'
               OR question ILIKE '%major R&D field%'
               OR question ILIKE '%major field%'
            GROUP BY question
            ORDER BY n DESC
            """
        ).fetchall()
        if not rows:
            print("    (none)")
        for (q, n) in rows:
            print(f"    n={n:>6,}  question={q!r}")

        # Pass 2: questionnaire_no patterns. Standard-form Q2 has qno
        # like '02', '02A'; short-form may use '02' on different file
        # population, or a distinct prefix. Also 'SF02', 'S02', etc.
        print("\n  Distinct questionnaire_no values in raw:")
        qnos = con.execute(
            f"""
            SELECT questionnaire_no, COUNT(*) AS n
            FROM ({rel.sql_query()})
            GROUP BY questionnaire_no
            ORDER BY n DESC
            LIMIT 30
            """
        ).fetchall()
        for (qn, n) in qnos:
            print(f"    qno={qn!r:<10s} n={n:>6,}")

        # Pass 3: are there institutions in the raw file that *only*
        # appear under a short-form-distinct question? Short-form
        # respondents are below the $1M threshold; per scoping doc §9.1,
        # Short Form Q2 ships at form_type='short'. If short-form
        # questions are interleaved in the same file, the population
        # split is by question, not by file. If short-form is in a
        # separate file, this probe finds nothing.
        # Identify candidate short-form questions by characteristic
        # row-label fingerprint or low row count.
        # For now we just report — the disposition is what the data shows.

        # Pass 4: short-form Q2 candidate — rows where question matches
        # short-form pattern, characterize column/row structure.
        print("\n  If short-form Q2 candidates exist, distinct columns:")
        cols = con.execute(
            f"""
            SELECT question, "column", COUNT(*) AS n
            FROM ({rel.sql_query()})
            WHERE question ILIKE '%short form%'
               OR question ILIKE '%short-form%'
               OR question ILIKE '%major R&D field%'
               OR question ILIKE '%major field%'
            GROUP BY question, "column"
            ORDER BY question, "column"
            """
        ).fetchall()
        if not cols:
            print("    (no short-form candidates found in raw)")
        for (q, c, n) in cols:
            print(f"    q={q[:40]!r:<42s} col={c!r:<20s} n={n:>6,}")

        # Pass 5: sample rows from short-form Q2 candidates.
        print("\n  Sample short-form rows (top 5):")
        samples = con.execute(
            f"""
            SELECT question, questionnaire_no, "row", "column", data, status
            FROM ({rel.sql_query()})
            WHERE question ILIKE '%short form%'
               OR question ILIKE '%short-form%'
               OR question ILIKE '%major R&D field%'
               OR question ILIKE '%major field%'
            LIMIT 5
            """
        ).fetchall()
        if not samples:
            print("    (none)")
        for (q, qno, r, c, d, s) in samples:
            print(f"    q={q[:40]!r:<42s} qno={qno!r:<6s} "
                  f"row={(r or '')[:30]!r:<32s} col={c!r:<15s} "
                  f"data={d!r:<10s} status={s!r}")


def main() -> int:
    con = duckdb.connect()
    probe_q14(con)
    probe_short_form_q2(con)
    return 0


if __name__ == "__main__":
    sys.exit(main())
