"""
Throwaway probe: Q15/Q16 row/column structure across 2020-2024.

Phase 1 of personnel-sibling build. Asks the data:
  1. Which years actually carry Q15/Q16 microdata?
  2. What are the distinct row labels (personnel categories)?
  3. What are the distinct column labels (sex / citizenship / education /
     other axes)?
  4. Are there year-to-year shifts in the row/column taxonomy?

Author: Skipper, 2026-05-01.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from etl._load import read_herd_csv  # noqa: E402


def main() -> int:
    # Sanity checks before per-year detail:
    # 1. Confirm no Q15/Q16 microdata in pre-2022 era-B years (HD 1.2 finding).
    print("=== Pre-2022 era-B Q15/Q16 sanity check ===")
    for year in (2010, 2012, 2015, 2017, 2019, 2020, 2021):
        rel = read_herd_csv(year)
        n = (
            rel.filter("questionnaire_no IN ('15', '16')")
            .aggregate("COUNT(*) AS n")
            .fetchone()[0]
        )
        print(f"  {year}: {n} Q15/Q16 rows")
    print()

    # 2. Confirm 2024's full questionnaire_no inventory has no orphan personnel modules.
    print("=== 2024 full questionnaire_no inventory ===")
    rel_2024 = read_herd_csv(2024)
    qnos_2024 = rel_2024.project("questionnaire_no").distinct().fetchall()
    qnos_sorted = sorted({q for (q,) in qnos_2024 if q is not None})
    print(f"  {len(qnos_sorted)} distinct: {qnos_sorted}")
    print()

    # 3. Surface every question label that mentions personnel/headcount/FTE/postdoc
    #    in 2024, regardless of questionnaire_no.
    print("=== 2024 personnel-related question labels (any questionnaire_no) ===")
    rel_p = rel_2024.filter(
        "LOWER(question) LIKE '%personnel%' OR "
        "LOWER(question) LIKE '%fte%' OR "
        "LOWER(question) LIKE '%headcount%' OR "
        "LOWER(question) LIKE '%postdoc%'"
    )
    rows = rel_p.project("questionnaire_no, question").distinct().fetchall()
    for qno, q in sorted(rows):
        print(f"  qno={qno!r}  question={q!r}")
    print()

    print("=== Per-year Q15/Q16 microdata structure ===")
    for year in (2020, 2021, 2022, 2023, 2024):
        rel = read_herd_csv(year)
        # Filter to Q15 / Q16
        sub = rel.filter("questionnaire_no IN ('15', '16')")
        n = sub.aggregate("COUNT(*) AS n").fetchone()[0]
        print(f"=== {year}: {n} total Q15/Q16 microdata rows ===")
        if n == 0:
            print(f"  (no Q15/Q16 rows present in {year})")
            print()
            continue

        # Distinct (qno, question, row, column) tuples
        combos = sub.project(
            'questionnaire_no, question, "row", "column"'
        ).distinct().fetchall()

        # Bucket by qno
        by_qno: dict[str, list[tuple]] = {}
        for qno, q, r, c in combos:
            by_qno.setdefault(qno, []).append((q, r, c))

        for qno in sorted(by_qno):
            cs = by_qno[qno]
            print(f"  Q{qno}: {len(cs)} distinct (question, row, column) combos")
            qs = sorted({q for q, _, _ in cs if q is not None})
            print(f"    questions ({len(qs)}): {qs}")

            rs = sorted({r for _, r, _ in cs if r is not None})
            print(f"    rows ({len(rs)} distinct):")
            for r in rs[:50]:
                print(f"      - {r!r}")
            if len(rs) > 50:
                print(f"      ... ({len(rs) - 50} more)")

            cols = sorted({c for _, _, c in cs if c is not None})
            print(f"    columns ({len(cols)} distinct):")
            for c in cols[:50]:
                print(f"      - {c!r}")
            if len(cols) > 50:
                print(f"      ... ({len(cols) - 50} more)")

        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
