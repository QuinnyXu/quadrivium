"""THROWAWAY (HD 3.2 finalization gate): run Vision's three finalization
checks (a)/(b)/(c) against the actual data. Budget: this spike, no production
code. Kill: if any check changes the structural reading, STOP and surface.

(a) 10.8% no-HERD-name tier: re-probe with the FULL in-scope name logic
    (exact + normalized + of-rule + flat-token-set) to confirm the unmatched
    research-orgs/system-offices genuinely have NO HERD counterpart the spine
    COULD match — not a normalization miss dressed as 'no name'. Report the
    recoverable dollar share (must be < ~5% of anchor to pass).

(b) 4 collision keys: confirm enumerable, not the visible edge of a systematic
    same-name collision class. Report the count + whether it generalizes.

(c) DISPOSITION-CHANGING: confirm the 7.9% NULL-UNITID tier genuinely needs
    IPEDS. For each era-B HERD institution behind the NULL-UNITID tier (Johns
    Hopkins, Ohio State, Texas A&M, Vanderbilt, UConn, Oregon State,
    Cincinnati, ...), check whether the UNITID is recoverable from an artifact
    HERD ALREADY has:
      - the SAME institution's OTHER era-B rows in herd_panel (any non-null
        ipeds_unitid on the same inst_id / ncses_inst_id / name?)
      - the personnel + attributes parquets (do they carry a non-null UNITID
        for that inst?)
      - the RAW era-B HERD files via the loader (standard + short form): does
        the raw NSF row itself emit a non-null ipeds_unitid the panel build
        dropped, OR is it genuinely NULL at source?
    If recoverable from already-present HERD artifacts -> HERD-side fix, NOT an
    IPEDS deferral -> STOP, surface.
"""
import sys
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "etl"))
import duckdb
from build_fedsupport_identity_spine import (flat_key, normalize, of_rule_key)
import _load  # the HERD raw loader

HERD = (ROOT / "data" / "harmonized" / "herd_panel.parquet").as_posix()
PERS = (ROOT / "data" / "harmonized" / "herd_personnel.parquet").as_posix()
ATTR = (ROOT / "data" / "harmonized" / "herd_panel_attributes.parquet").as_posix()
FED = (ROOT / "data" / "harmonized" / "fedsupport_obligations.parquet").as_posix()
ANCHOR = 48_961_658

con = duckdb.connect()

# ---- rebuild the union + match exactly as the spine does -------------------
fed = con.execute(
    f"SELECT year, state, institution_name_raw, value_kusd "
    f"FROM read_parquet('{FED}') WHERE activity_type='all_obligations'"
).fetchall()
union = {}
for y, st, nm, val in fed:
    rec = union.setdefault((nm, st), {"years": set(), "d2023": 0.0})
    rec["years"].add(y)
    if y == 2023:
        rec["d2023"] = val or 0.0

# HERD era-B name->unitid maps (non-null), and the FULL name set (incl null)
herd_full = con.execute(
    f"SELECT DISTINCT inst_name_long, ipeds_unitid, ncses_inst_id, institution_id "
    f"FROM read_parquet('{HERD}') WHERE era='B' AND inst_name_long IS NOT NULL"
).fetchall()

exact_map = defaultdict(set); norm_map = defaultdict(set)
ofrule_map = defaultdict(set); flat_map = defaultdict(set)
flat_any = defaultdict(set)          # flat_key -> set(name) over ALL era-B names
flat_to_uid_full = defaultdict(set)  # flat_key -> set(unitid) incl via other rows
for nm, uid, ncses, iid in herd_full:
    flat_any[flat_key(nm)].add(nm)
    if uid is not None:
        exact_map[nm.strip().lower()].add(uid)
        norm_map[normalize(nm)].add(uid)
        ofrule_map[of_rule_key(nm)].add(uid)
        flat_map[flat_key(nm)].add(uid)
        flat_to_uid_full[flat_key(nm)].add(uid)


def match(nm):
    ek = nm.strip().lower()
    if ek in exact_map:
        return (sorted(exact_map[ek])[0], "exact", len(exact_map[ek]))
    nk = normalize(nm)
    if nk in norm_map:
        return (sorted(norm_map[nk])[0], "normalized", len(norm_map[nk]))
    ok = of_rule_key(nm)
    if ok in ofrule_map and len(ofrule_map[ok]) == 1:
        return (sorted(ofrule_map[ok])[0], "of-rule", 1)
    fk = flat_key(nm)
    if fk in flat_map:
        if len(flat_map[fk]) == 1:
            return (sorted(flat_map[fk])[0], "flat-token-set", 1)
        return (None, "unresolved-collision", len(flat_map[fk]))
    return (None, "unresolved", 0)


