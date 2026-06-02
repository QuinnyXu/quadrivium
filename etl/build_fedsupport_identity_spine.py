"""
etl/build_fedsupport_identity_spine.py — cross-survey institution-identity
spine (v3.0 re-base: UNITID-keyed, native-UNITID join).

The MVP reconstructed FedSupport↔IPEDS identity by name-matching (73.1% FY2023
dollar-match ceiling). The full-series Build Table export carries a **native
IPEDS UnitID**, so name-reconstruction is RETIRED for FedSupport↔IPEDS
(re-base decision (c), authorized 2026-06-01). This build:

  1. JOIN RECEIPT (RH clause-(c), two numbers) — joins the FedSupport
     higher-ed universe to HERD era-B on the NATIVE UNITID and reports the
     institution-match and dollar-match rates (FY2023 anchor).
  2. SPINE (authoritative alias) — crosswalks/_shared/institution_identity.csv:
     one row per distinct FedSupport higher-ed UNITID, the NCSES authoritative
     name alias, and whether it joins to a HERD era-B UNITID.
  3. HERD-BACKFILL OFFER (offer-only, Seam-B-gated, gated to IPEDS #4) —
     crosswalks/_shared/herd_unitid_backfill_offer.csv: HERD era-B institutions
     that carry a NULL ipeds_unitid (the §6.3 canonical-not-complete gap, e.g.
     Johns Hopkins) matched by name to a FedSupport native UNITID, OFFERED as a
     candidate. Multi-campus (system-vs-campus grain, Seam B) candidates are
     FLAGGED and NOT offered. **Per the ratified offer-only disposition, these
     are NOT written into the HERD panel — the actual backfill is an IPEDS #4
     deliverable; this file only surfaces what the join would reach.**

Reads:
  data/harmonized/fedsupport_institution_year.parquet  (higher-ed, matched UNITID)
  data/harmonized/fedsupport_obligations.parquet        (for FY2023 higher-ed $)
  data/harmonized/herd_panel.parquet                    (era-B UNITID join target)

Reproducibility (§3): deterministic — sorted outputs, documented tiebreaks,
generator-emitted receipt (Option A). Two-build SHA stable.

Author: Skipper, 2026-06-02 (v3.0 re-base).
"""

from __future__ import annotations

import csv as _csv
import io
import re
import sys
from collections import defaultdict
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from etl._load_fedsupport import write_text_clean  # noqa: E402

FS_INSTYEAR = ROOT / "data" / "harmonized" / "fedsupport_institution_year.parquet"
FS_LONG = ROOT / "data" / "harmonized" / "fedsupport_obligations.parquet"
HERD_PARQUET = ROOT / "data" / "harmonized" / "herd_panel.parquet"
SPINE_OUT = ROOT / "crosswalks" / "_shared" / "institution_identity.csv"
BACKFILL_OUT = ROOT / "crosswalks" / "_shared" / "herd_unitid_backfill_offer.csv"
RECEIPT = (ROOT / "validation" / "reports" / "fedsupport"
           / "identity_spine_match_rate.md")

FY2023_ANCHOR_KUSD = 48_961_658

# --------------------------------------------------------------------------
# Name normalizer — retained ONLY for the HERD-backfill OFFER (HERD-NULL rows
# carry no UNITID, so the offer must name-match HERD→FedSupport). It is NOT
# used for FedSupport↔IPEDS identity, which is native. Flat token-set with
# city folded in; collisions (>1 UNITID) are Seam-B and left UNOFFERED.
# --------------------------------------------------------------------------
_ABBREV = [
    (r"\bU\.\s*", "university "), (r"\bUniv\.?\b", "university"),
    (r"\bColl\.?\b", "college"), (r"\bC\.\s*", "college "),
    (r"\bInst\.?\b", "institute"), (r"\bTech\.?\b", "technology"),
    (r"\bTechnol\.?\b", "technology"), (r"\bSt\.\s*", "saint "),
    (r"\bA&M\b", "a m"), (r"\bSci\.?\b", "science"), (r"\bMed\.?\b", "medical"),
    (r"\bCtr\.?\b", "center"), (r"\bN\.\s*", "north "), (r"\bS\.\s*", "south "),
    (r"\bE\.\s*", "east "), (r"\bW\.\s*", "west "),
]
_STOP = {"of", "the", "at", "in", "and"}
_LOCATOR = {"campus", "the"}


