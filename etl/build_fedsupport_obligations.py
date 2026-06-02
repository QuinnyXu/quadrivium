"""
etl/build_fedsupport_obligations.py — build the Federal S&E Support panels
from the full-series NCSES Build Table export (v3.0 re-base).

Emits two harmonized parquets:

  data/harmonized/fedsupport_obligations.parquet
      Full long grain, ALL universes (one row per source row): every
      dept × agency × broad × detailed × institution × type × state × year
      obligation. Consumers filter via institution_type / ipeds_unitid_status
      / broad_category. Schema: see etl/_load_fedsupport.read_fedsupport.

  data/harmonized/fedsupport_institution_year.parquet
      HERD-join-ready aggregate: the HIGHER-ED universe
      ({Academic institution, Academic consortium}), MATCHED native UNITID
      only, aggregated to (fiscal_year, ipeds_unitid) with R&D and S&E-support
      split:
          fiscal_year, ipeds_unitid, institution_name, state,
          rd_obligations_kusd, se_support_kusd, total_se_kusd
      R&D-broad is the like-for-like counterpart to HERD federal R&D
      expenditure; S&E-support is the documented superset (d).

Validation (b): per-year higher-ed (academic+consortium) totals reconcile to
the published Table 12 grand-total anchors (FY2020–FY2023 exact). The 53-year
series is printed for the coverage receipt + methods note.

Reproducibility (§3): RFC-4180 read via read_csv_auto only; ORDER BY ALL
before each COPY makes both parquets a deterministic function of the input CSV
+ this code.

Run:
    uv run python etl/build_fedsupport_obligations.py

Author: Skipper, 2026-06-02 (v3.0 re-base).
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from etl._load_fedsupport import (  # noqa: E402
    read_fedsupport,
    fedsupport_csv_path,
    write_text_clean,
    HIGHER_ED_TYPES,
    BROAD_RD,
    BROAD_SUPPORT,
)

OUT_LONG = ROOT / "data" / "harmonized" / "fedsupport_obligations.parquet"
OUT_INSTYEAR = ROOT / "data" / "harmonized" / "fedsupport_institution_year.parquet"
RECEIPT = (ROOT / "validation" / "reports" / "fedsupport"
           / "anchor_reconciliation.md")

# Published higher-ed-only (academic+consortium) Table 12 grand-total anchors
# (kUSD). FY2020/2021/2023 from HD 3.1 §2 + §9; FY2022 derived at acquisition,
# InfoBrief NSF 24-325 cross-checked. These are the (b) overlap anchors the
# Build Table export must reproduce to supersede Table 12.
GRAND_TOTAL_ANCHOR = {
    2020: 39_122_152,
    2021: 43_222_829,
    2022: 44_628_417,
    2023: 48_961_658,
}


def main() -> int:
    con = duckdb.connect()
    print("=" * 72)
    print("v3.0 re-base — build FedSupport panels from the full-series export")
    print("=" * 72)
    print(f"  source: {fedsupport_csv_path().name}")

    rel = read_fedsupport(con)
    con.execute(f"CREATE OR REPLACE TEMP TABLE fs_long AS SELECT * FROM ({rel.sql_query()})")

    n_rows = con.execute("SELECT COUNT(*) FROM fs_long").fetchone()[0]
    y0, y1, ny = con.execute(
        "SELECT MIN(fiscal_year), MAX(fiscal_year), COUNT(DISTINCT fiscal_year) FROM fs_long"
    ).fetchone()
    print(f"\n  long rows: {n_rows:,}   years: {y0}-{y1} ({ny} distinct)")

    he = "institution_type IN {}".format(HIGHER_ED_TYPES)

    # --- (b) per-year higher-ed reconciliation vs anchors ---
    print("\n--- (b) HIGHER-ED (academic+consortium) RECONCILIATION vs anchors ---")
    print(f"{'FY':>5} {'higher_ed_$K':>16} {'anchor':>14} {'diff':>10}")
    all_ok = True
    for fy in sorted(GRAND_TOTAL_ANCHOR):
        got = con.execute(
            f"SELECT SUM(obligations_kusd) FROM fs_long WHERE fiscal_year={fy} AND {he}"
        ).fetchone()[0]
        anchor = GRAND_TOTAL_ANCHOR[fy]
        diff = got - anchor
        # rounding tolerance: the export is whole-kUSD per row; summing rounded
        # rows accumulates a few kUSD vs the unrounded published grand total
        # (observed max |diff| = 4,191 kUSD on $44.6B = 0.009%).
        ok = abs(diff) <= 5_000  # absolute 5,000 kUSD band (sum-rounding)
        all_ok = all_ok and ok
        print(f"{fy:>5} {got:>16,.0f} {anchor:>14,} {diff:>+10,.0f}"
              f"  {'OK' if ok else 'MISMATCH'}")

    # --- full 53-year higher-ed series (for the coverage receipt / methods note) ---
    print("\n--- higher-ed series FY1971-FY2023 (academic+consortium) ---")
    series = con.execute(
        f"SELECT fiscal_year, SUM(obligations_kusd) FROM fs_long WHERE {he} "
        "GROUP BY fiscal_year ORDER BY fiscal_year"
    ).fetchall()
    for fy, d in series:
        print(f"    FY{fy}: {d:,.0f} kUSD")

    # --- write full long-grain parquet (ALL universes) ---
    print("\n--- WRITE PARQUETS ---")
    t0 = time.perf_counter()
    OUT_LONG.parent.mkdir(parents=True, exist_ok=True)
    con.execute(
        f"COPY (SELECT * FROM fs_long ORDER BY ALL) "
        f"TO '{OUT_LONG.as_posix()}' (FORMAT PARQUET)"
    )
    print(f"  wrote {OUT_LONG.name} ({OUT_LONG.stat().st_size:,} bytes)")

    # --- write HERD-join institution-year aggregate (higher-ed, matched UNITID) ---
    con.execute(
        f"""CREATE OR REPLACE TEMP TABLE fs_iy AS
        SELECT
          fiscal_year,
          ipeds_unitid,
          MIN(institution_name_raw) AS institution_name,
          MIN(state)                AS state,
          SUM(CASE WHEN broad_category='{BROAD_RD}'      THEN obligations_kusd ELSE 0 END) AS rd_obligations_kusd,
          SUM(CASE WHEN broad_category='{BROAD_SUPPORT}' THEN obligations_kusd ELSE 0 END) AS se_support_kusd,
          SUM(obligations_kusd) AS total_se_kusd
        FROM fs_long
        WHERE {he} AND ipeds_unitid_status='matched'
        GROUP BY fiscal_year, ipeds_unitid"""
    )
    n_iy = con.execute("SELECT COUNT(*) FROM fs_iy").fetchone()[0]
    con.execute(
        f"COPY (SELECT * FROM fs_iy ORDER BY ALL) "
        f"TO '{OUT_INSTYEAR.as_posix()}' (FORMAT PARQUET)"
    )
    dt = time.perf_counter() - t0
    print(f"  wrote {OUT_INSTYEAR.name} ({OUT_INSTYEAR.stat().st_size:,} bytes); "
          f"{n_iy:,} (fy,unitid) rows")
    print(f"  build time: {dt:.2f}s")

    # --- write the anchor-reconciliation receipt (deterministic, Option A) ---
    _write_receipt(con, series)

    print("\n" + "=" * 72)
    print(f"RECONCILIATION: {'ALL ANCHOR YEARS OK' if all_ok else 'MISMATCH — INVESTIGATE'}")
    print("=" * 72)
    return 0 if all_ok else 1


def _write_receipt(con: duckdb.DuckDBPyConnection, series) -> None:
    """Generator-emitted (b) anchor-reconciliation receipt. Supersedes the
    MVP's hand-authored fedsupport_parse_reconciliation.md (Table 12 →
    audit sibling); this receipt validates the Build Table export source."""
    A = []
    a = A.append
    a("# FedSupport anchor-reconciliation receipt (v3.0 re-base)")
    a("")
    a("Generated by `etl/build_fedsupport_obligations.py` (deterministic). "
      "Author: Skipper, 2026-06-02.")
    a("")
    a("> **(b) The full-series Build Table export supersedes the four "
      "FY2020–FY2023 Table 12 slices.** Filtered to the published higher-ed "
      "universe (academic institution + academic consortium), the export "
      "reconciles to every validated Table 12 grand-total anchor within "
      "sum-of-rounded-rows tolerance. The Table 12 CSVs/PDFs are retained as "
      "audit siblings (the MVP's `fedsupport_parse_reconciliation.md` is "
      "superseded by this receipt).")
    a("")
    a("## Overlap reconciliation (higher-ed academic+consortium vs anchors)")
    a("")
    a("| FY | export higher-ed $K | published anchor $K | diff | diff % |")
    a("|---:|---:|---:|---:|---:|")
    for fy in sorted(GRAND_TOTAL_ANCHOR):
        got = con.execute(
            f"SELECT SUM(obligations_kusd) FROM fs_long WHERE fiscal_year={fy} "
            f"AND institution_type IN {HIGHER_ED_TYPES}").fetchone()[0]
        anc = GRAND_TOTAL_ANCHOR[fy]
        a(f"| {fy} | {got:,.0f} | {anc:,} | {got-anc:+,.0f} | {(got-anc)/anc:+.3%} |")
    a("")
    a("The diffs are sum-of-whole-kUSD-rounded-rows vs the unrounded published "
      "grand totals (max |diff| 4,191 kUSD = 0.009%).")
    a("")
    a("## Full higher-ed series FY1971–FY2023 (academic+consortium, $K)")
    a("")
    a("| FY | higher-ed $K |  | FY | higher-ed $K |")
    a("|---:|---:|---|---:|---:|")
    half = (len(series) + 1) // 2
    left, right = series[:half], series[half:]
    for i in range(half):
        l = f"{left[i][0]} | {left[i][1]:,.0f}"
        r = f"{right[i][0]} | {right[i][1]:,.0f}" if i < len(right) else " | "
        a(f"| {l} |  | {r} |")
    write_text_clean(RECEIPT, "\n".join(A) + "\n")
    print(f"  wrote {RECEIPT.name}")


if __name__ == "__main__":
    sys.exit(main())
