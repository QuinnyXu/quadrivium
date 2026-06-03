"""etl/build_gss_race.py — HD 4.3 GSS Race (enrollment/demographic) panel.

Builds ``data/harmonized/gss_race.parquet``: long-format graduate-student
enrollment by enrollment-status × degree × gender × race, FY1972–2024,
native-UNITID-keyed. Wide → long via ``crosswalks/gss/race_column_map.csv``.

Same conventions as ``gss_support`` (HD 4.2): non-zero grain (omitted cell =
structural zero); field names deferred (``gss_code`` raw, ``field_coarse/fine``
NULL pending the field-code crosswalk). Deterministic ORDER BY before COPY.

    uv run python etl/build_gss_race.py
"""
from __future__ import annotations
import csv, glob, os, re
from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parent.parent
CSV_GLOB = str(ROOT / "data" / "raw" / "gss" / "csv" / "gss*_race.csv")
XWALK = ROOT / "crosswalks" / "gss" / "race_column_map.csv"
OUT = ROOT / "data" / "harmonized" / "gss_race.parquet"
ID_MAP = {
    "UNITID": "unitid", "Institution_Name": "institution_name",
    "school_id": "gss_school_id", "gss_code": "gss_code", "hdg_code": "hdg_code",
    "institution_state": "state", "hbcu_flag": "hbcu_flag", "land_grant_flag": "land_grant_flag",
}


def build_year(con, path, xcols):
    year = int(re.search(r"(\d{4})", os.path.basename(path)).group(1))
    era = "pre2017" if year <= 2016 else "post2017"
    with open(path, encoding="utf-8") as fh:
        header = next(csv.reader(fh))
    measure = [c for c in header if c in xcols]
    con.execute(f"CREATE OR REPLACE TABLE raw AS SELECT * FROM "
                f"read_csv('{Path(path).as_posix()}', header=true, all_varchar=true)")
    on_list = ", ".join(f'"{c}"' for c in measure)
    id_sel = ", ".join(f'"{src}"' for src in ID_MAP if src in header)
    con.execute(f"""CREATE OR REPLACE TABLE long_y AS
        SELECT {id_sel}, source_column, value
        FROM (UNPIVOT raw ON {on_list} INTO NAME source_column VALUE value)
        WHERE TRY_CAST(value AS DOUBLE) IS NOT NULL AND TRY_CAST(value AS DOUBLE) <> 0""")
    sel_ids = ", ".join(f'l."{src}" AS {dst}' for src, dst in ID_MAP.items() if src in header)
    con.execute(f"""INSERT INTO panel
        SELECT {sel_ids},
          CAST(NULL AS VARCHAR) AS field_coarse, CAST(NULL AS VARCHAR) AS field_fine,
          {year} AS year, '{era}' AS era,
          x.enrollment_status, x.degree_level, x.gender, x.race,
          CAST(ROUND(CAST(l.value AS DOUBLE)) AS BIGINT) AS value,
          'headcount' AS unit, 'count' AS value_type, 'reported' AS quality_flag,
          'Race' AS source_sheet, '{os.path.basename(path)}' AS source_file,
          CAST(NULL AS VARCHAR) AS notes
        FROM long_y l JOIN xwalk x USING (source_column)""")
    return con.execute("SELECT COUNT(*) FROM long_y").fetchone()[0]


def main() -> int:
    con = duckdb.connect()
    con.execute(f"CREATE OR REPLACE TABLE xwalk AS SELECT * FROM "
                f"read_csv('{XWALK.as_posix()}', header=true, all_varchar=true)")
    xcols = {r[0] for r in con.execute("SELECT source_column FROM xwalk").fetchall()}
    con.execute("""CREATE TABLE panel (
        unitid VARCHAR, institution_name VARCHAR, gss_school_id VARCHAR, gss_code VARCHAR,
        hdg_code VARCHAR, state VARCHAR, hbcu_flag VARCHAR, land_grant_flag VARCHAR,
        field_coarse VARCHAR, field_fine VARCHAR, year BIGINT, era VARCHAR,
        enrollment_status VARCHAR, degree_level VARCHAR, gender VARCHAR, race VARCHAR,
        value BIGINT, unit VARCHAR, value_type VARCHAR, quality_flag VARCHAR,
        source_sheet VARCHAR, source_file VARCHAR, notes VARCHAR)""")
    total = 0
    for f in sorted(glob.glob(CSV_GLOB)):
        total += build_year(con, f, xcols)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    con.execute(f"""COPY (SELECT * FROM panel
        ORDER BY unitid, gss_school_id, year, gss_code, hdg_code, enrollment_status,
                 degree_level, gender, race, value)
        TO '{OUT.as_posix()}' (FORMAT parquet)""")
    rows = con.execute("SELECT COUNT(*) FROM panel").fetchone()[0]
    insts = con.execute("SELECT COUNT(DISTINCT unitid) FROM panel").fetchone()[0]
    yrs = con.execute("SELECT MIN(year), MAX(year) FROM panel").fetchone()
    print(f"Wrote {OUT.relative_to(ROOT)}: {rows:,} rows, {insts} institutions, "
          f"FY{yrs[0]}-{yrs[1]} ({OUT.stat().st_size/1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
