"""
etl/_load.py — single-year HERD CSV loader.

Public entry point: ``read_herd_csv(year, con=None) -> duckdb.DuckDBPyRelation``.

Responsibilities (HD 1.2):

- Read the staged year zip from ``data/raw/herd/`` directly. Do NOT extract
  the CSV permanently to disk under the project tree (provenance lives in
  the zip; see ``data/raw/MANIFEST.md``).
- Accept both filename patterns inside the zip: ``herd_YYYY.csv`` (1972-2015)
  and ``herdYYYY.csv`` (2016-2024).
- Unify era-A (1972-2009, 20 cols, ``fice`` ID) and era-B (2010-2024,
  23 cols, ``inst_id`` + ``ncses_inst_id`` + ``ipeds_unitid``) into a single
  long-format DuckDB relation with stable column order. Era-A rows carry
  NULLs in era-B-only columns; era-A's ``inst_state`` is mapped to
  ``inst_state_code`` so downstream code sees one name.
- Apply the ``questionnaire_no`` non-data row filter documented in
  ``data/raw/INVENTORY.md`` §5.1 — drop rows whose ``questionnaire_no``
  matches a US state code (``^[A-Z]{2}$``) or a ZIP-like pattern
  (``^\\d{5}(-\\d{4})?$``). These are tracking/footnote rows keyed by
  institution location, not science data.
- Cast ``data`` to ``DOUBLE`` as ``value`` (NULL-on-fail) but preserve the
  raw ``data`` text and ``status`` verbatim per INVENTORY §7.

Returns a long DuckDB relation. Does NOT pivot. Caller composes further.

Example (REPL)::

    >>> from etl._load import read_herd_csv
    >>> rel_2024 = read_herd_csv(2024)
    >>> rel_2024.aggregate("COUNT(*) AS n").fetchone()
    (264321,)  # or thereabouts; HD 1.2 light test wants > 0

In-memory extraction note
-------------------------
DuckDB on Windows cannot read CSV members directly from inside a zip.
``read_herd_csv`` extracts the CSV bytes from the year zip into the OS
temporary directory (``tempfile.NamedTemporaryFile``), points DuckDB's
``read_csv_auto`` at that path, materializes the rows into an in-memory
DuckDB table, then deletes the temp file. No extracted CSV ever lands
inside the project tree. The temp file's lifetime is bounded by the
``with`` block; on cleanup the OS temp dir reclaims it.

Author: Skipper, 2026-04-29 (HD 1.2).
"""

from __future__ import annotations

import csv as _csv
import re
import tempfile
import zipfile
from pathlib import Path
from typing import Optional

import duckdb

# --------------------------------------------------------------------------- #
# Paths and constants
# --------------------------------------------------------------------------- #

ROOT = Path(__file__).resolve().parent.parent
RAW_HERD_DIR = ROOT / "data" / "raw" / "herd"
RAW_HERD_SHORT_FORM_DIR = ROOT / "data" / "raw" / "herd" / "short_form"
ENCODING_LOG_PATH = ROOT / "validation" / "reports" / "encoding_substitutions.csv"
_ENCODING_LOG_FIELDS = (
    "source_file",
    "row_number",
    "byte_offset",
    "original_bytes",
    "latin1_character",
)

ERA_A_LAST = 2009  # 1972-2009 use the 20-col `fice` schema
ERA_B_FIRST = 2010  # 2010-2024 use the 23-col `inst_id` schema
YEAR_MIN = 1972
YEAR_MAX = 2024

# Era-A schema (1972-2009): 20 cols.
ERA_A_COLS = (
    "fice",
    "fice_combined",
    "year",
    "hbcu_flag",
    "has_med_sch_flag",
    "hhe_flag",
    "toi_code",
    "hdg_code",
    "toc_code",
    "pilot_fy09_flag",
    "inst_name_long",
    "inst_city",
    "inst_state",
    "inst_zip",
    "questionnaire_no",
    "question",
    "row",
    "column",
    "data",
    "status",
)

