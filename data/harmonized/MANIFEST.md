# `data/harmonized/` Manifest

Generated: 2026-05-25 (Skipper, Stage 2 deposit packaging; Decision A — pin harmonized-parquet SHA-256s for citation).

Parallel to `data/raw/MANIFEST.md` (collected raw data) and `data/reference/MANIFEST.md` (queried-from-public-sources material). This MANIFEST is the integrity anchor for the harmonized analytical panels the deposit ships.

## What is here, what is not

`data/harmonized/` is **tracked in git**; the seven parquets are deposit artifacts. The harmonized parquets are **regenerable artifacts**: a cold reader with the lockfile (`uv.lock`), the raw zips named in `data/raw/MANIFEST.md`, and the reference PDFs in `data/reference/MANIFEST.md` regenerates them bit-equivalently (modulo parquet-writer determinism, which the build holds on a fixed input-and-code-version pair — `etl/build_herd_panel.py` imposes a deterministic `ORDER BY` before the parquet `COPY`).

The SHA-256s below are the **packaging anchor**: they pin the exact bytes the deposit ships, so a consumer who downloads a deposited parquet can verify its integrity, and a consumer who rebuilds can confirm the rebuild matches the deposit. This is the both/and the build's reproducibility contract (CLAUDE.md §3) and the deposit's citability require — **regenerable by the build, pinned for packaging.** The `etl/`-side treatment of the parquets as regenerable (input SHAs + lockfile + code reproduce them) is unchanged; this MANIFEST is a packaging layer on top, per the decision `docs/methods_notes/herd_panel_etl_scoping.md` §12 reserved for deposit-packaging time (Decision A, Stage 2).

## Staged files — `data/harmonized/`

| SHA-256 | Bytes | File | Description |
|---------|-------|------|-------------|
| `196132459f07725ed2d863d748dd637640a76e77245f87f8bb72d8dfad0c6fcc` | 6,088,076 | `herd_panel.parquet` | 50-year field-level R&D expenditure panel, FY 1975–2024; two parallel reconstructed series across the 2010 era boundary (era-A direct 1975–2009, era-B reconstructed 2010–2024 via the Q9+Q11 rule). Carries the `quality_flag` column. |
| `b3b937ebfe54d1c2a55e08144c2fed6eeea0693e360b143e6936718d81e4e101` | 108,811 | `herd_personnel.parquet` | Q15 headcount + Q16 FTE personnel panel, FY 2022–2024 (microdata-bearing years; FY 2020–2021 are aggregate-only in NCSES Data Table 26, no per-institution microdata). No `quality_flag` column — documented imputation-provenance asymmetry vs. the financial panel (README; scoping §12). |
| `216b8df8510fc03ce3d425e4395f2691dd723e1c384509675ebd5c276a6e6d81` | 151,158 | `herd_panel_attributes.parquet` | Institution-year Q4/Q5 attribute sibling: medical-school and clinical-trials share and value columns (era-B; era-A NULL). |
| `33511ffcbf791b931d793ab02a4ee2648b329c38b400f17edd46652220bd8e64` | 3,163,984 | `fedsupport_obligations.parquet` | Federal S&E Support full-series long panel, FY1971–FY2023 (v3.0 re-base): one row per dept × agency × broad/detailed activity × institution × type × state, with native IPEDS UnitID + status. All universes (higher-ed / nonprofit / FFRDC); filter via `institution_type`. Built by `etl/build_fedsupport_obligations.py`. |
| `5f6e0d215307bf3bb9ea51f0c70c3f3320a5379651c813309769fb12dea8b352` | 730,708 | `fedsupport_institution_year.parquet` | HERD-join-ready aggregate: higher-ed (academic+consortium), matched-UNITID, aggregated to (fiscal_year, ipeds_unitid) with R&D / S&E-support / total obligation columns. |
| `ce2b3527046ecd9a16dc2b014204cd680eb6a4006513573286294f14abaab6be` | 22,348,523 | `gss_race.parquet` | GSS enrollment/demographic face (dataset #3): long-format graduate students by enrollment-status × `degree_level` × gender × race, FY1972–2024, native-UNITID-keyed. Race taxonomy pre-bridged (legacy `*_98` → `*_legacy`, retained). Non-zero grain. Field names deferred. Built by `etl/build_gss_race.py` from `crosswalks/gss/race_column_map.csv`. §5 PASS vs Tables 4-3/1-2a; validation `validation/reports/gss/gss_race_validation.md`. |
| `de8acded3032ef1d31a7473597abae7fc32a8675074e4d0882bff81556f72010` | 22,570,917 | `gss_support.parquet` | GSS funding face (dataset #3 MVP): long-format full-time graduate students by support mechanism × federal agency × fed/nonfed, FY1972–2024, native-UNITID-keyed; `degree_level` (all_grad / masters / doctoral — post-2017 split). Non-zero grain (omitted cell = structural zero). Field names deferred (`gss_code` raw; `field_coarse`/`field_fine` NULL pending the NCSES field-code reference). Built by `etl/build_gss_support.py` from the crosswalk `crosswalks/gss/support_column_map.csv`. Validation: `validation/reports/gss/gss_support_validation.md`. |

## Regeneration

To recompute the checksum list (Windows PowerShell):

```powershell
Get-ChildItem data/harmonized/ -File -Filter *.parquet | ForEach-Object {
  $h = (Get-FileHash -Algorithm SHA256 $_.FullName).Hash.ToLower()
  "{0}  {1}  {2}" -f $h, $_.Length, $_.Name
}
```

POSIX:

```bash
cd data/harmonized && sha256sum -- *.parquet
```

To regenerate the parquets themselves from raw inputs:

```bash
uv sync
uv run python etl/build_herd_panel.py        # herd_panel.parquet + herd_panel_attributes.parquet
uv run python etl/build_herd_personnel.py    # herd_personnel.parquet
uv run python etl/acquire_gss.py             # GSS zips -> CSV (acquisition, gitignored)
uv run python etl/build_gss_support_column_map.py   # crosswalks/gss/support_column_map.csv
uv run python etl/build_gss_support.py       # gss_support.parquet
uv run python etl/build_gss_race_column_map.py      # crosswalks/gss/race_column_map.csv
uv run python etl/build_gss_race.py          # gss_race.parquet
```

If a recomputed hash diverges from this manifest, either the build inputs or code changed (the raw zips, the crosswalks, `era_b_reconstruction_rule.yaml`, the build scripts, or the `uv.lock` runtime pins — regenerate this manifest and re-tag the release) **or** the deposited file drifted from the build (re-verify the inputs against `data/raw/MANIFEST.md` and rebuild). The committed SHA is the ground truth a rebuild must reproduce; do not edit this manifest to match a divergent rebuild without first diagnosing the divergence.
