"""
etl/spikes/spike_dst_table_builder_reproducibility.py — HD 2.4.g
precondition gate.

Verifies that two CSV exports from NSF NCSES Table Builder, generated
by the maintainer under identical query parameters, are reproducible
(byte-identical OR content-identical modulo documented header
timestamps).

Per Vision DST anchor architecture verdict 2026-05-10 morning Item 1:
Table Builder CSV export reproducibility must verify before the
240-cell verification grid runs. Pass condition: byte-identical CSV
exports, or content-identical modulo header timestamps. Fail
condition: non-deterministic exports — panel reconvene before HD
2.4.g substantive work.

Procedure (maintainer-driven manual export, this spike consumes):
  1. Maintainer queries Table Builder for the precondition spec (see
     surface comment to user). Exports CSV to:
       data/reference/dst-table-builder/precondition_export_1.csv
  2. Maintainer closes/reopens browser, re-configures identical
     parameters, exports CSV to:
       data/reference/dst-table-builder/precondition_export_2.csv
  3. Maintainer captures access timestamps + canonical URL to:
       data/reference/dst-table-builder/precondition_metadata.txt
  4. This spike runs, surfaces verdict.

Spike outputs:
  - SHA-256 of each CSV.
  - Byte-identity check (raw file hash equality).
  - Content-identity check (line-by-line diff, with header-line
    timestamp tolerance if a timestamp-shaped header line is
    identified).
  - Row-axis count comparison.
  - Verdict: PASS (deposit's reproducibility contract holds) or
    FAIL (panel reconvene per Vision kill criterion).
"""
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
STAGING_DIR = ROOT / "data" / "reference" / "dst-table-builder"
EXPORT_1 = STAGING_DIR / "precondition_export_1.csv"
EXPORT_2 = STAGING_DIR / "precondition_export_2.csv"
METADATA = STAGING_DIR / "precondition_metadata.txt"

# Header lines that often carry export-time timestamps. The
# reproducibility test should tolerate timestamps in these lines
# (NSF tools sometimes embed export-time in a header comment).
TIMESTAMP_PATTERNS = [
    re.compile(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}'),
    re.compile(r'\d{2}[/-]\d{2}[/-]\d{4}'),
    re.compile(
        r'(Mon|Tue|Wed|Thu|Fri|Sat|Sun),?\s+\d+\s+'
        r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)'
    ),
    re.compile(r'(?i)\bexport(ed)?\s+(at|on|time)\b'),
    re.compile(r'(?i)\bgenerated\s+(at|on)\b'),
]


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def line_has_timestamp(line: str) -> bool:
    return any(p.search(line) for p in TIMESTAMP_PATTERNS)


