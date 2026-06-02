# Federal S&E Support — methodological discontinuities (FY1971–FY2023)

*Reconstructive Harmonization applied to the NSF Survey of Federal Science and
Engineering Support to Universities, Colleges, and Nonprofit Institutions
(Federal S&E Support), full-series Build Table export.*

This note is written for the cold reader who wants to use the 53-year
funding-IN series — federal S&E obligations to individual institutions — and
join it to HERD's expenditure-OUT panel without misreading what changes across
five decades. Machine-readable receipts are the sources of truth and live in
`validation/reports/fedsupport/`; this prose translates them.

## The series, and the one thing a reader must not do

The Federal S&E Support module is **$2.3B (FY1971) → $49.0B (FY2023)** of
federal S&E obligations to higher-education institutions, one row per
`year × department × agency × broad/detailed activity × institution × type ×
state`, carrying a **native IPEDS UnitID**. The dollars are on a **federal
fiscal-year obligation basis** — *not* the institution reporting-year
expenditure basis HERD uses. The funding-IN ↔ expenditure-OUT join is therefore
not a free same-year join; the timing seam is a decomposition object (HD 3.6
Seam A), and every row carries an FY-basis flag so the gap is never read as
funding-conversion efficiency.

## Contribution-decomposition: what crosses each discontinuity

The re-base names and sizes four discontinuities. None is a coverage *defect*;
each is a documented break a reader can use either side of.

**1. Identity is native and near-complete — there is no name-only era.**
The Build Table carries a native IPEDS UnitID across all 53 years, so the MVP's
name-reconstruction is retired. On the join universe (academic institutions +
academic consortia), **UNITID covers ~92–97% of dollars every year, 1971–2023**
— flat, no early-era collapse. The join residual is **HERD-side**, not
FedSupport-side: institutions whose HERD era-B row carries a NULL `ipeds_unitid`
(scoping §6.3), and — for the dollar-dominant ones (Johns Hopkins, Ohio State,
Texas A&M, Cincinnati, Connecticut) — a **system-vs-campus grain** ambiguity
(those institutions appear under multiple campus UNITIDs on the FedSupport side
too). FedSupport→HERD joins on the native UNITID at **78.4% of FY2023 dollars**
(up from the MVP's 73.1% name-reconstruction); the rest is the HERD-side gap,
gated to the IPEDS cycle (dataset #4). Receipt:
`identity_spine_match_rate.md`.

> **A correction worth stating plainly.** An earlier scope pass reported
> early-era coverage at ~65% with a cliff at FY1998/99. That was a **universe
> artifact** — it counted FFRDCs (whose UNITID is "not applicable" by design)
> in the denominator. On the join universe the early era is well-covered
> (~92–97%); the FFRDC boundary is real but belongs to the FFRDC universe
> (point 2). Caught by an independent recompute on the correct universe; see
> `coverage_discontinuity.md` and `seeds/overrides.md`.

**2. The FFRDC reporting boundary (FY1998/99) — a separate universe.**
University-administered FFRDCs (national labs like APL, JPL, Lincoln Lab) were
reported in this survey's academic universe through **FY1998** — ~**29% of
(academic + FFRDC) dollars in FY1971**, declining to ~19% by FY1998 — then
**drop out entirely from FY1999**. This is a real structural break, but it is an
FFRDC-universe event: FFRDCs are not IPEDS institutions and are excluded from
the HERD join by design. We carry them in the long artifact (institution type =
`Academic FFRDC` / `Nonprofit FFRDC`, UNITID status = `na_ffrdc`) so the break
is visible and quantified, not silently mixed into the higher-ed series.

**3. Two modest coverage steps, decomposed (not population growth).**
Within the join universe, dollar coverage steps **97.0% → 93.5% at FY2008/09**
and **93.3% → 89.5% at FY2015/16**. Both are driven by *continuing*
institutions, not new entrants (new institutions contribute <$5K of each
~$1.3–1.5B unmatched-dollar increase):
- **FY2008/09** coincides with the **ARRA surge ($28.6B → $35.9B)**. The drop is
  ARRA dollars flowing into *pre-existing* system-level `no_match` attributions
  (U. Michigan, Pittsburgh, Rutgers — Seam-B system rows), **not** new
  unmatched recipients. ARRA is a dollar amplifier of the existing Seam-B set.
- **FY2015/16** is a **back-assignment vintage**: 21 continuing institutions
  recoded matched → no-match, **Johns Hopkins alone (~$1.1B) ≈ 87% of the step.**

This mirrors the HERD 2008→2011 four-driver decomposition (real growth /
definitional / population / residual): here the live drivers are real growth
(ARRA) and back-assignment vintage; population expansion is nil.

**4. Roster and taxonomy churn across 53 years.**
Departments come and go — defunct: Office of Economic Opportunity (1971–74),
Labor (→2017), Housing & Urban Development (→2019); new: Education (1980→),
Homeland Security (2003→), Justice (1996→). The **broad activity split is
era-invariant** (two values — *Research and development* vs *S&E support
activities* — across all 53 years), which is what lets us isolate the
like-for-like R&D-obligations counterpart to HERD federal R&D expenditure;
the *detailed* activity taxonomy does shift (e.g. *Other support for S&E*
retired after FY2020; the DOD detail split in FY1994). Raw department / agency /
detailed-category labels are preserved verbatim in the long artifact.

## Validation receipt

The full-series export **reconciles to the published higher-ed Table 12
grand-total anchors** (academic + consortium): FY2023 **$48,961,705K vs
$48,961,658K (+47, +0.000%)**; FY2020–FY2022 within sum-of-rounded-rows
tolerance (≤0.009%). The export therefore supersedes the four FY2020–FY2023
Table 12 slices, which are retained as audit siblings. Both harmonized parquets
rebuild bit-identically (two-build SHA, §3). Receipts:
`anchor_reconciliation` (the (b) overlap + full series), `identity_spine_match_rate`
(join), `coverage_discontinuity` (the corrected per-year coverage and its
decomposition).
