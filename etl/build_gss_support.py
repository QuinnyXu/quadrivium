"""etl/build_gss_support.py — HD 4.2 GSS Support harmonized panel (MVP).

Builds ``data/harmonized/gss_support.parquet``: the long-format funding face of
GSS — full-time graduate students by support mechanism × federal agency ×
fed/nonfed, FY1972–2024, native-UNITID-keyed. Wide → long via the committed
crosswalk ``crosswalks/gss/support_column_map.csv`` (every Support column →
canonical tuple), reconciling the 2017 redesign (clause-(a)).

Grain decision (HD 4.2): GSS reports a **complete grid with explicit zeros**
(2023: 86.5% of support cells are 0, 13.5% positive, 0 empty). The panel emits
**non-zero values only**; an omitted (institution × field × degree × gender ×
mechanism × source × agency) cell is a **structural zero** (lossless — the source
grid is complete per reported institution-field). Field names are deferred:
``gss_code``/``hdg_code`` are carried raw, ``field_coarse``/``field_fine`` NULL
pending the NCSES GSS field-code reference.

Input: gitignored converted CSVs (``etl/acquire_gss.py``) + the crosswalk.
Output: the deposit parquet (deterministic ORDER BY before COPY, §3).

    uv run python etl/build_gss_support.py
"""
from __future__ import annotations
import csv, glob, os, re
from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parent.parent
CSV_GLOB = str(ROOT / "data" / "raw" / "gss" / "csv" / "gss*_support.csv")
XWALK = ROOT / "crosswalks" / "gss" / "support_column_map.csv"
OUT = ROOT / "data" / "harmonized" / "gss_support.parquet"

ID_MAP = {  # source column -> schema column
    "UNITID": "unitid", "Institution_Name": "institution_name",
    "school_id": "gss_school_id", "gss_code": "gss_code", "hdg_code": "hdg_code",
    "institution_state": "state", "hbcu_flag": "hbcu_flag",
    "land_grant_flag": "land_grant_flag",
}


def crosswalk_columns(con) -> set[str]:
    con.execute(f"CREATE OR REPLACE TABLE xwalk AS "
                f"SELECT * FROM read_csv('{XWALK.as_posix()}', header=true, all_varchar=true)")
    return {r[0] for r in con.execute("SELECT source_column FROM xwalk").fetchall()}


def build_year(con, path: str, xcols: set[str]) -> int:
    year = int(re.search(r"(\d{4})", os.path.basename(path)).group(1))
    era = "pre2017" if year <= 2016 else "post2017"
    with open(path, encoding="utf-8") as fh:
        header = next(csv.reader(fh))
    measure = [c for c in header if c in xcols]
    con.execute(f"CREATE OR REPLACE TABLE raw AS "
                f"SELECT * FROM read_csv('{Path(path).as_posix()}', header=true, all_varchar=true)")
    on_list = ", ".join(f'"{c}"' for c in measure)
    id_sel = ", ".join(f'"{src}"' for src in ID_MAP if src in header)
    # UNPIVOT measure columns -> (source_column, value); keep id columns.
    con.execute(f"""
        CREATE OR REPLACE TABLE long_y AS
        SELECT {id_sel}, source_column, value
        FROM (UNPIVOT raw ON {on_list} INTO NAME source_column VALUE value)
        WHERE TRY_CAST(value AS DOUBLE) IS NOT NULL
          AND TRY_CAST(value AS DOUBLE) <> 0
    """)
    # join crosswalk, project to schema, append to result
    sel_ids = ", ".join(f'l."{src}" AS {dst}' for src, dst in ID_MAP.items() if src in header)
    con.execute(f"""
        INSERT INTO panel
        SELECT
          {sel_ids},
          CAST(NULL AS VARCHAR) AS field_coarse, CAST(NULL AS VARCHAR) AS field_fine,
          {year} AS year, '{era}' AS era,
          'full_time' AS enrollment_status,
          x.degree_level, x.gender, x.support_mechanism, x.source_class, x.funding_agency,
          CAST(ROUND(CAST(l.value AS DOUBLE)) AS BIGINT) AS value,
          'headcount' AS unit, 'count' AS value_type, 'reported' AS quality_flag,
          'Support' AS source_sheet,
          '{os.path.basename(path)}' AS source_file,
          CAST(NULL AS VARCHAR) AS notes
        FROM long_y l JOIN xwalk x USING (source_column)
    """)
    return con.execute("SELECT COUNT(*) FROM long_y").fetchone()[0]


def main() -> int:
    con = duckdb.connect()
    xcols = crosswalk_columns(con)
    con.execute("""
        CREATE TABLE panel (
          unitid VARCHAR, institution_name VARCHAR, gss_school_id VARCHAR,
          gss_code VARCHAR, hdg_code VARCHAR, state VARCHAR,
          hbcu_flag VARCHAR, land_grant_flag VARCHAR,
          field_coarse VARCHAR, field_fine VARCHAR,
          year BIGINT, era VARCHAR, enrollment_status VARCHAR,
          degree_level VARCHAR, gender VARCHAR, support_mechanism VARCHAR,
          source_class VARCHAR, funding_agency VARCHAR,
          value BIGINT, unit VARCHAR, value_type VARCHAR, quality_flag VARCHAR,
          source_sheet VARCHAR, source_file VARCHAR, notes VARCHAR)
    """)
    total = 0
    for f in sorted(glob.glob(CSV_GLOB)):
        n = build_year(con, f, xcols)
        total += n
    OUT.parent.mkdir(parents=True, exist_ok=True)
    con.execute(f"""
        COPY (SELECT * FROM panel
              ORDER BY unitid, gss_school_id, year, gss_code, hdg_code,
                       degree_level, gender, support_mechanism, source_class,
                       funding_agency, value)
        TO '{OUT.as_posix()}' (FORMAT parquet)
    """)
    rows = con.execute("SELECT COUNT(*) FROM panel").fetchone()[0]
    insts = con.execute("SELECT COUNT(DISTINCT unitid) FROM panel").fetchone()[0]
    yrs = con.execute("SELECT MIN(year), MAX(year) FROM panel").fetchone()
    print(f"Wrote {OUT.relative_to(ROOT)}: {rows:,} rows, {insts} institutions, "
          f"FY{yrs[0]}-{yrs[1]} ({OUT.stat().st_size/1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
