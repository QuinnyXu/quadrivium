"""etl/build_gss_pd_nfr_column_map.py — HD 4.3 GSS PD_NFR column crosswalk.

The PD_NFR sheet is NOT a single factorial table: it is several **overlapping
marginal tables** sharing the same postdoc/NFR totals (decomposed by support, by
degree-type, by citizenship, by gender×mechanism, plus the non-faculty-researcher
block). A faithful long panel therefore carries a **`measure_group` discriminator**
so a consumer sums WITHIN a marginal, never across them (which would double-count).

Generates ``crosswalks/gss/pd_nfr_column_map.csv``: every PD_NFR wide column
(FY1972–2024) → ``(population, measure_group, gender, race, support_mechanism,
source_class, funding_agency, degree_type, citizenship)`` (unused axes = 'all'),
with per-row ``decision_rationale``. Reconciles the 2017 relabel (felshp=fel,
trneeshp=trn, rsch_grnt=grt, oth_mech=om, *_degr suffix dropped, nmed=nonmed,
unk=unknown, hhs_nih=nih, hhs_oth=hhs, nonfed=nfed). Asserts 100% coverage.

    uv run python etl/build_gss_pd_nfr_column_map.py
"""
from __future__ import annotations
import csv, glob, os, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSV_GLOB = str(ROOT / "data" / "raw" / "gss" / "csv" / "gss*_pd_nfr.csv")
OUT = ROOT / "crosswalks" / "gss" / "pd_nfr_column_map.csv"
ID_PREFIXES = (
    "institution_id", "UNITID", "school_id", "gss_code", "year", "Institution_Name",
    "hdg_inst", "toc_code", "institution_state", "hbcu_flag", "land_grant_flag",
    "carnegie_code", "full_school_name", "school_name", "school_zip",
    "school_type_code", "hdg_code", "hhe_flag", "ncses_inst_id",
)
MECH = {"tot": "all", "felshp": "fellowship", "fel": "fellowship",
        "trneeshp": "traineeship", "trn": "traineeship",
        "rsch_grnt": "research_grant", "grt": "research_grant",
        "oth_mech": "other", "om": "other"}
GENDER = {"tot": "total", "men": "men", "wmen": "women"}
RACE = {"all_races": "all_races", "us": "us_citizen", "forgn": "foreign",
        "hisp": "hispanic", "indian": "american_indian", "asian": "asian",
        "black": "black", "pacific": "pacific_islander", "white": "white",
        "multi_non_hisp": "multiracial", "multi": "multiracial",
        "unknown": "unknown", "unk": "unknown"}
DEGR = {"med": "medical", "nonmed": "nonmedical", "nmed": "nonmedical",
        "dual": "dual", "unknown": "unknown", "unk": "unknown", "all": "all"}
SOURCE = {"all_srces": ("all_sources", "all"), "all": ("all_sources", "all"),
          "fed_all_srces": ("federal", "all"), "fed_all": ("federal", "all"),
          "fed_dod": ("federal", "DOD"), "fed_doe": ("federal", "DOE"),
          "fed_doa": ("federal", "USDA"), "fed_nasa": ("federal", "NASA"),
          "fed_nsf": ("federal", "NSF"), "fed_oth": ("federal", "other_federal"),
          "fed_nih": ("federal", "NIH"), "fed_hhs_nih": ("federal", "NIH"),
          "fed_hhs": ("federal", "HHS_other"), "fed_hhs_oth": ("federal", "HHS_other"),
          "nonfed_all_srces": ("nonfederal", "all"), "nfed_all": ("nonfederal", "all"),
          "nonfed_inst_sup": ("nonfederal", "institutional"), "nfed_inst": ("nonfederal", "institutional"),
          "nonfed_oth_us": ("nonfederal", "other_us"), "nfed_othus": ("nonfederal", "other_us"),
          "nonfed_forgn": ("nonfederal", "foreign"), "nfed_forgn": ("nonfederal", "foreign"),
          "self_sup": ("self_support", "all"),
          "unknown_sup": ("unknown_source", "all"), "unk_sup": ("unknown_source", "all")}

A = "all"  # default axis value


def base(pop="postdoc", group="", gender=A, race=A, mech=A, sc=A, ag=A, degr=A, cit=A):
    return dict(population=pop, measure_group=group, gender=gender, race=race,
                support_mechanism=mech, source_class=sc, funding_agency=ag,
                degree_type=degr, citizenship=cit)


