"""etl/spikes/gss/gss_methods_figures.py — GSS methods-note figures (charts dev-group).

Generates the three lead-anchor figures for docs/methods_notes/gss/ (§9 convention):
  fig1 problem visualization — GSS frame instability (enrollment + institution count)
  fig2 contribution-decomposition — four-driver bars for the 2017/2014/1984 boundaries
  fig3 validation receipt — federal-support: parquet vs published Table 1-7, 49/49 years
matplotlib is dev-group only (NOT runtime). Deterministic PNGs (timestamp stripped).

    uv run --group charts python etl/spikes/gss/gss_methods_figures.py
"""
import re, zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
import duckdb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[3]
RACE = (ROOT / "data" / "harmonized" / "gss_race.parquet").as_posix()
T17 = ROOT / "data" / "reference" / "gss" / "nsf25317-tab001-007.xlsx"
OUT = ROOT / "docs" / "methods_notes" / "gss" / "figures"
OUT.mkdir(parents=True, exist_ok=True)
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
META = {"Software": None}  # strip matplotlib version + timestamp for determinism
con = duckdb.connect()


def save(fig, name):
    fig.savefig(OUT / name, dpi=120, bbox_inches="tight", metadata=META)
    plt.close(fig)
    print(f"  wrote {(OUT / name).relative_to(ROOT)}")


def series():
    rows = con.execute(f"""SELECT year, SUM(value) e, COUNT(DISTINCT unitid) n FROM '{RACE}'
        WHERE enrollment_status IN ('full_time','part_time') AND degree_level='all_grad'
          AND gender='total' AND race='all_races' GROUP BY year ORDER BY year""").fetchall()
    return [r[0] for r in rows], [int(r[1]) for r in rows], [r[2] for r in rows]


def t17_federal():
    z = zipfile.ZipFile(T17); sst = []
    for _, e in ET.iterparse(z.open("xl/sharedStrings.xml")):
        if e.tag == NS + "si":
            sst.append("".join(t.text or "" for t in e.iter(NS + "t"))); e.clear()
    def ci(r):
        L = re.match(r"[A-Z]+", r).group(0); n = 0
        for c in L: n = n * 26 + (ord(c) - 64)
        return n - 1
    ws = sorted(n for n in z.namelist() if n.startswith("xl/worksheets/") and n.endswith(".xml"))[0]
    pub = {}; seen = False
    for row in ET.fromstring(z.read(ws)).iter(NS + "row"):
        d = {}
        for c in row.iter(NS + "c"):
            v = c.find(NS + "v")
            if v is not None: d[ci(c.get("r"))] = sst[int(v.text)] if c.get("t") == "s" else v.text
        lab = str(d.get(0, "")); m = re.match(r"(\d{4})", lab)
        if not m or 1 not in d:
            continue
        try: val = int(float(d[1]))
        except (ValueError, TypeError): continue
        if seen: break
        y = int(m.group(1))
        if y in pub and "new" not in lab: continue
        pub[y] = val
        if y == 2023: seen = True
    return pub


def fed_parquet(years):
    out = {}
    for y in years:
        r = con.execute(f"""SELECT SUM(value) FROM '{RACE.replace('gss_race','gss_support')}'
            WHERE year={y} AND degree_level='all_grad' AND gender='total'
              AND support_mechanism='all' AND source_class='federal' AND funding_agency<>'all'""").fetchone()[0]
        out[y] = int(r) if r else 0
    return out


