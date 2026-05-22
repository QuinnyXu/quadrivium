"""
etl/spikes/harvest_era_a_row_labels.py — HD 2.1.c era-A row-label harvest.

Per docs/hd_2_1_scoping.md §7 task 2.1.c (0.5 half-days, clean):
harvest era-A row labels from `read_herd_csv(year)` row values for years
1973–2009, filtered to `question = 'Expenditures by S&E field'` (the
era-A field-level question per HD 1.4 finding, CLAUDE.md §6).

Output: crosswalks/_harvest/era_a_row_labels.csv with one row per
(year_range, raw_row_label) where the row label is stable across the
range. Schema:
    year_range_start, year_range_end, raw_row_label,
    n_years_observed, first_year_seen, last_year_seen,
    first_year_with_positive_value, source_csv_paths

`first_year_seen` is when the **label** first appears in the CSV row
dictionary. `first_year_with_positive_value` is when the field first
carries actual nonzero positive expenditure data. These differ for
bioengineering (label 1984, data FY 1997) and metallurgical+materials
(label 1984, data FY 1990) — the FY24 Guide page 14 dates refer to the
data-onset year, not the label-onset year. HD 2.1.e uses both anchors
when authoring decision_rationale.

Author: Skipper, 2026-05-01 (HD 2.1.c).
Throwaway harvester — output is the artifact; rationales are HD 2.1.e.
"""

from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path

# Make the repo root importable so `etl._load` resolves when run as a script.
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from etl._load import read_herd_csv, zip_path_for  # noqa: E402

ERA_A_QUESTION = "Expenditures by S&E field"
YEARS = list(range(1973, 2010))  # 1973..2009 inclusive
OUTPUT_PATH = ROOT / "crosswalks" / "_harvest" / "era_a_row_labels.csv"


def harvest_year(year: int) -> tuple[set[str], set[str]]:
    """Return (all_labels, labels_with_positive_value) for the era-A
    field-level question in `year`.

    `all_labels` is every distinct row value for the question.
    `labels_with_positive_value` is the subset whose `value > 0` for at
    least one observation in that year — distinguishing label-presence
    from reportable-data presence (see module docstring).

    Returns ((), ()) if the year file is missing or the question is
    absent (which itself is a finding to surface).
    """
    rel = read_herd_csv(year)
    sub = rel.filter(f"question = '{ERA_A_QUESTION}'")
    all_labels: set[str] = {
        v for (v,) in sub.project('"row"').distinct().fetchall() if v is not None
    }
    pos_labels: set[str] = {
        v for (v,) in sub.filter("value IS NOT NULL AND value > 0")
        .project('"row"').distinct().fetchall() if v is not None
    }
    return all_labels, pos_labels


