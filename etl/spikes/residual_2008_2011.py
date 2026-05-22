"""
etl/spikes/residual_2008_2011.py — HD 2.1.b residual computation.

Computes per-(institution × coarse_bucket × year_pair) residuals between
era-A direct field-level totals and era-B reconstructed totals (Q9 + Q11
column='Total'), per the locked summation rule from
docs/hd_2_1_scoping.md §2.1.

Sample shape per HD 2.1.b directive:
- Years: FY 2008, 2009 (era A); FY 2010, 2011 (era B reconstructed).
- Institutions: top 10 by FY 2008 total R&D expenditure (row='All',
  column='Total' in era-A `'Expenditures by S&E field'`). If any of the
  top 10 are missing from FY 2010, substitute with the next-ranked
  institution that is present in all four years 2008–2011. Substitutions
  documented in the report.
- Coarse buckets: 7 gating + Other sciences nec + Non-S&E (supporting).
- Adjacent residual: 2009 vs. reconstructed 2010.
- Long-gap sanity: 2008 vs. reconstructed 2011.

Coarse aggregation rule (no crosswalks/discipline_coarse.csv yet — that
is HD 2.1.f, gated on this residual passing):

| coarse_bucket             | era-A label predicate                                  | era-B label predicate                                                            |
|---------------------------|--------------------------------------------------------|----------------------------------------------------------------------------------|
| Engineering               | starts_with('Engineering, ')                           | starts_with('Engineering, ')                                                     |
| Life sciences             | starts_with('Life sciences, ')                         | starts_with('Life sciences, ')                                                   |
| Math & CS                 | in {'Mathematical sciences, all', 'Computer sciences, all'} | in {'Mathematics and statistics, all', 'Computer and information sciences, all'} |
| Physical sciences         | starts_with('Physical sciences, ')                     | starts_with('Physical sciences, ')                                               |
| Geosciences/Environmental | starts_with('Environmental sciences, ')                | starts_with('Geosciences, ')                                                     |
| Psychology                | == 'Psychology, all'                                   | == 'Psychology, all'                                                             |
| Social sciences           | starts_with('Social sciences, ')                       | starts_with('Social sciences, ')                                                 |
| Other sciences nec        | == 'Other sciences, all'                               | == 'Other sciences, all'                                                         |
| Non-S&E                   | starts_with('Non-S&E')                                 | starts_with('Non-S&E')                                                           |

Aggregation strategy: for each coarse bucket, prefer the `*, all` rollup
where present (avoids leaf double-counting). Era A has `*, all` rollups
for all 7 + Other sciences. Era B has `*, all` rollups for all coarse
buckets (verified from `crosswalks/_harvest/era_b_row_labels.csv`).

Output:
- `validation/reports/era_reconciliation_2008_2011.md` — prose + tables.

NOT a production module. Spike-shape: throwaway compute script to gate
the residual disposition. The residual analysis itself is a deposit
artifact; this script produces it reproducibly.

Author: Skipper, 2026-05-01 (HD 2.1.b).
"""

from __future__ import annotations

import statistics
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from etl._load import read_herd_csv  # noqa: E402

ERA_A_QUESTION = "Expenditures by S&E field"
ERA_B_Q9 = "Federal expenditures by field and agency"
ERA_B_Q11 = "Nonfederal expenditures by field and source"

OUTPUT_PATH = ROOT / "validation" / "reports" / "era_reconciliation_2008_2011.md"

# Coarse-bucket assignment. Order matters: more-specific predicates first.
# Returns the coarse bucket name or None if unmappable.
def coarse_bucket(label: str, era: str) -> Optional[str]:
    if label is None:
        return None
    if label == "Other sciences, all":
        return "Other sciences nec"
    if label.startswith("Non-S&E"):
        return "Non-S&E"
    if label.startswith("Engineering, "):
        return "Engineering"
    if label.startswith("Life sciences, "):
        return "Life sciences"
    if label.startswith("Physical sciences, "):
        return "Physical sciences"
    if label.startswith("Social sciences, "):
        return "Social sciences"
    if label == "Psychology, all":
        return "Psychology"
    if era == "A":
        if label.startswith("Environmental sciences, "):
            return "Geosciences/Environmental"
        if label in ("Mathematical sciences, all", "Computer sciences, all"):
            return "Math & CS"
    else:  # era B
        if label.startswith("Geosciences, "):
            return "Geosciences/Environmental"
        if label in (
            "Mathematics and statistics, all",
            "Computer and information sciences, all",
        ):
            return "Math & CS"
    return None


