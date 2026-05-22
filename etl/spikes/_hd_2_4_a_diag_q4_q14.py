"""Diagnostic 2 for HD 2.4.a smoke-test surface.

Q14 (capitalized R&D equipment) and Q4 (medical school) — confirm
their actual question labels and questionnaire_no values in FY 2024.
The Stage 2 filter spec assumes raw qno '4', '5', '9', '11', '14'
literals; FY 2024 evidently uses zero-padded compound forms.
Surface the actual question-label / qno relationship for Q14 and Q4
specifically.
"""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from etl._load import read_herd_csv


def main() -> None:
    con = duckdb.connect()
    rel = read_herd_csv(2024, con=con)

    # Search question labels containing "equipment", "medical", "clinical".
    for needle in ("equipment", "medical", "clinical", "school"):
        print(f"--- question labels containing {needle!r} ---")
        sql = (
            f"SELECT DISTINCT questionnaire_no, question, COUNT(*) AS n "
            f"FROM ({rel.sql_query()}) "
            f"WHERE LOWER(question) LIKE '%{needle}%' "
            f"GROUP BY questionnaire_no, question ORDER BY n DESC LIMIT 25"
        )
        res = con.sql(sql).fetchall()
        if not res:
            print("  (no matches)")
        for r in res:
            print(f"  qno={r[0]!r:>10s}  q={r[1]!r:60s}  n={r[2]:,}")
        print()

    # Show qno values that start with '14' or are exactly '14'/'4'.
    print("--- qno LIKE '14%' or exactly '14' or '4' or '04' ---")
    sql = (
        f"SELECT questionnaire_no, COUNT(DISTINCT question) AS distinct_q, "
        f"  ANY_VALUE(question) AS sample_q, COUNT(*) AS n "
        f"FROM ({rel.sql_query()}) "
        f"WHERE questionnaire_no LIKE '14%' OR questionnaire_no IN ('14','4','04') "
        f"GROUP BY questionnaire_no ORDER BY n DESC LIMIT 30"
    )
    res = con.sql(sql).fetchall()
    if not res:
        print("  (no matches)")
    for r in res:
        print(
            f"  qno={r[0]!r:>10s}  distinct_q={r[1]}  "
            f"sample_q={r[2]!r}  n={r[3]:,}"
        )
    print()

    # And qno LIKE '04%' or '4%'
    print("--- qno LIKE '04%' or '4%' or '4' ---")
    sql = (
        f"SELECT questionnaire_no, COUNT(DISTINCT question) AS distinct_q, "
        f"  ANY_VALUE(question) AS sample_q, COUNT(*) AS n "
        f"FROM ({rel.sql_query()}) "
        f"WHERE questionnaire_no LIKE '04%' OR questionnaire_no LIKE '4%' "
        f"OR questionnaire_no = '4' "
        f"GROUP BY questionnaire_no ORDER BY n DESC LIMIT 30"
    )
    res = con.sql(sql).fetchall()
    if not res:
        print("  (no matches)")
    for r in res:
        print(
            f"  qno={r[0]!r:>10s}  distinct_q={r[1]}  "
            f"sample_q={r[2]!r}  n={r[3]:,}"
        )


if __name__ == "__main__":
    main()
