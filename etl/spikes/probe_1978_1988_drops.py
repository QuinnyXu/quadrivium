"""
etl/spikes/probe_1978_1988_drops.py — Flag 3 probe: characterize the
FY 1978 and FY 1988 ~32% row-count drops surfaced at HD 2.4.b Stage 4
smoke test.

The Stage 4 panel showed FY 1978 = 3,194 rows (vs FY 1977 = 4,718) and
FY 1988 = 15,970 rows (vs FY 1987 = 23,478). Both drops are ~32% of
the prior year. Question: upstream (HERD coverage gap, methodology
change), or build-side (filter/projection treating those years
differently).

Probe scope:
  - For FY 1977, 1978, 1987, 1988: report raw row counts at three grains:
    (a) total raw rows after Stage 1 unified projection,
    (b) Stage 2 in-scope rows (after era-A field/equipment filter),
    (c) Stage 4 panel rows (after column='Total' + projection).
  - Distinct institution counts at each grain.
  - Per-question row counts in scope.

If (a) is also low for 1978/1988, the drop is upstream. If (a) is
normal but (c) is low, the drop is build-side.

Author: probe spike at HD 2.4.b round 1 Flag 3.
"""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from etl._load import read_herd_csv  # noqa: E402
from etl.build_herd_panel import (  # noqa: E402
    _load_discipline_fine_crosswalk,
    _load_question_map_crosswalk,
    filter_in_scope_questions,
    normalize_discipline,
    ERA_A_FIELD_QUESTION,
    ERA_A_EQUIPMENT_QUESTION,
    ERA_A_EQUIPMENT_QUESTION_RAW,
)

PROBE_PAIRS = [(1977, 1978), (1987, 1988)]


def main() -> int:
    con = duckdb.connect()
    _load_discipline_fine_crosswalk(con)
    _load_question_map_crosswalk(con)

    print("=" * 78)
    print("probe_1978_1988_drops — Flag 3: characterize ~32% row drops")
    print("=" * 78)

    for (good_year, drop_year) in PROBE_PAIRS:
        print(f"\n{'-' * 50}")
        print(f"Pair: FY {good_year} (baseline) vs FY {drop_year} (drop)")
        print(f"{'-' * 50}")

        for year in (good_year, drop_year):
            rel1 = read_herd_csv(year, con=con)

            # (a) Stage 1 raw row count
            n1 = rel1.aggregate("COUNT(*) AS n").fetchone()[0]
            distinct_inst_raw = con.execute(
                f"SELECT COUNT(DISTINCT inst_id) FROM ({rel1.sql_query()})"
            ).fetchone()[0]

            # (b) Stage 2 in-scope row count (era-A field+equipment).
            rel2 = filter_in_scope_questions(rel1, "A", con)
            n2 = rel2.aggregate("COUNT(*) AS n").fetchone()[0]

            # Per-question breakdown of stage-2 in-scope rows.
            per_q = con.execute(
                f"""
                SELECT question, COUNT(*) AS n
                FROM ({rel2.sql_query()})
                GROUP BY question
                ORDER BY n DESC
                """
            ).fetchall()

            # (c) Stage 4 panel row count (column='Total' filter).
            rel3 = normalize_discipline(rel2, con)
            n_panel = con.execute(
                f"""
                SELECT COUNT(*)
                FROM ({rel3.sql_query()})
                WHERE "column" = 'Total'
                """
            ).fetchone()[0]
            distinct_inst_panel = con.execute(
                f"""
                SELECT COUNT(DISTINCT inst_id)
                FROM ({rel3.sql_query()})
                WHERE "column" = 'Total'
                """
            ).fetchone()[0]

            # All distinct columns in stage-2 in-scope rows.
            cols = con.execute(
                f"""
                SELECT "column", COUNT(*) AS n
                FROM ({rel2.sql_query()})
                GROUP BY "column"
                ORDER BY n DESC
                """
            ).fetchall()

            print(f"\nFY {year}:")
            print(f"  (a) Stage 1 raw rows (after unified projection):  {n1:>9,}")
            print(f"      distinct institution_id (raw):                {distinct_inst_raw:>9,}")
            print(f"  (b) Stage 2 in-scope rows (era-A filter):         {n2:>9,}")
            for (q, qn) in per_q:
                share = (qn / n2 * 100) if n2 else 0.0
                print(f"      question={q!r:<60s} n={qn:>6,} ({share:5.1f}%)")
            print(f"  (b') Stage 2 distinct columns observed:")
            for (c, cn) in cols:
                share = (cn / n2 * 100) if n2 else 0.0
                print(f"      column={c!r:<20s} n={cn:>6,} ({share:5.1f}%)")
            print(f"  (c) Stage 4 panel rows (column='Total'):          {n_panel:>9,}")
            print(f"      distinct institution_id (panel):              {distinct_inst_panel:>9,}")

        # Compute deltas at each grain.
        print(f"\nDelta analysis (FY {drop_year} vs FY {good_year}):")
        # Re-run quickly to fetch baseline for delta math.
        rel_g = read_herd_csv(good_year, con=con)
        rel_d = read_herd_csv(drop_year, con=con)
        n1_g = rel_g.aggregate("COUNT(*) AS n").fetchone()[0]
        n1_d = rel_d.aggregate("COUNT(*) AS n").fetchone()[0]
        rel2_g = filter_in_scope_questions(rel_g, "A", con)
        rel2_d = filter_in_scope_questions(rel_d, "A", con)
        n2_g = rel2_g.aggregate("COUNT(*) AS n").fetchone()[0]
        n2_d = rel2_d.aggregate("COUNT(*) AS n").fetchone()[0]
        rel3_g = normalize_discipline(rel2_g, con)
        rel3_d = normalize_discipline(rel2_d, con)
        n_panel_g = con.execute(
            f"""
            SELECT COUNT(*) FROM ({rel3_g.sql_query()})
            WHERE "column" = 'Total'
            """
        ).fetchone()[0]
        n_panel_d = con.execute(
            f"""
            SELECT COUNT(*) FROM ({rel3_d.sql_query()})
            WHERE "column" = 'Total'
            """
        ).fetchone()[0]
        print(f"  Stage 1 raw     : {n1_g:>9,} -> {n1_d:>9,}   "
              f"delta={n1_d - n1_g:+,}  ({(n1_d/n1_g - 1)*100:+.1f}%)")
        print(f"  Stage 2 in-scope: {n2_g:>9,} -> {n2_d:>9,}   "
              f"delta={n2_d - n2_g:+,}  ({(n2_d/n2_g - 1)*100:+.1f}%)")
        print(f"  Stage 4 panel   : {n_panel_g:>9,} -> {n_panel_d:>9,}   "
              f"delta={n_panel_d - n_panel_g:+,}  ({(n_panel_d/n_panel_g - 1)*100:+.1f}%)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
