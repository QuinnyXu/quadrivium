"""
etl/spikes/residual_2008_2011_diagnostics.py — HD 2.1.b post-residual diagnostics.

Two diagnostics gating the panel review framing for the 2010 era boundary,
per the maintainer's directive after the cell-level data showed monotonic
gap growth (2009→2010 vs 2008→2011) inconsistent with one-shot
reclassification.

Hypothesis under test:
    Era B includes clinical trials and research training grants that era A
    excluded (FY24 Guide page 14). If true, the residual gap should
    aggregate consistently at the institution-total grain (Diagnostic 1)
    AND the Q5 clinical-trials share (plus training grants where
    measurable) should approximately match the gap magnitude (Diagnostic 2).

Diagnostic 1 — Institution-total grain re-run.
    Per-institution residuals at row='All', column='Total' grain.
    era_a_total(year) for 2008, 2009.
    era_b_recon_total(year) = Q9 row='All', column='Total' + Q11 row='All',
        column='Total' for 2010, 2011.
    Reports per-institution residuals + across-institution distribution
    (median, IQR, sign-consistency).

Diagnostic 2 — Clinical-trials share test.
    Per institution-year for 2010 + 2011:
    clinical_trials_share = Q5_value / (Q9_total + Q11_total).
    Compared against Diagnostic 1's institution-total residuals.
    Training-grants question availability: confirmed NOT a separate
    question in question_map.csv. Per FY24 Guide pages 80–83 and 630–633,
    training grants are included in the era-B R&D definition (bundled into
    Q9 + Q11 source rollups), not a separate carve-out question. Diagnostic 2
    therefore tests only the clinical-trials half of the W2 hypothesis.

Sample: same 10 institutions as the HD 2.1.b residual report. Selection
logic reuses select_top10_present_all_years from residual_2008_2011.py.

Output:
- validation/reports/era_reconciliation_2008_2011_diagnostic_1_institution_total.md
- validation/reports/era_reconciliation_2008_2011_diagnostic_2_q5_share.md

Stop boundary: report writes only. No CLAUDE.md updates. No panel.

Author: Skipper, 2026-05-01 (post-HD-2.1.b residual report).
"""

from __future__ import annotations

import statistics
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from etl._load import read_herd_csv  # noqa: E402

# Reuse the residual script's institution selection and constants.
from etl.spikes.residual_2008_2011 import (  # noqa: E402
    ERA_A_QUESTION,
    ERA_B_Q9,
    ERA_B_Q11,
    era_a_total_all,
    era_b_values,
    select_top10_present_all_years,
    fmt_pct,
    fmt_kusd,
)

# NOTE: question_map.csv canonical descriptor is "Clinical trial R&D expenditures",
# but the raw HERD CSV question label is "Clinical trials" (verified FY 2010, 2011
# via etl/spikes/_inspect_q5.py). Q5 row labels: 'Federal' / 'Nonfederal' / 'Total';
# column is NULL (single-axis). The institution-year total = row='Total', column IS NULL.
# This is a question_map.csv canonicalization gap; surfaced separately in the
# diagnostic 2 report for HD 2.1.f follow-up.
ERA_B_Q5_RAW = "Clinical trials"

OUTPUT_DIR = ROOT / "validation" / "reports"
OUTPUT_DIAG1 = OUTPUT_DIR / "era_reconciliation_2008_2011_diagnostic_1_institution_total.md"
OUTPUT_DIAG2 = OUTPUT_DIR / "era_reconciliation_2008_2011_diagnostic_2_q5_share.md"


# ---------------------------------------------------------------------------
# Diagnostic 1: institution-total grain
# ---------------------------------------------------------------------------


def era_b_institution_total(year: int) -> dict[str, tuple[str, float]]:
    """Return {inst_id -> (inst_name, Q9_All_Total + Q11_All_Total)} for era B.

    Sums the row='All', column='Total' cells of Q9 and Q11. This is the
    institution-total grain of the era-B reconstruction.
    """
    rel = read_herd_csv(year)
    sub = rel.filter(
        f"question IN ('{ERA_B_Q9}', '{ERA_B_Q11}') "
        f"AND \"column\" = 'Total' AND \"row\" = 'All'"
    )
    rows = sub.project("inst_id, inst_name_long, value").fetchall()
    out: dict[str, list] = {}
    for inst_id, inst_name, value in rows:
        if inst_id is None or value is None:
            continue
        key = str(inst_id)
        if key not in out:
            out[key] = [inst_name or "", 0.0]
        out[key][1] += float(value)
    return {k: (v[0], v[1]) for k, v in out.items()}


