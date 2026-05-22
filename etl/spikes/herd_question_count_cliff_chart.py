"""
etl/spikes/herd_question_count_cliff_chart.py — methods-note slot 1 anchor chart.

Renders the HERD question-count cliff: 1973-2024 line chart of distinct
questions per year in the field-level S&E expenditure section of the
survey, with the 2010 boundary visually emphasized as the moment NSF
fragmented era-A's single field-level question into era-B's source-class
questions.

Output:
  - docs/methods_notes/figures/herd_question_count_cliff.svg
  - docs/methods_notes/figures/herd_question_count_cliff.png  (200dpi raster fallback)

DESIGN DECISIONS (Skipper-locked at HD 2.1.i finalization, 2026-05-01)

1. Visual language matched to era_2010_decomposition_chart.py for deposit
   consistency: same Wong 2011 color-blind safe palette (signature blue +
   vermilion accent + neutral greys), same TEXT_DARK / TEXT_MUTED text
   scheme, same suptitle/subtitle/source-line block convention, same
   non-interactive Agg backend, same SVG-primary + PNG-fallback dual save.

2. The chart's job is to make the 2010 cliff visually unmistakable. A
   line chart on year x question-count y, with a vertical reference line
   at 2010 + a shaded band marking the era-B regime, makes the eye land
   on the discontinuity without needing the caption to say "look here".

3. Numbers come straight from docs/herd_question_structure_by_year.csv
   (HD 1.5 per-year question-structure profile). Verified at HD 2.1.i:
     - 2009: distinct_question_count = 7 (era_a_question_present = true,
       era_b_*_present = false; the era-A 7-question regime).
     - 2010: distinct_question_count = 19 (era_a_question_present = false,
       era_b_federal_present = true, era_b_nonfederal_present = true; the
       era-B 19-question redesign).
   The methods-note slot-1 sentence draft "jumped from 7 questions to 19"
   is consistent with the source data; no caption update needed.

4. 1972 carries distinct_question_count = 2 with era_a_question_present
   = true but no field-level question (the era-A field-level question
   `Expenditures by S&E field` first appears 1973). Per CLAUDE.md §6, 1972
   is preserved in the deposit but excluded from field-level analyses.
   The chart includes 1972 for completeness but visually deprioritizes it
   (no annotation; the line simply starts low and climbs to 1973's first
   field-level reading).

DATA SOURCE
  docs/herd_question_structure_by_year.csv (HD 1.5 profile).

PALETTE
  Wong 2011 color-blind safe (matches era_2010_decomposition_chart.py).

STOP BOUNDARY
  Chart only. No methods-note prose changes from this spike.

Author: Skipper, 2026-05-01 (HD 2.1.i finalization).
"""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib

# Non-interactive backend for headless / uv run reliability.
matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent
PROFILE_CSV = ROOT / "docs" / "herd_question_structure_by_year.csv"
OUTPUT_SVG = (
    ROOT / "docs" / "methods_notes" / "figures" / "herd_question_count_cliff.svg"
)
OUTPUT_PNG = OUTPUT_SVG.with_suffix(".png")


# ---------------------------------------------------------------------------
# Color palette (Wong 2011 color-blind safe; matches era_2010_decomposition).
# ---------------------------------------------------------------------------

WONG_BLUE = "#0072B2"        # signature; era-A line + era-B line
WONG_VERMILION = "#D55E00"   # era-2010 boundary marker
WONG_GREY = "#999999"
WONG_DARK = "#444444"

ERA_B_BAND = "#FFE8D6"       # very pale tint of vermilion for era-B band
ERA_A_BAND = "#E8F1F7"       # very pale tint of blue for era-A band

TEXT_DARK = "#222222"
TEXT_MUTED = "#555555"


# ---------------------------------------------------------------------------
# Load the HD 1.5 profile.
# ---------------------------------------------------------------------------

