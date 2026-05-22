"""Diagnostic for HD 2.4.a smoke-test surface: FY 2024 questionnaire_no
filter returned zero in-scope rows. Establish what the questionnaire_no
values in the FY 2024 unified-schema relation actually look like, and
under what value the Q9/Q11/Q14/Q4/Q5 question labels appear.

Throwaway. One-shot. Stops at findings.
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

    print("--- distinct questionnaire_no in FY 2024 ---")
    res = con.sql(
        f"SELECT questionnaire_no, COUNT(*) AS n "
        f"FROM ({rel.sql_query()}) "
        f"GROUP BY questionnaire_no ORDER BY n DESC LIMIT 30"
    ).fetchall()
    for r in res:
        print(f"  qno={r[0]!r:>20s}  n={r[1]:,}")

    print()
    print("--- DESCRIBE schema (all columns) ---")
    schema = con.sql(f"DESCRIBE ({rel.sql_query()})").fetchall()
    for s in schema:
        print(f"  {s[0]!r:30s} {s[1]!r}")

    print()
    print("--- Q9/Q11/Q14/Q4/Q5 question labels: presence + qno value ---")
    labels = (
        "Federal expenditures by field and agency",
        "Nonfederal expenditures by field and source",
        "Capitalized R&D equipment expenditures by field",
        "Medical school R&D expenditures",
        "Clinical trial R&D expenditures",
        "Clinical trials",
    )
    for lab in labels:
        sql = (
            f"SELECT questionnaire_no, COUNT(*) AS n "
            f"FROM ({rel.sql_query()}) "
            f"WHERE question = '{lab.replace(chr(39), chr(39)+chr(39))}' "
            f"GROUP BY questionnaire_no ORDER BY n DESC"
        )
        res = con.sql(sql).fetchall()
        if res:
            for r in res:
                print(
                    f"  question={lab!r:55s} qno={r[0]!r:>15s} n={r[1]:,}"
                )
        else:
            print(f"  question={lab!r:55s} NOT FOUND")

    print()
    print("--- top 30 distinct (questionnaire_no, question) pairs by row count ---")
    res = con.sql(
        f"SELECT questionnaire_no, question, COUNT(*) AS n "
        f"FROM ({rel.sql_query()}) "
        f"GROUP BY questionnaire_no, question "
        f"ORDER BY n DESC LIMIT 30"
    ).fetchall()
    for r in res:
        print(f"  qno={r[0]!r:>15s}  q={r[1]!r:55s}  n={r[2]:,}")


if __name__ == "__main__":
    main()