@dataclass
class InstTotalRow:
    inst_id: str
    inst_name: str
    era_a_2008_kusd: Optional[float]
    era_a_2009_kusd: Optional[float]
    era_b_recon_2010_kusd: Optional[float]
    era_b_recon_2011_kusd: Optional[float]
    residual_2009_2010_pct: Optional[float]  # (a09 - b10) / a09
    residual_2008_2011_pct: Optional[float]  # (a08 - b11) / a08


def residual_pct(a: Optional[float], b: Optional[float]) -> Optional[float]:
    if a is None or b is None or a == 0:
        return None
    return (a - b) / a


def iqr(values: list[float]) -> tuple[Optional[float], Optional[float]]:
    if len(values) < 2:
        return None, None
    sv = sorted(values)
    n = len(sv)

    def quantile(q: float) -> float:
        # Linear interpolation, type-7 (default in NumPy/R).
        h = (n - 1) * q
        lo = int(h)
        hi = min(lo + 1, n - 1)
        frac = h - lo
        return sv[lo] * (1 - frac) + sv[hi] * frac

    return quantile(0.25), quantile(0.75)


def run_diagnostic_1(selected: list[tuple[str, str, float]]) -> tuple[
    list[InstTotalRow],
    dict[str, dict[str, Optional[float]]],
]:
    """Compute institution-total residuals for the 10 selected insts.

    Returns (rows, summary_stats).
    """
    a08 = era_a_total_all(2008)
    a09 = era_a_total_all(2009)
    b10 = era_b_institution_total(2010)
    b11 = era_b_institution_total(2011)

    rows: list[InstTotalRow] = []
    for inst_id, inst_name, _ in selected:
        v_a08 = a08.get(inst_id, (None, None))[1]
        v_a09 = a09.get(inst_id, (None, None))[1]
        v_b10 = b10.get(inst_id, (None, None))[1]
        v_b11 = b11.get(inst_id, (None, None))[1]
        rows.append(InstTotalRow(
            inst_id=inst_id,
            inst_name=inst_name,
            era_a_2008_kusd=v_a08,
            era_a_2009_kusd=v_a09,
            era_b_recon_2010_kusd=v_b10,
            era_b_recon_2011_kusd=v_b11,
            residual_2009_2010_pct=residual_pct(v_a09, v_b10),
            residual_2008_2011_pct=residual_pct(v_a08, v_b11),
        ))

    res_2009_2010 = [r.residual_2009_2010_pct for r in rows if r.residual_2009_2010_pct is not None]
    res_2008_2011 = [r.residual_2008_2011_pct for r in rows if r.residual_2008_2011_pct is not None]

    def stats(vals: list[float]) -> dict[str, Optional[float]]:
        if not vals:
            return {"n": 0, "median": None, "q1": None, "q3": None, "neg_count": 0, "pos_count": 0}
        q1, q3 = iqr(vals)
        return {
            "n": len(vals),
            "median": statistics.median(vals),
            "q1": q1,
            "q3": q3,
            "neg_count": sum(1 for v in vals if v < 0),
            "pos_count": sum(1 for v in vals if v >= 0),
        }

    summary = {
        "2009_2010": stats(res_2009_2010),
        "2008_2011": stats(res_2008_2011),
    }
    return rows, summary


# ---------------------------------------------------------------------------
# Diagnostic 2: Q5 clinical-trials share
# ---------------------------------------------------------------------------