def _expand(s: str) -> str:
    out = " " + s + " "
    for pat, rep in _ABBREV:
        out = re.sub(pat, rep, out, flags=re.IGNORECASE)
    return out.strip()


def flat_key(name: str) -> frozenset:
    s = re.sub(r",\s*The\b", "", name.strip(), flags=re.IGNORECASE)
    s = _expand(s.replace("-", " ").replace(",", " "))
    s = s.lower().replace("&", " and ")
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return frozenset(t for t in s.split() if t not in _STOP and t not in _LOCATOR)


def main() -> int:
    con = duckdb.connect()
    print("=" * 72)
    print("v3.0 re-base — UNITID-keyed cross-survey identity spine")
    print("=" * 72)

    fsiy = FS_INSTYEAR.as_posix()
    fslong = FS_LONG.as_posix()
    herd = HERD_PARQUET.as_posix()

    # --- HERD era-B join target: non-null UNITID set + names; NULL-unitid names ---
    herd_uids = set(r[0] for r in con.execute(
        f"SELECT DISTINCT ipeds_unitid FROM read_parquet('{herd}') "
        "WHERE era='B' AND ipeds_unitid IS NOT NULL").fetchall())
    herd_name_by_uid = {}
    for uid, nm, n in con.execute(
        f"""SELECT ipeds_unitid, inst_name_long, COUNT(*) n
            FROM read_parquet('{herd}')
            WHERE era='B' AND ipeds_unitid IS NOT NULL AND inst_name_long IS NOT NULL
            GROUP BY ipeds_unitid, inst_name_long""").fetchall():
        herd_name_by_uid.setdefault(uid, []).append((nm, n))
    # deterministic alias: most-frequent era-B display name, then alphabetical.
    herd_alias = {uid: sorted(c, key=lambda x: (-x[1], x[0]))[0][0]
                  for uid, c in herd_name_by_uid.items()}
    # HERD era-B names that carry NULL unitid on EVERY row (the §6.3 gap).
    herd_null_names = [r[0] for r in con.execute(
        f"""SELECT DISTINCT inst_name_long FROM read_parquet('{herd}') a
            WHERE era='B' AND inst_name_long IS NOT NULL
              AND NOT EXISTS (SELECT 1 FROM read_parquet('{herd}') b
                 WHERE b.era='B' AND b.inst_name_long=a.inst_name_long
                   AND b.ipeds_unitid IS NOT NULL)""").fetchall()]
    print(f"  HERD era-B non-null UNITIDs: {len(herd_uids):,}")
    print(f"  HERD era-B NULL-on-every-row names (§6.3 gap): {len(herd_null_names)}")

    # --- FedSupport higher-ed UNITID universe (native) ---
    fs_uids = set(str(r[0]) for r in con.execute(
        f"SELECT DISTINCT ipeds_unitid FROM read_parquet('{fsiy}')").fetchall())
    # authoritative alias: name in the most-recent fiscal year, tie alphabetical.
    fs_alias = {}
    fs_state = {}
    fs_years = defaultdict(set)
    for uid, fy, nm, st in con.execute(
        f"SELECT ipeds_unitid, fiscal_year, institution_name, state "
        f"FROM read_parquet('{fsiy}')").fetchall():
        fs_years[str(uid)].add(fy)
    for uid, nm, st in con.execute(
        f"""SELECT ipeds_unitid, institution_name, state FROM (
              SELECT ipeds_unitid, institution_name, state, fiscal_year,
                ROW_NUMBER() OVER (PARTITION BY ipeds_unitid
                  ORDER BY fiscal_year DESC, institution_name ASC) rn
              FROM read_parquet('{fsiy}'))
            WHERE rn=1""").fetchall():
        fs_alias[str(uid)] = nm
        fs_state[str(uid)] = st
    print(f"  FedSupport higher-ed distinct native UNITIDs: {len(fs_uids):,}")

    # --- (1) JOIN RECEIPT: native-UNITID FedSupport↔HERD ---
    matched_uids = fs_uids & herd_uids
    inst_rate = len(matched_uids) / len(fs_uids) if fs_uids else 0.0
    # FY2023 dollar match: higher-ed FY2023 obligations whose native UNITID is in HERD.
    fy23_total = con.execute(
        f"""SELECT SUM(total_se_kusd) FROM read_parquet('{fsiy}')
            WHERE fiscal_year=2023""").fetchone()[0]
    # join target as a SQL list
    uid_list = ",".join("'%s'" % u for u in sorted(herd_uids))
    fy23_matched = con.execute(
        f"""SELECT SUM(total_se_kusd) FROM read_parquet('{fsiy}')
            WHERE fiscal_year=2023 AND ipeds_unitid IN ({uid_list})""").fetchone()[0]
    dollar_rate = fy23_matched / FY2023_ANCHOR_KUSD
    print(f"\n--- (1) NATIVE-UNITID JOIN RECEIPT ---")
    print(f"  institution match: {len(matched_uids):,}/{len(fs_uids):,} = {inst_rate:.1%}")
    print(f"  FY2023 dollar match: {fy23_matched:,.0f}/{FY2023_ANCHOR_KUSD:,} "
          f"= {dollar_rate:.1%}  (vs MVP name-recon 73.1%)")

    # --- (3) HERD-BACKFILL OFFER (name-match HERD-NULL → FedSupport native UNITID) ---
    # FedSupport flat-key -> set(native unitid) over the higher-ed universe.
    fs_flat = defaultdict(set)
    for uid in fs_uids:
        fs_flat[flat_key(fs_alias[uid])].add(uid)
    backfill_rows = []
    offer_single = 0
    offer_seamb = 0
    offer_none = 0
    # FY2023 HERD-NULL dollars recoverable by the offer (uplift ceiling): we
    # measure on the FedSupport side — FY2023 dollars on the offered UNITIDs
    # that are NOT currently in HERD (so the join would gain them).
    offered_uids = set()
    for nm in sorted(herd_null_names):
        fk = flat_key(nm)
        cands = fs_flat.get(fk, set())
        if len(cands) == 1:
            uid = next(iter(cands))
            offer_single += 1
            offered_uids.add(uid)
            backfill_rows.append({
                "herd_inst_name_long": nm,
                "offered_ipeds_unitid": uid,
                "fedsupport_name": fs_alias[uid],
                "state": fs_state.get(uid, ""),
                "offer_status": "single_candidate",
                "decision_rationale": (
                    "HERD era-B row carries NULL ipeds_unitid (canonical-not-"
                    "complete, scoping §6.3); name flat-key matches exactly ONE "
                    "FedSupport native UNITID. OFFER-ONLY — gated to IPEDS #4, "
                    "NOT written into the HERD panel (re-base decision (c))."),
            })
        elif len(cands) > 1:
            offer_seamb += 1
            backfill_rows.append({
                "herd_inst_name_long": nm,
                "offered_ipeds_unitid": "",
                "fedsupport_name": "; ".join(sorted(fs_alias[c] for c in cands)),
                "state": "",
                "offer_status": "seam_b_multi_campus_unoffered",
                "decision_rationale": (
                    "name flat-key matches >1 FedSupport native UNITID "
                    "(system-vs-campus grain, Seam B); NO campus pick made — "
                    "UNOFFERED, deferred to HD 3.6 / IPEDS #4."),
            })
        else:
            offer_none += 1
    # uplift: FY2023 FedSupport dollars on single-candidate offered UNITIDs not in HERD.
    uplift = 0.0
    if offered_uids:
        ol = ",".join("'%s'" % u for u in sorted(offered_uids - herd_uids))
        if ol:
            uplift = con.execute(
                f"""SELECT SUM(total_se_kusd) FROM read_parquet('{fsiy}')
                    WHERE fiscal_year=2023 AND ipeds_unitid IN ({ol})""").fetchone()[0] or 0.0
    ceiling = dollar_rate + uplift / FY2023_ANCHOR_KUSD
    print(f"\n--- (3) HERD-BACKFILL OFFER (offer-only, gated to IPEDS #4) ---")
    print(f"  single-candidate offers: {offer_single}   Seam-B unoffered: {offer_seamb}"
          f"   no FedSupport match: {offer_none}")
    print(f"  FY2023 uplift if offers backfilled into HERD: +{uplift:,.0f} kUSD "
          f"(+{uplift/FY2023_ANCHOR_KUSD:.1%}) -> ceiling {ceiling:.1%}")

    # --- (2) WRITE SPINE CSV (UNITID-keyed authoritative alias) ---
    SPINE_OUT.parent.mkdir(parents=True, exist_ok=True)
    spine_rows = []
    for uid in sorted(fs_uids, key=lambda u: int(u)):
        joins = uid in herd_uids
        spine_rows.append({
            "ipeds_unitid": uid,
            "fedsupport_name": fs_alias[uid],
            "state": fs_state.get(uid, ""),
            "fedsupport_years": f"{min(fs_years[uid])}-{max(fs_years[uid])}",
            "joins_herd_erab": "yes" if joins else "no",
            "herd_inst_name_long": herd_alias.get(uid, ""),
            "match_basis": "native_unitid",
            "decision_rationale": (
                "FedSupport native IPEDS UnitID (NCSES-assigned); "
                + ("joins HERD era-B on UNITID" if joins
                   else "no HERD era-B row carries this UNITID "
                        "(NSF-funded institution outside the HERD UNITID set "
                        "or HERD-side NULL — see backfill offer)")),
        })
    fields = ["ipeds_unitid", "fedsupport_name", "state", "fedsupport_years",
              "joins_herd_erab", "herd_inst_name_long", "match_basis",
              "decision_rationale"]
    _sio = io.StringIO()
    w = _csv.DictWriter(_sio, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    w.writerows(spine_rows)
    write_text_clean(SPINE_OUT, _sio.getvalue())
    print(f"\n  wrote {SPINE_OUT.name} ({len(spine_rows)} UNITID rows)")

    # backfill offer CSV (sorted: single-candidate first by name, then seam-b)
    bfields = ["herd_inst_name_long", "offered_ipeds_unitid", "fedsupport_name",
               "state", "offer_status", "decision_rationale"]
    backfill_rows.sort(key=lambda r: (r["offer_status"], r["herd_inst_name_long"]))
    _sio2 = io.StringIO()
    w = _csv.DictWriter(_sio2, fieldnames=bfields, lineterminator="\n")
    w.writeheader()
    w.writerows(backfill_rows)
    write_text_clean(BACKFILL_OUT, _sio2.getvalue())
    print(f"  wrote {BACKFILL_OUT.name} ({len(backfill_rows)} HERD-NULL rows)")

    receipt = {
        "n_fs_uids": len(fs_uids), "n_herd_uids": len(herd_uids),
        "matched_uids": len(matched_uids), "inst_rate": inst_rate,
        "fy23_total": fy23_total, "fy23_matched": fy23_matched,
        "dollar_rate": dollar_rate, "anchor": FY2023_ANCHOR_KUSD,
        "offer_single": offer_single, "offer_seamb": offer_seamb,
        "offer_none": offer_none, "uplift": uplift, "ceiling": ceiling,
        "n_herd_null": len(herd_null_names),
    }
    _write_receipt(receipt, backfill_rows)
    return 0


def _write_receipt(r, backfill_rows) -> None:
    """Generator-emitted clause-(c) receipt (Option A — data-derived figures
    templated; editorial voice as literals; rebuild byte-stable)."""
    A = []
    a = A.append
    a("# FedSupport ↔ HERD identity-spine match-rate receipt (v3.0 re-base, native UNITID)")
    a("")
    a("**Two-number match-rate receipt (RH clause-(c)).** Author: Skipper. "
      "Generated by `etl/build_fedsupport_identity_spine.py` (deterministic).  ")
    a("Spine: `crosswalks/_shared/institution_identity.csv` (UNITID-keyed). "
      "Backfill offer: `crosswalks/_shared/herd_unitid_backfill_offer.csv`. "
      f"Anchor: FY2023 higher-ed grand total = **${r['anchor']:,}K**.")
    a("")
    a("> **What changed at v3.0.** The MVP reconstructed FedSupport↔IPEDS "
      "identity by name-matching and topped out at a **73.1%** FY2023 "
      "dollar-match. The full-series Build Table export carries a **native "
      "IPEDS UnitID**, so name-reconstruction is retired for FedSupport↔IPEDS "
      "and the join runs on the authoritative key. The number below is the "
      "native-UNITID join, not a name reconstruction.")
    a("")
    a("## 0. The two numbers (native-UNITID join)")
    a("")
    a("| Axis | Matched | Total | Rate |")
    a("|---|---:|---:|---:|")
    a(f"| **Institutions** (FedSupport higher-ed UNITIDs in HERD era-B) | "
      f"{r['matched_uids']:,} | {r['n_fs_uids']:,} | **{r['inst_rate']:.1%}** |")
    a(f"| **Dollars** (FY2023, thread-critical) | ${r['fy23_matched']:,.0f}K | "
      f"${r['anchor']:,}K | **{r['dollar_rate']:.1%}** |")
    a("")
    a(f"The join target is HERD era-B's **{r['n_herd_uids']:,}** non-null "
      "UNITIDs. The dollar rate is the share of FY2023 higher-ed obligations "
      "whose native FedSupport UNITID is present in the HERD era-B panel.")
    a("")
    a("## 1. Why the residual is HERD-side — and why most of it is NOT a clean backfill")
    a("")
    a("On the FedSupport side identity is now authoritative (native UNITID, "
      "~90.2% of FY2023 higher-ed dollars carry one; the rest are the NCSES "
      "`No match` sentinel). The join residual is therefore HERD-side, and it "
      "splits into two structural classes — and the **dollar-dominant** one is "
      "NOT trivially backfillable:")
    a("")
    a("- **System-vs-campus grain (Seam B) — the big-dollar class.** The "
      "HERD-NULL institutions that carry the most money — **Johns Hopkins, Ohio "
      "State, Texas A&M (College Station), University of Cincinnati, University "
      "of Connecticut** — are exactly the ones FedSupport lists under "
      "**multiple campus UNITIDs** (`Johns Hopkins U.` resolves to two native "
      "UNITIDs, not one). So the native column does **not** hand us a single "
      "UNITID for them; picking the campus is the Seam-B / IPEDS #4 "
      "system→campus judgment, deliberately NOT made here.")
    a("- **Clean single-UNITID NULLs — the small-dollar class.** The HERD-NULL "
      "names that DO map to exactly one FedSupport native UNITID are smaller "
      "institutions (Art Center, Bard, Embry-Riddle, Oregon State, Scripps, …); "
      "these are the offerable backfills below, and they are worth only "
      f"**+{r['uplift']/r['anchor']:.1%}** of the anchor.")
    a("")
    a("**Correction vs the Phase-2 scope memo:** the memo implied the native "
      "UNITID could backfill the HERD-NULL giants (e.g. Johns Hopkins → "
      "162928). The build shows otherwise — those giants are multi-campus on "
      "the FedSupport side, so they need the IPEDS #4 system→campus hierarchy, "
      "not a one-line UNITID copy. This **reinforces** IPEDS #4's rationale "
      "rather than weakening it (logged: `seeds/overrides.md`, v3.0 build "
      "calibration).")
    a("")
    a("## 2. HERD-backfill OFFER — offer-only, Seam-B-gated, gated to IPEDS #4")
    a("")
    a(f"Of the **{r['n_herd_null']}** HERD era-B names that carry NULL "
      f"`ipeds_unitid` on every row: **{r['offer_single']}** match exactly one "
      f"FedSupport native UNITID (offered), **{r['offer_seamb']}** match "
      "multiple campus UNITIDs (system-vs-campus grain, **Seam B** — UNOFFERED, "
      "no forced pick; this is where the dollar-dominant giants land), "
      f"**{r['offer_none']}** have no FedSupport higher-ed match. **Per the "
      "ratified disposition these offers are NOT written into the HERD panel** "
      "— they record what the join would reach once the IPEDS #4 cycle "
      "resolves HERD's UNITIDs.")
    a("")
    a(f"If the single-candidate offers were backfilled into HERD, the FY2023 "
      f"dollar-match would rise from **{r['dollar_rate']:.1%}** to only "
      f"**{r['ceiling']:.1%}** (+{r['uplift']/r['anchor']:.1%}, "
      f"${r['uplift']:,.0f}K) — the clean backfill is small; the large recovery "
      "is gated behind the Seam-B campus resolution (IPEDS #4), not this offer.")
    a("")
    a("Top single-candidate backfill offers (HERD-NULL → FedSupport native UNITID):")
    a("")
    a("| HERD name (NULL UNITID) | Offered UNITID | FedSupport name |")
    a("|---|---|---|")
    singles = [b for b in backfill_rows if b["offer_status"] == "single_candidate"]
    for b in singles[:12]:
        a(f"| {b['herd_inst_name_long']} | {b['offered_ipeds_unitid']} | "
          f"{b['fedsupport_name']} |")
    a("")
    a("## 3. Scope guardrail (§4)")
    a("")
    a("Name-matching is retired for FedSupport↔IPEDS (native UNITID). The "
      "normalizer survives ONLY for the HERD-backfill offer (HERD-NULL rows "
      "carry no UNITID to key on). The spine is scoped to the active-survey "
      "set; comprehensive identity-over-time and the system→campus hierarchy "
      "(Seam B) remain the IPEDS-cycle deliverables — KILL-on-sight here.")
    write_text_clean(RECEIPT, "\n".join(A) + "\n")
    print(f"  wrote {RECEIPT}")


if __name__ == "__main__":
    sys.exit(main())