# Whether a label is the rollup we prefer when summing the coarse bucket.
# Era A rollups: 'Engineering, all', 'Life sciences, all', etc.
# Era B rollups: same '*, all' shape; for Geosciences: 'Geosciences, atmospheric sciences, and ocean sciences, all'.
def is_coarse_rollup(label: str, era: str) -> bool:
    if label is None:
        return False
    if label in (
        "Other sciences, all",
        "Engineering, all",
        "Life sciences, all",
        "Physical sciences, all",
        "Social sciences, all",
        "Psychology, all",
        "Non-S&E, all",
    ):
        return True
    if era == "A" and label in ("Environmental sciences, all", "Mathematical sciences, all", "Computer sciences, all"):
        return True
    if era == "B" and label in (
        "Geosciences, atmospheric sciences, and ocean sciences, all",
        "Geosciences, atmospheric sciences and ocean sciences, all",
        "Mathematics and statistics, all",
        "Computer and information sciences, all",
    ):
        return True
    return False


# Math & CS has TWO rollups (Math + CS), so its bucket value is the SUM
# of its two `*, all` rollups, not a single `*, all` rollup.
MATH_CS_TWO_ROLLUP_BUCKETS = {"Math & CS"}


# ---------------------------------------------------------------------------
# Era-A read: institution-year-discipline values from `Expenditures by S&E field`
# ---------------------------------------------------------------------------


@dataclass
class CellValue:
    inst_id: str
    inst_name: str
    bucket: str
    value_kusd: float


def era_a_values(year: int) -> dict[tuple[str, str], float]:
    """Return {(inst_id, bucket) -> sum_value_kusd} for era-A direct read.

    Sums coarse-rollup labels per bucket; for Math&CS, sums both rollups
    ('Mathematical sciences, all' + 'Computer sciences, all').
    """
    rel = read_herd_csv(year)
    sub = rel.filter(
        f"question = '{ERA_A_QUESTION}' AND \"column\" = 'Total'"
    )
    rows = sub.project(
        'inst_id, inst_name_long, "row" AS row_label, value'
    ).fetchall()

    out: dict[tuple[str, str], float] = defaultdict(float)
    inst_names: dict[str, str] = {}
    for inst_id, inst_name, row_label, value in rows:
        if inst_id is None or value is None:
            continue
        if not is_coarse_rollup(row_label, "A"):
            continue
        bucket = coarse_bucket(row_label, "A")
        if bucket is None:
            continue
        out[(str(inst_id), bucket)] += float(value)
        inst_names[str(inst_id)] = inst_name or ""

    # Attach inst_names via a side-channel dict.
    era_a_values.last_names = inst_names  # type: ignore[attr-defined]
    return dict(out)


def era_a_total_all(year: int) -> dict[str, tuple[str, float]]:
    """Return {inst_id -> (inst_name, total_rd_kusd)} from row='All', column='Total'.

    Used for top-10 institution selection (FY 2008).
    """
    rel = read_herd_csv(year)
    sub = rel.filter(
        f"question = '{ERA_A_QUESTION}' AND \"column\" = 'Total' AND \"row\" = 'All'"
    )
    rows = sub.project("inst_id, inst_name_long, value").fetchall()
    out: dict[str, tuple[str, float]] = {}
    for inst_id, inst_name, value in rows:
        if inst_id is None or value is None:
            continue
        out[str(inst_id)] = (inst_name or "", float(value))
    return out


# ---------------------------------------------------------------------------
# Era-B read: reconstructed all-source = Q9 'Total' + Q11 'Total'
# ---------------------------------------------------------------------------


