"""
etl/build_herd_personnel.py — HERD personnel sibling panel builder.

Phase 1 deliverable for the personnel sibling deposit (CLAUDE.md §6 paired
Zenodo deposit, W9-10). Builds ``data/harmonized/herd_personnel.parquet``
from Q15 (Headcount of research personnel) and Q16 (Full-time equivalents
of research personnel) microdata.

Scope (this build, draft schema)
--------------------------------
- **Years covered:** 2022, 2023, 2024 (microdata-only this build).
  2020 and 2021 are aggregate-only in the public-use file (no Q15/Q16
  rows in the per-year CSVs); their published aggregates land at Phase 2
  reconciliation against NCSES Data Table 26 (NSF 26-304), if at all.
- **Era:** B-only. Q15/Q16 are era-B questions; no era-A counterpart
  exists. The era flag column is constant 'B' but retained for parallel
  reading with the financial panel.
- **Microdata structure (verified empirically across all three years):**
  ``questionnaire_no in ('15', '16')`` rows carry ``row='Total'`` and
  ``column in {'Researchers', 'Technicians', 'Support Staff', 'Total'}``.
  No discipline axis, no source-of-funds axis, no
  sex/citizenship/education breakdown (FY24 Guide §1.2: demographic
  detail "is not published or released" in the public-use file).

Standard-form-population filtering
----------------------------------
This build does NOT apply the NCSES Data Table 26 standard-form-
population constraint ($1M+ FY23 R&D). Per the dispatch's stop boundary,
the parquet retains every Q15/Q16 row from the microdata; the filter is
applied at Phase 2 reconciliation time only. Keeping the parquet
filter-free preserves three downstream options:
  (a) reconciliation against Table 26 (filtered),
  (b) all-respondents personnel views (unfiltered),
  (c) any future publication that uses a different population definition.

Schema (draft — locked at Phase 2 panel touch)
----------------------------------------------
::

    institution_id              VARCHAR  (era-B inst_id, FICE-style)
    ncses_inst_id               VARCHAR  (era-B identifier)
    ipeds_unitid                VARCHAR  (era-B identifier)
    inst_name_long              VARCHAR  (cold-reader convenience)
    year                        INTEGER  (2022-2024)
    era                         VARCHAR  ('B' constant; parallel with financial)
    measure_type                VARCHAR  ('headcount' or 'fte')
    personnel_function          VARCHAR  ('researchers','technicians',
                                          'support_staff','total')
    value                       DOUBLE   (persons or fte-persons)
    unit                        VARCHAR  ('persons' or 'fte_persons')
    source_questionnaire_no     VARCHAR  ('15' or '16')
    source_question_canonical   VARCHAR  (FY24 Guide canonical label)
    source_question_raw         VARCHAR  (HERD CSV raw label)
    source_file                 VARCHAR  (e.g., 'herd2024.csv')
    notes                       VARCHAR  (nullable; per-row caveats)

Why this schema (not the financial schema)
------------------------------------------
Per CLAUDE.md §6 paired-deposit framing: "Same provenance, same
harmonization decisions, separate artifacts because the question types
don't share a value axis." The personnel schema preserves the spirit of
the financial schema (long format, institution_id, year, era,
source_file) and replaces value-axis columns with personnel-axis
equivalents. Specifically:

  - **Dropped** ``value_type`` (current/constant): not deflatable.
  - **Dropped** ``discipline_coarse``/``discipline_fine``: Q15/Q16 carry
    no discipline axis (row='Total' only).
  - **Dropped** ``source_coarse``/``source_fine``: Q15/Q16 carry no
    source-of-funds axis.
  - **Dropped** ``expenditure_type``: not an expenditure.
  - **Added** ``measure_type`` ('headcount'/'fte') — the personnel value
    axis.
  - **Added** ``personnel_function`` ('researchers'/'technicians'/
    'support_staff'/'total') — the personnel disaggregation axis.

Question-map handling
---------------------
Q15 and Q16 already exist as rows in ``crosswalks/question_map.csv``
(rows 26-27, both ``era-B-attribute,
contributes_to_all_source_total=false``). This builder does NOT
introduce a sibling question-map CSV. The rationale is in the dispatch
report: same registry, same disposition columns, no axis violation. The
existing rows' ``raw_question_label`` field (currently empty) needs
populating with the observed HERD CSV strings ('Headcount of personnel'
for Q15, 'FTEs' for Q16) — same drift pattern as Q5 ('Clinical trials'
vs 'Clinical trial R&D expenditures'). That update is queued as a small
follow-up and surfaced at the Phase 1 boundary.

Author: Skipper, 2026-05-01 (Phase 1 dispatch).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import duckdb

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from etl._load import read_herd_csv, csv_member_for, zip_path_for  # noqa: E402

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

# Microdata year coverage. 2020/2021 are aggregate-only in the public-use file
# (verified empirically by `etl/spikes/probe_q15_q16_structure.py`).
PERSONNEL_MICRODATA_YEARS = (2022, 2023, 2024)

# FY24 Guide canonical question labels (page 6 Q15/Q16 bullets).
Q15_CANONICAL = "Headcount of research personnel"
Q16_CANONICAL = "Full-time equivalents of research personnel"

# Raw HERD CSV question labels observed in 2022/2023/2024 microdata.
# Drift pattern matches Q5 ('Clinical trials' vs canonical 'Clinical trial
# R&D expenditures') — surfaced at HD 2.1.b Diagnostic 2 and recorded in
# crosswalks/question_map.csv.raw_question_label for build-code joins.
Q15_RAW_LABEL = "Headcount of personnel"
Q16_RAW_LABEL = "FTEs"

# Personnel function category mapping. The HERD CSV uses presentation-case
# labels in `column`; we normalize to snake_case enum values for downstream
# joins. 'Total' is preserved as a row (rolled across the three functions);
# downstream code that wants only the disaggregation filters
# personnel_function != 'total'.
FUNCTION_MAP = {
    "Researchers": "researchers",
    "Technicians": "technicians",
    "Support Staff": "support_staff",
    "Total": "total",
}

OUT_PATH = ROOT / "data" / "harmonized" / "herd_personnel.parquet"


# --------------------------------------------------------------------------- #
# Build
# --------------------------------------------------------------------------- #


def build_personnel_panel(
    con: Optional[duckdb.DuckDBPyConnection] = None,
    out_path: Path = OUT_PATH,
) -> Path:
    """Build ``herd_personnel.parquet`` from Q15/Q16 microdata.

    Returns the absolute path of the written parquet.
    """
    if con is None:
        con = duckdb.connect()

    # 1. Load each microdata year, filter to Q15/Q16, register a per-year
    #    relation. Era-A and era-B identifier columns are already aligned by
    #    `read_herd_csv`; we project to the personnel schema explicitly.
    per_year_rels = []
    for year in PERSONNEL_MICRODATA_YEARS:
        rel = read_herd_csv(year, con=con)
        # Source file name (for provenance column). Look up the actual member
        # name inside the year zip rather than reconstructing — protects
        # against the herd_YYYY vs. herdYYYY filename pattern.
        import zipfile

        with zipfile.ZipFile(zip_path_for(year), "r") as zf:
            source_file = csv_member_for(zf, year)

        # Filter to Q15/Q16 only.
        sub = rel.filter("questionnaire_no IN ('15', '16')")

        # Project to the personnel schema. The CASE expressions normalize
        # measure_type, unit, personnel_function, and the canonical/raw
        # question labels.
        projected_sql = f"""
            SELECT
                inst_id            AS institution_id,
                ncses_inst_id,
                ipeds_unitid,
                inst_name_long,
                year,
                era,
                CASE questionnaire_no
                    WHEN '15' THEN 'headcount'
                    WHEN '16' THEN 'fte'
                END AS measure_type,
                CASE "column"
                    WHEN 'Researchers'   THEN 'researchers'
                    WHEN 'Technicians'   THEN 'technicians'
                    WHEN 'Support Staff' THEN 'support_staff'
                    WHEN 'Total'         THEN 'total'
                    ELSE 'UNKNOWN_' || COALESCE("column", 'NULL')
                END AS personnel_function,
                value,
                CASE questionnaire_no
                    WHEN '15' THEN 'persons'
                    WHEN '16' THEN 'fte_persons'
                END AS unit,
                questionnaire_no   AS source_questionnaire_no,
                CASE questionnaire_no
                    WHEN '15' THEN '{Q15_CANONICAL}'
                    WHEN '16' THEN '{Q16_CANONICAL}'
                END AS source_question_canonical,
                question           AS source_question_raw,
                '{source_file}'    AS source_file,
                CAST(NULL AS VARCHAR) AS notes
            FROM ({sub.sql_query()})
        """
        per_year = con.sql(projected_sql)
        per_year_rels.append(per_year)

    # 2. UNION ALL the per-year relations.
    union_sql = " UNION ALL ".join(f"({r.sql_query()})" for r in per_year_rels)
    union_rel = con.sql(union_sql)

    # 3. Sanity assertions before write.
    n_rows = union_rel.aggregate("COUNT(*) AS n").fetchone()[0]
    if n_rows == 0:
        raise RuntimeError(
            "Personnel panel is empty — no Q15/Q16 rows loaded. "
            f"Expected microdata in years {PERSONNEL_MICRODATA_YEARS}."
        )

    # No UNKNOWN_ personnel_function rows (would mean an unexpected column
    # value slipped past our enum mapping).
    n_unknown = union_rel.filter(
        "personnel_function LIKE 'UNKNOWN_%'"
    ).aggregate("COUNT(*) AS n").fetchone()[0]
    if n_unknown > 0:
        raise RuntimeError(
            f"{n_unknown} rows have an unmapped column value. "
            "Inspect raw data and update FUNCTION_MAP / CASE."
        )

    # 4. Write parquet. DuckDB native parquet writer; no pyarrow dependency.
    out_path.parent.mkdir(parents=True, exist_ok=True)
    union_rel.to_parquet(str(out_path))

    return out_path


# --------------------------------------------------------------------------- #
# Sanity-check / report (Phase 1 acceptance)
# --------------------------------------------------------------------------- #


def sanity_report(parquet_path: Path = OUT_PATH) -> None:
    """Print the Phase 1 sanity check against the written parquet."""
    con = duckdb.connect()
    rel = con.read_parquet(str(parquet_path))

    print("=" * 70)
    print(f"herd_personnel.parquet sanity report ({parquet_path})")
    print("=" * 70)

    n_rows = rel.aggregate("COUNT(*) AS n").fetchone()[0]
    print(f"Total rows: {n_rows}")

    print("\n--- Column types ---")
    for r in con.execute(
        f"DESCRIBE SELECT * FROM read_parquet('{parquet_path.as_posix()}')"
    ).fetchall():
        col_name, col_type = r[0], r[1]
        print(f"  {col_name:30s} {col_type}")

    print("\n--- Row counts by year × measure_type ---")
    for r in (
        rel.aggregate(
            "year, measure_type, COUNT(*) AS n",
            group_expr="year, measure_type",
        )
        .order("year, measure_type")
        .fetchall()
    ):
        print(f"  {r[0]}  {r[1]:10s}  n={r[2]}")

    print("\n--- Distinct personnel_function values ---")
    for r in (
        rel.project("personnel_function")
        .distinct()
        .order("personnel_function")
        .fetchall()
    ):
        print(f"  {r[0]!r}")

    print("\n--- Distinct measure_type values ---")
    for r in (
        rel.project("measure_type")
        .distinct()
        .order("measure_type")
        .fetchall()
    ):
        print(f"  {r[0]!r}")

    print("\n--- Distinct unit values ---")
    for r in (
        rel.project("unit").distinct().order("unit").fetchall()
    ):
        print(f"  {r[0]!r}")

    print("\n--- Distinct era values ---")
    for r in (
        rel.project("era").distinct().order("era").fetchall()
    ):
        print(f"  {r[0]!r}")

    print("\n--- Distinct (source_questionnaire_no, source_question_raw, "
          "source_question_canonical) ---")
    for r in (
        rel.project(
            "source_questionnaire_no, source_question_raw, "
            "source_question_canonical"
        )
        .distinct()
        .order("source_questionnaire_no")
        .fetchall()
    ):
        print(f"  qno={r[0]!r}  raw={r[1]!r}  canonical={r[2]!r}")

    print("\n--- Institution coverage by year ---")
    for r in (
        rel.aggregate(
            "year, COUNT(DISTINCT institution_id) AS n_inst",
            group_expr="year",
        )
        .order("year")
        .fetchall()
    ):
        print(f"  {r[0]}  n_distinct_institutions={r[1]}")

    print("\n--- Identifier coverage (era-B only; expect 0 NULLs) ---")
    nulls = rel.aggregate(
        """
        COUNT(*) FILTER (WHERE institution_id IS NULL)        AS null_inst_id,
        COUNT(*) FILTER (WHERE ncses_inst_id  IS NULL)        AS null_ncses,
        COUNT(*) FILTER (WHERE ipeds_unitid   IS NULL)        AS null_ipeds,
        COUNT(*) FILTER (WHERE inst_name_long IS NULL)        AS null_name
        """
    ).fetchone()
    print(f"  null institution_id={nulls[0]}, ncses_inst_id={nulls[1]}, "
          f"ipeds_unitid={nulls[2]}, inst_name_long={nulls[3]}")

    print("\n--- Value column NULL/zero summary ---")
    vsum = rel.aggregate(
        """
        COUNT(*)                            AS total_rows,
        COUNT(*) FILTER (WHERE value IS NULL) AS null_value,
        COUNT(*) FILTER (WHERE value = 0)   AS zero_value,
        MIN(value)                          AS min_value,
        MAX(value)                          AS max_value
        """
    ).fetchone()
    print(f"  total={vsum[0]}, null={vsum[1]}, zero={vsum[2]}, "
          f"min={vsum[3]}, max={vsum[4]}")

    # Cross-check: free-sum of headcount Total across institutions per year
    # (NOT standard-form-filtered — see module docstring). Useful as a
    # back-of-envelope read; Phase 2 will apply the standard-form filter.
    print("\n--- Free-sum (NOT standard-form-filtered): "
          "value where personnel_function='total' ---")
    for r in (
        rel.filter("personnel_function = 'total'")
        .aggregate(
            "year, measure_type, SUM(value) AS total_value, "
            "COUNT(*) AS n_inst",
            group_expr="year, measure_type",
        )
        .order("year, measure_type")
        .fetchall()
    ):
        print(f"  {r[0]}  {r[1]:10s}  free_sum={r[2]:>15,.0f}  "
              f"n_inst_rows={r[3]}")
    print("  NOTE: Phase 2 will apply the Table 26 standard-form filter "
          "($1M+ FY23 R&D); free-sums above are upper bounds, not "
          "reconciliation candidates.")

    print()


def main() -> int:
    out = build_personnel_panel()
    print(f"Wrote {out} ({out.stat().st_size:,} bytes)")
    sanity_report(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