def main() -> int:
    # year -> set of row labels
    year_labels: dict[int, set[str]] = {}
    year_pos_labels: dict[int, set[str]] = {}
    year_zip: dict[int, str] = {}
    missing_years: list[int] = []
    empty_years: list[int] = []

    for y in YEARS:
        try:
            zp = zip_path_for(y)
            if not zp.exists():
                missing_years.append(y)
                continue
            year_zip[y] = zp.name
            labels, pos_labels = harvest_year(y)
            if not labels:
                empty_years.append(y)
            year_labels[y] = labels
            year_pos_labels[y] = pos_labels
        except Exception as e:  # noqa: BLE001
            print(f"  [WARN] {y}: {type(e).__name__}: {e}")
            missing_years.append(y)

    # Coverage check.
    print(f"Years requested: {len(YEARS)} ({YEARS[0]}–{YEARS[-1]})")
    print(f"Years loaded   : {len(year_labels)}")
    print(f"Missing zips   : {missing_years}")
    print(f"Empty (no '{ERA_A_QUESTION}' rows): {empty_years}")

    if not year_labels:
        print("FAIL: no years loaded.")
        return 1

    # Per-year label-set fingerprint, year-by-year.
    print("\n=== Per-year label counts ===")
    for y in sorted(year_labels):
        print(f"  {y}: {len(year_labels[y]):3d} labels")

    # Group years by identical label-set fingerprint to find stable ranges.
    fingerprint_to_years: dict[frozenset[str], list[int]] = defaultdict(list)
    for y in sorted(year_labels):
        fp = frozenset(year_labels[y])
        fingerprint_to_years[fp].append(y)

    print(f"\n=== Distinct label-set fingerprints: {len(fingerprint_to_years)} ===")
    # Convert to ordered, contiguous-or-not year-range buckets.
    # Within a fingerprint, the year list is sorted; report it as-is (gaps
    # are possible if any year is empty/missing).
    buckets: list[tuple[int, int, frozenset[str], list[int]]] = []
    for fp, ys in fingerprint_to_years.items():
        buckets.append((min(ys), max(ys), fp, sorted(ys)))
    buckets.sort(key=lambda b: (b[0], b[1]))

    for start, end, fp, ys in buckets:
        contig = (ys == list(range(ys[0], ys[-1] + 1)))
        contig_flag = "" if contig else " (NON-CONTIGUOUS)"
        print(f"  {start}–{end}: {len(fp):3d} labels, {len(ys)} years{contig_flag}")
        # Print the years comprising the bucket if non-contiguous.
        if not contig:
            print(f"      years: {ys}")

    # Per-label aggregation across all years (for the CSV).
    label_first: dict[str, int] = {}
    label_last: dict[str, int] = {}
    label_first_pos: dict[str, int] = {}
    label_years: dict[str, list[int]] = defaultdict(list)
    label_paths: dict[str, set[str]] = defaultdict(set)
    for y in sorted(year_labels):
        for lab in year_labels[y]:
            label_years[lab].append(y)
            if lab not in label_first or y < label_first[lab]:
                label_first[lab] = y
            if lab not in label_last or y > label_last[lab]:
                label_last[lab] = y
            label_paths[lab].add(year_zip[y])
        for lab in year_pos_labels.get(y, set()):
            if lab not in label_first_pos or y < label_first_pos[lab]:
                label_first_pos[lab] = y

    # Write one row per (year_range_bucket, label) — i.e., for each
    # fingerprint bucket, emit each label in that fingerprint with the
    # bucket's range and the per-label observation totals across all years.
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "year_range_start", "year_range_end", "raw_row_label",
            "n_years_observed", "first_year_seen", "last_year_seen",
            "first_year_with_positive_value", "source_csv_paths",
        ])
        for start, end, fp, ys in buckets:
            for lab in sorted(fp):
                # n_years_observed: count within this bucket
                n_in_bucket = len([y for y in ys if lab in year_labels[y]])
                w.writerow([
                    start, end, lab,
                    n_in_bucket,
                    label_first[lab],
                    label_last[lab],
                    label_first_pos.get(lab, ""),
                    ";".join(sorted({year_zip[y] for y in ys if lab in year_labels[y]})),
                ])

    print(f"\nHarvest written: {OUTPUT_PATH}")

    # Sub-period transition check: which labels first appear in which year?
    print("\n=== Label first-seen years (sub-period transition probe) ===")
    by_first: dict[int, list[str]] = defaultdict(list)
    for lab, fy in label_first.items():
        by_first[fy].append(lab)
    for fy in sorted(by_first):
        print(f"  {fy}: {len(by_first[fy])} new label(s)")
        for lab in sorted(by_first[fy]):
            fyp = label_first_pos.get(lab, None)
            tag = f"  (first positive value: {fyp})" if fyp and fyp != fy else ""
            print(f"      + {lab!r}{tag}")

    # Label first-positive-value year, when it disagrees with first-seen.
    print("\n=== Labels where first-positive-value differs from first-seen ===")
    diffs = [
        (lab, label_first[lab], label_first_pos.get(lab))
        for lab in sorted(label_first)
        if label_first_pos.get(lab) and label_first_pos[lab] != label_first[lab]
    ]
    if not diffs:
        print("  (none)")
    for lab, lfs, lfp in diffs:
        print(f"  {lab!r}: label first-seen {lfs}, first positive value {lfp}")

    # Label last-seen years (labels that disappear before 2009).
    print("\n=== Label last-seen years (labels that exit before 2009) ===")
    by_last: dict[int, list[str]] = defaultdict(list)
    for lab, ly in label_last.items():
        if ly < 2009:
            by_last[ly].append(lab)
    if not by_last:
        print("  (none — all labels survive to 2009)")
    else:
        for ly in sorted(by_last):
            print(f"  {ly}: {len(by_last[ly])} label(s) last observed")
            for lab in sorted(by_last[ly]):
                print(f"      - {lab!r}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
