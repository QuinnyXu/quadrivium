# Data License — Creative Commons Attribution 4.0 International (CC BY 4.0)

The harmonized data artifacts in this repository — including but not limited to the parquet files in `data/harmonized/`, the crosswalk CSVs in `crosswalks/`, the harvest files in `crosswalks/_harvest/`, the validation reports in `validation/reports/`, the per-year HERD profile in `validation/profile/`, and the methods-note figures in `docs/methods_notes/figures/` — are licensed under the Creative Commons Attribution 4.0 International License (CC BY 4.0).

The full license text is available at: https://creativecommons.org/licenses/by/4.0/legalcode

## Summary (not a substitute for the license)

You are free to:

- **Share** — copy and redistribute the data in any medium or format.
- **Adapt** — remix, transform, and build upon the data for any purpose, even commercially.

Under the following terms:

- **Attribution** — You must give appropriate credit, provide a link to this license, and indicate if changes were made. You may do so in any reasonable manner, but not in any way that suggests the licensor endorses you or your use.

## Attribution

When using quadrivium's harmonized data in research, presentations, dashboards, or derivative works, please cite:

> Quadrivium contributors. *Quadrivium: Reconstructive Harmonization of U.S. higher-education survey data.* Available at: https://github.com/QuinnyXu/quadrivium. License: CC BY 4.0.

Concept DOI (all versions): [10.5281/zenodo.20404785](https://doi.org/10.5281/zenodo.20404785) (Zenodo). See [`CITATION.cff`](CITATION.cff) for the machine-readable citation.

## Underlying source data

The harmonized panels in `data/harmonized/` are derived from NSF Higher Education Research and Development (HERD) survey data published by the National Center for Science and Engineering Statistics (NCSES). NSF / NCSES source data is U.S. government work and not subject to copyright. The harmonization, crosswalks, decomposition, and methods notes contributed by quadrivium are the licensed work covered by this CC BY 4.0 license.

The raw NSF / NCSES PDFs in `data/reference/` are U.S. government publications; their access dates and SHA-256 fingerprints are tracked in `data/reference/MANIFEST.md` for reproducibility, but their original publication terms (U.S. government work) govern their use.

## Note on code

The Python source code and the lockfile in this repository are licensed separately under the MIT License (see `LICENSE`). This data license applies to the harmonized data artifacts and the documentation that explains the harmonization; the code license applies to the executables that produce those artifacts.