# Era-B schema (2010-2024): 23 cols.
ERA_B_COLS = (
    "inst_id",
    "year",
    "ncses_inst_id",
    "ipeds_unitid",
    "hbcu_flag",
    "med_sch_flag",
    "hhe_flag",
    "toi_code",
    "hdg_code",
    "toc_code",
    "inst_name_long",
    "inst_city",
    "inst_state_code",
    "inst_zip",
    "questionnaire_no",
    "question",
    "row",
    "column",
    "data",
    "status",
    "othinfo",
    "othinfo_s",
    "standardized_agency_names",
)

# Short-form schema (FY 2012-2024): 21 cols. Same as ERA_B_COLS minus
# `othinfo_s` and `standardized_agency_names`. Short-form files publish
# in `data/raw/herd/short_form/` as `higher_education_r_and_d_{year}_short.zip`
# containing `short{year}.csv`. Confirmed empirically across FY 2012/2017/2024
# (probe `etl/spikes/probe_short_form_structure.py`, HD 2.4.b round 1,
# 2026-05-10). Era classification: short-form rows are era 'B' (added FY
# 2012, contemporary with the era-B redesign that introduced the short-form
# instrument).
SHORT_FORM_COLS = (
    "inst_id",
    "year",
    "ncses_inst_id",
    "ipeds_unitid",
    "hbcu_flag",
    "med_sch_flag",
    "hhe_flag",
    "toi_code",
    "hdg_code",
    "toc_code",
    "inst_name_long",
    "inst_city",
    "inst_state_code",
    "inst_zip",
    "questionnaire_no",
    "question",
    "row",
    "column",
    "data",
    "status",
    "othinfo",
)
SHORT_FORM_YEAR_MIN = 2012
SHORT_FORM_YEAR_MAX = 2024

# Unified column order returned by read_herd_csv. Era determines whether
# era-only columns are populated or NULL.
UNIFIED_COLS = (
    "year",
    "era",                       # 'A' or 'B'
    "inst_id",                   # era B; for era A, copy of fice
    "fice",                      # era A only; NULL in era B (era B inst_id is FICE-style)
    "ncses_inst_id",             # era B only
    "ipeds_unitid",              # era B only
    "fice_combined",             # era A only
    "hbcu_flag",
    "med_sch_flag",              # unified name: era A 'has_med_sch_flag' -> 'med_sch_flag'
    "hhe_flag",
    "toi_code",
    "hdg_code",
    "toc_code",
    "pilot_fy09_flag",           # era A only; NULL in era B
    "inst_name_long",
    "inst_city",
    "inst_state_code",           # unified name: era A 'inst_state' -> 'inst_state_code'
    "inst_zip",
    "questionnaire_no",
    "question",
    "row",
    "column",
    "data",                      # raw text, preserved verbatim
    "status",                    # raw text, preserved verbatim
    "othinfo",                   # era B only; NULL in era A
    "othinfo_s",                 # era B only; NULL in era A
    "standardized_agency_names", # era B only; NULL in era A
    "value",                     # TRY_CAST(data AS DOUBLE)
)

# Non-data questionnaire_no filter — INVENTORY §5.1.
# State-code shape: exactly 2 uppercase ASCII letters (AL, CA, TX, ...).
# ZIP shape: 5 digits, optionally followed by -4 digits (06106, 06106-2791).
_NONDATA_QNO_RE = re.compile(r"^[A-Z]{2}$|^\d{5}(-\d{4})?$")


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #


def is_nondata_questionnaire_no(value: str) -> bool:
    """Return True if ``value`` matches the non-data row pattern (state or ZIP)."""
    if value is None:
        return False
    return bool(_NONDATA_QNO_RE.match(value))


def _scan_invalid_utf8_bytes(raw_bytes: bytes) -> list[dict]:
    """Return one record per byte-range that fails UTF-8 decoding.

    Walks ``raw_bytes`` greedily: on each ``UnicodeDecodeError`` records the
    failing range (``start..end`` from the exception) and resumes scanning
    from ``end``. Each record carries the absolute byte offset, the 1-indexed
    CSV row number (newline-counted), the original bytes (hex), and the
    Latin-1 character that the byte will decode to under the fallback.

    Empty list ⇒ ``raw_bytes`` is valid UTF-8.
    """
    substitutions: list[dict] = []
    pos = 0
    n = len(raw_bytes)
    while pos < n:
        try:
            raw_bytes[pos:].decode("utf-8")
            break
        except UnicodeDecodeError as e:
            bad_start = pos + e.start
            bad_end = pos + e.end
            bad_bytes = raw_bytes[bad_start:bad_end]
            row = raw_bytes[:bad_start].count(b"\n") + 1
            substitutions.append(
                {
                    "row_number": row,
                    "byte_offset": bad_start,
                    "original_bytes": "0x" + bad_bytes.hex().upper(),
                    "latin1_character": bad_bytes.decode("latin-1"),
                }
            )
            pos = bad_end
    return substitutions


