"""HD 1.5 — Per-year HERD profile + era-B question-structure audit.

Outputs three artifacts:

1. ``docs/herd_question_structure_by_year.csv`` (compact, deposit artifact)
   - year, n_rows, distinct_question_count,
     era_a_question_present, era_b_federal_present, era_b_nonfederal_present,
     encoding_fallback_triggered, encoding_fallback_count

2. ``validation/profile/herd_profile.parquet`` (long-format detail)
   - per (year, dimension ∈ {questionnaire_no, question, row, column},
     value, n_rows). Filter by dimension for per-dim breakdowns.

3. ``docs/methods_notes/herd_profile.md`` (1-page summary)
   - era boundaries as observed; transitional-year findings; encoding
     fallback distribution; anything unexpected for the panel.

Stops at findings — does not attempt to resolve transitional years
(HD 2.1's crosswalk-builders own those calls).

Author: Skipper, 2026-04-30 (HD 1.5).
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

import duckdb

from etl._load import (
    RAW_HERD_DIR,
    YEAR_MAX,
    YEAR_MIN,
    _scan_invalid_utf8_bytes,
    csv_member_for,
    read_herd_csv,
    zip_path_for,
)

ERA_A_QUESTION = "Expenditures by S&E field"
ERA_B_FEDERAL = "Federal expenditures by field and agency"
ERA_B_NONFEDERAL = "Nonfederal expenditures by field and source"

ROOT = Path(__file__).resolve().parent.parent
OUT_QUESTION_STRUCT = ROOT / "docs" / "herd_question_structure_by_year.csv"
OUT_PROFILE_PARQUET = ROOT / "validation" / "profile" / "herd_profile.parquet"
OUT_PROFILE_MD = ROOT / "docs" / "methods_notes" / "herd_profile.md"


def years_available() -> list[int]:
    """Return sorted list of years we have staged zips for."""
    have: list[int] = []
    for y in range(YEAR_MIN, YEAR_MAX + 1):
        if zip_path_for(y).exists():
            have.append(y)
    return have


def scan_year_encoding(year: int) -> int:
    """Number of invalid-UTF-8 byteranges in this year's raw CSV (no log writes)."""
    zip_p = zip_path_for(year)
    with zipfile.ZipFile(zip_p, "r") as zf:
        member = csv_member_for(zf, year)
        raw = zf.read(member)
    return len(_scan_invalid_utf8_bytes(raw))


def profile_year(
    year: int,
    con: duckdb.DuckDBPyConnection,
) -> tuple[dict, list[tuple]]:
    """Profile one year. Returns (per-year stats, long-format detail rows)."""
    n_subs = scan_year_encoding(year)
    rel = read_herd_csv(year, con)
    con.register(f"y_{year}", rel)

    stats_row = con.execute(
        f"""
        SELECT
            COUNT(*)                                                   AS n_rows,
            COUNT(DISTINCT question)                                   AS n_distinct_questions,
            COUNT(*) FILTER (WHERE question = '{ERA_A_QUESTION}')      AS n_era_a,
            COUNT(*) FILTER (WHERE question = '{ERA_B_FEDERAL}')       AS n_era_b_fed,
            COUNT(*) FILTER (WHERE question = '{ERA_B_NONFEDERAL}')    AS n_era_b_nonfed
        FROM y_{year}
        """
    ).fetchone()

    stats = {
        "year": year,
        "n_rows": stats_row[0],
        "distinct_question_count": stats_row[1],
        "era_a_question_present": stats_row[2] > 0,
        "era_b_federal_present": stats_row[3] > 0,
        "era_b_nonfederal_present": stats_row[4] > 0,
        "encoding_fallback_triggered": n_subs > 0,
        "encoding_fallback_count": n_subs,
    }

    # Long-format detail across the four dimensions.
    detail: list[tuple] = []
    for dim in ("questionnaire_no", "question", "row", "column"):
        rows = con.execute(
            f"""
            SELECT {year} AS year,
                   '{dim}' AS dimension,
                   CAST("{dim}" AS VARCHAR) AS value,
                   COUNT(*) AS n_rows
            FROM y_{year}
            GROUP BY "{dim}"
            """
        ).fetchall()
        detail.extend(rows)

    con.unregister(f"y_{year}")
    return stats, detail


