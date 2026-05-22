# Source documents — citations and access dates

Source documents stashed locally for reproducibility. Each row carries its
canonical URL and access date. If you re-fetch, update the access date.

| Local path | Title | Source | URL | Access date |
|------------|-------|--------|-----|-------------|
| `data/raw/herd/Guide To Herd Data Files FY24.pdf` | Guide to HERD Data Files FY 2024 | NSF NCSES | bundled in NSF_HERD.zip | 2026-04-29 |
| `data/reference/nsf26304-tab026.pdf` | Table 26. Headcount and FTEs of R&D personnel at higher education institutions in the standard form survey population, by personnel function and sex: FYs 2020-24 | NSF NCSES (NSF 26-304) | https://ncses.nsf.gov/pubs/nsf26304/assets/data-tables/tables/nsf26304-tab026.pdf | 2026-04-29 |
| `data/reference/nsf26304-taba-003.pdf` | Table A-3. Population counts by degree level: FYs 2019-24 | NSF NCSES (NSF 26-304) | https://ncses.nsf.gov/pubs/nsf26304/assets/technical-tables/tables/nsf26304-taba-003.pdf | 2026-04-29 |
| `data/reference/nsf26304-taba-023.pdf` | Table A-23. HERD Survey data table crosswalk: FY 2023 vs. FY 2024 | NSF NCSES (NSF 26-304) | https://ncses.nsf.gov/pubs/nsf26304/assets/technical-tables/tables/nsf26304-taba-023.pdf | 2026-04-29 |
| `data/reference/nsf26304.pdf` | Higher Education Research and Development: Fiscal Year 2024 (full DST report) | NSF NCSES (NSF 26-304) | https://ncses.nsf.gov/pubs/nsf26304/assets/nsf26304.pdf | 2026-05-10 |
| `data/reference/nsf26304-tab010.pdf` | Table 10. R&D expenditures at higher education institutions, by R&D field and source of funds: FY 2024 | NSF NCSES (NSF 26-304) | https://ncses.nsf.gov/pubs/nsf26304/assets/data-tables/tables/nsf26304-tab010.pdf | 2026-05-10 |
| `data/reference/nsf26304-tab011.pdf` | Table 11. Federally financed R&D expenditures at higher education institutions, by federal agency and R&D field: FY 2024 | NSF NCSES (NSF 26-304) | https://ncses.nsf.gov/pubs/nsf26304/assets/data-tables/tables/nsf26304-tab011.pdf | 2026-05-10 |
| `data/reference/nsf26304-tab015.pdf` | Table 15. R&D expenditures at higher education institutions, ranked by all R&D, by R&D field: FY 2024 | NSF NCSES (NSF 26-304) | https://ncses.nsf.gov/pubs/nsf26304/assets/data-tables/tables/nsf26304-tab015.pdf | 2026-05-10 |

## Reconciliation anchors used in `validation/reports/herd_reconciliation_v1.md`

Table 26 (NSF 26-304) supplies the personnel sibling's HD 2.7 Cell 5
anchor: All personnel functions, Headcount, FY 2024 = **1,086,850**;
FTEs FY 2024 = 525,960. Constraint: standard form population only
(institutions with $1M+ FY23 R&D expenditures). Reconciliation query
must filter the personnel sibling to the same population.

The four financial cell anchors (PANEL_SKIPPER.md §4) come from FY 2023
NSF NCSES HERD published totals — those URLs to be added when HD 2.7
reconciliation v1 is authored.

## Table Builder reproducibility-gate exports (HD 2.4.a Round 2, staged 2026-05-19/20)

Per `docs/methods_notes/herd_panel_etl_scoping.md` §2(e), HD 2.4.a Round 2's
export-reproducibility gate confirms the NSF NCSES Table Builder returns
deterministic CSVs against fixed query parameters. The Round-2 verification
issued the same JHU 029977 × 3-discipline × 2-source × FY 2024 query twice
on 2026-05-10 (~12-minute interval); both exports are byte-identical (SHA-256
`4153dd0ab2f57f1dd748e1b36414f601bd6c18c7c3e79637f243a5f7f6ee7998`),
satisfying the §2(d.2) tier-(b) re-verification path's necessary condition
for the broader HD 2.4.g full-grid staging. The precondition exports are the
**pattern-of-staging reference**, not grid-cell data — JHU is one institution
of the §2(b) 10-institution cohort and the cohort × disciplines × source-
classes × spot-years grid (240 cells) remains to be staged at HD 2.4.g
full run.

