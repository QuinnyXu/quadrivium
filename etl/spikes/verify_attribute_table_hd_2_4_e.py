"""
etl/spikes/verify_attribute_table_hd_2_4_e.py — HD 2.4.e scope
verification. Verifies herd_panel_attributes.parquet against scoping
doc §1(c) schema spec + per-era population sanity + share ranges.

Output prints to stdout. Read-only on the deposit parquet.
"""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent.parent
ATTR_PARQUET = ROOT / "data" / "harmonized" / "herd_panel_attributes.parquet"

EXPECTED_COLUMNS = [
    ("institution_id",          "VARCHAR"),
    ("year",                    "INTEGER"),
    ("era",                     "VARCHAR"),
    ("med_school_share",        "DOUBLE"),
    ("clinical_trials_share",   "DOUBLE"),
    ("med_school_value",        "DOUBLE"),
    ("clinical_trials_value",   "DOUBLE"),
    ("source_file",             "VARCHAR"),
    ("notes",                   "VARCHAR"),
]


def main() -> int:
    if not ATTR_PARQUET.exists():
        print(f"FAIL: {ATTR_PARQUET} does not exist")
        return 1

    con = duckdb.connect()
    parquet_sql = f"'{ATTR_PARQUET.as_posix()}'"

    print("=" * 78)
    print("HD 2.4.e — attribute table verification")
    print("=" * 78)

    # 1. Schema check
    print("\n[1] Schema (scoping doc §1(c)):")
    schema = con.execute(
        f"DESCRIBE SELECT * FROM {parquet_sql} LIMIT 0"
    ).fetchall()
    actual = [(c[0], c[1]) for c in schema]
    schema_ok = True
    for (exp_name, exp_type), (act_name, act_type) in zip(
            EXPECTED_COLUMNS, actual):
        match = (exp_name == act_name) and (exp_type == act_type)
        flag = "OK " if match else "DIFF"
        if not match:
            schema_ok = False
        print(f"  [{flag}] expected={exp_name:<24s} {exp_type:<8s} | "
              f"actual={act_name:<24s} {act_type}")
    if len(actual) != len(EXPECTED_COLUMNS):
        print(f"  [DIFF] column count: expected={len(EXPECTED_COLUMNS)}, "
              f"actual={len(actual)}")
        schema_ok = False
    print(f"\n  Schema match: {'PASS' if schema_ok else 'FAIL'}")

    # 2. Total row count
    print("\n[2] Total rows + uniqueness on (institution_id, year):")
    n_total = con.execute(
        f"SELECT COUNT(*) FROM {parquet_sql}").fetchone()[0]
    n_distinct = con.execute(
        f"SELECT COUNT(*) FROM (SELECT DISTINCT institution_id, year "
        f"FROM {parquet_sql})").fetchone()[0]
    print(f"  Total rows:                       {n_total:>10,}")
    print(f"  Distinct (institution_id, year):  {n_distinct:>10,}")
    unique_ok = (n_total == n_distinct)
    print(f"  Uniqueness: {'PASS' if unique_ok else 'FAIL'}")

    # 3. Per-era population
    print("\n[3] Per-era population:")
    per_era = con.execute(f"""
        SELECT
          era,
          COUNT(*) AS n_rows,
          COUNT(med_school_value) AS n_med_v,
          COUNT(clinical_trials_value) AS n_ct_v,
          COUNT(med_school_share) AS n_med_s,
          COUNT(clinical_trials_share) AS n_ct_s
        FROM {parquet_sql}
        GROUP BY era ORDER BY era
    """).fetchall()
    print(f"  {'era':<5s} {'n_rows':>10s} {'n_med_v':>10s} "
          f"{'n_ct_v':>10s} {'n_med_s':>10s} {'n_ct_s':>10s}")
    era_ok = True
    for r in per_era:
        print(f"  {r[0]:<5s} {r[1]:>10,} {r[2]:>10,} {r[3]:>10,} "
              f"{r[4]:>10,} {r[5]:>10,}")
        if r[0] == 'A':
            if r[2] != 0 or r[3] != 0 or r[4] != 0 or r[5] != 0:
                era_ok = False
                print(f"    DIFF: era-A should carry NULL for all four "
                      f"Q4/Q5 columns")
    print(f"  Era-A NULL discipline: {'PASS' if era_ok else 'FAIL'}")

    # 4. Year coverage
    print("\n[4] Year coverage by era:")
    year_cov = con.execute(f"""
        SELECT era, MIN(year) AS y_min, MAX(year) AS y_max,
               COUNT(DISTINCT year) AS n_years
        FROM {parquet_sql}
        GROUP BY era ORDER BY era
    """).fetchall()
    for r in year_cov:
        print(f"  era={r[0]} years=[{r[1]}, {r[2]}] n_distinct={r[3]}")

    # 5. Share value ranges (era-B only — era-A NULL by construction)
    print("\n[5] Era-B share value ranges:")
    share_b = con.execute(f"""
        SELECT
          MIN(med_school_share) AS mmin, MAX(med_school_share) AS mmax,
          MIN(clinical_trials_share) AS cmin, MAX(clinical_trials_share) AS cmax
        FROM {parquet_sql}
        WHERE era = 'B'
    """).fetchone()
    print(f"  med_school_share:      "
          f"[{share_b[0]!s:>12s}, {share_b[1]!s:>12s}]")
    print(f"  clinical_trials_share: "
          f"[{share_b[2]!s:>12s}, {share_b[3]!s:>12s}]")
    share_in_band = (
        (share_b[0] is None or share_b[0] >= 0)
        and (share_b[1] is None or share_b[1] <= 1.0001)
        and (share_b[2] is None or share_b[2] >= 0)
        and (share_b[3] is None or share_b[3] <= 1.0001)
    )
    print(f"  Shares in [0, ~1]: {'PASS' if share_in_band else 'FAIL'}")

    # 6. Q5 raw-vs-canonical drift handling (HD 2.4.e §10 explicit
    # deliverable). Stage 8 admits both 'Clinical trial R&D
    # expenditures' (canonical) and 'Clinical trials' (raw) in its
    # source filter. Verify by counting institution-years that have
    # a clinical_trials_value populated, by year, to confirm both
    # vintages are represented (canonical raw label appears in 2010+,
    # the raw 'Clinical trials' label per crosswalks/question_map.csv
    # row 16 may appear in earlier-vintage CSVs).
    print("\n[6] Q5 raw-vs-canonical drift coverage by year:")
    q5_by_year = con.execute(f"""
        SELECT year,
               COUNT(*) AS n_rows,
               COUNT(clinical_trials_value) AS n_ct_value
        FROM {parquet_sql}
        WHERE era = 'B'
        GROUP BY year ORDER BY year
    """).fetchall()
    print(f"  {'year':>6s} {'n_rows':>10s} {'n_ct_value':>12s}")
    coverage_ok = True
    for r in q5_by_year:
        print(f"  {r[0]:>6d} {r[1]:>10,} {r[2]:>12,}")
        if r[2] == 0:
            coverage_ok = False
            print(f"    DIFF: year {r[0]} has zero clinical_trials_value")
    print(f"  Q5 covered every era-B year: "
          f"{'PASS' if coverage_ok else 'FAIL'}")

    # 7. Final summary
    print("\n" + "=" * 78)
    print("HD 2.4.e scope verification summary:")
    print("=" * 78)
    all_pass = (schema_ok and unique_ok and era_ok and share_in_band
                and coverage_ok)
    print(f"  [{'PASS' if schema_ok else 'FAIL'}] Schema matches §1(c) spec")
    print(f"  [{'PASS' if unique_ok else 'FAIL'}] "
          f"(institution_id, year) uniqueness")
    print(f"  [{'PASS' if era_ok else 'FAIL'}] "
          f"Era-A Q4/Q5 NULL discipline")
    print(f"  [{'PASS' if share_in_band else 'FAIL'}] "
          f"Era-B shares within [0, ~1]")
    print(f"  [{'PASS' if coverage_ok else 'FAIL'}] "
          f"Q5 coverage at every era-B year")
    print()
    print(f"  Verdict: HD 2.4.e {'CLOSED-AT-HD-2.4.d' if all_pass else 'OPEN'}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
