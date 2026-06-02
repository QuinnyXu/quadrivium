"""
etl/_load_fedsupport.py — Federal S&E Support loader (v3.0 re-base).

Public entry points:
    ``fedsupport_csv_path() -> Path``                 — the staged Build Table CSV
    ``read_fedsupport(con=None) -> duckdb.DuckDBPyRelation``  — long relation
    ``HIGHER_ED_TYPES``, ``FFRDC_TYPES``, ``BROAD_CATEGORIES`` — universe constants

Dataset #2 of the quadrivium program: NSF *Survey of Federal Science and
Engineering Support to Universities, Colleges, and Nonprofit Institutions*.

v3.0 re-base (2026-06-02)
-------------------------
The MVP read the four FY2020–FY2023 Table 12 xlsx slices through a positional
parser. The re-base reads the authoritative **full-series NCSES Build Table
export** — 53 contiguous fiscal years (FY1971–FY2023), a clean RFC-4180
long-format CSV with one row per
``Year × Federal Department × Federal Agency × Broad Category ×
Detailed Category × Institution × IPEDS UnitID × Institution Type × State``.

Per the re-base scope memo (`docs/fedsupport_rebase_scope.md`, authorized
2026-06-01):
  * (b) the Build Table export SUPERSEDES Table 12 as the source; the four
        Table 12 CSVs/PDFs are retained as audit siblings.
  * (e) the loader reads the CSV with **RFC-4180 quoted-CSV parsing**
        (DuckDB ``read_csv_auto``) — NEVER a naive split. A naive comma-split
        field-shifts quoted institution / agency names (the reviewer's
        "Packers and Stockyards Administration" under Broad Category was that
        artifact). The build asserts column integrity (Broad Category ∈ the
        2-value set) before harmonizing.
  * §3 reproducibility: CSV-native, ``read_csv_auto`` only — no runtime
        ``excel`` extension, no network fetch. The xlsx→CSV acquisition lock
        is moot here; the source arrives as CSV.

Identity (a)/(c)
----------------
The export carries a **native IPEDS UnitID column**, populated across all 53
years — there is NO pre-UNITID name-only era. Where IPEDS does not resolve,
the column carries one of three explicit sentinel strings, mapped here to a
first-class ``ipeds_unitid_status`` column:

    numeric                                       -> status='matched',     ipeds_unitid=<n>
    'No match or no exact match for IPEDS UnitID' -> status='no_match',    ipeds_unitid=NULL
    'IPEDS UnitID not applicable to Nonprofits'   -> status='na_nonprofit',ipeds_unitid=NULL
    'IPEDS UnitID not applicable to FFRDCs'       -> status='na_ffrdc',    ipeds_unitid=NULL

The native UNITID supersedes the MVP's name-reconstruction spine (90.2%
academic+consortium dollar coverage vs 73.1%); name-matching is retired for
FedSupport↔IPEDS. See ``etl/build_fedsupport_identity_spine.py``.

Universes
---------
``Detailed Institution Type`` carries six values. The HERD-join universe is
HIGHER_ED_TYPES = {Academic institution, Academic consortium} (reconciles to
the published higher-ed Table 12 anchors). FFRDC_TYPES = {Academic FFRDC,
Nonprofit FFRDC} are a SEPARATE universe, present FY1971–FY1998 only, excluded
from the HERD join by design (they carry the ``na_ffrdc`` sentinel). Nonprofit
{institution, consortium} are carried in the long artifact but are not
higher-ed. Do NOT free-sum across universes (HD 3.1 §2).

Emitted long relation (one row per source row, full grain preserved)
--------------------------------------------------------------------
    fiscal_year, federal_department, federal_agency, broad_category,
    detailed_category, institution_name_raw, ipeds_unitid,
    ipeds_unitid_status, institution_type, state, obligations_kusd,
    source, notes

``obligations_kusd`` is federal-FY-basis (NOT institution-FY expenditure
basis); every row carries the FY-basis ``notes`` flag so no downstream
consumer misreads the timing seam (HD 3.6 Seam A) as funding-conversion
efficiency.

Author: Skipper, 2026-06-02 (v3.0 re-base).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import duckdb

ROOT = Path(__file__).resolve().parent.parent
RAW_FEDSUPPORT_DIR = ROOT / "data" / "raw" / "fedsupport"

# The staged Build Table export. Globbed (the NCSES download carries a
# timestamp in the name); exactly one must be staged for a deterministic build.
FEDSUPPORT_GLOB = "ncses_table_raw_data_FSS_*.csv"

SOURCE_LABEL = "NCSES-FSS-BuildTable-FY1971-FY2023"

# Universes (Detailed Institution Type).
HIGHER_ED_TYPES = ("Academic institution", "Academic consortium")
FFRDC_TYPES = ("Academic FFRDC", "Nonprofit FFRDC")
NONPROFIT_TYPES = ("Nonprofit institution", "Nonprofit consortium")
ALL_INSTITUTION_TYPES = HIGHER_ED_TYPES + FFRDC_TYPES + NONPROFIT_TYPES

# Broad Category is era-invariant across all 53 years (2 values). This is the
# column-integrity invariant the build asserts (e).
BROAD_RD = "Research and development"
BROAD_SUPPORT = "S&E support activities"
BROAD_CATEGORIES = (BROAD_RD, BROAD_SUPPORT)

# UNITID sentinel strings -> status code.
_SENTINEL_STATUS = {
    "No match or no exact match for IPEDS UnitID": "no_match",
    "IPEDS UnitID not applicable to Nonprofits": "na_nonprofit",
    "IPEDS UnitID not applicable to FFRDCs": "na_ffrdc",
}

FY_BASIS_NOTE = (
    "federal-FY obligation basis (NOT institution-FY expenditure basis); "
    "do not free-join to HERD expenditures as same-year-comparable — see HD 3.6 seam"
)


def write_text_clean(path: Path, text: str) -> None:
    """Write a TEXT deposit artifact as UTF-8, LF-only, and ASSERT validity
    after write — zero NUL bytes, decodable UTF-8, no CR.

    Why this exists (reproducible != valid). The determinism gate proves an
    artifact rebuilds byte-identically; it does NOT prove the bytes are valid
    text. A stray PowerShell `>` redirect (UTF-16LE) or a Windows text-mode
    write (CRLF, and LF on Linux — breaking the §3 cross-OS SHA contract) can
    ship a "deterministically corrupt" file straight through the byte-stability
    check. Writing raw bytes here (no platform newline translation) plus a
    read-back assertion closes that gap at the generator. Pre-tag, the
    release-runbook gate sweeps EVERY generated text artifact for the same
    invariant (sibling to the byte-stability discipline)."""
    data = text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    b = path.read_bytes()
    nul = b.count(0)
    if nul:
        raise AssertionError(f"{path}: {nul} NUL byte(s) after write (UTF-16/encoding corruption)")
    b.decode("utf-8")  # raises UnicodeDecodeError if not valid UTF-8
    if b"\r" in b:
        raise AssertionError(f"{path}: CR byte(s) present (expected LF-only)")


def fedsupport_csv_path() -> Path:
    """Resolve the single staged Build Table CSV. Errors if 0 or >1 match,
    so the build is a deterministic function of one named input."""
    matches = sorted(RAW_FEDSUPPORT_DIR.glob(FEDSUPPORT_GLOB))
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise FileNotFoundError(
            f"No FedSupport Build Table CSV ({FEDSUPPORT_GLOB}) under "
            f"{RAW_FEDSUPPORT_DIR}. See data/raw/MANIFEST.md `fedsupport` "
            "section to re-stage (extract from the staged .zip)."
        )
    raise RuntimeError(
        f"Multiple FedSupport Build Table CSVs match {FEDSUPPORT_GLOB}: "
        f"{[m.name for m in matches]}. Exactly one must be staged for a "
        "deterministic build."
    )


def _assert_column_integrity(con: duckdb.DuckDBPyConnection, rel_sql: str) -> None:
    """(e) column-integrity guard — confirm the RFC-4180 parse landed the
    columns correctly before harmonizing. A naive split would scatter quoted
    names into Broad Category; assert Broad Category is exactly the 2-value
    set and that no subtotal rows leaked in (no double-count, per (d))."""
    bad_broad = con.execute(
        f"SELECT DISTINCT broad_category FROM ({rel_sql}) "
        f"WHERE broad_category NOT IN {BROAD_CATEGORIES!r}"
    ).fetchall()
    if bad_broad:
        raise AssertionError(
            "FedSupport column-integrity FAILED: unexpected Broad Category "
            f"value(s) {[b[0] for b in bad_broad]} — likely a CSV field-shift. "
            "The loader must use RFC-4180 quoted parsing (read_csv_auto)."
        )
    subtotal = con.execute(
        f"SELECT COUNT(*) FROM ({rel_sql}) "
        "WHERE lower(detailed_category) LIKE '%total%'"
    ).fetchone()[0]
    if subtotal:
        raise AssertionError(
            f"FedSupport column-integrity FAILED: {subtotal} subtotal-like "
            "detailed-category rows present — summing finest grain would "
            "double-count (d)."
        )
    bad_type = con.execute(
        f"SELECT DISTINCT institution_type FROM ({rel_sql}) "
        f"WHERE institution_type NOT IN {ALL_INSTITUTION_TYPES!r}"
    ).fetchall()
    if bad_type:
        raise AssertionError(
            "FedSupport column-integrity FAILED: unexpected Detailed "
            f"Institution Type value(s) {[b[0] for b in bad_type]}."
        )


def read_fedsupport(con: Optional[duckdb.DuckDBPyConnection] = None) -> "duckdb.DuckDBPyRelation":
    """Read the full-series Build Table export into the harmonized long
    relation. RFC-4180 quoted parse via read_csv_auto (e); native UNITID
    mapped to a first-class status column (a)/(c); column integrity asserted
    before return."""
    csv = fedsupport_csv_path()
    if con is None:
        con = duckdb.connect()
    p = csv.as_posix()

    # CASE expression mapping the native UNITID cell -> (unitid, status).
    sentinel_when = "\n".join(
        f"      WHEN \"IPEDS UnitID\" = '{s}' THEN '{st}'"
        for s, st in _SENTINEL_STATUS.items()
    )
    rel_sql = f"""
        SELECT
          CAST("Fiscal Year" AS INTEGER)            AS fiscal_year,
          "Federal Department"                       AS federal_department,
          "Federal Agency"                           AS federal_agency,
          "Broad Category"                           AS broad_category,
          "Detailed Category"                        AS detailed_category,
          "Institution Name"                         AS institution_name_raw,
          TRY_CAST("IPEDS UnitID" AS BIGINT)         AS ipeds_unitid,
          CASE
            WHEN TRY_CAST("IPEDS UnitID" AS BIGINT) IS NOT NULL THEN 'matched'
{sentinel_when}
            ELSE 'unknown'
          END                                        AS ipeds_unitid_status,
          "Detailed Institution Type"                AS institution_type,
          "State"                                    AS state,
          TRY_CAST("Fed Obligations for S&E" AS DOUBLE) AS obligations_kusd,
          '{SOURCE_LABEL}'                           AS source,
          '{FY_BASIS_NOTE}'                          AS notes
        FROM read_csv_auto('{p}', header=true, all_varchar=true)
    """
    _assert_column_integrity(con, rel_sql)
    # Guard the sentinel map is exhaustive (no 'unknown' status slipped through).
    unknown = con.execute(
        f"SELECT COUNT(*) FROM ({rel_sql}) WHERE ipeds_unitid_status='unknown'"
    ).fetchone()[0]
    if unknown:
        raise AssertionError(
            f"FedSupport loader: {unknown} rows carry an unmapped UNITID "
            "sentinel — extend _SENTINEL_STATUS."
        )
    return con.sql(rel_sql)
