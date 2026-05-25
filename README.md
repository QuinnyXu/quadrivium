# quadrivium

Open-source harmonization of U.S. higher-education survey data into reproducible analytical panels.

The current scope is NSF HERD (Higher Education Research and Development survey), FY 1972–2024. The roadmap covers IPEDS, NSF GSS, and other NCSES surveys.

## What makes this different

Higher-education survey data has methodological discontinuities — era boundaries in survey instruments, encoding shifts, taxonomy redesigns, infrastructure changes. Most published analyses treat the data as if those discontinuities don't exist, or skip the eras where they do.

Quadrivium applies **Reconstructive Harmonization**:

> (a) reconstruct what each era can support on its own terms (rules, crosswalks, validated reconstructions);
>
> (b) decompose what crossing a discontinuity actually involves into named, quantified components (real growth, definitional change, population expansion, residual unmeasurables);
>
> (c) publish both the reconstruction and the decomposition with sufficient documentation that a cold reader can use either without misreading the discontinuity.

This is not a bridge across discontinuities. It is the discipline of making operational data legible across them by being precise about what is reconstructible, what is decomposable, and what remains unmeasurable. See [`docs/methods_notes/reconstructive_harmonization.md`](docs/methods_notes/reconstructive_harmonization.md) for the methodological account applied to the 2010 HERD era boundary.

## Canonical artifacts

- **`data/harmonized/herd_panel.parquet`** — 50-year field-level R&D expenditure panel (FY 1975–2024), two parallel reconstructed series across the 2010 era boundary.
- **`data/harmonized/herd_panel_attributes.parquet`** — institution-year Q4/Q5 attribute sibling: medical-school and clinical-trials share and value columns.
- **`data/harmonized/herd_personnel.parquet`** — Q15 headcount + Q16 FTE personnel panel for FY 2022–2024 (the microdata-bearing years; NCSES Data Table 26 publishes institution totals for FY 2020–2024, but FY 2020–2021 are aggregate-only, with no per-institution microdata). Carries no `quality_flag` column — a documented imputation-provenance asymmetry with the financial panel (see [`docs/methods_notes/herd_panel_etl_scoping.md`](docs/methods_notes/herd_panel_etl_scoping.md) §12).

Companion validation reports in `validation/reports/` carry the reconciliation against published NSF / NCSES ground truth.

## Quick start

```bash
git clone <repo-url> quadrivium
cd quadrivium
uv sync
uv run python etl/build_herd_panel.py        # rebuild financial + attribute parquets
uv run python etl/build_herd_personnel.py    # rebuild personnel parquet
```

Requirements: Python 3.12 and `uv` (installed locally; this repo pins `uv` 0.11.8 in the lockfile and runtime deps to `duckdb==1.5.2` + `pypdf==6.10.2`).

Raw NSF HERD zips are not redistributed via git. SHA-256 manifests in [`data/raw/MANIFEST.md`](data/raw/MANIFEST.md) document the exact files that reproduce the harmonized outputs; download from NSF's HERD survey archive (URLs listed in the MANIFEST).

## Reproducibility contract

A cold reader with the lockfile, the raw zips named in `data/raw/MANIFEST.md`, and the NCSES reference PDFs in `data/reference/` reaches the same harmonized parquet bit-equivalently (modulo parquet writer determinism on a fixed input-and-code-version pair).

Methods-note figures are not deposit runtime. To rebuild figures:

```bash
uv sync --group charts
uv run --group charts python etl/spikes/era_2010_decomposition_chart.py
uv run --group charts python etl/spikes/herd_question_count_cliff_chart.py
```

## Methods note

The HERD methods note lives at [`docs/methods_notes/reconstructive_harmonization.md`](docs/methods_notes/reconstructive_harmonization.md). The deposit's personnel sibling README is at [`docs/methods_notes/herd_personnel_README.md`](docs/methods_notes/herd_personnel_README.md). The HERD per-year profile is at [`docs/methods_notes/herd_profile.md`](docs/methods_notes/herd_profile.md).

The full HD 2.1 / HD 2.4 implementation contract — schema, era handling, codeset policy, validation gates — is in [`docs/methods_notes/herd_panel_etl_scoping.md`](docs/methods_notes/herd_panel_etl_scoping.md) and [`docs/hd_2_1_scoping.md`](docs/hd_2_1_scoping.md).

## Repository layout

```
quadrivium/
├── CLAUDE.md                    project doctrine, locked decisions
├── README.md                    you are here
├── LICENSE                      MIT (code)
├── LICENSE-DATA.md              CC-BY-4.0 (data)
├── crosswalks/                  discipline + question-mapping CSVs (decision_rationale tracked)
├── data/
│   ├── raw/                     raw NSF zips (gitignored payload); MANIFEST.md is the SHA-256 anchor
│   ├── harmonized/              canonical parquets
│   └── reference/               NCSES reference PDFs; MANIFEST.md is the staging anchor
├── docs/                        methods notes, scoping, source documents
├── etl/                         loaders, builders, spikes
└── validation/                  reconciliation reports, per-year profiling
```

## Roadmap

Quadrivium is at **Stage 1** of a three-stage trajectory:

- **Stage 1 (current) — open datasets.** HERD harmonization (current). Future migrations: IPEDS, NSF GSS, other NCSES surveys. Each migration applies the Reconstructive Harmonization methodology to that survey's discontinuities; the schema and validation patterns adapt to the survey's structure, the methodology does not.
- **Stage 2 (planned) — platform.** Interactive query and comparative-panel surface on top of the harmonized data.
- **Stage 3 (planned) — commercial analytics.** Analytics built on the platform.

Stages 2 and 3 are not built now; they are the durable framing of where the project goes. Stage-1 work does not assume Stage-2 readiness.

## License

- **Code:** MIT — see [`LICENSE`](LICENSE).
- **Data:** CC-BY-4.0 — see [`LICENSE-DATA.md`](LICENSE-DATA.md).

## Citation

If you use quadrivium's harmonized panels in research, please cite the deposit DOI (Zenodo deposit pending) and the methods note. A formal citation block will land with the first Zenodo release.

## Contributing

External contribution flow is currently issue-based. To propose a crosswalk amendment or methodology extension, open a GitHub issue with: the proposed change, the empirical anchor (which raw HERD year and file, or which published NSF document), and the `decision_rationale` you would add to the crosswalk row. A `CONTRIBUTING.md` will land at Stage 2 when external contribution becomes a routine flow.