def load_profile() -> list[dict[str, object]]:
    """Read the per-year question-structure profile from CSV."""
    rows: list[dict[str, object]] = []
    with PROFILE_CSV.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(
                {
                    "year": int(r["year"]),
                    "distinct_question_count": int(r["distinct_question_count"]),
                    "era_a_question_present": r["era_a_question_present"] == "true",
                    "era_b_federal_present": r["era_b_federal_present"] == "true",
                    "era_b_nonfederal_present": r["era_b_nonfederal_present"] == "true",
                }
            )
    rows.sort(key=lambda x: x["year"])
    return rows


# ---------------------------------------------------------------------------
# Render.
# ---------------------------------------------------------------------------

def render() -> None:
    rows = load_profile()
    years = [r["year"] for r in rows]
    counts = [r["distinct_question_count"] for r in rows]

    # Verify the cliff numbers up front and announce them. If the data has
    # shifted from the methods-note draft (7 -> 19), this surfaces immediately.
    by_year = {r["year"]: r for r in rows}
    fy2009 = by_year[2009]
    fy2010 = by_year[2010]

    print("=== herd_question_count_cliff_chart.py ===")
    print(f"  Data source: {PROFILE_CSV.relative_to(ROOT)}")
    print(f"  Year range: {min(years)}-{max(years)} ({len(years)} years)")
    print(f"  FY 2009: distinct_question_count = {fy2009['distinct_question_count']}")
    print(
        f"           era_a_question_present = {fy2009['era_a_question_present']}, "
        f"era_b_federal_present = {fy2009['era_b_federal_present']}"
    )
    print(f"  FY 2010: distinct_question_count = {fy2010['distinct_question_count']}")
    print(
        f"           era_a_question_present = {fy2010['era_a_question_present']}, "
        f"era_b_federal_present = {fy2010['era_b_federal_present']}, "
        f"era_b_nonfederal_present = {fy2010['era_b_nonfederal_present']}"
    )
    print(
        f"  Cliff: {fy2009['distinct_question_count']} -> "
        f"{fy2010['distinct_question_count']} questions in a single year."
    )
    print()

    fig, ax = plt.subplots(figsize=(11.0, 6.5), dpi=110)

    # Era bands as background shading. Era A: 1972-2009 inclusive; Era B:
    # 2010-2024 inclusive. The shading lands first (zorder=1) so line and
    # markers sit on top.
    ax.axvspan(min(years) - 0.5, 2009.5, color=ERA_A_BAND, zorder=1)
    ax.axvspan(2009.5, max(years) + 0.5, color=ERA_B_BAND, zorder=1)

    # Split line into era-A and era-B segments so each picks up era color
    # without being misread as a single continuous series across the break.
    era_a_years = [y for y in years if y <= 2009]
    era_a_counts = [by_year[y]["distinct_question_count"] for y in era_a_years]
    era_b_years = [y for y in years if y >= 2010]
    era_b_counts = [by_year[y]["distinct_question_count"] for y in era_b_years]

    ax.plot(
        era_a_years, era_a_counts,
        color=WONG_BLUE, linewidth=2.0,
        marker="o", markersize=4.5, markerfacecolor=WONG_BLUE,
        markeredgecolor=TEXT_DARK, markeredgewidth=0.5,
        zorder=4, label="Era A (1972-2009): single field-level question",
    )
    ax.plot(
        era_b_years, era_b_counts,
        color=WONG_VERMILION, linewidth=2.0,
        marker="s", markersize=4.5, markerfacecolor=WONG_VERMILION,
        markeredgecolor=TEXT_DARK, markeredgewidth=0.5,
        zorder=4, label="Era B (2010-2024): fragmented into source-class questions",
    )

    # Vertical reference line at the era boundary.
    ax.axvline(
        x=2009.5, color=WONG_VERMILION, linestyle="--", linewidth=1.5,
        zorder=3, alpha=0.85,
    )

    # Boundary annotation pointing to the cliff edge. Placed up high and
    # left of 2010 so the arrow lands on the cliff edge without colliding
    # with the era-B point at 2010.
    ax.annotate(
        "2010 redesign:\nfield-level question\nfragmented into Q9 + Q11",
        xy=(2010, fy2010["distinct_question_count"]),
        xytext=(1996, 16.5),
        fontsize=10, color=TEXT_DARK,
        ha="center", va="center",
        arrowprops=dict(
            arrowstyle="->",
            color=WONG_VERMILION,
            lw=1.2,
            connectionstyle="arc3,rad=0.18",
        ),
        zorder=5,
    )

    # Highlight the 2009 and 2010 points with text labels giving the exact
    # counts so the cliff numbers are readable from the chart alone.
    ax.annotate(
        f"FY 2009: {fy2009['distinct_question_count']}",
        xy=(2009, fy2009["distinct_question_count"]),
        xytext=(2003.5, 3.5),
        fontsize=9.5, color=WONG_BLUE, fontweight="bold",
        ha="center", va="center",
        arrowprops=dict(
            arrowstyle="-",
            color=WONG_BLUE,
            lw=0.8,
            alpha=0.6,
        ),
        zorder=5,
    )
    ax.annotate(
        f"FY 2010: {fy2010['distinct_question_count']}",
        xy=(2010, fy2010["distinct_question_count"]),
        xytext=(2014.0, 11.5),
        fontsize=9.5, color=WONG_VERMILION, fontweight="bold",
        ha="center", va="center",
        arrowprops=dict(
            arrowstyle="-",
            color=WONG_VERMILION,
            lw=0.8,
            alpha=0.6,
        ),
        zorder=5,
    )

    # Axes setup.
    ax.set_xlabel("Fiscal year", fontsize=11, color=TEXT_DARK)
    ax.set_ylabel(
        "Distinct questions per year (HERD survey)",
        fontsize=11, color=TEXT_DARK,
    )
    ax.set_xlim(min(years) - 0.8, max(years) + 0.8)
    ax.set_ylim(0, max(counts) + 8)
    ax.tick_params(axis="both", labelcolor=TEXT_DARK, labelsize=10)

    # Era labels inside the bands, in the upper portion of the plot but
    # below the suptitle. Place them above the line but below the y-axis
    # ceiling, so they read as in-band headers without competing with the
    # data line or colliding with point annotations.
    ax.text(
        (min(years) + 2009) / 2, max(counts) + 6.5,
        "Era A (1972-2009)\nAcademic R&D Expenditures Survey",
        ha="center", va="top",
        fontsize=10, color=WONG_BLUE, fontweight="bold",
        zorder=2,
    )
    ax.text(
        (2010 + max(years)) / 2, max(counts) + 6.5,
        "Era B (2010-2024)\nHigher Ed R&D Survey",
        ha="center", va="top",
        fontsize=10, color=WONG_VERMILION, fontweight="bold",
        zorder=2,
    )

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", linestyle=":", alpha=0.4, zorder=1)

    # Title (figure-level for consistency with the decomposition chart).
    fig.suptitle(
        "The 2010 HERD question-count cliff",
        fontsize=13, color=TEXT_DARK, x=0.06, ha="left", y=0.965,
    )
    fig.text(
        0.06, 0.925,
        "NSF replaced the era-A single field-level question with era-B "
        "source-class questions in a single year, with no overlap.",
        fontsize=10, color=TEXT_MUTED, ha="left", va="bottom",
    )

    # Source line (matches era_2010_decomposition_chart.py footer convention).
    source_line = (
        "Source: docs/herd_question_structure_by_year.csv (HD 1.5 per-year "
        "profile, distinct_question_count column).  "
        "Spike: etl/spikes/herd_question_count_cliff_chart.py."
    )
    fig.text(
        0.5, 0.025, source_line,
        ha="center", va="bottom", fontsize=7.5, color=TEXT_MUTED,
    )

    plt.subplots_adjust(top=0.86, bottom=0.13, left=0.07, right=0.96)

    OUTPUT_SVG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT_SVG, format="svg", bbox_inches="tight")
    fig.savefig(OUTPUT_PNG, format="png", dpi=200, bbox_inches="tight")
    plt.close(fig)

    print(f"  Wrote SVG: {OUTPUT_SVG}")
    print(f"  Wrote PNG: {OUTPUT_PNG}")


if __name__ == "__main__":
    render()
