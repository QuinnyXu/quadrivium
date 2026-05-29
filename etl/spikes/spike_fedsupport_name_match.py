"""
etl/spikes/spike_fedsupport_name_match.py — THROWAWAY SPIKE (HD 3.2 §11).

Name-match de-risking spike for the Federal S&E Support module's
institution-identity spine. Points at ONE number (the RAW normalized
match yield, no manual resolution) + tests ONE edge (the city
disambiguator, hidden-edge §8.2), then STOPS at the finding.

THROWAWAY. Does NOT promote to production. HD 3.2 MVP consumes the
FINDINGS (validation/reports/fedsupport/hd_3_2_name_match_spike_findings.md),
not this code. Budget: 3 half-days, kill at 3.

What it does
------------
1. Obtain FY2023 Table 12 xlsx (HD 3.1 §7 stable URL); verify SHA-256 ==
   dea92dce...b73c7. Reuse gitignored gate scratch if present.
2. Parse Column A into (state, institution_name_raw) WITHOUT a row-type
   column — positional-hierarchy edge (§8.1). Isolate institution rows.
3. First-pass NSF-abbreviation normalizer that PRESERVES the city suffix
   as a disambiguator (do NOT collapse it).
4. Match against the era-B HERD UNITID set (era=='B', distinct
   (inst_name_long, ipeds_unitid)) from data/harmonized/herd_panel.parquet.
   Exact + normalized match. RAW yield (no manual resolution).

Two principal-ratified additions (both mandatory)
-------------------------------------------------
ADD 1: report the raw normalized-match NUMBER (institution-match count/rate
       AND dollar-match rate = matched institutions' "All federal
       obligations" / the $48,961,658K FY2023 anchor). The dollar rate is
       the thread-critical one and diverges from the institution rate.
ADD 2: explicitly test the city-disambiguator edge. Confirm same-name /
       different-city institutions (e.g. U. Alabama, The, Birmingham vs.
       Tuscaloosa) resolve to DISTINCT UNITIDs, not silent-merged. Scan
       for ALL same-name-different-city groups; report any collapse.

Reading xlsx via the DuckDB `excel` extension is FINE here (throwaway
spike; the §3 no-runtime-extension lock binds only the deposit build).

Author: Skipper, 2026-05-29 (HD 3.2 spike). Throwaway.
"""

from __future__ import annotations

import hashlib
import re
import sys
import urllib.request
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent.parent
SCRATCH = ROOT / "etl" / "spikes" / "_fedsupport_scratch"
SCRATCH.mkdir(parents=True, exist_ok=True)

HERD_PARQUET = ROOT / "data" / "harmonized" / "herd_panel.parquet"

# HD 3.1 §7 stable URL + gate-recorded hash + anchor.
FY2023_XLSX_URL = (
    "https://ncses.nsf.gov/pubs/nsf25339/assets/data-tables/tables/nsf25339-tab012.xlsx"
)
FY2023_SHA256 = "dea92dcecb94ba72333c5dd39b6a8b4c0046124b9e135bea01a30ac94c5b73c7"
FY2023_ANCHOR_KUSD = 48_961_658  # higher-ed-only grand total (HD 3.1 §2)
UA = "quadrivium-skipper-spike/1.0 (research; HD3.2 name-match)"

# U.S. states + DC + outlying areas as they head Column A in Table 12.
# Used to distinguish state-header rows from institution rows positionally
# (§8.1: no row-type column). The grand-total row is its own literal.
GRAND_TOTAL_LABEL = "All states and outlying areas"
STATE_NAMES = {
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado",
    "Connecticut", "Delaware", "District of Columbia", "Florida", "Georgia",
    "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky",
    "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota",
    "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada",
    "New Hampshire", "New Jersey", "New Mexico", "New York", "North Carolina",
    "North Dakota", "Ohio", "Oklahoma", "Oregon", "Pennsylvania",
    "Rhode Island", "South Carolina", "South Dakota", "Tennessee", "Texas",
    "Utah", "Vermont", "Virginia", "Washington", "West Virginia", "Wisconsin",
    "Wyoming",
    # Outlying areas / territories that appear in NCSES state-grouping headers.
    "American Samoa", "Guam", "Northern Mariana Islands", "Puerto Rico",
    "U.S. Virgin Islands", "Virgin Islands", "Federated States of Micronesia",
    "Marshall Islands", "Palau",
}


