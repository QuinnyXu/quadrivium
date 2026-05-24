---
name: feedback-hd-entry-phase-budget
description: HD entry-phase work that crosses a known operational-data discontinuity surface runs ~2x the §10 baseline allocation; pre-allocate ~2x and name the surfaces so the overrun reads as anticipated investigation, not slip.
metadata:
  node_type: memory
  type: feedback
---

For HD work in quadrivium, when a sub-action's **entry phase crosses a known operational-data discontinuity surface**, pre-allocate ~2× the §10 timeline baseline for that sub-action. Discontinuity surfaces seen so far: Table Builder UI navigation, NCSES historical archives, cross-vintage cohort assembly, classified-DOD reporting conventions, and era-boundary publication-regime drift.

**Why:** the entry phase is where substrate-shape findings surface, and surfacing them is the expensive, irreducible part of Reconstructive Harmonization — not slippage. HD 2.4.g's entry phase ran ~3 half-days against the §10 timeline's 1.5-half-day allocation (~2×). The overrun bought three substrate-shape findings (the 86→55 DST publication-regime contraction + the FY 2017 2-D-slice publication shape that defeats 3-D cell reconstruction; the UCSF Engineering structural absence; the Table Builder UI navigation hazard), the Vision consultation turnaround on the Branch I/II/III scope-shape fork, and the §2(b) re-shape pass scope addition. The 1.5-half-day estimate had assumed a mechanical spike; crossing the discontinuity surface turned it into an investigation. This driver is **distinct from, and additive to**, the code-first-then-renegotiate waste that [[feedback-etl-spike-scoping]] addresses: even with scope locked first, a discontinuity-crossing entry phase costs ~2× because the investigation is unavoidable.

**How to apply:** at scoping time, when the entry phase will cross one of the discontinuity surfaces above — the list generalizes; the test is *"does this entry phase touch a surface where the data's own discontinuities live?"* — budget ~2× the mechanical-spike baseline and name the surfaces in the scoping doc, so the overrun reads as anticipated investigation rather than slip. Forthcoming work this applies to: HD 3.x (NSF GSS) and HD 4.x (IPEDS) migrations, each carrying its own publication-regime and instrument discontinuities. Empirical anchor: `PANEL_SKIPPER.md` §8 HD 2.4.g combined entry (locked 2026-05-24). Connects to [[feedback-etl-spike-scoping]] (scope-first surface before spike code) and [[feedback-cross-temporal-sampling]] (era-wide default for cross-temporal characterization).
