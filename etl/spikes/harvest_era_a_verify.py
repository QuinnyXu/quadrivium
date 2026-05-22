"""Quick verification probes against the harvest's surprises.

We expected (per Guide page 14):
  - bioengineering arrives FY 1997
  - metallurgical+materials arrives FY 1990
Harvest reports both first-seen at 1984. Probe directly:
  - 1984: are there nonzero `value` rows on those labels, or just label
    rows with NULL/zero data?
  - 1996, 1997: same probes.
  - 1989, 1990: same probes.
Also probe pre-1981 sub-period structure (Guide page 18 Item 2 lists
1973–74, 1975–77, 1978, 1979, 1980–89 distinct).
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from etl._load import read_herd_csv  # noqa: E402

ERA_A_QUESTION = "Expenditures by S&E field"

PROBE_LABELS = [
    "Engineering, bioengineering and biomedical",
    "Engineering, metallurgical and materials",
]


def probe_label_year(year: int, label: str) -> dict:
    rel = read_herd_csv(year)
    sub = rel.filter(
        f"question = '{ERA_A_QUESTION}' AND \"row\" = '{label}'"
    )
    n_rows = sub.aggregate("COUNT(*) AS n").fetchone()[0]
    n_with_value = sub.filter("value IS NOT NULL").aggregate("COUNT(*) AS n").fetchone()[0]
    n_pos_value = sub.filter("value IS NOT NULL AND value > 0").aggregate("COUNT(*) AS n").fetchone()[0]
    sum_value = sub.aggregate("SUM(value) AS s").fetchone()[0]
    return {
        "year": year,
        "label": label,
        "n_rows": n_rows,
        "n_with_value": n_with_value,
        "n_pos_value": n_pos_value,
        "sum_value": sum_value,
    }


def main() -> int:
    print("=== Bioengineering / metallurgical-materials presence probe ===")
    print(f"{'year':<6}{'label':<55}{'n_rows':>8}{'n_with_value':>14}{'n_pos_value':>14}{'sum_value':>16}")
    for year in [1984, 1985, 1989, 1990, 1991, 1996, 1997, 1998, 2009]:
        for lab in PROBE_LABELS:
            r = probe_label_year(year, lab)
            sv = r["sum_value"]
            sv_str = f"{sv:,.0f}" if sv is not None else "None"
            print(f"{r['year']:<6}{r['label']:<55}{r['n_rows']:>8}{r['n_with_value']:>14}{r['n_pos_value']:>14}{sv_str:>16}")

    # Pre-1981 sub-period probe: which fine-leaf engineering labels exist
    # in 1973 vs. 1979 vs. 1980?
    print("\n=== Pre-1981 engineering fine-leaf presence ===")
    eng_leaves = [
        "Engineering, aeronautical and astronautical",
        "Engineering, chemical",
        "Engineering, civil",
        "Engineering, electrical",
        "Engineering, mechanical",
        "Engineering, other",
        "Engineering, bioengineering and biomedical",
        "Engineering, metallurgical and materials",
    ]
    for year in [1973, 1974, 1975, 1977, 1978, 1979, 1980, 1981, 1984]:
        rel = read_herd_csv(year)
        rows = rel.filter(f"question = '{ERA_A_QUESTION}'").project('"row"').distinct()
        present = {r[0] for r in rows.fetchall() if r[0]}
        line = ", ".join(lab.split(", ", 1)[1] for lab in eng_leaves if lab in present)
        n_eng = sum(1 for lab in eng_leaves if lab in present)
        print(f"  {year}: {n_eng}/8 engineering leaves present  [{line}]")

    return 0


if __name__ == "__main__":
    sys.exit(main())
