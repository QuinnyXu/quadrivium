"""
etl/spikes/spike_fedsupport_acquisition_probe.py — THROWAWAY GATE SPIKE.

HD 3.1 de-risking gate for the Federal S&E Support module (quadrivium
dataset #2: NSF Survey of Federal Science and Engineering Support to
Universities, Colleges, and Nonprofit Institutions).

This is a THROWAWAY spike. It does NOT promote to production. HD 3.0 / 3.2
consume the FINDINGS (the validation report under
validation/reports/fedsupport/), not this code. Per
[[feedback-etl-spike-scoping]] the spike is pointed at two gate questions
and three kill conditions, nothing more — it does NOT harmonize.

Two gate questions
------------------
(i)  ACQUISITION ARTIFACT: downloadable microdata PUF, or published data
     tables requiring a parse?  (Leading hypothesis: tables-not-PUF, since
     the survey is ABSENT from the NCSES microdata-PUF list. Confirmed by
     web evidence; this spike inspects the table artifact itself.)
(ii) INSTITUTION IDENTIFIER: does the artifact carry IPEDS UNITID,
     ncses_inst_id, an NCSES internal ID, or name+state only?  Reported
     PER SIDE of the volume-71 (FY2021-22) redesign boundary.

Boundary sampling (per [[feedback-cross-temporal-sampling]]): the kill
condition K3 is cross-temporal (did the identifier scheme change across the
redesign?), so the frame is NOT a single anchor year. We sample three years
spanning the boundary:
  - FY2020  (NSF 22-342)  — PRE-redesign
  - FY2021  (NSF 24-311)  — volume-71 first redesigned year (boundary)
  - FY2023  (NSF 25-339)  — anchor year (POST), the reconciliation target
This is enough to answer the gate without harmonizing anything era-wide.

Artifact under inspection: Table 12 (higher-ed, institution-level):
"Federal obligations for science and engineering to universities and
colleges, by state, outlying area, institution, and type of activity".
This is the higher-ed-ONLY institution-grain table — NOT the agency-grain
all-performer data, and NOT the nonprofit tables (Table 32/33). The
higher-ed/nonprofit separability is itself a K2 sub-check.

Runtime deps: duckdb==1.5.2 + pypdf==6.10.2 only (CLAUDE.md §3 exact-only).
The native table format is XLSX (NEW-DEP territory). This spike attempts to
read XLSX via DuckDB's `excel` extension (no new pip dep — extension is
fetched by DuckDB itself). If that path fails, it falls back to the PDF
sibling via pypdf (Table-26 precedent). Either way the spike SURFACES the
runtime-format decision rather than silently adding a dep.

Network: this spike performs the bounded FY2023+boundary gate slice
download (principal-authorized). Any acquisition beyond this needs a
separate green-light.

Author: Skipper, 2026-05-29 (HD 3.1 gate). Throwaway.
"""

from __future__ import annotations

import io
import sys
import urllib.request
import zipfile
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent.parent
SCRATCH = ROOT / "etl" / "spikes" / "_fedsupport_scratch"
SCRATCH.mkdir(parents=True, exist_ok=True)

# Table 12 (higher-ed institution-level) across the volume-71 boundary.
# (year, side-label, report_no, xlsx_url, pdf_url)
TARGETS = [
    (
        2020,
        "PRE-redesign (pre vol-71)",
        "nsf22342",
        "https://ncses.nsf.gov/pubs/nsf22342/assets/data-tables/tables/nsf22342-tab012.xlsx",
        "https://ncses.nsf.gov/pubs/nsf22342/assets/data-tables/tables/nsf22342-tab012.pdf",
    ),
    (
        2021,
        "vol-71 first year (boundary)",
        "nsf24311",
        "https://ncses.nsf.gov/pubs/nsf24311/assets/data-tables/tables/nsf24311-tab012.xlsx",
        "https://ncses.nsf.gov/pubs/nsf24311/assets/data-tables/tables/nsf24311-tab012.pdf",
    ),
    (
        2023,
        "POST / ANCHOR",
        "nsf25339",
        "https://ncses.nsf.gov/pubs/nsf25339/assets/data-tables/tables/nsf25339-tab012.xlsx",
        "https://ncses.nsf.gov/pubs/nsf25339/assets/data-tables/tables/nsf25339-tab012.pdf",
    ),
]