# Per-process state for the encoding log. The panel build reads each raw CSV
# multiple times (≈6 `load_year` call sites across stages) and the build may be
# re-run; both duplicate substitution rows. Append mode (the prior behavior)
# accumulated across runs unboundedly. We therefore (a) truncate the log on the
# first write of each process and (b) dedup rows within the process, so the log
# is a deterministic function of the input set — one row per distinct
# (source_file, row, offset, byte) substitution, in first-seen order — and
# byte-identical across re-runs. See PANEL_SKIPPER.md §8 HD 2.4.h.
_encoding_log_initialized = False
_encoding_log_seen: set[tuple] = set()


def _reset_encoding_log_state() -> None:
    """Reset per-process encoding-log state. Test hook; normal runs reset on
    fresh interpreter start."""
    global _encoding_log_initialized
    _encoding_log_initialized = False
    _encoding_log_seen.clear()


def _append_encoding_log(source_file: str, substitutions: list[dict]) -> None:
    """Write substitution records to ``validation/reports/encoding_substitutions.csv``.

    Deterministic per build. The first write of the process truncates the file
    and writes the header; subsequent writes append. Rows are deduplicated
    within the process against ``_encoding_log_seen``, so the build's repeated
    reads of the same raw file do not multiply rows. No-op if ``substitutions``
    is empty or contributes no new rows. The committed log is therefore a
    function of the input set only — byte-identical across re-runs.

    Note: the personnel build reads only clean (UTF-8-valid) years and produces
    no substitutions, so it never truncates this log. If a future build path
    produced substitutions for a different input set, the first such write of
    that process would re-truncate; the log reflects one process's input set.
    """
    if not substitutions:
        return
    global _encoding_log_initialized
    path = ENCODING_LOG_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    new_rows = []
    for s in substitutions:
        key = (
            source_file,
            s["row_number"],
            s["byte_offset"],
            s["original_bytes"],
            s["latin1_character"],
        )
        if key in _encoding_log_seen:
            continue
        _encoding_log_seen.add(key)
        new_rows.append(s)
    if not new_rows:
        return
    mode = "a" if _encoding_log_initialized else "w"
    with path.open(mode, newline="", encoding="utf-8") as f:
        writer = _csv.DictWriter(f, fieldnames=_ENCODING_LOG_FIELDS)
        if not _encoding_log_initialized:
            writer.writeheader()
            _encoding_log_initialized = True
        for s in new_rows:
            writer.writerow({"source_file": source_file, **s})


def _decode_with_fallback(raw_bytes: bytes, source_file: str) -> bytes:
    """UTF-8 first; on failure, fall back to Latin-1 and log the substitutions.

    Returns UTF-8-encoded bytes ready to hand to DuckDB. The byte stream is
    preserved (Latin-1 is byte-preserving 1:1) — re-encoding to UTF-8 only
    changes how the high bytes are represented, not which characters they map
    to. Every substituted byte is logged to ``ENCODING_LOG_PATH`` with its
    original byte value, so a future reader can reconstruct the original.
    """
    try:
        raw_bytes.decode("utf-8")
        return raw_bytes
    except UnicodeDecodeError:
        pass
    substitutions = _scan_invalid_utf8_bytes(raw_bytes)
    _append_encoding_log(source_file, substitutions)
    return raw_bytes.decode("latin-1").encode("utf-8")


