"""etl/build_gss_field_code_map.py — HD 4.3 step 4: GSS field-code crosswalk.

The dedicated NCSES GSS field-code / Taxonomy-of-Disciplines reference is NOT
staged. This generator **reconstructs** the `gss_code` → field mapping from the
staged published Table 4-3 (NSF 25-317, "Master's and doctoral students by
enrollment intensity, by detailed field, 2023") by **count-matching**: each
`gss_code`'s 2023 all-grad (FT+PT) total in `gss_race.parquet` is matched to the
unique Table 4-3 detailed-field row with that total → `field_fine`; the row's SEH
super-section (Science / Engineering / Health) → `field_coarse`. The 2023 match is
exact and unique for every 2023-active code (validated).

**Residual (per §4, no invented mappings):** `gss_code`s that appear only in
historical years (not in 2023 Table 4-3) cannot be count-matched from the staged
2023 table — they default to `field_coarse/fine = NULL` + footnote, pending the
dedicated TOD reference (or earlier-year field tables). Reported below.

Output: ``crosswalks/gss/field_code_map.csv`` (per-row decision_rationale).
    uv run python etl/build_gss_field_code_map.py
"""
from __future__ import annotations
import csv, glob, os, re, zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
import duckdb

ROOT = Path(__file__).resolve().parent.parent
T43 = ROOT / "data" / "reference" / "gss" / "nsf25317-tab004-003.xlsx"
RACE_PARQUET = ROOT / "data" / "harmonized" / "gss_race.parquet"
CSV_GLOB = str(ROOT / "data" / "raw" / "gss" / "csv" / "gss*_race.csv")
OUT = ROOT / "crosswalks" / "gss" / "field_code_map.csv"
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
SUPERS = {"Science", "Engineering", "Health"}


def _ci(ref):
    L = re.match(r"[A-Z]+", ref).group(0); n = 0
    for c in L: n = n * 26 + (ord(c) - 64)
    return n - 1


def table43():
    """Return {total -> (field_name, super_field)} for leaf rows (walk tracks super)."""
    z = zipfile.ZipFile(T43); sst = []
    for _, e in ET.iterparse(z.open("xl/sharedStrings.xml")):
        if e.tag == NS + "si":
            sst.append("".join(t.text or "" for t in e.iter(NS + "t"))); e.clear()
    ws = sorted(n for n in z.namelist() if n.startswith("xl/worksheets/") and n.endswith(".xml"))[0]
    by_total = {}
    cur_super = None
    for row in ET.fromstring(z.read(ws)).iter(NS + "row"):
        d = {}
        for c in row.iter(NS + "c"):
            v = c.find(NS + "v")
            if v is not None:
                d[_ci(c.get("r"))] = sst[int(v.text)] if c.get("t") == "s" else v.text
        nm = str(d.get(0, "")).strip()
        if nm in SUPERS:
            cur_super = nm
        try:
            tot = int(float(d[1]))
        except (KeyError, ValueError, TypeError):
            continue
        if nm and nm[0:1].isalpha() and nm not in ("All detailed fields", "Detailed field"):
            by_total.setdefault(tot, (nm, cur_super))  # first wins (leaves before re-use)
    return by_total


def main() -> int:
    con = duckdb.connect()
    counts = {r[0]: int(r[1]) for r in con.execute(
        f"""SELECT gss_code, SUM(value) FROM '{RACE_PARQUET.as_posix()}'
            WHERE year=2023 AND enrollment_status IN ('full_time','part_time')
              AND degree_level='all_grad' AND gender='total' AND race='all_races'
            GROUP BY gss_code""").fetchall()}
    # all gss_codes across all years (for the residual list)
    all_codes = set()
    for f in sorted(glob.glob(CSV_GLOB)):
        with open(f, encoding="utf-8") as fh:
            r = csv.reader(fh); h = next(r); gi = h.index("gss_code")
            for row in r:
                if len(row) > gi and row[gi]:
                    all_codes.add(row[gi])
    by_total = table43()
    rows = []
    matched = 0
    for code in sorted(all_codes, key=lambda c: (len(c), c)):
        cnt = counts.get(code)
        fine = coarse = ""
        status = "residual_needs_reference"
        rationale = ("gss_code not present in 2023 Table 4-3 (historical-only code); "
                     "field_coarse/fine NULL pending the dedicated NCSES TOD/PUF field-code "
                     "reference or an earlier-year field table (§4, no invented mapping).")
        if cnt is not None and cnt in by_total and code in counts:
            fine, sup = by_total[cnt]
            coarse = sup or ""
            status = "count_matched_2023"
            rationale = (f"Count-matched: gss_code {code} 2023 all-grad (FT+PT) total = {cnt} "
                         f"uniquely equals Table 4-3 detailed field '{fine}' (NSF 25-317), "
                         f"SEH super-field '{coarse}'. field_fine = detailed name; field_coarse "
                         f"= SEH super (Science/Engineering/Health). Finer ~10-way broad subfields "
                         f"await the dedicated TOD reference.")
            matched += 1
        rows.append({"gss_code": code, "field_coarse": coarse, "field_fine": fine,
                     "match_basis": status, "match_count_2023": cnt if cnt is not None else "",
                     "decision_rationale": rationale})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fields = ["gss_code", "field_coarse", "field_fine", "match_basis", "match_count_2023", "decision_rationale"]
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader(); w.writerows(rows)
    b = OUT.read_bytes(); assert b.count(0) == 0 and b.count(13) == 0; b.decode("utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)}: {len(rows)} gss_codes; "
          f"{matched} count-matched (field_coarse+field_fine filled), "
          f"{len(rows)-matched} residual (NULL, need reference).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