# ---------- fig 1: problem visualization ----------
yrs, enr, insts = series()
fig, ax1 = plt.subplots(figsize=(9, 4.5))
ax1.plot(yrs, [e / 1000 for e in enr], color="#1f4e79", lw=2, label="Graduate enrollment (thousands)")
ax1.set_ylabel("Graduate enrollment (thousands)", color="#1f4e79")
ax1.set_xlabel("Survey year")
ax2 = ax1.twinx()
ax2.plot(yrs, insts, color="#c55a11", lw=1.4, ls="--", label="Institutions surveyed")
ax2.set_ylabel("Institutions surveyed", color="#c55a11")
for x, lab, yf, ha in [(1985.5, "1984–87\nframe contraction", 0.97, "center"),
                       (2013, "2014\nframe expansion", 0.97, "right"),
                       (2018.5, "2017\nredesign", 0.80, "left")]:
    ax1.annotate(lab, (x, ax1.get_ylim()[1] * yf), ha=ha, va="top", fontsize=7.5, color="#444")
for x in (1984, 2014, 2017):
    ax1.axvspan(x - 0.4, x + 0.4, color="grey", alpha=0.12)
# FY2024 end-of-series note: latest cycle, still collecting (~52 small institutions
# absent, <1% of enrollment) — not a fourth discontinuity.
ax2.annotate("FY2024: latest cycle,\nstill collecting (small\ninstitutions absent)",
             (yrs[-1], insts[-1]), textcoords="offset points", xytext=(-6, 24),
             ha="right", va="bottom", fontsize=6.3, color="#c55a11",
             arrowprops=dict(arrowstyle="->", color="#c55a11", lw=0.7))
ax1.set_title("GSS is frame-unstable: three discontinuities punctuate FY1972–2024", fontsize=10)
save(fig, "gss_frame_instability.png")

# ---------- fig 2: four-driver decomposition (grouped signed bars) ----------
labels = ["2017 redesign", "2014 expansion", "1984–87 onset"]
real = [-34.254, 19.215, 26.724]      # fixed-cohort change (real + definitional)
frame = [-1.459, 14.361, -22.486]     # institutions entering/leaving the frame
net = [-35.713, 33.576, 4.238]
fig, ax = plt.subplots(figsize=(8.5, 4.4))
x = list(range(len(labels))); w = 0.34
ax.bar([i - w / 2 for i in x], real, w, label="Fixed-cohort change (real + definitional)", color="#2e75b6")
ax.bar([i + w / 2 for i in x], frame, w, label="Frame (institutions entering / leaving)", color="#c55a11")
for i, n in enumerate(net):
    ax.plot(i, n, "D", color="black", ms=6, zorder=5)
    ax.annotate(f"net {n:+.1f}k", (i, n), textcoords="offset points",
                xytext=(0, 8 if n >= 0 else -14), ha="center", fontsize=8, fontweight="bold")
ax.axhline(0, color="black", lw=0.8)
ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=9)
ax.set_ylabel("Enrollment change (thousands)")
ax.set_title("Each GSS boundary splits into fixed-cohort vs frame components\n"
             "(♦ net): 2017 is a definitional-dominated cohort drop; 1984–87 a frame contraction masking real growth",
             fontsize=9.5)
ax.legend(fontsize=8, loc="upper right")
save(fig, "gss_boundary_decomposition.png")

# ---------- fig 3: validation receipt ----------
pub = t17_federal()
yy = sorted(pub)
pq = fed_parquet(yy)
fig, ax = plt.subplots(figsize=(9, 4))
ax.plot(yy, [pub[y] / 1000 for y in yy], color="#c55a11", lw=3, alpha=0.45, label="Published (NSF 25-317 Table 1-7)")
ax.plot(yy, [pq[y] / 1000 for y in yy], color="#1f4e79", lw=1.2, label="Harmonized panel (gss_support)")
ax.set_ylabel("FT graduate students with federal support (thousands)")
ax.set_xlabel("Survey year")
mism = sum(1 for y in yy if pub[y] != pq[y])
ax.set_title(f"Validation receipt: the panel reproduces published federal support, "
             f"{len(yy)}/{len(yy)} years exact (FY{min(yy)}–{max(yy)})", fontsize=9.5)
ax.legend(fontsize=8)
save(fig, "gss_validation_receipt.png")
print(f"  fig3 mismatches: {mism} (expect 0)")
