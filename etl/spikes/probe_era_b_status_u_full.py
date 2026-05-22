"""
etl/spikes/probe_era_b_status_u_full.py — full era-B characterization
of status='u' for HD 2.4.d Stage 9 disposition.

HD 2.4.b round 1 surfaced 9 rows at FY 2020 Q14 column='Total' /
institution_id '003446' violating the W4 lock's "FY-2017-only,
non-Total-only" empirical baseline. The W4 NULL characterization spike
scanned only FY 2008/2017/2024 spot years; this probe extends the
characterization to all era-B years (2010-2024) + all questions + all
columns, plus identifying institution '003446' (name, state, type).

Probe scope (load-bearing for Stage 9 disposition options α/β/γ):

  Pass 1 — All era-B years, all questions, all columns: per-year
  count of status='u' rows.

  Pass 2 — For each year that has status='u' rows: breakdown by
  (question, column).

  Pass 3 — For each year that has status='u' rows: identify
  institutions emitting them. Cross-year persistence check (is
  '003446' a one-off or a chronic pattern?).

  Pass 4 — Institution '003446' lookup: inst_name_long, state, etc.

  Pass 5 — Q14 column='Total' status='u' rows specifically (the HD
  2.4.b round 1 surface): full per-row detail for all era-B years.

  Pass 6 — Standard-form + short-form scope: do short-form HERD CSVs
  emit status='u' anywhere?

Output prints to stdout. Spike discipline per W2: stop at findings,
do not patch.

Author: probe spike at HD 2.4.d round 1.
"""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from etl._load import read_herd_csv, read_herd_short_form_csv  # noqa: E402

ERA_B_YEARS = range(2010, 2025)
SHORT_FORM_YEARS = range(2012, 2025)