def era_b_values(year: int) -> dict[tuple[str, str], float]:
    """Return {(inst_id, bucket) -> Q9_total + Q11_total} per coarse bucket.

    Sums coarse-rollup labels (`*, all`) per bucket; Math & CS sums both
    rollups. Q9 and Q11 row labels can drift in punctuation (e.g.,
    `Geosciences, ... ocean sciences,` Oxford comma in Q9 vs. no Oxford
    comma in Q11) — both Q9 and Q11 rollups for Geosciences map to the
    same coarse bucket, so the union-on-bucket aggregation absorbs this
    drift transparently.
    """
    rel = read_herd_csv(year)
    sub = rel.filter(
        f"question IN ('{ERA_B_Q9}', '{ERA_B_Q11}') AND \"column\" = 'Total'"
    )
    rows = sub.project(
        'inst_id, inst_name_long, "row" AS row_label, value'
    ).fetchall()

    out: dict[tuple[str, str], float] = defaultdict(float)
    inst_names: dict[str, str] = {}
    for inst_id, inst_name, row_label, value in rows:
        if inst_id is None or value is None:
            continue
        if not is_coarse_rollup(row_label, "B"):
            continue
        bucket = coarse_bucket(row_label, "B")
        if bucket is None:
            continue
        out[(str(inst_id), bucket)] += float(value)
        inst_names[str(inst_id)] = inst_name or ""

    era_b_values.last_names = inst_names  # type: ignore[attr-defined]
    return dict(out)


# ---------------------------------------------------------------------------
# Top-10 selection
# ---------------------------------------------------------------------------


def select_top10_present_all_years(
    fy2008_totals: dict[str, tuple[str, float]],
    inst_present_2010: set[str],
    inst_present_2009: set[str],
    inst_present_2011: set[str],
) -> tuple[list[tuple[str, str, float]], list[tuple[str, str, str]]]:
    """Pick top 10 by FY 2008 total R&D, substituting if missing 2009/2010/2011.

    Per HD 2.1.b directive: 'If any of those top 10 are missing from FY 2010
    (population shift per W6), substitute with the next-ranked institution
    that is present in all four years 2008–2011.' We extend this to require
    presence in 2009 and 2011 too (the residual computation needs all four).

    Returns:
        selected: list of (inst_id, inst_name, fy2008_total_kusd) — exactly 10.
        substitutions: list of (dropped_inst_id, dropped_inst_name, reason) for the report.
    """
    # Sorted descending by FY 2008 total.
    ranked = sorted(
        fy2008_totals.items(),
        key=lambda kv: kv[1][1],
        reverse=True,
    )
    selected: list[tuple[str, str, float]] = []
    substitutions: list[tuple[str, str, str]] = []
    for inst_id, (inst_name, total) in ranked:
        missing = []
        if inst_id not in inst_present_2009:
            missing.append("2009")
        if inst_id not in inst_present_2010:
            missing.append("2010")
        if inst_id not in inst_present_2011:
            missing.append("2011")
        if missing:
            substitutions.append(
                (inst_id, inst_name, f"missing {','.join(missing)}")
            )
            continue
        selected.append((inst_id, inst_name, total))
        if len(selected) == 10:
            break
    return selected, substitutions


# ---------------------------------------------------------------------------
# Residual computation
# ---------------------------------------------------------------------------


@dataclass
class ResidualRow:
    inst_id: str
    inst_name: str
    bucket: str
    era_a_2008_kusd: Optional[float]
    era_a_2009_kusd: Optional[float]
    era_b_recon_2010_kusd: Optional[float]
    era_b_recon_2011_kusd: Optional[float]
    residual_2009_2010_pct: Optional[float]
    residual_2008_2011_pct: Optional[float]
    pre_doc_class: bool
    likely_cause: str


GATING_BUCKETS = (
    "Engineering",
    "Life sciences",
    "Math & CS",
    "Physical sciences",
    "Geosciences/Environmental",
    "Psychology",
    "Social sciences",
)
SUPPORTING_BUCKETS = (
    "Other sciences nec",
    "Non-S&E",
)
ALL_BUCKETS = GATING_BUCKETS + SUPPORTING_BUCKETS

# Pre-doc list (post §3.6 update at this turn): only Geosciences/Environmental.
PRE_DOC_BUCKETS = {"Geosciences/Environmental"}


def safe_pct(numer: Optional[float], denom: Optional[float]) -> Optional[float]:
    if numer is None or denom is None:
        return None
    if denom == 0:
        return None
    return (numer - denom) / numer if False else (numer - denom) / numer  # placeholder; computed below


def residual_pct(era_a_value: Optional[float], era_b_value: Optional[float]) -> Optional[float]:
    """(era_a - era_b) / era_a, or None if era_a is missing/zero."""
    if era_a_value is None or era_b_value is None:
        return None
    if era_a_value == 0:
        return None
    return (era_a_value - era_b_value) / era_a_value