# --------------------------------------------------------------------------
# 1. Obtain FY2023 Table 12 xlsx + verify SHA-256.
# --------------------------------------------------------------------------
def fetch(url: str) -> bytes | None:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.read()
    except Exception as e:  # noqa: BLE001
        print(f"  FETCH-FAIL {url}\n    {type(e).__name__}: {e}")
        return None


def obtain_xlsx() -> Path | None:
    xp = SCRATCH / "nsf25339-tab012-FY2023.xlsx"
    if xp.exists():
        h = hashlib.sha256(xp.read_bytes()).hexdigest()
        if h == FY2023_SHA256:
            print(f"  reused gate scratch: {xp.name} (SHA-256 OK)")
            return xp
        print(f"  scratch hash mismatch ({h[:12]}...), re-fetching")
    b = fetch(FY2023_XLSX_URL)
    if b is None:
        return None
    h = hashlib.sha256(b).hexdigest()
    if h != FY2023_SHA256:
        print(f"  SHA-256 MISMATCH: got {h}\n    expected {FY2023_SHA256}")
        return None
    xp.write_bytes(b)
    print(f"  fetched + staged {xp.name} ({len(b):,} bytes), SHA-256 OK")
    return xp


# --------------------------------------------------------------------------
# 2. Parse Column A into (state, institution_name_raw) — positional hierarchy.
# --------------------------------------------------------------------------
def load_raw_rows(con: duckdb.DuckDBPyConnection, xlsx: Path):
    """Return list of (labelA, all_fed_obligations_kusd) for every data row,
    raw, in sheet order. all_varchar so we keep the band intact."""
    p = xlsx.as_posix()
    # NOTE (spike finding): without an explicit `range`, the DuckDB excel
    # extension auto-detects only column A (the one-cell title band in A1
    # makes it infer a 1-col sheet) and DROPS every value column. An explicit
    # wide range over all rows is required to read B..G. Table 12 has ~1,171
    # rows; A1:G1200 covers it with headroom.
    con.execute(
        f"CREATE OR REPLACE TABLE raw AS "
        f"SELECT * FROM read_xlsx('{p}', header=false, all_varchar=true, "
        f"range='A1:G1200', stop_at_empty=false)"
    )
    cols = [r[0] for r in con.execute("DESCRIBE raw").fetchall()]
    rows = con.execute("SELECT * FROM raw").fetchall()
    return cols, rows