def parse(col: str):
    b = col[:-2] if col.endswith("_v") else col
    # --- NFR block: nfr_<gen>_<degr> ---
    m = re.match(r"nfr_(tot|men|wmen)_(all_degr|all|med_degr|med|nonmed_degr|nmed|dual_degr|dual|unknown_degr|unk)$", b)
    if m:
        degr = m.group(2).replace("_degr", "")
        return base("nonfaculty_researcher", "nfr_demographic", gender=GENDER[m.group(1)],
                    degr=DEGR.get(degr, "all"))
    # --- pre-2017 combined: <gen>_postdoc_<mech|nonfed> ---
    m = re.match(r"(tot|men|wmen)_postdoc_(felshp|trneeshp|rsch_grnt|nonfed)$", b)
    if m:
        x = m.group(2)
        if x == "nonfed":
            return base(group="gender_support", gender=GENDER[m.group(1)], sc="nonfederal")
        return base(group="gender_support", gender=GENDER[m.group(1)], mech=MECH[x])
    # --- pre-2017 medical-degree postdoc/NFR block ---
    m = re.match(r"med_degr_postdoc_(all_srces|felshp|trneeshp|rsch_grnt|nonfed|forgn)$", b)
    if m:
        x = m.group(1)
        if x == "forgn":
            return base(group="degree_citizenship", degr="medical", cit="foreign")
        if x == "nonfed":
            return base(group="mechanism_degree", degr="medical", sc="nonfederal")
        if x == "all_srces":
            return base(group="mechanism_degree", degr="medical")
        return base(group="mechanism_degree", degr="medical", mech=MECH[x])
    if b == "med_degr_oth_non_fcty":
        return base("nonfaculty_researcher", "nfr_demographic", degr="medical")
    # --- degree origin: pd_degr_<us|forgn|unknown_orig|unk_orig> ---
    m = re.match(r"pd_degr_(us|forgn|unknown_orig|unk_orig)$", b)
    if m:
        c = {"us": "us", "forgn": "foreign", "unknown_orig": "unknown", "unk_orig": "unknown"}[m.group(1)]
        return base(group="degree_origin", cit=c)
    if not b.startswith("pd_"):
        return None
    body = b[3:]
    # --- citizenship × degree: (tot_cit|us|forgn)_(degr) ---
    m = re.match(r"(tot_cit|us|forgn)_(med_degr|med|nonmed_degr|nmed|dual_degr|dual|unknown_degr|unk)$", body)
    if m:
        cit = {"tot_cit": "all", "us": "us", "forgn": "foreign"}[m.group(1)]
        return base(group="citizenship_degree", cit=cit, degr=DEGR[m.group(2).replace("_degr", "")])
    # --- mechanism × gender: <mech>_<gen>_all[_srces] ---
    m = re.match(r"(tot|felshp|fel|trneeshp|trn|rsch_grnt|grt|oth_mech|om)_(men|wmen)_(all_srces|all)$", body)
    if m:
        return base(group="gender_mechanism", gender=GENDER[m.group(2)], mech=MECH[m.group(1)])
    # --- mechanism × degree: <mech>_<degr>[_degr] ---
    m = re.match(r"(tot|felshp|fel|trneeshp|trn|rsch_grnt|grt|oth_mech|om)_(med_degr|med|nonmed_degr|nmed|dual_degr|dual|unknown_degr|unk)$", body)
    if m:
        return base(group="mechanism_degree", mech=MECH[m.group(1)], degr=DEGR[m.group(2).replace("_degr", "")])
    # --- support: <mech>_<source> ---
    m = re.match(r"(tot|felshp|fel|trneeshp|trn|rsch_grnt|grt|oth_mech|om)_(.+)$", body)
    if m and m.group(2) in SOURCE:
        sc, ag = SOURCE[m.group(2)]
        return base(group="support", mech=MECH[m.group(1)], sc=sc, ag=ag)
    # --- demographic: <gen>_<race> ---
    m = re.match(r"(tot|men|wmen)_(.+)$", body)
    if m and m.group(2) in RACE:
        return base(group="demographic", gender=GENDER[m.group(1)], race=RACE[m.group(2)])
    return None


def main() -> int:
    cols = {}
    for f in sorted(glob.glob(CSV_GLOB)):
        yr = int(re.search(r"(\d{4})", os.path.basename(f)).group(1))
        with open(f, encoding="utf-8") as fh:
            for c in next(csv.reader(fh)):
                if not any(c == p or c.startswith(p) for p in ID_PREFIXES):
                    rng = cols.setdefault(c, [yr, yr]); rng[0] = min(rng[0], yr); rng[1] = max(rng[1], yr)
    rows, unmapped = [], []
    for col, (y0, y1) in sorted(cols.items()):
        p = parse(col)
        if p is None:
            unmapped.append(col); continue
        era = "pre-2017" if y1 <= 2016 else "post-2017" if y0 >= 2017 else "spans 2017"
        p2 = {"source_column": col, "first_year": y0, "last_year": y1, **p,
              "decision_rationale": (f"{era} PD_NFR column; {p['population']}, "
                  f"measure_group={p['measure_group']}; axes "
                  f"(gender={p['gender']}, race={p['race']}, mechanism={p['support_mechanism']}, "
                  f"{p['source_class']}/{p['funding_agency']}, degree={p['degree_type']}, "
                  f"citizenship={p['citizenship']}). Sum only WITHIN measure_group "
                  f"(marginals overlap). 2017 relabels reconcile to one tuple.")}
        rows.append(p2)
    if unmapped:
        raise SystemExit(f"FAIL: {len(unmapped)} unmapped PD_NFR columns (§4): {unmapped}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fields = ["source_column", "first_year", "last_year", "population", "measure_group",
              "gender", "race", "support_mechanism", "source_class", "funding_agency",
              "degree_type", "citizenship", "decision_rationale"]
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader(); w.writerows(rows)
    bts = OUT.read_bytes()
    assert bts.count(0) == 0 and bts.count(13) == 0; bts.decode("utf-8")
    from collections import Counter
    grp = Counter(r["measure_group"] for r in rows)
    print(f"Wrote {OUT.relative_to(ROOT)}: {len(rows)} columns, 100% coverage (0 unmapped).")
    print("  measure_groups:", dict(grp))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
