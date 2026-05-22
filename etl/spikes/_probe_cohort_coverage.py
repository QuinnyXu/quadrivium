"""HD 2.4.g entry sub-action — confirm HD 2.1.b cohort has FY 2024 coverage.

Throwaway probe (NOT a build-promoted script). Verifies the HD 2.1.b residual
report's substituted top-10 cohort (10 institutions, preserves cohort
continuity per docs/methods_notes/herd_panel_etl_scoping.md §2(b)) has
era-B FY 2024 rows in the harmonized panel for all 10 institutions.

If any institution is missing FY 2024 coverage, the §2(b) grid contracts
to the institution count actually present.

Run: `uv run python etl/spikes/_probe_cohort_coverage.py`
Output: stdout only — no files written.
"""
from __future__ import annotations

from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
PANEL = ROOT / "data" / "harmonized" / "herd_panel.parquet"

# HD 2.1.b cohort (per validation/reports/era_reconciliation_2008_2011.md §Sample)
COHORT = [
    ("029977", "Johns Hopkins University"),
    ("001319", "University of California, San Francisco"),
    ("003895", "University of Wisconsin Madison"),
    ("001315", "University of California, Los Angeles"),
    ("001317", "University of California, San Diego"),
    ("002920", "Duke University"),
    ("003378", "University of Pennsylvania"),
    ("008802", "Ohio State University all campuses"),
    ("001305", "Stanford University"),
    ("002178", "Massachusetts Institute of Technology"),
]


def main() -> None:
    con = duckdb.connect()
    ids = ", ".join(f"'{i}'" for i, _ in COHORT)
    rows = con.execute(
        f"""
        SELECT institution_id, COUNT(*) row_count
        FROM read_parquet('{PANEL.as_posix()}')
        WHERE era = 'B' AND year = 2024
          AND institution_id IN ({ids})
        GROUP BY institution_id
        ORDER BY institution_id
        """
    ).fetchall()
    found = dict(rows)
    print(f"FY 2024 era-B row coverage for the HD 2.1.b cohort:")
    for iid, name in COHORT:
        cnt = found.get(iid, 0)
        marker = "OK" if cnt > 0 else "MISSING"
        print(f"  [{marker:>7}] {iid}  rows={cnt:>5}  {name}")


if __name__ == "__main__":
    main()