UA = "quadrivium-skipper-spike/1.0 (research; HD3.1 gate)"


def fetch(url: str) -> bytes | None:
    """Best-effort GET. Returns bytes or None on failure (prints reason)."""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.read()
    except Exception as e:  # noqa: BLE001
        print(f"    FETCH-FAIL {url}\n      {type(e).__name__}: {e}")
        return None


def try_duckdb_excel(con: duckdb.DuckDBPyConnection) -> bool:
    """Attempt to load DuckDB's excel extension. Returns True if available."""
    try:
        con.execute("INSTALL excel")
        con.execute("LOAD excel")
        return True
    except Exception as e:  # noqa: BLE001
        print(f"  duckdb excel extension unavailable: {type(e).__name__}: {e}")
        return False


def inspect_xlsx(con: duckdb.DuckDBPyConnection, path: Path, year: int) -> None:
    """Print the first ~25 rows raw so we can see the header band + identifier
    columns. NCSES table XLSX files carry title/footnote bands, so we read
    all-varchar with no header assumption."""
    p = path.as_posix()
    # read_xlsx (duckdb excel ext) — read raw, no header, so we see the
    # title/column-label band that NCSES tables prepend.
    for opts in ("header=false, all_varchar=true", "all_varchar=true"):
        try:
            con.execute(
                f"CREATE OR REPLACE TABLE t_{year} AS "
                f"SELECT * FROM read_xlsx('{p}', {opts})"
            )
            cols = [r[0] for r in con.execute(f"DESCRIBE t_{year}").fetchall()]
            n = con.execute(f"SELECT COUNT(*) FROM t_{year}").fetchone()[0]
            print(f"    read_xlsx OK ({opts}) — {n} rows, {len(cols)} cols")
            print(f"    columns: {cols}")
            head = con.execute(f"SELECT * FROM t_{year} LIMIT 25").fetchall()
            for i, row in enumerate(head):
                cells = [("" if c is None else str(c))[:22] for c in row]
                print(f"      r{i:02d}: {cells}")
            return
        except Exception as e:  # noqa: BLE001
            print(f"    read_xlsx FAIL ({opts}): {type(e).__name__}: {e}")
    print("    read_xlsx exhausted all option sets")


def inspect_pdf(pdf_bytes: bytes, year: int) -> None:
    """Fallback: dump first-page text via pypdf (Table-26 precedent) so we can
    read the column headers + a couple of institution rows."""
    import pypdf

    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    print(f"    PDF pages: {len(reader.pages)}")
    txt = reader.pages[0].extract_text() or ""
    lines = [ln for ln in txt.splitlines() if ln.strip()]
    for ln in lines[:35]:
        print(f"      | {ln[:90]}")


def main() -> int:
    print("=" * 72)
    print("HD 3.1 GATE SPIKE — Federal S&E Support acquisition probe")
    print("=" * 72)

    con = duckdb.connect()
    excel_ok = try_duckdb_excel(con)
    print(f"duckdb excel extension available: {excel_ok}\n")

    for year, side, report, xlsx_url, pdf_url in TARGETS:
        print(f"\n--- FY{year}  [{side}]  report={report} ---")
        # XLSX
        xb = fetch(xlsx_url)
        if xb is not None:
            xp = SCRATCH / f"{report}-tab012-FY{year}.xlsx"
            xp.write_bytes(xb)
            print(f"  XLSX staged: {xp.name} ({len(xb):,} bytes)")
            if excel_ok:
                inspect_xlsx(con, xp, year)
        else:
            print("  XLSX fetch failed — trying PDF sibling")

        # PDF (always pull for FY2023 anchor; for others only if XLSX path
        # gave us nothing). Cheap insurance for the pypdf-fallback finding.
        need_pdf = (xb is None) or (year == 2023)
        if need_pdf:
            pb = fetch(pdf_url)
            if pb is not None:
                pp = SCRATCH / f"{report}-tab012-FY{year}.pdf"
                pp.write_bytes(pb)
                print(f"  PDF staged: {pp.name} ({len(pb):,} bytes)")
                try:
                    inspect_pdf(pb, year)
                except Exception as e:  # noqa: BLE001
                    print(f"    PDF inspect failed: {type(e).__name__}: {e}")

    print("\n" + "=" * 72)
    print("Scratch dir (throwaway, gitignored territory):", SCRATCH)
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