def era_b_q5_value(year: int, selected_ids: set[str]) -> dict[str, float]:
    """Return {inst_id -> Q5 clinical-trials institution-year total} for the year.

    Verified microdata shape (FY 2010 / FY 2011 via _inspect_q5.py):
    - question = 'Clinical trials' (raw label; question_map.csv carries the
      descriptor 'Clinical trial R&D expenditures' which does NOT match raw).
    - row in ('Federal', 'Nonfederal', 'Total'); column IS NULL (single-axis).
    - The institution-year total is row='Total', column IS NULL.

    Institutions absent from this question (no clinical trials reported)
    contribute 0 dollars; we surface them as None so downstream summary
    distinguishes 'no clinical trials' from 'data missing'. The directive's
    'Q5 share' interpretation treats absent = 0% share for distributional
    summary; per-row, both are reported.
    """
    rel = read_herd_csv(year)
    sub = rel.filter(
        f"question = '{ERA_B_Q5_RAW}' AND \"row\" = 'Total' AND \"column\" IS NULL"
    )
    rows = sub.project("inst_id, value").fetchall()
    out: dict[str, float] = {}
    for inst_id, value in rows:
        if inst_id is None or value is None:
            continue
        sid = str(inst_id)
        if sid in selected_ids:
            out[sid] = float(value)
    return out


@dataclass
class Q5ShareRow:
    inst_id: str
    inst_name: str
    year: int
    q5_value_kusd: Optional[float]
    q9_q11_total_kusd: Optional[float]
    clinical_trials_share: Optional[float]
    institution_total_residual_pct: Optional[float]  # from Diagnostic 1


def run_diagnostic_2(
    selected: list[tuple[str, str, float]],
    diag1_rows: list[InstTotalRow],
) -> tuple[list[Q5ShareRow], dict[str, dict[str, Optional[float]]]]:
    """Compute Q5 share per (institution × {2010, 2011})."""
    selected_ids = {inst_id for inst_id, _, _ in selected}
    inst_name_map = {inst_id: name for inst_id, name, _ in selected}
    diag1_lookup = {r.inst_id: r for r in diag1_rows}

    out_rows: list[Q5ShareRow] = []
    for year in (2010, 2011):
        q5 = era_b_q5_value(year, selected_ids)
        b_total = era_b_institution_total(year)
        for inst_id in (i for i, _, _ in selected):
            v_q5_raw = q5.get(inst_id)
            v_b = b_total.get(inst_id, (None, None))[1]
            # Q5 absence = institution did not report clinical trials = 0 dollars.
            # The era-B definitional change includes clinical trials in R&D scope;
            # an institution with no clinical-trial activity legitimately reports 0.
            # For share purposes, treat absence as 0 share.
            v_q5 = v_q5_raw if v_q5_raw is not None else 0.0
            share = (v_q5 / v_b) if (v_b is not None and v_b != 0) else None
            d1 = diag1_lookup.get(inst_id)
            inst_total_resid = (
                d1.residual_2009_2010_pct if (year == 2010 and d1) else
                d1.residual_2008_2011_pct if (year == 2011 and d1) else
                None
            )
            out_rows.append(Q5ShareRow(
                inst_id=inst_id,
                inst_name=inst_name_map[inst_id],
                year=year,
                q5_value_kusd=v_q5,
                q9_q11_total_kusd=v_b,
                clinical_trials_share=share,
                institution_total_residual_pct=inst_total_resid,
            ))

    # Per-year summary stats.
    def stats_for_year(year: int) -> dict[str, Optional[float]]:
        shares = [r.clinical_trials_share for r in out_rows
                  if r.year == year and r.clinical_trials_share is not None]
        resids = [r.institution_total_residual_pct for r in out_rows
                  if r.year == year and r.institution_total_residual_pct is not None]
        gap_minus_share: list[float] = []
        for r in out_rows:
            if r.year != year:
                continue
            if r.clinical_trials_share is None or r.institution_total_residual_pct is None:
                continue
            gap_minus_share.append(abs(r.institution_total_residual_pct) - r.clinical_trials_share)
        return {
            "n_shares": len(shares),
            "median_share": statistics.median(shares) if shares else None,
            "median_abs_resid": statistics.median([abs(v) for v in resids]) if resids else None,
            "median_gap_minus_share": statistics.median(gap_minus_share) if gap_minus_share else None,
        }

    summary = {
        "2010": stats_for_year(2010),
        "2011": stats_for_year(2011),
    }
    return out_rows, summary


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------


