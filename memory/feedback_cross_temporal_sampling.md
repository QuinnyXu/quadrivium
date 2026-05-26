---
name: feedback-cross-temporal-sampling
description: Spike sampling for empirical characterization of cross-temporal NCSES encoding patterns defaults to era-wide coverage; three-spot-year sampling is reserved for spikes whose kill condition does not depend on cross-temporal scope completeness.
metadata: 
  node_type: memory
  type: feedback
  originSessionId: c72ebc7d-a052-4948-b2b2-0eb7d42cf785
---

Spike sampling methodology for quadrivium HD work:

- **Empirical characterization of cross-temporal NCSES encoding patterns (status codes, NULL semantics, label drift, etc.):** default to era-wide coverage.
- **Three-spot-year sampling:** reserved for (a) assumption-testing spikes whose kill condition is not cross-temporal, (b) proof-of-concept spikes that do not influence panel-affecting decisions.

**Why:** Locked 2026-05-10 PM as part of the W4 NULL-handling re-characterization. The original spike (`spike_herd_null_characterization.py` first pass) sampled three spot years and missed the era-B `status='u'` ~4,000-row population, leading to a kill criterion that fired falsely. Re-running era-wide surfaced the true encoding pattern and produced the locked three-tier corrected baseline (era-A NOT expected; era-B 2010–2022 allowed; era-B 2023+ NOT expected per FY 2023+ retirement evidence). See `validation/reports/herd_null_characterization_findings.md` and PANEL_SKIPPER §8 W4 entry.

**How to apply:** When Skipper scopes any new empirical-characterization spike under `etl/spikes/`, the default sampling frame is the full era (era-A: 1972–2009; era-B: 2010–2024; or full panel where the question is era-agnostic). If a spike proposes spot-year sampling, the scoping surface must explicitly justify why the kill condition does not depend on cross-temporal completeness. Connects to [[feedback-etl-spike-scoping]] — the validation-plan slot of the scoping prompt is where the sampling frame is declared and defended.
