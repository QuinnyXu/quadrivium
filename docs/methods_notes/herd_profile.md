# HERD per-year profile (HD 1.5)

_Generated 2026-04-30. 53 staged years profiled (1972–2024)._

## Era boundaries as observed

- **Era A** (carries `question = 'Expenditures by S&E field'` only): **1973–2009** (37 years).
- **Era B** (carries the federal/nonfederal source-class split, no era-A question): **2010–2024** (15 years).
- **Transitional (carries both)**: none observed. The 2010 boundary is a clean cliff.
- **Pre-era-A** (carries neither): **1972**. Only `'Capital expenditures by area'` (6,654 rows) and `'Source'` (2,574 rows) are present; no field-level discipline question. The era-A field-level question first appears in 1973.

This validates the encoded boundary in `etl/_load.py` (`ERA_A_LAST = 2009`, `ERA_B_FIRST = 2010`) against the data — not just the FY24 Guide TOC. **Implication for HD 2.1:** the longitudinal field-level panel effectively spans 1973–2024 (52 years), not 1972–2024. `crosswalks/discipline_fine.csv` has no rows to author for 1972.

## Encoding fallback (UTF-8 → Latin-1)

5 of 53 years required the UTF-8 → Latin-1 fallback during raw-bytes scan. The pattern:

| Year | Substitutions |
|---|---:|
| 1972–2009 | 0 |
| 2010 | 1 |
| 2011–2013 | 0 |
| 2014 | 149 |
| 2015 | 158 |
| 2016 | 159 |
| 2017 | 308 |
| 2018–2024 | 0 |

The 2014–2017 cluster looks like an upstream NSF data-export pipeline change: 2010's lone substitution is a single Windows-1252 curly apostrophe in "Veteran's"; 2014 introduces wide Windows-1252 contamination; 2018+ is clean again. Hypothesis: web-form-collected free-text fields started flowing through unconverted from Windows clients in 2014, then NSF normalized to UTF-8 export starting 2018.

**Per-byte log status:** HD 1.5 used the no-write `_scan_invalid_utf8_bytes` path, so `validation/reports/encoding_substitutions.csv` currently holds only the single 2010 entry from the 2026-04-30 verification load. To populate the log with every 2014–2017 substitution, re-run loads through `read_herd_csv` (the production load path); this is left to HD 2.x or a deliberate audit run.

## Question-count trajectory

- 1972: 2 questions (no field-level data).
- 1973–1980: 3 questions (field-level + capital + source-of-funds).
- 1981–1996: 4 questions (source-of-funds module appears in 1981).
- 1997–1999: 4 questions.
- 2000–2002: 5 questions.
- 2003–2009: 7 questions (matches the 2003 format-expansion finding — Non-S&E rows + per-agency Federal columns added).
- 2010: 19 questions. **The era-B cliff: 7 → 19 questions in one year, with no question-name overlap.**
- 2011–2024: 16–19 questions, oscillating.

## Other observed anomalies

- **1978 half-coverage**: row count 7,602 vs. 1977's 17,514 and 1979's 22,307. Matches the inventory's "316 institutions vs. ~555 the year before/after" finding. No new action needed; documented for the methods note.

## Citing this profile

- `docs/herd_question_structure_by_year.csv` — compact per-year summary, deposit artifact, cited from the methods note's *Reconstructive Harmonization* section.
- `validation/profile/herd_profile.parquet` — long-format detail across (year × dimension × value), dimension ∈ {questionnaire_no, question, row, column}.
- `validation/reports/encoding_substitutions.csv` — per-byte substitution log. Currently single entry (2010 verification). Re-running production loads through `read_herd_csv` populates the rest.
