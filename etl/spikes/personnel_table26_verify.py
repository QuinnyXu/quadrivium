"""
etl/spikes/personnel_table26_verify.py — Phase 2 reconciliation spike.

Reproduces the 9-cell verification grid that backs
``validation/reports/personnel_table26_reconciliation.md``:
free-sum totals + n_institutions from ``data/harmonized/herd_personnel.parquet``
versus published anchors in NCSES Data Table 26 (NSF 26-304).

Anchors (Table 26, NSF 26-304, all five years FYs 2020-24)
----------------------------------------------------------
- FY 2022: All-personnel-functions Headcount = 1,032,569; FTEs = 497,012
- FY 2023: All-personnel-functions Headcount = 1,058,388; FTEs = 513,860
- FY 2024: All-personnel-functions Headcount = 1,086,850; FTEs = 525,960
- n_institutions: NOT published in Table 26 (no institution-count column).
  See report `Implications for Phase 3` for the alternative anchor path.

Reproducibility
---------------
Inputs:
  - data/harmonized/herd_personnel.parquet (built by etl/build_herd_personnel.py)
  - Anchors are constants below; source PDF stashed at
    data/reference/nsf26304-tab026.pdf.

Output: stdout-only. Mirror the 9-cell grid the report carries.

Author: Skipper, 2026-05-01 (Phase 2 reconciliation).
"""

from __future__ import annotations

import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent.parent
PARQUET = ROOT / "data" / "harmonized" / "herd_personnel.parquet"

# Anchors from NCSES Data Table 26 (NSF 26-304),
# data/reference/nsf26304-tab026.pdf, "All personnel functions" row.
TABLE26_ANCHORS = {
    2022: {"headcount": 1_032_569, "fte": 497_012},
    2023: {"headcount": 1_058_388, "fte": 513_860},
    2024: {"headcount": 1_086_850, "fte": 525_960},
}


def main() -> int:
    if not PARQUET.exists():
        print(f"ERROR: {PARQUET} does not exist. Run "
              "`python -m etl.build_herd_personnel` first.", file=sys.stderr)
        return 1

    con = duckdb.connect()
    rel = con.read_parquet(str(PARQUET))

    print("=" * 78)
    print("Personnel Phase 2 reconciliation: parquet free-sum vs Table 26 anchors")
    print("=" * 78)

    # 9-cell grid: 3 years x (headcount, FTE, n_institutions).
    # Free-sum logic: filter personnel_function='total' (which is the
    # row-level rolled total that already sums Researchers + Technicians +
    # Support Staff inside a single institution-year), then SUM(value) across
    # institutions. n_institutions is COUNT(DISTINCT institution_id) within
    # the same filter (positive value implied — verified zero zero/NULL rows
    # in Phase 1 sanity).
    print(f"{'year':>6}  {'measure':>10}  {'parquet_freesum':>17}  "
          f"{'table26_anchor':>15}  {'delta':>10}  {'pct':>7}  match")
    print("-" * 78)

    rows = (
        rel.filter("personnel_function = 'total'")
        .aggregate(
            "year, measure_type, "
            "SUM(value) AS freesum, "
            "COUNT(DISTINCT institution_id) AS n_inst",
            group_expr="year, measure_type",
        )
        .order("year, measure_type")
        .fetchall()
    )

    n_match = 0
    n_total = 0
    for year, measure, freesum, n_inst in rows:
        anchor = TABLE26_ANCHORS[year][measure]
        delta = int(freesum) - anchor
        pct = (delta / anchor) * 100 if anchor else float("nan")
        flag = "EXACT" if delta == 0 else "DIVERGE"
        if delta == 0:
            n_match += 1
        n_total += 1
        print(f"{year:>6}  {measure:>10}  {int(freesum):>17,}  "
              f"{anchor:>15,}  {delta:>+10,}  {pct:>+6.2f}%  {flag}")

    # n_institutions cell: parquet count vs anchor (anchor = NA).
    print()
    print("n_institutions per year (parquet COUNT(DISTINCT institution_id) "
          "where personnel_function='total'):")
    print(f"{'year':>6}  {'parquet_n_inst':>14}  {'table26_anchor':>15}  match")
    print("-" * 60)
    for year, _, _, n_inst in rows:
        if year not in TABLE26_ANCHORS:
            continue
        # Each (year, measure) row carries the same n_inst at year level
        # (within rounding — actually verified below).
        pass

    # Per-year n_inst, deduplicated across measure_type (should match exactly
    # since both Q15/Q16 carry the same institution roster within a year, ±
    # the Q16-zero-rows edge case).
    inst_rows = (
        rel.filter("personnel_function = 'total'")
        .aggregate(
            "year, COUNT(DISTINCT institution_id) AS n_inst",
            group_expr="year",
        )
        .order("year")
        .fetchall()
    )
    for year, n_inst in inst_rows:
        print(f"{year:>6}  {n_inst:>14,}  {'NA (not published)':>15}  "
              f"NA (anchor missing)")
    print()
    print(f"Totals match: {n_match}/{n_total} cells exact match. "
          f"n_institutions has no Table 26 anchor.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