def zip_path_for(year: int) -> Path:
    """Path to the staged year zip. Filename pattern is constant 1972-2024."""
    if year < YEAR_MIN or year > YEAR_MAX:
        raise ValueError(f"year {year} outside HERD coverage [{YEAR_MIN}, {YEAR_MAX}]")
    return RAW_HERD_DIR / f"higher_education_r_and_d_{year}.zip"


def csv_member_for(zf: zipfile.ZipFile, year: int) -> str:
    """Return the CSV member name inside ``zf``.

    Handles both filename patterns documented in INVENTORY §2:
    ``herd_YYYY.csv`` (1972-2015) and ``herdYYYY.csv`` (2016-2024).
    Falls back to scanning the namelist if neither exact name is present.
    """
    candidates = [f"herd_{year}.csv", f"herd{year}.csv"]
    for name in candidates:
        if name in zf.namelist():
            return name
    # Defensive fallback: any .csv member that mentions the year.
    for name in zf.namelist():
        if name.lower().endswith(".csv") and str(year) in name:
            return name
    raise FileNotFoundError(
        f"No CSV member found in {zf.filename!r} for year {year}; "
        f"members were: {zf.namelist()}"
    )


def _era_for(year: int) -> str:
    return "A" if year <= ERA_A_LAST else "B"


def read_herd_csv(
    year: int,
    con: Optional[duckdb.DuckDBPyConnection] = None,
) -> duckdb.DuckDBPyRelation:
    """Read one year of HERD CSV into a unified DuckDB relation.

    Parameters
    ----------
    year : int
        4-digit fiscal year, 1972..2024.
    con : duckdb.DuckDBPyConnection, optional
        Existing DuckDB connection to register the table on. If None, a new
        in-memory connection is created and returned with the relation; the
        connection is owned by the relation's lifetime and will be cleaned
        up by Python's GC. Pass an explicit connection if you intend to
        accumulate multiple years.

    Returns
    -------
    duckdb.DuckDBPyRelation
        Long-format relation with stable column order ``UNIFIED_COLS``.
        Non-data questionnaire rows are filtered out.
    """
    zip_p = zip_path_for(year)
    if not zip_p.exists():
        raise FileNotFoundError(
            f"Staged zip not found: {zip_p}. See data/raw/MANIFEST.md to re-stage."
        )

    if con is None:
        con = duckdb.connect()  # in-memory

    era = _era_for(year)

    # Extract the CSV member to a tempfile, register it, then drop the file.
    # We materialize the CSV into an in-memory DuckDB table inside this
    # function so the temp file is no longer needed by the time we return.
    # Pre-2015 federal survey CSVs occasionally carry Windows-1252 high
    # bytes (e.g., the curly apostrophe 0x92 in "Veteran's") that fail
    # UTF-8 decoding; ``_decode_with_fallback`` retries as Latin-1 and
    # logs each substituted byte to ``validation/reports/encoding_substitutions.csv``.
    with zipfile.ZipFile(zip_p, "r") as zf:
        member = csv_member_for(zf, year)
        raw_bytes = _decode_with_fallback(zf.read(member), source_file=member)
        with tempfile.NamedTemporaryFile(
            suffix=f"_herd_{year}.csv",
            delete=False,
        ) as tmp:
            tmp_path = Path(tmp.name)
            tmp.write(raw_bytes)

    try:
        # Read everything as VARCHAR first so we don't lose precision or
        # mis-parse mixed-format columns; cast to value at projection time.
        # Era-specific column lists ensure we don't depend on header order.
        if era == "A":
            select_clause = _era_a_select_clause()
            era_cols = ERA_A_COLS
        else:
            select_clause = _era_b_select_clause()
            era_cols = ERA_B_COLS

        # Note on read_csv_auto: HERD CSVs are clean enough that header=True
        # plus all_varchar=True gives stable parses across all 53 years
        # (verified empirically by the discipline-rename spike).
        con.execute(
            f"""
            CREATE OR REPLACE TEMP TABLE _herd_raw_{year} AS
            SELECT * FROM read_csv_auto(
                '{tmp_path.as_posix()}',
                header=True,
                all_varchar=True
            )
            """
        )

        # Sanity-check column count matches era expectation. If not, the
        # CSV header drifted from inventory; surface it loudly rather than
        # producing silently mis-aligned columns.
        actual_cols = [
            r[0]
            for r in con.execute(
                f"DESCRIBE _herd_raw_{year}"
            ).fetchall()
        ]
        if len(actual_cols) != len(era_cols):
            raise RuntimeError(
                f"HERD {year} ({zip_p.name}): expected {len(era_cols)} columns "
                f"({era_cols}), got {len(actual_cols)} ({actual_cols}). "
                "Update etl/_load.py if the upstream schema changed."
            )

        # Project to unified schema with the questionnaire_no row filter.
        # Use a regex match in DuckDB; mirrors `_NONDATA_QNO_RE`.
        unified_sql = f"""
            SELECT {select_clause}
            FROM _herd_raw_{year}
            WHERE NOT regexp_matches(
                COALESCE(questionnaire_no, ''),
                '^[A-Z]{{2}}$|^\\d{{5}}(-\\d{{4}})?$'
            )
        """
        rel = con.sql(unified_sql)
        # Force the column order one more time so callers can rely on it.
        # Double-quote identifiers to dodge DuckDB keyword collisions
        # (`row`, `column` are SQL reserved-ish words).
        quoted = ", ".join(f'"{c}"' for c in UNIFIED_COLS)
        return rel.project(quoted)
    finally:
        try:
            tmp_path.unlink()
        except OSError:
            # Best-effort cleanup; OS temp dir handles strays.
            pass


