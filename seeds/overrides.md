# Override Log

When the Maintainer overrides an agent verdict, log it here with one paragraph: what was proposed, what was overridden, the reasoning, and the kill condition that would prove the override wrong. Periodic panel reviews check overrides against outcomes — that is where the calibration happens, not in-session.

Format: date, agent overridden, proposed bet, verdict, override, kill condition.

---

(No overrides logged to date.)

## Calibration notes

Not overrides (no Maintainer-override-of-agent-verdict) — calibration evidence for periodic panel review, kept here alongside the override log per §12's "calibration happens at panel review" framing.

- **2026-05-26 — De-staling judgment near-miss (Stage 3 Phase C).** During the Phase C DOI swap, Skipper expanded beyond the literal `XXXXXXX → DOI` string replacement to de-stale the surrounding "reserved / minted-at-release" framing (README, CITATION.cff, BibTeX note, LICENSE-DATA.md) that a literal-only swap would have left false post-mint. Skipper applied the expansion and surfaced it transparently at completion; Vision (step-5 assessment) endorsed it as methodologically correct ("would have approved on sight") and coherent. **Calibration:** the judgment was right, but under the 7-step pattern a framing-semantics expansion ideally routes to Vision *before* application — transparent-flag-at-completion is the floor, Vision-surface-before-application the ceiling. Captured durably in `memory/feedback_scope_expansion_vision_surface.md`. No outcome harm. Kill condition for the captured guidance: if surface-before-application proves to add material latency on time-critical inline fixes without a quality benefit, revisit the floor/ceiling framing.
