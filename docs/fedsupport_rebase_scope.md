# FedSupport re-base scope memo — full-series 1971–2023 Build Table export

**Status: SCOPE SURFACE — STOP for maintainer authorization before the Phase 3 build.**
Author: Skipper (engineering) + Vision (strategy lens on (c) / roadmap). Date: 2026-06-01.
Scope discipline: surfaced before any build code, per the §10 scope-first reflex and the
~2× discontinuity budget ([[feedback_hd_entry_phase_budget]], [[feedback_etl_spike_scoping]]).

This memo re-bases dataset #2 (Federal S&E Support) from the FY2020–FY2023 Table 12 slice
onto the authoritative full-series NCSES Build Table export
(`data/raw/fedsupport/ncses_table_raw_data_FSS_2026-06-01T04_05_16Z.csv`, in the staged
`.zip`): **53 contiguous fiscal years 1971–2023, 434,547 long rows**, dimensions
Year × Federal Department × Federal Agency × Broad Category × Detailed Category ×
Institution × IPEDS UnitID × Detailed Institution Type × State → Fed Obligations for S&E
(thousands, current $). All figures below are from read-only DuckDB probes against the
staged CSV (RFC-4180 parse) — no build code landed.

---

## Phase 1 — verify + reconcile (DONE; results)

**1. v2.0 reproduces — determinism gate PASS.** Two consecutive builds of every
generator-emitted artifact produced byte-identical SHA-256, each matching the committed
value (`data/harmonized/MANIFEST.md` for the three pinned parquets; `seeds/overrides.md`
6th-calibration `df74f9bb…` for the spine CSV):