# --------------------------------------------------------------------------- #
# Era-specific projection SQL
# --------------------------------------------------------------------------- #


def _era_a_select_clause() -> str:
    """Project era-A raw cols to UNIFIED_COLS, NULLing era-B-only fields."""
    return """
        TRY_CAST(year AS INTEGER)        AS year,
        'A'                              AS era,
        CAST(fice AS VARCHAR)            AS inst_id,
        CAST(fice AS VARCHAR)            AS fice,
        CAST(NULL AS VARCHAR)            AS ncses_inst_id,
        CAST(NULL AS VARCHAR)            AS ipeds_unitid,
        CAST(fice_combined AS VARCHAR)   AS fice_combined,
        CAST(hbcu_flag AS VARCHAR)       AS hbcu_flag,
        CAST(has_med_sch_flag AS VARCHAR) AS med_sch_flag,
        CAST(hhe_flag AS VARCHAR)        AS hhe_flag,
        CAST(toi_code AS VARCHAR)        AS toi_code,
        CAST(hdg_code AS VARCHAR)        AS hdg_code,
        CAST(toc_code AS VARCHAR)        AS toc_code,
        CAST(pilot_fy09_flag AS VARCHAR) AS pilot_fy09_flag,
        CAST(inst_name_long AS VARCHAR)  AS inst_name_long,
        CAST(inst_city AS VARCHAR)       AS inst_city,
        CAST(inst_state AS VARCHAR)      AS inst_state_code,
        CAST(inst_zip AS VARCHAR)        AS inst_zip,
        CAST(questionnaire_no AS VARCHAR) AS questionnaire_no,
        CAST(question AS VARCHAR)        AS question,
        CAST("row" AS VARCHAR)           AS "row",
        CAST("column" AS VARCHAR)        AS "column",
        CAST(data AS VARCHAR)            AS data,
        CAST(status AS VARCHAR)          AS status,
        CAST(NULL AS VARCHAR)            AS othinfo,
        CAST(NULL AS VARCHAR)            AS othinfo_s,
        CAST(NULL AS VARCHAR)            AS standardized_agency_names,
        TRY_CAST(data AS DOUBLE)         AS value
    """


