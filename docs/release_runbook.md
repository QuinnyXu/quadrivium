# Release Runbook — GitHub public release + Zenodo DOI

How a quadrivium release goes public and gets a citable DOI. Written from the HERD `v1.0.0-herd` first release (2026-05); reusable for HERD re-mints (data corrections, new fiscal years) and future dataset additions (FedSupport, IPEDS, NSF GSS) under the **one-database, one-concept-DOI** model (CLAUDE.md §10; overturns Decision B — see `seeds/overrides.md`). The integrated harmonized database is **one Zenodo deposit under one concept DOI** (`10.5281/zenodo.20404785`); every release — HERD re-mint or new survey — is a new **version** of that one database, minting a version DOI under the constant concept DOI.

## Parameters (fill per release)

| Placeholder | v1.0.0-herd value | Meaning |
|---|---|---|
| `<ACCOUNT>` | `QuinnyXu` | GitHub account/org owning the public repo |
| `<REPO>` | `quadrivium` | repository name |
| `<TAG>` | `v1.0.0-herd` | annotated release tag (`vMAJOR.MINOR.PATCH-<dataset>`); the `-<dataset>` slug is a readability label on a **version of the one database**, not a separate deposit |
| `<DATASET>` | HERD | the dataset this version adds or re-mints |
| `<CONCEPT_DOI>` | `10.5281/zenodo.20404785` | the single **database** concept DOI — **constant across all datasets and all versions** (canonical for citation; never re-minted per dataset) |
| `<VERSION_DOI>` | `10.5281/zenodo.20404786` | this version's DOI (audit trail) |

## Phase structure (reversibility is the organizing principle)

- **Phase 0 — history hygiene (optional, local, revertible).** Only if commit-author identity needs normalizing before the first public push.
- **Phase A — pre-deposit gates (local, revertible).** A1: the generator-determinism sweep (two-build SHA on every generated artifact — a HARD gate). A2: CONTRIBUTING.md, repo-URL fill, doc reconciliation.
- **Phase B — public surface (IRREVOCABLE, credential-gated).** Push, release/tag, DOI mint. **One-way doors.**
- **Phase C — DOI fill (post-release commit, revisable).** Swap the placeholder for the minted **version** DOI on `main`; the **concept** DOI (`10.5281/zenodo.20404785`) is constant and already in place from v1.0.0.

The irrevocability boundary is the **first push (B1)**. Everything before it is revertible; everything at and after it is permanent (a public commit is assumed cached/forked; a minted Zenodo DOI is permanent by policy).

---

## Phase 0 — commit-author identity normalization (optional)

Run only if the local commit history carries an identity that should not be the public author (e.g., a working identity ≠ the release account). Skip otherwise.

1. **Back up externally first** — `git bundle create ../<REPO>-prerewrite.bundle --all`. *Not* a tag or branch: a history rewrite rewrites all refs (a tag follows the rewrite) and `git filter-repo`'s cleanup expires the reflog. The bundle is an external file the rewrite cannot touch; recovery is `git clone` from it.
2. **Rewrite** with `git filter-repo --mailmap <mailmapfile> --force` (a mailmap maps old → new identity; `--mailmap` rewrites author + committer + tagger; message bodies untouched, so any `Co-Authored-By` trailers survive). `--force` is expected on a working repo (not a fresh clone).
3. **Reconcile in-doc commit-hash references.** A rewrite changes every commit hash but **not file content** — so file SHA-256s (parquets, MANIFESTs) are preserved; only commit hashes referenced in tracked docs go stale. Translate them via `.git/filter-repo/commit-map` and land a single reconciliation commit. Then re-grep the repo for the old hashes → expect zero.
4. **Verify:** all commits show the new author + committer; the parquet SHAs still match `data/harmonized/MANIFEST.md`; tree clean.

> **Lesson (v1.0.0-herd):** file SHAs survive an author rewrite; commit hashes do not. The reproducibility contract (CLAUDE.md §3) is about *file* reproducibility, so the rewrite leaves it intact — but in-doc audit references (`git show <hash>`) must be reconciled or they dangle, which fails the clause-(c) auditability bar.

---

## Phase A — pre-deposit gates (local, revertible)

Run these **before** the irrevocable B1 push. They are content/reproducibility gates; any failure is a build-bug investigation, not a release step.

### A1 — ⚠️ HARD GATE: generator-determinism sweep (two-build SHA on EVERY generated artifact)

Every **generator-emitted** deposit artifact must rebuild **bit-equivalently** (CLAUDE.md §3 cold-reader contract). Hand-authored artifacts (crosswalk CSVs with curated `decision_rationale`, hand-written reconciliation prose) are **out of this gate by definition** — they are not regenerated. The gate fires on EVERY dataset deposit (HERD re-mints, FedSupport, GSS/SED, IPEDS), not only the dataset under active work.

