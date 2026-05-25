"""
etl/build_herd_panel.py - HERD financial panel builder (HD 2.4).

Skeleton + Stages 1-3 for HD 2.4.a (round 1 of HD 2.4 implementation).
Stages 4-10 carry signatures only; bodies land in HD 2.4.b through .i per
the §10 timeline in `docs/methods_notes/herd_panel_etl_scoping.md`.

Reads `data/raw/herd/higher_education_r_and_d_{1973..2024}.zip` via
`etl._load.read_herd_csv`, joins discipline crosswalks, and (in HD 2.4.b
onward) writes the era-A direct + era-B reconstructed panel to
`data/harmonized/herd_panel.parquet` with the 20-column schema locked at
the scoping doc §1. Q4/Q5 carve-outs travel as institution-year
attributes in a sibling parquet `data/harmonized/herd_panel_attributes.parquet`.

The implementation contract is the LOCKED scoping doc:
`docs/methods_notes/herd_panel_etl_scoping.md` (locked 2026-05-09). The
era-B reconstruction rule and `quality_flag` propagation ordering are
locked in `crosswalks/era_b_reconstruction_rule.yaml`. Every Stage 1-10
function below references the scoping-doc section that scopes it.

This round (HD 2.4.a):
  - Stages 1, 2, 3 implemented.
  - Stages 4-10 raise NotImplementedError.
  - main() runs Stages 1-3 only via the smoke-test path; full panel
    build is gated on `RUN_STAGES_BEYOND_3 = False` until HD 2.4.b
    onward fills in the bodies.
  - YAML/scoping-doc consistency assertion runs at the top of main()
    before any stage executes (drift defense for the propagation ordering).
  - Smoke-test code is written as `smoke_test_stages_1_3()` but is NOT
    invoked by main() in this round; the maintainer greenlights the
    smoke-test execution after reviewing the skeleton + Stages 1-3.

Author: Skipper, 2026-05-09 (HD 2.4.a round 1).
"""

from __future__ import annotations

import re
import sys
import time
from pathlib import Path
from typing import Optional

import duckdb

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from etl._load import read_herd_csv, read_herd_short_form_csv  # noqa: E402

# --------------------------------------------------------------------------- #
# Module constants (scoping doc §6.1)
# --------------------------------------------------------------------------- #

# Era boundary year (CLAUDE.md §6 era handling). Mirror of `etl._load.ERA_A_LAST`.
ERA_A_LAST_YEAR = 2009

# Field-level panel coverage: 1975-2024 inclusive (50 years).
#
# Three-exclusion audit trail:
#
#   - 1972: no field-level question. FY24 Guide page 16 §2.1.5
#     ("Expenditures by fields of science are not available for FY 1972").
#     Per scoping doc §3(a). Raw zip preserved in `data/raw/herd/`.
#
#   - 1973-1974: Guide-undocumented `status='c'` code on field-level
#     `column='Total'` rows (13 affected cells across the two years; full
#     characterization in `validation/reports/era_a_status_codeset_findings.md`).
#     Carved per Vision verdict 2026-05-10 (Category II option (a)) —
#     codeset extension requires Guide-documented anchor or panel review
#     with explicit semantic anchor (codeset-extension policy locked
#     CLAUDE.md §6 / W4 NULL-handling lock 2026-05-10). Raw zips preserved
#     in `data/raw/herd/` as deposit artifacts; methods-note footnote
#     queued for HD 2.4.i. NCSES historical-publications documentation
#     hunt absorbs into HD 2.4.i (1-half-day budget, non-blocking) — if
#     `'c'` semantic anchor surfaces, quarter-boundary panel review
#     revisits the carve-out.
#
# `build_era_a_rows()` enforces the floor defensively at the function
# level (`if year < PANEL_FIRST_YEAR: continue`) parallel to its existing
# `if year > ERA_A_LAST_YEAR: continue` ceiling.
PANEL_FIRST_YEAR = 1975
PANEL_YEARS = range(PANEL_FIRST_YEAR, 2025)

# FY24 Guide canonical question names (scoping doc §6.1).
ERA_A_FIELD_QUESTION = "Expenditures by S&E field"
ERA_A_EQUIPMENT_QUESTION = "Current fund research equipment expenditures by field"
# Era-A Item 3 raw-vs-canonical drift (same pattern as Q4/Q5/Q14):
# raw HERD CSVs use 'Equipment expenditures by S&E field' across FY
# 1981, 1995, 2009 (probe `etl/spikes/probe_era_a_item_3_label.py`,
# HD 2.4.b round 1 surface 2026-05-10). Crosswalk row 8 carries the
# raw label in the `raw_question_label` column.
ERA_A_EQUIPMENT_QUESTION_RAW = "Equipment expenditures by S&E field"
ERA_B_Q9 = "Federal expenditures by field and agency"
ERA_B_Q11 = "Nonfederal expenditures by field and source"
ERA_B_Q14 = "Capitalized R&D equipment expenditures by field"
ERA_B_Q4 = "Medical school R&D expenditures"
# Q4/Q5/Q14 raw-vs-canonical drift per `crosswalks/question_map.csv` rows
# 15 / 16 / 25: HERD CSVs use abbreviated raw labels while the FY24 Guide
# uses canonical forms. Build code joins on `raw_question_label` when
# populated, falling back to the canonical (HD 2.1.e pattern). Q4 and
# Q14 raw-label drift locked at HD 2.4.a Track 2 (qno suffix semantics
# spike, 2026-05-09). Q9 and Q11 raw labels match canonical per
# crosswalk rows 20 / 22.
ERA_B_Q4_RAW = "Medical school expenditures"
ERA_B_Q5_CANONICAL = "Clinical trial R&D expenditures"
ERA_B_Q5_RAW = "Clinical trials"
ERA_B_Q14_RAW = "Capitalized equipment expenditures by field and source"

# Short Form Q2 — the only short-form question with field-level
# disaggregation. Raw HERD short-form CSVs use 'Expenditures by major
# field and source' (parallel to standard-form Q9/Q11 naming); FY24
# Guide page 6 canonical is 'Short form: R&D expenditures by major
# R&D field'. Drift pattern matches Q4/Q5/Q14/Item-3. Crosswalk row
# 34 carries the raw label in `raw_question_label`; build joins on
# raw_question_label when populated, falling back to canonical. The
# question carries Federal/Nonfederal/Total columns at equal volume
# per (inst, row) triple; column='Total' is the rolled all-source
# value (parallel to standard-form Q14). Row labels are coarse
# `*, all` rollups only (10 buckets + 'All' grand total) — no per-leaf
# disaggregation, by short-form-instrument design.
# Empirical anchor: `etl/spikes/probe_short_form_structure.py`
# confirmed cross-year stable FY 2012/2017/2024. Surfaced at HD 2.4.b
# round 1 (2026-05-10).
SHORT_FORM_Q2_CANONICAL = "Short form: R&D expenditures by major R&D field"
SHORT_FORM_Q2_RAW = "Expenditures by major field and source"

# Short-form year coverage; mirrors `etl._load.SHORT_FORM_YEAR_MIN/MAX`.
SHORT_FORM_FIRST_YEAR = 2012
SHORT_FORM_LAST_YEAR = 2024

# In-scope era-B canonical question labels (scoping doc §6.2 Stage 2,
# HD 2.4.a Track 2 Option 2 lock 2026-05-09). Stage 2 expands these
# canonical labels plus their raw counterparts (via `question_map.csv`
# `raw_question_label`) into the `_xwalk_question_map_in_scope` temp
# table for the SEMI JOIN filter. The qno suffix is fidelity-only — its
# bijection to `row` text makes label-filter and qno-prefix-filter
# strictly redundant per
# `validation/reports/qno_suffix_semantics_findings.md`.
ERA_B_IN_SCOPE_QUESTIONS_CANONICAL = (
    ERA_B_Q4,
    ERA_B_Q5_CANONICAL,
    ERA_B_Q9,
    ERA_B_Q11,
    ERA_B_Q14,
)

# Output paths (scoping doc §6.1).
OUT_PATH = ROOT / "data" / "harmonized" / "herd_panel.parquet"
ATTR_OUT_PATH = ROOT / "data" / "harmonized" / "herd_panel_attributes.parquet"

# Crosswalk paths.
DISCIPLINE_FINE_CSV = ROOT / "crosswalks" / "discipline_fine.csv"
QUESTION_MAP_CSV = ROOT / "crosswalks" / "question_map.csv"
ERA_B_RULE_YAML = ROOT / "crosswalks" / "era_b_reconstruction_rule.yaml"
SCOPING_DOC_MD = ROOT / "docs" / "methods_notes" / "herd_panel_etl_scoping.md"

# --- quality_flag enum + raw-status mapping (scoping doc §1, §6.2) ---------
#
# Mapping from raw HERD CSV `status` to harmonized `quality_flag` enum
# (scoping doc §1 `quality_flag` value semantics, FY24 Guide pages 8 / 23 /
# 10 / 25). Keys are the raw `status` strings emitted by `_load.py` after
# CAST(status AS VARCHAR); blank/NULL is the dominant case (~93-97% of
# in-scope Total-column rows per
# `validation/reports/herd_null_characterization_findings.md`).
#
# **Case-fold note (HD 2.4.b round 1, 2026-05-10).** Pre-1990 era-A raw
# files emit status codes in mixed case ('I' / 'E' alongside 'i' / 'e'),
# freely interleaved within the same file. Vision verdict 2026-05-10
# Category I locked the case-fold: `UPPER(status) IN ('I','E','U')` in
# the CASE expression preserves the locked semantics exactly because
# the FY24 Guide codeset specification is semantic, not lexical. Empirical
# anchor: `validation/reports/era_a_status_codeset_findings.md` Finding 2.
# Methods-note one-liner queued for HD 2.4.i.
#
# Anything not in this mapping must raise loud (scoping doc §6.2 Stage 4
# directive: "anything else -> build raises RuntimeError"). The codeset-
# extension policy locked at HD 2.4.b round 1 (CLAUDE.md §6 W4 NULL-handling
# lock, Vision verdict 2026-05-10 Category II / Item 5) requires a Guide-
# documented semantic anchor or quarter-boundary panel review for any
# extension; empirical surfacing alone is not sufficient grounds.
QUALITY_FLAG_MAP = {
    "i": "imputed",
    "e": "estimated",
    "u": "unspecified_zero",
}
QUALITY_FLAG_REPORTED = "reported"  # blank/NULL status -> reported
QUALITY_FLAG_ENUM = ("reported", "imputed", "estimated", "unspecified_zero")

# Locked propagation ordering (worst -> best) per
# `crosswalks/era_b_reconstruction_rule.yaml` `quality_flag_propagation.ordering`
# (locked 2026-05-09, maintainer-greenlit). The build's runtime ordering
# constant is sourced here for least-good-flag-wins logic at Stage 6;
# `_assert_yaml_doc_consistency()` (called from main() before any stage
# runs) cross-checks this list against both the YAML and the scoping doc
# to defend against drift.
QUALITY_FLAG_ORDERING_WORST_TO_BEST = (
    "unspecified_zero",
    "estimated",
    "imputed",
    "reported",
)

# Run gate: in HD 2.4.a, only Stages 1-3 are implemented. main() short-
# circuits before Stage 4. Flip to True in HD 2.4.b once Stages 4-5 land.
RUN_STAGES_BEYOND_3 = False


# --------------------------------------------------------------------------- #
# Drift-defense: YAML / scoping-doc / runtime-constant consistency
# --------------------------------------------------------------------------- #


def _parse_yaml_ordering(yaml_path: Path) -> list[str]:
    """Extract the `quality_flag_propagation.ordering` list from the YAML.

    Hand-rolled minimal parser to avoid a build-time pyyaml dependency
    (pyyaml lives in the `match-engine` group per pyproject.toml; the
    HERD build's runtime deps are duckdb + pypdf only). The parser walks
    the YAML as text, finds the `ordering:` key under
    `quality_flag_propagation:`, and collects dash-prefixed entries until
    the indent decreases or a sibling key arrives.

    Parse anchor: the YAML's `ordering:` block under
    `quality_flag_propagation:`, locked 2026-05-09 and maintainer-greenlit.
    Brittle if the YAML is reflowed; that is the intended brittleness
    (the consistency test catches reflow drift exactly because it is
    structural). If the parser ever fails to find a list of strings, it
    raises with the byte offset and surrounding context.

    Returns
    -------
    list[str]
        The 4 propagation-ordering enum values as strings, worst -> best
        per the YAML's authored intent.
    """
    text = yaml_path.read_text(encoding="utf-8")
    # Locate `quality_flag_propagation:` at column 0.
    block_marker = "quality_flag_propagation:"
    block_pos = text.find("\n" + block_marker)
    if block_pos < 0:
        # Top-of-file is also acceptable.
        if not text.startswith(block_marker):
            raise RuntimeError(
                f"{yaml_path}: cannot find '{block_marker}' at column 0; "
                "YAML structure changed and parse anchor is invalid."
            )
        block_start = 0
    else:
        block_start = block_pos + 1  # skip leading newline
    # Within that block, find the first `ordering:` line at >= 2-space indent.
    ordering_re = re.compile(
        r"^(?P<indent> {2,})ordering:\s*$",
        re.MULTILINE,
    )
    m = ordering_re.search(text, pos=block_start)
    if m is None:
        raise RuntimeError(
            f"{yaml_path}: cannot find 'ordering:' under "
            f"'quality_flag_propagation:'; parse anchor invalid."
        )
    list_indent_min = len(m.group("indent")) + 2  # entries indent further
    cursor = m.end()
    items: list[str] = []
    # Entry pattern: `<indent>- <value>` (optionally with trailing comment).
    entry_re = re.compile(
        r"^(?P<indent> +)- (?P<value>[A-Za-z_]\w*)\s*(#.*)?$"
    )
    # Comment-line pattern (interleaved comments are common inside YAML
    # lists; the maintainer-greenlit `ordering:` block has two leading
    # comment lines explaining "worst -> best" before the entries begin).
    comment_re = re.compile(r"^\s*#")
    for line in text[cursor:].splitlines():
        if not line.strip():
            # Blank line within the list is allowed.
            continue
        if comment_re.match(line):
            # Comment line — skip without ending the block.
            continue
        em = entry_re.match(line)
        if em is None:
            # First non-list-entry, non-comment, non-blank line ends the block.
            break
        if len(em.group("indent")) < list_indent_min:
            break
        items.append(em.group("value"))
    if not items:
        raise RuntimeError(
            f"{yaml_path}: ordering block found but contained no "
            "dash-prefixed entries; parse anchor returned empty list."
        )
    return items


def _parse_scoping_doc_ordering(scoping_path: Path) -> list[str]:
    """Extract the propagation ordering from the scoping doc.

    Parse anchor: scoping doc §6.2 Stage 6 contains a fenced ASCII line
    of the form ::

        unspecified_zero  <  estimated  <  imputed  <  reported

    Locked 2026-05-09 alongside the YAML. The line's stable shape is
    four `[a-z_]+` tokens separated by `<` with arbitrary surrounding
    whitespace, inside a fenced code block under §6.2 Stage 6. We
    search for that exact ASCII shape (4 enum-style tokens + 3 `<`
    operators on a single line) anywhere in the doc and return the
    first match. If the anchor moves or the four tokens drift, the
    consistency test fails loud.
    """
    text = scoping_path.read_text(encoding="utf-8")
    # Pattern: 4 lowercase-snake_case tokens separated by ` < ` (with
    # whitespace tolerance). We require all 4 tokens to be from the
    # known enum set so we don't accidentally match prose.
    enum_alt = "(?:unspecified_zero|estimated|imputed|reported)"
    line_re = re.compile(
        rf"^\s*({enum_alt})\s+<\s+({enum_alt})\s+<\s+({enum_alt})\s+<\s+({enum_alt})\s*$",
        re.MULTILINE,
    )
    m = line_re.search(text)
    if m is None:
        raise RuntimeError(
            f"{scoping_path}: cannot find the fenced 4-token ordering line "
            "under §6.2 Stage 6 (parse anchor: "
            "'unspecified_zero  <  estimated  <  imputed  <  reported'). "
            "Scoping-doc structure changed; surface to maintainer."
        )
    return [m.group(1), m.group(2), m.group(3), m.group(4)]


def _assert_yaml_doc_consistency() -> None:
    """Cross-check propagation ordering across YAML / scoping doc / runtime.

    The YAML (`crosswalks/era_b_reconstruction_rule.yaml`) and the scoping
    doc (`docs/methods_notes/herd_panel_etl_scoping.md` §6.2 Stage 6 /
    §14.2) are co-authored sources of truth on the propagation rule
    (locked 2026-05-09, maintainer-greenlit). The runtime constant
    `QUALITY_FLAG_ORDERING_WORST_TO_BEST` mirrors them. Drift between
    any pair is a CI/test concern — this assertion runs at the top of
    main() before any stage executes, fails loud if the three disagree,
    and is the build-side enforcement of the surface flagged in
    Skipper's lock summary 2026-05-09.

    Mirrors the spirit of Stage 9's status='u' FY-2017-only / non-Total
    sanity assertion: the YAML and the scoping doc are co-authored; the
    consistency test is drift defense.
    """
    yaml_ordering = _parse_yaml_ordering(ERA_B_RULE_YAML)
    doc_ordering = _parse_scoping_doc_ordering(SCOPING_DOC_MD)
    runtime_ordering = list(QUALITY_FLAG_ORDERING_WORST_TO_BEST)

    if yaml_ordering != runtime_ordering:
        raise RuntimeError(
            "quality_flag propagation ordering drift: "
            f"YAML={yaml_ordering!r} vs runtime={runtime_ordering!r}. "
            f"Source: {ERA_B_RULE_YAML} `quality_flag_propagation.ordering`. "
            "Update the runtime constant or the YAML; do not silently patch."
        )
    if doc_ordering != runtime_ordering:
        raise RuntimeError(
            "quality_flag propagation ordering drift: "
            f"scoping doc={doc_ordering!r} vs runtime={runtime_ordering!r}. "
            f"Source: {SCOPING_DOC_MD} §6.2 Stage 6 fenced ordering line. "
            "Update the runtime constant or the scoping doc; do not silently patch."
        )


# --------------------------------------------------------------------------- #
# Crosswalk loading
# --------------------------------------------------------------------------- #