# classify the FY2023 unmatched tail into the three tiers (mirror the build)
tier_null_unitid = []   # HERD name exists, has ncses/name but no usable unitid
tier_no_name = []       # no HERD era-B name at all (the 10.8% tier)
for (nm, st), rec in union.items():
    if 2023 not in rec["years"]:
        continue
    uid, method, ncand = match(nm)
    if uid is not None:
        continue
    d = rec["d2023"]
    fk = flat_key(nm)
    if fk in flat_any:        # HERD has the NAME, just no usable unitid
        tier_null_unitid.append((nm, st, d, method))
    else:
        tier_no_name.append((nm, st, d, method))

print("=" * 74)
print("CHECK (a) — 10.8% no-HERD-name tier: hidden in-scope recoverable?")
print("=" * 74)
# Re-probe the no-name tier with the FULL in-scope name logic, but this time
# also test a SUBSET relationship (fed tokens subset of a HERD name w/ unitid)
# — the same 'recoverable' notion used in the build's gate-evidence pass, to catch a
# normalization miss dressed as 'no name'. A TRUE in-scope recoverable = a
# UNIQUE HERD name (with non-null unitid) the spine's 4 layers should have hit
# but didn't.
herd_uid_rows = [(flat_key(nm), nm, uid) for nm, uid, _, _ in herd_full
                 if uid is not None]
recoverable_d = 0.0; recoverable = []
ambiguous_d = 0.0; ambiguous = []
truly_no_match_d = 0.0; truly_no_match_n = 0
no_name_total_d = sum(d for _, _, d, _ in tier_no_name)
for nm, st, d, method in tier_no_name:
    fk = flat_key(nm)
    # exact in-scope-layer re-probe already failed (method=unresolved). Now the
    # generous subset probe: fed tokens subset of a herd-with-unitid name.
    cands = [(len(fk) / len(hk), hnm, uid) for hk, hnm, uid in herd_uid_rows
             if fk and fk <= hk and len(hk) - len(fk) <= 2]
    uniq_uids = {u for _, _, u in cands}
    if len(uniq_uids) == 1:
        recoverable_d += d
        recoverable.append((d, nm, st, cands[0][1]))
    elif len(uniq_uids) > 1:
        ambiguous_d += d
        ambiguous.append((d, nm, st))
    else:
        truly_no_match_d += d
        truly_no_match_n += 1
print(f"  no-name tier total: {no_name_total_d:,.0f} kUSD "
      f"({no_name_total_d/ANCHOR:.1%} of anchor)")
print(f"  -> in-scope RECOVERABLE (unique HERD-w-unitid subset cand): "
      f"{len(recoverable)} insts  {recoverable_d:,.0f} "
      f"({recoverable_d/ANCHOR:.1%})  <== must be < ~5% to PASS")
print(f"  -> AMBIGUOUS (multi-campus, grain, NOT a normalization miss): "
      f"{len(ambiguous)} insts  {ambiguous_d:,.0f} ({ambiguous_d/ANCHOR:.1%})")
print(f"  -> genuinely no HERD counterpart: {truly_no_match_n} insts "
      f"{truly_no_match_d:,.0f} ({truly_no_match_d/ANCHOR:.1%})")
print("  top in-scope recoverable candidates (if any):")
for d, nm, st, hnm in sorted(recoverable, reverse=True)[:10]:
    print(f"    {d:>11,.0f} [{st}] {nm!r} -> {hnm!r}")
check_a_pass = (recoverable_d / ANCHOR) < 0.05
print(f"  CHECK (a) {'PASS' if check_a_pass else 'FAIL'}: recoverable "
      f"{recoverable_d/ANCHOR:.1%} {'<' if check_a_pass else '>='} 5%")

print()
print("=" * 74)
print("CHECK (b) — 4 collision keys: enumerable, or systematic same-name class?")
print("=" * 74)
collisions = []
for fk, uids in flat_map.items():
    if len(uids) > 1:
        names = sorted(flat_any.get(fk, set()))
        collisions.append((fk, sorted(uids), names))
# Also count: how many DISTINCT flat-keys in the whole HERD era-B set collide
# (the systematic-class denominator) vs how many the FedSupport union actually
# HITS as unresolved-collision.
fed_hit_collisions = []
for (nm, st), rec in union.items():
    if 2023 not in rec["years"]:
        continue
    uid, method, ncand = match(nm)
    if method == "unresolved-collision":
        fed_hit_collisions.append((nm, st, normalize(nm), ncand))
print(f"  HERD-side flat-key collisions (>1 unitid on one key), total: "
      f"{len(collisions)}")
for fk, uids, names in collisions[:20]:
    print(f"    {sorted(fk)} -> {uids}  names={names}")
print(f"  FedSupport-union keys hitting a collision (unresolved-collision): "
      f"{len(fed_hit_collisions)}")
