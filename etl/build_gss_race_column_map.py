"""etl/build_gss_race_column_map.py — HD 4.3 GSS Race-column crosswalk.

Generates ``crosswalks/gss/race_column_map.csv``: every Race-sheet wide column
(FY1972–2024) → canonical ``(degree_level, enrollment_status, gender, race)``,
with per-row ``decision_rationale`` (§6). Reconciles the 2017 redesign and the
OMB-1997 race-taxonomy bridge (clause-(a)): NCSES carries legacy (`asian_pi_98`,
`other_98`) parallel to modern OMB-1997 categories 1972–2016, retired at 2017 —
the legacy columns map to distinct ``*_legacy`` race values (kept, not dropped,
§4); `multi_non_hisp`↔`multi` and `unknown`↔`unk` are 2017 relabels → one tuple.

Asserts 100% column coverage. UTF-8/LF, deterministic.

    uv run python etl/build_gss_race_column_map.py
"""
from __future__ import annotations
import csv, glob, os, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSV_GLOB = str(ROOT / "data" / "raw" / "gss" / "csv" / "gss*_race.csv")
OUT = ROOT / "crosswalks" / "gss" / "race_column_map.csv"
ID_PREFIXES = (
    "institution_id", "UNITID", "school_id", "gss_code", "year", "Institution_Name",
    "hdg_inst", "toc_code", "institution_state", "hbcu_flag", "land_grant_flag",
    "carnegie_code", "full_school_name", "school_name", "school_zip",
    "school_type_code", "hdg_code", "hhe_flag", "ncses_inst_id",
)
DEGREE = {"ma": "masters", "dr": "doctoral"}
ENROLL = {"ft_frst": "full_time_first_year", "ft": "full_time", "pt": "part_time"}
GENDER = {"tot": "total", "men": "men", "wmen": "women"}
RACE = {
    "all_races": "all_races", "white": "white", "black": "black", "asian": "asian",
    "pacific": "pacific_islander", "indian": "american_indian", "hisp": "hispanic",
    "forgn": "foreign", "unk": "unknown", "unknown": "unknown",
    "multi": "multiracial", "multi_non_hisp": "multiracial",
    "asian_pi_98": "asian_pacific_legacy", "other_98": "other_legacy",
}


def is_id(c): return any(c == p or c.startswith(p) for p in ID_PREFIXES)


def parse_column(col: str):
    body = col[:-2] if col.endswith("_v") else col
    t = body.split("_")
    degree = "all_grad"
    if t and t[0] in DEGREE:
        degree = DEGREE[t[0]]; t = t[1:]
    if len(t) >= 2 and t[0] == "ft" and t[1] == "frst":
        enroll = "full_time_first_year"; t = t[2:]
    elif t and t[0] in ("ft", "pt"):
        enroll = ENROLL[t[0]]; t = t[1:]
    else:
        return None
    if not t or t[0] not in GENDER:
        return None
    gender = GENDER[t[0]]; t = t[1:]
    race_key = "_".join(t)
    if race_key not in RACE:
        return None
    return degree, enroll, gender, RACE[race_key], race_key


def main() -> int:
    cols = {}
    for f in sorted(glob.glob(CSV_GLOB)):
        yr = int(re.search(r"(\d{4})", os.path.basename(f)).group(1))
        with open(f, encoding="utf-8") as fh:
            for c in next(csv.reader(fh)):
                if not is_id(c):
                    rng = cols.setdefault(c, [yr, yr])
                    rng[0] = min(rng[0], yr); rng[1] = max(rng[1], yr)
    rows, unmapped = [], []
    for col, (y0, y1) in sorted(cols.items()):
        p = parse_column(col)
        if p is None:
            unmapped.append(col); continue
        degree, enroll, gender, race, race_key = p
        era = "pre-2017" if y1 <= 2016 else "post-2017" if y0 >= 2017 else "spans 2017"
        legacy = " (pre-1998 OMB legacy category, retained parallel per §4)" if race_key in ("asian_pi_98", "other_98") else ""
        rows.append({
            "source_column": col, "first_year": y0, "last_year": y1,
            "degree_level": degree, "enrollment_status": enroll, "gender": gender, "race": race,
            "decision_rationale": (f"{era} Race column; {degree}, {enroll}, gender={gender}, "
                                   f"race={race}{legacy}. 2017 relabels reconcile to one tuple "
                                   f"(multi_non_hisp=multi, unknown=unk)."),
        })
    if unmapped:
        raise SystemExit(f"FAIL: {len(unmapped)} unmapped Race columns (§4): {unmapped[:20]}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fields = ["source_column", "first_year", "last_year", "degree_level",
              "enrollment_status", "gender", "race", "decision_rationale"]
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader(); w.writerows(rows)
    b = OUT.read_bytes()
    assert b.count(0) == 0 and b.count(13) == 0; b.decode("utf-8")
    tuples = {(r["degree_level"], r["enrollment_status"], r["gender"], r["race"]) for r in rows}
    print(f"Wrote {OUT.relative_to(ROOT)}: {len(rows)} columns -> {len(tuples)} canonical tuples; "
          f"100% coverage (0 unmapped).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
