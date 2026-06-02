"""etl/acquire_gss.py — HD 4.2 GSS acquisition-format conversion (§3 lock).

Per the ratified HD 4.1 §3 decision (seeds/overrides.md 2026-06-02): GSS arrives
as per-year zips carrying ``gssYYYY_Code.xlsx`` (3-sheet wide tabulation) +
``gssYYYY_code.sas7bdat`` (microdata). The **XLSX is authoritative**; this script
converts it **once, at acquisition, to CSV** (Race / Support / PD_NFR → 3 CSVs per
year) using only the Python standard library (xlsx = zip + XML) — **zero new
runtime dependency**; the deposit runtime stays ``duckdb`` + ``pypdf``. The
``sas7bdat`` is retained, unread, as the provenance/audit sibling.

Converted CSVs are **generated artifacts** → this generator emits **UTF-8 / LF**
with a read-back validity assertion (zero NUL, no CR), the HD-4.x complement to
``etl/_load_fedsupport.write_text_clean`` (seeds/overrides.md "reproducible ≠
valid"). The as-downloaded zips are provenance, SHA-256-pinned in
``data/raw/MANIFEST.md``. Output (gitignored, regenerable):
``data/raw/gss/csv/gssYYYY_<sheet>.csv``.

    uv run python etl/acquire_gss.py            # convert all staged years
    uv run python etl/acquire_gss.py 1975 2023  # convert specific years

Faithful passthrough only — column order, row order, and cell values mirror the
source sheet exactly. NO harmonization, schema, or taxonomy decisions are made
here (those belong to the loader/panel build, surfaced separately).
"""
from __future__ import annotations
import sys, io, os, re, csv, glob, zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw" / "gss"
OUT_DIR = RAW_DIR / "csv"
SHEETS = ("Race", "Support", "PD_NFR")

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
RNS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"


def _col_idx(ref: str) -> int:
    letters = re.match(r"[A-Z]+", ref).group(0)
    n = 0
    for c in letters:
        n = n * 26 + (ord(c) - 64)
    return n - 1


def _load_shared_strings(z: zipfile.ZipFile) -> list[str]:
    out: list[str] = []
    if "xl/sharedStrings.xml" not in z.namelist():
        return out
    with z.open("xl/sharedStrings.xml") as f:
        for _, el in ET.iterparse(f):
            if el.tag == NS + "si":
                out.append("".join(t.text or "" for t in el.iter(NS + "t")))
                el.clear()
    return out


def _sheet_paths(z: zipfile.ZipFile) -> dict[str, str]:
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    rid_to_target = {r.get("Id"): r.get("Target") for r in rels}
    out = {}
    for s in wb.iter(NS + "sheet"):
        tgt = rid_to_target[s.get(RNS + "id")]
        out[s.get("name")] = ("xl/" + tgt) if not tgt.startswith("/") else tgt[1:]
    return out


def _cell_value(c, sst: list[str]) -> str:
    v = c.find(NS + "v")
    if v is None:
        isv = c.find(NS + "is")
        if isv is not None:
            return "".join(t.text or "" for t in isv.iter(NS + "t"))
        return ""
    if c.get("t") == "s":
        return sst[int(v.text)]
    return v.text if v.text is not None else ""


def _assert_clean(path: Path) -> None:
    b = path.read_bytes()
    if b.count(0):
        raise AssertionError(f"NUL bytes in {path}")
    if b.count(13):
        raise AssertionError(f"CR byte (non-LF) in {path}")
    b.decode("utf-8")  # raises if not valid UTF-8


def convert_sheet(z: zipfile.ZipFile, spath: str, sst: list[str], out_path: Path) -> tuple[int, int]:
    """Stream one sheet → CSV. Returns (data_rows, ncols). Memory-bounded."""
    # First pass: header width (max column index in row 1).
    ncols = 0
    with z.open(spath) as f:
        for _, row in ET.iterparse(f):
            if row.tag == NS + "row" and row.get("r") == "1":
                for c in row.iter(NS + "c"):
                    ncols = max(ncols, _col_idx(c.get("r")) + 1)
                row.clear()
                break
    data_rows = 0
    with z.open(spath) as f, out_path.open("w", encoding="utf-8", newline="") as out:
        w = csv.writer(out, lineterminator="\n")  # LF-only; csv default is \r\n
        for _, row in ET.iterparse(f):
            if row.tag != NS + "row":
                continue
            width = ncols
            cells = {}
            for c in row.iter(NS + "c"):
                ci = _col_idx(c.get("r"))
                cells[ci] = _cell_value(c, sst)
                width = max(width, ci + 1)
            w.writerow([cells.get(i, "") for i in range(width)])
            if row.get("r") != "1":
                data_rows += 1
            row.clear()
    return data_rows, ncols


def convert_year(zip_path: Path) -> None:
    year = re.search(r"(\d{4})", zip_path.name).group(1)
    zf = zipfile.ZipFile(zip_path)
    xlsx_name = [n for n in zf.namelist() if n.lower().endswith(".xlsx")][0]
    z = zipfile.ZipFile(io.BytesIO(zf.read(xlsx_name)))
    sst = _load_shared_strings(z)
    spaths = _sheet_paths(z)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for sheet in SHEETS:
        if sheet not in spaths:
            print(f"  {year} [{sheet}] MISSING — skipped")
            continue
        out_path = OUT_DIR / f"gss{year}_{sheet.lower()}.csv"
        rows, cols = convert_sheet(z, spaths[sheet], sst, out_path)
        _assert_clean(out_path)
        print(f"  {year} [{sheet:7s}] -> {out_path.name}  rows={rows} cols={cols}")


def main(argv: list[str]) -> int:
    years = set(argv[1:])
    zips = sorted(glob.glob(str(RAW_DIR / "*.zip")))
    if years:
        zips = [z for z in zips if re.search(r"(\d{4})", os.path.basename(z)).group(1) in years]
    if not zips:
        print(f"No GSS zips found under {RAW_DIR}", file=sys.stderr)
        return 1
    print(f"Converting {len(zips)} year(s) -> {OUT_DIR}")
    for zp in zips:
        convert_year(Path(zp))
    print("Done. Converted CSVs are gitignored regenerable intermediates;")
    print("the as-downloaded zips are the SHA-pinned provenance (data/raw/MANIFEST.md).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
