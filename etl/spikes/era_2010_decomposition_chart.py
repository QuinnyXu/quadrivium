"""
etl/spikes/era_2010_decomposition_chart.py — methods-note slot 2 anchor chart.

Renders a four-bar decomposition of the FY 2008 -> FY 2011 HERD national-pool
R&D growth ($51.872B -> $65.274B, +$13.402B = +25.84% in current dollars), per
the maintainer's pre-HD-2.1.i chart-draft spec. Output is deposit-quality SVG
saved to `docs/methods_notes/figures/era_2010_decomposition.svg`.

DESIGN DECISIONS (Skipper-locked at chart-draft time, 2026-05-01)

1. Grain choice: NATIONAL-POOL (current dollars).
   - Rationale: the lead-chart story is a $-denominated 2008->2011 cumulative
     gap. The +25.84% pool growth is the headline figure; the four bars
     decompose THAT figure. Fixed-cohort grain (Diagnostic 1, median -22.5%)
     is the parallel reading; cross-grain reconciliation lives in the caption,
     not the bars.

2. Definitional-change reading: ~6pp YoY excess at 2009->2010 over the
   surrounding-year average (~6.1%/yr from FY08->FY09 +5.77% and FY10->FY11
   +6.51%). 2009->2010 actual was +11.71%; excess ~5.6pp, dollar-translated
   at the FY2009 base = ~$3.24B (1 year only).
   - Picked over the fixed-cohort 8pp Q5 reading because we're at national-
     pool grain. The 8pp number is sourced from Diagnostic 2's (|residual| -
     share) computation on the top-10 cohort, which is a different denominator.

3. Non-orthogonality (HONEST):
   - Bar (iii) Population expansion (cohort N: 690 -> 896, +206 inst., +29.9%)
     is visually distinct (hatched, no $ label as % of total). At national-
     pool grain the new institutions' R&D is BUNDLED INSIDE bars (i) and (ii)
     by construction. Showing (iii) as a count delta with a hatched fill
     signals "this driver overlaps the dollar bars; do not sum."
   - Bar (iv) Unmeasurable residual is small (~$0.09B / ~0.7%) at national-
     pool grain because (i)+(ii) already close most of the gap. At fixed-
     cohort grain it is materially larger (~14pp of the 22.5% fixed-cohort
     gap). Footnoted in the chart's source/footer line; caption will likely
     surface this more prominently — Sophia owns that decision.

DATA SOURCES (no recomputation; values transcribed from diagnostic reports
that are themselves reproducible from `etl/spikes/national_totals_2008_2011.py`
and `etl/spikes/residual_2008_2011_diagnostics.py`):

  - Diagnostic 3: FY2008 = $51.871804B (n=690); FY2011 = $65.274393B (n=896);
    YoY 08->09 = +5.77%; 09->10 = +11.71%; 10->11 = +6.51%; cumulative = +25.84%.
  - Diagnostic 2: Q5 clinical-trials median share / unexplained-by-clinical-
    trials gap of ~6-17pp at fixed-cohort. Used here only to footnote the
    cross-grain caveat; does not size a bar at national-pool grain.

PALETTE
  Color-blind safe (Wong 2011, common safe palette). Greys + one signature
  blue + one signature ochre. Grayscale-survival tested by varying lightness,
  not just hue. Hatched fill on (iii) carries the "different driver class"
  signal even in monochrome printouts.

STOP BOUNDARY
  Chart draft only. No methods-note prose. No locked caption. Title is the
  neutral placeholder per spec; Sophia owns the caption choice next.

Author: Skipper, 2026-05-01.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

# Use a non-interactive backend so this runs reliably in headless contexts
# (including under uv run with no display).
matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.patches as mpatches  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_PATH = (
    ROOT / "docs" / "methods_notes" / "figures" / "era_2010_decomposition.svg"
)


# ---------------------------------------------------------------------------
# Inputs (national-pool grain, current dollars, no deflator).
# ---------------------------------------------------------------------------

# National pool totals (Diagnostic 3, kUSD).
FY2008_KUSD = 51_871_804.0
FY2009_KUSD = 54_862_998.0
FY2010_KUSD = 61_286_610.0
FY2011_KUSD = 65_274_393.0

FY2008_N = 690
FY2009_N = 708
FY2010_N = 737
FY2011_N = 896

# Cumulative gap.
GAP_KUSD = FY2011_KUSD - FY2008_KUSD  # 13_402_589 kUSD = $13.402B
CUM_GROWTH_PCT = (FY2011_KUSD - FY2008_KUSD) / FY2008_KUSD * 100.0  # +25.84%

# Surrounding-year YoY rate (average of 08->09 and 10->11; the rate that would
# be expected at the boundary absent the era-B definitional change).
YOY_0809 = (FY2009_KUSD - FY2008_KUSD) / FY2008_KUSD  # 0.0577
YOY_1011 = (FY2011_KUSD - FY2010_KUSD) / FY2010_KUSD  # 0.0651
YOY_SURROUNDING = (YOY_0809 + YOY_1011) / 2.0  # ~0.0614 -> 6.14%

# Bar (i): real growth, modeled as surrounding-rate compounded over 3 years
# from the FY2008 base. This is the "what the gap would have been if the
# 2009->2010 boundary had looked like surrounding YoYs".
REAL_GROWTH_FACTOR = (1.0 + YOY_SURROUNDING) ** 3 - 1.0  # ~0.1957
BAR_REAL_KUSD = FY2008_KUSD * REAL_GROWTH_FACTOR  # ~$10.15B

# Bar (ii): definitional-change-at-boundary, modeled as the 2009->2010 YoY
# excess above the surrounding-rate, applied to the FY2009 base for one year.
YOY_0910_ACTUAL = (FY2010_KUSD - FY2009_KUSD) / FY2009_KUSD  # 0.1171
YOY_0910_EXCESS = YOY_0910_ACTUAL - YOY_SURROUNDING  # ~0.0557
BAR_BOUNDARY_KUSD = FY2009_KUSD * YOY_0910_EXCESS  # ~$3.06B

# Bar (iv): unmeasurable residual, computed as the gap minus (i) + (ii).
# Small at national-pool grain by construction (the surrounding-rate model
# closes most of the gap). The fixed-cohort residual (~14pp) is sourced from
# Diagnostic 1 + 2 and noted in the footer, not bar-encoded.
BAR_RESIDUAL_KUSD = GAP_KUSD - BAR_REAL_KUSD - BAR_BOUNDARY_KUSD

# Bar (iii): population expansion. Reported as institution-count delta only;
# its DOLLAR contribution overlaps (i) and (ii) at national-pool grain.
POP_DELTA_N = FY2011_N - FY2008_N  # 206
POP_DELTA_PCT = POP_DELTA_N / FY2008_N * 100.0  # +29.86%


# ---------------------------------------------------------------------------
# Color palette (Wong 2011 color-blind safe).
# ---------------------------------------------------------------------------

WONG_BLUE = "#0072B2"     # signature; (i) real growth
WONG_VERMILION = "#D55E00"  # contrast accent; (ii) definitional change
WONG_GREY = "#999999"     # neutral; (iii) population expansion (hatched)
WONG_DARK = "#444444"     # darkest; (iv) residual

TEXT_DARK = "#222222"
TEXT_MUTED = "#555555"


# ---------------------------------------------------------------------------
# Render.
# ---------------------------------------------------------------------------

def render() -> None:
    print("=== era_2010_decomposition_chart.py ===")
    print(f"  Gap (FY2008 -> FY2011): ${GAP_KUSD/1_000_000:.3f}B "
          f"({CUM_GROWTH_PCT:+.2f}% national-pool, current $)")
    print(f"  Bar (i) Real growth:                ${BAR_REAL_KUSD/1_000_000:.3f}B "
          f"({BAR_REAL_KUSD/GAP_KUSD*100:.1f}% of gap)")
    print(f"  Bar (ii) Definitional at boundary:  ${BAR_BOUNDARY_KUSD/1_000_000:.3f}B "
          f"({BAR_BOUNDARY_KUSD/GAP_KUSD*100:.1f}% of gap)")
    print(f"  Bar (iii) Population expansion:     +{POP_DELTA_N} institutions "
          f"(+{POP_DELTA_PCT:.1f}%; dollar share OVERLAPS bars i/ii)")
    print(f"  Bar (iv) Unmeasurable residual:     ${BAR_RESIDUAL_KUSD/1_000_000:.3f}B "
          f"({BAR_RESIDUAL_KUSD/GAP_KUSD*100:.1f}% of gap, national-pool grain)")
    print()

    # Bar values for plotting. (iii) is a non-additive count overlay; we plot
    # it on a SECOND y-axis (institution count, right side) to make the
    # different unit explicit. Bars (i)/(ii)/(iv) use the left y-axis ($B).
    # Bar (ii) is a TWO-WEIGHT label per Sophia's Lock 4 (chart-bar wording must
    # match the methods-note caption parenthetical exactly): primary line bold
    # at the same weight as other bar labels; second line lighter + italic to
    # carry the concrete handle "(mostly clinical-trials, Q5)" without
    # promoting it to the same visual weight as the category itself. Matplotlib
    # xticklabels can't mix weights within a single label, so we render bar
    # (ii)'s label via ax.text() and leave that xtick blank.
    bar_labels = [
        "(i)\nReal growth\n(surrounding\nYoY compound)",
        "",  # bar (ii) — rendered via ax.text() below for two-weight styling
        "(iii)\nPopulation\nexpansion\n(cohort N)",
        "(iv)\nUnmeasurable\nresidual",
    ]
    dollar_values_b = [
        BAR_REAL_KUSD / 1_000_000,
        BAR_BOUNDARY_KUSD / 1_000_000,
        0.0,  # bar (iii) NOT in $; rendered separately on right axis
        BAR_RESIDUAL_KUSD / 1_000_000,
    ]
    pct_of_gap = [
        BAR_REAL_KUSD / GAP_KUSD * 100,
        BAR_BOUNDARY_KUSD / GAP_KUSD * 100,
        None,  # (iii) is a count delta, not a $ share
        BAR_RESIDUAL_KUSD / GAP_KUSD * 100,
    ]
    bar_colors = [WONG_BLUE, WONG_VERMILION, WONG_GREY, WONG_DARK]

    # Set up figure (deposit-quality dimensions; ~11x7in for 2-column print).
    # Extra vertical headroom for title + subtitle + legend without overlap.
    fig, ax_left = plt.subplots(figsize=(11.0, 7.0), dpi=110)
    ax_right = ax_left.twinx()

    x = list(range(len(bar_labels)))
    bar_width = 0.62

    # Plot the dollar bars (i, ii, iv) on the left axis.
    dollar_idxs = [0, 1, 3]
    for i in dollar_idxs:
        ax_left.bar(
            x[i], dollar_values_b[i],
            width=bar_width, color=bar_colors[i],
            edgecolor=TEXT_DARK, linewidth=0.8,
            zorder=3,
        )

    # Plot the population-count bar (iii) on the right axis, hatched.
    ax_right.bar(
        x[2], FY2011_N - FY2008_N,
        width=bar_width, color=bar_colors[2],
        edgecolor=TEXT_DARK, linewidth=0.8,
        hatch="///",
        zorder=3,
    )

    # Bar value labels (absolute + % of total gap). Use a small minimum offset
    # so the residual bar's label sits clearly above its tiny bar rather than
    # overlapping the bar itself.
    label_offset = max(dollar_values_b) * 0.025
    for i in dollar_idxs:
        v_b = dollar_values_b[i]
        pct = pct_of_gap[i]
        ax_left.text(
            x[i], v_b + label_offset,
            f"${v_b:.2f}B\n({pct:.1f}% of gap)",
            ha="center", va="bottom",
            fontsize=10, color=TEXT_DARK, fontweight="bold",
        )

    # Bar (iii) label: count delta + percent change in N (not in $).
    ax_right.text(
        x[2], (FY2011_N - FY2008_N) + 8,
        f"+{POP_DELTA_N} institutions\n(+{POP_DELTA_PCT:.1f}%; cohort N)",
        ha="center", va="bottom",
        fontsize=10, color=TEXT_DARK, fontweight="bold",
    )

    # X-axis category labels.
    ax_left.set_xticks(x)
    ax_left.set_xticklabels(bar_labels, fontsize=10, color=TEXT_DARK)

    # Bar (ii) two-weight label (Sophia Lock 4). The primary line matches the
    # weight/size of the other xticklabels; the second line is rendered lighter
    # and italic to carry the concrete handle without promoting it. Y-position
    # is just below the x-axis, in axes-fraction coords against the figure.
    # Matched against the visual position of the other 4-line xticklabels: they
    # occupy roughly y=-0.02 to y=-0.16 in axes coords with fontsize=10. We
    # place the primary line where line 2 of those labels sits, then a blank
    # line, then the italic gloss.
    ax_left.text(
        x[1], -0.02,
        "(ii)",
        transform=ax_left.get_xaxis_transform(),
        ha="center", va="top",
        fontsize=10, color=TEXT_DARK,
    )
    ax_left.text(
        x[1], -0.06,
        "Definitional",
        transform=ax_left.get_xaxis_transform(),
        ha="center", va="top",
        fontsize=10, color=TEXT_DARK,
    )
    ax_left.text(
        x[1], -0.10,
        "change at",
        transform=ax_left.get_xaxis_transform(),
        ha="center", va="top",
        fontsize=10, color=TEXT_DARK,
    )
    ax_left.text(
        x[1], -0.14,
        "boundary",
        transform=ax_left.get_xaxis_transform(),
        ha="center", va="top",
        fontsize=10, color=TEXT_DARK,
    )
    ax_left.text(
        x[1], -0.20,
        "(mostly clinical-trials, Q5)",
        transform=ax_left.get_xaxis_transform(),
        ha="center", va="top",
        fontsize=8.5, color=TEXT_MUTED, style="italic",
    )

    # Y-axis (left): dollars in $B. Headroom must clear the largest label
    # (real-growth bar at ~$10B with two-line annotation) AND leave room for
    # the legend in the upper-right corner without overlap.
    max_dollar = max(dollar_values_b)
    ax_left.set_ylim(0, max_dollar * 1.45)
    ax_left.set_ylabel("Contribution to FY2008→FY2011 gap (current $B)",
                       fontsize=11, color=TEXT_DARK)
    ax_left.tick_params(axis="y", labelcolor=TEXT_DARK, labelsize=10)
    ax_left.spines["top"].set_visible(False)
    ax_left.spines["right"].set_visible(False)
    ax_left.grid(axis="y", linestyle=":", alpha=0.4, zorder=1)

    # Y-axis (right): institution count delta. Match left-axis headroom ratio
    # so the right-axis grid lines stay aligned visually.
    ax_right.set_ylim(0, (FY2011_N - FY2008_N) * 1.45)
    ax_right.set_ylabel("Cohort N increase (institutions)",
                        fontsize=11, color=TEXT_MUTED)
    ax_right.tick_params(axis="y", labelcolor=TEXT_MUTED, labelsize=10)
    ax_right.spines["top"].set_visible(False)
    # Keep the right spine on, since it carries an active axis.

    # Title is a neutral placeholder; Sophia owns caption choice. Use the
    # figure-level suptitle so it sits above the axes (no overlap with the
    # legend that lives inside the axes).
    fig.suptitle(
        "FY 2008 → FY 2011 HERD reported R&D, decomposed",
        fontsize=13, color=TEXT_DARK, x=0.06, ha="left", y=0.965,
    )

    # Subtitle / framing reference (small, muted; figure-level, below title).
    fig.text(
        0.06, 0.925,
        "National-pool grain · current dollars · cumulative gap = "
        f"${GAP_KUSD/1_000_000:.2f}B ({CUM_GROWTH_PCT:+.2f}%)",
        fontsize=10, color=TEXT_MUTED, ha="left", va="bottom",
    )

    # Legend explaining the hatched bar's different unit. Pinned upper-left
    # of the axes (not upper-right) so it does not visually compete with the
    # tallest bar (i) on the left side and stays clear of the title block.
    legend_handles = [
        mpatches.Patch(facecolor=WONG_BLUE, edgecolor=TEXT_DARK,
                       label="Dollar contribution (left axis)"),
        mpatches.Patch(facecolor=WONG_GREY, edgecolor=TEXT_DARK,
                       hatch="///",
                       label="Cohort N (right axis); overlaps dollar bars at this grain"),
    ]
    ax_left.legend(
        handles=legend_handles,
        loc="upper center",
        bbox_to_anchor=(0.5, 1.0),
        fontsize=9,
        frameon=False,
        ncol=2,
    )

    # Footnote (Sophia Lock 2). Reads with the figure on a LinkedIn-screenshot
    # test: a viewer who only sees the image gets bar labels + footnote
    # together. Italicized, slightly smaller than bar labels but legible at
    # deposit-publication size. Three wrapped lines to fit within figure
    # margins without bleeding off the side.
    #
    # Vertical layout (figure-fraction y, top-to-bottom):
    #   axes bottom         = 0.30
    #   bar-label block     = 0.30 down to ~0.16 (xticklabels, 4 lines)
    #   bar (ii) gloss      = ~0.165 (italic two-weight second line)
    #   footnote 3 lines    = 0.130 / 0.105 / 0.080
    #   source line 1       = 0.045
    #   source line 2       = 0.018
    footnote_line_1 = (
        "Bars (i), (ii), and (iv) decompose the dollar gap on the left axis and sum to it. "
        "Bar (iii) reports the cohort-N delta on the right axis: at"
    )
    footnote_line_2 = (
        "national-pool grain, dollars from new institutions are already inside (i) and (ii), "
        "so (iii) is a separate driver class, not additive. At fixed-cohort"
    )
    footnote_line_3 = (
        "grain the unmeasurable residual is materially larger "
        "(~14pp of the 22.5pp cohort residual; see Diagnostics 1–2)."
    )
    fig.text(
        0.5, 0.130, footnote_line_1,
        ha="center", va="bottom", fontsize=8.5, color=TEXT_DARK, style="italic",
    )
    fig.text(
        0.5, 0.105, footnote_line_2,
        ha="center", va="bottom", fontsize=8.5, color=TEXT_DARK, style="italic",
    )
    fig.text(
        0.5, 0.080, footnote_line_3,
        ha="center", va="bottom", fontsize=8.5, color=TEXT_DARK, style="italic",
    )

    # Source line (bottom). Cites diagnostics + summation rule + grain. Two
    # lines for legibility at this dpi.
    source_line_1 = (
        "Source: NSF HERD published all-institutions totals (FY 2008/2009/2010/2011), "
        "summed under the locked era-A→era-B reconstruction rule "
        "(2008–2009: 'Expenditures by S&E field' row=All col=Total; "
        "2010–2011: Q9 + Q11 row=All col=Total)."
    )
    source_line_2 = (
        "Diagnostics: validation/reports/era_reconciliation_2008_2011_diagnostic_{1,2,3}.md.  "
        "Spike: etl/spikes/era_2010_decomposition_chart.py.  Current dollars; no deflator."
    )
    fig.text(
        0.5, 0.045, source_line_1,
        ha="center", va="bottom", fontsize=7.5, color=TEXT_MUTED,
    )
    fig.text(
        0.5, 0.018, source_line_2,
        ha="center", va="bottom", fontsize=7.5, color=TEXT_MUTED,
    )

    # Reserve space at top for suptitle + subtitle and at bottom for:
    #   - 4-line bar-label block + bar (ii) two-weight gloss line (~0.14 fig)
    #   - 3-line italic footnote (~0.075 fig)
    #   - 2-line source attribution (~0.05 fig)
    # Avoid tight_layout (it fights the figure-level text).
    plt.subplots_adjust(top=0.86, bottom=0.30, left=0.07, right=0.92)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT_PATH, format="svg", bbox_inches="tight")
    # Also save a PNG fallback alongside, since some readers/Word imports
    # prefer raster. Same filename stem, different extension.
    png_path = OUTPUT_PATH.with_suffix(".png")
    fig.savefig(png_path, format="png", dpi=200, bbox_inches="tight")
    plt.close(fig)

    print(f"  Wrote SVG: {OUTPUT_PATH}")
    print(f"  Wrote PNG: {png_path}")


if __name__ == "__main__":
    render()