def likely_cause_for(bucket: str, residual: Optional[float]) -> str:
    if residual is None:
        return "missing-data"
    a = abs(residual)
    if bucket in PRE_DOC_BUCKETS:
        return "W5 definitional drift (Environmental→Geosciences scope expansion)"
    if a < 0.02:
        return "within reporting noise"
    if a < 0.05:
        return "minor; W6 population-scope shift / imputation differences"
    if a < 0.15:
        return "elevated; W6/W2 carve-out drift candidate"
    return "OUT OF BAND — investigate"


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def median_pct(values: list[Optional[float]]) -> Optional[float]:
    clean = [v for v in values if v is not None]
    if not clean:
        return None
    return statistics.median(clean)


def fmt_pct(p: Optional[float]) -> str:
    if p is None:
        return "n/a"
    return f"{p*100:+.2f}%"


def fmt_kusd(v: Optional[float]) -> str:
    if v is None:
        return "n/a"
    return f"{v:,.0f}"


def main() -> int:
    print("=== HD 2.1.b residual computation ===")
    print("Loading era-A FY 2008 totals (top-10 selection)...")
    fy2008 = era_a_total_all(2008)
    print(f"  FY 2008 institutions with row='All' total: {len(fy2008)}")

    print("Loading era-A 2009, era-B 2010 / 2011 institution sets (membership check)...")
    fy2009 = era_a_total_all(2009)
    fy2010_b = era_b_values(2010)
    fy2011_b = era_b_values(2011)
    inst_2009 = set(fy2009.keys())
    inst_2010 = {k[0] for k in fy2010_b.keys()}
    inst_2011 = {k[0] for k in fy2011_b.keys()}
    print(f"  2009 inst: {len(inst_2009)}, 2010 inst: {len(inst_2010)}, 2011 inst: {len(inst_2011)}")

    print("Selecting top 10 by FY 2008 R&D, present in all four years...")
    selected, substitutions = select_top10_present_all_years(
        fy2008, inst_2010, inst_2009, inst_2011
    )
    print(f"  selected: {len(selected)} institutions")
    print(f"  substitutions logged: {len(substitutions)}")
    for inst_id, inst_name, total in selected:
        print(f"    {inst_id} {inst_name!r}  FY 2008 total = ${total:,.0f}k")

    selected_ids = {inst_id for inst_id, _, _ in selected}

    print("Loading per-bucket values for the 4 years × 10 institutions...")
    a08 = era_a_values(2008)
    a09 = era_a_values(2009)
    b10 = fy2010_b
    b11 = fy2011_b

    # Filter to selected institutions.
    a08 = {k: v for k, v in a08.items() if k[0] in selected_ids}
    a09 = {k: v for k, v in a09.items() if k[0] in selected_ids}
    b10 = {k: v for k, v in b10.items() if k[0] in selected_ids}
    b11 = {k: v for k, v in b11.items() if k[0] in selected_ids}

    # Build residual rows: one per (inst, bucket) for 10 × 9 = 90 rows.
    rows: list[ResidualRow] = []
    inst_name_map = {inst_id: name for inst_id, name, _ in selected}
    for inst_id in (i for i, _, _ in selected):
        for bucket in ALL_BUCKETS:
            v_a08 = a08.get((inst_id, bucket))
            v_a09 = a09.get((inst_id, bucket))
            v_b10 = b10.get((inst_id, bucket))
            v_b11 = b11.get((inst_id, bucket))
            r_2009_2010 = residual_pct(v_a09, v_b10)
            r_2008_2011 = residual_pct(v_a08, v_b11)
            cause = likely_cause_for(bucket, r_2009_2010)
            rows.append(ResidualRow(
                inst_id=inst_id,
                inst_name=inst_name_map[inst_id],
                bucket=bucket,
                era_a_2008_kusd=v_a08,
                era_a_2009_kusd=v_a09,
                era_b_recon_2010_kusd=v_b10,
                era_b_recon_2011_kusd=v_b11,
                residual_2009_2010_pct=r_2009_2010,
                residual_2008_2011_pct=r_2008_2011,
                pre_doc_class=bucket in PRE_DOC_BUCKETS,
                likely_cause=cause,
            ))

    # ---------------- Per-bucket median residual ----------------
    bucket_medians: dict[str, dict[str, Optional[float]]] = {}
    for bucket in ALL_BUCKETS:
        b_rows = [r for r in rows if r.bucket == bucket]
        bucket_medians[bucket] = {
            "median_2009_2010": median_pct([r.residual_2009_2010_pct for r in b_rows]),
            "median_2008_2011": median_pct([r.residual_2008_2011_pct for r in b_rows]),
            "max_abs_2009_2010": max(
                (abs(r.residual_2009_2010_pct) for r in b_rows if r.residual_2009_2010_pct is not None),
                default=None,
            ),
            "n_cells": sum(1 for r in b_rows if r.residual_2009_2010_pct is not None),
        }

    # ---------------- Gate verdict ----------------
    reopen_triggers: list[str] = []
    for bucket in GATING_BUCKETS:
        if bucket in PRE_DOC_BUCKETS:
            continue
        m = bucket_medians[bucket]["median_2009_2010"]
        if m is not None and abs(m) > 0.05:
            reopen_triggers.append(
                f"Bucket-median trigger: {bucket} median residual = {fmt_pct(m)} (>5%)"
            )
    for r in rows:
        if r.bucket not in GATING_BUCKETS or r.bucket in PRE_DOC_BUCKETS:
            continue
        if r.residual_2009_2010_pct is None:
            continue
        if abs(r.residual_2009_2010_pct) > 0.15:
            reopen_triggers.append(
                f"Cell trigger: {r.inst_name} ({r.inst_id}) × {r.bucket} = "
                f"{fmt_pct(r.residual_2009_2010_pct)} (>15%)"
            )

    gate_verdict = "CLEAR" if not reopen_triggers else "REOPEN"

    # ---------------- ARRA case-(a) confirmation ----------------
    # For each year 2010, 2011: compute federal-only 2010 across 10 insts as
    # SUM Q9 column='Total' for selected coarse rollups; compare to all-source
    # ratio. We don't have NSF aggregates handy locally; instead, we report
    # whether all-source residuals are clean (consistent magnitude) — the
    # directive specifies this as a 'side-product, not a separate gate.'
    arra_summary = (
        "ARRA case-(a) check: federal stream is bundled into Q9 column='Total' by NSF's "
        "aggregation. Within HD 2.1.b's resource budget, no published-NSF-federal-aggregate "
        "external reconciliation was attempted (HD 2.7 owns external reconciliation per scoping §8.7). "
        "Internal consistency check: if all-source residuals (this report) are within band, the "
        "all-source rule reconstructs without an explicit ARRA add — consistent with case (a) build "
        "assumption. Residuals exceeding the band on federal-heavy buckets (Engineering, Physical "
        "sciences, Life sciences) would be the empirical signal for case (b)."
    )

    # ---------------- Write report ----------------
    write_report(
        rows=rows,
        selected=selected,
        substitutions=substitutions,
        bucket_medians=bucket_medians,
        reopen_triggers=reopen_triggers,
        gate_verdict=gate_verdict,
        arra_summary=arra_summary,
    )
    print(f"\nReport written: {OUTPUT_PATH}")
    print(f"\nGate verdict: {gate_verdict}")
    if reopen_triggers:
        print("Reopen triggers:")
        for t in reopen_triggers:
            print(f"  - {t}")
    return 0