def _era_b_select_clause() -> str:
    """Project era-B raw cols to UNIFIED_COLS, NULLing era-A-only fields."""
    return """
        TRY_CAST(year AS INTEGER)        AS year,
        'B'                              AS era,
        CAST(inst_id AS VARCHAR)         AS inst_id,
        CAST(NULL AS VARCHAR)            AS fice,
        CAST(ncses_inst_id AS VARCHAR)   AS ncses_inst_id,
        CAST(ipeds_unitid AS VARCHAR)    AS ipeds_unitid,
        CAST(NULL AS VARCHAR)            AS fice_combined,
        CAST(hbcu_flag AS VARCHAR)       AS hbcu_flag,
        CAST(med_sch_flag AS VARCHAR)    AS med_sch_flag,
        CAST(hhe_flag AS VARCHAR)        AS hhe_flag,
        CAST(toi_code AS VARCHAR)        AS toi_code,
        CAST(hdg_code AS VARCHAR)        AS hdg_code,
        CAST(toc_code AS VARCHAR)        AS toc_code,
        CAST(NULL AS VARCHAR)            AS pilot_fy09_flag,
        CAST(inst_name_long AS VARCHAR)  AS inst_name_long,
        CAST(inst_city AS VARCHAR)       AS inst_city,
        CAST(inst_state_code AS VARCHAR) AS inst_state_code,
        CAST(inst_zip AS VARCHAR)        AS inst_zip,
        CAST(questionnaire_no AS VARCHAR) AS questionnaire_no,
        CAST(question AS VARCHAR)        AS question,
        CAST("row" AS VARCHAR)           AS "row",
        CAST("column" AS VARCHAR)        AS "column",
        CAST(data AS VARCHAR)            AS data,
        CAST(status AS VARCHAR)          AS status,
        CAST(othinfo AS VARCHAR)         AS othinfo,
        CAST(othinfo_s AS VARCHAR)       AS othinfo_s,
        CAST(standardized_agency_names AS VARCHAR) AS standardized_agency_names,
        TRY_CAST(data AS DOUBLE)         AS value
    """


def _short_form_select_clause() -> str:
    """Project short-form raw cols to UNIFIED_COLS.

    Short-form schema is era-B 23-col minus `othinfo_s` and
    `standardized_agency_names`; both project as NULL. Era is 'B'.
    `pilot_fy09_flag`, `fice`, and `fice_combined` project as NULL
    (era-A-only fields).
    """
    return """
        TRY_CAST(year AS INTEGER)        AS year,
        'B'                              AS era,
        CAST(inst_id AS VARCHAR)         AS inst_id,
        CAST(NULL AS VARCHAR)            AS fice,
        CAST(ncses_inst_id AS VARCHAR)   AS ncses_inst_id,
        CAST(ipeds_unitid AS VARCHAR)    AS ipeds_unitid,
        CAST(NULL AS VARCHAR)            AS fice_combined,
        CAST(hbcu_flag AS VARCHAR)       AS hbcu_flag,
        CAST(med_sch_flag AS VARCHAR)    AS med_sch_flag,
        CAST(hhe_flag AS VARCHAR)        AS hhe_flag,
        CAST(toi_code AS VARCHAR)        AS toi_code,
        CAST(hdg_code AS VARCHAR)        AS hdg_code,
        CAST(toc_code AS VARCHAR)        AS toc_code,
        CAST(NULL AS VARCHAR)            AS pilot_fy09_flag,
        CAST(inst_name_long AS VARCHAR)  AS inst_name_long,
        CAST(inst_city AS VARCHAR)       AS inst_city,
        CAST(inst_state_code AS VARCHAR) AS inst_state_code,
        CAST(inst_zip AS VARCHAR)        AS inst_zip,
        CAST(questionnaire_no AS VARCHAR) AS questionnaire_no,
        CAST(question AS VARCHAR)        AS question,
        CAST("row" AS VARCHAR)           AS "row",
        CAST("column" AS VARCHAR)        AS "column",
        CAST(data AS VARCHAR)            AS data,
        CAST(status AS VARCHAR)          AS status,
        CAST(othinfo AS VARCHAR)         AS othinfo,
        CAST(NULL AS VARCHAR)            AS othinfo_s,
        CAST(NULL AS VARCHAR)            AS standardized_agency_names,
        TRY_CAST(data AS DOUBLE)         AS value
    """


# --------------------------------------------------------------------------- #
# Short-form public API
# --------------------------------------------------------------------------- #