| Artifact | Two-build SHA-256 | Matches committed |
|---|---|---|
| `herd_panel.parquet` | `196132459f…0c6fcc` | ✅ MANIFEST |
| `herd_panel_attributes.parquet` | `216b8df851…a6e6d81` | ✅ MANIFEST |
| `herd_personnel.parquet` | `b3b937ebfe…1e4e101` | ✅ MANIFEST |
| `fedsupport_obligations.parquet` | `480cf6a308…44118cf` | ✅ (unpinned — see #3) |
| `crosswalks/_shared/institution_identity.csv` | `df74f9bbd1…1b0e99` | ✅ overrides.md |
| `validation/reports/fedsupport/identity_spine_match_rate.md` | `c2f87476d0…941d96` | ✅ |

> These are the **v2.0 (pre-re-base) SHAs** — this table records the Phase-1 verification that v2.0
> reproduced. The three **HERD** parquets are unchanged through v3.0. The three **fedsupport** MVP
> artifacts above (`480cf6a3…` obligations, `df74f9bb…` spine, `c2f87476…` receipt) were
> **superseded/rewritten by the Phase-3 re-base** — their v3.0 SHAs are pinned in the Phase-3
> determinism gate (the spine + receipts are now UTF-8/LF-clean per the A1b fix); see the v3.0
> harmonized `MANIFEST.md` and the regenerated receipts. Do not read the v2.0 hashes above as current.

**2. Working tree clean; no CRLF/LF churn.** `git status` clean before and after the
rebuilds (byte-identical outputs). `git add --renormalize .` is a **no-op** — the
reviewer's mount showed CRLF↔LF churn that does **not** reproduce locally; it was a mount
artifact. No `.gitattributes` is required. (Optional defensive `.gitattributes` can be
bundled with Phase 3 if cross-platform contributors arrive; not needed now.)

**3. Internal-record reconciliation.**
- **PANEL_VISION.md is NOT owed; `seeds/overrides.md` (+ CLAUDE.md doctrine) IS the
  strategy record.** `PANEL_SKIPPER.md` is the *engineering* lens's relitigation-proof
  locked-decision ledger (its §8 is what CLAUDE.md §8 cross-references). Vision's output has
  two homes by design: ratified verdicts become **CLAUDE.md** locked doctrine; overrides,
  divergences, and calibration land in **`seeds/overrides.md`** (which §12 explicitly names
  as where calibration lives — e.g. the 2026-05-31 GSS dataset-#3 decision record is already
  there). There is no orphaned class of Vision output needing a third file. Logged as a
  record-keeping note in `seeds/overrides.md` (2026-06-01).
- **`fedsupport_obligations.parquet` is absent from `data/harmonized/MANIFEST.md`** (only
  the 3 HERD parquets are pinned). Genuine gap, but the parquet is about to be redesigned by
  this re-base — **DEFER the MANIFEST entry to Phase 3** rather than pin a SHA that Phase 3
  immediately supersedes.
- **Cross-reference integrity OK.** The spine receipt's forward pointer to
  `docs/methods_notes/herd_panel_etl_scoping.md` §6.3 (HERD era-B `ipeds_unitid`
  canonical-not-complete: 47/1,125 institutions NULL, incl. Johns Hopkins ~$2.1B) resolves
  and is consistent.

**4. Deposit-facing scope rewrites DEFERRED (per instruction).** `README.md` line 5 still
reads *"The current scope is NSF HERD … The roadmap covers IPEDS, NSF GSS"* (stale on both
the shipped fedsupport dataset and the now-inverted GSS-then-IPEDS order); `.zenodo.json`
describes fedsupport as *"FY 2020–FY 2023."* **Not patched** — bundled with the Phase 3
version bump, since the re-base supersedes them wholesale.

---

## Phase 2 — the re-base scope (the eight questions)

### (a) Span + identity era — 1971–2023 contiguous; **NO pre-UNITID name-only era**

- **53 fiscal years, 1971–2023, fully contiguous** (no gaps in the span). 434,547 rows.
- **Native IPEDS UnitID is present across the ENTIRE span**, not just modern years. The
  Table Builder back-assigned UNITIDs to all 53 years. **The memo's working hypothesis — a
  pre-UNITID name-only era paralleling HERD's pre-2010 fice-only era — is FALSE.** There is
  no name-only identity era on the FedSupport side.
- The identity gap is **not** "no UNITID column"; it is **three explicit sentinel strings**
  in the UNITID column (the CSV codes them, it does not blank them):
  - `IPEDS UnitID not applicable to Nonprofits` (64,834 rows) — out of higher-ed scope.
  - `IPEDS UnitID not applicable to FFRDCs` (2,555 rows) — FFRDCs, out of academic scope.
  - `No match or no exact match for IPEDS UnitID` (16,177 rows) — **the genuine identity gap.**

### (b) Overlap reconciliation — export **SUPERSEDES** Table 12 (reconciles to all 4 anchors)

The higher-ed universe is **{Academic institution + Academic consortium}** (nonprofit and
FFRDC types are separable via `Detailed Institution Type`). Filtered to that universe, the
export reconciles to **all four** validated Table 12 grand-total anchors within sum-rounding:

| FY | Export (academic+consortium) | Published anchor | Diff |
|---|---:|---:|---:|
| 2020 | 39,120,944 | 39,122,152 | −1,208 (−0.003%) |
| 2021 | 43,218,819 | 43,222,829 | −4,010 (−0.009%) |
| 2022 | 44,624,226 | 44,628,417 | −4,191 (−0.009%) |
| 2023 | **48,961,705** | **48,961,658** | **+47 (+0.000%)** |

The tiny diffs are sum-of-whole-kUSD-rounded-rows vs the unrounded published total.
**Decision (b): the Build Table export becomes THE source; the four Table 12 CSVs/PDFs become
audit siblings** (retained, re-pointed as cross-checks, no longer the build input).

### (c) Native UNITID vs reconstructed spine — **SUPERSEDE the name-reconstruction** (Vision call)

This is the §4 KILL-on-sight spine-scope guardrail — a Vision-level scope call, surfaced
here, **not** a silent build choice.

- **Native UNITID dollar coverage (academic), FY2020–2023: ~90.2%** — vs the reconstructed
  name-spine's **73.1%** (`identity_spine_match_rate.md`). +17 points, and it is
  **source-native and authoritative**, not a name-reconstruction we maintain. The FY2023
  residual 9.8% is entirely the `No match` sentinel (FFRDC is 0.0% of the academic 2023
  total).
- **The native UNITID can backfill HERD's era-B NULL UNITIDs.** The export carries a native
  numeric UNITID for the exact §6.3 HERD-NULL giants: **Johns Hopkins → `162928`**, Ohio
  State → `204796`, Vanderbilt → `221999`, Oregon State → `209542`, U. Cincinnati →
  `201885`, Texas A&M College Station → `228723` (+ campus variants). This is an
  **authoritative NCSES name→UNITID source** that partially closes the HERD-side coverage
  gap the spine receipt and §6.3 attributed to the IPEDS cycle.
- **Caveats that persist (do NOT over-claim):** (1) the **system-vs-campus grain seam**
  (Seam B, HD 3.6) is unchanged — Texas A&M resolves to multiple campus UNITIDs; FedSupport
  reports a system-level obligation; backfilling HERD still needs a campus pick. (2) The
  `No match` class (~10% of FedSupport dollars) is structural. (3) Backfilling HERD is still
  a **name bridge** (FedSupport name → native UNITID → HERD name), now sourced from NCSES's
  authoritative assignment rather than our normalizer.

**Recommendation (c): the cross-survey spine pivots from a name-reconstruction crosswalk to a
UNITID-keyed join validated against the native column.** The name-matching machinery in
`build_fedsupport_identity_spine.py` is **retired** for FedSupport↔IPEDS (native UNITID
replaces it). The spine artifact's surviving role: (i) carry the FedSupport native
name→UNITID as an authoritative alias table, (ii) **offer** HERD era-B NULL-UNITID backfill
candidates (still subject to the Seam-B campus pick), (iii) hold the documented `No match`
residual as the clause-(c) receipt. **This does NOT pull the IPEDS cycle forward** — it uses
identity the new source already carries; HERD-side era-A (pre-2010) identity and authoritative
system→campus hierarchy remain the IPEDS #4 deliverables.

### (d) Schema / grain — preserve full long grain; isolate the R&D subset

- **Raw/long harmonized artifact** preserves the full grain (avg 6.3, max 59 rows per
  `(fy, unitid)` confirms genuine long format): `fiscal_year, federal_department,
  federal_agency, broad_category, detailed_category, institution_name_raw, ipeds_unitid,
  ipeds_unitid_status, institution_type, state, obligations_kusd, source, notes`
  (the `ipeds_unitid_status` column carries the sentinel class: `matched` / `no_match` /
  `na_nonprofit` / `na_ffrdc`; the FY-basis `notes` flag is retained from the MVP loader).
- **No double-counting:** `Broad Category` has exactly **2** values; `Detailed Category` has
  **10**, with **zero** `total`/subtotal rows. Summing the finest grain is safe (it
  reproduces the academic anchor exactly, per (b)).
- **Institution-year aggregation for the HERD join:** `SUM(obligations_kusd) GROUP BY
  (fiscal_year, ipeds_unitid)`, filtered to the higher-ed universe.
- **Like-for-like R&D isolation:** `Broad Category = 'Research and development'` is the
  expenditure-OUT counterpart to HERD federal R&D (FY2023 academic R&D = **$44,396,839K**);
  `'S&E support activities'` (fellowships, facilities, general/other support — FY2023
  $4.07B) is carried as a **documented superset**, not silently summed into the R&D figure.

### (e) Parse hygiene — **CLEAN under RFC-4180; the reviewer's field-shift was a naive-split artifact**

DuckDB `read_csv_auto` (RFC-4180 quoted parsing) yields exactly **2** Broad Category values
and **26** Federal Departments — no field-shift. The stray `"Packers and Stockyards
Administration"` / `"Drug Abuse"` the reviewer saw under Broad Category were a **naive
comma-split artifact**: these are real *Federal Agency* names (Packers & Stockyards is a USDA
agency; "Drug Abuse" is part of "National Institute on Drug Abuse"), correctly placed once
quotes are honored. **Lock: the loader MUST use RFC-4180 quoted-CSV parsing** (DuckDB
`read_csv_auto` or Python `csv` with quoting) — never naive split — and the build asserts
column integrity (Broad Category ∈ the 2-value set) before harmonizing.

### (f) 1971–2023 discontinuities (RH clause-(a)/(b)) — named + budgeted (~2×) — CORRECTED 2026-06-02

> **CORRECTION.** The original (f) reported a "1971–1998 ≈ 65% dollar coverage, cliff at
> 1998/99" UNITID-coverage discontinuity. That was a **universe artifact** — the by-year probe
> included **Academic FFRDC** rows (a separate institution type carrying the `na_ffrdc`
> sentinel by design) in the denominator. On the **join universe** (academic + consortium,
> FFRDC excluded — consistent with (b)/(c)), early-era coverage is **~92–97%**, flat across 53
> years; there is no 1998/99 cliff. Caught by independent RFC-4180 recompute (reviewer,
> 2026-06-01); re-derived in `validation/reports/fedsupport/coverage_discontinuity.md` and
> logged as a calibration finding in `seeds/overrides.md`. The corrected discontinuities:

1. **Join-universe UNITID coverage is flat ~92–97% dollars across all 53 years** (dual-rate
   per §4; row-level coverage similarly flat). No early-era collapse. The only genuine steps
   are modest: **1993→94** (91.7→96.5%, up), **2008→09** (97.0→93.5%, down), **2015→16**
   (93.3→89.5%, down). Both down-steps are **continuing-institution** effects, not population
   expansion (new institutions contribute <$5K of each ~$1.3–1.5B unmatched increase):
   - **2008→09** = real-growth (**ARRA $28.6B→$35.9B**) flowing into pre-existing
     system-level `no_match` (Seam-B) attributions; ARRA-new-recipient hypothesis **ruled out**.
   - **2015→16** = back-assignment vintage — 21 continuing institutions recoded
     matched→no-match, **Johns Hopkins (~$1.1B) ≈ 87% of the step.**
2. **FFRDC reporting boundary (FY1998/99) — a SEPARATE universe.** Academic + Nonprofit FFRDC
   are present **FY1971–FY1998** only (Academic FFRDC ~29% of academic+FFRDC dollars in FY1971,
   declining to ~19% by FY1998), then absent. A real RH clause-(b) break, **relocated to the
   FFRDC universe** (excluded from the HERD join by design), not a higher-ed coverage gap.
3. **Agency-roster changes (defunct / new departments).** Defunct: **Office of Economic
   Opportunity** (1971–74), Department of Labor (→2017), Housing & Urban Development (→2019),
   Treasury, GSA, Dept of State. New: Department of Education (1980→), Department of Homeland
   Security (2003→), DOJ (1996→), Nuclear Regulatory Commission (1975→). **Agency for
   International Development** persists 1971–2023.
4. **Category-taxonomy shifts (Detailed Category).** `'Other support for S&E'` retired after
   **2020**; DOD detail split at **1994**. **Broad Category (the 2-value R&D / S&E-support
   split) is era-invariant across all 53 years** — the stable spine for the R&D isolation in (d).

Budget: ~2× discontinuity crossing (≥4 named surfaces). The 2008/09 + 2015/16 steps were
decomposed with the HERD 2008→2011 four-driver template (real growth vs definitional vs
population vs residual); population is the nil driver in both.

### (g) Acquisition / provenance — CSV-native (§3 satisfied), SHA-256s recorded

Source is **CSV** — no xlsx→CSV conversion needed; the §3 no-runtime-extension lock is
satisfied natively (the loader reads the CSV via `read_csv_auto`). Provenance SHA-256s
(computed 2026-06-01; to be written into `data/raw/MANIFEST.md` fedsupport section **with**
the Phase 3 build, not before — deposit-facing, supersedes the current Table 12 section):

| SHA-256 | Bytes | File | Role |
|---|---:|---|---|
| `3cab4ebe3d…fd9536` | 90,133,450 | `…srv_data_FSS_2026-06-01T04_05_16Z.zip` | source archive |
| `796a55c325…aae6c8` | 90,132,415 | `…raw_data_FSS_2026-06-01T04_05_16Z.csv` | deposit build input |
| `22766c781d…131312` | 496,777 | `ncses_cust_table_FSS_…json` | query-definition sibling |
| `07c3e89ebe…bf781e` | 713 | `table-description-FSS.txt` | table-description sibling |

The four Table 12 CSVs + PDFs are retained as **audit siblings** (per (b)).

### (h) Versioning — major content change → new version under the one concept DOI

4-year → 53-year re-base is a **major content change** → **a new version of the one
integrated database** under the constant concept DOI `10.5281/zenodo.20404785` (CLAUDE.md
§10; not a new deposit). Proposed tag **`v3.0.0-fedsupport`** (major bump: dataset #2 is
re-based, schema redesigned). Per §10 + the release-runbook B2 pre-flight (the one
irreversible step): **update `.zenodo.json` title/description, `README.md`, and `CITATION.cff`
to the 1971–2023 scope BEFORE the release tag** — version-DOI metadata is permanent. Bundle
the deferred README line-5 / `.zenodo.json` fixes here. Add `fedsupport_obligations*` parquets
to `data/harmonized/MANIFEST.md` at this point.

---

## Roadmap implications (flagged per instruction)

- **HD 3.6 (obligation-vs-expenditure seam) gets richer.** The re-base makes the
  funding-conversion-efficiency deliverable **agency-resolved and R&D-to-R&D**: FedSupport
  `Broad Category='Research and development'` (federal R&D obligations-IN, by agency) against
  HERD federal R&D expenditure-OUT, on the institution-year hub — a far sharper join than the
  4-year all-S&E slice. The federal-FY-vs-institution-FY seam (Seam A) and the
  system-vs-campus grain seam (Seam B) are unchanged decomposition objects.
- **Dataset-#4 (IPEDS) rationale is REVISED, not eliminated.** IPEDS #4's headline
  justification was HERD era-B NULL-UNITID backfill (spine gate-check (c): 19/22 giants
  genuinely NULL, ~7.7% of anchor). **The re-base's native UNITID delivers much of that
  backfill itself** (Johns Hopkins `162928`, etc.). IPEDS #4's *remaining* unique value:
  (i) HERD **era-A** (pre-2010, fice-only, 35 years) identity; (ii) authoritative
  **system→campus** hierarchy (Seam B); (iii) comprehensive identity-over-time
  (mergers/renames). Net: **IPEDS #4 is even more clearly deferrable**, which **reinforces
  GSS-first** ([[overrides]] 2026-05-31). The GSS-first kill condition is unaffected.
- **No change to the GSS #3 blocker.** Still blocked on NSF/NCSES availability; HD 4.1
  gate-spike remains the first action on resumption.

---

## Scope decisions requiring authorization (the STOP gate)

Per the guardrail, **the Phase 3 build does not start until the maintainer authorizes**.
Decisions to ratify (each logged to `seeds/overrides.md` per §12 on authorization):

1. **(b)** Build Table export supersedes Table 12 as the source; Table 12 → audit siblings.
2. **(c)** Native UNITID supersedes the name-reconstruction spine; spine pivots to a
   UNITID-keyed join + authoritative alias + HERD-backfill *offer* (Seam-B-gated). **(§4
   KILL-on-sight guardrail — Vision-level call.)** **HERD backfill: RATIFIED OFFER-ONLY
   (2026-06-01)** — Phase 3 emits FedSupport native name→UNITID candidates in the spine but
   does **NOT** write them into the HERD panel; the actual HERD UNITID backfill stays an
   **IPEDS #4 deliverable**, keeping the §4 guardrail crisp.
3. **(d)** Schema: full long grain raw artifact + `(fy, unitid)` aggregation for the HERD
   join + R&D-broad isolation with S&E-support as documented superset.
4. **(f)** Discontinuity treatment: dual-rate (row + dollar) UNITID-coverage receipt across
   the vintages; methods note names the 1998/99 + 2008/09 coverage cliffs, the agency roster,
   and the category-taxonomy shifts.
5. **(h)** Version **`v3.0.0-fedsupport` — RATIFIED (2026-06-01)** under the one concept DOI;
   deposit-metadata rewrite (incl. deferred README/.zenodo fixes + harmonized MANIFEST
   fedsupport entry) lands BEFORE the tag.

**Ratified so far (2026-06-01):** decision 2's HERD-backfill sub-call (offer-only, gated to
IPEDS #4) and decision 5 (version `v3.0.0-fedsupport`). Decisions 1, 2-core (spine
supersede), 3, and 4 — and the overall go-to-build — remain pending maintainer authorization.
