"""
etl/_load_fedsupport.py — Federal S&E Support (Table 12) loader.

Public entry point:
    ``read_fedsupport_table12(year, con=None) -> duckdb.DuckDBPyRelation``

Dataset #2 of the quadrivium program: NSF *Survey of Federal Science and
Engineering Support to Universities, Colleges, and Nonprofit Institutions*
(Federal S&E Support Survey). This loader reads the **higher-ed-only**
Table 12 ("Federal obligations for science and engineering to universities
and colleges, by state, outlying area, institution, and type of activity").

Why a sibling module (not an extension of ``etl/_load.py``)
-----------------------------------------------------------
The HERD ``UNIFIED_COLS`` schema is question/discipline-grained
(questionnaire_no, row, column, status). Table 12 has no questionnaire grain
and no discipline; it is institution × type-of-activity obligation dollars.
The schemas do not share enough to make one loader carry both cleanly, so
this is a parallel module (HD 3.2 §5 loader-shape disposition — "a sibling
module is likely").

Acquisition contract (CLAUDE.md §3 lock)
----------------------------------------
The staged **CSV** under ``data/raw/fedsupport/`` is the deposit artifact.
It was produced by a ONE-TIME xlsx->CSV conversion at acquisition (the
DuckDB ``excel`` extension is permitted in that one-time step but NOT in
this build path). This loader reads the CSV via ``read_csv_auto`` only — no
runtime extension fetch, no network dependency at build time. The PDF audit
sibling lives in ``data/reference/``. SHA-256s for both are tracked in
``data/raw/MANIFEST.md`` (``fedsupport`` section).

The positional hierarchy (hidden edge §8.1 — the real difficulty)
-----------------------------------------------------------------
Column A nests institution rows under state-header rows by ordering, with a
leading "All states and outlying areas" grand-total row and per-state header
rows interleaved. There is NO row-type column. The parser distinguishes the
three row types with belt-and-suspenders:

  * grand-total row  = literal ``All states and outlying areas``;
  * state-header row = Column A label ∈ a fixed state/outlying-area name set
    (``STATE_NAMES``) AND no other state header has been "closed" mid-line;
  * institution row  = anything else that carries a numeric "All federal
    obligations" value, tagged with the most-recent state header above it.

Get this wrong and you either double-count (summing the grand-total or the
per-state subtotals alongside the institutions) or drop institutions. The
parse-reconciliation receipt
(``validation/reports/fedsupport/fedsupport_parse_reconciliation.md``)
proves the institution-row sum reconciles to the published grand total.

NOTE on per-state subtotals. In Table 12 the per-state header row itself
carries the state subtotal in the value columns (e.g. ``Alabama  879,493``).
The parser tags those as ``row_kind='state_subtotal'`` and they are NOT part
of the returned institution relation — they are returned separately so the
reconciliation receipt can verify grand_total == sum(state_subtotals) ==
sum(institutions) independently.

Emitted long relation (institution rows only)
---------------------------------------------
    year, state, institution_name_raw, ipeds_unitid, activity_type,
    value_kusd, source_table, source_file, quality_flag, notes

``ipeds_unitid`` is left NULL here — it is populated downstream by the
institution-identity spine (``crosswalks/_shared/institution_identity.csv``),
not free-string-matched in the loader (HD 3.2 §2 artifact #4).

``activity_type`` preserves the RAW per-era column label (the vol-71 8->6/
relabel boundary crosswalk is DEFERRED — HD 3.2 §5.2). The era-invariant
``All federal obligations`` column is emitted as ``activity_type='all_obligations'``
with a stable canonical key so the spine + dollar-match receipt run on it
without depending on the deferred taxonomy crosswalk.

FY-basis contract flag (hidden edge §8.5 -> HD 3.6 consumer hazard)
-------------------------------------------------------------------
Every row carries ``notes`` text marking obligations as **federal-FY basis**.
HERD expenditures are institution-FY basis. The seam decomposition is HD 3.6;
this flag exists so no downstream consumer (incl. a Power BI semantic model
built on the parquet) misreads a timing gap as funding-conversion efficiency.

Author: Skipper, 2026-05-29 (HD 3.2 MVP).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import duckdb

ROOT = Path(__file__).resolve().parent.parent
RAW_FEDSUPPORT_DIR = ROOT / "data" / "raw" / "fedsupport"

# (year, report, source_table_label). The staged CSV is
# ``data/raw/fedsupport/{report}-tab012-FY{year}.csv``. Report numbers
# resolved at acquisition (HD 3.1 §7 for FY2020/2021/2023; FY2022 = nsf24326,
# the data-tables companion to InfoBrief NSF 24-325, NCSES survey page).
YEAR_REPORT = {
    2020: "nsf22342",
    2021: "nsf24311",
    2022: "nsf24326",
    2023: "nsf25339",
}

GRAND_TOTAL_LABEL = "All states and outlying areas"

# U.S. states + DC + outlying areas as they head Column A in Table 12.
# Belt-and-suspenders against the positional parse (§8.1). Sourced from the
# spike's verified list; covers the 55 headers observed in FY2023.
STATE_NAMES = {
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado",
    "Connecticut", "Delaware", "District of Columbia", "Florida", "Georgia",
    "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky",
    "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota",
    "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada",
    "New Hampshire", "New Jersey", "New Mexico", "New York", "North Carolina",
    "North Dakota", "Ohio", "Oklahoma", "Oregon", "Pennsylvania",
    "Rhode Island", "South Carolina", "South Dakota", "Tennessee", "Texas",
    "Utah", "Vermont", "Virginia", "Washington", "West Virginia", "Wisconsin",
    "Wyoming",
    # Outlying areas / territories that appear in NCSES state-grouping headers.
    "American Samoa", "Guam", "Northern Mariana Islands", "Puerto Rico",
    "U.S. Virgin Islands", "Virgin Islands", "Federated States of Micronesia",
    "Marshall Islands", "Palau",
}

# Canonical key for the era-invariant total column. The per-era raw labels
# for the OTHER value columns are preserved verbatim (taxonomy crosswalk
# deferred, §5.2); only this one column gets a stable cross-year key, because
# the spine + dollar-match receipt run on it.
ALL_OBLIGATIONS_RAW = "All federal obligations"
ALL_OBLIGATIONS_CANONICAL = "all_obligations"

FY_BASIS_NOTE = (
    "federal-FY obligation basis (NOT institution-FY expenditure basis); "
    "do not free-join to HERD expenditures as same-year-comparable — see HD 3.6 seam"
)

# A trailing run of 1-2 lowercase ASCII letters appended directly to a label
# is an NCSES footnote marker (e.g. FY2023 'Northern Mariana Islandsb' -> the
# 'b' is a footnote). The state-header detector strips such a marker before
# testing against STATE_NAMES, so a footnoted state header is not
# misclassified as an institution row. Belt-and-suspenders: we only treat the
# stripped form as a state header if the STRIPPED label is EXACTLY a known
# state name (a real institution like 'U. Guam' or 'Northern Marianas C.'
# never strips to one). We try stripping 1 then 2 trailing letters so that
# e.g. 'Northern Mariana Islandsb' -> 'Northern Mariana Islands' (strip 'b')
# matches before the over-strip 'Northern Mariana Island' (strip 'sb').
_STATE_NAMES_LOWER = {s.lower() for s in STATE_NAMES}
_STATE_NAMES_BY_LOWER = {s.lower(): s for s in STATE_NAMES}


def _strip_footnote_candidates(label: str):
    """Yield the label and its 1-/2-trailing-lowercase-letter strips, in
    increasing strip length (prefer the shortest strip that matches)."""
    yield label
    if len(label) >= 2 and label[-1].islower() and label[-1].isascii():
        yield label[:-1]
    if (len(label) >= 3 and label[-1].islower() and label[-2].islower()
            and label[-1].isascii() and label[-2].isascii()):
        yield label[:-2]


def _is_state_header(label: str) -> Optional[str]:
    """Return the canonical state name if ``label`` is a state-header row
    (exact match OR a footnote-suffixed match), else None. The footnote case
    is narrow and enumerable: only FY2023 'Northern Mariana Islandsb' was
    observed across FY2020-FY2023 (surfaced during loader development),
    but the strip-and-retest is robust to any future single-/double-letter
    footnote marker on a state header."""
    for cand in _strip_footnote_candidates(label):
        if cand in STATE_NAMES:
            return cand
    return None


def _is_grand_total(label: str) -> bool:
    """True if ``label`` is the grand-total row, tolerating a footnote suffix
    (defensive — none observed FY2020-FY2023, but mirrors _is_state_header)."""
    return any(cand == GRAND_TOTAL_LABEL
               for cand in _strip_footnote_candidates(label))


def csv_path_for(year: int) -> Path:
    """Path to the staged Table 12 CSV (the deposit artifact)."""
    if year not in YEAR_REPORT:
        raise ValueError(
            f"FedSupport year {year} not staged; have {sorted(YEAR_REPORT)}"
        )
    report = YEAR_REPORT[year]
    return RAW_FEDSUPPORT_DIR / f"{report}-tab012-FY{year}.csv"


def _to_kusd(cell) -> Optional[float]:
    """Parse a value cell to kUSD float. Handles scientific notation (the
    xlsx->CSV conversion wrote some grand totals as e.g. ``3.91221522E7``)
    and FY2020's one-decimal precision (``7938.1``). NULL on non-numeric
    (footnote markers, blanks, ``na``)."""
    if cell is None:
        return None
    s = str(cell).strip().replace(",", "")
    if s in ("", "-", "na", "NA", "n/a", "NA "):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _read_raw_rows(con: duckdb.DuckDBPyConnection, csv: Path):
    """Read the staged CSV as all-varchar, header=false (the CSV was written
    headerless from the xlsx range read). Returns (col_names, rows)."""
    p = csv.as_posix()
    con.execute(
        f"CREATE OR REPLACE TEMP TABLE _fs_raw AS "
        f"SELECT * FROM read_csv_auto('{p}', header=false, all_varchar=true)"
    )
    rows = con.execute("SELECT * FROM _fs_raw").fetchall()
    cols = [r[0] for r in con.execute("DESCRIBE _fs_raw").fetchall()]
    return cols, rows


def _locate_header(rows):
    """Find the header band row and the value-column labels. Returns
    (header_row_index, value_col_labels) where value_col_labels[j] is the
    raw activity label for column index j (j>=1; index 0 is the label col)."""
    for i, r in enumerate(rows):
        a = "" if r[0] is None else str(r[0]).strip()
        if a.lower().startswith("state, outlying area"):
            labels = {}
            for j in range(1, len(r)):
                lbl = "" if r[j] is None else str(r[j]).strip()
                if lbl:
                    labels[j] = lbl
            return i, labels
    raise RuntimeError(
        "FedSupport Table 12: could not locate the "
        "'State, outlying area, and institution' header band."
    )


def parse_table12(rows):
    """Positional-hierarchy parse (§8.1). Returns a dict with:
      'grand_total'   : float kUSD (the 'All federal obligations' grand total)
      'value_labels'  : {col_index: raw_activity_label}
      'institutions'  : list of (state, name_raw, {col_index: value_kusd})
      'state_subtotals': list of (state, {col_index: value_kusd})
      'n_state_headers': int

    Institution rows are tagged with the most-recent state header. State
    headers (which carry the state subtotal in their value columns) are kept
    separately for the reconciliation receipt; they are NOT institutions.
    """
    header_i, value_labels = _locate_header(rows)
    val_idx = None
    for j, lbl in value_labels.items():
        if lbl.strip().lower().startswith("all federal"):
            val_idx = j
            break
    if val_idx is None:
        val_idx = 1  # first value column fallback

    grand_total = None
    institutions = []
    state_subtotals = []
    cur_state = None
    n_state_headers = 0

    for r in rows[header_i + 1:]:
        a = "" if r[0] is None else str(r[0]).strip()
        if not a:
            continue
        # collect all value cells for this row, keyed by col index
        vals = {}
        for j in value_labels:
            vals[j] = _to_kusd(r[j]) if j < len(r) else None

        if _is_grand_total(a):
            grand_total = vals.get(val_idx)
            continue
        state_canon = _is_state_header(a)
        if state_canon is not None:
            cur_state = state_canon
            n_state_headers += 1
            state_subtotals.append((state_canon, vals))
            continue
        # institution row: a label, a numeric all-obligations value, under a
        # state header. Rows with no numeric value (footnote text) are dropped.
        if vals.get(val_idx) is None:
            continue
        institutions.append((cur_state, a, vals))

    return {
        "grand_total": grand_total,
        "value_labels": value_labels,
        "val_idx": val_idx,
        "institutions": institutions,
        "state_subtotals": state_subtotals,
        "n_state_headers": n_state_headers,
    }


def read_fedsupport_table12(
    year: int,
    con: Optional[duckdb.DuckDBPyConnection] = None,
) -> "duckdb.DuckDBPyRelation":
    """Read one year of Federal S&E Support Table 12 into a long relation.

    Returns a DuckDB relation with columns (institution rows only):

        year, state, institution_name_raw, ipeds_unitid, activity_type,
        value_kusd, source_table, source_file, quality_flag, notes

    One row per (institution, activity_type). ``ipeds_unitid`` is NULL
    (populated downstream by the identity spine). ``activity_type`` is the
    canonical ``all_obligations`` for the era-invariant total column and the
    RAW per-era label for every other value column (taxonomy crosswalk
    deferred, §5.2). Every row carries the federal-FY-basis ``notes`` flag.
    """
    csv = csv_path_for(year)
    if not csv.exists():
        raise FileNotFoundError(
            f"Staged FedSupport CSV not found: {csv}. See "
            "data/raw/MANIFEST.md `fedsupport` section to re-stage."
        )
    if con is None:
        con = duckdb.connect()

    _, rows = _read_raw_rows(con, csv)
    parsed = parse_table12(rows)
    value_labels = parsed["value_labels"]
    source_file = csv.name
    source_table = f"{YEAR_REPORT[year]}-Table12-FY{year}"

    # Build a long VALUES list: one row per (institution, activity column).
    records = []
    for state, name_raw, vals in parsed["institutions"]:
        for j, raw_label in value_labels.items():
            v = vals.get(j)
            if v is None:
                continue  # skip empty cells; keeps the relation tight
            if raw_label.strip() == ALL_OBLIGATIONS_RAW:
                activity_type = ALL_OBLIGATIONS_CANONICAL
            else:
                # preserve raw per-era label verbatim (taxonomy crosswalk
                # deferred); namespace it so a consumer knows it is unmapped.
                activity_type = f"raw:{raw_label}"
            records.append(
                (year, state, name_raw, None, activity_type, float(v),
                 source_table, source_file, "reported", FY_BASIS_NOTE)
            )

    con.execute(
        """CREATE OR REPLACE TEMP TABLE _fs_long (
               year INTEGER, state VARCHAR, institution_name_raw VARCHAR,
               ipeds_unitid VARCHAR, activity_type VARCHAR, value_kusd DOUBLE,
               source_table VARCHAR, source_file VARCHAR,
               quality_flag VARCHAR, notes VARCHAR
           )"""
    )
    con.executemany(
        "INSERT INTO _fs_long VALUES (?,?,?,?,?,?,?,?,?,?)", records
    )
    return con.sql("SELECT * FROM _fs_long")