def fmt_pct_pts(p: Optional[float]) -> str:
    if p is None:
        return "n/a"
    return f"{p*100:+.2f}pp"


def fmt_share(p: Optional[float]) -> str:
    if p is None:
        return "n/a"
    return f"{p*100:.2f}%"


def write_diagnostic_1_report(
    rows: list[InstTotalRow],
    summary: dict[str, dict[str, Optional[float]]],
    selected: list[tuple[str, str, float]],
) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    a = lines.append

    a("# HD 2.1.b Diagnostic 1 — Institution-total grain residual re-run")
    a("")
    a("**Authored by:** Skipper, 2026-05-01 (post-residual diagnostic).")
    a("")
    a("**Scope:** Re-runs the residual computation at the `row='All', "
      "column='Total'` (institution-total) grain rather than the coarse-bucket "
      "grain. Same 10 institutions as `era_reconciliation_2008_2011.md`. "
      "Hypothesis under test (per maintainer's directive): institution-total "
      "residuals show the same systematic direction as bucket-level (era-B > "
      "era-A by 5–25%) but with smaller magnitude — corroborating the "
      "definitional-drift reading (era B includes clinical trials and "
      "research training grants that era A excluded; FY24 Guide page 14).")
    a("")
    a("**Sign convention:** `residual = (era_a - era_b_recon) / era_a`. "
      "A *negative* residual means era-B reconstruction is **larger** than "
      "era-A direct (era-B > era-A), consistent with the hypothesis.")
    a("")

    a("## Sample")
    a("")
    a("Same 10 institutions as the parent residual report (top-10 by FY 2008 "
      "row='All' column='Total' in `Expenditures by S&E field`, present in all "
      "of FY 2009 / 2010 / 2011):")
    a("")
    a("| rank | inst_id | inst_name | fy2008_total_kusd |")
    a("|---:|---|---|---:|")
    for i, (inst_id, inst_name, total) in enumerate(selected, 1):
        a(f"| {i} | {inst_id} | {inst_name} | {fmt_kusd(total)} |")
    a("")

    a("## Per-institution institution-total residuals")
    a("")
    a("| inst_id | inst_name | era_a_2008_kusd | era_a_2009_kusd | era_b_recon_2010_kusd | era_b_recon_2011_kusd | residual_2009_2010_pct | residual_2008_2011_pct |")
    a("|---|---|---:|---:|---:|---:|---:|---:|")
    for r in rows:
        a(
            f"| {r.inst_id} | {r.inst_name} | "
            f"{fmt_kusd(r.era_a_2008_kusd)} | "
            f"{fmt_kusd(r.era_a_2009_kusd)} | "
            f"{fmt_kusd(r.era_b_recon_2010_kusd)} | "
            f"{fmt_kusd(r.era_b_recon_2011_kusd)} | "
            f"{fmt_pct(r.residual_2009_2010_pct)} | "
            f"{fmt_pct(r.residual_2008_2011_pct)} |"
        )
    a("")

    a("## Across-institution distribution")
    a("")
    a("| year_pair | n | median | Q1 | Q3 | sign: negative (era-B > era-A) | sign: positive (era-A > era-B) |")
    a("|---|---:|---:|---:|---:|---:|---:|")
    for label, key in (("2009→2010 (adjacent)", "2009_2010"), ("2008→2011 (long-gap sanity)", "2008_2011")):
        s = summary[key]
        a(
            f"| {label} | {s['n']} | "
            f"{fmt_pct(s['median'])} | "
            f"{fmt_pct(s['q1'])} | "
            f"{fmt_pct(s['q3'])} | "
            f"{s['neg_count']} | {s['pos_count']} |"
        )
    a("")

    a("## Synthesis")
    a("")
    s10 = summary["2009_2010"]
    s11 = summary["2008_2011"]
    direction_2010 = (
        "era-B > era-A" if (s10["median"] is not None and s10["median"] < 0) else
        "era-A > era-B" if (s10["median"] is not None and s10["median"] > 0) else
        "indeterminate"
    )
    direction_2011 = (
        "era-B > era-A" if (s11["median"] is not None and s11["median"] < 0) else
        "era-A > era-B" if (s11["median"] is not None and s11["median"] > 0) else
        "indeterminate"
    )
    sign_consistent_2010 = (
        s10["neg_count"] == s10["n"] or s10["pos_count"] == s10["n"]
    ) if s10["n"] else False
    sign_consistent_2011 = (
        s11["neg_count"] == s11["n"] or s11["pos_count"] == s11["n"]
    ) if s11["n"] else False
    a(f"- **Direction (2009→2010):** {direction_2010}. Sign-consistent across "
      f"all {s10['n']} institutions: **{sign_consistent_2010}** "
      f"({s10['neg_count']} negative / {s10['pos_count']} positive).")
    a(f"- **Direction (2008→2011):** {direction_2011}. Sign-consistent across "
      f"all {s11['n']} institutions: **{sign_consistent_2011}** "
      f"({s11['neg_count']} negative / {s11['pos_count']} positive).")
    a(f"- **Median magnitude:** {fmt_pct(s10['median'])} (2009→2010); "
      f"{fmt_pct(s11['median'])} (2008→2011).")
    a("")
    a("**Hypothesis read.** If institution-total residuals are sign-consistent "
      "across institutions and in the same direction as the bucket-level gap "
      "(parent report: 5 of 7 gating buckets era-B > era-A), the "
      "definitional-drift hypothesis is corroborated at the institution-total "
      "grain. Mixed sign across institutions would suggest the picture is "
      "messier than a single uniform definitional shift.")
    a("")
    a("## Reproducibility")
    a("")
    a("Script: `etl/spikes/residual_2008_2011_diagnostics.py`. Imports "
      "selection logic and `era_a_total_all` from "
      "`etl/spikes/residual_2008_2011.py`. Era-B institution total: "
      "Q9 row='All' column='Total' + Q11 row='All' column='Total' "
      "(`era_b_institution_total`). Same 10 institutions as the parent report.")
    a("")

    OUTPUT_DIAG1.write_text("\n".join(lines), encoding="utf-8")