for nm, st, nk, n in fed_hit_collisions:
    print(f"    [{st}] {nm!r} norm={nk!r} -> {n} UNITIDs")
check_b_pass = len(fed_hit_collisions) <= 8 and len(collisions) <= 12
print(f"  CHECK (b) {'PASS' if check_b_pass else 'REVIEW'}: "
      f"{len(fed_hit_collisions)} fed-hit collisions, {len(collisions)} "
      f"herd-side collision keys total — "
      f"{'enumerable watch-list' if check_b_pass else 'CHECK systematic'}")

print()
print("=" * 74)
print("CHECK (c) — DISPOSITION-CHANGING: does the NULL-UNITID tier need IPEDS,")
print("            or is the UNITID recoverable from artifacts HERD ALREADY has?")
print("=" * 74)
null_total_d = sum(d for _, _, d, _ in tier_null_unitid)
print(f"  NULL-UNITID tier total: {len(tier_null_unitid)} insts  "
      f"{null_total_d:,.0f} kUSD ({null_total_d/ANCHOR:.1%} of anchor)")
print()
# C1: does the SAME institution (by flat_key) carry a non-null unitid on ANY
# OTHER era-B row in the panel? (i.e. did the build drop it on some rows?)
print("  [C1] Same flat-key with a non-null unitid ANYWHERE in herd_panel "
      "era-B?")
c1_recoverable = 0.0; c1_hits = []
for nm, st, d, method in tier_null_unitid:
    fk = flat_key(nm)
    if fk in flat_to_uid_full and len(flat_to_uid_full[fk]) >= 1:
        c1_recoverable += d
        c1_hits.append((d, nm, st, sorted(flat_to_uid_full[fk])))
if c1_hits:
    for d, nm, st, uids in sorted(c1_hits, reverse=True)[:15]:
        print(f"    RECOVERABLE {d:>11,.0f} [{st}] {nm!r} -> {uids}")
else:
    print("    none — no NULL-UNITID-tier institution has a non-null unitid on "
          "any other era-B panel row (flat-key).")
print(f"    C1 recoverable from panel itself: {c1_recoverable:,.0f} "
      f"({c1_recoverable/ANCHOR:.1%})")
print()

# C2: do personnel / attributes parquets carry a non-null unitid for the
# NULL-UNITID-tier institutions? Build their name->unitid maps.
def name_uid_map(path, name_col, has_era=True):
    cols = con.execute(f"DESCRIBE SELECT * FROM read_parquet('{path}')").fetchall()
    colnames = {c[0] for c in cols}
    if "ipeds_unitid" not in colnames or name_col not in colnames:
        return None, colnames
    where = "WHERE ipeds_unitid IS NOT NULL"
    rows = con.execute(
        f"SELECT DISTINCT {name_col}, ipeds_unitid FROM read_parquet('{path}') "
        f"{where}"
    ).fetchall()
    m = defaultdict(set)
    for nm, uid in rows:
        if nm is not None:
            m[flat_key(nm)].add(uid)
    return m, colnames

for label, path, ncol in [("personnel", PERS, "inst_name_long"),
                          ("attributes", ATTR, "inst_name_long")]:
    # try common name columns
    desc = con.execute(f"DESCRIBE SELECT * FROM read_parquet('{path}')").fetchall()
    cnames = [c[0] for c in desc]
    name_col = next((c for c in ("inst_name_long", "institution_name",
                                 "inst_name") if c in cnames), None)
    print(f"  [C2/{label}] cols={cnames}")
    if name_col is None or "ipeds_unitid" not in cnames:
        print(f"    -> no usable (name, ipeds_unitid) pair; skip")
        continue
    m, _ = name_uid_map(path, name_col)
    rec = 0.0; hits = []
    for nm, st, d, method in tier_null_unitid:
        fk = flat_key(nm)
        if fk in m and m[fk]:
            rec += d
            hits.append((d, nm, st, sorted(m[fk])))
    for d, nm, st, uids in sorted(hits, reverse=True)[:10]:
        print(f"    RECOVERABLE {d:>11,.0f} [{st}] {nm!r} -> {uids}")
    print(f"    {label} recoverable: {rec:,.0f} ({rec/ANCHOR:.1%})")
print()

# C3: the RAW era-B HERD files — does the raw NSF row itself emit a non-null
# ipeds_unitid the panel build dropped, or is it genuinely NULL at source?
# Direct raw probe via the project loader (read_herd_csv per year) for FY2023.
print("  [C3] RAW era-B HERD file (FY2023, standard form via _load."
      "read_herd_csv): is ipeds_unitid genuinely NULL AT SOURCE for the")