def _to_kusd(cell) -> float | None:
    if cell is None:
        return None
    s = str(cell).strip().replace(",", "")
    if s in ("", "-", "na", "NA", "n/a"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def parse_institution_rows(cols, rows):
    """Positionally distinguish grand-total / state-header / institution rows
    WITHOUT a row-type column (§8.1). Column A is rows[i][0]; the
    'All federal obligations' value is the first numeric column after A.

    Heuristic:
      - find the header row (the one whose col A == 'State, outlying area,
        and institution') to locate the value-column index;
      - the grand-total row is labelA == 'All states and outlying areas';
      - a row whose labelA (trimmed) is in STATE_NAMES is a state header;
      - every other row that carries a numeric 'All federal obligations'
        value and a non-empty label is an institution row, tagged with the
        most-recent state header seen above it.
    """
    # locate the 'All federal obligations' column index from the header band
    val_idx = None
    header_row_i = None
    for i, r in enumerate(rows):
        a = "" if r[0] is None else str(r[0]).strip()
        if a.lower().startswith("state, outlying area"):
            header_row_i = i
            # 'All federal obligations' is the first value column = col index 1
            # (col A is the label). Confirm by finding the header text.
            for j in range(1, len(r)):
                hj = "" if r[j] is None else str(r[j]).strip().lower()
                if "all federal" in hj:
                    val_idx = j
                    break
            if val_idx is None:
                val_idx = 1  # fallback: first column after label
            break
    if val_idx is None:
        val_idx = 1
        header_row_i = -1

    institutions = []  # (state, name_raw, all_fed_kusd)
    grand_total = None
    cur_state = None
    n_state_headers = 0
    start = (header_row_i + 1) if header_row_i is not None else 0
    for r in rows[start:]:
        a = "" if r[0] is None else str(r[0]).strip()
        if not a:
            continue
        val = _to_kusd(r[val_idx]) if val_idx < len(r) else None
        if a == GRAND_TOTAL_LABEL:
            grand_total = val
            continue
        if a in STATE_NAMES:
            cur_state = a
            n_state_headers += 1
            continue
        # institution row: has a label, carries a numeric obligation, and is
        # under a state header. (Rows with no numeric value are footnotes.)
        if val is None:
            continue
        institutions.append((cur_state, a, val))
    return institutions, grand_total, n_state_headers, val_idx


# --------------------------------------------------------------------------
# 3. Normalizer — PRESERVE the city suffix as a disambiguator.
# --------------------------------------------------------------------------
def normalize(name: str) -> str:
    """First-pass NSF-abbreviation normalizer. Expands the house-style
    abbreviations and strips ', The' / punctuation noise, but EXPLICITLY
    KEEPS the trailing city/campus token (it is load-bearing for
    multi-campus disambiguation, §8.2). Returns a casefolded key with the
    city token preserved as the last comma-segment.
    """
    s = name.strip()
    # strip a trailing ', The' or leading 'The '
    s = re.sub(r",\s*The\b", "", s, flags=re.IGNORECASE)
    s = re.sub(r"^The\s+", "", s, flags=re.IGNORECASE)

    # Split into name-part and (optional) city/campus suffix. NSF style puts
    # the campus city AFTER the institution as the last comma segment, e.g.
    # 'U. Alabama, Birmingham' / 'Auburn U., Auburn'. We keep the last
    # comma-segment as the disambiguator token and normalize the head.
    parts = [p.strip() for p in s.split(",") if p.strip()]
    head = parts[0] if parts else s
    suffix = parts[-1] if len(parts) > 1 else ""

    head = _expand_abbrevs(head)
    suffix_n = _norm_token(suffix)
    head_n = _norm_token(head)
    if suffix_n and suffix_n != head_n:
        return f"{head_n}|{suffix_n}"
    return head_n


# NSF house-style abbreviation expansions (first pass; not exhaustive — the
# spike measures RAW yield, the manual tail is the MVP artifact).
_ABBREV = [
    (r"\bU\.\s*", "university "),         # 'U. Alabama' / 'Auburn U.'
    (r"\bUniv\.?\b", "university"),
    (r"\bColl\.?\b", "college"),
    (r"\bInst\.?\b", "institute"),
    (r"\bTech\.?\b", "technology"),
    (r"\bTechnol\.?\b", "technology"),
    (r"\bSt\.\s*", "saint "),             # 'St. John's' -> 'saint johns'
    (r"\bA&M\b", "a m"),
    (r"\bA & M\b", "a m"),
    (r"\bSci\.?\b", "science"),
    (r"\bMed\.?\b", "medical"),
    (r"\bCtr\.?\b", "center"),
    (r"\bSys\.?\b", "system"),
    (r"\bN\.\s*", "north "),
    (r"\bS\.\s*", "south "),
    (r"\bE\.\s*", "east "),
    (r"\bW\.\s*", "west "),
]


def _expand_abbrevs(s: str) -> str:
    out = " " + s + " "
    for pat, rep in _ABBREV:
        out = re.sub(pat, rep, out, flags=re.IGNORECASE)
    return out.strip()


def _norm_token(s: str) -> str:
    s = s.lower()
    s = s.replace("&", " and ")
    s = re.sub(r"[^\w\s]", " ", s)        # drop punctuation (apostrophes etc.)
    s = re.sub(r"\s+", " ", s).strip()
    # drop a leading 'the' that survived
    s = re.sub(r"^the\s+", "", s)
    return s


# --------------------------------------------------------------------------
# 4. Match against era-B HERD UNITID set.
# --------------------------------------------------------------------------
def load_herd_unitid_set(con: duckdb.DuckDBPyConnection):
    """era-B distinct (inst_name_long, ipeds_unitid). Returns:
      exact_map: lower(raw inst_name_long) -> set(unitid)
      norm_map:  normalize(inst_name_long) -> set(unitid)
    """
    p = HERD_PARQUET.as_posix()
    pairs = con.execute(
        f"""SELECT DISTINCT inst_name_long, ipeds_unitid
            FROM read_parquet('{p}')
            WHERE era='B' AND ipeds_unitid IS NOT NULL
              AND inst_name_long IS NOT NULL"""
    ).fetchall()
    exact_map: dict[str, set] = {}
    norm_map: dict[str, set] = {}
    for name, unitid in pairs:
        exact_map.setdefault(name.strip().lower(), set()).add(unitid)
        norm_map.setdefault(normalize(name), set()).add(unitid)
    return exact_map, norm_map, len(pairs)


def match(name_raw, exact_map, norm_map):
    """Return (unitid_or_None, method). Exact first, then normalized.
    If a key maps to >1 unitid we record it but pick deterministically
    (sorted first) — and the caller flags multi-unitid keys as a hazard."""
    ekey = name_raw.strip().lower()
    if ekey in exact_map:
        s = exact_map[ekey]
        return (sorted(s)[0], "exact", len(s))
    nkey = normalize(name_raw)
    if nkey in norm_map:
        s = norm_map[nkey]
        return (sorted(s)[0], "normalized", len(s))
    return (None, "unmatched", 0)


# --------------------------------------------------------------------------
# ADDITION 2 — city-disambiguator edge test.
# --------------------------------------------------------------------------
def _name_head_key(name_raw: str) -> str:
    """The normalized HEAD only (no city suffix) — used to GROUP
    same-name-different-city institutions on the FedSupport side."""
    s = re.sub(r",\s*The\b", "", name_raw.strip(), flags=re.IGNORECASE)
    parts = [p.strip() for p in s.split(",") if p.strip()]
    head = parts[0] if parts else s
    return _norm_token(_expand_abbrevs(head))


def city_disambiguator_test(institutions, exact_map, norm_map):
    """Find FedSupport same-name-different-city groups (>=2 distinct city
    suffixes sharing a normalized head). For each group, confirm the members
    normalize to DISTINCT keys AND (when matched) land on DISTINCT UNITIDs.
    Report any collapse (two distinct-city rows -> one key or one UNITID)."""
    from collections import defaultdict

    groups = defaultdict(list)  # head_key -> list of (state, name_raw, val)
    for st, nm, val in institutions:
        # only group rows that actually carry a city suffix (a comma segment)
        if "," in nm.replace(", The", "").replace(",The", ""):
            groups[_name_head_key(nm)].append((st, nm, val))

    multi = {k: v for k, v in groups.items()
             if len({m[1] for m in v}) >= 2}  # >=2 distinct raw names

    findings = []  # dicts per group
    for head, members in sorted(multi.items()):
        rows = []
        norm_keys = {}
        unitids = {}
        for st, nm, val in members:
            nk = normalize(nm)
            uid, meth, mult = match(nm, exact_map, norm_map)
            rows.append((st, nm, nk, uid, meth, mult))
            norm_keys.setdefault(nk, []).append(nm)
            if uid is not None:
                unitids.setdefault(uid, []).append(nm)
        norm_collapse = any(len(v) >= 2 for v in norm_keys.values())
        unitid_collapse = any(len(v) >= 2 for v in unitids.values())
        findings.append({
            "head": head,
            "rows": rows,
            "norm_collapse": norm_collapse,
            "unitid_collapse": unitid_collapse,
        })
    return findings


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
def main() -> int:
    print("=" * 72)
    print("HD 3.2 SPIKE — Federal S&E Support name-match yield + city edge")
    print("=" * 72)

    if not HERD_PARQUET.exists():
        print(f"FINDING: HERD parquet missing at {HERD_PARQUET} — cannot match.")
        return 2

    xlsx = obtain_xlsx()
    if xlsx is None:
        print("FINDING: FY2023 Table 12 xlsx could not be obtained/verified. "
              "Network fetch blocked or hash mismatch — reporting as the "
              "finding, not working around it.")
        return 2

    con = duckdb.connect()
    try:
        con.execute("INSTALL excel")
        con.execute("LOAD excel")
    except Exception as e:  # noqa: BLE001
        print(f"FINDING: duckdb excel extension unavailable: "
              f"{type(e).__name__}: {e}")
        return 2

    cols, rows = load_raw_rows(con, xlsx)
    institutions, grand_total, n_states, val_idx = parse_institution_rows(cols, rows)
    n_inst = len(institutions)
    print(f"\n--- PARSE (positional hierarchy, §8.1) ---")
    print(f"  value column index (All federal obligations): {val_idx}")
    print(f"  state-header rows seen:        {n_states}")
    print(f"  grand-total row value (kUSD):  {grand_total:,.0f}"
          if grand_total else "  grand-total row value: NOT FOUND")
    print(f"  institution rows isolated:     {n_inst}  (sanity vs ~1,110)")
    inst_dollar_sum = sum(v for _, _, v in institutions)
    print(f"  sum of institution obligations: {inst_dollar_sum:,.0f} kUSD "
          f"(vs anchor {FY2023_ANCHOR_KUSD:,})")

    exact_map, norm_map, n_herd_pairs = load_herd_unitid_set(con)
    print(f"\n--- HERD era-B match target ---")
    print(f"  era-B distinct (inst_name_long, unitid) pairs: {n_herd_pairs}")
    print(f"  distinct exact keys: {len(exact_map)}  "
          f"distinct normalized keys: {len(norm_map)}")

    # --- RAW match (ADDITION 1) ---
    matched_inst = 0
    matched_dollars = 0.0
    n_exact = n_norm = n_unmatched = 0
    multi_unitid_keys = 0
    for st, nm, val in institutions:
        uid, meth, mult = match(nm, exact_map, norm_map)
        if uid is not None:
            matched_inst += 1
            matched_dollars += val
            if meth == "exact":
                n_exact += 1
            else:
                n_norm += 1
            if mult > 1:
                multi_unitid_keys += 1
        else:
            n_unmatched += 1

    inst_rate = matched_inst / n_inst if n_inst else 0.0
    dollar_rate = matched_dollars / FY2023_ANCHOR_KUSD if FY2023_ANCHOR_KUSD else 0.0

    print(f"\n--- RAW NORMALIZED-MATCH YIELD (no manual resolution) ---")
    print(f"  matched institutions: {matched_inst} / {n_inst}  "
          f"= {inst_rate:6.1%}   (exact={n_exact}, normalized={n_norm})")
    print(f"  unmatched institutions: {n_unmatched}")
    print(f"  matched dollars: {matched_dollars:,.0f} / {FY2023_ANCHOR_KUSD:,} "
          f"= {dollar_rate:6.1%}   <-- thread-critical")
    print(f"  match keys hitting >1 UNITID (hazard flag): {multi_unitid_keys}")

    # --- city-disambiguator edge (ADDITION 2) ---
    print(f"\n--- CITY-DISAMBIGUATOR EDGE TEST (§8.2) ---")
    cd = city_disambiguator_test(institutions, exact_map, norm_map)
    print(f"  same-name-different-city groups found: {len(cd)}")
    any_collapse = False
    for g in cd:
        flag = ""
        if g["norm_collapse"] or g["unitid_collapse"]:
            any_collapse = True
            flag = "  <<< COLLAPSE"
        print(f"  group head='{g['head']}'  "
              f"norm_collapse={g['norm_collapse']} "
              f"unitid_collapse={g['unitid_collapse']}{flag}")
        for st, nm, nk, uid, meth, mult in g["rows"]:
            print(f"      [{st}] {nm!r}")
            print(f"          norm_key={nk!r}  unitid={uid}  ({meth})")
    if not any_collapse:
        print("  RESULT: no collapses — distinct cities -> distinct keys/UNITIDs.")
    else:
        print("  RESULT: COLLAPSE(S) FOUND — see flagged groups above (LOUD).")

    # --- SECOND-PASS diagnostic (sizes verdict: thin-normalizer vs ceiling) ---
    # Still mechanical (no manual resolution): match on a token-SET head with
    # stopwords {of,the,at,in,and} dropped, city token preserved. This closes
    # the NSF 'U. X' vs HERD 'University of X' word-order gap that the
    # first-pass exact-string key cannot. Reported so the verdict distinguishes
    # "first-pass normalizer too thin" (recoverable) from "true ~35% ceiling".
    def _tokenset_key(name: str):
        k = normalize(name)
        head, city = (k.split("|", 1) + [""])[:2] if "|" in k else (k, "")
        stop = {"of", "the", "at", "in", "and"}
        return (frozenset(t for t in head.split() if t not in stop), city)

    herd2: dict = {}
    p = HERD_PARQUET.as_posix()
    for nm_h, uid_h in con.execute(
        f"""SELECT DISTINCT inst_name_long, ipeds_unitid FROM read_parquet('{p}')
            WHERE era='B' AND ipeds_unitid IS NOT NULL
              AND inst_name_long IS NOT NULL"""
    ).fetchall():
        herd2.setdefault(_tokenset_key(nm_h), set()).add(uid_h)
    m2 = 0
    d2 = 0.0
    coll2 = 0
    for st, nm, val in institutions:
        k2 = _tokenset_key(nm)
        if k2 in herd2:
            m2 += 1
            d2 += val
            if len(herd2[k2]) > 1:
                coll2 += 1
    print(f"\n--- SECOND-PASS (token-set head, stopword-drop, city kept) ---")
    print(f"  matched institutions: {m2} / {n_inst} = {m2/n_inst:.1%}")
    print(f"  matched dollars: {d2:,.0f} / {FY2023_ANCHOR_KUSD:,} "
          f"= {d2/FY2023_ANCHOR_KUSD:.1%}")
    print(f"  token-set keys hitting >1 UNITID (collision hazard): {coll2}")

    # explicit Alabama probe (named in the spike spec)
    print(f"\n  explicit U. Alabama probe:")
    for st, nm, val in institutions:
        if _name_head_key(nm).startswith("university alabama"):
            uid, meth, mult = match(nm, exact_map, norm_map)
            print(f"    [{st}] {nm!r} -> norm={normalize(nm)!r} "
                  f"unitid={uid} ({meth})")

    # --- branch verdict ---
    print(f"\n" + "=" * 72)
    floor = 0.60
    if inst_rate < floor:
        print(f"BRANCH: raw institution match {inst_rate:.1%} < 60% floor "
              f"-> SURFACE TO VISION (manual tail exceeds ~2x budget).")
    else:
        print(f"BRANCH: raw institution match {inst_rate:.1%} >= 60% floor "
              f"-> MVP GREENLIGHTS, sized to yield.")
    print(f"  (dollar match {dollar_rate:.1%}; city collapses: "
          f"{'YES' if any_collapse else 'none'})")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
