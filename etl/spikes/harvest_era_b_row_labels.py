"""
etl/spikes/harvest_era_b_row_labels.py — HD 2.1.d era-B row-label harvest.

Per docs/hd_2_1_scoping.md §7 task 2.1.d (0.5 half-days, clean):
harvest era-B row labels from `read_herd_csv(year)` row values for years
2010–2024. Era B fragmented era A's single `'Expenditures by S&E field'`
into multiple source-class questions (HD 1.4 finding, CLAUDE.md §6).

The era-B field-level rows live across two questions:

- `'Federal expenditures by field and agency'`     (Q9, column='Total')
- `'Nonfederal expenditures by field and source'`  (Q11, column='Total')

Harvest both row-label sets separately. They should agree (same field
axis, different source axis); a disagreement is a non-mechanical finding.

Output: crosswalks/_harvest/era_b_row_labels.csv with one row per
(year_range, raw_row_label) per the agreement/disagreement shape.
Schema (when sets agree fully — recommended):
    year_range_start, year_range_end, raw_row_label,
    n_years_observed, first_year_seen, last_year_seen,
    first_year_with_positive_value,
    present_in_q9, present_in_q11,
    source_csv_paths

If sets disagree, a `source_question` column distinguishes Q9-only,
Q11-only, and both rows.

Sub-period transitions to confirm against INVENTORY.md §5.2 / §6:
  - FY 2017: `Engineering, industrial and manufacturing` arrives.
  - FY 2017: `Life sciences, natural resources and conservation` arrives.

§3.6 conditional pre-doc resolution (scoping doc):
  - Psychology — does era B preserve top-level coarse Psychology?
  - Social sciences — does era B preserve top-level coarse Social sciences?

Mechanical-clean → resolution; non-mechanical → stop and surface.

Author: Skipper, 2026-05-01 (HD 2.1.d).
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

ERA_B_Q9 = "Federal expenditures by field and agency"
ERA_B_Q11 = "Nonfederal expenditures by field and source"
YEARS = list(range(2010, 2025))  # 2010..2024 inclusive
OUTPUT_PATH = ROOT / "crosswalks" / "_harvest" / "era_b_row_labels.csv"

# Column filter: row-label harvest at the all-source axis. Per scoping
# §2.1, the summation rule consumes column='Total' from both Q9 and Q11.
# Restricting harvest to column='Total' aligns the row-label set with
# the rule's consumption pattern; agency-/source-breakdown columns may
# carry the same row labels but harvesting all of them inflates the
# row dictionary with axis-by-axis duplicates.
COLUMN_TOTAL = "Total"


def harvest_year(
    year: int, question: str
) -> tuple[set[str], set[str]]:
    """Return (all_labels, labels_with_positive_value) for `question` in `year`,
    restricted to column='Total'.

    Returns ((), ()) if the year file is missing or the question/column
    combination is absent (which itself is a finding to surface).
    """
    rel = read_herd_csv(year)
    sub = rel.filter(
        f"question = '{question}' AND \"column\" = '{COLUMN_TOTAL}'"
    )
    all_labels: set[str] = {
        v for (v,) in sub.project('"row"').distinct().fetchall() if v is not None
    }
    pos_labels: set[str] = {
        v for (v,) in sub.filter("value IS NOT NULL AND value > 0")
        .project('"row"').distinct().fetchall() if v is not None
    }
    return all_labels, pos_labels


def main() -> int:
    # year -> {question: set of labels}
    year_labels: dict[int, dict[str, set[str]]] = {}
    year_pos_labels: dict[int, dict[str, set[str]]] = {}
    year_zip: dict[int, str] = {}
    missing_years: list[int] = []
    empty_years: list[tuple[int, str]] = []  # (year, question)

    questions = [ERA_B_Q9, ERA_B_Q11]

    for y in YEARS:
        try:
            zp = zip_path_for(y)
            if not zp.exists():
                missing_years.append(y)
                continue
            year_zip[y] = zp.name
            year_labels[y] = {}
            year_pos_labels[y] = {}
            for q in questions:
                labels, pos_labels = harvest_year(y, q)
                if not labels:
                    empty_years.append((y, q))
                year_labels[y][q] = labels
                year_pos_labels[y][q] = pos_labels
        except Exception as e:  # noqa: BLE001
            print(f"  [WARN] {y}: {type(e).__name__}: {e}")
            missing_years.append(y)

    print(f"Years requested: {len(YEARS)} ({YEARS[0]}-{YEARS[-1]})")
    print(f"Years loaded   : {len(year_labels)}")
    print(f"Missing zips   : {missing_years}")
    if empty_years:
        print(f"Empty (no rows for question/column='Total'):")
        for y, q in empty_years:
            print(f"  {y}: {q!r}")

    if not year_labels:
        print("FAIL: no years loaded.")
        return 1

    # Per-year, per-question label counts.
    print("\n=== Per-year label counts (column='Total') ===")
    print(f"{'year':>6} {'Q9':>5} {'Q11':>5} {'Q9∩Q11':>8} {'Q9-only':>9} {'Q11-only':>10}")
    for y in sorted(year_labels):
        q9 = year_labels[y].get(ERA_B_Q9, set())
        q11 = year_labels[y].get(ERA_B_Q11, set())
        both = q9 & q11
        only9 = q9 - q11
        only11 = q11 - q9
        print(f"{y:>6} {len(q9):>5} {len(q11):>5} {len(both):>8} {len(only9):>9} {len(only11):>10}")

    # ---------------- Q9 vs. Q11 agreement check ----------------
    # If for any year the symmetric difference is non-empty, that's the
    # structural-inconsistency stop-and-surface condition. Report which
    # labels are involved.
    disagreement_years: list[tuple[int, set[str], set[str]]] = []
    for y in sorted(year_labels):
        q9 = year_labels[y].get(ERA_B_Q9, set())
        q11 = year_labels[y].get(ERA_B_Q11, set())
        if q9 != q11:
            disagreement_years.append((y, q9 - q11, q11 - q9))

    print("\n=== Q9 vs. Q11 row-label agreement ===")
    if not disagreement_years:
        print("  CLEAN: Q9 and Q11 carry identical row-label sets in every year.")
    else:
        print(f"  DISAGREEMENT in {len(disagreement_years)} year(s):")
        for y, q9_only, q11_only in disagreement_years:
            print(f"    {y}: Q9-only={sorted(q9_only)}; Q11-only={sorted(q11_only)}")

    # ---------------- Year-range buckets via fingerprint ----------------
    # Use the union (Q9 ∪ Q11) as the per-year fingerprint when the sets
    # agree (then union == Q9 == Q11). When they disagree, document each
    # year in which bucket it sits.
    fingerprint_to_years: dict[frozenset[str], list[int]] = defaultdict(list)
    for y in sorted(year_labels):
        q9 = year_labels[y].get(ERA_B_Q9, set())
        q11 = year_labels[y].get(ERA_B_Q11, set())
        # Use the union as fingerprint key — captures any divergence.
        fp = frozenset(q9 | q11)
        fingerprint_to_years[fp].append(y)

    print(f"\n=== Distinct label-set fingerprints (Q9 ∪ Q11): {len(fingerprint_to_years)} ===")
    buckets: list[tuple[int, int, frozenset[str], list[int]]] = []
    for fp, ys in fingerprint_to_years.items():
        buckets.append((min(ys), max(ys), fp, sorted(ys)))
    buckets.sort(key=lambda b: (b[0], b[1]))
    for start, end, fp, ys in buckets:
        contig = (ys == list(range(ys[0], ys[-1] + 1)))
        contig_flag = "" if contig else " (NON-CONTIGUOUS)"
        print(f"  {start}-{end}: {len(fp):3d} labels, {len(ys)} years{contig_flag}")
        if not contig:
            print(f"      years: {ys}")

    # ---------------- Per-label aggregation across Q9 and Q11 ----------------
    # For each label, capture: union presence, Q9 presence, Q11 presence,
    # first-seen, last-seen, first-positive-value (across either question).
    label_first: dict[str, int] = {}
    label_last: dict[str, int] = {}
    label_first_pos: dict[str, int] = {}
    label_in_q9: dict[str, set[int]] = defaultdict(set)
    label_in_q11: dict[str, set[int]] = defaultdict(set)
    for y in sorted(year_labels):
        q9 = year_labels[y].get(ERA_B_Q9, set())
        q11 = year_labels[y].get(ERA_B_Q11, set())
        union = q9 | q11
        for lab in union:
            if lab not in label_first or y < label_first[lab]:
                label_first[lab] = y
            if lab not in label_last or y > label_last[lab]:
                label_last[lab] = y
        for lab in q9:
            label_in_q9[lab].add(y)
        for lab in q11:
            label_in_q11[lab].add(y)
        # First-positive-value: any year where the label has value > 0
        # in either Q9 or Q11.
        pos_any = year_pos_labels[y].get(ERA_B_Q9, set()) | year_pos_labels[y].get(
            ERA_B_Q11, set()
        )
        for lab in pos_any:
            if lab not in label_first_pos or y < label_first_pos[lab]:
                label_first_pos[lab] = y

    # ---------------- Write CSV ----------------
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "year_range_start", "year_range_end", "raw_row_label",
            "n_years_observed", "first_year_seen", "last_year_seen",
            "first_year_with_positive_value",
            "present_in_q9", "present_in_q11",
            "source_csv_paths",
        ])
        for start, end, fp, ys in buckets:
            for lab in sorted(fp):
                # n_years_observed: count within this bucket (union presence)
                bucket_years_with_label = [
                    y for y in ys
                    if lab in (year_labels[y].get(ERA_B_Q9, set())
                               | year_labels[y].get(ERA_B_Q11, set()))
                ]
                n_in_bucket = len(bucket_years_with_label)
                # present_in_q9 / present_in_q11: 1 if the label appears in
                # that question in *any* year of this bucket, else 0.
                bucket_q9 = any(
                    lab in year_labels[y].get(ERA_B_Q9, set())
                    for y in ys
                )
                bucket_q11 = any(
                    lab in year_labels[y].get(ERA_B_Q11, set())
                    for y in ys
                )
                # first_year_with_positive_value: uniform — populate for
                # every label using the global first-pos year (across all
                # bucket-years). If the label never carries a positive
                # value, populate with the first-seen year as a floor (the
                # label exists; mark it data-onset == label-onset rather
                # than NULL, keeping the column uniformly populated).
                fyp = label_first_pos.get(lab, label_first[lab])
                w.writerow([
                    start, end, lab,
                    n_in_bucket,
                    label_first[lab],
                    label_last[lab],
                    fyp,
                    1 if bucket_q9 else 0,
                    1 if bucket_q11 else 0,
                    ";".join(sorted({
                        year_zip[y] for y in bucket_years_with_label
                    })),
                ])

    print(f"\nHarvest written: {OUTPUT_PATH}")

    # ---------------- Sub-period transition check ----------------
    # Confirm INVENTORY.md §5.2 / §6 transitions:
    #   FY 2017: 'Engineering, industrial and manufacturing'
    #   FY 2017: 'Life sciences, natural resources and conservation'
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

    # Disagreements between first-seen and first-positive-value.
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

    # Last-seen years (labels exiting before 2024).
    print("\n=== Label last-seen years (labels that exit before 2024) ===")
    by_last: dict[int, list[str]] = defaultdict(list)
    for lab, ly in label_last.items():
        if ly < 2024:
            by_last[ly].append(lab)
    if not by_last:
        print("  (none — all labels survive to 2024)")
    else:
        for ly in sorted(by_last):
            print(f"  {ly}: {len(by_last[ly])} label(s) last observed")
            for lab in sorted(by_last[ly]):
                print(f"      - {lab!r}")

    # ---------------- §3.6 conditional pre-doc resolution ----------------
    print("\n=== §3.6 conditional pre-doc resolution probe ===")
    # All labels that contain 'Psychology' or 'Social sciences' (case-insensitive
    # substring) — surfaces both top-level coarse rollups and any fine
    # leaves (which would themselves be a finding under era B).
    psych_labels = sorted({
        lab for lab in label_first
        if "psychology" in lab.lower()
    })
    social_labels = sorted({
        lab for lab in label_first
        if "social sciences" in lab.lower()
    })
    print("  Psychology-related labels (era-B union, all years):")
    for lab in psych_labels:
        in_q9 = "Y" if label_in_q9.get(lab) else "n"
        in_q11 = "Y" if label_in_q11.get(lab) else "n"
        print(f"    [{in_q9}/{in_q11}] {lab!r}  first={label_first[lab]} last={label_last[lab]}")
    if not psych_labels:
        print("    (none — surface; would mean era B drops Psychology entirely)")

    print("  Social-sciences-related labels (era-B union, all years):")
    for lab in social_labels:
        in_q9 = "Y" if label_in_q9.get(lab) else "n"
        in_q11 = "Y" if label_in_q11.get(lab) else "n"
        print(f"    [{in_q9}/{in_q11}] {lab!r}  first={label_first[lab]} last={label_last[lab]}")
    if not social_labels:
        print("    (none — surface; would mean era B drops Social sciences entirely)")

    # ---------------- Coarse-bucket presence summary ----------------
    # For sanity: verify the §3.6 verified-clean coarse buckets are present
    # era B (Engineering, Life sciences, Math&CS, Physical sciences). And
    # confirm the documented W5 rename: Environmental sciences → Geosciences.
    print("\n=== Coarse-bucket presence summary (era-B union) ===")
    coarse_probes = [
        ("Engineering", ["engineering"]),
        ("Life sciences", ["life sciences"]),
        ("Computer / Math", ["computer", "mathematic", "mathematics"]),
        ("Physical sciences", ["physical sciences"]),
        ("Environmental sciences", ["environmental sciences"]),
        ("Geosciences (era-B rename)", ["geosciences"]),
        ("Psychology", ["psychology"]),
        ("Social sciences", ["social sciences"]),
        ("Non-S&E", ["non-s&e", "non s&e", "non-se"]),
    ]
    for label, needles in coarse_probes:
        hits = sorted({
            lab for lab in label_first
            if any(n in lab.lower() for n in needles)
        })
        print(f"  {label}: {len(hits)} label(s)")
        for lab in hits[:8]:
            print(f"      {lab!r}")
        if len(hits) > 8:
            print(f"      ... ({len(hits) - 8} more)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