def short_form_zip_path_for(year: int) -> Path:
    """Path to the staged short-form year zip.

    Naming convention `higher_education_r_and_d_{year}_short.zip` in
    `data/raw/herd/short_form/`. Per `data/raw/MANIFEST.md` short-form
    section (staged 2026-05-10 per Vision Option (b) disposition).
    """
    if year < SHORT_FORM_YEAR_MIN or year > SHORT_FORM_YEAR_MAX:
        raise ValueError(
            f"short-form year {year} outside coverage "
            f"[{SHORT_FORM_YEAR_MIN}, {SHORT_FORM_YEAR_MAX}]"
        )
    return (
        RAW_HERD_SHORT_FORM_DIR
        / f"higher_education_r_and_d_{year}_short.zip"
    )


def short_form_csv_member_for(zf: zipfile.ZipFile, year: int) -> str:
    """Return the short-form CSV member name inside ``zf``.

    Empirical convention from FY 2012/2017/2024 probe
    (`etl/spikes/probe_short_form_structure.py`, 2026-05-10): the member
    is `short{year}.csv`. Falls back to scanning the namelist if the
    naming convention drifts.
    """
    candidates = [f"short{year}.csv", f"short_{year}.csv"]
    for name in candidates:
        if name in zf.namelist():
            return name
    for name in zf.namelist():
        if name.lower().endswith(".csv") and str(year) in name:
            return name
    raise FileNotFoundError(
        f"No short-form CSV member found in {zf.filename!r} for year "
        f"{year}; members were: {zf.namelist()}"
    )


def read_herd_short_form_csv(
    year: int,
    con: Optional[duckdb.DuckDBPyConnection] = None,
) -> duckdb.DuckDBPyRelation:
    """Read one year of the HERD short-form CSV into a unified DuckDB relation.

    Parallel to `read_herd_csv` but consumes the short-form public-use
    file (`data/raw/herd/short_form/higher_education_r_and_d_{year}_short.zip`,
    coverage FY 2012-2024).

    Schema: 21 raw columns (`SHORT_FORM_COLS`), projected to the same
    `UNIFIED_COLS` returned by `read_herd_csv`. `othinfo_s` and
    `standardized_agency_names` are NULL in the projection (the
    short-form file does not carry these era-B-only columns; the
    unified-schema NULL position preserves cross-form readability).

    Era classification: all rows ship at `era='B'` because short-form
    was added contemporaneously with the era-B redesign (FY 2012).

    Same non-data questionnaire_no filter applies as for standard-form
    (state-code / ZIP pattern rejection per `_NONDATA_QNO_RE`).

    The Latin-1 fallback encoding-substitution discipline applies
    identically; substitutions log to the same
    `validation/reports/encoding_substitutions.csv` artifact.

    Parameters
    ----------
    year : int
        4-digit fiscal year, 2012..2024.
    con : duckdb.DuckDBPyConnection, optional
        Existing DuckDB connection; if None, a new in-memory connection
        is created.

    Returns
    -------
    duckdb.DuckDBPyRelation
        Long-format relation with stable column order ``UNIFIED_COLS``.

    Surfaced. HD 2.4.b round 1 (2026-05-10) per Vision Short-Form-Q2
    Option (b) disposition; maintainer staged the 13 short-form zips
    locally to enable Stage 5 to project `form_type='short'` rows in
    the same atomic commit as the standard-form Stage 5 work.
    """
    zip_p = short_form_zip_path_for(year)
    if not zip_p.exists():
        raise FileNotFoundError(
            f"Short-form zip not found: {zip_p}. See "
            "data/raw/MANIFEST.md `short_form/` section to re-stage."
        )

    if con is None:
        con = duckdb.connect()

    with zipfile.ZipFile(zip_p, "r") as zf:
        member = short_form_csv_member_for(zf, year)
        raw_bytes = _decode_with_fallback(
            zf.read(member), source_file=member
        )
        with tempfile.NamedTemporaryFile(
            suffix=f"_short_{year}.csv",
            delete=False,
        ) as tmp:
            tmp_path = Path(tmp.name)
            tmp.write(raw_bytes)

    try:
        con.execute(
            f"""
            CREATE OR REPLACE TEMP TABLE _short_raw_{year} AS
            SELECT * FROM read_csv_auto(
                '{tmp_path.as_posix()}',
                header=True,
                all_varchar=True
            )
            """
        )

        # Verify column count matches the locked short-form schema.
        actual_cols = [
            r[0]
            for r in con.execute(
                f"DESCRIBE _short_raw_{year}"
            ).fetchall()
        ]
        if len(actual_cols) != len(SHORT_FORM_COLS):
            raise RuntimeError(
                f"HERD short-form {year} ({zip_p.name}): expected "
                f"{len(SHORT_FORM_COLS)} columns ({SHORT_FORM_COLS}), got "
                f"{len(actual_cols)} ({actual_cols}). Update etl/_load.py "
                "SHORT_FORM_COLS if the upstream schema changed."
            )

        unified_sql = f"""
            SELECT {_short_form_select_clause()}
            FROM _short_raw_{year}
            WHERE NOT regexp_matches(
                COALESCE(questionnaire_no, ''),
                '^[A-Z]{{2}}$|^\\d{{5}}(-\\d{{4}})?$'
            )
        """
        rel = con.sql(unified_sql)
        quoted = ", ".join(f'"{c}"' for c in UNIFIED_COLS)
        return rel.project(quoted)
    finally:
        try:
            tmp_path.unlink()
        except OSError:
            pass


