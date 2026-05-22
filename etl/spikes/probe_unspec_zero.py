"""Diagnostic: where do the 9 unspecified_zero rows in Stage 5 come from?"""
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from etl.build_herd_panel import (  # noqa: E402
    build_era_b_components,
    _load_discipline_fine_crosswalk,
    _load_question_map_crosswalk,
)


def main() -> int:
    con = duckdb.connect()
    _load_discipline_fine_crosswalk(con)
    _load_question_map_crosswalk(con)
    rel = build_era_b_components(range(2010, 2025), con)
    con.execute(f"CREATE TEMP TABLE _s5 AS {rel.sql_query()}")

    print("unspecified_zero rows in Stage 5 panel (per year × source_class × form_type):")
    rows = con.execute(
        """
        SELECT year, source_class, expenditure_type, form_type,
               source_questionnaire_no, source_question_canonical, value,
               institution_id, discipline_fine, source_question_raw
        FROM _s5
        WHERE quality_flag = 'unspecified_zero'
        ORDER BY year, source_class, expenditure_type
        """
    ).fetchall()
    for r in rows:
        (yr, sc, et, ft, qno, sq, v, iid, df, sqr) = r
        print(f"  year={yr} src={sc} type={et} form={ft} qno={qno!r} "
              f"sq={sq[:50]!r} value={v} inst={iid!r} "
              f"fine={df!r} raw_q={sqr[:50]!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