def main() -> int:
    con = duckdb.connect()

    print("=" * 78)
    print("probe_era_b_status_u_full — full era-B status='u' characterization")
    print("=" * 78)

    # ------------------------------------------------------------------ #
    # Pass 1: per-year status='u' counts (standard-form, all questions)
    # ------------------------------------------------------------------ #
    print("\n--- Pass 1: per-year status='u' counts in standard-form HERD CSVs ---")
    print("  year   total_rows   status_u_rows   share")
    per_year_summary: list[tuple] = []
    for year in ERA_B_YEARS:
        rel = read_herd_csv(year, con=con)
        n_total = rel.aggregate("COUNT(*) AS n").fetchone()[0]
        n_u = con.execute(
            f"""
            SELECT COUNT(*) FROM ({rel.sql_query()})
            WHERE status = 'u' OR status = 'U'
            """
        ).fetchone()[0]
        per_year_summary.append((year, n_total, n_u))
        flag = "  <-- status='u' present" if n_u > 0 else ""
        share = (n_u / n_total * 100) if n_total else 0.0
        print(f"  {year}  {n_total:>10,}   {n_u:>10,}   {share:6.4f}%{flag}")

    # ------------------------------------------------------------------ #
    # Pass 2: for years with status='u', breakdown by (question, column)
    # ------------------------------------------------------------------ #
    print("\n--- Pass 2: status='u' breakdown by (question, column) per year ---")
    affected_years = [yr for (yr, _, n_u) in per_year_summary if n_u > 0]
    for year in affected_years:
        rel = read_herd_csv(year, con=con)
        breakdown = con.execute(
            f"""
            SELECT question, "column", COUNT(*) AS n
            FROM ({rel.sql_query()})
            WHERE status = 'u' OR status = 'U'
            GROUP BY question, "column"
            ORDER BY n DESC
            """
        ).fetchall()
        print(f"\n  FY {year}:")
        for (q, c, n) in breakdown:
            print(f"    n={n:>5,}  question={q[:55]!r:<57s} column={c!r}")

    # ------------------------------------------------------------------ #
    # Pass 3: institutions emitting status='u' per year
    # ------------------------------------------------------------------ #
    print("\n--- Pass 3: distinct institutions emitting status='u' per year ---")
    inst_persistence: dict[str, list[int]] = {}
    for year in affected_years:
        rel = read_herd_csv(year, con=con)
        insts = con.execute(
            f"""
            SELECT DISTINCT inst_id, inst_name_long
            FROM ({rel.sql_query()})
            WHERE status = 'u' OR status = 'U'
            ORDER BY inst_id
            """
        ).fetchall()
        print(f"\n  FY {year}: {len(insts)} distinct institutions")
        for (iid, inm) in insts:
            print(f"    inst={iid!r:<10s} name={(inm or '')[:60]!r}")
            inst_persistence.setdefault(iid, []).append(year)

    print("\n--- Cross-year persistence check ---")
    print(f"  Total distinct institutions emitting status='u' anywhere: "
          f"{len(inst_persistence)}")
    multi_year = {k: v for k, v in inst_persistence.items() if len(v) > 1}
    print(f"  Multi-year institutions: {len(multi_year)}")
    for (iid, years) in sorted(multi_year.items()):
        print(f"    inst={iid!r}  years={years}")

    # ------------------------------------------------------------------ #
    # Pass 4: institution '003446' identity lookup (HD 2.4.b round 1
    # finding's institution-of-interest).
    # ------------------------------------------------------------------ #
    print("\n--- Pass 4: institution '003446' identity ---")
    # Pull from FY 2024 to get current metadata.
    rel_2024 = read_herd_csv(2024, con=con)
    inst_meta = con.execute(
        f"""
        SELECT DISTINCT
            inst_id, inst_name_long, inst_city, inst_state_code,
            inst_zip, hbcu_flag, med_sch_flag, hhe_flag, toi_code,
            hdg_code, toc_code
        FROM ({rel_2024.sql_query()})
        WHERE inst_id = '003446'
        """
    ).fetchall()
    for row in inst_meta:
        print(f"  inst_id              : {row[0]!r}")
        print(f"  inst_name_long       : {row[1]!r}")
        print(f"  inst_city            : {row[2]!r}")
        print(f"  inst_state_code      : {row[3]!r}")
        print(f"  inst_zip             : {row[4]!r}")
        print(f"  hbcu_flag            : {row[5]!r}")
        print(f"  med_sch_flag         : {row[6]!r}")
        print(f"  hhe_flag             : {row[7]!r}")
        print(f"  toi_code             : {row[8]!r}")
        print(f"  hdg_code             : {row[9]!r}")
        print(f"  toc_code             : {row[10]!r}")

    # ------------------------------------------------------------------ #
    # Pass 5: Q14 column='Total' status='u' detail (HD 2.4.b round 1
    # finding scope).
    # ------------------------------------------------------------------ #
    print("\n--- Pass 5: Q14 column='Total' status='u' detail (all era-B years) ---")
    for year in affected_years:
        rel = read_herd_csv(year, con=con)
        detail = con.execute(
            f"""
            SELECT year, inst_id, inst_name_long, questionnaire_no,
                   question, "row", "column", data, status
            FROM ({rel.sql_query()})
            WHERE (status = 'u' OR status = 'U')
              AND question ILIKE '%Capitalized%'
              AND "column" = 'Total'
            ORDER BY inst_id, "row"
            """
        ).fetchall()
        if not detail:
            continue
        print(f"\n  FY {year}: {len(detail)} Q14 column='Total' status='u' rows")
        for d in detail:
            (yr, iid, inm, qno, q, r, c, dat, s) = d
            print(f"    inst={iid!r:<8s} qno={qno!r:<6s} "
                  f"row={(r or '')[:35]!r:<37s} "
                  f"col={c!r:<8s} data={dat!r:<8s} status={s!r}")

    # ------------------------------------------------------------------ #
    # Pass 6: short-form HERD CSVs — any status='u'?
    # ------------------------------------------------------------------ #
    print("\n--- Pass 6: status='u' in short-form HERD CSVs ---")
    print("  year   total_rows   status_u_rows")
    for year in SHORT_FORM_YEARS:
        rel = read_herd_short_form_csv(year, con=con)
        n_total = rel.aggregate("COUNT(*) AS n").fetchone()[0]
        n_u = con.execute(
            f"""
            SELECT COUNT(*) FROM ({rel.sql_query()})
            WHERE status = 'u' OR status = 'U'
            """
        ).fetchone()[0]
        flag = "  <-- present" if n_u > 0 else ""
        print(f"  {year}  {n_total:>10,}   {n_u:>10,}{flag}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
