# `data/reference/` Manifest

Generated: 2026-05-20 (Skipper, HD 2.4.g entry sub-action, item 5).
Per maintainer disposition 2026-05-20 (Option (b)): `data/reference/`
queried-from-authoritative-public-sources material gets its own
audit anchor parallel to `data/raw/MANIFEST.md` (collected raw data).
Supports future reference-data expansion at HD 2.4.g full run and beyond.

## What is here, what is not

`data/reference/` is tracked in git (small public-source PDFs and CSV
snapshots). This MANIFEST is the audit trail. The mirror discipline of
`data/raw/MANIFEST.md` applies — filename, SHA-256, byte size, source
citation, brief description.

## Staged files — root `data/reference/`

Static-PDF anchors per `docs/methods_notes/herd_panel_etl_scoping.md`
§2(d.1). Provenance and access dates live in
`docs/source_documents/citations.md`.

| SHA-256 | Bytes | File | Description |
|---------|-------|------|-------------|
| `19dc6c61844f08994befa2acb5f3a1f14793f5db6fb6f23fa810c921909d4c8e` | 9,192,189 | `nsf26304.pdf` | NSF NCSES 26-304 full HERD FY 2024 DST report |
| `2feb1d03efbe9763fa823cc59bae647e3476fdd61eca359702fd75c3bc0dc5ec` | 71,805 | `nsf26304-tab010.pdf` | Table 10 — R&D expenditures by R&D field and source of funds: FY 2024 |
| `f0158f94dfe3f0598e6d173e1c20b9cc0624fdd7ccb97aa50c310f860fa65987` | 73,579 | `nsf26304-tab011.pdf` | Table 11 — Federally financed R&D expenditures by federal agency and R&D field: FY 2024 |
| `85b5a083628fb6142d1a5a68c99c19aecd11b2da612bb9eb596200e0f5bd91f3` | 705,942 | `nsf26304-tab015.pdf` | Table 15 — R&D expenditures ranked by all R&D, by R&D field: FY 2024 |
| `5c71f38129021f85ad17d0adc94df8fecf0cc5f273ab011cd1de1e5b76d0727d` | 64,191 | `nsf26304-tab026.pdf` | Table 26 — Headcount and FTEs of R&D personnel (personnel sibling anchor) FYs 2020–24 |
| `4e54ce316784df6926d8d148e92f3bbc7fe1b56520a10bf54623c364cb1440f5` | 58,716 | `nsf26304-taba-003.pdf` | Table A-3 — Population counts by degree level FYs 2019–24 (personnel sibling completeness cross-check) |
| `ca69f36496cf859e836f3c6d74865948186f866f5a26f2a62b54e258e766e347` | 100,767 | `nsf26304-taba-023.pdf` | Table A-23 — HERD Survey data table crosswalk FY 2023 vs. FY 2024 |

## Staged files — `data/reference/dst-table-builder/`

Table Builder CSV snapshots + per-spot-year YAML query sidecars per
`docs/methods_notes/herd_panel_etl_scoping.md` §2(d.2). The CSV snapshot
is the canonical reproducibility anchor; the YAML sidecar captures the
exact Table Builder query parameters at staging time so the live tool
can be re-queried and reconciled against the snapshot while the NSF
tool persists.

### Precondition exports (reproducibility-gate artifacts)

Staged 2026-05-19 / 2026-05-20 by maintainer as the Table Builder
export-reproducibility gate (HD 2.4.a Round 2 verification). Both
exports issued with identical query parameters (JHU 029977 ×
Engineering + Life sciences + Physical sciences × federal/nonfederal
× FY 2024); byte-identical output confirms the live Table Builder
returns deterministic CSVs against fixed query parameters. The
precondition exports are the **pattern-of-staging reference**, not
grid-cell data — they cover one institution of the §2(b) Branch A
10-institution cohort.

