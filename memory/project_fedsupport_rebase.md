---
name: project_fedsupport_rebase
description: FedSupport dataset-#2 re-base onto the full 1971–2023 NCSES Build Table export — scoped, awaiting maintainer authorization for the Phase 3 build.
metadata:
  type: project
---

The Federal S&E Support module (dataset #2, currently the FY2020–2023 Table 12 slice) is being re-based onto the authoritative full-series NCSES Build Table export: `data/raw/fedsupport/ncses_table_raw_data_FSS_2026-06-01T04_05_16Z.csv` (in the staged `.zip`), 53 contiguous FYs **1971–2023**, 434,547 long rows, 10 columns (Year × Fed Dept × Fed Agency × Broad Category × Detailed Category × Institution × IPEDS UnitID × Detailed Institution Type × State → obligations kUSD).

**Phase 3 BUILT (2026-06-02); STOPPED before the v3.0.0 tag for the maintainer's pre-tag confirm** (corrected (f) + methods-note framing + deposit-metadata rewrite). Scope memo: `docs/fedsupport_rebase_scope.md`. Phase 1+2 done 2026-06-01.

**Phase 3 build artifacts (all determinism-gate STABLE, two-build):** `etl/_load_fedsupport.py` (RFC-4180 Build Table reader, native-UNITID→status, column-integrity assert), `etl/build_fedsupport_obligations.py` (→ `fedsupport_obligations.parquet` full long grain all-universes + `fedsupport_institution_year.parquet` higher-ed matched-UNITID (fy,unitid) aggregate + `anchor_reconciliation.md`), `etl/build_fedsupport_identity_spine.py` (UNITID-keyed join + `institution_identity.csv` + `herd_unitid_backfill_offer.csv` + `identity_spine_match_rate.md`), `etl/build_fedsupport_coverage_receipt.py` (→ `coverage_discontinuity.md`). Methods note: `docs/methods_notes/fedsupport/discontinuities.md`. Anchors reconcile (FY2023 +47K). Native-UNITID join = **78.4%** FY2023 dollars (vs MVP 73.1%).

**Two build-time corrections logged to `seeds/overrides.md` (2026-06-01/06-02):** (1) the Phase-2 (f) coverage-cliff was a UNIVERSE ARTIFACT (Academic FFRDC in denominator) — corrected to flat ~92–97% join-universe coverage; FFRDC is a separate universe (1971–98, ~30% early share, the real "1998/99 cliff"); steps are 1993→94 / 2008→09 (ARRA amplification of Seam-B no-match) / 2015→16 (back-assignment vintage, JHU ~87%). (2) native UNITID does NOT cleanly backfill the HERD-NULL giants (JHU/OSU/TAMU/Cincinnati/UConn are Seam-B multi-campus) — REINFORCES IPEDS #4 (reverses the Phase-2 roadmap read).

**PENDING pre-tag (NOT yet applied/done):** deposit-metadata rewrite (README line 5, `.zenodo.json`, `CITATION.cff` — bump to 3.0.0, FY2020–23→1971–2023) for the permanent version-DOI; the harmonized + raw MANIFEST entries ARE applied. **Survey-name flag:** `.zenodo`/`CITATION`/CLAUDE.md §1 say "Survey of Federal Funds for R&D" but the actual source is the "Survey of Federal **S&E Support**" (per table-description.txt) — surface to maintainer, do not silently change doctrine. Then tag `v3.0.0-fedsupport` (B2 irreversible).

Load-bearing findings:
- **v2.0 reproduces** — determinism gate PASS on all 6 generated artifacts (byte-identical two-build SHA, all matching committed). Tree clean; the reviewer's CRLF↔LF churn was a mount artifact (`git add --renormalize` is a no-op) — no `.gitattributes` needed.
- **Native IPEDS UnitID is present across ALL 53 years** — there is NO pre-UNITID name-only era (the working hypothesis was false). The gap is 3 explicit sentinel strings in the UNITID column: `No match…` (the real gap), `…not applicable to Nonprofits`, `…not applicable to FFRDCs`.
- **Overlap reconciles:** higher-ed = {Academic institution + Academic consortium}; export reconciles to all 4 Table 12 anchors within sum-rounding (FY2023 +47 kUSD on $48.96B). Export **supersedes** Table 12; Table 12 → audit siblings.
- **Native UNITID dollar coverage ~90.2% (FY2020–23) vs the reconstructed name-spine's 73.1%** → native UNITID **supersedes** the name-reconstruction (a §4 KILL-on-sight Vision call). The export even carries native UNITIDs for the HERD-NULL giants (Johns Hopkins `162928`, Ohio State `204796`, Vanderbilt `221999`, …), so it can **backfill HERD's era-B NULL UNITIDs**.
- **Discontinuity headline (clause-b):** UNITID *dollar* coverage is non-stationary — ~63–66% in 1971–98, cliff to ~97% at 1998/99, ~90% from 2016 (NCSES back-assignment vintages, not real funding shifts). Plus defunct/new agency roster + Detailed-Category taxonomy shifts (Other-support retired 2020, DOD detail split 1994). Broad Category (2-value R&D / S&E-support) is era-invariant.
- **Parse hygiene:** clean under RFC-4180 (DuckDB `read_csv_auto`); the reviewer's stray "Packers and Stockyards Administration" under Broad Category was a naive-split artifact (real Federal Agency names). Loader MUST use quoted-CSV parsing.

**Roadmap shift:** dataset-#4 IPEDS rationale is REVISED not eliminated (native UNITID delivers much of the HERD-backfill that justified it; IPEDS's remaining value is HERD era-A identity + system→campus hierarchy + identity-over-time) → reinforces GSS-first ([[overrides]] 2026-05-31). HD 3.6 funding-conversion-efficiency gets agency-resolved, R&D-to-R&D.

**Ratified 2026-06-01:** version = **`v3.0.0-fedsupport`**; HERD backfill = **offer-only, gated to IPEDS #4** (Phase 3 emits FedSupport native UNITID candidates in the spine but does NOT write them into the HERD panel). Spine-supersede core + schema + discontinuity treatment + go-to-build remain pending authorization.

**Version:** `v3.0.0-fedsupport` under the one concept DOI `10.5281/zenodo.20404785`; deposit-metadata rewrite (README line-5, `.zenodo.json` FY2020–23 → 1971–2023, CITATION, + add fedsupport parquet to `data/harmonized/MANIFEST.md` which currently omits it) lands BEFORE the tag (B2 pre-flight, permanent metadata). All deferred per the "bundle deposit-facing rewrites with Phase 3" instruction.

Related: [[feedback_etl_spike_scoping]] (scope-first), [[feedback_hd_entry_phase_budget]] (~2× discontinuity budget), [[feedback_scope_expansion_vision_surface]] (the §4 spine-scope call was surfaced to Vision, not built silently).
