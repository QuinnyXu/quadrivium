"""
etl/build_fedsupport_obligations.py — build the Federal S&E Support
obligations panel (HD 3.2 MVP, parse output / artifact #4).

Reads the four staged Table 12 CSVs (FY2020-FY2023, via
``etl/_load_fedsupport.read_fedsupport_table12``), unions them, and writes
the long-format harmonized parquet:

    data/harmonized/fedsupport_obligations.parquet

Columns:
    year, state, institution_name_raw, ipeds_unitid, activity_type,
    value_kusd, source_table, source_file, quality_flag, notes

``ipeds_unitid`` is NULL here — it is the spine's join target, populated by
``crosswalks/_shared/institution_identity.csv`` downstream, not in this
build. The build prints a per-year reconciliation (institution-row sum vs
state-subtotal sum vs published grand total) for the parse-reconciliation
receipt.

Reproducibility (§3): the loader reads the staged CSV via ``read_csv_auto``
only — no runtime ``excel`` extension, no network fetch. ``ORDER BY ALL``
before the parquet COPY makes the output a deterministic function of the
input CSVs + this code (mirrors ``etl/build_herd_panel.py`` HD 2.4.h).

Run:
    uv run python etl/build_fedsupport_obligations.py

Author: Skipper, 2026-05-29 (HD 3.2 MVP).
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from etl._load_fedsupport import (  # noqa: E402
    YEAR_REPORT,
    ALL_OBLIGATIONS_CANONICAL,
    parse_table12,
    read_fedsupport_table12,
    _read_raw_rows,
    csv_path_for,
)

OUT_PATH = ROOT / "data" / "harmonized" / "fedsupport_obligations.parquet"

# Published higher-ed-only grand-total anchors (kUSD). FY2020/2021/2023 from
# HD 3.1 §2 + §9. FY2022 derived at acquisition from the staged table
# ('All states and outlying areas' row) and cross-checked to the InfoBrief
# NSF 24-325 "+3% in FY2022" narrative ($44.6B vs FY2021 $43.2B = +3.3%).
GRAND_TOTAL_ANCHOR = {
    2020: 39_122_152,
    2021: 43_222_829,
    2022: 44_628_417,  # derived (no §9 anchor); InfoBrief-narrative cross-checked
    2023: 48_961_658,
}


def reconcile_year(con: duckdb.DuckDBPyConnection, year: int) -> dict:
    """Parse one year and compute the three independent dollar totals for the
    reconciliation receipt: published grand total, sum of state subtotals,
    sum of institution rows (on the 'All federal obligations' column)."""
    csv = csv_path_for(year)
    _, rows = _read_raw_rows(con, csv)
    parsed = parse_table12(rows)
    vi = parsed["val_idx"]
    inst_sum = sum(
        v[vi] for _, _, v in parsed["institutions"] if v.get(vi) is not None
    )
    sub_sum = sum(
        v[vi] for _, v in parsed["state_subtotals"] if v.get(vi) is not None
    )
    return {
        "year": year,
        "report": YEAR_REPORT[year],
        "n_inst": len(parsed["institutions"]),
        "n_states": parsed["n_state_headers"],
        "grand_total_parsed": parsed["grand_total"],
        "anchor": GRAND_TOTAL_ANCHOR[year],
        "inst_sum": inst_sum,
        "state_subtotal_sum": sub_sum,
    }


def main() -> int:
    con = duckdb.connect()
    print("=" * 72)
    print("HD 3.2 — build fedsupport_obligations.parquet (FY2020-FY2023)")
    print("=" * 72)

    # --- per-year reconciliation (parse receipt input) ---
    print("\n--- PARSE RECONCILIATION (kUSD) ---")
    print(f"{'FY':>5} {'report':>9} {'n_inst':>7} {'n_st':>5} "
          f"{'grand_parsed':>14} {'anchor':>12} {'inst_sum':>14} "
          f"{'state_sub_sum':>14}")
    recons = []
    for year in sorted(YEAR_REPORT):
        r = reconcile_year(con, year)
        recons.append(r)
        print(f"{r['year']:>5} {r['report']:>9} {r['n_inst']:>7} "
              f"{r['n_states']:>5} {r['grand_total_parsed']:>14,.1f} "
              f"{r['anchor']:>12,} {r['inst_sum']:>14,.1f} "
              f"{r['state_subtotal_sum']:>14,.1f}")

    # --- reconciliation verdict ---
    # PASS criterion (the MVP's proving deliverable, §9): the parsed grand
    # total equals the published higher-ed anchor EXACTLY. The institution-row
    # sum running slightly OVER the grand total is a CHARACTERIZED residual,
    # not a parse failure — it is system-office double-attribution (the system
    # office row sums alongside its campuses; spike §1) plus NCSES per-state
    # rounding (FY2023 is published to whole kUSD, so summing rounded rows
    # accumulates ±1/state). Reported, not corrected: the obligation dollars
    # are real and the system-office rows are legitimate institutions.
    print("\n--- RECONCILIATION VERDICT ---")
    print("  PASS criterion: parsed grand_total == published anchor (exact).")
    print("  Characterized residual: institution-sum over grand_total "
          "(system-office double-attrib + NCSES rounding).")
    all_ok = True
    for r in recons:
        gt = r["grand_total_parsed"]
        anchor = r["anchor"]
        sub = r["state_subtotal_sum"]
        gt_ok = abs(gt - anchor) <= 0.5
        inst_over = r["inst_sum"] - gt
        sub_under = sub - gt
        all_ok = all_ok and gt_ok
        print(f"  FY{r['year']}: grand_total={gt:,.1f} vs anchor={anchor:,} "
              f"-> {'OK (exact)' if gt_ok else 'MISMATCH'}")
        print(f"          inst_sum over grand_total: {inst_over:+,.1f} kUSD "
              f"({inst_over / gt * 100:+.4f}%)  "
              f"state_subtotal_sum vs grand_total: {sub_under:+,.1f} kUSD "
              f"({sub_under / gt * 100:+.4f}%)")

    # --- union all years into the long relation + write parquet ---
    print("\n--- BUILD LONG RELATION + WRITE PARQUET ---")
    t0 = time.perf_counter()
    union_sql_parts = []
    for year in sorted(YEAR_REPORT):
        rel = read_fedsupport_table12(year, con)
        # materialize each year into a named temp table (the loader uses a
        # shared _fs_long temp table name, so capture each before the next).
        con.execute(
            f"CREATE OR REPLACE TEMP TABLE _fs_year_{year} AS "
            f"SELECT * FROM ({rel.sql_query()})"
        )
        union_sql_parts.append(f"SELECT * FROM _fs_year_{year}")
    union_sql = "\nUNION ALL\n".join(union_sql_parts)
    con.execute(f"CREATE OR REPLACE TEMP TABLE _fs_all AS {union_sql}")

    n_rows = con.execute("SELECT COUNT(*) FROM _fs_all").fetchone()[0]
    n_inst_year = con.execute(
        "SELECT COUNT(*) FROM (SELECT DISTINCT year, institution_name_raw "
        "FROM _fs_all)"
    ).fetchone()[0]
    n_all_obl = con.execute(
        f"SELECT COUNT(*) FROM _fs_all WHERE activity_type = "
        f"'{ALL_OBLIGATIONS_CANONICAL}'"
    ).fetchone()[0]
    print(f"  total long rows: {n_rows:,}")
    print(f"  distinct (year, institution) pairs: {n_inst_year:,}")
    print(f"  rows on canonical 'all_obligations' column: {n_all_obl:,}")

    # activity_type inventory (raw labels preserved per era)
    print("\n  activity_type inventory (raw labels preserved; "
          "taxonomy crosswalk deferred):")
    inv = con.execute(
        "SELECT activity_type, COUNT(*) n, MIN(year) y0, MAX(year) y1 "
        "FROM _fs_all GROUP BY activity_type ORDER BY y0, activity_type"
    ).fetchall()
    for at, n, y0, y1 in inv:
        print(f"    [{y0}-{y1}] {at!r}: {n:,} rows")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    con.execute(
        f"COPY (SELECT * FROM _fs_all ORDER BY ALL) "
        f"TO '{OUT_PATH.as_posix()}' (FORMAT PARQUET)"
    )
    dt = time.perf_counter() - t0
    print(f"\n  wrote {OUT_PATH} ({OUT_PATH.stat().st_size:,} bytes) in {dt:.2f}s")

    print("\n" + "=" * 72)
    print(f"RECONCILIATION: {'ALL YEARS OK' if all_ok else 'MISMATCH — INVESTIGATE'}")
    print("=" * 72)
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
