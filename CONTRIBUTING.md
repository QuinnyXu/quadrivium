# Contributing to quadrivium

quadrivium harmonizes U.S. higher-education survey data into reproducible analytical panels a cold reader can use without misreading the methodological discontinuities in the underlying data. Contributions that improve the harmonization — a crosswalk amendment, a methodology extension, a correction anchored in the source data — are welcome.

External contribution is currently **issue-based**. Direct pull-request mechanics arrive at the platform stage (the trajectory's Stage 2; see `CLAUDE.md` §1). For now, the issue is the path.

## How to propose a change

Open a [GitHub issue](https://github.com/QuinnyXu/quadrivium/issues) with three things:

1. **The proposed change** — what you would add, amend, or correct, and where (which crosswalk, which methods-note section, which build step).
2. **The empirical anchor** — which raw HERD year and file (e.g. `data/raw/herd/higher_education_r_and_d_2017.zip`), or which published NSF / NCSES document (with page or table number). A proposal without an anchor in the source data or a cited NCSES publication cannot be evaluated.
3. **The `decision_rationale`** — the one- or two-sentence rationale you would add to the affected crosswalk row. Every crosswalk row in this repo carries a `decision_rationale` column; treat each as a methods-note sentence (`CLAUDE.md` §6). Your proposal should read like one.

## What makes a mergeable proposal

- **Anchored in published ground truth.** The deposit validates every harmonized artifact against a published NSF/NCSES anchor (NSF HERD all-institution totals, NCSES Data Table 26, NSF Science & Engineering Indicators). A proposal that moves a number should name the anchor it reconciles against.
- **Guide-documented where it touches the codeset.** Extensions to the locked `quality_flag` / status codeset require either a Guide-documented semantic anchor or panel review (`CLAUDE.md` §4). Empirically surfacing an undocumented code is *not*, on its own, sufficient grounds — the default disposition is exclude-with-footnote pending review. If you propose a codeset change, cite the documentation.
- **Reproducible.** A change to the build must leave the cold-reader reproducibility contract intact (`CLAUDE.md` §3): the harmonized parquets rebuild bit-equivalently from the raw zips + lockfile, and their SHA-256s match `data/harmonized/MANIFEST.md`.
- **Methodology-respecting.** quadrivium's signature is Reconstructive Harmonization (`CLAUDE.md` §2; `docs/methods_notes/reconstructive_harmonization.md`): reconstruct each era on its own terms, decompose what crossing a discontinuity involves, publish both without bridging. A proposal that silently bridges a discontinuity — concatenating across an era boundary as if it were continuous — runs against the methodology.

## Where to look first

- **Methods note:** `docs/methods_notes/reconstructive_harmonization.md` — the worked methodology.
- **Crosswalks:** `crosswalks/` — every row carries `decision_rationale`; the discipline and question-mapping crosswalks are where most amendments land.
- **Locked decisions:** `CLAUDE.md` (project anchors) and `PANEL_SKIPPER.md` §8 (locked engineering decisions) — read these before proposing a change to a locked disposition; they record why the codebase is shaped the way it is.
- **Validation:** `validation/reports/` — every harmonized artifact ships with a reconciliation against a published anchor.

## License

By contributing, you agree your contributions are licensed under the repository's terms: code under MIT (`LICENSE`), data and documentation under CC-BY-4.0 (`LICENSE-DATA.md`).