def _load_discipline_fine_crosswalk(
    con: duckdb.DuckDBPyConnection,
) -> None:
    """Register `discipline_fine.csv` as a DuckDB temp table for joins.

    Creates a temp table `_xwalk_discipline_fine` with columns
    `(era, raw_row_label, discipline_fine, discipline_coarse)` derived
    from the locked 96-row crosswalk. Stage 3 joins against this table
    on `(era, raw_row_label)` per scoping doc §6.2 Stage 3.

    The crosswalk's full schema is `era,year_range_start,year_range_end,
    raw_row_label,discipline_coarse,discipline_fine,era_b_counterpart,
    first_year_with_positive_value,decision_rationale,source_doc_anchor`;
    Stage 3 needs only the four columns above. Year-range filtering is
    not applied here — the crosswalk's row coverage already reflects the
    stable label-to-bucket mapping per era (e.g., the 1975-1978 pre-leaf
    fingerprint emits only `Engineering, all` rows by construction —
    1973-1974 carry the same fingerprint shape but are carved out of
    the panel per HD 2.4.b round 1 Vision verdict 2026-05-10 Category II
    option (a)).
    """
    con.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE _xwalk_discipline_fine AS
        SELECT
            era,
            raw_row_label,
            discipline_fine,
            discipline_coarse
        FROM read_csv_auto(
            '{DISCIPLINE_FINE_CSV.as_posix()}',
            header=True,
            all_varchar=True
        )
        """
    )


def _load_question_map_crosswalk(
    con: duckdb.DuckDBPyConnection,
) -> None:
    """Register `question_map.csv` and the era-B Stage 2 in-scope label set.

    Creates two DuckDB temp tables:

    - `_xwalk_question_map`: full question-map crosswalk projected to the
      columns the build consumes (`era`, `year_range`, `question`,
      `raw_question_label`, `era_role`, `contributes_to_all_source_total`).
      `raw_question_label` is normalized so the empty-string case (CSV
      blank) becomes NULL.
    - `_xwalk_question_map_in_scope`: era-B Stage 2 in-scope label set,
      expanded canonical + raw labels into one `label` column. Stage 2
      filters via SEMI JOIN against this table per scoping doc §6.2
      Stage 2 (HD 2.4.a Track 2 Option 2 lock, 2026-05-09).

    The expand-then-union pattern handles Q4/Q5/Q14 raw-vs-canonical
    Guide drift uniformly: every canonical entry in
    `ERA_B_IN_SCOPE_QUESTIONS_CANONICAL` contributes its canonical label,
    plus its `raw_question_label` if populated. Q9 and Q11 contribute
    only the canonical (raw matches canonical per crosswalk rows 20 / 22).

    Defensive: every canonical in `ERA_B_IN_SCOPE_QUESTIONS_CANONICAL`
    MUST resolve to ≥1 row in `_xwalk_question_map`. If a canonical has
    drifted out of the crosswalk (e.g., renamed without updating the
    runtime constant), surface as a build-blocker — same loud-log
    discipline as Stage 3's unmapped-row-label assertion.
    """
    con.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE _xwalk_question_map AS
        SELECT
            era,
            year_range,
            question,
            NULLIF(raw_question_label, '') AS raw_question_label,
            era_role,
            contributes_to_all_source_total
        FROM read_csv_auto(
            '{QUESTION_MAP_CSV.as_posix()}',
            header=True,
            all_varchar=True
        )
        """
    )
    in_scope_literals = ", ".join(
        f"'{q}'" for q in ERA_B_IN_SCOPE_QUESTIONS_CANONICAL
    )
    con.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE _xwalk_question_map_in_scope AS
        WITH base AS (
            SELECT era, question, raw_question_label
            FROM _xwalk_question_map
            WHERE era = 'B' AND question IN ({in_scope_literals})
        )
        SELECT era, question AS label FROM base
        UNION ALL
        SELECT era, raw_question_label AS label
        FROM base
        WHERE raw_question_label IS NOT NULL
        """
    )

    # Loud-log: every canonical in ERA_B_IN_SCOPE_QUESTIONS_CANONICAL
    # must resolve to a row in the era-B crosswalk. If a canonical drops
    # out (rename, deletion), surface here rather than silently filtering
    # out every microdata row of that question family at Stage 2.
    found = con.sql(
        f"""
        SELECT question
        FROM _xwalk_question_map
        WHERE era = 'B' AND question IN ({in_scope_literals})
        """
    ).fetchall()
    found_set = {r[0] for r in found}
    missing = [
        q for q in ERA_B_IN_SCOPE_QUESTIONS_CANONICAL if q not in found_set
    ]
    if missing:
        raise RuntimeError(
            "Stage 2 crosswalk-coverage: "
            f"{len(missing)} canonical question label(s) from "
            "ERA_B_IN_SCOPE_QUESTIONS_CANONICAL have no matching era-B "
            "row in crosswalks/question_map.csv. Update the crosswalk "
            "or the runtime constant; do not silently patch. "
            f"Missing: {missing!r}"
        )


# --------------------------------------------------------------------------- #
# Stage 1 - Raw ingestion (scoping doc §6.2 Stage 1)
# --------------------------------------------------------------------------- #


def load_year(
    year: int,
    con: duckdb.DuckDBPyConnection,
) -> duckdb.DuckDBPyRelation:
    """Load one year of HERD CSV into a unified-schema relation.

    Thin wrapper around `etl._load.read_herd_csv`. No filtering at this
    stage — Stage 1 is pure load. Stage 2 applies question-axis filtering;
    Stage 3 applies discipline-axis normalization.

    The connection is required (not optional) so callers can accumulate
    multiple years on one connection; this matters for Stage 4-5 UNION
    ALL of per-year relations.
    """
    return read_herd_csv(year, con=con)


# --------------------------------------------------------------------------- #
# Stage 2 - Question filtering (scoping doc §6.2 Stage 2)
# --------------------------------------------------------------------------- #


def filter_in_scope_questions(
    rel: duckdb.DuckDBPyRelation,
    era: str,
    con: duckdb.DuckDBPyConnection,
) -> duckdb.DuckDBPyRelation:
    """Filter to in-scope questions for the era (label-based, HD 2.4.a Track 2).

    Era A (1973-2009) — keep rows where ``question`` matches the era-A
    field-level question or the era-A equipment question (Items 2 and
    3 in FY24 Guide terminology). Era-A has no Q4/Q5 carve-outs.

    Era B (2010-2024) — keep rows where ``question`` matches a canonical
    or raw label of any in-scope question (Q4, Q5, Q9, Q11, Q14) per
    `_xwalk_question_map_in_scope`, the canonical-or-raw label set
    expanded by `_load_question_map_crosswalk()`. Filter primitive is a
    SEMI JOIN against the in-scope label table; Q4/Q5/Q14
    raw-vs-canonical Guide drift is handled by the in-scope table's
    expand-then-union construction, not by a separate code path.

    The build does NOT filter on `questionnaire_no` enumeration. The qno
    suffix encodes question-family in the numeric prefix (`'04'`/`'05'`/
    `'09'`/`'11'`/`'14'`) and field-discipline in the alphabetic-plus-
    leaf-digit suffix (`'09B05'` = Question 9, Engineering family,
    electrical/electronic/communications leaf). The bijection between
    qno suffix and `row` text (per
    `validation/reports/qno_suffix_semantics_findings.md`) makes
    label-filtering and qno-prefix-filtering strictly redundant; we
    filter on the canonical question label because it is more readable
    in spec / methods-note prose and more stable under hypothetical NSF
    question renumbering. The qno suffix is preserved in raw rows as
    fidelity-only data.

    Stage 5 (era-B build) and Stage 8 (attribute build) re-filter from
    this superset on `question` further; Stage 2 is the union of
    in-scope questions for the era so a single Stage-1 read can feed
    both downstream branches.

    Parameters
    ----------
    rel : DuckDBPyRelation
        Stage 1 output (unified-schema row stream for one year).
    era : str
        'A' or 'B'.
    con : DuckDBPyConnection
        Connection carrying the registered
        `_xwalk_question_map_in_scope` temp table (loaded via
        `_load_question_map_crosswalk()` before Stage 2 runs).
    """
    if era == "A":
        # Era-A Item 3 raw-vs-canonical drift: raw HERD CSVs use
        # 'Equipment expenditures by S&E field'; FY24 Guide canonical is
        # 'Current fund research equipment expenditures by field'.
        # Filter admits both per crosswalks/question_map.csv row 8 and
        # the HD 2.4.b round 1 Item 3 label probe (2026-05-10).
        return rel.filter(
            f"question IN ('{ERA_A_FIELD_QUESTION}', "
            f"'{ERA_A_EQUIPMENT_QUESTION}', "
            f"'{ERA_A_EQUIPMENT_QUESTION_RAW}')"
        )
    if era == "B":
        sub_sql = rel.sql_query()
        return con.sql(
            f"""
            SELECT r.*
            FROM ({sub_sql}) AS r
            WHERE r.question IN (
                SELECT label
                FROM _xwalk_question_map_in_scope
                WHERE era = 'B'
            )
            """
        )
    raise ValueError(f"era must be 'A' or 'B'; got {era!r}")


# --------------------------------------------------------------------------- #
# Stage 3 - Discipline normalization (scoping doc §6.2 Stage 3)
# --------------------------------------------------------------------------- #


def normalize_discipline(
    rel: duckdb.DuckDBPyRelation,
    con: duckdb.DuckDBPyConnection,
) -> duckdb.DuckDBPyRelation:
    """Join `discipline_fine` crosswalk and assert no unmapped row labels.

    Joins the Stage 2 output against `_xwalk_discipline_fine` on
    `(era, "row")` to populate `discipline_fine` and `discipline_coarse`.
    Filters apply only to the field-axis questions (`Expenditures by S&E
    field`, era-A equipment, Q9, Q11, Q14) — Q4/Q5 rows pass through
    unjoined because they have no field axis (they are institution-year
    carve-outs handled at Stage 8 via the attribute table). For Q4/Q5,
    `discipline_fine` and `discipline_coarse` are NULL on the joined
    output by construction.

    Decision: the `quality_flag` mapping is also populated here, in the
    same SELECT, alongside discipline normalization. Rationale: keeping
    Stage 1 a thin pure-load wrapper preserves the parallel with
    `etl/build_herd_personnel.py`'s pattern (read_herd_csv -> filter ->
    project), and Stage 3 is the first stage that materializes any
    non-trivial expression beyond the loader's projection. Co-locating
    discipline + quality_flag derivation here keeps the per-year SQL
    block in one readable place and keeps Stages 4/5/6 focused on
    schema-projection and reconstruction concerns rather than enum
    mapping. The status->quality_flag CASE is duplicated nowhere else.

    Loud-log discipline (scoping doc §4(b); mirrors
    `etl/build_herd_personnel.py` lines 226-234 UNKNOWN_personnel_function
    pattern): for in-scope FIELD-axis rows (era-A field/equipment, era-B
    Q9/Q11/Q14), every raw `row` MUST have a matching crosswalk entry.
    If any unmapped row label appears, raise RuntimeError with the
    label, year, and question. The assertion runs inside this Stage 3
    function via a follow-up scan of the joined relation.

    Parameters
    ----------
    rel : DuckDBPyRelation
        Stage 2 output (in-scope question rows for one year).
    con : DuckDBPyConnection
        Connection carrying the registered `_xwalk_discipline_fine`
        temp table.

    Returns
    -------
    DuckDBPyRelation
        Stage 2 schema augmented with `discipline_fine`,
        `discipline_coarse`, and `quality_flag` (in addition to the
        existing UNIFIED_COLS).
    """
    # Field-axis questions are the ones that need a crosswalk join.
    # Q4 and Q5 have no field axis (institution-year carve-outs); they
    # pass through with NULL discipline columns and are extracted at
    # Stage 8. Q14 carries both its canonical and raw labels here
    # because the raw HERD CSVs use the abbreviated form (HD 2.4.a
    # Track 2 lock); without `ERA_B_Q14_RAW` in the field-axis set, raw
    # Q14 rows would slip past the unmapped-row-label assertion below.
    field_axis_filter = (
        f"question IN ('{ERA_A_FIELD_QUESTION}', "
        f"'{ERA_A_EQUIPMENT_QUESTION}', "
        f"'{ERA_A_EQUIPMENT_QUESTION_RAW}', "
        f"'{ERA_B_Q9}', '{ERA_B_Q11}', "
        f"'{ERA_B_Q14}', '{ERA_B_Q14_RAW}')"
    )
    # Q4/Q5 raw-label-aware predicate: a row is "in field-axis scope"
    # only if its `question` matches a canonical-or-raw field-axis
    # label. Q4 raw (`Medical school expenditures`) and Q5 raw
    # (`Clinical trials`) are NOT in this set, which correctly excludes
    # them from the field-axis assertion path (they are institution-year
    # carve-outs, handled at Stage 8 via the attribute table).

    # Build a per-year joined relation with discipline columns and
    # quality_flag populated. The CASE on status maps the four FY24-Guide-
    # documented raw codes (case-folded via UPPER() per HD 2.4.b round 1
    # Vision verdict 2026-05-10 Category I — pre-1990 era-A files emit
    # 'I' / 'E' alongside 'i' / 'e' freely; case-fold preserves locked
    # semantics) to the harmonized enum; anything else flows to
    # 'UNKNOWN_<status>' so the assertion below catches it. Empirical
    # anchor: `validation/reports/era_a_status_codeset_findings.md`.
    sub_sql = rel.sql_query()
    joined_sql = f"""
        SELECT
            r.*,
            x.discipline_fine     AS discipline_fine,
            x.discipline_coarse   AS discipline_coarse,
            CASE
                WHEN r.status IS NULL OR r.status = '' THEN '{QUALITY_FLAG_REPORTED}'
                WHEN UPPER(r.status) = 'I' THEN 'imputed'
                WHEN UPPER(r.status) = 'E' THEN 'estimated'
                WHEN UPPER(r.status) = 'U' THEN 'unspecified_zero'
                ELSE 'UNKNOWN_' || r.status
            END AS quality_flag
        FROM ({sub_sql}) AS r
        LEFT JOIN _xwalk_discipline_fine AS x
          ON x.era = r.era
         AND x.raw_row_label = r."row"
    """
    joined = con.sql(joined_sql)

    # Loud-log assertion 1: no UNKNOWN_<status> values in quality_flag
    # (scoping doc §6.2 Stages 4-5 directive: "anything else -> build
    # raises RuntimeError"). We surface the offending (year, status,
    # question, row) tuples.
    unknown_flag_rows = con.sql(
        f"""
        SELECT DISTINCT year, status, question, "row"
        FROM ({joined.sql_query()})
        WHERE quality_flag LIKE 'UNKNOWN_%'
        ORDER BY year, status, question
        LIMIT 20
        """
    ).fetchall()
    if unknown_flag_rows:
        sample = "\n".join(
            f"  year={r[0]} status={r[1]!r} question={r[2]!r} row={r[3]!r}"
            for r in unknown_flag_rows
        )
        raise RuntimeError(
            "Stage 3: encountered raw `status` values outside the documented "
            "codeset {blank, 'i', 'e', 'u'}. Update QUALITY_FLAG_MAP and the "
            "scoping doc §1 quality_flag value semantics, or treat as a "
            f"build-blocker. First {len(unknown_flag_rows)} offending tuples:\n"
            f"{sample}"
        )

    # Loud-log assertion 2: no unmapped field-axis row labels (scoping
    # doc §4(b)). Mirrors `etl/build_herd_personnel.py` lines 226-234
    # UNKNOWN_personnel_function pattern. Field-axis rows that fail the
    # crosswalk join carry NULL `discipline_fine` AND `discipline_coarse`;
    # we surface the offending (year, question, row) tuples and raise.
    unmapped_rows = con.sql(
        f"""
        SELECT DISTINCT year, question, "row"
        FROM ({joined.sql_query()})
        WHERE {field_axis_filter}
          AND discipline_fine IS NULL
        ORDER BY year, question, "row"
        LIMIT 20
        """
    ).fetchall()
    if unmapped_rows:
        sample = "\n".join(
            f"  year={r[0]} question={r[1]!r} row={r[2]!r}"
            for r in unmapped_rows
        )
        raise RuntimeError(
            "Stage 3: encountered raw `row` labels with no matching entry in "
            "crosswalks/discipline_fine.csv. Update the crosswalk first; do "
            f"not silently skip. First {len(unmapped_rows)} offending tuples:\n"
            f"{sample}"
        )

    return joined


# --------------------------------------------------------------------------- #
# Stages 4-10 (signatures only; bodies in HD 2.4.b through .d)
# --------------------------------------------------------------------------- #


def build_era_a_rows(
    years: range,
    con: duckdb.DuckDBPyConnection,
) -> duckdb.DuckDBPyRelation:
    """Stage 4: era-A direct rows (scoping doc §6.2 Stage 4).

    For each year in `years` where `PANEL_FIRST_YEAR (1975) <= year <=
    ERA_A_LAST_YEAR (2009)`:
      1. Stage 1 load via `load_year(year, con)`.
      2. Stage 2 filter to in-scope era-A questions
         (`ERA_A_FIELD_QUESTION` and `ERA_A_EQUIPMENT_QUESTION`).
      3. Stage 3 discipline normalization + `quality_flag` derivation.
      4. Filter to `column='Total'` (the era-A all-source column per
         FY24 Guide page 18 Item 2 / page 19 Item 3).
      5. Project to the locked 21-column panel schema per scoping
         doc §1: `era='A'`, `source_class='all_source'`,
         `form_type='standard'`, `expenditure_type` keyed off the
         question (Item 2 -> 'r&d', Item 3 -> 'r&d_equipment'),
         `value_type='current'`, `unit='kUSD_current'`,
         `quality_flag` propagated from Stage 3.

    UNION ALL across years.

    Year-filter discipline. Two filters apply at the function level
    parallel to `PANEL_FIRST_YEAR` / `PANEL_YEARS` constants. Years
    above `ERA_A_LAST_YEAR` are skipped silently (Stage 5 picks up the
    era-B side). Years below `PANEL_FIRST_YEAR` are skipped silently
    per the FY 1973-1974 carve-out locked at HD 2.4.b round 1 (Vision
    verdict 2026-05-10 Category II option (a); empirical anchor
    `validation/reports/era_a_status_codeset_findings.md`). The carve-
    out is enforced both at the constant (`PANEL_YEARS`) and at the
    function (this floor check) — defensive double-enforcement so a
    caller passing a custom year range cannot accidentally include
    1972/1973/1974 in the panel.

    Pre-1981 fingerprint (per scoping doc §3(b)): 1975-1978 emits only
    `*, all` rollup rows; 1979 onward emits leaves. Stage 4 emits the
    rows verbatim from the raw CSV after the discipline-fine join; no
    synthetic completion. Per-year row counts therefore differ pre/
    post-1979 by construction.

    Equipment series (Item 3): 1981-2009 only. 1975-1980 emits no
    `expenditure_type='r&d_equipment'` rows because Item 3 was added
    FY 1981 (FY24 Guide page 19; question_map.csv row 8).
    """
    union_parts: list[str] = []
    for year in years:
        if year > ERA_A_LAST_YEAR:
            continue
        if year < PANEL_FIRST_YEAR:
            # FY 1972-1974 carve-out (HD 2.4.b round 1 Vision verdict
            # 2026-05-10 Category II option (a)). 1972: no field-level
            # question (FY24 Guide page 16 §2.1.5). 1973-1974: Guide-
            # undocumented status='c' code on field-level Total-column
            # rows. Raw zips preserved in data/raw/herd/.
            continue
        rel1 = load_year(year, con)
        rel2 = filter_in_scope_questions(rel1, "A", con)
        rel3 = normalize_discipline(rel2, con)

        # Stage 4 projection: filter to column='Total' and map to the
        # locked 21-column schema. Era-A files use 'herd_YYYY.csv'
        # naming (per etl/_load.py:csv_member_for, 1972-2015).
        sub_sql = rel3.sql_query()
        projected_sql = f"""
            SELECT
                CAST(inst_id AS VARCHAR)            AS institution_id,
                CAST(fice AS VARCHAR)               AS fice,
                CAST(ncses_inst_id AS VARCHAR)      AS ncses_inst_id,
                CAST(ipeds_unitid AS VARCHAR)       AS ipeds_unitid,
                CAST(inst_name_long AS VARCHAR)     AS inst_name_long,
                CAST(year AS INTEGER)               AS year,
                CAST(era AS VARCHAR)                AS era,
                CAST(discipline_coarse AS VARCHAR)  AS discipline_coarse,
                CAST(discipline_fine AS VARCHAR)    AS discipline_fine,
                CASE
                    WHEN question IN (
                        '{ERA_A_EQUIPMENT_QUESTION}',
                        '{ERA_A_EQUIPMENT_QUESTION_RAW}'
                    ) THEN 'r&d_equipment'
                    ELSE 'r&d'
                END                                  AS expenditure_type,
                'all_source'                         AS source_class,
                'standard'                           AS form_type,
                CAST(value AS DOUBLE)                AS value,
                'kUSD_current'                       AS unit,
                'current'                            AS value_type,
                CAST(quality_flag AS VARCHAR)        AS quality_flag,
                CAST(questionnaire_no AS VARCHAR)    AS source_questionnaire_no,
                -- Item 3 raw-vs-canonical drift: when the row carries
                -- the raw label, source_question_canonical materializes
                -- the FY24 Guide canonical; source_question_raw preserves
                -- the CSV raw text. Era-A field question has no drift
                -- (both columns identical).
                CASE
                    WHEN question = '{ERA_A_EQUIPMENT_QUESTION_RAW}'
                        THEN '{ERA_A_EQUIPMENT_QUESTION}'
                    ELSE question
                END                                  AS source_question_canonical,
                CAST(question AS VARCHAR)            AS source_question_raw,
                'herd_' || CAST(year AS VARCHAR) || '.csv'
                                                     AS source_file,
                CAST(NULL AS VARCHAR)                AS notes
            FROM ({sub_sql})
            WHERE "column" = 'Total'
        """
        union_parts.append(projected_sql)

    if not union_parts:
        raise RuntimeError(
            "Stage 4: build_era_a_rows received no era-A years "
            f"(input years={list(years)!r}, ERA_A_LAST_YEAR={ERA_A_LAST_YEAR}). "
            "Check PANEL_YEARS configuration."
        )

    union_sql = "\nUNION ALL\n".join(f"({p})" for p in union_parts)
    return con.sql(union_sql)


def build_era_b_components(
    years: range,
    con: duckdb.DuckDBPyConnection,
) -> duckdb.DuckDBPyRelation:
    """Stage 5: era-B per-component rows (scoping doc §6.2 Stage 5).

    Three sub-paths assembled into one UNION ALL relation:

    1. **Standard-form Q9/Q11/Q14 path** (years 2010-2024). For each
       year:
         - Load via `read_herd_csv(year, con)` (Stage 1).
         - Filter to era-B in-scope questions via the
           `_xwalk_question_map_in_scope` SEMI JOIN (Stage 2). Admits
           Q4/Q5/Q9/Q11/Q14 raw+canonical labels.
         - Normalize discipline via `_xwalk_discipline_fine` (Stage 3),
           which also derives `quality_flag` from raw `status`.
         - Filter Q4/Q5 OUT of the panel output (they route to Stage 8
           attribute extraction; their rows pass through Stage 2/3 to
           share the per-year scan, but are not projected to panel rows
           here).
         - Filter to `column='Total'` (the rolled all-source/all-agency
           column per scoping doc §6.2 Stage 5 + HD 2.4.b round 1 Q14
           column-structure probe).
         - Project to the locked 21-column panel schema with
           `era='B'`, `form_type='standard'`, `source_class` keyed off
           question (Q9 -> 'federal', Q11 -> 'nonfederal',
           Q14 -> 'all_source' per scoping doc §1(b) / §14.5),
           `expenditure_type` keyed off question (Q9/Q11 -> 'r&d',
           Q14 -> 'r&d_equipment').

    2. **Short-form Q2 path** (years 2012-2024 per
       `SHORT_FORM_FIRST_YEAR`/`SHORT_FORM_LAST_YEAR`). For each year:
         - Load via `read_herd_short_form_csv(year, con)`.
         - Filter to Short Form Q2 raw or canonical label.
         - Normalize discipline (same crosswalk; short-form row labels
           are a subset of era-B labels already in the crosswalk).
         - Filter to `column='Total'`.
         - Project to schema with `era='B'`, `form_type='short'`,
           `source_class='all_source'` (the rolled value at column
           ='Total'), `expenditure_type='r&d'`. Per scoping doc §9.1
           (revised at HD 2.4.b round 1 per Vision Option (b)).

    3. **Q4/Q5 carve-out rows** (years 2010-2024). Stage 5 does NOT
       emit these as panel rows — they are institution-year attributes
       per scoping doc §1(c) / Stage 8. The Stage 2 filter admits them
       so a single per-year scan feeds both Stage 5 and the eventual
       Stage 8 attribute build; Stage 5's projection filter excludes
       them via `question NOT IN (Q4 canonical, Q4 raw, Q5 canonical,
       Q5 raw)`.

    `quality_flag` propagation. Stage 3 derives `quality_flag` from
    raw `status` for every row (case-folded `UPPER(status)`); Stage 5
    propagates the derived flag verbatim. The W4 NULL-handling lock's
    least-good-flag-wins propagation for the reconstructed
    `source_class='all_source'` rows lives in Stage 6, not here.

    UNION ALL across the three sub-paths.
    """
    union_parts: list[str] = []

    # --- Path 1: standard-form Q9/Q11/Q14 ---------------------------- #
    for year in years:
        if year < 2010 or year > 2024:
            continue
        rel1 = load_year(year, con)
        rel2 = filter_in_scope_questions(rel1, "B", con)
        rel3 = normalize_discipline(rel2, con)
        sub_sql = rel3.sql_query()
        # Era-B file naming: 'herd_YYYY.csv' (2010-2015), 'herdYYYY.csv'
        # (2016-2024). Per etl/_load.py:csv_member_for.
        if year <= 2015:
            source_file_literal = f"herd_{year}.csv"
        else:
            source_file_literal = f"herd{year}.csv"
        projected_sql = f"""
            SELECT
                CAST(inst_id AS VARCHAR)            AS institution_id,
                CAST(fice AS VARCHAR)               AS fice,
                CAST(ncses_inst_id AS VARCHAR)      AS ncses_inst_id,
                CAST(ipeds_unitid AS VARCHAR)       AS ipeds_unitid,
                CAST(inst_name_long AS VARCHAR)     AS inst_name_long,
                CAST(year AS INTEGER)               AS year,
                CAST(era AS VARCHAR)                AS era,
                CAST(discipline_coarse AS VARCHAR)  AS discipline_coarse,
                CAST(discipline_fine AS VARCHAR)    AS discipline_fine,
                CASE
                    WHEN question IN ('{ERA_B_Q14}', '{ERA_B_Q14_RAW}')
                        THEN 'r&d_equipment'
                    ELSE 'r&d'
                END                                  AS expenditure_type,
                CASE
                    WHEN question = '{ERA_B_Q9}'    THEN 'federal'
                    WHEN question = '{ERA_B_Q11}'   THEN 'nonfederal'
                    WHEN question IN ('{ERA_B_Q14}', '{ERA_B_Q14_RAW}')
                        THEN 'all_source'
                END                                  AS source_class,
                'standard'                           AS form_type,
                CAST(value AS DOUBLE)                AS value,
                'kUSD_current'                       AS unit,
                'current'                            AS value_type,
                CAST(quality_flag AS VARCHAR)        AS quality_flag,
                CAST(questionnaire_no AS VARCHAR)    AS source_questionnaire_no,
                CASE
                    WHEN question = '{ERA_B_Q14_RAW}'
                        THEN '{ERA_B_Q14}'
                    ELSE question
                END                                  AS source_question_canonical,
                CAST(question AS VARCHAR)            AS source_question_raw,
                '{source_file_literal}'              AS source_file,
                CAST(NULL AS VARCHAR)                AS notes
            FROM ({sub_sql})
            WHERE "column" = 'Total'
              AND question IN (
                  '{ERA_B_Q9}', '{ERA_B_Q11}',
                  '{ERA_B_Q14}', '{ERA_B_Q14_RAW}'
              )
        """
        union_parts.append(projected_sql)

    # --- Path 2: short-form Q2 --------------------------------------- #
    for year in years:
        if year < SHORT_FORM_FIRST_YEAR or year > SHORT_FORM_LAST_YEAR:
            continue
        rel_s = read_herd_short_form_csv(year, con=con)
        # Stage 2 equivalent: filter to Short Form Q2 raw + canonical.
        rel_s_filtered = rel_s.filter(
            f"question IN ('{SHORT_FORM_Q2_CANONICAL}', "
            f"'{SHORT_FORM_Q2_RAW}')"
        )
        # Stage 3 equivalent: join discipline + derive quality_flag.
        # Reuses `_xwalk_discipline_fine` (loaded once by caller).
        # Short-form row labels are a subset of era-B labels; the join
        # on (era='B', raw_row_label=row) is the same as standard-form
        # era-B path. We inline the join + quality_flag CASE here
        # because Stage 3's `normalize_discipline` wraps the full
        # assertion machinery — for short-form, we trust the era-B
        # crosswalk to cover all 10 coarse buckets + 'All' (verified
        # empirically at HD 2.4.b round 1 short-form probe).
        sub_sql = rel_s_filtered.sql_query()
        joined_sql = f"""
            SELECT
                r.*,
                x.discipline_fine     AS discipline_fine,
                x.discipline_coarse   AS discipline_coarse,
                CASE
                    WHEN r.status IS NULL OR r.status = '' THEN '{QUALITY_FLAG_REPORTED}'
                    WHEN UPPER(r.status) = 'I' THEN 'imputed'
                    WHEN UPPER(r.status) = 'E' THEN 'estimated'
                    WHEN UPPER(r.status) = 'U' THEN 'unspecified_zero'
                    ELSE 'UNKNOWN_' || r.status
                END AS quality_flag
            FROM ({sub_sql}) AS r
            LEFT JOIN _xwalk_discipline_fine AS x
              ON x.era = r.era
             AND x.raw_row_label = r."row"
        """
        # Defensive: any short-form row that fails the crosswalk
        # lookup raises here, parallel to Stage 3's discipline
        # assertion. Empirically the era-B crosswalk covers all 10
        # short-form coarse buckets + 'All' grand total (verified at
        # HD 2.4.b round 1 short-form probe); the assertion is
        # drift-defense.
        joined = con.sql(joined_sql)
        unmapped = con.execute(
            f"""
            SELECT DISTINCT year, "row"
            FROM ({joined.sql_query()})
            WHERE discipline_fine IS NULL
            ORDER BY year, "row"
            LIMIT 20
            """
        ).fetchall()
        if unmapped:
            sample = "\n".join(
                f"  year={r[0]} row={r[1]!r}" for r in unmapped
            )
            raise RuntimeError(
                "Stage 5 short-form: encountered raw `row` labels with no "
                "matching entry in crosswalks/discipline_fine.csv (era='B'). "
                "Update the crosswalk first; do not silently skip. First "
                f"{len(unmapped)} offending tuples:\n{sample}"
            )
        # Loud-log: unknown status codes (drift-defense parallel to
        # Stage 3).
        unknown_flag = con.execute(
            f"""
            SELECT DISTINCT year, status, "row"
            FROM ({joined.sql_query()})
            WHERE quality_flag LIKE 'UNKNOWN_%'
            ORDER BY year, status
            LIMIT 20
            """
        ).fetchall()
        if unknown_flag:
            sample = "\n".join(
                f"  year={r[0]} status={r[1]!r} row={r[2]!r}"
                for r in unknown_flag
            )
            raise RuntimeError(
                "Stage 5 short-form: encountered raw `status` values "
                "outside the documented codeset {blank, 'i', 'e', 'u'} "
                "(case-folded). Surface to maintainer per codeset-extension "
                "policy (CLAUDE.md §6 W4 NULL-handling lock); do not "
                f"silently extend. First {len(unknown_flag)} offending tuples:\n"
                f"{sample}"
            )

        short_projected_sql = f"""
            SELECT
                CAST(inst_id AS VARCHAR)            AS institution_id,
                CAST(fice AS VARCHAR)               AS fice,
                CAST(ncses_inst_id AS VARCHAR)      AS ncses_inst_id,
                CAST(ipeds_unitid AS VARCHAR)       AS ipeds_unitid,
                CAST(inst_name_long AS VARCHAR)     AS inst_name_long,
                CAST(year AS INTEGER)               AS year,
                CAST(era AS VARCHAR)                AS era,
                CAST(discipline_coarse AS VARCHAR)  AS discipline_coarse,
                CAST(discipline_fine AS VARCHAR)    AS discipline_fine,
                'r&d'                                AS expenditure_type,
                'all_source'                         AS source_class,
                'short'                              AS form_type,
                CAST(value AS DOUBLE)                AS value,
                'kUSD_current'                       AS unit,
                'current'                            AS value_type,
                CAST(quality_flag AS VARCHAR)        AS quality_flag,
                CAST(questionnaire_no AS VARCHAR)    AS source_questionnaire_no,
                '{SHORT_FORM_Q2_CANONICAL}'          AS source_question_canonical,
                CAST(question AS VARCHAR)            AS source_question_raw,
                'short{year}.csv'                    AS source_file,
                CAST(NULL AS VARCHAR)                AS notes
            FROM ({joined.sql_query()})
            WHERE "column" = 'Total'
        """
        union_parts.append(short_projected_sql)

    if not union_parts:
        raise RuntimeError(
            "Stage 5: build_era_b_components received no era-B years "
            f"(input years={list(years)!r}). Check PANEL_YEARS / "
            "year-range configuration."
        )

    union_sql = "\nUNION ALL\n".join(f"({p})" for p in union_parts)
    return con.sql(union_sql)


def build_era_b_all_source(
    era_b_components_rel: duckdb.DuckDBPyRelation,
    con: duckdb.DuckDBPyConnection,
) -> duckdb.DuckDBPyRelation:
    """Stage 6: era-B all-source reconstruction (scoping doc §6.2 Stage 6).

    Reads Stage 5's Q9 and Q11 rows, FULL OUTER JOIN on
    `(institution_id, year, discipline_fine)`, computes
    ``COALESCE(Q9.value,0) + COALESCE(Q11.value,0)`` as the
    reconstructed ``source_class='all_source'`` value, and propagates a
    ``quality_flag`` per the W4-locked least-good-flag-wins rule with
    row-absence contributing no flag (the YAML's
    `quality_flag_propagation.consumer_contract`).

    Inputs filtered from `era_b_components_rel`:
      - Q9 component: ``source_class='federal' AND
        expenditure_type='r&d' AND form_type='standard'``.
      - Q11 component: ``source_class='nonfederal' AND
        expenditure_type='r&d' AND form_type='standard'``.

    Q14 (``r&d_equipment``) and Short Form Q2 (``form_type='short'``)
    rows ship from Stage 5 as direct-read all_source rows and do NOT
    enter Stage 6.

    Propagation ordering per `crosswalks/era_b_reconstruction_rule.yaml`
    `quality_flag_propagation.ordering` (locked 2026-05-09):
    ``unspecified_zero < estimated < imputed < reported`` (worst -> best).
    The runtime constant `QUALITY_FLAG_ORDERING_WORST_TO_BEST` mirrors
    this; the YAML/doc/runtime consistency assertion runs at main()
    entry per `_assert_yaml_doc_consistency()`.

    Provenance columns on reconstructed rows. The reconstructed row
    represents two source-row inputs, not one. Provenance columns are
    set as composites that distinguish reconstructed rows from
    direct-read rows:

      - ``source_questionnaire_no = '9+11'`` (composite literal).
      - ``source_question_canonical =
        '[reconstructed: Q9 + Q11 per era_b_reconstruction_rule_v1]'``.
      - ``source_question_raw`` mirrors canonical (no raw drift on the
        composite literal).
      - ``source_file`` = ``COALESCE(q9.source_file, q11.source_file)``
        (Q9 and Q11 originate from the same per-year HERD CSV).
      - ``notes = NULL`` (the composite source_question_canonical
        already names the row as reconstructed).

    Equipment and short-form rows (which ship at ``source_class
    ='all_source'`` from Stage 5 direct reads) carry their original
    per-question source_questionnaire_no values (14X / 02.X); the
    ``'9+11'`` qno on reconstructed rows is the marker that
    distinguishes reconstruction from direct read.
    """
    sub_sql = era_b_components_rel.sql_query()

    # Stage 6's logical core. The FULL OUTER JOIN materializes one row
    # per (inst, year, disc) where at least one of Q9 / Q11 is present;
    # COALESCE arithmetic handles row-absence as zero on the value
    # axis; CASE expressions handle row-absence as no-op on the flag
    # axis (the present side's flag passes through unmodified) and
    # least-good-flag-wins when both sides are present.
    reconstruction_sql = f"""
        WITH _stage_5 AS ({sub_sql}),
        q9 AS (
            SELECT *
            FROM _stage_5
            WHERE source_class = 'federal'
              AND expenditure_type = 'r&d'
              AND form_type = 'standard'
        ),
        q11 AS (
            SELECT *
            FROM _stage_5
            WHERE source_class = 'nonfederal'
              AND expenditure_type = 'r&d'
              AND form_type = 'standard'
        )
        SELECT
            -- Identifier columns (COALESCE preserves whichever side
            -- carries the row; both sides agree on identifier values
            -- by construction at this grain).
            COALESCE(q9.institution_id, q11.institution_id)   AS institution_id,
            COALESCE(q9.fice, q11.fice)                       AS fice,
            COALESCE(q9.ncses_inst_id, q11.ncses_inst_id)     AS ncses_inst_id,
            COALESCE(q9.ipeds_unitid, q11.ipeds_unitid)       AS ipeds_unitid,
            COALESCE(q9.inst_name_long, q11.inst_name_long)   AS inst_name_long,
            CAST(COALESCE(q9.year, q11.year) AS INTEGER)      AS year,
            'B'                                                AS era,
            COALESCE(q9.discipline_coarse, q11.discipline_coarse)
                                                               AS discipline_coarse,
            COALESCE(q9.discipline_fine, q11.discipline_fine) AS discipline_fine,
            'r&d'                                              AS expenditure_type,
            'all_source'                                       AS source_class,
            'standard'                                         AS form_type,
            -- Row-absent-as-zero arithmetic per YAML
            -- quality_flag_propagation.semantic_clarification.
            COALESCE(q9.value, 0) + COALESCE(q11.value, 0)    AS value,
            'kUSD_current'                                     AS unit,
            'current'                                          AS value_type,
            -- Least-good-flag-wins with row-absence not propagating.
            -- Order matches YAML quality_flag_propagation.ordering
            -- (worst -> best): unspecified_zero < estimated < imputed
            -- < reported. The CASE walks the ordering top-down and
            -- shortcircuits on the worst-present flag.
            CASE
                WHEN q9.quality_flag IS NULL THEN q11.quality_flag
                WHEN q11.quality_flag IS NULL THEN q9.quality_flag
                WHEN q9.quality_flag = 'unspecified_zero'
                  OR q11.quality_flag = 'unspecified_zero'
                    THEN 'unspecified_zero'
                WHEN q9.quality_flag = 'estimated'
                  OR q11.quality_flag = 'estimated'
                    THEN 'estimated'
                WHEN q9.quality_flag = 'imputed'
                  OR q11.quality_flag = 'imputed'
                    THEN 'imputed'
                ELSE 'reported'
            END                                                AS quality_flag,
            -- Composite-source provenance: '9+11' qno + reconstruction-
            -- naming canonical label. Distinguishes reconstructed rows
            -- from era-B direct reads (Q14 r&d_equipment at qno '14X';
            -- Short Form Q2 at qno '02.X').
            '9+11'                                             AS source_questionnaire_no,
            '[reconstructed: Q9 + Q11 per era_b_reconstruction_rule_v1]'
                                                               AS source_question_canonical,
            '[reconstructed: Q9 + Q11 per era_b_reconstruction_rule_v1]'
                                                               AS source_question_raw,
            COALESCE(q9.source_file, q11.source_file)         AS source_file,
            CAST(NULL AS VARCHAR)                              AS notes
        FROM q9
        FULL OUTER JOIN q11
          ON q9.institution_id = q11.institution_id
         AND q9.year = q11.year
         AND q9.discipline_fine = q11.discipline_fine
        -- WHERE not strictly needed (FULL OUTER JOIN never emits a row
        -- with both sides absent), but stated defensively in case the
        -- inputs ever shift shape:
        WHERE q9.institution_id IS NOT NULL
           OR q11.institution_id IS NOT NULL
    """
    return con.sql(reconstruction_sql)


def assemble_panel(
    era_a_rel: duckdb.DuckDBPyRelation,
    era_b_components_rel: duckdb.DuckDBPyRelation,
    era_b_all_source_rel: duckdb.DuckDBPyRelation,
    con: duckdb.DuckDBPyConnection,
) -> duckdb.DuckDBPyRelation:
    """Stage 7: schema assembly (scoping doc §6.2 Stage 7).

    UNION ALL of:
      - Stage 4 era-A direct rows (era='A', source_class='all_source',
        expenditure_type in {r&d, r&d_equipment}, form_type='standard').
      - Stage 5 era-B per-component rows (era='B', source_class in
        {federal, nonfederal, all_source}, expenditure_type in
        {r&d, r&d_equipment}, form_type in {standard, short}).
      - Stage 6 era-B reconstructed all_source rows (era='B',
        source_class='all_source', expenditure_type='r&d',
        form_type='standard').

    All three relations share the locked 21-column schema per §1 and
    UNION ALL produces the assembled panel. No deduplication is
    applied — Stage 5's all_source rows (Q14 r&d_equipment +
    Short Form Q2) and Stage 6's reconstructed all_source rows
    (Q9+Q11 sum) coexist as distinct rows distinguishable by
    `expenditure_type` and `source_questionnaire_no`.

    The column order is enforced explicitly via the SELECT projection
    so downstream consumers (Stage 10 parquet write; verification
    spikes) can rely on it.
    """
    cols = ", ".join(f'"{c}"' for c in (
        "institution_id", "fice", "ncses_inst_id", "ipeds_unitid",
        "inst_name_long", "year", "era", "discipline_coarse",
        "discipline_fine", "expenditure_type", "source_class",
        "form_type", "value", "unit", "value_type", "quality_flag",
        "source_questionnaire_no", "source_question_canonical",
        "source_question_raw", "source_file", "notes",
    ))
    union_sql = f"""
        SELECT {cols} FROM ({era_a_rel.sql_query()})
        UNION ALL
        SELECT {cols} FROM ({era_b_components_rel.sql_query()})
        UNION ALL
        SELECT {cols} FROM ({era_b_all_source_rel.sql_query()})
    """
    return con.sql(union_sql)


def build_attribute_table(
    panel_rel: duckdb.DuckDBPyRelation,
    con: duckdb.DuckDBPyConnection,
) -> duckdb.DuckDBPyRelation:
    """Stage 8: Q4/Q5 attribute table (scoping doc §6.2 Stage 8 / §1(c)).

    Builds `herd_panel_attributes.parquet` schema:

      ``institution_id, year, era, med_school_share,
        clinical_trials_share, med_school_value,
        clinical_trials_value, source_file, notes``

    One row per distinct (institution_id, year) pair in the assembled
    panel. For era-B years (2010-2024): Q4 ('Medical school
    R&D expenditures' canonical / 'Medical school expenditures' raw)
    and Q5 ('Clinical trial R&D expenditures' canonical / 'Clinical
    trials' raw) are pivoted onto the (inst, year) row.

    Empirical structure (HD 2.4.d Stage 8 probe at
    `etl/spikes/probe_q4_q5_attribute_structure.py`, 2026-05-10 PM):
      - Q4: `column=NULL`, only `row='Total'`. One value per
        institution-year.
      - Q5: `column=NULL`, three row-axis values: `'Total'`,
        `'Federal'`, `'Nonfederal'`. Stage 8 projects `row='Total'`
        as the canonical `clinical_trials_value` per §1(c). The
        Federal/Nonfederal Q5 row-axis decomposition is NOT in the
        §1(c) schema; future schema extension would add
        `clinical_trials_federal_value` /
        `clinical_trials_nonfederal_value` columns if downstream
        analysis demands. Documented for HD 2.4.b Track 2 finding
        §3 traceability.

    Share computation. `med_school_share` and `clinical_trials_share`
    are computed as `value / institution_year_total_rd` where the
    denominator is the institution-year R&D total at
    `discipline_fine='All'` from the assembled panel:
      - Era-B 2010-2024: source_class='all_source',
        expenditure_type='r&d', form_type='standard',
        source_questionnaire_no='9+11' (the reconstructed Q9+Q11
        institution-year-total row at the 'All' discipline grain).
      - Era-A 1975-2009: source_class='all_source',
        expenditure_type='r&d', form_type='standard', read from
        Stage 4 era-A direct (`source_question_canonical=
        'Expenditures by S&E field'`).

    Era-A rows in the attribute table carry NULL for all four
    Q4/Q5 columns (Q4 and Q5 are era-B-only questions).

    Parameters
    ----------
    panel_rel : DuckDBPyRelation
        Stage 7 assembled panel relation. Used both to enumerate
        distinct (inst, year) pairs and to source the
        institution-year R&D total for share computation.
    con : DuckDBPyConnection
        Connection used for the per-year raw-CSV reads (Q4/Q5
        source) and for the share-computation joins.
    """
    # Materialize the assembled panel for repeated reads.
    con.execute("DROP TABLE IF EXISTS _stage8_panel")
    con.execute(f"CREATE TEMP TABLE _stage8_panel AS {panel_rel.sql_query()}")

    # --- Build Q4/Q5 raw extracts per era-B year --------------------- #
    q4_q5_year_parts: list[str] = []
    for year in range(2010, 2025):
        rel = load_year(year, con)
        sub_sql = rel.sql_query()
        # Era-B file naming: 'herd_YYYY.csv' (2010-2015), 'herdYYYY.csv'
        # (2016-2024). Per etl/_load.py:csv_member_for.
        if year <= 2015:
            source_file_literal = f"herd_{year}.csv"
        else:
            source_file_literal = f"herd{year}.csv"
        # Q4: project to (inst_id, year, med_school_value, source_file).
        # Q5: project to (inst_id, year, clinical_trials_value, source_file)
        #     using ONLY row='Total' per §1(c) schema (the Federal/
        #     Nonfederal row variants are excluded from the attribute
        #     table; documented in the docstring above).
        year_extract_sql = f"""
            WITH q4_raw AS (
                SELECT
                    inst_id, year,
                    TRY_CAST(data AS DOUBLE) AS med_school_value
                FROM ({sub_sql})
                WHERE question IN ('{ERA_B_Q4}', '{ERA_B_Q4_RAW}')
                  AND "row" = 'Total'
            ),
            q5_raw AS (
                SELECT
                    inst_id, year,
                    TRY_CAST(data AS DOUBLE) AS clinical_trials_value
                FROM ({sub_sql})
                WHERE question IN ('{ERA_B_Q5_CANONICAL}', '{ERA_B_Q5_RAW}')
                  AND "row" = 'Total'
            )
            SELECT
                COALESCE(q4_raw.inst_id, q5_raw.inst_id) AS institution_id,
                CAST(COALESCE(q4_raw.year, q5_raw.year) AS INTEGER) AS year,
                q4_raw.med_school_value,
                q5_raw.clinical_trials_value,
                '{source_file_literal}' AS source_file
            FROM q4_raw
            FULL OUTER JOIN q5_raw
              ON q4_raw.inst_id = q5_raw.inst_id
             AND q4_raw.year = q5_raw.year
        """
        q4_q5_year_parts.append(year_extract_sql)

    q4_q5_union_sql = "\nUNION ALL\n".join(f"({p})" for p in q4_q5_year_parts)
    con.execute("DROP TABLE IF EXISTS _stage8_q4_q5")
    con.execute(f"CREATE TEMP TABLE _stage8_q4_q5 AS {q4_q5_union_sql}")

    # --- Build institution-year R&D total at discipline='All' grain --- #
    # Pulled from the assembled panel at the 'All' discipline rollup.
    # Era-A: source_class='all_source', expenditure_type='r&d',
    # discipline_fine='All' (Stage 4 era-A direct 'All' row).
    # Era-B: same filters plus source_questionnaire_no='9+11' (the
    # reconstructed row, not the direct Q14 'r&d_equipment' row or the
    # short-form 'r&d' row at the 'All' grain). Short Form Q2 also
    # ships at discipline_fine='All' for short-form institutions; the
    # attribute table's denominator uses standard-form data only.
    con.execute("DROP TABLE IF EXISTS _stage8_inst_year_total")
    con.execute(
        """
        CREATE TEMP TABLE _stage8_inst_year_total AS
        SELECT
            institution_id,
            year,
            era,
            value AS inst_year_total_rd
        FROM _stage8_panel
        WHERE source_class = 'all_source'
          AND expenditure_type = 'r&d'
          AND form_type = 'standard'
          AND discipline_fine = 'All'
          AND (
              -- Era-A direct read.
              (era = 'A')
           OR -- Era-B reconstructed row (qno='9+11').
              (era = 'B' AND source_questionnaire_no = '9+11')
          )
        """
    )

    # --- Assemble attribute table -------------------------------- #
    # One row per distinct (institution_id, year) in the panel.
    # Era-A rows: med_school_*/clinical_trials_* NULL (era-B-only Qs).
    # Era-B rows: pivoted Q4/Q5 values + computed shares.
    attribute_sql = """
        WITH distinct_inst_year AS (
            SELECT DISTINCT institution_id, year, era
            FROM _stage8_panel
        )
        SELECT
            d.institution_id                              AS institution_id,
            d.year                                         AS year,
            d.era                                          AS era,
            -- med_school_share / clinical_trials_share: only era-B
            -- emits Q4/Q5; era-A computes to NULL by construction.
            CASE
                WHEN d.era = 'B'
                  AND t.inst_year_total_rd IS NOT NULL
                  AND t.inst_year_total_rd > 0
                THEN q.med_school_value / t.inst_year_total_rd
                ELSE NULL
            END                                            AS med_school_share,
            CASE
                WHEN d.era = 'B'
                  AND t.inst_year_total_rd IS NOT NULL
                  AND t.inst_year_total_rd > 0
                THEN q.clinical_trials_value / t.inst_year_total_rd
                ELSE NULL
            END                                            AS clinical_trials_share,
            q.med_school_value                             AS med_school_value,
            q.clinical_trials_value                        AS clinical_trials_value,
            -- source_file: era-B uses the year-specific HERD CSV;
            -- era-A uses the era-A naming pattern (herd_YYYY.csv).
            COALESCE(q.source_file,
                     'herd_' || CAST(d.year AS VARCHAR) || '.csv')
                                                           AS source_file,
            CAST(NULL AS VARCHAR)                          AS notes
        FROM distinct_inst_year d
        LEFT JOIN _stage8_q4_q5 q
          ON q.institution_id = d.institution_id
         AND q.year = d.year
        LEFT JOIN _stage8_inst_year_total t
          ON t.institution_id = d.institution_id
         AND t.year = d.year
        ORDER BY d.year, d.institution_id
    """
    return con.sql(attribute_sql)


def assert_panel_invariants(
    panel_rel: duckdb.DuckDBPyRelation,
    con: duckdb.DuckDBPyConnection,
) -> None:
    """Stage 9: sanity assertions before parquet write.

    SQL-level assertions over the assembled panel relation (Stage 7
    output). Fail-loud discipline: any assertion violation raises
    RuntimeError with the offending tuple(s) named, before any parquet
    is written. The build cannot produce a deposit-quality parquet
    that violates these invariants.

    Assertions per scoping doc §6.2 Stage 9 (revised 2026-05-10 PM for
    the W4 amendment — three-tier `unspecified_zero` defense replacing
    the original "FY-2017-only / non-Total-only" assertion):

      1. Row count > 0.
      2. No `discipline_fine='UNMAPPED_*'` rows (Stage 3 already raises
         on unmapped; this is defense-in-depth).
      3. `era='A'` for years <= ERA_A_LAST_YEAR (2009); `era='B'` for
         years > ERA_A_LAST_YEAR. No exceptions.
      4. `source_class` is one of {all_source, federal, nonfederal}.
      5. `expenditure_type` is one of {r&d, r&d_equipment}.
      6. `form_type` is one of {standard, short}.
      7. `quality_flag` is one of {reported, imputed, estimated,
         unspecified_zero}; no NULL.
      8. **Three-tier `unspecified_zero` defense** (locked 2026-05-10 PM):
         (a) Era-A `unspecified_zero` rows are NOT expected (era-A
             never emits `status='u'` empirically); any raise.
         (b) Era-B `unspecified_zero` rows in years outside 2010-2022
             are NOT expected (FY 2023+ retired the encoding); any
             raise.
         (c) Era-B 2010-2022 `unspecified_zero` rows are allowed per
             the corrected baseline.
      9. Era-B reconstruction identity (where both Q9 and Q11 component
         rows exist at (institution_id, year, discipline_fine), the
         reconstructed all_source row's value equals Q9.value +
         Q11.value within rounding tolerance).
     10. Era-B reconstruction propagation (the propagated quality_flag
         on reconstructed rows is the least-good of the present-side
         component flags per the locked ordering; assertion catches
         integration bugs).

    Parameters
    ----------
    panel_rel : DuckDBPyRelation
        Stage 7 assembled panel relation (21 columns; era-A direct
        rows + era-B per-component rows + era-B reconstructed all_source
        rows).
    con : DuckDBPyConnection
        Connection used for assertion-side SQL queries.

    Raises
    ------
    RuntimeError
        On any assertion violation. The exception message names the
        offending tuple(s) so the operator can disposition.
    """
    # Materialize the panel into a temp table for repeated assertion
    # scans without re-evaluating the UNION ALL each time.
    con.execute("DROP TABLE IF EXISTS _stage9_panel")
    con.execute(f"CREATE TEMP TABLE _stage9_panel AS {panel_rel.sql_query()}")

    # Assertion 1: row count > 0.
    n_rows = con.execute("SELECT COUNT(*) FROM _stage9_panel").fetchone()[0]
    if n_rows == 0:
        raise RuntimeError("Stage 9 assertion 1: panel has zero rows.")

    # Assertion 2: no UNMAPPED discipline_fine.
    n_unmapped = con.execute(
        """
        SELECT COUNT(*) FROM _stage9_panel
        WHERE discipline_fine LIKE 'UNMAPPED_%'
        """
    ).fetchone()[0]
    if n_unmapped > 0:
        raise RuntimeError(
            f"Stage 9 assertion 2: {n_unmapped} rows carry "
            "`discipline_fine` matching 'UNMAPPED_*'. Stage 3 "
            "should have raised; this is defense-in-depth."
        )

    # Assertion 3: era matches year.
    bad_era = con.execute(
        f"""
        SELECT DISTINCT year, era
        FROM _stage9_panel
        WHERE (year <= {ERA_A_LAST_YEAR} AND era != 'A')
           OR (year >  {ERA_A_LAST_YEAR} AND era != 'B')
        ORDER BY year, era
        LIMIT 10
        """
    ).fetchall()
    if bad_era:
        sample = "\n".join(f"  year={r[0]} era={r[1]!r}" for r in bad_era)
        raise RuntimeError(
            "Stage 9 assertion 3: era flag does not match year "
            f"(ERA_A_LAST_YEAR={ERA_A_LAST_YEAR}):\n{sample}"
        )

    # Assertion 4: source_class enum.
    bad_sc = con.execute(
        """
        SELECT DISTINCT source_class
        FROM _stage9_panel
        WHERE source_class NOT IN ('all_source', 'federal', 'nonfederal')
        ORDER BY source_class
        LIMIT 10
        """
    ).fetchall()
    if bad_sc:
        raise RuntimeError(
            "Stage 9 assertion 4: source_class values outside "
            f"{{all_source, federal, nonfederal}}: {bad_sc!r}"
        )

    # Assertion 5: expenditure_type enum.
    bad_et = con.execute(
        """
        SELECT DISTINCT expenditure_type
        FROM _stage9_panel
        WHERE expenditure_type NOT IN ('r&d', 'r&d_equipment')
        ORDER BY expenditure_type
        LIMIT 10
        """
    ).fetchall()
    if bad_et:
        raise RuntimeError(
            "Stage 9 assertion 5: expenditure_type values outside "
            f"{{r&d, r&d_equipment}}: {bad_et!r}"
        )

    # Assertion 6: form_type enum.
    bad_ft = con.execute(
        """
        SELECT DISTINCT form_type
        FROM _stage9_panel
        WHERE form_type NOT IN ('standard', 'short')
        ORDER BY form_type
        LIMIT 10
        """
    ).fetchall()
    if bad_ft:
        raise RuntimeError(
            "Stage 9 assertion 6: form_type values outside "
            f"{{standard, short}}: {bad_ft!r}"
        )

    # Assertion 7: quality_flag enum + no NULL.
    bad_qf = con.execute(
        f"""
        SELECT DISTINCT quality_flag
        FROM _stage9_panel
        WHERE quality_flag IS NULL
           OR quality_flag NOT IN {QUALITY_FLAG_ENUM!r}
        ORDER BY quality_flag
        LIMIT 10
        """
    ).fetchall()
    if bad_qf:
        raise RuntimeError(
            "Stage 9 assertion 7: quality_flag values outside "
            f"{QUALITY_FLAG_ENUM!r} (or NULL): {bad_qf!r}"
        )

    # Assertion 8: three-tier unspecified_zero defense (locked 2026-05-10 PM).
    #
    # Tier (a): era-A unspecified_zero rows raise.
    bad_8a = con.execute(
        """
        SELECT year, institution_id, source_question_canonical,
               source_question_raw, source_questionnaire_no, COUNT(*) AS n
        FROM _stage9_panel
        WHERE era = 'A' AND quality_flag = 'unspecified_zero'
        GROUP BY year, institution_id, source_question_canonical,
                 source_question_raw, source_questionnaire_no
        ORDER BY year, institution_id
        LIMIT 20
        """
    ).fetchall()
    if bad_8a:
        sample = "\n".join(
            f"  year={r[0]} inst={r[1]!r} qno={r[4]!r} "
            f"raw_q={(r[3] or '')[:40]!r} n={r[5]}"
            for r in bad_8a
        )
        raise RuntimeError(
            "Stage 9 assertion 8(a): era-A `unspecified_zero` rows "
            "are NOT expected per the W4 corrected baseline "
            "(2026-05-10 PM lock; era-A does not emit `status='u'` "
            "empirically across 1973-2009 per "
            "etl/spikes/probe_status_c_codeset.py). Surface as "
            f"real finding before proceeding:\n{sample}"
        )

    # Tier (b): era-B unspecified_zero rows outside 2010-2022 raise.
    bad_8b = con.execute(
        """
        SELECT year, institution_id, source_question_canonical,
               source_question_raw, source_questionnaire_no, COUNT(*) AS n
        FROM _stage9_panel
        WHERE era = 'B'
          AND quality_flag = 'unspecified_zero'
          AND (year < 2010 OR year > 2022)
        GROUP BY year, institution_id, source_question_canonical,
                 source_question_raw, source_questionnaire_no
        ORDER BY year, institution_id
        LIMIT 20
        """
    ).fetchall()
    if bad_8b:
        sample = "\n".join(
            f"  year={r[0]} inst={r[1]!r} qno={r[4]!r} "
            f"raw_q={(r[3] or '')[:40]!r} n={r[5]}"
            for r in bad_8b
        )
        raise RuntimeError(
            "Stage 9 assertion 8(b): era-B `unspecified_zero` rows "
            "in years outside 2010-2022 are NOT expected per the W4 "
            "corrected baseline (2026-05-10 PM lock; FY 2023+ "
            "retired the encoding per "
            "validation/reports/herd_null_characterization_findings.md "
            "§7.5 retirement evidence). Resumption signal — surface "
            f"and panel reconvene before proceeding:\n{sample}"
        )

    # Tier (c): era-B 2010-2022 unspecified_zero is allowed; no
    # assertion fires here (assertion is "should not exist outside
    # this scope," which is covered by 8(a) and 8(b)).

    # Assertion 9: era-B reconstruction identity. For every (inst,
    # year, disc) where both Q9 (source_class='federal', exp_type=
    # 'r&d', form='standard') and Q11 (source_class='nonfederal',
    # exp_type='r&d', form='standard') rows exist, the corresponding
    # reconstructed all_source row (source_class='all_source',
    # exp_type='r&d', form='standard', source_questionnaire_no=
    # '9+11') value equals Q9.value + Q11.value within rounding.
    bad_9 = con.execute(
        """
        WITH q9 AS (
            SELECT institution_id, year, discipline_fine,
                   value AS q9_value
            FROM _stage9_panel
            WHERE era = 'B' AND source_class = 'federal'
              AND expenditure_type = 'r&d' AND form_type = 'standard'
        ),
        q11 AS (
            SELECT institution_id, year, discipline_fine,
                   value AS q11_value
            FROM _stage9_panel
            WHERE era = 'B' AND source_class = 'nonfederal'
              AND expenditure_type = 'r&d' AND form_type = 'standard'
        ),
        recon AS (
            SELECT institution_id, year, discipline_fine,
                   value AS recon_value
            FROM _stage9_panel
            WHERE era = 'B' AND source_class = 'all_source'
              AND expenditure_type = 'r&d' AND form_type = 'standard'
              AND source_questionnaire_no = '9+11'
        )
        SELECT q9.institution_id, q9.year, q9.discipline_fine,
               q9.q9_value, q11.q11_value, recon.recon_value,
               ABS(recon.recon_value - (q9.q9_value + q11.q11_value))
                   AS abs_residual
        FROM q9
        INNER JOIN q11
          ON q9.institution_id = q11.institution_id
         AND q9.year = q11.year
         AND q9.discipline_fine = q11.discipline_fine
        INNER JOIN recon
          ON recon.institution_id = q9.institution_id
         AND recon.year = q9.year
         AND recon.discipline_fine = q9.discipline_fine
        WHERE ABS(recon.recon_value - (q9.q9_value + q11.q11_value)) > 0.001
        ORDER BY abs_residual DESC
        LIMIT 20
        """
    ).fetchall()
    if bad_9:
        sample = "\n".join(
            f"  inst={r[0]!r} year={r[1]} disc={r[2][:30]!r} "
            f"q9={r[3]} + q11={r[4]} = {r[3]+r[4]}; "
            f"recon={r[5]}; abs_residual={r[6]}"
            for r in bad_9
        )
        raise RuntimeError(
            "Stage 9 assertion 9: era-B reconstruction identity "
            "violated (Q9.value + Q11.value != recon.value within "
            f"rounding) on {len(bad_9)} cells. The reconstruction "
            "rule is preserved by construction; assertion fail "
            f"indicates integration bug:\n{sample}"
        )

    # Assertion 10: era-B reconstruction propagation. For each
    # reconstructed all_source row (qno='9+11'), the propagated
    # quality_flag is the least-good of the present-side component
    # flags. SQL implementation: walk the worst-to-best ordering
    # and check that recon.flag matches the expected least-good
    # against the component flags.
    bad_10 = con.execute(
        f"""
        WITH q9 AS (
            SELECT institution_id, year, discipline_fine,
                   quality_flag AS q9_flag
            FROM _stage9_panel
            WHERE era = 'B' AND source_class = 'federal'
              AND expenditure_type = 'r&d' AND form_type = 'standard'
        ),
        q11 AS (
            SELECT institution_id, year, discipline_fine,
                   quality_flag AS q11_flag
            FROM _stage9_panel
            WHERE era = 'B' AND source_class = 'nonfederal'
              AND expenditure_type = 'r&d' AND form_type = 'standard'
        ),
        recon AS (
            SELECT institution_id, year, discipline_fine,
                   quality_flag AS recon_flag
            FROM _stage9_panel
            WHERE era = 'B' AND source_class = 'all_source'
              AND expenditure_type = 'r&d' AND form_type = 'standard'
              AND source_questionnaire_no = '9+11'
        ),
        joined AS (
            -- FULL OUTER JOIN on (inst, year, disc), then match
            -- against the recon row at the same grain.
            SELECT
                COALESCE(q9.institution_id, q11.institution_id) AS institution_id,
                COALESCE(q9.year, q11.year) AS year,
                COALESCE(q9.discipline_fine, q11.discipline_fine) AS discipline_fine,
                q9.q9_flag,
                q11.q11_flag,
                CASE
                    WHEN q9.q9_flag IS NULL THEN q11.q11_flag
                    WHEN q11.q11_flag IS NULL THEN q9.q9_flag
                    WHEN q9.q9_flag = 'unspecified_zero'
                      OR q11.q11_flag = 'unspecified_zero'
                        THEN 'unspecified_zero'
                    WHEN q9.q9_flag = 'estimated'
                      OR q11.q11_flag = 'estimated'
                        THEN 'estimated'
                    WHEN q9.q9_flag = 'imputed'
                      OR q11.q11_flag = 'imputed'
                        THEN 'imputed'
                    ELSE 'reported'
                END AS expected_flag
            FROM q9
            FULL OUTER JOIN q11
              ON q9.institution_id = q11.institution_id
             AND q9.year = q11.year
             AND q9.discipline_fine = q11.discipline_fine
            WHERE q9.institution_id IS NOT NULL
               OR q11.institution_id IS NOT NULL
        )
        SELECT j.institution_id, j.year, j.discipline_fine,
               j.q9_flag, j.q11_flag, j.expected_flag, recon.recon_flag
        FROM joined j
        INNER JOIN recon
          ON recon.institution_id = j.institution_id
         AND recon.year = j.year
         AND recon.discipline_fine = j.discipline_fine
        WHERE recon.recon_flag != j.expected_flag
        ORDER BY j.year, j.institution_id
        LIMIT 20
        """
    ).fetchall()
    if bad_10:
        sample = "\n".join(
            f"  inst={r[0]!r} year={r[1]} disc={r[2][:30]!r} "
            f"q9_flag={r[3]!r} q11_flag={r[4]!r} "
            f"expected={r[5]!r} actual_recon={r[6]!r}"
            for r in bad_10
        )
        raise RuntimeError(
            "Stage 9 assertion 10: era-B reconstruction propagation "
            "violated. The propagated quality_flag should be the "
            "least-good of the present-side component flags per the "
            "locked ordering (worst -> best: unspecified_zero < "
            "estimated < imputed < reported). The propagation rule "
            "is preserved by construction; assertion fail indicates "
            f"integration bug:\n{sample}"
        )

    # All assertions pass.
    return None


def write_parquet(
    panel_rel: duckdb.DuckDBPyRelation,
    out_path: Path,
    con: duckdb.DuckDBPyConnection,
) -> Path:
    """Stage 10: parquet write via DuckDB native writer.

    No pyarrow dependency (per personnel sibling pattern). Creates the
    output directory if absent. Returns the written path.

    Parameters
    ----------
    panel_rel : DuckDBPyRelation
        Relation to write (the assembled panel or the attribute table).
    out_path : Path
        Absolute output path. Parent directory auto-created.
    con : DuckDBPyConnection
        Connection used to execute the COPY statement.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # Use DuckDB's COPY ... TO ... (FORMAT PARQUET) native writer.
    # Single-quote escape: DuckDB COPY tolerates POSIX-style paths on
    # Windows (forward slashes); use as_posix() to normalize.
    con.execute(
        f"""
        COPY (
            {panel_rel.sql_query()}
        ) TO '{out_path.as_posix()}' (FORMAT PARQUET)
        """
    )
    return out_path


# --------------------------------------------------------------------------- #
# Smoke test (HD 2.4.a; written here, NOT invoked from main() this round)
# --------------------------------------------------------------------------- #


def smoke_test_stages_1_3(
    con: Optional[duckdb.DuckDBPyConnection] = None,
    years: tuple[int, ...] = (2008, 2024),
) -> None:
    """Run Stages 1-3 end-to-end on representative years; print sanity.

    NOT invoked from main() in HD 2.4.a — the maintainer greenlights this
    smoke-test execution after reviewing the skeleton and Stages 1-3
    code. To run manually after greenlight:

        from etl.build_herd_panel import smoke_test_stages_1_3
        smoke_test_stages_1_3()

    Or invoke with ``RUN_STAGES_BEYOND_3=False`` and call this function
    directly from a Python REPL.

    What it checks (per dispatch §7):
      - FY 2008 (era-A representative): row counts after Stages 1-3,
        confirms only era-A field-level / equipment questions survive.
      - FY 2024 (era-B representative): row counts after Stages 1-3,
        confirms Q4/Q5/Q9/Q11/Q14 all survive Stage 2.
      - Per-era distinct discipline_coarse buckets after Stage 3.
      - quality_flag distribution: counts per (year, quality_flag).
      - Unmapped row label count: must be zero (the assertion in Stage 3
        already raises if non-zero, so this is informational).

    Stops at findings; does not write any artifact.
    """
    if con is None:
        con = duckdb.connect()

    t_start = time.perf_counter()

    _load_discipline_fine_crosswalk(con)
    _load_question_map_crosswalk(con)

    print("=" * 78)
    print("HD 2.4.a smoke test - Stages 1-3 on representative years")
    print("=" * 78)

    for year in years:
        era = "A" if year <= ERA_A_LAST_YEAR else "B"
        print(f"\n--- FY {year} (era {era}) ---")
        rel1 = load_year(year, con)
        n1 = rel1.aggregate("COUNT(*) AS n").fetchone()[0]
        print(f"  Stage 1 raw rows: {n1:>9,}")

        rel2 = filter_in_scope_questions(rel1, era, con)
        n2 = rel2.aggregate("COUNT(*) AS n").fetchone()[0]
        print(f"  Stage 2 in-scope rows: {n2:>9,}")
        # Show distinct in-scope questions with per-question row counts.
        # `question` is the Stage-1-3-grain analog of `source_class`
        # (derived at Stage 5+: Q9 -> federal, Q11 -> nonfederal,
        # Q14 -> all_source/equipment, era-A field/equipment ->
        # all_source). Per-question counts make the Q4/Q5/Q14 raw-label
        # filter materializing the expected row sets visible at a glance.
        per_q = (
            rel2.aggregate(
                "question, COUNT(*) AS n", group_expr="question"
            )
            .order("question")
            .fetchall()
        )
        for q, qn in per_q:
            print(f"    question={q!r:<70s} n={qn:,}")

        rel3 = normalize_discipline(rel2, con)
        n3 = rel3.aggregate("COUNT(*) AS n").fetchone()[0]
        print(f"  Stage 3 joined rows: {n3:>9,}")

        # Distinct discipline_coarse (excluding NULL — Q4/Q5 carry NULL
        # by design at Stage 3).
        coarse = (
            rel3.filter("discipline_coarse IS NOT NULL")
            .project("discipline_coarse")
            .distinct()
            .order("discipline_coarse")
            .fetchall()
        )
        print(f"  distinct discipline_coarse (non-NULL): {len(coarse)}")
        for c in coarse:
            print(f"    {c[0]!r}")

        # quality_flag distribution + imputation share.
        flag_dist = (
            rel3.aggregate(
                "quality_flag, COUNT(*) AS n",
                group_expr="quality_flag",
            )
            .order("quality_flag")
            .fetchall()
        )
        total_n3 = sum(c for _, c in flag_dist)
        print("  quality_flag distribution:")
        for f, c in flag_dist:
            share = (c / total_n3 * 100) if total_n3 else 0.0
            print(f"    {f!r:>22s}  n={c:>9,}  ({share:5.2f}%)")

        # Three example rows per question (Stage-1-3-grain analog of
        # source_class). Pulls representative rows so the maintainer can
        # eyeball that the right row text + column axis is materializing
        # for each in-scope question.
        print("  Sample rows (3 per question):")
        sample_sql = f"""
        WITH ranked AS (
            SELECT
                question,
                questionnaire_no,
                "row",
                "column",
                data,
                status,
                discipline_coarse,
                discipline_fine,
                quality_flag,
                ROW_NUMBER() OVER (
                    PARTITION BY question ORDER BY questionnaire_no, "row", "column"
                ) AS rn
            FROM ({rel3.sql_query()})
        )
        SELECT
            question, questionnaire_no, "row", "column",
            data, status, discipline_coarse, discipline_fine, quality_flag
        FROM ranked
        WHERE rn <= 3
        ORDER BY question, questionnaire_no, "row", "column"
        """
        samples = con.sql(sample_sql).fetchall()
        for s in samples:
            (q, qno, rowtxt, coltxt, dat, sta, dcoarse, dfine, qflag) = s
            print(
                f"    q={q[:50]!r:<52s} qno={qno!r:<8s} "
                f"row={(rowtxt or '')[:38]!r:<40s} col={coltxt!r:<28s} "
                f"data={dat!r:<10s} status={sta!r:<5s} "
                f"coarse={(dcoarse or '')[:18]!r:<20s} flag={qflag!r}"
            )

    elapsed = time.perf_counter() - t_start

    print("\n--- Smoke-test boundaries ---")
    print("  No assertions raised: Stage 3 crosswalk-coverage and "
          "status-codeset checks passed for all years tested.")
    print("  No parquet written: this is a Stages-1-3-only smoke test.")
    print(f"  Wall time (full smoke test, all years): {elapsed:.2f}s")


def smoke_test_stage_4(
    con: Optional[duckdb.DuckDBPyConnection] = None,
) -> None:
    """Run Stage 4 end-to-end on PANEL_YEARS; print sanity (HD 2.4.b).

    Stage 4 emits panel rows only for era-A years in the panel range
    (PANEL_FIRST_YEAR=1975 through ERA_A_LAST_YEAR=2009; FY 1972 / 1973
    / 1974 are carved out per scoping doc §3(a) and HD 2.4.b round 1
    Vision verdict 2026-05-10 Category II option (a)). For era-B years
    (2010-2024), the smoke test runs Stages 1-3 to surface a *raw
    in-scope row count* preview alongside era-A panel rows, so the
    maintainer can see the full panel + era-B-preview shape in one
    report. Era-B preview is intentionally Stages-1-3-only because
    Stage 5 has not yet shipped at HD 2.4.b round 1 run time.

    What it checks:
      - Per-year row count distribution 1975-2024 (era-A panel rows
        post-Stage-4; era-B Stage-2 in-scope row counts as preview).
      - Pre-1981 fingerprint: rows for 1975-1980 are expected to come
        from `Expenditures by S&E field` only (no Item 3 equipment
        question; the equipment Item 3 added FY 1981 per FY24 Guide
        page 19). 1975-1978 emits only `*, all` rollup rows; 1979
        onward emits leaves. Surface the row-count discontinuity
        explicitly. (FY 1973-1974 are carved out and do not appear
        in the panel; the pre-1981 fingerprint as observed in the
        deposit panel begins at 1975.)
      - Distinct discipline_coarse buckets observed across era-A.
      - quality_flag distribution across era-A years.
      - Schema column types and order (matches locked §1 21-column
        schema).
      - Three example rows per era-A decade (1970s, 1980s, 1990s, 2000s).
      - expenditure_type distribution across era-A (r&d vs r&d_equipment;
        equipment expected only 1981-2009).
      - Wall time.

    Stops at findings; does not write any artifact.
    """
    if con is None:
        con = duckdb.connect()

    t_start = time.perf_counter()

    _load_discipline_fine_crosswalk(con)
    _load_question_map_crosswalk(con)

    print("=" * 78)
    print("HD 2.4.b Stage 4 smoke test - era-A direct rows + era-B preview")
    print("=" * 78)

    # --- Stage 4 build ----------------------------------------------------- #
    t_build = time.perf_counter()
    stage4_rel = build_era_a_rows(PANEL_YEARS, con)
    # Materialize into a temp table so we can run multiple aggregates without
    # re-scanning the 37-year UNION ALL each time.
    con.execute("DROP TABLE IF EXISTS _stage4_panel")
    con.execute(f"CREATE TEMP TABLE _stage4_panel AS {stage4_rel.sql_query()}")
    build_elapsed = time.perf_counter() - t_build

    n_total = con.execute("SELECT COUNT(*) FROM _stage4_panel").fetchone()[0]
    print(f"\nStage 4 panel rows (era-A, {PANEL_FIRST_YEAR}-{ERA_A_LAST_YEAR}): "
          f"{n_total:,}")
    print(f"Stage 4 build wall time: {build_elapsed:.2f}s")
    print(f"Year scope: PANEL_YEARS=range({PANEL_FIRST_YEAR}, 2025); "
          f"era-A subset = [{PANEL_FIRST_YEAR}, {ERA_A_LAST_YEAR}].")
    print("Carve-out: 1972 (no field-level question) and 1973-1974 "
          "(Guide-undocumented status='c'; HD 2.4.b round 1 Vision verdict "
          "2026-05-10) preserved as raw artifacts only.")

    # --- Schema check: column order and types ------------------------------ #
    expected_schema = [
        ("institution_id", "VARCHAR"),
        ("fice", "VARCHAR"),
        ("ncses_inst_id", "VARCHAR"),
        ("ipeds_unitid", "VARCHAR"),
        ("inst_name_long", "VARCHAR"),
        ("year", "INTEGER"),
        ("era", "VARCHAR"),
        ("discipline_coarse", "VARCHAR"),
        ("discipline_fine", "VARCHAR"),
        ("expenditure_type", "VARCHAR"),
        ("source_class", "VARCHAR"),
        ("form_type", "VARCHAR"),
        ("value", "DOUBLE"),
        ("unit", "VARCHAR"),
        ("value_type", "VARCHAR"),
        ("quality_flag", "VARCHAR"),
        ("source_questionnaire_no", "VARCHAR"),
        ("source_question_canonical", "VARCHAR"),
        ("source_question_raw", "VARCHAR"),
        ("source_file", "VARCHAR"),
        ("notes", "VARCHAR"),
    ]
    actual_schema = con.execute("DESCRIBE _stage4_panel").fetchall()
    actual_pairs = [(r[0], r[1]) for r in actual_schema]
    print(f"\n--- Schema check ({len(actual_pairs)} columns) ---")
    if actual_pairs == expected_schema:
        print("  Column order and types match locked §1 schema (21 columns). PASS")
    else:
        print("  SCHEMA DRIFT — expected vs actual:")
        for i, (e, a) in enumerate(zip(expected_schema, actual_pairs)):
            mark = "OK" if e == a else "DRIFT"
            print(f"    [{i:2d}] {mark:5s}  expected={e}  actual={a}")
        if len(expected_schema) != len(actual_pairs):
            print(f"  Column count: expected={len(expected_schema)} "
                  f"actual={len(actual_pairs)}")

    # --- Per-year row count distribution: era-A (panel) ------------------- #
    print(f"\n--- Per-year era-A panel row counts ({PANEL_FIRST_YEAR}-{ERA_A_LAST_YEAR}) ---")
    print("  year   total   r&d    r&d_eq  notes")
    rows = con.execute(
        """
        SELECT
            year,
            COUNT(*)                                                     AS total,
            COUNT(*) FILTER (WHERE expenditure_type = 'r&d')             AS rd,
            COUNT(*) FILTER (WHERE expenditure_type = 'r&d_equipment')   AS rd_eq
        FROM _stage4_panel
        GROUP BY year
        ORDER BY year
        """
    ).fetchall()
    prev_total = None
    for (year, total, rd, rd_eq) in rows:
        marker = ""
        if prev_total is not None:
            delta = total - prev_total
            if abs(delta) > max(50, prev_total * 0.20):
                marker = f"  <-- discontinuity (delta={delta:+,})"
        notable = ""
        if year == 1979:
            notable = " (pre-1981 fingerprint: leaves first appear)"
        elif year == 1981:
            notable = " (Item 3 equipment added per FY24 Guide page 19)"
        elif year == 2003:
            notable = " (Items 2A/2B per FY24 Guide pages 15/19)"
        print(f"  {year}  {total:>5,}   {rd:>5,}  {rd_eq:>5,}{marker}{notable}")
        prev_total = total

    # --- Pre-1981 fingerprint check --------------------------------------- #
    print("\n--- Pre-1981 fingerprint check (scoping doc §3(b)) ---")
    print(f"  (1975-1978: rollup-only fingerprint; 1979 onward: leaves emerge.")
    print(f"   FY 1973-1974 are carved out per the codeset disposition; the")
    print(f"   pre-1981 fingerprint window in the panel is therefore 1975-1980.)")
    fp_rows = con.execute(
        """
        SELECT
            year,
            COUNT(*)                                                AS total,
            COUNT(*) FILTER (WHERE discipline_fine LIKE '%, all')   AS rollup,
            COUNT(*) FILTER (WHERE discipline_fine NOT LIKE '%, all'
                             AND discipline_fine NOT IN ('All', 'All R&D fields total'))
                                                                    AS leaves,
            COUNT(*) FILTER (WHERE discipline_fine = 'All')         AS grand_all
        FROM _stage4_panel
        WHERE year BETWEEN 1975 AND 1985
        GROUP BY year
        ORDER BY year
        """
    ).fetchall()
    print("  year   total   rollup  leaves  grand_All")
    for (yr, total, rollup, leaves, grand_all) in fp_rows:
        print(f"  {yr}  {total:>5,}   {rollup:>5,}   {leaves:>5,}   {grand_all:>5,}")

    # --- Distinct discipline_coarse buckets across era-A ------------------ #
    print("\n--- Distinct discipline_coarse buckets (era-A panel) ---")
    coarse = con.execute(
        """
        SELECT discipline_coarse, COUNT(*) AS n,
               MIN(year) AS first_year, MAX(year) AS last_year
        FROM _stage4_panel
        WHERE discipline_coarse IS NOT NULL
        GROUP BY discipline_coarse
        ORDER BY discipline_coarse
        """
    ).fetchall()
    print(f"  {len(coarse)} distinct buckets")
    for (c, n, fy, ly) in coarse:
        print(f"    {c!r:>40s}  n={n:>6,}  years=[{fy}-{ly}]")

    # --- quality_flag distribution across era-A --------------------------- #
    print("\n--- quality_flag distribution (era-A panel) ---")
    flag_dist = con.execute(
        """
        SELECT quality_flag, COUNT(*) AS n
        FROM _stage4_panel
        GROUP BY quality_flag
        ORDER BY n DESC
        """
    ).fetchall()
    flag_total = sum(c for _, c in flag_dist)
    for (f, c) in flag_dist:
        share = (c / flag_total * 100) if flag_total else 0.0
        print(f"    {f!r:>22s}  n={c:>9,}  ({share:5.2f}%)")

    # --- expenditure_type distribution ------------------------------------ #
    print("\n--- expenditure_type distribution (era-A panel) ---")
    et_dist = con.execute(
        """
        SELECT expenditure_type, COUNT(*) AS n,
               MIN(year) AS first_year, MAX(year) AS last_year
        FROM _stage4_panel
        GROUP BY expenditure_type
        ORDER BY expenditure_type
        """
    ).fetchall()
    for (et, n, fy, ly) in et_dist:
        print(f"    {et!r:>16s}  n={n:>9,}  years=[{fy}-{ly}]")

    # --- Three example rows per decade ------------------------------------ #
    print("\n--- Sample rows: 3 per era-A decade ---")
    decades = [(1975, 1979, "late-1970s"), (1980, 1989, "1980s"),
               (1990, 1999, "1990s"), (2000, 2009, "2000s")]
    for (start, end, label) in decades:
        print(f"\n  {label} ({start}-{end}):")
        sample = con.execute(
            f"""
            WITH ranked AS (
                SELECT *,
                       ROW_NUMBER() OVER (ORDER BY year, institution_id,
                                          discipline_fine, expenditure_type) AS rn
                FROM _stage4_panel
                WHERE year BETWEEN {start} AND {end}
            )
            SELECT year, institution_id, discipline_coarse, discipline_fine,
                   expenditure_type, value, quality_flag,
                   source_question_canonical
            FROM ranked
            WHERE rn IN (1, 2, 3)
            """
        ).fetchall()
        for (yr, iid, dc, df, et, v, qf, sq) in sample:
            sq_short = sq[:35] if sq else ''
            df_short = (df or '')[:30]
            print(f"    yr={yr} inst={iid!r:>8s} "
                  f"coarse={(dc or '')[:18]!r:<20s} "
                  f"fine={df_short!r:<32s} "
                  f"et={et!r:<16s} v={v!r:>10s} "
                  f"qf={qf!r:<12s} sq={sq_short!r}")

    # --- Era-B preview: Stage 1+2 row counts (no panel projection yet) --- #
    print("\n--- Era-B preview: Stages 1-2 in-scope row counts (2010-2024) ---")
    print("  (Stage 5 has not shipped yet; this is the raw in-scope")
    print("   row stream Stage 5 will project at HD 2.4.b round 2.)")
    print("  year   in_scope_rows   Q4     Q5     Q9     Q11    Q14")
    for year in range(2010, 2025):
        rel1 = load_year(year, con)
        rel2 = filter_in_scope_questions(rel1, "B", con)
        n_in_scope = rel2.aggregate("COUNT(*) AS n").fetchone()[0]
        # Per-question buckets — match raw + canonical labels.
        per_q = con.execute(
            f"""
            SELECT
                COUNT(*) FILTER (
                    WHERE question IN ('{ERA_B_Q4}', '{ERA_B_Q4_RAW}')
                ),
                COUNT(*) FILTER (
                    WHERE question IN ('{ERA_B_Q5_CANONICAL}', '{ERA_B_Q5_RAW}')
                ),
                COUNT(*) FILTER (WHERE question = '{ERA_B_Q9}'),
                COUNT(*) FILTER (WHERE question = '{ERA_B_Q11}'),
                COUNT(*) FILTER (
                    WHERE question IN ('{ERA_B_Q14}', '{ERA_B_Q14_RAW}')
                )
            FROM ({rel2.sql_query()})
            """
        ).fetchone()
        q4, q5, q9, q11, q14 = per_q
        print(f"  {year}  {n_in_scope:>11,}    "
              f"{q4:>5,}  {q5:>5,}  {q9:>5,}  {q11:>5,}  {q14:>5,}")
    print("\n  Note: Short Form Q2 is NOT in ERA_B_IN_SCOPE_QUESTIONS_CANONICAL")
    print("  and does not appear in the Stage 2 in-scope filter at HD 2.4.b")
    print("  round 1. Surface 3 probe (Short Form Q2 raw structure) runs as")
    print("  a separate scan against rel1 in HD 2.4.b round 2; the projection")
    print("  path Stage 5 needs for short-form rows is locked there.")

    elapsed = time.perf_counter() - t_start
    print("\n--- Smoke-test boundaries ---")
    print(f"  Total wall time (Stage 4 full + era-B preview): {elapsed:.2f}s")
    print("  No parquet written: Stage 4 smoke test only.")


def smoke_test_stage_5(
    con: Optional[duckdb.DuckDBPyConnection] = None,
) -> None:
    """Run Stage 5 end-to-end across 2010-2024; print sanity (HD 2.4.b).

    Stage 5 emits era-B per-component rows: Q9 (federal), Q11
    (nonfederal), Q14 (all_source equipment) from standard-form, plus
    Short Form Q2 (all_source standard r&d) from short-form. Q4/Q5
    carve-outs route to Stage 8 attribute extraction; Stage 5 does NOT
    emit them as panel rows.

    What it checks:
      - Per-year row count distribution 2010-2024 by question (Q9, Q11,
        Q14, Short Form Q2).
      - form_type distribution per year: FY 2012-2024 should show both
        'standard' and 'short' rows; FY 2010-2011 should be 100%
        'standard'.
      - source_class distribution (federal / nonfederal / all_source).
      - expenditure_type distribution (r&d / r&d_equipment).
      - quality_flag distribution per (year, form_type).
      - Three example rows per (year, source_class, expenditure_type,
        form_type) combination at FY 2010, 2017, 2024.
      - Schema column types and order match locked §1 schema.
      - Wall time.

    Stops at findings; does not write any artifact.
    """
    if con is None:
        con = duckdb.connect()

    t_start = time.perf_counter()

    _load_discipline_fine_crosswalk(con)
    _load_question_map_crosswalk(con)

    print("=" * 78)
    print("HD 2.4.b Stage 5 smoke test - era-B per-component + Short Form Q2")
    print("=" * 78)

    # --- Stage 5 build ---------------------------------------------------- #
    t_build = time.perf_counter()
    era_b_years = range(2010, 2025)
    stage5_rel = build_era_b_components(era_b_years, con)
    con.execute("DROP TABLE IF EXISTS _stage5_panel")
    con.execute(f"CREATE TEMP TABLE _stage5_panel AS {stage5_rel.sql_query()}")
    build_elapsed = time.perf_counter() - t_build

    n_total = con.execute("SELECT COUNT(*) FROM _stage5_panel").fetchone()[0]
    print(f"\nStage 5 panel rows (era-B, 2010-2024): {n_total:,}")
    print(f"Stage 5 build wall time: {build_elapsed:.2f}s")

    # --- Schema check ----------------------------------------------------- #
    expected_schema = [
        ("institution_id", "VARCHAR"),
        ("fice", "VARCHAR"),
        ("ncses_inst_id", "VARCHAR"),
        ("ipeds_unitid", "VARCHAR"),
        ("inst_name_long", "VARCHAR"),
        ("year", "INTEGER"),
        ("era", "VARCHAR"),
        ("discipline_coarse", "VARCHAR"),
        ("discipline_fine", "VARCHAR"),
        ("expenditure_type", "VARCHAR"),
        ("source_class", "VARCHAR"),
        ("form_type", "VARCHAR"),
        ("value", "DOUBLE"),
        ("unit", "VARCHAR"),
        ("value_type", "VARCHAR"),
        ("quality_flag", "VARCHAR"),
        ("source_questionnaire_no", "VARCHAR"),
        ("source_question_canonical", "VARCHAR"),
        ("source_question_raw", "VARCHAR"),
        ("source_file", "VARCHAR"),
        ("notes", "VARCHAR"),
    ]
    actual_schema = con.execute("DESCRIBE _stage5_panel").fetchall()
    actual_pairs = [(r[0], r[1]) for r in actual_schema]
    print(f"\n--- Schema check ({len(actual_pairs)} columns) ---")
    if actual_pairs == expected_schema:
        print("  Column order and types match locked §1 schema (21 columns). PASS")
    else:
        print("  SCHEMA DRIFT — expected vs actual:")
        for i, (e, a) in enumerate(zip(expected_schema, actual_pairs)):
            mark = "OK" if e == a else "DRIFT"
            print(f"    [{i:2d}] {mark:5s}  expected={e}  actual={a}")

    # --- Per-year row count distribution by question --------------------- #
    print("\n--- Per-year era-B panel row counts by source_class × form_type ---")
    print("  year   total   fed    nonfed  all-src(eq)  short(all-src)")
    rows = con.execute(
        """
        SELECT
            year,
            COUNT(*)                                                            AS total,
            COUNT(*) FILTER (WHERE source_class = 'federal'
                             AND form_type = 'standard')                        AS fed,
            COUNT(*) FILTER (WHERE source_class = 'nonfederal'
                             AND form_type = 'standard')                        AS nonfed,
            COUNT(*) FILTER (WHERE source_class = 'all_source'
                             AND form_type = 'standard'
                             AND expenditure_type = 'r&d_equipment')            AS allsrc_eq,
            COUNT(*) FILTER (WHERE form_type = 'short')                         AS short_all
        FROM _stage5_panel
        GROUP BY year
        ORDER BY year
        """
    ).fetchall()
    for (year, total, fed, nonfed, allsrc_eq, short_all) in rows:
        marker = ""
        if year == 2012:
            marker = " (Short Form Q2 begins)"
        print(f"  {year}  {total:>6,}   {fed:>5,}  {nonfed:>5,}  "
              f"{allsrc_eq:>5,}        {short_all:>5,}{marker}")

    # --- form_type distribution ----------------------------------------- #
    print("\n--- form_type distribution per year ---")
    ft_rows = con.execute(
        """
        SELECT year, form_type, COUNT(*) AS n
        FROM _stage5_panel
        GROUP BY year, form_type
        ORDER BY year, form_type
        """
    ).fetchall()
    cur_year = None
    for (yr, ft, n) in ft_rows:
        if yr != cur_year:
            print(f"  FY {yr}:")
            cur_year = yr
        print(f"    {ft!r:>12s}  n={n:>6,}")

    # --- source_class distribution -------------------------------------- #
    print("\n--- source_class distribution ---")
    sc_rows = con.execute(
        """
        SELECT source_class, COUNT(*) AS n
        FROM _stage5_panel
        GROUP BY source_class
        ORDER BY n DESC
        """
    ).fetchall()
    total_n = sum(n for _, n in sc_rows)
    for (sc, n) in sc_rows:
        share = (n / total_n * 100) if total_n else 0.0
        print(f"    {sc!r:>12s}  n={n:>7,}  ({share:5.2f}%)")

    # --- expenditure_type distribution ---------------------------------- #
    print("\n--- expenditure_type distribution ---")
    et_rows = con.execute(
        """
        SELECT expenditure_type, COUNT(*) AS n
        FROM _stage5_panel
        GROUP BY expenditure_type
        ORDER BY n DESC
        """
    ).fetchall()
    for (et, n) in et_rows:
        share = (n / total_n * 100) if total_n else 0.0
        print(f"    {et!r:>16s}  n={n:>7,}  ({share:5.2f}%)")

    # --- quality_flag distribution by form_type ------------------------- #
    print("\n--- quality_flag distribution by form_type ---")
    qf_rows = con.execute(
        """
        SELECT form_type, quality_flag, COUNT(*) AS n
        FROM _stage5_panel
        GROUP BY form_type, quality_flag
        ORDER BY form_type, n DESC
        """
    ).fetchall()
    for (ft, qf, n) in qf_rows:
        print(f"    {ft!r:>12s}  {qf!r:>20s}  n={n:>7,}")

    # --- Three example rows per (year, source_class, expenditure_type,
    #     form_type) combination at FY 2010, 2017, 2024 ----------------- #
    print("\n--- Sample rows: 3 per (year, source_class, expenditure_type, "
          "form_type) at FY 2010 / 2017 / 2024 ---")
    sample_sql = """
        WITH ranked AS (
            SELECT *,
                   ROW_NUMBER() OVER (
                       PARTITION BY year, source_class, expenditure_type, form_type
                       ORDER BY institution_id, discipline_fine
                   ) AS rn
            FROM _stage5_panel
            WHERE year IN (2010, 2017, 2024)
        )
        SELECT year, source_class, expenditure_type, form_type,
               institution_id, discipline_coarse, discipline_fine,
               value, quality_flag, source_question_canonical
        FROM ranked
        WHERE rn <= 3
        ORDER BY year, form_type, source_class, expenditure_type,
                 institution_id, discipline_fine
    """
    samples = con.execute(sample_sql).fetchall()
    cur_combo = None
    for (yr, sc, et, ft, iid, dc, df, v, qf, sq) in samples:
        combo = (yr, ft, sc, et)
        if combo != cur_combo:
            print(f"\n  yr={yr} form={ft} src={sc} type={et}")
            cur_combo = combo
        df_short = (df or '')[:30]
        sq_short = (sq or '')[:42]
        print(f"    inst={iid!r:>8s} "
              f"coarse={(dc or '')[:16]!r:<18s} "
              f"fine={df_short!r:<32s} "
              f"v={v!r:>10s} qf={qf!r:<12s} sq={sq_short!r}")

    elapsed = time.perf_counter() - t_start
    print("\n--- Smoke-test boundaries ---")
    print(f"  Total wall time (Stage 5 full): {elapsed:.2f}s")
    print("  No parquet written: Stage 5 smoke test only.")


def smoke_test_stage_6(
    con: Optional[duckdb.DuckDBPyConnection] = None,
) -> None:
    """Run Stage 6 end-to-end across 2010-2024; print sanity (HD 2.4.c).

    Stage 6 reconstructs era-B `source_class='all_source'` rows from
    Q9 (federal) + Q11 (nonfederal) Stage 5 fragments per the W4-locked
    rule in `crosswalks/era_b_reconstruction_rule.yaml`.

    What it checks:
      - Per-year all_source row count distribution 2010-2024.
      - Total reconstructed row count + share-by-overlap-case (both
        present, Q9-absent, Q11-absent).
      - `quality_flag` distribution on reconstructed rows.
      - **Reconstruction identity check** (load-bearing): for every
        (institution, year, discipline_fine) where Q9 AND Q11 both
        have rows, `reconstructed.value` must equal `Q9.value +
        Q11.value` within rounding tolerance. Median absolute residual
        expected ~0 (exact arithmetic).
      - **Three propagation examples**:
        (a) Q9 reported + Q11 reported -> all_source 'reported'.
        (b) Q9 row-absent + Q11 reported -> all_source 'reported'
            (present side's flag passes through, NOT 'unspecified_zero').
        (c) Q9 imputed + Q11 reported -> all_source 'imputed' (least-good).
      - Schema column types and order match locked §1 schema.
      - Wall time.

    Stops at findings; does not write any artifact.
    """
    if con is None:
        con = duckdb.connect()

    t_start = time.perf_counter()

    _load_discipline_fine_crosswalk(con)
    _load_question_map_crosswalk(con)

    print("=" * 78)
    print("HD 2.4.c Stage 6 smoke test - era-B all_source reconstruction")
    print("=" * 78)

    # --- Build Stage 5 (input to Stage 6) -------------------------------- #
    t_s5 = time.perf_counter()
    era_b_years = range(2010, 2025)
    stage5_rel = build_era_b_components(era_b_years, con)
    con.execute("DROP TABLE IF EXISTS _stage5_panel")
    con.execute(f"CREATE TEMP TABLE _stage5_panel AS {stage5_rel.sql_query()}")
    s5_elapsed = time.perf_counter() - t_s5
    n_s5 = con.execute("SELECT COUNT(*) FROM _stage5_panel").fetchone()[0]
    print(f"\nStage 5 input rows: {n_s5:,} (era-B per-component + Short Form Q2)")
    print(f"Stage 5 wall time: {s5_elapsed:.2f}s")

    # --- Build Stage 6 reconstruction ---------------------------------- #
    t_s6 = time.perf_counter()
    stage5_input_rel = con.sql("SELECT * FROM _stage5_panel")
    stage6_rel = build_era_b_all_source(stage5_input_rel, con)
    con.execute("DROP TABLE IF EXISTS _stage6_panel")
    con.execute(f"CREATE TEMP TABLE _stage6_panel AS {stage6_rel.sql_query()}")
    s6_elapsed = time.perf_counter() - t_s6
    n_s6 = con.execute("SELECT COUNT(*) FROM _stage6_panel").fetchone()[0]
    print(f"\nStage 6 reconstructed all_source rows: {n_s6:,}")
    print(f"Stage 6 reconstruction wall time: {s6_elapsed:.2f}s")

    # --- Schema check --------------------------------------------------- #
    expected_schema = [
        ("institution_id", "VARCHAR"),
        ("fice", "VARCHAR"),
        ("ncses_inst_id", "VARCHAR"),
        ("ipeds_unitid", "VARCHAR"),
        ("inst_name_long", "VARCHAR"),
        ("year", "INTEGER"),
        ("era", "VARCHAR"),
        ("discipline_coarse", "VARCHAR"),
        ("discipline_fine", "VARCHAR"),
        ("expenditure_type", "VARCHAR"),
        ("source_class", "VARCHAR"),
        ("form_type", "VARCHAR"),
        ("value", "DOUBLE"),
        ("unit", "VARCHAR"),
        ("value_type", "VARCHAR"),
        ("quality_flag", "VARCHAR"),
        ("source_questionnaire_no", "VARCHAR"),
        ("source_question_canonical", "VARCHAR"),
        ("source_question_raw", "VARCHAR"),
        ("source_file", "VARCHAR"),
        ("notes", "VARCHAR"),
    ]
    actual_schema = con.execute("DESCRIBE _stage6_panel").fetchall()
    actual_pairs = [(r[0], r[1]) for r in actual_schema]
    print(f"\n--- Schema check ({len(actual_pairs)} columns) ---")
    if actual_pairs == expected_schema:
        print("  Column order and types match locked §1 schema (21 columns). PASS")
    else:
        print("  SCHEMA DRIFT — expected vs actual:")
        for i, (e, a) in enumerate(zip(expected_schema, actual_pairs)):
            mark = "OK" if e == a else "DRIFT"
            print(f"    [{i:2d}] {mark:5s}  expected={e}  actual={a}")

    # --- Per-year row count distribution ------------------------------- #
    print("\n--- Per-year era-B reconstructed all_source row counts (2010-2024) ---")
    rows = con.execute(
        """
        SELECT year, COUNT(*) AS n
        FROM _stage6_panel
        GROUP BY year
        ORDER BY year
        """
    ).fetchall()
    print("  year   recon_rows")
    for (yr, n) in rows:
        print(f"  {yr}  {n:>8,}")

    # --- Overlap-case breakdown (load-bearing diagnostic) ---------------- #
    # FULL OUTER JOIN materializes three cases per (inst, year, disc):
    # both present, Q9 absent, Q11 absent. Re-run the join structure to
    # surface the per-case counts.
    print("\n--- Overlap case breakdown (FULL OUTER JOIN result) ---")
    overlap = con.execute(
        """
        WITH q9 AS (
            SELECT institution_id, year, discipline_fine, value, quality_flag
            FROM _stage5_panel
            WHERE source_class = 'federal'
              AND expenditure_type = 'r&d'
              AND form_type = 'standard'
        ),
        q11 AS (
            SELECT institution_id, year, discipline_fine, value, quality_flag
            FROM _stage5_panel
            WHERE source_class = 'nonfederal'
              AND expenditure_type = 'r&d'
              AND form_type = 'standard'
        )
        SELECT
            COUNT(*) FILTER (WHERE q9.institution_id IS NOT NULL
                              AND q11.institution_id IS NOT NULL) AS both_present,
            COUNT(*) FILTER (WHERE q9.institution_id IS NULL
                              AND q11.institution_id IS NOT NULL) AS q9_absent,
            COUNT(*) FILTER (WHERE q9.institution_id IS NOT NULL
                              AND q11.institution_id IS NULL)     AS q11_absent
        FROM q9
        FULL OUTER JOIN q11
          ON q9.institution_id = q11.institution_id
         AND q9.year = q11.year
         AND q9.discipline_fine = q11.discipline_fine
        """
    ).fetchone()
    both, q9_absent, q11_absent = overlap
    total = both + q9_absent + q11_absent
    print(f"  Both Q9 and Q11 present : {both:>8,}  ({both/total*100:5.2f}%)")
    print(f"  Q9 row-absent, Q11 present : {q9_absent:>8,}  ({q9_absent/total*100:5.2f}%)")
    print(f"  Q9 present, Q11 row-absent : {q11_absent:>8,}  ({q11_absent/total*100:5.2f}%)")
    print(f"  Total                       : {total:>8,}")
    print(f"  Matches Stage 6 row count   : {total == n_s6}")

    # --- quality_flag distribution on reconstructed rows ---------------- #
    print("\n--- quality_flag distribution on reconstructed rows ---")
    qf_rows = con.execute(
        """
        SELECT quality_flag, COUNT(*) AS n
        FROM _stage6_panel
        GROUP BY quality_flag
        ORDER BY n DESC
        """
    ).fetchall()
    total_qf = sum(n for _, n in qf_rows)
    for (qf, n) in qf_rows:
        share = (n / total_qf * 100) if total_qf else 0.0
        print(f"    {qf!r:>22s}  n={n:>7,}  ({share:5.2f}%)")

    # --- Reconstruction identity check (load-bearing) ------------------- #
    print("\n--- Reconstruction identity check (median absolute residual) ---")
    identity = con.execute(
        """
        WITH q9 AS (
            SELECT institution_id, year, discipline_fine, value AS q9_value
            FROM _stage5_panel
            WHERE source_class = 'federal'
              AND expenditure_type = 'r&d'
              AND form_type = 'standard'
        ),
        q11 AS (
            SELECT institution_id, year, discipline_fine, value AS q11_value
            FROM _stage5_panel
            WHERE source_class = 'nonfederal'
              AND expenditure_type = 'r&d'
              AND form_type = 'standard'
        ),
        joined AS (
            SELECT q9.institution_id, q9.year, q9.discipline_fine,
                   q9.q9_value, q11.q11_value,
                   q9.q9_value + q11.q11_value AS expected_value
            FROM q9
            INNER JOIN q11
              ON q9.institution_id = q11.institution_id
             AND q9.year = q11.year
             AND q9.discipline_fine = q11.discipline_fine
        ),
        with_recon AS (
            SELECT j.expected_value, s.value AS reconstructed_value,
                   ABS(s.value - j.expected_value) AS abs_residual
            FROM joined j
            INNER JOIN _stage6_panel s
              ON s.institution_id = j.institution_id
             AND s.year = j.year
             AND s.discipline_fine = j.discipline_fine
        )
        SELECT
            COUNT(*)                            AS n_both_present_cells,
            MIN(abs_residual)                   AS min_abs_residual,
            MEDIAN(abs_residual)                AS median_abs_residual,
            MAX(abs_residual)                   AS max_abs_residual,
            COUNT(*) FILTER (WHERE abs_residual > 0.001) AS n_residual_above_0_001
        FROM with_recon
        """
    ).fetchone()
    (n_cells, min_r, med_r, max_r, n_above) = identity
    print(f"  N cells (both Q9 and Q11 present + reconstructed)  : {n_cells:>8,}")
    print(f"  Min absolute residual                              : {min_r}")
    print(f"  Median absolute residual                           : {med_r}")
    print(f"  Max absolute residual                              : {max_r}")
    print(f"  N cells with abs_residual > 0.001                  : {n_above:>8,}")
    if med_r == 0 and max_r == 0:
        print("  PASS: median = max = 0 (exact arithmetic, no rounding loss).")
    elif med_r == 0 and (max_r or 0) < 0.001:
        print("  PASS: median = 0, max within rounding tolerance.")
    else:
        print("  WARN: residual exceeds rounding tolerance; surface to "
              "maintainer before commit.")

    # --- Three propagation case examples ------------------------------- #
    print("\n--- Three propagation case examples ---")

    # Case (a): Q9 reported + Q11 reported -> all_source 'reported'.
    print("\n  Case (a): Q9 reported + Q11 reported -> all_source 'reported'")
    case_a = con.execute(
        """
        WITH q9 AS (
            SELECT institution_id, year, discipline_fine,
                   value AS q9_value, quality_flag AS q9_flag
            FROM _stage5_panel
            WHERE source_class = 'federal' AND quality_flag = 'reported'
              AND form_type = 'standard' AND expenditure_type = 'r&d'
        ),
        q11 AS (
            SELECT institution_id, year, discipline_fine,
                   value AS q11_value, quality_flag AS q11_flag
            FROM _stage5_panel
            WHERE source_class = 'nonfederal' AND quality_flag = 'reported'
              AND form_type = 'standard' AND expenditure_type = 'r&d'
        )
        SELECT q9.institution_id, q9.year, q9.discipline_fine,
               q9.q9_value, q11.q11_value,
               s.value AS recon_value, s.quality_flag AS recon_flag
        FROM q9
        INNER JOIN q11
          ON q9.institution_id = q11.institution_id
         AND q9.year = q11.year
         AND q9.discipline_fine = q11.discipline_fine
        INNER JOIN _stage6_panel s
          ON s.institution_id = q9.institution_id
         AND s.year = q9.year
         AND s.discipline_fine = q9.discipline_fine
        WHERE q9.q9_value > 0 AND q11.q11_value > 0
        LIMIT 3
        """
    ).fetchall()
    for r in case_a:
        (iid, yr, df, q9v, q11v, rv, rf) = r
        print(f"    inst={iid!r} yr={yr} disc={df[:28]!r:<30s} "
              f"q9={q9v} + q11={q11v} = recon={rv} flag={rf!r}")

    # Case (b): Q9 row-absent + Q11 reported -> all_source 'reported'.
    print("\n  Case (b): Q9 row-absent + Q11 reported -> all_source 'reported'")
    case_b = con.execute(
        """
        WITH q9 AS (
            SELECT institution_id, year, discipline_fine
            FROM _stage5_panel
            WHERE source_class = 'federal'
              AND form_type = 'standard' AND expenditure_type = 'r&d'
        ),
        q11 AS (
            SELECT institution_id, year, discipline_fine,
                   value AS q11_value, quality_flag AS q11_flag
            FROM _stage5_panel
            WHERE source_class = 'nonfederal' AND quality_flag = 'reported'
              AND form_type = 'standard' AND expenditure_type = 'r&d'
        )
        SELECT q11.institution_id, q11.year, q11.discipline_fine,
               q11.q11_value, q11.q11_flag,
               s.value AS recon_value, s.quality_flag AS recon_flag
        FROM q11
        LEFT JOIN q9
          ON q11.institution_id = q9.institution_id
         AND q11.year = q9.year
         AND q11.discipline_fine = q9.discipline_fine
        INNER JOIN _stage6_panel s
          ON s.institution_id = q11.institution_id
         AND s.year = q11.year
         AND s.discipline_fine = q11.discipline_fine
        WHERE q9.institution_id IS NULL
          AND q11.q11_value > 0
        LIMIT 3
        """
    ).fetchall()
    for r in case_b:
        (iid, yr, df, q11v, q11f, rv, rf) = r
        print(f"    inst={iid!r} yr={yr} disc={df[:28]!r:<30s} "
              f"q9=absent q11={q11v} ({q11f!r}) recon={rv} flag={rf!r}")

    # Case (c): Q9 imputed + Q11 reported -> all_source 'imputed'.
    print("\n  Case (c): Q9 imputed + Q11 reported -> all_source 'imputed'")
    case_c = con.execute(
        """
        WITH q9 AS (
            SELECT institution_id, year, discipline_fine,
                   value AS q9_value, quality_flag AS q9_flag
            FROM _stage5_panel
            WHERE source_class = 'federal' AND quality_flag = 'imputed'
              AND form_type = 'standard' AND expenditure_type = 'r&d'
        ),
        q11 AS (
            SELECT institution_id, year, discipline_fine,
                   value AS q11_value, quality_flag AS q11_flag
            FROM _stage5_panel
            WHERE source_class = 'nonfederal' AND quality_flag = 'reported'
              AND form_type = 'standard' AND expenditure_type = 'r&d'
        )
        SELECT q9.institution_id, q9.year, q9.discipline_fine,
               q9.q9_value, q9.q9_flag, q11.q11_value, q11.q11_flag,
               s.value AS recon_value, s.quality_flag AS recon_flag
        FROM q9
        INNER JOIN q11
          ON q9.institution_id = q11.institution_id
         AND q9.year = q11.year
         AND q9.discipline_fine = q11.discipline_fine
        INNER JOIN _stage6_panel s
          ON s.institution_id = q9.institution_id
         AND s.year = q9.year
         AND s.discipline_fine = q9.discipline_fine
        LIMIT 3
        """
    ).fetchall()
    for r in case_c:
        (iid, yr, df, q9v, q9f, q11v, q11f, rv, rf) = r
        print(f"    inst={iid!r} yr={yr} disc={df[:28]!r:<30s} "
              f"q9={q9v} ({q9f!r}) q11={q11v} ({q11f!r}) "
              f"recon={rv} flag={rf!r}")

    elapsed = time.perf_counter() - t_start
    print("\n--- Smoke-test boundaries ---")
    print(f"  Total wall time (Stage 5 + Stage 6 full): {elapsed:.2f}s")
    print("  No parquet written: Stage 6 smoke test only.")


# --------------------------------------------------------------------------- #
# main() shell
# --------------------------------------------------------------------------- #


def sanity_report(
    panel_parquet: Path,
    attr_parquet: Path,
    con: duckdb.DuckDBPyConnection,
) -> None:
    """Sanity report over disk-loaded parquet files (scoping doc §6.3).

    Verbose stdout output paralleling the personnel sibling's
    `etl/build_herd_personnel.py:sanity_report`. Loads the parquet
    files back from disk so the report exercises the full-roundtrip
    path (panel materializes, parquet writes, parquet re-reads;
    consumers downstream see the same data the report describes).

    Sections:
      - Total panel rows + parquet file size.
      - Schema column types + order (matches §1 lock).
      - Row counts by (year, era, source_class, expenditure_type).
      - Distinct discipline_coarse / discipline_fine values.
      - Identifier coverage by era.
      - value column NULL/zero summary.
      - quality_flag distribution by era and source_class.
      - Free-sum totals by year × source-class (back-of-envelope read).
      - Era-B reconstruction identity check (median abs residual over
        the full disk-loaded panel).
      - Attribute table summary.
    """
    print("=" * 78)
    print("Sanity report — herd_panel.parquet + herd_panel_attributes.parquet")
    print("=" * 78)

    # Load both parquets back from disk.
    con.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE _sanity_panel AS
        SELECT * FROM read_parquet('{panel_parquet.as_posix()}')
        """
    )
    con.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE _sanity_attr AS
        SELECT * FROM read_parquet('{attr_parquet.as_posix()}')
        """
    )

    # File sizes.
    panel_size = panel_parquet.stat().st_size
    attr_size = attr_parquet.stat().st_size
    print(f"\nPanel parquet: {panel_parquet.name}")
    print(f"  Size: {panel_size:,} bytes ({panel_size / 1024 / 1024:.2f} MB)")
    print(f"Attribute parquet: {attr_parquet.name}")
    print(f"  Size: {attr_size:,} bytes ({attr_size / 1024 / 1024:.2f} MB)")

    # Panel row count.
    n_panel = con.execute("SELECT COUNT(*) FROM _sanity_panel").fetchone()[0]
    print(f"\nPanel total rows: {n_panel:,}")

    # Schema.
    print("\n--- Panel schema (column / type) ---")
    for r in con.execute("DESCRIBE _sanity_panel").fetchall():
        print(f"  {r[0]:<28s}  {r[1]}")

    # Row counts by (year, era, source_class, expenditure_type).
    # Aggregated to era for compactness; year breakdown shipped via the
    # full-build smoke test output rather than here.
    print("\n--- Row counts by (era, source_class, expenditure_type, form_type) ---")
    rows = con.execute(
        """
        SELECT era, source_class, expenditure_type, form_type,
               COUNT(*) AS n
        FROM _sanity_panel
        GROUP BY era, source_class, expenditure_type, form_type
        ORDER BY era, source_class, expenditure_type, form_type
        """
    ).fetchall()
    print("  era  source_class  expenditure_type  form_type   n")
    for (era, sc, et, ft, n) in rows:
        print(f"  {era}    {sc:<12s}  {et:<16s}  {ft:<10s}  {n:>9,}")

    # Distinct discipline buckets.
    print("\n--- Distinct discipline_coarse buckets ---")
    coarse = con.execute(
        """
        SELECT discipline_coarse, COUNT(*) AS n
        FROM _sanity_panel
        WHERE discipline_coarse IS NOT NULL
        GROUP BY discipline_coarse
        ORDER BY discipline_coarse
        """
    ).fetchall()
    for (c, n) in coarse:
        print(f"  {c!r:<32s}  n={n:>9,}")

    # quality_flag distribution by era.
    print("\n--- quality_flag distribution by era ---")
    qf = con.execute(
        """
        SELECT era, quality_flag, COUNT(*) AS n
        FROM _sanity_panel
        GROUP BY era, quality_flag
        ORDER BY era, n DESC
        """
    ).fetchall()
    for (era, flag, n) in qf:
        share = n / n_panel * 100
        print(f"  era={era}  {flag!r:<22s}  n={n:>9,}  ({share:5.2f}%)")

    # Free-sum totals by year × source-class (back-of-envelope).
    # Filter to source_class='all_source', expenditure_type='r&d',
    # discipline_fine='All' for the institution-year-rollup grain.
    print("\n--- Free-sum institution-year-total R&D ($M) by year × era ---")
    totals = con.execute(
        """
        SELECT year, era, SUM(value) / 1000.0 AS total_million_usd
        FROM _sanity_panel
        WHERE source_class = 'all_source'
          AND expenditure_type = 'r&d'
          AND form_type = 'standard'
          AND discipline_fine = 'All'
        GROUP BY year, era
        ORDER BY year
        """
    ).fetchall()
    for (yr, era, tm) in totals:
        print(f"  year={yr}  era={era}  total=${tm:>10,.1f}M")

    # Era-B reconstruction identity (median abs residual from disk).
    print("\n--- Era-B reconstruction identity check (from disk) ---")
    identity = con.execute(
        """
        WITH q9 AS (
            SELECT institution_id, year, discipline_fine, value AS q9_v
            FROM _sanity_panel
            WHERE era = 'B' AND source_class = 'federal'
              AND expenditure_type = 'r&d' AND form_type = 'standard'
        ),
        q11 AS (
            SELECT institution_id, year, discipline_fine, value AS q11_v
            FROM _sanity_panel
            WHERE era = 'B' AND source_class = 'nonfederal'
              AND expenditure_type = 'r&d' AND form_type = 'standard'
        ),
        recon AS (
            SELECT institution_id, year, discipline_fine, value AS r_v
            FROM _sanity_panel
            WHERE era = 'B' AND source_class = 'all_source'
              AND expenditure_type = 'r&d' AND form_type = 'standard'
              AND source_questionnaire_no = '9+11'
        )
        SELECT
            COUNT(*) AS n_both_present,
            MIN(ABS(recon.r_v - (q9.q9_v + q11.q11_v))) AS min_residual,
            MEDIAN(ABS(recon.r_v - (q9.q9_v + q11.q11_v))) AS median_residual,
            MAX(ABS(recon.r_v - (q9.q9_v + q11.q11_v))) AS max_residual
        FROM q9
        INNER JOIN q11 USING (institution_id, year, discipline_fine)
        INNER JOIN recon USING (institution_id, year, discipline_fine)
        """
    ).fetchone()
    (n_id, min_r, med_r, max_r) = identity
    print(f"  N both-present cells (full panel)      : {n_id:>9,}")
    print(f"  Min absolute residual                   : {min_r}")
    print(f"  Median absolute residual                : {med_r}")
    print(f"  Max absolute residual                   : {max_r}")
    if med_r == 0 and max_r == 0:
        print("  PASS: median = max = 0 (exact arithmetic survives roundtrip).")

    # Attribute table summary.
    n_attr = con.execute("SELECT COUNT(*) FROM _sanity_attr").fetchone()[0]
    print(f"\n--- Attribute table summary ---")
    print(f"  Total rows: {n_attr:,}")
    attr_breakdown = con.execute(
        """
        SELECT
            era,
            COUNT(*) AS n_rows,
            COUNT(*) FILTER (WHERE med_school_value IS NOT NULL)
                AS n_with_med_school,
            COUNT(*) FILTER (WHERE clinical_trials_value IS NOT NULL)
                AS n_with_clinical_trials,
            COUNT(*) FILTER (WHERE med_school_share IS NOT NULL)
                AS n_with_med_share,
            COUNT(*) FILTER (WHERE clinical_trials_share IS NOT NULL)
                AS n_with_clinical_share
        FROM _sanity_attr
        GROUP BY era
        ORDER BY era
        """
    ).fetchall()
    for (era, n_rows, n_med, n_clin, n_med_s, n_clin_s) in attr_breakdown:
        print(f"  era={era}  n_rows={n_rows:>6,}  "
              f"with_med_school={n_med:>5,}  "
              f"with_clinical_trials={n_clin:>5,}  "
              f"with_med_share={n_med_s:>5,}  "
              f"with_clinical_share={n_clin_s:>5,}")


def build_panel(
    con: Optional[duckdb.DuckDBPyConnection] = None,
) -> tuple[Path, Path]:
    """End-to-end HD 2.4 panel build.

    Runs Stages 1 through 10 plus the attribute table build (Stage 8)
    and writes both `herd_panel.parquet` and
    `herd_panel_attributes.parquet`.

    Pipeline:
      Stage 1-3 — Raw ingestion + question filtering + discipline
                  normalization (called inline by Stages 4 and 5).
      Stage 4 — Era-A direct rows (1975-2009 per FY 1975 floor).
      Stage 5 — Era-B per-component rows (2010-2024 standard-form
                Q9/Q11/Q14 + 2012-2024 short-form Q2).
      Stage 6 — Era-B all_source reconstruction (Q9+Q11 FULL OUTER
                JOIN with COALESCE-to-zero + least-good-flag-wins
                propagation).
      Stage 7 — Schema assembly (UNION ALL of Stages 4/5/6).
      Stage 8 — Attribute table (Q4/Q5 pivot onto institution-year
                rows; share computation from panel all_source totals).
      Stage 9 — SQL-level sanity assertions over assembled panel.
                Three-tier `unspecified_zero` defense + reconstruction
                identity + propagation invariants.
      Stage 10 — Parquet write (panel + attribute, DuckDB native).

    Returns (panel_parquet_path, attribute_parquet_path).
    """
    if con is None:
        con = duckdb.connect()

    # Drift defense — assertion at entry per HD 2.4.a discipline.
    _assert_yaml_doc_consistency()

    # Load crosswalks once.
    _load_discipline_fine_crosswalk(con)
    _load_question_map_crosswalk(con)

    print("Stage 4 — era-A direct rows (1975-2009)...")
    t0 = time.perf_counter()
    era_a_rel = build_era_a_rows(PANEL_YEARS, con)
    con.execute("DROP TABLE IF EXISTS _panel_stage_4")
    con.execute(
        f"CREATE TEMP TABLE _panel_stage_4 AS {era_a_rel.sql_query()}"
    )
    n4 = con.execute("SELECT COUNT(*) FROM _panel_stage_4").fetchone()[0]
    print(f"  Stage 4 rows: {n4:,}  ({time.perf_counter() - t0:.2f}s)")

    print("Stage 5 — era-B per-component rows (2010-2024)...")
    t0 = time.perf_counter()
    era_b_components_rel = build_era_b_components(range(2010, 2025), con)
    con.execute("DROP TABLE IF EXISTS _panel_stage_5")
    con.execute(
        f"CREATE TEMP TABLE _panel_stage_5 AS "
        f"{era_b_components_rel.sql_query()}"
    )
    n5 = con.execute("SELECT COUNT(*) FROM _panel_stage_5").fetchone()[0]
    print(f"  Stage 5 rows: {n5:,}  ({time.perf_counter() - t0:.2f}s)")

    print("Stage 6 — era-B all_source reconstruction...")
    t0 = time.perf_counter()
    era_b_components_for_recon = con.sql("SELECT * FROM _panel_stage_5")
    era_b_all_source_rel = build_era_b_all_source(
        era_b_components_for_recon, con
    )
    con.execute("DROP TABLE IF EXISTS _panel_stage_6")
    con.execute(
        f"CREATE TEMP TABLE _panel_stage_6 AS "
        f"{era_b_all_source_rel.sql_query()}"
    )
    n6 = con.execute("SELECT COUNT(*) FROM _panel_stage_6").fetchone()[0]
    print(f"  Stage 6 rows: {n6:,}  ({time.perf_counter() - t0:.2f}s)")

    print("Stage 7 — schema assembly (UNION ALL)...")
    t0 = time.perf_counter()
    panel_rel = assemble_panel(
        con.sql("SELECT * FROM _panel_stage_4"),
        con.sql("SELECT * FROM _panel_stage_5"),
        con.sql("SELECT * FROM _panel_stage_6"),
        con,
    )
    con.execute("DROP TABLE IF EXISTS _panel_assembled")
    con.execute(
        f"CREATE TEMP TABLE _panel_assembled AS {panel_rel.sql_query()}"
    )
    n7 = con.execute("SELECT COUNT(*) FROM _panel_assembled").fetchone()[0]
    print(f"  Assembled panel rows: {n7:,} (= {n4:,} + {n5:,} + {n6:,})"
          f"  ({time.perf_counter() - t0:.2f}s)")

    print("Stage 9 — sanity assertions (SQL-level, pre-write)...")
    t0 = time.perf_counter()
    assembled_rel = con.sql("SELECT * FROM _panel_assembled")
    assert_panel_invariants(assembled_rel, con)
    print(f"  All Stage 9 assertions passed."
          f"  ({time.perf_counter() - t0:.2f}s)")

    print("Stage 8 — attribute table (Q4/Q5 pivot)...")
    t0 = time.perf_counter()
    attr_rel = build_attribute_table(assembled_rel, con)
    con.execute("DROP TABLE IF EXISTS _attr_assembled")
    con.execute(
        f"CREATE TEMP TABLE _attr_assembled AS {attr_rel.sql_query()}"
    )
    n_attr = con.execute("SELECT COUNT(*) FROM _attr_assembled").fetchone()[0]
    print(f"  Attribute table rows: {n_attr:,}"
          f"  ({time.perf_counter() - t0:.2f}s)")

    print("Stage 10 — parquet write...")
    t0 = time.perf_counter()
    # Deterministic row order before the parquet COPY. Without an explicit
    # ORDER BY, DuckDB emits the assembled rows in a run-varying order, so the
    # parquet was byte-non-deterministic across rebuilds (identical content,
    # different SHA-256) — a §3 reproducibility-contract gap surfaced at
    # HD 2.4.h boundary 3. ORDER BY ALL imposes a total order over every
    # column, so the bytes become a function of the data alone. Applied to the
    # panel only; the attribute table is already byte-deterministic and is left
    # untouched (its write below is unchanged).
    panel_path = write_parquet(
        con.sql("SELECT * FROM _panel_assembled ORDER BY ALL"), OUT_PATH, con
    )
    attr_path = write_parquet(
        con.sql("SELECT * FROM _attr_assembled"), ATTR_OUT_PATH, con
    )
    try:
        panel_display = panel_path.relative_to(ROOT)
    except ValueError:
        panel_display = panel_path
    try:
        attr_display = attr_path.relative_to(ROOT)
    except ValueError:
        attr_display = attr_path
    print(f"  Wrote {panel_display} ({panel_path.stat().st_size:,} bytes)")
    print(f"  Wrote {attr_display} ({attr_path.stat().st_size:,} bytes)"
          f"  ({time.perf_counter() - t0:.2f}s)")

    return panel_path, attr_path


def main() -> int:
    """HD 2.4 build-script entry point.

    Runs the YAML/doc/runtime consistency assertion, then orchestrates
    the full Stage 1-10 build via `build_panel()`, then prints the
    sanity report over the written parquet.
    """
    _assert_yaml_doc_consistency()
    print("YAML / scoping-doc / runtime ordering: consistent "
          f"({list(QUALITY_FLAG_ORDERING_WORST_TO_BEST)!r}).")

    con = duckdb.connect()
    t_total = time.perf_counter()

    panel_path, attr_path = build_panel(con)

    print()
    sanity_report(panel_path, attr_path, con)

    elapsed = time.perf_counter() - t_total
    print(f"\nTotal HD 2.4 build wall time: {elapsed:.2f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
