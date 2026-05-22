"""
etl/spikes/probe_q4_q5_attribute_structure.py — characterize Q4/Q5
row-axis + column-axis structure for HD 2.4.d Stage 8 attribute table.

Scoping doc §1(c) attribute table schema:
  institution_id, year, era, med_school_share, clinical_trials_share,
  med_school_value, clinical_trials_value, source_file, notes

User flagged: "Q5 row-axis Federal/Nonfederal/Total decomposition
handling per HD 2.4.b Track 2 finding §3" — verify empirically.

Probe scope: FY 2010, 2017, 2024.
  - Q4 raw label (canonical 'Medical school R&D expenditures'; raw
    'Medical school expenditures' per question_map.csv row 15).
  - Q5 raw label (canonical 'Clinical trial R&D expenditures'; raw
    'Clinical trials' per question_map.csv row 16).
  - For each: distinct columns, distinct row labels, per-(inst, row,
    column) row counts, sample rows.

Output prints to stdout.
"""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from etl._load import read_herd_csv  # noqa: E402
from etl.build_herd_panel import (  # noqa: E402
    ERA_B_Q4, ERA_B_Q4_RAW,
    ERA_B_Q5_CANONICAL, ERA_B_Q5_RAW,
)

YEARS = (2010, 2017, 2024)


def probe(con, year, q_label_pair):
    canonical, raw = q_label_pair
    rel = read_herd_csv(year, con=con)
    print(f"\n  FY {year} — {canonical!r} / raw {raw!r}:")
    rows = con.execute(
        f"""
        SELECT question, COUNT(*) AS n
        FROM ({rel.sql_query()})
        WHERE question IN (?, ?)
        GROUP BY question
        """,
        [canonical, raw]
    ).fetchall()
    for (q, n) in rows:
        print(f"    n={n:>5,}  question={q!r}")

    cols = con.execute(
        f"""
        SELECT "column", COUNT(*) AS n
        FROM ({rel.sql_query()})
        WHERE question IN (?, ?)
        GROUP BY "column"
        ORDER BY n DESC
        """,
        [canonical, raw]
    ).fetchall()
    print(f"    Columns:")
    for (c, n) in cols:
        print(f"      {c!r:<20s} n={n:>5,}")

    row_labels = con.execute(
        f"""
        SELECT "row", COUNT(*) AS n
        FROM ({rel.sql_query()})
        WHERE question IN (?, ?)
        GROUP BY "row"
        ORDER BY n DESC
        """,
        [canonical, raw]
    ).fetchall()
    print(f"    Row labels:")
    for (r, n) in row_labels:
        print(f"      {(r or '')!r:<35s} n={n:>5,}")

    print(f"    Sample rows (5):")
    samples = con.execute(
        f"""
        SELECT inst_id, questionnaire_no, "row", "column", data, status
        FROM ({rel.sql_query()})
        WHERE question IN (?, ?)
        LIMIT 5
        """,
        [canonical, raw]
    ).fetchall()
    for s in samples:
        (iid, qno, r, c, d, st) = s
        print(f"      inst={iid!r:<8s} qno={qno!r:<8s} "
              f"row={(r or '')[:30]!r:<32s} col={c!r:<12s} "
              f"data={d!r:<8s} status={st!r}")


def main() -> int:
    con = duckdb.connect()
    print("=" * 78)
    print("probe_q4_q5_attribute_structure — HD 2.4.d Stage 8 design")
    print("=" * 78)

    for year in YEARS:
        print(f"\n{'-' * 50}")
        print(f"FY {year}")
        print(f"{'-' * 50}")
        probe(con, year, (ERA_B_Q4, ERA_B_Q4_RAW))
        probe(con, year, (ERA_B_Q5_CANONICAL, ERA_B_Q5_RAW))

    return 0


if __name__ == "__main__":
    sys.exit(main())
