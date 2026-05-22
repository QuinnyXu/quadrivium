"""HD 2.4.g entry sub-action — derive top-10-by-FY-2008-R&D cohort.

Throwaway probe (NOT a build-promoted script). Reads the harmonized panel,
selects era='A' FY 2008 institution-total R&D rows (discipline_fine='All',
source_class='all_source', expenditure_type='r&d'), takes the 10 largest by
value, prints the cohort list to stdout for citation into the HD 2.4.g
YAML sidecars and PANEL_SKIPPER §8 entry.

Cross-references: docs/methods_notes/herd_panel_etl_scoping.md §2(b) Branch A
cohort scope ("top-10-by-FY-2008-R&D"); the residual-test cohort established
at HD 2.1.b for validation/reports/era_reconciliation_2008_2011.md.

Run: `uv run python etl/spikes/_probe_top10_cohort.py`
Output: stdout only — no files written.
"""
from __future__ import annotations

from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
PANEL = ROOT / "data" / "harmonized" / "herd_panel.parquet"


def main() -> None:
    con = duckdb.connect()
    rows = con.execute(
        f"""
        SELECT institution_id, inst_name_long, fice, value
        FROM read_parquet('{PANEL.as_posix()}')
        WHERE era = 'A' AND year = 2008
          AND expenditure_type = 'r&d'
          AND source_class = 'all_source'
          AND discipline_fine = 'All'
        ORDER BY value DESC
        LIMIT 10
        """
    ).fetchall()

    print("Top-10 institutions by FY 2008 R&D (institution-total, all_source):")
    print(f"  {'rank':>4}  {'inst_id':<10}  {'fice':<8}  {'value_kUSD':>14}  inst_name")
    for i, (iid, name, fice, val) in enumerate(rows, start=1):
        print(f"  {i:>4}  {iid:<10}  {fice or '':<8}  {val:>14,.0f}  {name}")

    # Cohort YAML sidecar list helper
    print()
    print("YAML sidecar `query_parameters.institutions:` list (era-A inst_id):")
    for iid, name, fice, val in rows:
        print(f"  - {iid}  # {name}")


if __name__ == "__main__":
    main()