def main() -> int:
    print("=" * 78)
    print("HD 2.4.g precondition — DST Table Builder reproducibility")
    print("=" * 78)

    # 1. Existence check
    print("\n[1] CSV staging check:")
    missing = []
    for label, p in (("export_1", EXPORT_1),
                     ("export_2", EXPORT_2)):
        exists = p.exists()
        size = p.stat().st_size if exists else None
        mark = "OK " if exists else "MISS"
        print(f"  [{mark}] {label:<10s} path={p.relative_to(ROOT)} "
              f"size={size}")
        if not exists:
            missing.append(label)
    if missing:
        print("\n  AWAITING CSV STAGING. The precondition gate requires "
              "the maintainer to query Table Builder twice under "
              "identical parameters and stage two CSVs at:")
        for label, p in (("export_1", EXPORT_1),
                         ("export_2", EXPORT_2)):
            print(f"    {p.relative_to(ROOT)}")
        print("\n  Spike returns NEEDS-STAGING; no verdict.")
        return 3  # needs-staging exit code

    # 2. Byte-identity (raw SHA-256 comparison)
    print("\n[2] Byte-identity (SHA-256):")
    h1 = file_sha256(EXPORT_1)
    h2 = file_sha256(EXPORT_2)
    print(f"  export_1 SHA-256: {h1}")
    print(f"  export_2 SHA-256: {h2}")
    byte_identical = (h1 == h2)
    print(f"  Byte-identical: {'PASS' if byte_identical else 'NO'}")

    # 3. Content-identity (line-by-line, with timestamp tolerance)
    print("\n[3] Content-identity (line-by-line, timestamp-tolerant):")
    with EXPORT_1.open("r", encoding="utf-8-sig", errors="replace") as f:
        lines_1 = f.read().splitlines()
    with EXPORT_2.open("r", encoding="utf-8-sig", errors="replace") as f:
        lines_2 = f.read().splitlines()
    print(f"  export_1 line count: {len(lines_1):,}")
    print(f"  export_2 line count: {len(lines_2):,}")
    if len(lines_1) != len(lines_2):
        print(f"  Line counts differ -> content NOT identical")
        content_identical = False
        diff_summary = "line-count mismatch"
    else:
        diffs: list[tuple[int, str, str]] = []
        timestamp_tolerated: list[int] = []
        for i, (a, b) in enumerate(zip(lines_1, lines_2)):
            if a == b:
                continue
            if line_has_timestamp(a) and line_has_timestamp(b):
                timestamp_tolerated.append(i)
                continue
            diffs.append((i, a, b))
        if not diffs:
            content_identical = True
            diff_summary = (
                f"all {len(lines_1):,} lines match"
                + (f" (tolerated {len(timestamp_tolerated)} "
                   f"header-timestamp lines)"
                   if timestamp_tolerated else "")
            )
        else:
            content_identical = False
            diff_summary = (
                f"{len(diffs)} line(s) differ on non-timestamp content"
            )
            print(f"  Sample diff (first 5):")
            for (i, a, b) in diffs[:5]:
                print(f"    line {i+1}:")
                print(f"      export_1: {a[:120]}")
                print(f"      export_2: {b[:120]}")
        print(f"  Content-identical (timestamp-tolerant): "
              f"{'PASS' if content_identical else 'NO'}")
        print(f"  Summary: {diff_summary}")

    # 4. Row-axis sanity (counts only — does each export emit the
    #    same number of data rows assuming the first line is a header)
    print("\n[4] Row-axis sanity (line counts above):")
    print(f"  Lines 1 vs 2: {len(lines_1)} vs {len(lines_2)}  "
          f"(delta {len(lines_1) - len(lines_2)})")

    # 5. Metadata staging check
    print("\n[5] Metadata staging:")
    md_present = METADATA.exists()
    print(f"  {'OK' if md_present else 'OPT'}  {METADATA.relative_to(ROOT)}"
          f" {'staged' if md_present else 'not staged (optional)'}")
    if md_present:
        print(f"  Metadata contents:")
        with METADATA.open("r", encoding="utf-8") as f:
            for line in f.read().splitlines()[:20]:
                print(f"    {line}")

    # 6. Verdict
    print("\n" + "=" * 78)
    print("Precondition verdict:")
    print("=" * 78)
    pass_overall = byte_identical or content_identical
    if pass_overall:
        path_chosen = ("byte-identical" if byte_identical
                       else "content-identical (timestamp-tolerant)")
        print(f"  PASS via {path_chosen}.")
        print()
        print(f"  Table Builder CSV exports are reproducible under "
              f"identical query parameters. HD 2.4.g substantive grid "
              f"work cleared to proceed.")
    else:
        print(f"  FAIL. Table Builder CSV exports are NOT reproducible "
              f"under identical query parameters.")
        print()
        print(f"  Per Vision DST anchor architecture verdict 2026-05-10 "
              f"morning Item 1 kill criterion: panel reconvene before "
              f"HD 2.4.g substantive work continues. Option (b) "
              f"(Table Builder CSV snapshot path) may collapse to "
              f"Option (c) per the Vision-locked branching.")

    return 0 if pass_overall else 2


if __name__ == "__main__":
    sys.exit(main())
