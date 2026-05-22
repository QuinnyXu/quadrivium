"""
etl/spikes/spike_equipment_era_boundary.py — HD 2.4.f.

Compare era-A Item 3 ('Current fund research equipment expenditures
by field' / raw 'Equipment expenditures by S&E field', 1981-2009)
totals at FY 2008/2009 with era-B Q14 ('Capitalized R&D equipment
expenditures by field and source', 2010-2024) totals at FY 2010/2011
for the top-10-by-FY-2008-R&D cohort (continuity with HD 2.1.b's
`validation/reports/era_reconciliation_2008_2011.md`).

Question: is the equipment series continuous across the 2009->2010
era boundary, or does the Item-3-to-Q14 question reframing introduce
a level shift?

Verdict criteria (locked at session kickoff):
  - Sign-consistent + magnitude-stable: methods-note ships the
    parallel-rows assumption. Item 3 -> Q14 r&d_equipment direct read
    across 2010 boundary. No footnote needed.
  - Divergent: methods-note ships an equipment-series footnote at
    HD 2.4.i naming the divergence with empirical magnitudes.

Reads from `data/harmonized/herd_panel.parquet`. Source rows:
  - Era-A: `era='A'`, `expenditure_type='r&d_equipment'`,
    `source_class='all_source'`, `form_type='standard'`,
    `discipline_fine='All'` (institution-year equipment total).
  - Era-B: `era='B'`, `expenditure_type='r&d_equipment'`,
    `source_class='all_source'`, `form_type='standard'`,
    `discipline_fine='All'`.

Output prints to stdout; also emits a Markdown findings table.
"""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent.parent
PANEL_PARQUET = ROOT / "data" / "harmonized" / "herd_panel.parquet"

