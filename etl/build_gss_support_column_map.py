"""etl/build_gss_support_column_map.py — HD 4.2 GSS Support-column crosswalk.

Generates ``crosswalks/gss/support_column_map.csv``: every distinct Support-sheet
wide-column name across FY1972–2024 → its canonical tuple
``(degree_level, gender, support_mechanism, source_class, funding_agency)``, with
a per-row ``decision_rationale`` (a methods-note sentence each, §6). The map is
the clause-(a) reconstruction object for the 2017 redesign: pre- and post-2017
spellings of the *same* measure collapse to one canonical tuple (e.g. pre
``ft_tot_fed_hhs_nih_v`` and post ``ft_tot_fed_nih_v`` → same NIH tuple), so the
funding face reconciles across the boundary.

Input: the gitignored converted CSV headers under ``data/raw/gss/csv/`` (produced
by ``etl/acquire_gss.py``). Output: the committed crosswalk (UTF-8/LF,
deterministic). Asserts 100% column coverage — an unmapped Support column fails
the build (codeset-extension discipline, §4).

    uv run python etl/build_gss_support_column_map.py
"""
from __future__ import annotations
import csv, glob, os, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSV_GLOB = str(ROOT / "data" / "raw" / "gss" / "csv" / "gss*_support.csv")
OUT = ROOT / "crosswalks" / "gss" / "support_column_map.csv"

ID_PREFIXES = (
    "institution_id", "UNITID", "school_id", "gss_code", "year", "Institution_Name",
    "hdg_inst", "toc_code", "institution_state", "hbcu_flag", "land_grant_flag",
    "carnegie_code", "full_school_name", "school_name", "school_zip",
    "school_type_code", "hdg_code", "hhe_flag", "ncses_inst_id",
)

# --- canonical normalization (the crosswalk's controlled vocabulary) ---------
DEGREE = {"ma": "masters", "dr": "doctoral"}            # absent prefix => all_grad
SEGMENT = {  # token after `ft` -> (gender, support_mechanism); exactly one is specific
    "tot": ("total", "all"),  "men": ("men", "all"),  "wmen": ("women", "all"),
    "felshp": ("total", "fellowship"),    "fel": ("total", "fellowship"),
    "trneeshp": ("total", "traineeship"), "trn": ("total", "traineeship"),
    "rsch_asst": ("total", "research_assistant"), "ra": ("total", "research_assistant"),
    "tchg_asst": ("total", "teaching_assistant"), "ta": ("total", "teaching_assistant"),
    "oth_mech": ("total", "other"),       "ots": ("total", "other"),
}
SOURCE = {  # source remainder -> (source_class, funding_agency)
    "all_srces": ("all_sources", "all"), "all": ("all_sources", "all"),
    "fed_all": ("federal", "all"),
    "fed_dod": ("federal", "DOD"),  "fed_doe": ("federal", "DOE"),
    "fed_doa": ("federal", "USDA"), "fed_nasa": ("federal", "NASA"),
    "fed_nsf": ("federal", "NSF"),  "fed_oth": ("federal", "other_federal"),
    "fed_nih": ("federal", "NIH"),  "fed_hhs_nih": ("federal", "NIH"),
    "fed_hhs": ("federal", "HHS_other"), "fed_hhs_oth": ("federal", "HHS_other"),
    "nfed_all": ("nonfederal", "all"),
    "nonfed_inst_sup": ("nonfederal", "institutional"), "nfed_inst": ("nonfederal", "institutional"),
    "nonfed_oth_us": ("nonfederal", "other_us"),        "nfed_othus": ("nonfederal", "other_us"),
    "nonfed_forgn": ("nonfederal", "foreign"),          "nfed_forgn": ("nonfederal", "foreign"),
    "self_sup": ("self_support", "all"),
}
# Two-token segments must be tried before single-token splits.
TWO_TOKEN_SEG = {"rsch_asst", "tchg_asst", "oth_mech"}


def is_id(c: str) -> bool:
    return any(c == p or c.startswith(p) for p in ID_PREFIXES)


def parse_column(col: str):
    """col -> (degree_level, gender, support_mechanism, source_class, funding_agency) or None."""
    body = col[:-2] if col.endswith("_v") else col
    t = body.split("_")
    degree = "all_grad"
    if t and t[0] in DEGREE:
        degree = DEGREE[t[0]]; t = t[1:]
    if not t or t[0] != "ft":
        return None
    t = t[1:]
    if not t:
        return None
    # segment: try two-token, then single-token
    seg = None
    if len(t) >= 2 and "_".join(t[:2]) in TWO_TOKEN_SEG:
        seg = "_".join(t[:2]); t = t[2:]
    elif t[0] in SEGMENT:
        seg = t[0]; t = t[1:]
    else:
        return None
    gender, mech = SEGMENT[seg]
    src_key = "_".join(t)
    if src_key not in SOURCE:
        return None
    source_class, agency = SOURCE[src_key]
    return degree, gender, mech, source_class, agency


def harvest_columns():
    cols = {}
    for f in sorted(glob.glob(CSV_GLOB)):
        yr = int(re.search(r"(\d{4})", os.path.basename(f)).group(1))
        with open(f, encoding="utf-8") as fh:
            for c in next(csv.reader(fh)):
                if not is_id(c):
                    rng = cols.setdefault(c, [yr, yr])
                    rng[0] = min(rng[0], yr); rng[1] = max(rng[1], yr)
    return cols


def rationale(col, degree, gender, mech, sc, agency, y0, y1):
    era = ("pre-2017" if y1 <= 2016 else "post-2017" if y0 >= 2017 else "spans 2017")
    return (f"{era} Support column; {degree} full-time, gender={gender}, "
            f"mechanism={mech}, {sc}" + (f"/{agency}" if agency != "all" else "")
            + f". Canonical tuple reconciles the 2017 relabel (e.g. hhs_nih=nih, "
              f"all_srces=all, oth_mech=ots, nonfed_*=nfed_*).")


def main() -> int:
    cols = harvest_columns()
    rows, unmapped = [], []
    for col, (y0, y1) in sorted(cols.items()):
        p = parse_column(col)
        if p is None:
            unmapped.append(col); continue
        degree, gender, mech, sc, agency = p
        rows.append({
            "source_column": col, "first_year": y0, "last_year": y1,
            "degree_level": degree, "gender": gender, "support_mechanism": mech,
            "source_class": sc, "funding_agency": agency,
            "decision_rationale": rationale(col, degree, gender, mech, sc, agency, y0, y1),
        })
    if unmapped:
        raise SystemExit(f"FAIL: {len(unmapped)} unmapped Support columns (codeset-extension "
                         f"gate, §4): {unmapped[:20]}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fields = ["source_column", "first_year", "last_year", "degree_level", "gender",
              "support_mechanism", "source_class", "funding_agency", "decision_rationale"]
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    # read-back validity (A1b)
    b = OUT.read_bytes()
    assert b.count(0) == 0 and b.count(13) == 0, "NUL/CR in crosswalk"
    b.decode("utf-8")
    tuples = {(r["degree_level"], r["gender"], r["support_mechanism"],
               r["source_class"], r["funding_agency"]) for r in rows}
    print(f"Wrote {OUT.relative_to(ROOT)}: {len(rows)} columns -> {len(tuples)} canonical tuples; "
          f"100% coverage (0 unmapped).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
