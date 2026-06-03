"""etl/build_gss_pd_nfr.py — HD 4.3 GSS PD_NFR (postdoc + non-faculty-researcher) panel.

Builds ``data/harmonized/gss_pd_nfr.parquet``: long-format postdocs and
non-faculty researchers, FY1972–2024, native-UNITID-keyed. Wide → long via
``crosswalks/gss/pd_nfr_column_map.csv``.

**Overlapping-marginal grain.** The PD_NFR sheet carries several marginal tables
sharing the same totals; each row is tagged with ``measure_group`` — a consumer
sums WITHIN a group, never across (which would double-count). Non-zero grain
(omitted = structural zero); field names deferred. Deterministic ORDER BY.

    uv run python etl/build_gss_pd_nfr.py
"""
from __future__ import annotations
import csv, glob, os, re
from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parent.parent
CSV_GLOB = str(ROOT / "data" / "raw" / "gss" / "csv" / "gss*_pd_nfr.csv")
XWALK = ROOT / "crosswalks" / "gss" / "pd_nfr_column_map.csv"
OUT = ROOT / "data" / "harmonized" / "gss_pd_nfr.parquet"
ID_MAP = {
    "UNITID": "unitid", "Institution_Name": "institution_name",
    "school_id": "gss_school_id", "gss_code": "gss_code", "hdg_code": "hdg_code",
    "institution_state": "state", "hbcu_flag": "hbcu_flag", "land_grant_flag": "land_grant_flag",
}
CANON = ["population", "measure_group", "gender", "race", "support_mechanism",
         "source_class", "funding_agency", "degree_type", "citizenship"]


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
    canon_sel = ", ".join(f"x.{c}" for c in CANON)
    con.execute(f"""INSERT INTO panel
        SELECT {sel_ids},
          fc.fc AS field_coarse, fc.ff AS field_fine,
          {year} AS year, '{era}' AS era, {canon_sel},
          CAST(ROUND(CAST(l.value AS DOUBLE)) AS BIGINT) AS value,
          'headcount' AS unit, 'count' AS value_type, 'reported' AS quality_flag,
          'PD_NFR' AS source_sheet, '{os.path.basename(path)}' AS source_file,
          CAST(NULL AS VARCHAR) AS notes
        FROM long_y l JOIN xwalk x USING (source_column)
        LEFT JOIN fcmap fc ON l."gss_code" = fc.gss_code""")
    return con.execute("SELECT COUNT(*) FROM long_y").fetchone()[0]


def main() -> int:
    con = duckdb.connect()
    con.execute(f"CREATE OR REPLACE TABLE xwalk AS SELECT * FROM "
                f"read_csv('{XWALK.as_posix()}', header=true, all_varchar=true)")
    xcols = {r[0] for r in con.execute("SELECT source_column FROM xwalk").fetchall()}
    con.execute(f"CREATE OR REPLACE TABLE fcmap AS SELECT gss_code, "
                f"NULLIF(field_coarse,'') fc, NULLIF(field_fine,'') ff FROM "
                f"read_csv('{(ROOT / 'crosswalks' / 'gss' / 'field_code_map.csv').as_posix()}', "
                f"header=true, all_varchar=true)")
    canon_cols = ", ".join(f"{c} VARCHAR" for c in CANON)
    con.execute(f"""CREATE TABLE panel (
        unitid VARCHAR, institution_name VARCHAR, gss_school_id VARCHAR, gss_code VARCHAR,
        hdg_code VARCHAR, state VARCHAR, hbcu_flag VARCHAR, land_grant_flag VARCHAR,
        field_coarse VARCHAR, field_fine VARCHAR, year BIGINT, era VARCHAR, {canon_cols},
        value BIGINT, unit VARCHAR, value_type VARCHAR, quality_flag VARCHAR,
        source_sheet VARCHAR, source_file VARCHAR, notes VARCHAR)""")
    total = 0
    for f in sorted(glob.glob(CSV_GLOB)):
        total += build_year(con, f, xcols)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    order = "unitid, gss_school_id, year, gss_code, hdg_code, population, measure_group, " \
            "gender, race, support_mechanism, source_class, funding_agency, degree_type, citizenship, value"
    con.execute(f"COPY (SELECT * FROM panel ORDER BY {order}) TO '{OUT.as_posix()}' (FORMAT parquet)")
    rows = con.execute("SELECT COUNT(*) FROM panel").fetchone()[0]
    insts = con.execute("SELECT COUNT(DISTINCT unitid) FROM panel").fetchone()[0]
    yrs = con.execute("SELECT MIN(year), MAX(year) FROM panel").fetchone()
    print(f"Wrote {OUT.relative_to(ROOT)}: {rows:,} rows, {insts} institutions, "
          f"FY{yrs[0]}-{yrs[1]} ({OUT.stat().st_size/1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