| SHA-256 | Bytes | File | Description |
|---------|-------|------|-------------|
| `4153dd0ab2f57f1dd748e1b36414f601bd6c18c7c3e79637f243a5f7f6ee7998` | 8,540 | `dst-table-builder/precondition_export_1.csv` | JHU 029977 / 3-discipline / 2-source / FY 2024 — Round 2 export 1 of 2 (gate artifact) |
| `4153dd0ab2f57f1dd748e1b36414f601bd6c18c7c3e79637f243a5f7f6ee7998` | 8,540 | `dst-table-builder/precondition_export_2.csv` | JHU 029977 / 3-discipline / 2-source / FY 2024 — Round 2 export 2 of 2 (gate artifact, byte-identical to export 1) |
| `eaf6b0b46072e9063b14ad9f88d80e41c6bea78d47d1192f62d2d1b647f3992a` | 600 | `dst-table-builder/precondition_metadata.txt` | Query parameters and access timestamps for the precondition exports |

### Spot-year Table Builder CSV snapshots

Per HD 2.4.g entry sub-action: the FY 2024 grid anchor materialized
2026-05-21 (maintainer drove the Table Builder UI; Skipper staged the
sidecar and audit trail). Historical vintages (FY 2008 / FY 2010 /
FY 2017) remain blocked on the regime-stability finding (see
PANEL_SKIPPER §8 entries 2026-05-20 and 2026-05-21).

**Materialized 2026-05-21:**

| SHA-256 | Bytes | File | Description |
|---------|-------|------|-------------|
| `e0fc1f7b08f32f8963463ba591e18a188fbfc9d9f4584f2ffc50778ef46738a6` | 3,472 | `dst-table-builder/dst-table-builder-FY2024.csv` | NSF NCSES Table Builder export — FY 2024 institution × discipline × source-class anchor (HD 2.1.b 10-institution cohort × 3 disciplines × 2 source classes; 60 cells nominal, 58 substantive — UCSF Engineering structurally absent, health-sciences-only institution); paired query-parameter sidecar at `data/reference/dst-table-builder-FY2024-query.yaml` (filename aligned to scoping doc §2(d.2):190 convention `dst-table-builder-FY{year}-query.yaml` via `git mv` 2026-05-21, re-shape pass step 2) |

**Reserved (blocked on Vision Branch I/II/III scope-shape resolution per PANEL_SKIPPER §8 2026-05-20 Finding 2):**

| Forthcoming path | Description | Status |
|---|---|---|
| `dst-table-builder-FY2017.csv` (if Table Builder path applies) | FY 2017 grid anchor — pending item-2 substrate disposition | Blocked on item-2 regime-stability finding (see PANEL_SKIPPER §8 entry 2026-05-20) |
| `dst-table-builder-FY2010.csv` (if Table Builder path applies) | FY 2010 grid anchor — pending item-2 substrate disposition | Blocked on item-2 regime-stability finding |
| `dst-table-builder-FY2008.csv` (if Table Builder path applies) | FY 2008 grid anchor — pending item-2 substrate disposition | Blocked on item-2 regime-stability finding |

## Regeneration

To recompute the checksum list (Windows PowerShell):

```powershell
Get-ChildItem data/reference/ -File | ForEach-Object {
  $h = (Get-FileHash -Algorithm SHA256 $_.FullName).Hash.ToLower()
  "{0}  {1}  {2}" -f $h, $_.Length, $_.Name
}
Get-ChildItem data/reference/dst-table-builder/ -File | ForEach-Object {
  $h = (Get-FileHash -Algorithm SHA256 $_.FullName).Hash.ToLower()
  "{0}  {1}  {2}" -f $h, $_.Length, $_.Name
}
```

POSIX:

```bash
cd data/reference && sha256sum -- *
cd data/reference/dst-table-builder && sha256sum -- *
```

If a recomputed hash diverges from this manifest, the staged file has
drifted from the source-of-truth — re-fetch from the canonical URL in
`docs/source_documents/citations.md` and verify before continuing.