print("       NULL-UNITID-tier institutions (Johns Hopkins et al.)?")
try:
    rel = _load.read_herd_csv(2023, con)
    # read_herd_csv returns a DuckDBPyRelation; materialize then query.
    rel.create("raw_b_2023")
    probe = con.execute(
        """SELECT inst_name_long,
                  COUNT(*) AS n_rows,
                  COUNT(ipeds_unitid) AS n_nonnull_uid
           FROM raw_b_2023
           WHERE inst_name_long ILIKE '%Johns Hopkins%'
              OR inst_name_long ILIKE '%Ohio State%'
              OR inst_name_long ILIKE '%Texas A&M%College Station%'
              OR inst_name_long ILIKE '%Vanderbilt%'
              OR inst_name_long ILIKE '%Connecticut%'
              OR inst_name_long ILIKE '%Oregon State%'
              OR inst_name_long ILIKE '%Cincinnati%'
           GROUP BY 1 ORDER BY 2 DESC"""
    ).fetchall()
    print("    RAW FY2023 (name, n_rows, n_nonnull_ipeds_unitid):")
    for nm, n, nn in probe:
        flag = "GENUINELY NULL at source" if nn == 0 else f"** HAS {nn} **"
        print(f"      {nn:>4}/{n:<4} {nm!r}  -> {flag}")
except Exception as e:
    print(f"    raw probe failed ({e!r}); relying on panel-passthrough audit "
          f"below (build passes ipeds_unitid verbatim, _load.py:530).")

print()
print("  [C3-fallback] Per-institution raw NULL audit via herd_panel era-B:")
print("    For each NULL-UNITID-tier inst, count era-B panel rows and how many")
print("    carry a non-null ipeds_unitid (0 of N => genuinely NULL at source,")
print("    since the build passes ipeds_unitid through verbatim, _load.py:530).")
# group herd_panel era-B by flat_key over the FULL set, count null vs non-null
grp = con.execute(
    f"""SELECT inst_name_long, institution_id, ncses_inst_id,
               COUNT(*) AS n_rows,
               COUNT(ipeds_unitid) AS n_nonnull_uid
        FROM read_parquet('{HERD}') WHERE era='B' AND inst_name_long IS NOT NULL
        GROUP BY 1,2,3"""
).fetchall()
fk_cov = defaultdict(lambda: [0, 0])
for nm, iid, ncses, n, nn in grp:
    fk = flat_key(nm)
    fk_cov[fk][0] += n
    fk_cov[fk][1] += nn
genuinely_null_d = 0.0; genuinely_null_n = 0
for nm, st, d, method in sorted(tier_null_unitid, key=lambda x: -x[2])[:15]:
    fk = flat_key(nm)
    n, nn = fk_cov.get(fk, [0, 0])
    flag = "GENUINELY NULL" if nn == 0 else f"** HAS {nn} non-null **"
    print(f"    {d:>11,.0f} [{st}] {nm!r}: {n} era-B rows, "
          f"{nn} non-null unitid  -> {flag}")
for nm, st, d, method in tier_null_unitid:
    fk = flat_key(nm)
    n, nn = fk_cov.get(fk, [0, 0])
    if nn == 0:
        genuinely_null_d += d
        genuinely_null_n += 1
print(f"\n    genuinely-NULL-at-source (0 non-null on ANY era-B row): "
      f"{genuinely_null_n}/{len(tier_null_unitid)} insts  "
      f"{genuinely_null_d:,.0f} ({genuinely_null_d/ANCHOR:.1%})")
recoverable_c = null_total_d - genuinely_null_d
print(f"    => potentially HERD-side recoverable (has non-null somewhere): "
      f"{recoverable_c:,.0f} ({recoverable_c/ANCHOR:.1%})")
check_c_needs_ipeds = (recoverable_c / ANCHOR) < 0.005  # <0.5% = trivially nil
print(f"  CHECK (c) {'PASS (genuinely needs IPEDS)' if check_c_needs_ipeds else 'STOP — HERD-SIDE RECOVERABLE'}: "
      f"{recoverable_c/ANCHOR:.2%} recoverable from already-present HERD artifacts")

print()
print("=" * 74)
print("GATE SUMMARY")
print("=" * 74)
print(f"  (a) no-name recoverable {recoverable_d/ANCHOR:.1%} "
      f"-> {'PASS' if check_a_pass else 'FAIL'}")
print(f"  (b) fed-hit collisions {len(fed_hit_collisions)}, herd-side "
      f"{len(collisions)} -> {'PASS' if check_b_pass else 'REVIEW'}")
print(f"  (c) HERD-side recoverable {recoverable_c/ANCHOR:.2%} -> "
      f"{'PASS (needs IPEDS)' if check_c_needs_ipeds else 'STOP'}")
gate = check_a_pass and check_b_pass and check_c_needs_ipeds
print(f"\n  GATE: {'PASS — structural reading holds' if gate else 'CHANGED — surface'}")