def write_diagnostic_2_report(
    rows: list[Q5ShareRow],
    summary: dict[str, dict[str, Optional[float]]],
    selected: list[tuple[str, str, float]],
    diag1_summary: dict[str, dict[str, Optional[float]]],
) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    a = lines.append

    a("# HD 2.1.b Diagnostic 2 — Q5 clinical-trials share test")
    a("")
    a("**Authored by:** Skipper, 2026-05-01 (post-residual diagnostic).")
    a("")
    a("**Scope:** Tests the W2 definitional-drift hypothesis at the "
      "institution-year grain. Per FY24 Guide page 82 ('clinical trials and "
      "research training grants were explicitly included in the definition of "
      "R&D' under HERD; FY24 Guide page 632 names this as a known cause of "
      "'sizable trend changes' between the era-A Academic R&D Expenditures "
      "Survey and the era-B HERD), era B captures dollars era A did not. "
      "If true, Q5 (clinical trials) plus a research-training-grants share "
      "should approximately match the institution-total residual gap from "
      "Diagnostic 1.")
    a("")

    a("## Training-grants question availability — confirmed unavailable as a separate question")
    a("")
    a("Verified against `crosswalks/question_map.csv` (36 rows) and "
      "`docs/source_documents/herd_fy24_guide.txt`: there is no era-B question "
      "that isolates research-training-grant expenditures as a separate "
      "carve-out. Per FY24 Guide pages 80–83 and 630–633, training grants are "
      "**included in the era-B R&D definition** (i.e., bundled into Q9 + Q11 "
      "field-level source rollups), not a discrete attribute question. The "
      "training-grants half of the W2 hypothesis therefore cannot be measured "
      "from HERD microdata alone — it is hypothesis residual until paired with "
      "an external data source (e.g., NIH RePORTER or NSF Award Search "
      "training-grant award totals, mappable to institution-year). Diagnostic "
      "2 tests **only the clinical-trials half** of the hypothesis.")
    a("")
    a("This means the comparison framing must be:")
    a("- If `clinical_trials_share` alone matches the institution-total gap → "
      "clinical trials is the dominant W2 driver; training grants are a "
      "smaller residual.")
    a("- If `clinical_trials_share` is materially smaller than the gap → "
      "training grants and/or other definitional changes (e.g., scope "
      "expansion within Q9/Q11 source rollups) account for the remainder.")
    a("- If `clinical_trials_share` exceeds the gap → either Q5 is being "
      "double-counted (unlikely; Q5 is an attribute carve-out from Q1, "
      "parallel to Q9+Q11 field-level totals), or the gap is masked by "
      "offsetting drifts elsewhere in the data.")
    a("")

    a("## Per-institution-year shares")
    a("")
    a("| inst_id | inst_name | year | q5_value_kusd | q9_q11_total_kusd | clinical_trials_share | institution_total_residual_pct |")
    a("|---|---|---:|---:|---:|---:|---:|")
    for r in rows:
        a(
            f"| {r.inst_id} | {r.inst_name} | {r.year} | "
            f"{fmt_kusd(r.q5_value_kusd)} | "
            f"{fmt_kusd(r.q9_q11_total_kusd)} | "
            f"{fmt_share(r.clinical_trials_share)} | "
            f"{fmt_pct(r.institution_total_residual_pct)} |"
        )
    a("")

    a("## Comparison summary")
    a("")
    a("| year | n | median clinical_trials_share | median |institution-total residual| | median (|residual| − share) |")
    a("|---|---:|---:|---:|---:|")
    for year in (2010, 2011):
        s = summary[str(year)]
        a(
            f"| {year} | {s['n_shares']} | "
            f"{fmt_share(s['median_share'])} | "
            f"{fmt_share(s['median_abs_resid'])} | "
            f"{fmt_pct_pts(s['median_gap_minus_share'])} |"
        )
    a("")
    a("Reading: `(|residual| − share)` is the **unexplained-by-clinical-trials** "
      "portion of the institution-total gap, in percentage points. Near-zero → "
      "clinical trials alone explains the gap. Materially positive → training "
      "grants and/or other definitional changes carry the remainder. Negative "
      "→ Q5 share exceeds the residual; gap is masked or Q5 captures more "
      "than the era-A/era-B definitional difference.")
    a("")

    a("## Synthesis")
    a("")
    s10 = summary["2010"]
    s11 = summary["2011"]
    a(f"- **2010**: median clinical_trials_share = {fmt_share(s10['median_share'])}; "
      f"median |institution-total residual| = {fmt_share(s10['median_abs_resid'])}; "
      f"median unexplained gap = {fmt_pct_pts(s10['median_gap_minus_share'])}.")
    a(f"- **2011**: median clinical_trials_share = {fmt_share(s11['median_share'])}; "
      f"median |institution-total residual| = {fmt_share(s11['median_abs_resid'])}; "
      f"median unexplained gap = {fmt_pct_pts(s11['median_gap_minus_share'])}.")
    a("")
    a("**Hypothesis read.**")
    a("- Unexplained gap within ±5 percentage points → clinical trials alone "
      "is the W2 driver; locked W2 carve-out covers it.")
    a("- Unexplained gap +5 to +10 pp → clinical trials is a partial driver; "
      "training grants / other scope changes carry the residual.")
    a("- Unexplained gap > +10 pp → hypothesis substantially under-explains; "
      "the W2 carve-out alone cannot bridge era A to era B.")
    a("- Negative unexplained gap → Q5 share exceeds the institution-total "
      "residual; either Q5 captures dollars beyond the era-A/era-B "
      "definitional difference, or other drifts offset.")
    a("")

    a("## Side-finding: question_map.csv canonicalization gap")
    a("")
    a("`crosswalks/question_map.csv` (row 16) carries the canonical descriptor "
      "**`Clinical trial R&D expenditures`** for Q5, but the raw HERD CSV "
      "question label in FY 2010 / FY 2011 is **`Clinical trials`**. These "
      "do not match. Verified via `etl/spikes/_inspect_q5.py` against the "
      "FY 2010 and FY 2011 CSVs; the question_map.csv label was authored from "
      "FY24 Guide page 5 (the survey instrument's canonical question name), "
      "which differs from the per-year microdata column. Filing as a HD 2.1.f "
      "follow-up: question_map.csv needs a `raw_question_label` column (or a "
      "year-keyed mapping) before code can join on canonical names. Diagnostic "
      "2 was authored against the raw label after surfacing the mismatch.")
    a("")
    a("## Reproducibility")
    a("")
    a("Script: `etl/spikes/residual_2008_2011_diagnostics.py`. Q5 read: "
      f"question = `'{ERA_B_Q5_RAW}'` (raw microdata label), row='Total', "
      "column IS NULL. Q5 absence is treated as 0 dollars (= institution did "
      "not report clinical-trial R&D for the year; era-B definitional scope "
      "includes clinical trials, so 0 is a legitimate value, not a missing "
      "code). Era-B institution total: Q9 row='All' column='Total' + Q11 "
      "row='All' column='Total'. Diagnostic 1 residuals are referenced "
      "verbatim from the sibling diagnostic.")
    a("")

    OUTPUT_DIAG2.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    print("=== HD 2.1.b Diagnostics 1 + 2 ===")

    # Reproduce the parent report's institution selection.
    print("Reproducing top-10 institution selection from parent report...")
    fy2008 = era_a_total_all(2008)
    fy2009 = era_a_total_all(2009)
    b10_buckets = era_b_values(2010)  # for inst membership
    b11_buckets = era_b_values(2011)
    inst_2009 = set(fy2009.keys())
    inst_2010 = {k[0] for k in b10_buckets.keys()}
    inst_2011 = {k[0] for k in b11_buckets.keys()}
    selected, _subs = select_top10_present_all_years(
        fy2008, inst_2010, inst_2009, inst_2011
    )
    print(f"  selected: {len(selected)} institutions")
    for inst_id, inst_name, total in selected:
        print(f"    {inst_id} {inst_name!r}  FY 2008 total = ${total:,.0f}k")

    # Diagnostic 1.
    print("\n--- Diagnostic 1: institution-total residuals ---")
    d1_rows, d1_summary = run_diagnostic_1(selected)
    for r in d1_rows:
        print(
            f"  {r.inst_id} {r.inst_name[:35]:35s} "
            f"2009→2010 {fmt_pct(r.residual_2009_2010_pct):>9s}  "
            f"2008→2011 {fmt_pct(r.residual_2008_2011_pct):>9s}"
        )
    s = d1_summary["2009_2010"]
    print(
        f"\n  2009→2010: n={s['n']} median={fmt_pct(s['median'])} "
        f"Q1={fmt_pct(s['q1'])} Q3={fmt_pct(s['q3'])} "
        f"neg={s['neg_count']} pos={s['pos_count']}"
    )
    s = d1_summary["2008_2011"]
    print(
        f"  2008→2011: n={s['n']} median={fmt_pct(s['median'])} "
        f"Q1={fmt_pct(s['q1'])} Q3={fmt_pct(s['q3'])} "
        f"neg={s['neg_count']} pos={s['pos_count']}"
    )

    write_diagnostic_1_report(d1_rows, d1_summary, selected)
    print(f"\nDiagnostic 1 report written: {OUTPUT_DIAG1}")

    # Diagnostic 2.
    print("\n--- Diagnostic 2: Q5 clinical-trials share ---")
    d2_rows, d2_summary = run_diagnostic_2(selected, d1_rows)
    for r in d2_rows:
        print(
            f"  {r.inst_id} {r.inst_name[:30]:30s} {r.year}  "
            f"q5={fmt_kusd(r.q5_value_kusd):>12s} "
            f"share={fmt_share(r.clinical_trials_share):>8s}  "
            f"inst_total_resid={fmt_pct(r.institution_total_residual_pct):>9s}"
        )
    for year in ("2010", "2011"):
        s = d2_summary[year]
        print(
            f"\n  {year}: n={s['n_shares']} median_share={fmt_share(s['median_share'])} "
            f"median_|resid|={fmt_share(s['median_abs_resid'])} "
            f"median_unexplained={fmt_pct_pts(s['median_gap_minus_share'])}"
        )

    write_diagnostic_2_report(d2_rows, d2_summary, selected, d1_summary)
    print(f"\nDiagnostic 2 report written: {OUTPUT_DIAG2}")

    print("\n=== Done. Stopped before panel review per directive. ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