def write_report(
    rows: list[ResidualRow],
    selected: list[tuple[str, str, float]],
    substitutions: list[tuple[str, str, str]],
    bucket_medians: dict[str, dict[str, Optional[float]]],
    reopen_triggers: list[str],
    gate_verdict: str,
    arra_summary: str,
) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    a = lines.append

    a("# HD 2.1.b Era Reconciliation Residual Report (FY 2008 / 2009 / 2010 / 2011)")
    a("")
    a("**Authored by:** Skipper, 2026-05-01.")
    a("")
    a("**Scope:** HD 2.1.b residual gate per `docs/hd_2_1_scoping.md` §3. Tests "
      "the locked summation rule (§2.1: era-B all-source total = Q9 Total + Q11 "
      "Total) against era-A direct field-level totals at the institution × "
      "coarse-bucket level. Top-10 institutions by FY 2008 R&D × 7 gating "
      "buckets + 2 supporting buckets, year-pairs 2009→2010 (adjacent) and "
      "2008→2011 (long-gap sanity).")
    a("")
    a("**Path B locked.** External-referent search (Step 1 of HD 2.1.b) "
      "canvassed NSF, NCSES, ASEE, and academic literature for a published "
      "numerical tolerance for the 2010 era boundary. None surfaced — NCSES "
      "guidance is qualitative (\"exact comparisons may be misleading; contact "
      "NCSES\"). The locked 5%/15% thresholds remain in force as "
      "empirically/descriptively grounded; the methods note will footnote: "
      "*\"Thresholds set descriptively against practitioner reporting-noise "
      "priors; no published NSF/NCSES tolerance surface found at HD 2.1.b "
      "external search (sources canvassed: NCSES HERD methodology pages 2021–"
      "2024; NSF Science & Engineering Indicators NSB-2025-7; ASEE Engineering "
      "by the Numbers; academic literature using HERD longitudinally).\"*")
    a("")

    a("## Gate verdict")
    a("")
    a(f"**{gate_verdict}**")
    a("")
    if reopen_triggers:
        a("Triggers:")
        a("")
        for t in reopen_triggers:
            a(f"- {t}")
        a("")
    else:
        a("No non-pre-doc bucket median exceeded ±5%; no non-pre-doc cell "
          "exceeded ±15%. HD 2.1.c–.i greenlight ask follows.")
        a("")

    a("## Sample")
    a("")
    a(f"- **Top-10 institutions** (selected by FY 2008 row='All' column='Total' "
      f"in `Expenditures by S&E field`):")
    a("")
    a("| rank | inst_id | inst_name | fy2008_total_kusd |")
    a("|---:|---|---|---:|")
    for i, (inst_id, inst_name, total) in enumerate(selected, 1):
        a(f"| {i} | {inst_id} | {inst_name} | {fmt_kusd(total)} |")
    a("")
    if substitutions:
        a("- **Substitutions** (institutions in the rank-stream skipped because "
          "they were missing one or more of FY 2009 / 2010 / 2011):")
        a("")
        a("| dropped_inst_id | dropped_inst_name | reason |")
        a("|---|---|---|")
        for inst_id, inst_name, reason in substitutions:
            a(f"| {inst_id} | {inst_name} | {reason} |")
        a("")
    else:
        a("- No substitutions: the top-10 by FY 2008 R&D were all present in "
          "FY 2009, FY 2010, and FY 2011.")
        a("")

    a("## Coarse aggregation rule (ad-hoc; pre-`crosswalks/discipline_coarse.csv`)")
    a("")
    a("Per HD 2.1.b directive: `crosswalks/discipline_coarse.csv` is HD 2.1.f, "
      "gated behind this residual passing. Bucket assignment in this report "
      "uses label-prefix predicates and prefers `*, all` rollups where present "
      "to avoid leaf double-counting:")
    a("")
    a("- `Engineering, *` → Engineering (era-A `Engineering, all` rollup; "
      "era-B `Engineering, all` rollup).")
    a("- `Life sciences, *` → Life sciences (`Life sciences, all`).")
    a("- `Physical sciences, *` → Physical sciences (`Physical sciences, all`).")
    a("- `Mathematical sciences, *` + `Computer sciences, *` (era A) / "
      "`Mathematics and statistics, *` + `Computer and information sciences, *` "
      "(era B) → Math & CS. Two rollups summed: `Mathematical/Mathematics, all` + "
      "`Computer sciences/Computer and information sciences, all`.")
    a("- `Environmental sciences, *` (era A) / `Geosciences, *` (era B) → "
      "Geosciences/Environmental. Pre-documented W5 drift cell.")
    a("- `Psychology, all` → Psychology.")
    a("- `Social sciences, *` → Social sciences (`Social sciences, all`).")
    a("- `Other sciences, all` → Other sciences nec (supporting).")
    a("- `Non-S&E, *` → Non-S&E (supporting; era-A presence: 2003+ only).")
    a("")

    a("## Per-bucket median residuals (10 institutions, 2009→2010)")
    a("")
    a("| bucket | n_cells | median_2009_2010 | max_abs_2009_2010 | median_2008_2011 | gating | pre_doc |")
    a("|---|---:|---:|---:|---:|:---:|:---:|")
    for bucket in ALL_BUCKETS:
        m = bucket_medians[bucket]
        gating = "Y" if bucket in GATING_BUCKETS else "n"
        pre_doc = "Y" if bucket in PRE_DOC_BUCKETS else "n"
        a(f"| {bucket} | {m['n_cells']} | "
          f"{fmt_pct(m['median_2009_2010'])} | "
          f"{fmt_pct(m['max_abs_2009_2010'])} | "
          f"{fmt_pct(m['median_2008_2011'])} | "
          f"{gating} | {pre_doc} |")
    a("")
    a("**Reopen rule (per scoping §3.3):** non-pre-doc bucket with "
      "|median_2009_2010| > 5% OR any non-pre-doc cell with "
      "|residual_2009_2010| > 15%. Pre-doc cells are footnoted as W5 "
      "definitional drift, not rule failures.")
    a("")

    a("## Cell-level residual table")
    a("")
    a("One row per (institution × coarse_bucket). `pre_doc_class = Y` flags "
      "the W5 Environmental→Geosciences cells; their residuals are "
      "reported but do not count against the reopen triggers.")
    a("")
    a("| inst_id | discipline_coarse | era_a_2008_kusd | era_a_2009_kusd | era_b_recon_2010_kusd | era_b_recon_2011_kusd | residual_2009_2010_pct | residual_2008_2011_pct | pre_doc_class | likely_cause |")
    a("|---|---|---:|---:|---:|---:|---:|---:|:---:|---|")
    for r in rows:
        a(
            f"| {r.inst_id} | {r.bucket} | "
            f"{fmt_kusd(r.era_a_2008_kusd)} | "
            f"{fmt_kusd(r.era_a_2009_kusd)} | "
            f"{fmt_kusd(r.era_b_recon_2010_kusd)} | "
            f"{fmt_kusd(r.era_b_recon_2011_kusd)} | "
            f"{fmt_pct(r.residual_2009_2010_pct)} | "
            f"{fmt_pct(r.residual_2008_2011_pct)} | "
            f"{'Y' if r.pre_doc_class else 'n'} | "
            f"{r.likely_cause} |"
        )
    a("")

    a("## ARRA case-(a) confirmation")
    a("")
    a(arra_summary)
    a("")

    a("## Methods-note framing language (conditional)")
    a("")
    if gate_verdict == "CLEAR":
        # Decide between "within reporting noise" and "approximately clean"
        # based on whether any non-pre-doc bucket exceeds 2%.
        any_2_to_5 = False
        for bucket in GATING_BUCKETS:
            if bucket in PRE_DOC_BUCKETS:
                continue
            m = bucket_medians[bucket]["median_2009_2010"]
            if m is not None and abs(m) > 0.02:
                any_2_to_5 = True
                break
        if any_2_to_5:
            a("> *\"We validated reconstruction at the institution-year level. "
              "Approximately-clean reconstruction; residual band documented and "
              "attributed to W6 population-scope shift / W2 carve-out definition "
              "drift / W5 fine-leaf reorganization within preserved coarse "
              "buckets. The W5 Environmental→Geosciences cell carries a known "
              "definitional-drift footnote per scoping §3.6.\"*")
        else:
            a("> *\"We validated reconstruction at the institution-year level; "
              "residuals are within reporting noise. The W5 Environmental→"
              "Geosciences cell carries a known definitional-drift footnote per "
              "scoping §3.6.\"*")
    else:
        a("> *\"Reopen — the simple Q9 + Q11 all-source rule does not "
          "reconstruct era-A field-level totals within the locked residual "
          "band on a non-pre-documented bucket or cell. Surface to panel for "
          "widen-rule (case (b) ARRA add, additional component) vs. "
          "absorb-into-band (descriptive band widening) call. HD 2.1.b "
          "halts at this report; HD 2.1.c–.i remain locked behind the "
          "reopen disposition.\"*")
    a("")

    a("## Reproducibility")
    a("")
    a("Script: `etl/spikes/residual_2008_2011.py`. Loaders: `etl/_load.py "
      "read_herd_csv(year)` for 2008 / 2009 / 2010 / 2011. Question filter: "
      "era A `'Expenditures by S&E field'`, column='Total'; era B "
      "`'Federal expenditures by field and agency'` + `'Nonfederal "
      "expenditures by field and source'`, column='Total'. Bucket filter: "
      "coarse-rollup labels only (e.g., `Engineering, all`) — leaves are not "
      "double-counted into rollups. Math & CS sums two rollups. Population "
      "filter: institutions present (row='All' total > 0) in all four years "
      "2008–2011. Substitutions documented above.")
    a("")

    OUTPUT_PATH.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