**Procedure:**
1. **Enumerate** every generator-emitted artifact in the deposit set — i.e., every file written by an `etl/build_*.py` (or equivalent) generator: harmonized parquets, generated crosswalk spines, build-emitted validation receipts. Classify each candidate **generated vs hand-authored** and record the classification (a one-line note per artifact in the release notes is sufficient).
2. **Two-build SHA each generated artifact:** run its generator **twice consecutively**, SHA-256 the output after each run, and confirm the two hashes match.
3. **Parquet carve-out (data-stability fallback).** §3 explicitly carves out "modulo parquet writer determinism on a fixed input-and-code-version pair." So for a parquet: check byte-stability first; **if and only if** the bytes flap, verify the **data** (logical rows) is stable instead — hash the deterministically-sorted full-row content across the two builds. Byte-flap + data-stable = within the §3 carve-out (acceptable). **Data-flap = a real defect — STOP and fix.** (Order the build's final write with `ORDER BY ALL` so the logical row order is itself deterministic.)
4. **ALL must match.** Any flap on a non-parquet generated artifact, or any *data* flap on a parquet, **blocks the deposit**.

> **Lesson (HD 3.2, 2026-05-30):** the determinism check must cover **every** generated artifact, not just the one under active edit. The FedSupport spine receipt got the two-build check because it was being edited; the spine CSV — equally generator-emitted, equally a deposit artifact — did not, and shipped a non-deterministic SHA into a commit (the `herd_inst_name_long` alias was picked by unordered DuckDB iteration when ≥2 HERD names shared a UNITID). Non-determinism hides in *finished* artifacts precisely because they stop being rebuilt. The fix: a manufactured display value ships with a **documented, total-order tiebreak**; the gate: enumerate-and-two-build-SHA the whole generated set before push. See `seeds/overrides.md` (6th calibration finding).

### A2 — repo-prep checks

CONTRIBUTING.md present, repo-URL fill, doc reconciliation (CITATION.cff / README / `.zenodo.json` consistent), in-doc commit-hash references reconciled if Phase 0 ran. (The harmonized-parquet SHA gate against `data/harmonized/MANIFEST.md` runs again as the **first command of B1** — the irrevocability boundary — so it is listed there.)

---

## Prerequisites

- **GitHub push auth** configured (`gh auth login`, a PAT, or SSH). Verify with `gh auth status`.
- **Zenodo account**, created via **GitHub OAuth** (zenodo.org → Sign up → "Sign in with GitHub" → authorize). This aligns the Zenodo profile with the GitHub account. ORCID is optional (link under Zenodo → Account → Linked accounts).
- **Zenodo GitHub-integration toggle location:** Zenodo → top-right user menu → **GitHub** → repository list with on/off toggles. The repo must already exist on GitHub to appear (press **Sync** to refresh). This is the **B2 pre-flight** toggle.

---

## B1 — Push to a new public repo (IRREVOCABLE once pushed)

1. **Pre-push hash gate (first command).** Recompute the harmonized-parquet SHA-256s and confirm they match `data/harmonized/MANIFEST.md`:
   ```powershell
   Get-ChildItem data\harmonized\*.parquet | ForEach-Object {
     "{0}  {1}" -f (Get-FileHash $_ -Algorithm SHA256).Hash.ToLower(), $_.Name
   }
   ```
   **STOP on any mismatch** — content drift is a build-bug investigation, not a release step. Confirm `git status` clean and on `main`.
2. **Create the repo empty** on GitHub: owner `<ACCOUNT>`, name `<REPO>`, **Public**, **Issues ON**, **no** README/.gitignore/license (an initialized repo rejects the push as non-fast-forward).
3. `git remote add origin https://github.com/<ACCOUNT>/<REPO>.git` then `git push -u origin main`.
4. **Validate** on GitHub: harmonized parquets present; raw payload absent (gitignored by design — only MANIFEST/INVENTORY under `data/raw/`); README renders; CONTRIBUTING.md visible; Issues enabled. **STOP** if content/history is wrong — do **not** force-push a fresh public repo; revert from the bundle and recreate.

---

## B2 — Tag + release (IRREVOCABLE; triggers the Zenodo archive)

1. **⚠️ HARD PRE-FLIGHT — toggle the repo ON in Zenodo** (Prerequisites location) **before** creating the release. A release published with the toggle OFF is **not** archived and **cannot** be retro-archived.
2. **⚠️ HARD PRE-FLIGHT — confirm `.zenodo.json` carries the integrated-database identity** (title/description) **before** tagging. Per **CLAUDE.md §10** (the one irreversible step, verbatim): *"The per-version `.zenodo.json` title/description must be updated to the integrated-database identity BEFORE each release tag — the GitHub integration full-replaces published metadata from `.zenodo.json` at tag time, and the version DOI's metadata is permanent (the one irreversible step)."* So: before pushing `<TAG>`, open `.zenodo.json` and confirm the `title`/`description` name the **integrated quadrivium database at this version** (not a single survey, not a stale prior-version title). A stale title at tag time mints a **permanently** wrong-titled version DOI — uncorrectable. This is doctrine (§10); the runbook step is its operational form, not a separate rule.
3. **Create the annotated tag** (annotated `-a` carries tagger/date/message — the citable kind; not a lightweight pointer):
   ```
   git tag -a <TAG> -m "<one-line deposit description; ships <parquets>; methods note path; Citation + DOI: see CITATION.cff>"
   ```
   Verify locally: `git tag -l "<TAG>"` and `git show <TAG>`. Push: `git push origin <TAG>`. Verify on `…/tags`.
   > **Do not put a DOI in the tag message** — it does not exist until B3 (see lesson below).
4. **Create the GitHub release:** repo → Releases → "Draft a new release" → **choose the existing `<TAG>`** (do not create a new one) → title `<TAG>` → description mirrors the tag message → "Set as latest" → **Publish**. Publishing (toggle ON) fires the Zenodo webhook.
5. **Validate the archive fired:** within minutes a new deposit appears in Zenodo → Upload. **STOP** if none appears — the toggle was off; enable it and cut a fresh release.

---

## B3 — DOI mint + community (IRREVOCABLE)

Zenodo mints the concept + version DOIs automatically on archive. Confirm the deposit metadata matches `.zenodo.json` (title, version, CC-BY-4.0, creators, the GitHub `related_identifiers` back-link). Add a community if desired (revisable post-mint). **Validate** both DOIs resolve at `https://doi.org/…` and the deposit page is public.

> **STOP / worst case — B3 mint fails after B1 push already landed:** recoverable, not catastrophic. The repo is public but not yet citable; CITATION.cff/README already say the DOI is reserved-pending-mint, so the interim is honest. Fix the Zenodo-side cause and cut a fresh release to re-trigger. **Never hand-mint a manual-upload DOI to rescue it** — that creates a DOI not backed by the archived tag and breaks the git-is-the-artifact integrity story.

---

## Phase C — DOI swap (post-release commit on `main`, no re-tag)

Swap the placeholder for the minted **concept** DOI at the touch-points, with `CITATION.cff` as the single source of truth:
1. `CITATION.cff` `identifiers` value (canonical).
2. `README.md` plain-text citation.
3. `README.md` BibTeX citation.
4. `LICENSE-DATA.md` citation line.

Commit to `main` and push. **Do not re-tag `<TAG>`** and **do not re-mint** — the frozen release snapshot legitimately carries "DOI in CITATION.cff"; `main` going forward carries the live DOI. Sweep for residual placeholders → expect zero.

> **Lesson (v1.0.0-herd):** the minted DOI **cannot** be inside the release snapshot — the native GitHub→Zenodo integration archives the tag's tree *before* the DOI mints. So the DOI swap is necessarily a *post-release* commit on `main`, not a re-tag. Re-tagging to embed the DOI would mint a wasteful second version DOI for a cosmetic change. CITATION.cff-as-source-of-truth makes the swap a one-canonical-edit-plus-propagation, and makes a future version re-mint a known small operation.

---

## STOP reference

| Gate | STOP trigger | Action |
|---|---|---|
| A1 determinism sweep | any generated artifact's two-build SHA flaps (non-parquet), or a parquet's *data* flaps | don't push; build-bug investigation (non-determinism in a deposit artifact) |
| B1 hash gate | parquet SHA ≠ MANIFEST | don't push; build-bug investigation |
| B1 validate | wrong content/history public | stop before B2; **no force-push**; revert from bundle, recreate repo |
| B2 pre-flight | Zenodo toggle OFF at release | release won't archive; enable + cut fresh release |
| B2 pre-flight | stale `.zenodo.json` title at tag time (permanent wrong-title version DOI — the §10 one irreversible step) | confirm `.zenodo.json` carries the **integrated-database identity** before tagging; do not push `<TAG>` until corrected |
| B2 validate | no Zenodo deposit appears | toggle was off; enable + re-release |
| B3 | mint fails after push landed | recoverable; fix Zenodo-side + re-release; **never hand-mint manual DOI** |

The bundle backup (if Phase 0 ran) is retained until B3 is green, then deleted.

---

## Future version re-mint (forward note)

A data correction or new fiscal-year bump: update `version` in `CITATION.cff` + `.zenodo.json`, cut a new `<TAG>`, and the native integration mints a new **version** DOI under the stable **concept** DOI automatically. Then a Phase C swap updates the version-DOI references. The concept DOI in `CITATION.cff` does not change across versions.

**Adding a new dataset is a new version of the database, not a new deposit** (CLAUDE.md §10; overturns Decision B). To add FedSupport (or later IPEDS, GSS): update `.zenodo.json` `title`/`description` to the **integrated-database identity at the new version** (the B2 pre-flight gate — the one irreversible step, §10), bump `version` in `CITATION.cff` + `.zenodo.json`, cut a new `<TAG>` (e.g. `v2.0.0-fedsupport` — the slug is a readability label, not a separate deposit), and the integration mints a new **version** DOI under the **one constant concept DOI `10.5281/zenodo.20404785`**. The concept DOI does **not** change — same runbook, new parameters, same single deposit.