# Top-10 cohort by FY 2008 R&D from
# `validation/reports/era_reconciliation_2008_2011.md` §Sample.
TOP10_COHORT = [
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
COHORT_IDS = [iid for (iid, _) in TOP10_COHORT]
COHORT_NAME = {iid: name for (iid, name) in TOP10_COHORT}
SPOT_YEARS = (2008, 2009, 2010, 2011)

# Magnitude-stability band for the 2009 -> 2010 boundary ratio
# (Q14_2010 / Item3_2009). The full year-over-year R&D context
# from HD 2.1.b's diagnostic 3 surfaced ~26% national R&D growth
# FY2008->FY2011 in current dollars. A reasonable equipment-series
# band absorbs real growth and modest measurement-frame variation.
# Bands chosen pre-spike (no result-driven tuning):
#   - Stable: per-institution 2009->2010 ratio in [0.5, 2.0].
#     Allows up to 2x level change (covers real growth across a
#     boundary year plus modest reframing).
#   - Sign-consistent: every per-institution per-spot-year value
#     positive (the equipment expenditure must not be a negative
#     or NaN where the question was asked).
STABLE_RATIO_BAND = (0.5, 2.0)


def fetch_equipment_totals(con: duckdb.DuckDBPyConnection) -> dict:
    """Return {inst_id: {year: value}} for the top-10 cohort at the
    institution-year r&d_equipment / all_source / 'All' grain."""
    parquet_sql = f"'{PANEL_PARQUET.as_posix()}'"
    placeholders = ",".join(["?"] * len(COHORT_IDS))
    sql = f"""
        SELECT institution_id, year, value
        FROM {parquet_sql}
        WHERE expenditure_type = 'r&d_equipment'
          AND source_class = 'all_source'
          AND form_type = 'standard'
          AND discipline_fine = 'All'
          AND year IN (2008, 2009, 2010, 2011)
          AND institution_id IN ({placeholders})
    """
    rows = con.execute(sql, COHORT_IDS).fetchall()
    out: dict = {iid: {} for iid in COHORT_IDS}
    for (iid, yr, val) in rows:
        out[iid][int(yr)] = float(val) if val is not None else None
    return out


def fetch_cohort_year_alt_totals(con: duckdb.DuckDBPyConnection) -> dict:
    """Sum across discipline_fine != 'All' as a cross-check on the
    'All' rollup row. If the 'All' row was missing or stale, the
    leaf-sum would diverge; the spike surfaces that cross-check."""
    parquet_sql = f"'{PANEL_PARQUET.as_posix()}'"
    placeholders = ",".join(["?"] * len(COHORT_IDS))
    sql = f"""
        SELECT institution_id, year, SUM(value) AS leaf_sum
        FROM {parquet_sql}
        WHERE expenditure_type = 'r&d_equipment'
          AND source_class = 'all_source'
          AND form_type = 'standard'
          AND discipline_fine != 'All'
          AND year IN (2008, 2009, 2010, 2011)
          AND institution_id IN ({placeholders})
        GROUP BY institution_id, year
    """
    rows = con.execute(sql, COHORT_IDS).fetchall()
    out: dict = {iid: {} for iid in COHORT_IDS}
    for (iid, yr, leaf_sum) in rows:
        out[iid][int(yr)] = float(leaf_sum) if leaf_sum is not None else None
    return out


def main() -> int:
    if not PANEL_PARQUET.exists():
        print(f"FAIL: {PANEL_PARQUET} does not exist")
        return 1

    con = duckdb.connect()
    print("=" * 78)
    print("HD 2.4.f — Q14 era-boundary spike")
    print("=" * 78)
    print()
    print("Cohort: top-10 by FY 2008 R&D (HD 2.1.b continuity).")
    print("Spot years: FY 2008, 2009 (era-A Item 3), "
          "FY 2010, 2011 (era-B Q14).")
    print("Grain: discipline_fine='All', source_class='all_source', "
          "form_type='standard', expenditure_type='r&d_equipment'.")
    print()

    totals = fetch_equipment_totals(con)
    leaf_sums = fetch_cohort_year_alt_totals(con)

    # ---- 1. Per-institution per-year totals (institutional table) -----
    print("[1] Per-institution per-year r&d_equipment totals "
          "(kUSD_current):")
    print()
    print(f"  {'inst_id':<8s} {'institution':<40s} "
          f"{'FY2008':>10s} {'FY2009':>10s} {'FY2010':>10s} "
          f"{'FY2011':>10s}")
    print(f"  {'-'*8:<8s} {'-'*40:<40s} "
          f"{'-'*10:>10s} {'-'*10:>10s} {'-'*10:>10s} {'-'*10:>10s}")
    md_inst_rows = []
    md_inst_rows.append(
        "| inst_id | institution | FY2008 (Item 3) | FY2009 (Item 3) "
        "| FY2010 (Q14) | FY2011 (Q14) |"
    )
    md_inst_rows.append(
        "|---|---|---:|---:|---:|---:|"
    )
    n_signs_positive = 0
    n_signs_total = 0
    for iid in COHORT_IDS:
        name = COHORT_NAME[iid]
        vals = totals[iid]
        cells = []
        for yr in SPOT_YEARS:
            v = vals.get(yr)
            if v is None:
                cells.append((yr, None, "    MISS"))
            else:
                n_signs_total += 1
                if v > 0:
                    n_signs_positive += 1
                cells.append((yr, v, f"{v:>10,.0f}"))
        print(f"  {iid:<8s} {name[:40]:<40s} "
              f"{cells[0][2]:>10s} {cells[1][2]:>10s} "
              f"{cells[2][2]:>10s} {cells[3][2]:>10s}")
        md_inst_rows.append(
            f"| {iid} | {name} | {cells[0][2].strip()} "
            f"| {cells[1][2].strip()} "
            f"| {cells[2][2].strip()} | {cells[3][2].strip()} |"
        )
    print()
    print(f"  Sign-positive cells: {n_signs_positive} / "
          f"{n_signs_total} populated")
    sign_pass = (n_signs_positive == n_signs_total)
    print(f"  Sign-consistency: {'PASS' if sign_pass else 'FAIL'}")
    print()

    # ---- 2. Boundary-ratio analysis (2009 -> 2010) -----
    print("[2] Boundary ratio (Q14 FY2010 / Item 3 FY2009):")
    print()
    print(f"  {'inst_id':<8s} {'institution':<40s} "
          f"{'Item3_2009':>12s} {'Q14_2010':>12s} {'ratio':>8s} "
          f"{'in band':>10s}")
    print(f"  {'-'*8:<8s} {'-'*40:<40s} "
          f"{'-'*12:>12s} {'-'*12:>12s} {'-'*8:>8s} {'-'*10:>10s}")
    md_ratio_rows = []
    md_ratio_rows.append(
        "| inst_id | institution | Item3 FY2009 | Q14 FY2010 "
        "| ratio | in band [0.5, 2.0] |"
    )
    md_ratio_rows.append(
        "|---|---|---:|---:|---:|---|"
    )
    ratios = []
    n_in_band = 0
    n_ratio_eval = 0
    for iid in COHORT_IDS:
        name = COHORT_NAME[iid]
        v2009 = totals[iid].get(2009)
        v2010 = totals[iid].get(2010)
        if v2009 is None or v2010 is None or v2009 <= 0:
            ratio_str = "  MISS"
            band_str = "  MISS"
            md_ratio_rows.append(
                f"| {iid} | {name} | "
                f"{v2009 if v2009 is None else f'{v2009:,.0f}'} "
                f"| {v2010 if v2010 is None else f'{v2010:,.0f}'} "
                f"| MISS | MISS |"
            )
        else:
            ratio = v2010 / v2009
            ratios.append(ratio)
            in_band = (STABLE_RATIO_BAND[0] <= ratio
                       <= STABLE_RATIO_BAND[1])
            if in_band:
                n_in_band += 1
            n_ratio_eval += 1
            ratio_str = f"{ratio:>8.3f}"
            band_str = ("OK" if in_band else "OUT") + (
                f" [{ratio:.2f}]")
            md_ratio_rows.append(
                f"| {iid} | {name} | {v2009:,.0f} | {v2010:,.0f} "
                f"| {ratio:.3f} | {'OK' if in_band else 'OUT'} |"
            )
        print(f"  {iid:<8s} {name[:40]:<40s} "
              f"{v2009 if v2009 is None else f'{v2009:>12,.0f}':>12s} "
              f"{v2010 if v2010 is None else f'{v2010:>12,.0f}':>12s} "
              f"{ratio_str:>8s} {band_str:>10s}")
    print()
    if ratios:
        ratios_sorted = sorted(ratios)
        n = len(ratios_sorted)
        median = (ratios_sorted[n // 2] if n % 2 == 1 else
                  0.5 * (ratios_sorted[n // 2 - 1]
                         + ratios_sorted[n // 2]))
        print(f"  Boundary ratio distribution "
              f"(n={n_ratio_eval} populated pairs):")
        print(f"    min:    {min(ratios):.3f}")
        print(f"    p25:    {ratios_sorted[n // 4]:.3f}")
        print(f"    median: {median:.3f}")
        print(f"    p75:    {ratios_sorted[(3 * n) // 4]:.3f}")
        print(f"    max:    {max(ratios):.3f}")
        print(f"    mean:   {sum(ratios)/n:.3f}")
    print()
    band_pass = (n_in_band == n_ratio_eval and n_ratio_eval > 0)
    print(f"  In-band [0.5, 2.0]: {n_in_band} / "
          f"{n_ratio_eval} populated pairs")
    print(f"  Magnitude-stability: {'PASS' if band_pass else 'FAIL'}")
    print()

    # ---- 3. Cohort-aggregate boundary ratios -----
    print("[3] Cohort-aggregate equipment totals + boundary ratios:")
    cohort_year_totals = {}
    for yr in SPOT_YEARS:
        total = sum(totals[iid].get(yr) or 0.0 for iid in COHORT_IDS)
        cohort_year_totals[yr] = total
    print()
    for yr in SPOT_YEARS:
        print(f"  FY{yr}:  cohort-total = "
              f"{cohort_year_totals[yr]:>14,.0f} kUSD_current")
    if cohort_year_totals[2009] > 0:
        cohort_ratio = (cohort_year_totals[2010]
                        / cohort_year_totals[2009])
        print(f"\n  Cohort boundary ratio "
              f"(Q14_2010 / Item3_2009): {cohort_ratio:.3f}")
        cohort_ratio_2011_2008 = (cohort_year_totals[2011]
                                  / cohort_year_totals[2008])
        print(f"  Cohort 2011/2008 ratio (long-gap):       "
              f"{cohort_ratio_2011_2008:.3f}")
    print()

    # ---- 4. Leaf-sum cross-check (catch 'All' rollup staleness) -----
    print("[4] Leaf-sum cross-check ('All' row vs. sum across "
          "discipline_fine!='All'):")
    print()
    print(f"  {'inst_id':<8s} {'year':>4s} "
          f"{'All_row':>12s} {'leaf_sum':>12s} "
          f"{'delta':>10s} {'delta_pct':>10s}")
    print(f"  {'-'*8:<8s} {'-'*4:>4s} "
          f"{'-'*12:>12s} {'-'*12:>12s} "
          f"{'-'*10:>10s} {'-'*10:>10s}")
    leaf_anomalies = 0
    leaf_pairs = 0
    for iid in COHORT_IDS:
        for yr in SPOT_YEARS:
            v_all = totals[iid].get(yr)
            v_leaf = leaf_sums[iid].get(yr)
            if v_all is None or v_leaf is None or v_all == 0:
                continue
            leaf_pairs += 1
            delta = v_leaf - v_all
            delta_pct = 100.0 * delta / v_all
            anomalous = abs(delta_pct) > 1.0
            if anomalous:
                leaf_anomalies += 1
            print(f"  {iid:<8s} {yr:>4d} "
                  f"{v_all:>12,.0f} {v_leaf:>12,.0f} "
                  f"{delta:>10,.0f} {delta_pct:>9.2f}%"
                  + ("  !" if anomalous else ""))
    print()
    print(f"  Leaf-sum anomalies (>1% delta): "
          f"{leaf_anomalies} / {leaf_pairs}")
    print()

    # ---- 5. Verdict -----
    print("=" * 78)
    print("HD 2.4.f verdict:")
    print("=" * 78)
    print(f"  Sign-consistent (every populated cell > 0):  "
          f"{'PASS' if sign_pass else 'FAIL'}")
    print(f"  Magnitude-stable (boundary ratios in [0.5, 2.0]): "
          f"{'PASS' if band_pass else 'FAIL'}")
    overall_pass = sign_pass and band_pass
    print()
    if overall_pass:
        print("  VERDICT: PARALLEL-ROWS-ASSUMPTION HOLDS.")
        print("  Item 3 -> Q14 r&d_equipment series ships across the")
        print("  2010 boundary as a direct-read parallel series. No")
        print("  equipment-series footnote needed at HD 2.4.i.")
    else:
        print("  VERDICT: EQUIPMENT-SERIES DIVERGENT.")
        print("  Item 3 and Q14 do not align as a continuous equipment")
        print("  series. Methods-note ships an equipment-series")
        print("  footnote at HD 2.4.i naming the divergence with the")
        print("  empirical magnitudes printed above.")
    print()

    # ---- 6. Markdown findings table dump (for findings report) -----
    print("=" * 78)
    print("Markdown findings tables (for findings report):")
    print("=" * 78)
    print()
    print("### Per-institution per-year r&d_equipment totals")
    print()
    for r in md_inst_rows:
        print(r)
    print()
    print("### Boundary ratios (Q14 FY2010 / Item 3 FY2009)")
    print()
    for r in md_ratio_rows:
        print(r)
    print()

    return 0 if overall_pass else 2


if __name__ == "__main__":
    sys.exit(main())
