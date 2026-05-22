"""
spike_discipline_rename_2009_2010.py

THROWAWAY SPIKE — DO NOT PROMOTE TO PRODUCTION.
Author: Skipper, 2026-04-29
Time budget: 2 hours.

Kill condition (locked in CLAUDE.md §6 / PANEL_SKIPPER §7 Round 4 on
2026-04-29). The spike outputs per-discipline median ratios; the
decision rule applies to the 34 distinct 2009 row-labels in
`question = 'Expenditures by S&E field'` (24 leaves + 9 coarse rollups
+ 1 grand `All`). First printed line of the spike MUST be the actual N
of distinct 2009 row-labels — recalibrate if N is not in [30, 40].

  Annotation-worthy (clean): <=3 of 34 cells outside [0.95, 1.05] AND
    no cell median outside [0.5, 2.0] AND every 2009 cell maps to
    exactly one 2010 cell.
  Structural (messy): >=6 of 34 cells outside [0.95, 1.05] OR any cell
    median outside [0.5, 2.0] OR any 2009 cell unmappable / many-to-one.
  In-between (4-5 cells out, no extremity violations, all cells mappable):
    Sophia/Vision panel call before HD 1.5.

Annotation-worthy => methods-note framing is "transparent crosswalk",
lead chart is breakpoint-timeline. Structural => methods-note framing
is "harmonization breakthrough", lead chart is magnitude story, era
boundary scheme returns to Vision for multi-break consideration.

Question this de-risks
----------------------
The 2010 HERD redesign renames most fine discipline labels (e.g., "Engineering,
electrical" -> "Engineering, electrical, electronic, and communications"). The
inventory says it's a one-to-one rename. Before we hand-author the crosswalk in
crosswalks/discipline_fine.csv with `decision_rationale` per row, we want to
verify that institutions reporting in both 2009 and 2010 show the SAME totals
under the renamed labels, modulo small noise. If totals match within +/- 5%
for the top 50 reporting institutions, the rename is real and one-to-one and
the crosswalk is mechanical. If totals diverge widely, the redesign actually
moved spending across categories and we need a more careful methods note.

What it does
------------
1. Loads the 2009 and 2010 raw CSVs from the temp inspection folder.
2. Filters to question == "Expenditures by S&E field" and column == "Total".
3. Joins 2009 totals (by old label) to 2010 totals (by new label) per
   institution using the spike's rename map (best-effort, not authoritative).
4. Reports per-discipline median ratio 2010/2009 across institutions, plus the
   count of institutions where the ratio is outside [0.5, 2.0].

Output
------
Prints to stdout. No files written. Anything worth keeping goes into
docs/methods_notes/discipline_rename.md when this spike is killed.
"""

from __future__ import annotations

import sys
from pathlib import Path

import duckdb

# Spike now reads from the staged zips via etl._load.read_herd_csv
# (HD 1.1 + HD 1.2). The pre-HD-1.1 _tmp_herd_inspect/ extraction tree
# was deleted; raw provenance lives in data/raw/herd/*.zip + MANIFEST.md.
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from etl._load import read_herd_csv  # noqa: E402

# Best-effort rename map from inventory observation. NOT the production
# crosswalk — that gets hand-authored with rationale per row.
RENAME = {
    "Computer sciences, all": "Computer and information sciences, all",
    "Engineering, aeronautical and astronautical": "Engineering, aerospace, aeronautical, and astronautical",
    "Engineering, all": "Engineering, all",
    "Engineering, bioengineering and biomedical": "Engineering, bioengineering and biomedical engineering",
    "Engineering, chemical": "Engineering, chemical",
    "Engineering, civil": "Engineering, civil",
    "Engineering, electrical": "Engineering, electrical, electronic, and communications",
    "Engineering, mechanical": "Engineering, mechanical",
    "Engineering, metallurgical and materials": "Engineering, metallurgical and materials",
    "Engineering, other": "Engineering, other",
    "Environmental sciences, all": "Geosciences, atmospheric sciences, and ocean sciences, all",
    "Environmental sciences, atmospheric sciences": "Geosciences, atmospheric sciences, and ocean sciences, atmospheric science and meteorology",
    "Environmental sciences, earth sciences": "Geosciences, atmospheric sciences, and ocean sciences, geological and earth sciences",
    "Environmental sciences, oceanography": "Geosciences, atmospheric sciences, and ocean sciences, ocean sciences and marine sciences",
    "Environmental sciences, other": "Geosciences, atmospheric sciences, and ocean sciences, other",
    "Life sciences, agricultural sciences": "Life sciences, agricultural sciences",
    "Life sciences, all": "Life sciences, all",
    "Life sciences, biological sciences": "Life sciences, biological and biomedical sciences",
    "Life sciences, medical sciences": "Life sciences, health sciences",
    "Life sciences, other": "Life sciences, other",
    "Mathematical sciences, all": "Mathematics and statistics, all",
    "Physical sciences, all": "Physical sciences, all",
    "Physical sciences, astronomy": "Physical sciences, astronomy",
}