def main() -> int:
    years = years_available()
    if not years:
        print("No staged year zips found in data/raw/herd/", file=sys.stderr)
        return 1

    print(f"=== HD 1.5 profile: {len(years)} years ({years[0]}-{years[-1]}) ===")
    OUT_PROFILE_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    OUT_PROFILE_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_QUESTION_STRUCT.parent.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect()

    all_stats: list[dict] = []
    all_detail: list[tuple] = []

    for y in years:
        try:
            stats, detail = profile_year(y, con)
        except Exception as e:  # noqa: BLE001
            print(f"  {y}: FAIL {type(e).__name__}: {e}", file=sys.stderr)
            continue
        all_stats.append(stats)
        all_detail.extend(detail)
        flags = []
        if stats["era_a_question_present"]:
            flags.append("eraA")
        if stats["era_b_federal_present"]:
            flags.append("eraB-fed")
        if stats["era_b_nonfederal_present"]:
            flags.append("eraB-nonfed")
        if stats["encoding_fallback_triggered"]:
            flags.append(f"enc:{stats['encoding_fallback_count']}")
        flags_str = ",".join(flags) if flags else "(none)"
        print(
            f"  {y}: rows={stats['n_rows']:>7d}  "
            f"qs={stats['distinct_question_count']:>3d}  "
            f"flags={flags_str}"
        )

    # Write compact CSV (deposit artifact for the methods note).
    con.execute(
        """
        CREATE OR REPLACE TABLE _stats(
            year INTEGER,
            n_rows BIGINT,
            distinct_question_count INTEGER,
            era_a_question_present BOOLEAN,
            era_b_federal_present BOOLEAN,
            era_b_nonfederal_present BOOLEAN,
            encoding_fallback_triggered BOOLEAN,
            encoding_fallback_count INTEGER
        )
        """
    )
    for s in all_stats:
        con.execute(
            "INSERT INTO _stats VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                s["year"],
                s["n_rows"],
                s["distinct_question_count"],
                s["era_a_question_present"],
                s["era_b_federal_present"],
                s["era_b_nonfederal_present"],
                s["encoding_fallback_triggered"],
                s["encoding_fallback_count"],
            ],
        )
    con.execute(
        f"COPY (SELECT * FROM _stats ORDER BY year) TO '{OUT_QUESTION_STRUCT.as_posix()}' "
        "(HEADER, DELIMITER ',')"
    )
    print(f"\nwrote {OUT_QUESTION_STRUCT}")

    # Write long-format detail parquet.
    con.execute(
        """
        CREATE OR REPLACE TABLE _detail(
            year INTEGER,
            dimension VARCHAR,
            value VARCHAR,
            n_rows BIGINT
        )
        """
    )
    con.executemany(
        "INSERT INTO _detail VALUES (?, ?, ?, ?)",
        all_detail,
    )
    con.execute(
        f"COPY (SELECT * FROM _detail ORDER BY year, dimension, value) "
        f"TO '{OUT_PROFILE_PARQUET.as_posix()}' (FORMAT PARQUET)"
    )
    print(f"wrote {OUT_PROFILE_PARQUET}")

    # ---- Findings synthesis ---------------------------------------------
    transitional_both = [
        s for s in all_stats
        if s["era_a_question_present"] and (s["era_b_federal_present"] or s["era_b_nonfederal_present"])
    ]
    transitional_neither = [
        s for s in all_stats
        if not s["era_a_question_present"]
        and not s["era_b_federal_present"]
        and not s["era_b_nonfederal_present"]
    ]
    era_a_only = [s for s in all_stats if s["era_a_question_present"] and not s["era_b_federal_present"] and not s["era_b_nonfederal_present"]]
    era_b_only = [s for s in all_stats if not s["era_a_question_present"] and (s["era_b_federal_present"] or s["era_b_nonfederal_present"])]
    fallback_years = [s for s in all_stats if s["encoding_fallback_triggered"]]

    print("\n=== Findings ===")
    print(f"  era-A-only years (carry only 'Expenditures by S&E field'): {len(era_a_only)}")
    if era_a_only:
        yrs = [s["year"] for s in era_a_only]
        print(f"    span: {yrs[0]}-{yrs[-1]} (count={len(yrs)})")

    print(f"  era-B-only years (federal/nonfederal split, no era-A question): {len(era_b_only)}")
    if era_b_only:
        yrs = [s["year"] for s in era_b_only]
        print(f"    span: {yrs[0]}-{yrs[-1]} (count={len(yrs)})")

    print(f"  TRANSITIONAL years (carry both era-A and era-B questions): {len(transitional_both)}")
    for s in transitional_both:
        print(
            f"    {s['year']}: era_a={s['era_a_question_present']}, "
            f"era_b_fed={s['era_b_federal_present']}, "
            f"era_b_nonfed={s['era_b_nonfederal_present']}"
        )

    print(f"  TRANSITIONAL years (carry NEITHER cleanly): {len(transitional_neither)}")
    for s in transitional_neither:
        print(f"    {s['year']}: distinct questions = {s['distinct_question_count']}")

    print(f"  encoding-fallback years: {len(fallback_years)}")
    for s in fallback_years:
        print(f"    {s['year']}: {s['encoding_fallback_count']} substitution(s)")

    # ---- Methods-note md ------------------------------------------------
    md_lines: list[str] = []
    md_lines.append("# HERD per-year profile (HD 1.5)\n")
    md_lines.append(f"_Generated 2026-04-30. {len(all_stats)} years profiled._\n")
    md_lines.append("\n## Era boundaries as observed\n")
    if era_a_only:
        md_lines.append(
            f"- **Era A** (carries `question = 'Expenditures by S&E field'` only): "
            f"{era_a_only[0]['year']}–{era_a_only[-1]['year']} ({len(era_a_only)} years).\n"
        )
    if era_b_only:
        md_lines.append(
            f"- **Era B** (carries the federal/nonfederal source-class split, no era-A question): "
            f"{era_b_only[0]['year']}–{era_b_only[-1]['year']} ({len(era_b_only)} years).\n"
        )
    if transitional_both:
        md_lines.append(
            f"- **Transitional (carries both)**: "
            f"{', '.join(str(s['year']) for s in transitional_both)}. "
            f"Flagged for HD 2.1 crosswalk-builders to resolve.\n"
        )
    else:
        md_lines.append("- **Transitional (carries both)**: none observed.\n")
    if transitional_neither:
        md_lines.append(
            f"- **Transitional (carries neither)**: "
            f"{', '.join(str(s['year']) for s in transitional_neither)}. "
            f"Indicates pre-1980 years where field-level reporting hadn't begun, "
            f"or unexpected gaps. Flagged for HD 2.1.\n"
        )
    md_lines.append("\n## Encoding fallback (UTF-8 → Latin-1)\n")
    if fallback_years:
        md_lines.append(
            f"{len(fallback_years)} year(s) required Latin-1 fallback. "
            f"Per-byte substitutions are logged at "
            f"`validation/reports/encoding_substitutions.csv` (deposit artifact).\n\n"
        )
        md_lines.append("| Year | Substitutions |\n|---|---:|\n")
        for s in fallback_years:
            md_lines.append(f"| {s['year']} | {s['encoding_fallback_count']} |\n")
    else:
        md_lines.append("All years decode cleanly as UTF-8. No fallback triggered.\n")
    md_lines.append("\n## Citing this profile\n")
    md_lines.append(
        "- `docs/herd_question_structure_by_year.csv` — compact per-year summary "
        "(deposit artifact; cited from the methods note's *Reconstructive "
        "Harmonization* section).\n"
    )
    md_lines.append(
        "- `validation/profile/herd_profile.parquet` — long-format detail across "
        "(year × dimension × value), where dimension ∈ {questionnaire_no, "
        "question, row, column}.\n"
    )

    OUT_PROFILE_MD.write_text("".join(md_lines), encoding="utf-8")
    print(f"wrote {OUT_PROFILE_MD}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
