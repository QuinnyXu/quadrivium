---
name: feedback-etl-spike-scoping
description: "For ETL spikes in quadrivium, Skipper surfaces a scoping prompt (what / MVP-vs-prod / runtime / validation plan / hidden edges / disposition) BEFORE writing spike code; principal reviews scope, then authorizes execution."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: c72ebc7d-a052-4948-b2b2-0eb7d42cf785
---

For HD work in quadrivium, every new ETL spike goes through a scoping-first surface before any spike code is written. Skipper's default output shape on a fresh spike is:

1. What the spike does (one paragraph, mechanics)
2. MVP vs production scope (what stays a spike, what would harden)
3. Expected runtime
4. Validation plan against the locked anchor
5. Hidden edges (gotchas, encoding shifts, structural absences)
6. Recommended disposition

Principal reviews the scope, then explicitly authorizes spike code to land.

**Why:** Two reasons. (1) HD 2.4.g entry-phase ran ~2× over the §10 energy-budget allocation last session because spikes landed code-first and then renegotiated scope mid-flight. Scoping-first burns less budget than scope-correction-after-code. (2) Spike code without a pre-committed validation plan tends to drift into "interesting findings" tangents that don't clear the HD sub-action — locking the validation surface up front keeps the spike pointed at the kill condition.

**How to apply:** Triggered for any new ETL spike under `etl/spikes/`. Skipper reads the relevant PANEL_SKIPPER §8 entries, the HD scoping doc section, and any anchor sidecar (CSV / YAML / SHA-256 manifest) BEFORE surfacing scope. Output goes to the principal, not to disk, until authorized. Three-spot-year sampling for cross-temporal characterization is already locked out per [[feedback-cross-temporal-sampling]] — scope must default to era-wide unless the kill condition is non-cross-temporal.

Does NOT apply to: re-runs of an already-authorized spike (substrate refresh), diagnostic probes named `_probe_*.py` or `_hd_*_diag*.py` (one-shot inspection, no panel-affecting output), or smoke-test outputs.
