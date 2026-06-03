# GSS 2017 redesign — RH clause-(b) boundary decomposition

**Boundary:** FY2016 → FY2017, the GSS instrument redesign. **Method:** fixed-cohort
decomposition (the HERD 2008→2011 four-driver template) on all-grad (FT+PT) total
enrollment, plus the degree-level structural change. **Date:** 2026-06-02.
Companion to `validation/reports/gss/gss_{support,race,pd_nfr}_validation.md`.

## The discontinuity

Total graduate enrollment falls **684,825 → 649,112 (net −35,713, −5.2%)** at the
2016→2017 boundary — the only *downward* step in the FY1972–2024 series. Concurrently
the source instrument is restructured: the Race/Support/PD_NFR sheets roughly double
in width (Race 122→290 columns), the support secondary axis swaps from gender to
degree-level, agency labels are recoded (`hhs_nih`→`nih`), and a **master's /
doctoral degree-level split is introduced** (all panels gain `ma_`/`dr_` columns).

## Decomposition (clause (b)) — the four drivers

| Driver | Value | Note |
|---|---|---|
| **Fixed-cohort change** (708 institutions present both years) | **−34,254** (−5.0% of base) | the same institutions report ~5% fewer students |
| **Frame / population** (6 entrants +1,496; 18 leavers −2,955) | **−1,459** | minimal — *not* a frame event |
| **Definitional: degree-level split** | **0 (additive)** | new disaggregation; all_grad = masters + doctoral **exactly** (2017: 649,112 = 378,587 + 270,525) |
| Identity check | −34,254 + (−1,459) = **−35,713** ✓ | = net |

The 2017 step is **almost entirely a fixed-cohort change** (96%), with negligible
frame movement — the opposite of the 1984–87 and 2014 boundaries (both
frame-dominated). Because the same 708 institutions drive it, and it reverses the
otherwise-monotonic enrollment trend exactly at a documented instrument redesign,
the fixed-cohort drop is **definitional-dominated** (a coverage/eligibility/
measurement change), not real enrollment decline.

## Clauses (a) / (b) / (c)

- **(a) Reconstructible.** Each era is usable on its own terms: pre-2017 carries
  all-grad enrollment by race × gender × enrollment-status; post-2017 adds the
  master's/doctoral split (a strict refinement). The harmonized panel keeps the
  `era` flag and the additive degree-level so a reader can stay within one regime.
- **(b) Decomposable.** Named, quantified components above: a definitional
  degree-level split (additive, net-zero), a near-zero frame term (−1,459), and a
  −34,254 fixed-cohort step attributable to the redesign's coverage/measurement
  change.
- **(c) Bounded unmeasurable.** The fixed-cohort −34,254 **conflates** any genuine
  2016→2017 enrollment change with the redesign's definitional change; the two
  cannot be separated without an external referent (Path B / descriptive, per HD
  2.1 §5). The bound: the entire −34,254 (−5.0%) is the maximum definitional
  attribution; the minimum is −34,254 minus the prior-year trend (~+2–3%/yr),
  i.e. the redesign removed roughly **5–8%** of the pre-2017 count basis.

## Cold-reader guidance
Use either era directly; do **not** difference a pre-2017 all-grad count against a
post-2017 count without noting the ~5% definitional step. The master's/doctoral
split is a post-2017-only refinement (additive to all-grad). §5 anchors (Tables
4-3/1-2a) reconcile **exactly** on each side of the boundary.
