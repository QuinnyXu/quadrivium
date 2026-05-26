# `data/harmonized/` Manifest

Generated: 2026-05-25 (Skipper, Stage 2 deposit packaging; Decision A — pin harmonized-parquet SHA-256s for citation).

Parallel to `data/raw/MANIFEST.md` (collected raw data) and `data/reference/MANIFEST.md` (queried-from-public-sources material). This MANIFEST is the integrity anchor for the harmonized analytical panels the deposit ships.

## What is here, what is not

`data/harmonized/` is **tracked in git**; the three parquets are deposit artifacts. The harmonized parquets are **regenerable artifacts**: a cold reader with the lockfile (`uv.lock`), the raw zips named in `data/raw/MANIFEST.md`, and the reference PDFs in `data/reference/MANIFEST.md` regenerates them bit-equivalently (modulo parquet-writer determinism, which the build holds on a fixed input-and-code-version pair — `etl/build_herd_panel.py` imposes a deterministic `ORDER BY` before the parquet `COPY`).

The SHA-256s below are the **packaging anchor**: they pin the exact bytes the deposit ships, so a consumer who downloads a deposited parquet can verify its integrity, and a consumer who rebuilds can confirm the rebuild matches the deposit. This is the both/and the build's reproducibility contract (CLAUDE.md §3) and the deposit's citability require — **regenerable by the build, pinned for packaging.** The `etl/`-side treatment of the parquets as regenerable (input SHAs + lockfile + code reproduce them) is unchanged; this MANIFEST is a packaging layer on top, per the decision `docs/methods_notes/herd_panel_etl_scoping.md` §12 reserved for deposit-packaging time (Decision A, Stage 2).

## Staged files — `data/harmonized/`

| SHA-256 | Bytes | File | Description |
|---------|-------|------|-------------|
| `196132459f07725ed2d863d748dd637640a76e77245f87f8bb72d8dfad0c6fcc` | 6,088,076 | `herd_panel.parquet` | 50-year field-level R&D expenditure panel, FY 1975–2024; two parallel reconstructed series across the 2010 era boundary (era-A direct 1975–2009, era-B reconstructed 2010–2024 via the Q9+Q11 rule). Carries the `quality_flag` column. |
| `b3b937ebfe54d1c2a55e08144c2fed6eeea0693e360b143e6936718d81e4e101` | 108,811 | `herd_personnel.parquet` | Q15 headcount + Q16 FTE personnel panel, FY 2022–2024 (microdata-bearing years; FY 2020–2021 are aggregate-only in NCSES Data Table 26, no per-institution microdata). No `quality_flag` column — documented imputation-provenance asymmetry vs. the financial panel (README; scoping §12). |
| `216b8df8510fc03ce3d425e4395f2691dd723e1c384509675ebd5c276a6e6d81` | 151,158 | `herd_panel_attributes.parquet` | Institution-year Q4/Q5 attribute sibling: medical-school and clinical-trials share and value columns (era-B; era-A NULL). |

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
```

If a recomputed hash diverges from this manifest, either the build inputs or code changed (the raw zips, the crosswalks, `era_b_reconstruction_rule.yaml`, the build scripts, or the `uv.lock` runtime pins — regenerate this manifest and re-tag the release) **or** the deposited file drifted from the build (re-verify the inputs against `data/raw/MANIFEST.md` and rebuild). The committed SHA is the ground truth a rebuild must reproduce; do not edit this manifest to match a divergent rebuild without first diagnosing the divergence.