| Local path | Title | Source | URL | Access date |
|------------|-------|--------|-----|-------------|
| `data/reference/dst-table-builder/precondition_export_1.csv` | Table Builder Round-2 reproducibility gate export 1 of 2 (JHU 029977 × 3-discipline × 2-source × FY 2024) | NSF NCSES Table Builder | https://ncsesdata.nsf.gov/builder/herd | 2026-05-10 |
| `data/reference/dst-table-builder/precondition_export_2.csv` | Table Builder Round-2 reproducibility gate export 2 of 2 (byte-identical to export 1; SHA-256 match confirms determinism) | NSF NCSES Table Builder | https://ncsesdata.nsf.gov/builder/herd | 2026-05-10 |
| `data/reference/dst-table-builder/precondition_metadata.txt` | Query parameters and access timestamps for the precondition export pair | Skipper (HD 2.4.a Round 2) | n/a | 2026-05-10 |

## Table Builder CSV snapshots (HD 2.4.g full run — FY 2024 materialized 2026-05-21; historical vintages reserved)

Per `docs/methods_notes/herd_panel_etl_scoping.md` §2(d.2), the FY 2024
DST Tables 28–54 surface (engineering subfield rankings, agency-specific
rankings) is Table-Builder-only — no static PDF. The deposit's
reproducibility contract anchors that surface against staged Table
Builder CSV snapshots, paired with `dst-table-builder-FY{year}.yaml`
sidecars capturing the exact query parameters used. The FY 2024 snapshot
+ sidecar materialized 2026-05-21 (maintainer-driven Table Builder UI
export + Skipper-staged audit trail); historical-vintage snapshots
(FY 2017 / FY 2010 / FY 2008) remain blocked on Vision Branch I/II/III
scope-shape resolution per PANEL_SKIPPER §8 entries 2026-05-20 and
2026-05-21.

**FY 2024 staged 2026-05-21:**

| Local path | Title | Source | URL | Access date |
|------------|-------|--------|-----|-------------|
| `data/reference/dst-table-builder/dst-table-builder-FY2024.csv` | NSF NCSES Table Builder export — FY 2024 institution × discipline × source-class anchor (HD 2.4 §2(d.2); HD 2.1.b 10-institution cohort × 3 disciplines × 2 source classes; 60 nominal / 58 substantive — UCSF Engineering structurally absent, health-sciences-only institution; SHA-256 `e0fc1f7b…6738a6`) | NSF NCSES Table Builder | https://ncsesdata.nsf.gov/builder/herd | 2026-05-21 |

The paired query-parameter YAML sidecar lives at
`data/reference/dst-table-builder-FY2024-query.yaml` (filename
aligned to scoping doc §2(d.2):190 convention
`dst-table-builder-FY{year}-query.yaml` via `git mv` 2026-05-21,
re-shape pass step 2 per maintainer disposition).

**Reserved (blocked on Vision Branch I/II/III scope-shape resolution per PANEL_SKIPPER §8 2026-05-20 Finding 2):**

| Local path | Title | Source | URL | Access date |
|------------|-------|--------|-----|-------------|
| `data/reference/dst-table-builder-FY2017.csv` | NSF NCSES Table Builder query — FY 2017 anchor | NSF NCSES Table Builder | _blocked on item-2 regime-stability resolution (see PANEL_SKIPPER §8 2026-05-20)_ | _to be recorded at HD 2.4.g_ |
| `data/reference/dst-table-builder-FY2010.csv` | NSF NCSES Table Builder query — FY 2010 anchor | NSF NCSES Table Builder | _blocked on item-2 regime-stability resolution_ | _to be recorded at HD 2.4.g_ |
| `data/reference/dst-table-builder-FY2008.csv` | NSF NCSES Table Builder query — FY 2008 anchor | NSF NCSES Table Builder | _blocked on item-2 regime-stability resolution_ | _to be recorded at HD 2.4.g_ |

The paired `data/reference/dst-table-builder-FY{year}-query.yaml`
sidecars materialize at HD 2.4.g run time per the template at
`data/reference/dst-table-builder-FY{YEAR}-query.yaml.template`
(scaffolded 2026-05-20 with the locked HD 2.1.b cohort and the
canonical query parameters pre-populated).

Tool-interface stability disclaimer: the Table Builder CSV snapshot is
the canonical anchor for the HD 2.4 verification grid. NSF may evolve
the Table Builder interface; if the live tool's behavior diverges from
the snapshot, the snapshot remains the deposit's reproducibility
contract. The paired query-parameter YAML sidecars capture the exact
query parameters at staging time so the live tool can be re-queried
and reconciled against the snapshot while the NSF tool persists.