def load_year(con: duckdb.DuckDBPyConnection, year: int) -> None:
    """Load a year via read_herd_csv, project to spike shape.

    The unified loader handles era-A/B column reconciliation, row-filtering
    state-code/ZIP non-data rows, and (since 2026-04-29) UTF-8 -> Latin-1
    encoding fallback with substitution logging. We project to the spike's
    minimal columns (inst, year, row, value) filtered to the field-level
    Total column.
    """
    rel = read_herd_csv(year, con)
    con.register(f"_herd_{year}_full", rel)
    con.execute(
        f"""
        CREATE OR REPLACE TABLE herd_{year} AS
        SELECT
            CAST(inst_id AS VARCHAR) AS inst,
            year,
            "row",
            value
        FROM _herd_{year}_full
        WHERE question = 'Expenditures by S&E field'
          AND "column" = 'Total'
        """
    )


def main() -> int:
    con = duckdb.connect()
    try:
        load_year(con, 2009)
        load_year(con, 2010)
    except FileNotFoundError as e:
        print(f"Missing staged zip: {e}", file=sys.stderr)
        return 2

    # Sanity-check the test premise BEFORE running ratios: era B may not
    # carry `question = 'Expenditures by S&E field'` at all (the 2010
    # redesign fragments era-A's single field-level question into
    # multiple source-class questions). If herd_2010 is empty, the
    # rename-map approach is the wrong tool — surface the verdict and
    # short-circuit. Closed HD 1.4 outcome on 2026-04-30; ratio
    # classification belongs in HD 2.1+ against the reconstructed
    # (questions-mapped + summed) ratios. See PANEL_SKIPPER §7 Round 4b.
    n09 = con.execute("SELECT COUNT(*) FROM herd_2009").fetchone()[0]
    n10 = con.execute("SELECT COUNT(*) FROM herd_2010").fetchone()[0]
    if n10 == 0 and n09 > 0:
        print("=== HD 1.4 spike verdict ===")
        print(
            "  Rename-map approach insufficient. Era B (2010+) carries no\n"
            "  rows under question = 'Expenditures by S&E field' / column =\n"
            "  'Total'. The 2009->2010 break is a question-model restructure,\n"
            "  not a label rename: era B fragments era A's single field-level\n"
            "  question into multiple source-class questions ('Federal\n"
            "  expenditures by field and agency', 'Nonfederal expenditures by\n"
            "  field and source', plus capitalization/clinical-trials variants).\n"
            "  Crosswalk builders (HD 2.1+) must map questions and apply\n"
            "  summation rules across era-B federal + nonfederal source-class\n"
            "  questions to reconstruct era-A field-level all-source totals.\n"
            "  The threshold ladder applies in HD 2.1 against those\n"
            "  reconstructed ratios; not in this spike."
        )
        print(f"\n  herd_2009 rows = {n09}")
        print(f"  herd_2010 rows = {n10}  <- premise-failure")
        return 0

    # First print: cell-count anchor (kill-condition basis).
    # CLAUDE.md §6 / PANEL_SKIPPER §7 Round 4 lock: N=34 (24 leaves +
    # 9 coarse '*, all' rollups + 1 grand 'All'). Recalibrate the
    # threshold ladder if this run reports N outside [30, 40].
    print("=== HD 1.4 cell-count anchor (kill-condition basis) ===")
    mix = con.execute(
        """
        WITH labels AS (SELECT DISTINCT "row" AS r FROM herd_2009)
        SELECT
            COUNT(*) FILTER (WHERE r = 'All')                                        AS grand_total,
            COUNT(*) FILTER (WHERE r LIKE '%, all')                                  AS coarse_rollups,
            COUNT(*) FILTER (WHERE r != 'All' AND r NOT LIKE '%, all')               AS leaves,
            COUNT(*)                                                                  AS n_total
        FROM labels
        """
    ).fetchone()
    print(f"  N (distinct 2009 row-labels in 'Expenditures by S&E field') = {mix[3]}")
    print(f"    leaves         = {mix[2]}")
    print(f"    coarse rollups = {mix[1]}")
    print(f"    grand total    = {mix[0]}")
    print(
        "  Locked anchor (CLAUDE.md §6, 2026-04-29): N=34 "
        "(24 leaves + 9 rollups + 1 grand 'All')."
    )
    if mix[3] < 30 or mix[3] > 40:
        print(f"  WARNING: N={mix[3]} outside [30, 40] — recalibrate threshold ladder before applying.")
    print()

    # Apply rename to 2009 labels so they line up with 2010 labels.
    cases = " ".join(
        f"WHEN \"row\" = '{old.replace(chr(39), chr(39)+chr(39))}' THEN '{new.replace(chr(39), chr(39)+chr(39))}'"
        for old, new in RENAME.items()
    )
    con.execute(
        f"""
        CREATE OR REPLACE TABLE h09 AS
        SELECT inst,
               CASE {cases} ELSE "row" END AS field_2010_label,
               value AS value_2009
        FROM herd_2009
        """
    )

    con.execute(
        """
        CREATE OR REPLACE TABLE h10 AS
        SELECT inst, "row" AS field_2010_label, value AS value_2010
        FROM herd_2010
        """
    )

    print("\n=== Per-discipline 2010/2009 ratio (top 50 institutions by 2009 total) ===")
    rows = con.execute(
        """
        WITH top_inst AS (
            SELECT inst FROM herd_2009
            WHERE "row" = 'All'
            ORDER BY value DESC NULLS LAST
            LIMIT 50
        ),
        joined AS (
            SELECT a.field_2010_label,
                   a.inst,
                   a.value_2009,
                   b.value_2010,
                   CASE WHEN a.value_2009 > 0 THEN b.value_2010 / a.value_2009 END AS ratio
            FROM h09 a
            JOIN h10 b USING (inst, field_2010_label)
            WHERE a.inst IN (SELECT inst FROM top_inst)
        )
        SELECT field_2010_label,
               COUNT(*)                                          AS n,
               MEDIAN(ratio)                                     AS median_ratio,
               SUM(CASE WHEN ratio < 0.5 OR ratio > 2.0 THEN 1 ELSE 0 END) AS n_outliers,
               SUM(CASE WHEN ratio IS NULL THEN 1 ELSE 0 END)    AS n_missing
        FROM joined
        GROUP BY 1
        ORDER BY 1
        """
    ).fetchall()
    # Manual table format (no pandas dep).
    label_w = max((len(r[0]) for r in rows), default=20)
    label_w = max(label_w, len("field_2010_label"))
    print(
        f"  {'field_2010_label'.ljust(label_w)}  {'n':>4}  "
        f"{'median_ratio':>12}  {'n_outliers':>10}  {'n_missing':>9}"
    )
    print(
        f"  {'-' * label_w}  {'-' * 4}  {'-' * 12}  {'-' * 10}  {'-' * 9}"
    )
    for label, n, median_ratio, n_outliers, n_missing in rows:
        mr = f"{median_ratio:.4f}" if median_ratio is not None else "NULL"
        print(
            f"  {label.ljust(label_w)}  {n:>4}  {mr:>12}  "
            f"{n_outliers:>10}  {n_missing:>9}"
        )

    # ---- HD 1.4 verdict (apply locked threshold ladder) ------------------
    # Threshold ladder anchored to N=34 cells (verified 2026-04-29).
    # The per-discipline ratio table above has one row per 2010-aligned
    # label that joined; cells outside [0.95, 1.05] are "out of band",
    # cells with ratio outside [0.5, 2.0] are "extremity violations".
    n_out = sum(
        1
        for _, _, mr, _, _ in rows
        if mr is not None and (mr < 0.95 or mr > 1.05)
    )
    n_extreme = sum(
        1
        for _, _, mr, _, _ in rows
        if mr is not None and (mr < 0.5 or mr > 2.0)
    )

    print("\n=== 2009 labels NOT in rename map (need crosswalk attention) ===")
    unmapped = con.execute(
        f"""
        SELECT DISTINCT "row"
        FROM herd_2009
        WHERE "row" NOT IN ({", ".join(repr(k) for k in RENAME.keys())})
        ORDER BY "row"
        """
    ).fetchall()
    if unmapped:
        for (r,) in unmapped:
            print(f"  - {r}")
    else:
        print("  (none)")

    print("\n=== 2010 labels with no 2009 source via the rename (potential new categories) ===")
    new_cats = con.execute(
        f"""
        SELECT DISTINCT "row"
        FROM herd_2010
        WHERE "row" NOT IN ({", ".join(repr(v) for v in RENAME.values())})
          AND "row" NOT LIKE 'Non-S&E%'
        ORDER BY "row"
        """
    ).fetchall()
    if new_cats:
        for (r,) in new_cats:
            print(f"  - {r}")
    else:
        print("  (none)")

    # ---- Verdict --------------------------------------------------------
    n_unmapped_2009_excluding_rollups_and_grand_total = sum(
        1
        for (r,) in unmapped
        if r != "All" and not r.endswith(", all")
    )
    print("\n=== HD 1.4 verdict against threshold ladder (CLAUDE.md §6) ===")
    print(f"  cells with median ratio outside [0.95, 1.05]:  {n_out}")
    print(f"  cells with median ratio outside [0.5, 2.0]:    {n_extreme}")
    print(
        f"  unmapped 2009 leaves (not in spike RENAME map): "
        f"{n_unmapped_2009_excluding_rollups_and_grand_total}"
    )
    if n_extreme > 0:
        verdict = "STRUCTURAL (extremity violation present)"
    elif n_unmapped_2009_excluding_rollups_and_grand_total > 0:
        # Spike's RENAME map is best-effort; missing leaves are a real
        # rename-map gap, not a structural-vs-annotation question.
        verdict = "SPIKE RENAME MAP INCOMPLETE — see unmapped section above"
    elif n_out >= 6:
        verdict = "STRUCTURAL (>=6 cells out of [0.95, 1.05])"
    elif n_out <= 3:
        verdict = "ANNOTATION-WORTHY (<=3 cells out, no extremity)"
    else:
        verdict = "IN-BETWEEN (4-5 cells out) — Sophia/Vision panel call"
    print(f"  VERDICT: {verdict}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
