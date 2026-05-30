"""THROWAWAY (HD 3.2 finalization #3): quantify the era-B ipeds_unitid
coverage gap surfaced by the FedSupport spine, to correct the falsified
"era-B: all three populated" assertion at herd_panel_etl_scoping.md ~L448.
Counts era-B distinct institutions with NULL ipeds_unitid + their share."""
from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parent.parent.parent
HERD = (ROOT / "data" / "harmonized" / "herd_panel.parquet").as_posix()
con = duckdb.connect()

mixed = con.execute(f"""
  WITH g AS (
    SELECT institution_id, COUNT(*) n, COUNT(ipeds_unitid) nn
    FROM read_parquet('{HERD}') WHERE era='B' GROUP BY 1)
  SELECT COUNT(*) FILTER (WHERE nn=0)        AS all_null,
         COUNT(*) FILTER (WHERE nn>0 AND nn<n) AS mixed,
         COUNT(*) FILTER (WHERE nn=n)        AS all_nonnull,
         COUNT(*)                            AS total
  FROM g
""").fetchone()
all_null, mixed_n, all_nonnull, total = mixed
print(f"era-B distinct institutions (by institution_id): {total}")
print(f"  all rows NULL ipeds_unitid : {all_null}  ({all_null/total:.1%})")
print(f"  mixed (some null some not) : {mixed_n}")
print(f"  all rows non-null          : {all_nonnull}  ({all_nonnull/total:.1%})")

nc = con.execute(f"""
  SELECT COUNT(DISTINCT institution_id) FROM read_parquet('{HERD}')
  WHERE era='B' AND ipeds_unitid IS NULL AND ncses_inst_id IS NOT NULL
""").fetchone()[0]
print(f"  of the NULL-ipeds insts, how many carry a non-null ncses_inst_id: {nc}")

# row-level coverage too (for the coverage statement framing)
rows = con.execute(f"""
  SELECT COUNT(*) n, COUNT(ipeds_unitid) nn, COUNT(ncses_inst_id) nnc,
         COUNT(institution_id) nfice
  FROM read_parquet('{HERD}') WHERE era='B'
""").fetchone()
print(f"\nera-B rows: {rows[0]}  non-null ipeds={rows[1]} ({rows[1]/rows[0]:.1%})  "
      f"non-null ncses={rows[2]} ({rows[2]/rows[0]:.1%})  "
      f"non-null institution_id(fice)={rows[3]} ({rows[3]/rows[0]:.1%})")

# the named giants — confirm they're in the all-null set
named = con.execute(f"""
  SELECT DISTINCT inst_name_long, institution_id, ncses_inst_id
  FROM read_parquet('{HERD}')
  WHERE era='B' AND ipeds_unitid IS NULL
    AND (inst_name_long ILIKE '%Johns Hopkins%'
      OR inst_name_long ILIKE '%Ohio State%'
      OR inst_name_long ILIKE '%Vanderbilt%'
      OR inst_name_long ILIKE '%Texas A&M University, College Station%')
  ORDER BY 1
""").fetchall()
print("\nNamed giants confirmed in era-B NULL-ipeds set:")
for nm, iid, ncses in named:
    print(f"  {nm!r}  institution_id={iid}  ncses_inst_id={ncses}")