# --------------------------------------------------------------------------- #
# Light test (HD 1.2 acceptance) — runnable as a script.
# --------------------------------------------------------------------------- #


def _light_test() -> int:
    """Run the HD 1.2 acceptance test. Returns 0 on pass, 1 on failure."""
    failures: list[str] = []

    # Era-B sanity: 2024.
    try:
        rel_2024 = read_herd_csv(2024)
        cols_2024 = rel_2024.columns
        n_2024 = rel_2024.aggregate("COUNT(*) AS n").fetchone()[0]
        era_2024 = rel_2024.aggregate("MIN(era) AS mn, MAX(era) AS mx").fetchone()
        if n_2024 <= 0:
            failures.append(f"2024 row count not > 0 (got {n_2024})")
        if list(cols_2024) != list(UNIFIED_COLS):
            failures.append(
                f"2024 columns mismatch:\n  got: {cols_2024}\n  exp: {UNIFIED_COLS}"
            )
        if era_2024 != ("B", "B"):
            failures.append(f"2024 era flag should be all 'B', got min/max = {era_2024}")
    except Exception as e:  # noqa: BLE001
        failures.append(f"2024 load raised: {type(e).__name__}: {e}")

    # Era-A sanity: 1995.
    try:
        rel_1995 = read_herd_csv(1995)
        cols_1995 = rel_1995.columns
        n_1995 = rel_1995.aggregate("COUNT(*) AS n").fetchone()[0]
        era_1995 = rel_1995.aggregate("MIN(era) AS mn, MAX(era) AS mx").fetchone()
        # Era-A NULL invariants: ncses_inst_id, ipeds_unitid, othinfo*,
        # standardized_agency_names must all be NULL.
        nulls = rel_1995.aggregate(
            """
            COUNT(*) FILTER (WHERE ncses_inst_id IS NOT NULL) AS bad_ncses,
            COUNT(*) FILTER (WHERE ipeds_unitid  IS NOT NULL) AS bad_ipeds,
            COUNT(*) FILTER (WHERE othinfo       IS NOT NULL) AS bad_othinfo,
            COUNT(*) FILTER (WHERE standardized_agency_names IS NOT NULL) AS bad_stdagency
            """
        ).fetchone()
        if n_1995 <= 0:
            failures.append(f"1995 row count not > 0 (got {n_1995})")
        if list(cols_1995) != list(UNIFIED_COLS):
            failures.append(
                f"1995 columns mismatch:\n  got: {cols_1995}\n  exp: {UNIFIED_COLS}"
            )
        if era_1995 != ("A", "A"):
            failures.append(f"1995 era flag should be all 'A', got min/max = {era_1995}")
        if any(v != 0 for v in nulls):
            failures.append(
                f"1995 era-B-only columns should all be NULL but counts non-null: "
                f"ncses={nulls[0]} ipeds={nulls[1]} othinfo={nulls[2]} stdagency={nulls[3]}"
            )
    except Exception as e:  # noqa: BLE001
        failures.append(f"1995 load raised: {type(e).__name__}: {e}")

    if failures:
        print("FAIL")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("passed")
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(_light_test())
