"""
etl/spikes/probe_short_form_structure.py — characterize short-form
HERD CSV raw structure for HD 2.4.b round 1 Surface 3 follow-up
(short-form files staged 2026-05-10 per Option (b) disposition).

Probes data/raw/herd/short_form/higher_education_r_and_d_{year}_short.zip
for FY 2012, 2017, 2024. Inspects:

  - Column header (CSV schema): what columns does the short-form file
    have, and how does it compare to the standard-form 20/23-col
    era-A/era-B schemas?
  - Question labels: confirm "Short form: R&D expenditures by major
    R&D field" appears; identify the raw label NSF actually uses.
  - questionnaire_no values: what qno prefixes do short-form rows use?
  - Row labels (discipline names): are they parallel to standard-form
    Q9/Q11 discipline_fine labels?
  - Column structure for Short Form Q2: does column='Total' exist as
    a rolled all-source column?
  - Status code distribution: same codeset as standard-form?

Output prints to stdout.

Author: HD 2.4.b round 1 Surface 3 follow-up probe (Option (b) path).
"""
from __future__ import annotations

import sys
import tempfile
import zipfile
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent.parent
SHORT_FORM_DIR = ROOT / "data" / "raw" / "herd" / "short_form"

PROBE_YEARS = (2012, 2017, 2024)


def zip_path(year: int) -> Path:
    return SHORT_FORM_DIR / f"higher_education_r_and_d_{year}_short.zip"


def csv_member(zf: zipfile.ZipFile, year: int) -> str:
    candidates = [f"short{year}.csv", f"short_{year}.csv"]
    for name in candidates:
        if name in zf.namelist():
            return name
    for name in zf.namelist():
        if name.lower().endswith(".csv") and str(year) in name:
            return name
    raise FileNotFoundError(
        f"No CSV in {zf.filename!r}; members: {zf.namelist()}"
    )


def probe_year(con: duckdb.DuckDBPyConnection, year: int) -> None:
    print(f"\n{'=' * 78}")
    print(f"FY {year} — short-form CSV raw structure probe")
    print(f"{'=' * 78}")

    zp = zip_path(year)
    if not zp.exists():
        print(f"  MISSING zip: {zp}")
        return

    with zipfile.ZipFile(zp, "r") as zf:
        member = csv_member(zf, year)
        raw_bytes = zf.read(member)
        with tempfile.NamedTemporaryFile(
            suffix=f"_short_{year}.csv", delete=False
        ) as tmp:
            tmp_path = Path(tmp.name)
            tmp.write(raw_bytes)

    try:
        # Load as VARCHAR for inspection.
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

        # Pass 1: column header.
        cols = [r[0] for r in con.execute(
            f"DESCRIBE _short_raw_{year}"
        ).fetchall()]
        n_total = con.execute(
            f"SELECT COUNT(*) FROM _short_raw_{year}"
        ).fetchone()[0]
        print(f"\n  CSV row count: {n_total:,}")
        print(f"  CSV column count: {len(cols)}")
        print(f"  Column headers: {cols}")

        # Pass 2: distinct question labels.
        # Need to find the 'question' column. Standard-form has it
        # exactly as 'question'. Short-form may have a similar name.
        question_col = None
        for c in cols:
            if c.lower() == "question":
                question_col = c
                break
        if question_col is None:
            print(f"  WARNING: no 'question'-named column; cols are {cols}")
            return

        print(f"\n  Distinct question labels in {question_col!r}:")
        rows = con.execute(
            f"""
            SELECT {question_col}, COUNT(*) AS n
            FROM _short_raw_{year}
            GROUP BY {question_col}
            ORDER BY n DESC
            """
        ).fetchall()
        for (q, n) in rows:
            print(f"    n={n:>6,}  question={q!r}")

        # Pass 3: distinct questionnaire_no values.
        qno_col = None
        for c in cols:
            if c.lower() in ("questionnaire_no", "questionnaireno", "question_no"):
                qno_col = c
                break
        if qno_col is not None:
            print(f"\n  Distinct {qno_col!r} prefixes (top 20):")
            qnos = con.execute(
                f"""
                SELECT {qno_col}, COUNT(*) AS n
                FROM _short_raw_{year}
                GROUP BY {qno_col}
                ORDER BY n DESC
                LIMIT 20
                """
            ).fetchall()
            for (q, n) in qnos:
                print(f"    qno={q!r:<10s} n={n:>6,}")

        # Pass 4: for "major R&D field" or "Short Form Q2"-pattern
        # questions, characterize columns + row labels.
        candidate_questions = [r[0] for r in rows if r[0] and (
            "major" in (r[0] or "").lower()
            or "field" in (r[0] or "").lower()
            or "short" in (r[0] or "").lower()
        )]
        print(f"\n  Candidate Short Form Q2 questions: "
              f"{len(candidate_questions)}")
        for cq in candidate_questions:
            print(f"\n    Question: {cq!r}")
            col_col = None
            row_col = None
            for c in cols:
                if c.lower() == "column":
                    col_col = c
                if c.lower() == "row":
                    row_col = c
            if col_col:
                col_dist = con.execute(
                    f"""
                    SELECT "{col_col}", COUNT(*) AS n
                    FROM _short_raw_{year}
                    WHERE {question_col} = ?
                    GROUP BY "{col_col}"
                    ORDER BY n DESC
                    """,
                    [cq]
                ).fetchall()
                print(f"      Columns under this question:")
                for (c, n) in col_dist:
                    print(f"        {c!r:<25s} n={n:>6,}")

            if row_col:
                # Sample row labels.
                row_dist = con.execute(
                    f"""
                    SELECT "{row_col}", COUNT(*) AS n
                    FROM _short_raw_{year}
                    WHERE {question_col} = ?
                    GROUP BY "{row_col}"
                    ORDER BY n DESC
                    LIMIT 15
                    """,
                    [cq]
                ).fetchall()
                print(f"      Top 15 row labels under this question:")
                for (r, n) in row_dist:
                    print(f"        {r!r:<55s} n={n:>6,}")

            # Sample rows.
            print(f"      Sample 5 rows:")
            samples = con.execute(
                f"""
                SELECT * FROM _short_raw_{year}
                WHERE {question_col} = ?
                LIMIT 5
                """,
                [cq]
            ).fetchall()
            for s in samples:
                print(f"        {s}")

        # Pass 5: distinct status values.
        status_col = None
        for c in cols:
            if c.lower() == "status":
                status_col = c
                break
        if status_col:
            status_dist = con.execute(
                f"""
                SELECT "{status_col}", COUNT(*) AS n
                FROM _short_raw_{year}
                GROUP BY "{status_col}"
                ORDER BY n DESC
                """
            ).fetchall()
            print(f"\n  Status code distribution:")
            for (s, n) in status_dist:
                print(f"    status={s!r:<12s} n={n:>6,}")
    finally:
        try:
            tmp_path.unlink()
        except OSError:
            pass


def main() -> int:
    con = duckdb.connect()
    print("=" * 78)
    print("probe_short_form_structure — HD 2.4.b round 1 Surface 3 follow-up")
    print("=" * 78)
    for year in PROBE_YEARS:
        probe_year(con, year)
    return 0


if __name__ == "__main__":
    sys.exit(main())
