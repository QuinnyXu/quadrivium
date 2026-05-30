# `data/raw/` Manifest

Generated: 2026-04-29 (Skipper, HD 1.1).
Companion to `data/raw/INVENTORY.md`. The inventory describes shape; this
manifest records bit-exact provenance.

## What is here, what is not

`data/raw/` is **gitignored**. Only `INVENTORY.md` and this `MANIFEST.md` are
tracked. The raw payload (`data/raw/herd/`) lives on disk locally and on the
deposit; it is not in git.

To rebuild from scratch:

1. Obtain `NSF_HERD.zip` (SHA-256 below) from the upstream NSF distribution.
2. Extract the 53 nested year zips and the FY24 Guide PDF directly into
   `data/raw/herd/` (flat layout — no subfolders).
3. Verify with `data/raw/herd/_checksums.txt`:
   `sha256sum -c _checksums.txt` (Linux/macOS) or
   `Get-FileHash -Algorithm SHA256` per file (Windows).

## Decision: zips, not extracted CSVs

We staged the 53 NSF-distributed year **zips** (not the unpacked CSVs). Two
reasons:

1. **Provenance.** The zip is the bit-identical artifact NSF shipped. A cold
   reader checksumming against this manifest gets exactly what NSF
   distributed; an extracted CSV would have line-ending and encoding
   ambiguity that no checksum can survive cleanly across OSes.
2. **Loader extracts on read.** `etl/_load.py` (HD 1.2) opens the year zip,
   reads the CSV member into DuckDB / pandas, and never writes the CSV to
   disk. No extracted-CSV cache, no drift between cache and zip.

The SAS7BDAT members inside each zip are ignored by the loader (CSV is
authoritative; SAS is fallback only and has not been needed).

## Source archive

| SHA-256 | Bytes | File |
|---------|-------|------|
| `f752db19ccb61c9fd72c27558c41a17a0a8a638c4f82918064c0b65c948c5c7c` | 99,597,912 | `NSF_HERD.zip` (project root, not under `data/raw/`) |

`NSF_HERD.zip` lives at the repo root for now and is also gitignored. It is
the upstream bundle from which the 53 year zips were extracted; keeping it
around lets us re-stage from a single artifact if `data/raw/herd/` is lost.

## Staged files — `data/raw/herd/` (standard-form)

54 files total: 53 standard-form year zips (1972-2024) + 1 FY24 Guide PDF.
Aggregate size on disk: ~150 MB. Short-form zips ship under
`data/raw/herd/short_form/` — see the parallel section below.

Authoritative checksum list: `data/raw/herd/_checksums.txt` (also
gitignored — the source of truth for the hashes is this manifest, the txt
file is a regenerable convenience for `sha256sum -c`).

| SHA-256 | Bytes | File |
|---------|-------|------|
| `f4d2384ee5be72c297b39f866ab0765748c93a616b51be2f64d770fc44170455` | 399,786 | `Guide To Herd Data Files FY24.pdf` |
| `8a412b79f4e66e63680a8729a8089a1a88228a09a1d9afe48de681c1395c79f9` | 177,658 | `higher_education_r_and_d_1972.zip` |
| `526f04dc39def1976bd386e13d477aee69528d3bc9bcd05ac9afb40baaa11094` | 347,766 | `higher_education_r_and_d_1973.zip` |
| `135bf96d20510f0f7d108966c8d8a413bdbee21e7232e831362889913d6ef10e` | 328,087 | `higher_education_r_and_d_1974.zip` |
| `c5dc555f3e54b0755c42e1a5e457154522e67932688c7f78847007659ad79757` | 305,683 | `higher_education_r_and_d_1975.zip` |
| `b9576aa811e16e0ccba53a6214ba9c42e3dac91bed36d3f27091a08e2be3a400` | 316,250 | `higher_education_r_and_d_1976.zip` |
| `7f3425fe4cb3a3bc635b37e28fd56bea33c4574369069594039fd504e31f6c3f` | 307,908 | `higher_education_r_and_d_1977.zip` |
| `b029a75a9c56a5fb7a8e481da2e00c6aa4f601425bdeb265c5d194c87d1ae5e0` | 144,201 | `higher_education_r_and_d_1978.zip` |
| `e1e11238f70cc6c6995f906f2442a7b80e91cdc87405106229239a76fb4ee63d` | 363,650 | `higher_education_r_and_d_1979.zip` |
| `42823f4fe2a2b271716877715b9fc0bc7064a0e9db5fae2450294cf17e9854bb` | 456,325 | `higher_education_r_and_d_1980.zip` |
| `f92461e691e9c74ecf0caf161278a84bb9bc7f8da190a3c39e42bd0aa485a004` | 710,999 | `higher_education_r_and_d_1981.zip` |
| `327df4a524f1fafab836663b06671def686d462feed58aa679f0f3072fa1af57` | 696,971 | `higher_education_r_and_d_1982.zip` |
| `13d0ba09dafd14f6fcfeb6b6adb04939b44e2658cd13a6bc054583fdb9862e27` | 701,344 | `higher_education_r_and_d_1983.zip` |
| `104cd2bfb0bc01304d3f6ce9d0499905121a8114382457fc9dd9e32bf3a44a0b` | 776,778 | `higher_education_r_and_d_1984.zip` |
| `dda960147a17aad8f609a48d47b95b5e9557472e34814c81242b1e60c2b99efa` | 799,036 | `higher_education_r_and_d_1985.zip` |
| `86b68b06ddce44bbaa894de1a42b56433965a505e2897857f284546b1e819722` | 824,588 | `higher_education_r_and_d_1986.zip` |
| `d4a323b9ff14891ccd7683d37130f66de8bce9bb7d2b58a349f149537fa9f517` | 742,973 | `higher_education_r_and_d_1987.zip` |
| `45b18bbbcd0a61cb1def23903fb0355b65b6696c6be4a3b660fa2beebb7e0d85` | 593,423 | `higher_education_r_and_d_1988.zip` |
| `3b1a30de27c6b45daadcc147d0c70828f99a576bbe17671eca0e2adf8abab64e` | 726,800 | `higher_education_r_and_d_1989.zip` |
| `8be343704b0ccbae86a32a5b09edcf1547a022a2b7a4ae2764901da7de37065f` | 659,779 | `higher_education_r_and_d_1990.zip` |
| `382fc6f963f58e00cee9fd536afbf586750970c2699e4dd792ad55dbe27f41c7` | 668,377 | `higher_education_r_and_d_1991.zip` |
| `690a09194becbe04d5105ddc3d2c11fa7026e86eaa29484ad92e5ef6953cd358` | 664,137 | `higher_education_r_and_d_1992.zip` |
| `af29fac11572b4700d3fda299d2c5d2376e7268dc8c9c04b35036a75b986bf48` | 620,206 | `higher_education_r_and_d_1993.zip` |
| `d879e10fc4651fb1f8484e7a97d6256f18161f5d00fa7c7161de83b5ffee33f0` | 735,437 | `higher_education_r_and_d_1994.zip` |
| `85885aaa37d2485165079d2d2d1f0f5ce1dfac40dccd51cc37152e1152ca95b7` | 786,447 | `higher_education_r_and_d_1995.zip` |
| `c703b9a315ed9baf246e6ab38814296946eeab049e64fa676272035553127db6` | 764,484 | `higher_education_r_and_d_1996.zip` |
| `14fa43dd604d91b344aa93a4e042e04ea2ecd912ebec18cee376de8d2de37053` | 781,973 | `higher_education_r_and_d_1997.zip` |
| `5ecc315c950a0d43f5f2a597aeaa14370efb8981e11392d873dfd525e54be7e3` | 758,666 | `higher_education_r_and_d_1998.zip` |
| `e7b1869599b0a6c3582be8f9f630f260250cba5b602f76fd1a00911be20c9225` | 740,332 | `higher_education_r_and_d_1999.zip` |
| `673d9ba80b7a954ef4c5945a668f64aae222877a2285cbdb831aae2fb73db7ed` | 785,307 | `higher_education_r_and_d_2000.zip` |
| `2f04f54b3088684de6e14c346090f964d09643593681ffd49dec2296b828e724` | 798,388 | `higher_education_r_and_d_2001.zip` |
| `90e130a5dee333c1a8a37f9ffb04bc063d0b9bfc534a36ccefb2240d4d917efe` | 780,345 | `higher_education_r_and_d_2002.zip` |
| `ac9f70d01730e3c8444d9d7b482bd7b49b6cf3a9afa5c380d14f355f5de5bb53` | 1,331,750 | `higher_education_r_and_d_2003.zip` |
| `414e91fd3c1f45d3ebdf080bfd9eb8e71b17f84328eff72a1d63ec572c9af965` | 1,368,108 | `higher_education_r_and_d_2004.zip` |
| `83f7a2adb35e6f278f118c23fdc532de5660a51b770a2a1be746c00afdc5d8d3` | 1,379,552 | `higher_education_r_and_d_2005.zip` |
| `f3ff78fb9b0ee40ab029de8c4e793930887d7f99fcce8a6a5898333f2f82a092` | 1,371,724 | `higher_education_r_and_d_2006.zip` |
| `ceb6e8975f97e8a29ea7bcab07fcb40d68920b6d9301681932971a5556a51e0b` | 1,381,506 | `higher_education_r_and_d_2007.zip` |
| `e23f8d3b558dd544dd4c085d426f39dfb6341036073015ad2d0f3d56121f5891` | 1,416,570 | `higher_education_r_and_d_2008.zip` |
| `b395b6601d11370d96e003f61d94ddd0fcda989056d5eae492333b815bd99e9a` | 1,443,276 | `higher_education_r_and_d_2009.zip` |
| `e2ccc2338ef86d39aefbc5fc3f138caf14d6d4dc0cbf12713386f2a2dc9c9615` | 6,417,489 | `higher_education_r_and_d_2010.zip` |
| `7b73c1f0beb7c4f29a3114cfcff6d3ef53933a945743a9890eb15b1a9d1cb884` | 7,233,335 | `higher_education_r_and_d_2011.zip` |
| `05cc7fdd41f5f31ef6bc58bcdc903f1d14182b945a6d983cb25b3598cab911aa` | 6,531,835 | `higher_education_r_and_d_2012.zip` |
| `ec403c2d009a9fb9dc51f625ae5d743e6a5b2fea5b44efa43a81a78495d94da0` | 6,402,365 | `higher_education_r_and_d_2013.zip` |
| `33dd4b5da5adf0a76c09801aad2abdc34e80ee1c58171ccf6c41836c36bb2f78` | 6,379,067 | `higher_education_r_and_d_2014.zip` |
| `4a5b7ef5b2332fdc0d345e36ce0a2e02090e731d472a6c177d2b74c9acda14f1` | 6,413,775 | `higher_education_r_and_d_2015.zip` |
| `87fb649b0a62950fdcafa761cfd8ac372d8b5df133b1d8179f831b5ea606c980` | 6,018,732 | `higher_education_r_and_d_2016.zip` |
| `a9ee7eae3067455c78c6ea4ff1eed9784aa6b02fa06f60219c9eec0c15814d68` | 6,199,181 | `higher_education_r_and_d_2017.zip` |
| `30f1ccab76713ec0bb899e7eb16f43eed622389b67b414f0623bbbf79f12fb2d` | 6,198,286 | `higher_education_r_and_d_2018.zip` |
| `f73beb48d111051b12d28070842ad4dc94f9d98d95aea3d5ebbc03d719fbc69c` | 6,271,033 | `higher_education_r_and_d_2019.zip` |
| `cb0c928daaf9c2160c932fad4f80089c74a2965b223b7b27835914b1b0a999e6` | 6,265,848 | `higher_education_r_and_d_2020.zip` |
| `bee103cc6a9c07c210e5b4f8117ac18d32b22ffb652c577727d7f39fdeaacc70` | 6,251,852 | `higher_education_r_and_d_2021.zip` |
| `2edf8ce0175b6ad486b4367633dc04f5a2f1400a247cbb41c8b8b002ecea4064` | 6,505,657 | `higher_education_r_and_d_2022.zip` |
| `7cd64fe7f74a598a5a18d66bd0f338c5f75f3984864a045af52615a06178fb1d` | 6,775,654 | `higher_education_r_and_d_2023.zip` |
| `d1fc1df5efe4a6ddf9b333857e36cfc6e28a8eac9430984aa0fadd4968b43f1b` | 7,467,540 | `higher_education_r_and_d_2024.zip` |

## Staged files — `data/raw/herd/short_form/` (short-form, FY 2012–2024)

13 short-form year zips (FY 2012–2024). The short-form public-use files
publish institutions below the FY 2024 Guide page 8 short-form-respondent
threshold (institutions reporting < $1M R&D in the prior fiscal year). The
short-form question structure is a strict subset of the standard-form
instrument; for the financial panel, only Short Form Q2 (`Expenditures
by major field and source` in raw HERD CSVs; `Short form: R&D expenditures
by major R&D field` in FY 2024 Guide canonical form) carries field-level
disaggregation. Aggregate size on disk: ~2 MB.

Staging context. Local stage of short-form files added at HD 2.4.b round
1 (2026-05-10) per Vision verdict Category Short-Form-Q2 Option (b)
locked by maintainer — original scoping doc §9.1 anticipated short-form
inclusion at HD 2.4 but did not stage the files; HD 2.4.b round 1
surfaced the gap (probe
`etl/spikes/probe_short_form_structure.py`) and the maintainer staged the
13 files locally rather than deferring Short Form Q2 to a follow-up round.

Schema. Each short-form CSV is 21 columns:

```
inst_id, year, ncses_inst_id, ipeds_unitid, hbcu_flag, med_sch_flag,
hhe_flag, toi_code, hdg_code, toc_code, inst_name_long, inst_city,
inst_state_code, inst_zip, questionnaire_no, question, row, column,
data, status, othinfo
```

This is the era-B standard-form 23-column schema minus `othinfo_s` and
`standardized_agency_names`. `etl/_load.py:read_herd_short_form_csv`
projects the short-form CSV into the same `UNIFIED_COLS` schema the
standard-form loader emits, with the two missing era-B columns NULL.

| SHA-256 | Bytes | File |
|---------|-------|------|
| `4269af90242d172336c1d98bfae4933c95baea71c2d0e82cc485b2005cfda355` | 165,790 | `short_form/higher_education_r_and_d_2012_short.zip` |
| `960069e5f56a7a8e01e650f8aead4e08e1fec0923721787a32391ea1b3fe9a17` | 153,328 | `short_form/higher_education_r_and_d_2013_short.zip` |
| `18a26ed2b5cd6198041c639308d661ec9fc196f3a8076d5318217a66417cc9e2` | 163,258 | `short_form/higher_education_r_and_d_2014_short.zip` |
| `4819c234b0df0e23464b324abafec55ecbafdc4b505ef6d23e25cbe2ec3118c9` | 164,975 | `short_form/higher_education_r_and_d_2015_short.zip` |
| `6f23651188750e5132826483e4bf06c242df96c5f6f43095c2e3cd3bfa2ac1ca` | 165,947 | `short_form/higher_education_r_and_d_2016_short.zip` |
| `62b01c1dd2cb16d2fa58215a0c374b555277f3e985b990702f8fa47d878a0287` | 158,969 | `short_form/higher_education_r_and_d_2017_short.zip` |
| `1d9ae78927ca1fb3603e54d350db5ce6c4eb7dc3bf9e1b0cd979b9c0102c08a1` | 170,273 | `short_form/higher_education_r_and_d_2018_short.zip` |
| `f733b02f976e86f8bed60779daef621023971c21fabd829b00e3730f6a100fe8` | 170,921 | `short_form/higher_education_r_and_d_2019_short.zip` |
| `820a9704879512e180e40e0b46eb7c6307da240649227fa4724f1ee017698261` | 163,729 | `short_form/higher_education_r_and_d_2020_short.zip` |
| `b920874bf295e6c5bf0e9de7a9df4a285c02a612eac9590e284e440e0a1085be` | 163,813 | `short_form/higher_education_r_and_d_2021_short.zip` |
| `f53bb7dee5a8d9df0805da90d7634373b793e046cbdd1b9010bcfaf266e9e369` | 169,519 | `short_form/higher_education_r_and_d_2022_short.zip` |
| `11a719246b5450882286a76858237212fa0c672b0e1a7aac89a8c087018dd455` | 156,747 | `short_form/higher_education_r_and_d_2023_short.zip` |
| `2315d3777e2e40e05d46f7fb91ef9a59d8101ebeaa8538f0bc9a3330ba0d78ec` | 157,193 | `short_form/higher_education_r_and_d_2024_short.zip` |

Inside each zip: `short{year}.csv` plus `short{year}.sas7bdat`. The
CSV member is the canonical source for the loader; the SAS file is
fallback only.

## Staged files — `data/raw/fedsupport/` (Federal S&E Support, dataset #2)

Generated: 2026-05-29 (Skipper, HD 3.2 MVP). Mirrors the HERD zip-provenance
model with one difference: the deposit artifact is a **CSV**, not the source
xlsx. NSF publishes Federal S&E Support Table 12 as **xlsx** (+ PDF + ZIP);
the locked acquisition contract (CLAUDE.md §3) converts xlsx→CSV **once at
acquisition** (DuckDB `excel` extension, a one-time step) and stages the CSV
as the artifact the loader reads via `read_csv_auto`. The §3 no-runtime-
extension lock binds the deposit **build path**, not the one-time conversion;
this keeps the cold-reader reproducibility contract intact (no runtime
extension fetch, no build-time network dependency).

`data/raw/fedsupport/` is **gitignored** (payload); these MANIFEST entries
are tracked. The PDF **audit sibling** per year lives in `data/reference/`
(see `data/reference/MANIFEST.md`) as the human-readable provenance anchor,
mirroring the FY24 Guide PDF and the Table-26 anchors.

**Survey:** NSF *Survey of Federal Science and Engineering Support to
Universities, Colleges, and Nonprofit Institutions*. Table 12 = higher-ed
institution-level federal obligations by state / institution / type of
activity (higher-ed-ONLY; nonprofit lives in separate tables — do NOT
free-sum, HD 3.1 §2). Report numbers: FY2020 NSF 22-342, FY2021 NSF 24-311,
FY2022 NSF 24-326, FY2023 NSF 25-339.

The deposit artifact (CSV) — what the loader reads:

| SHA-256 | Bytes | File |
|---------|-------|------|
| `3c68f81bf24558ae0529d08e339df39dc7da2706223863709c876ff963b3f45b` | 57,944 | `nsf22342-tab012-FY2020.csv` |
| `bd4f0de02f7bf7f0b0ce267d1602250019ada9fcd42ad6703f0166ac6f3d853d` | 63,101 | `nsf24311-tab012-FY2021.csv` |
| `a56b3ba42304bc51aa1e58de24d5948bf897c756861cdeb9cb4e3feee576376b` | 63,554 | `nsf24326-tab012-FY2022.csv` |
| `309f3d11705d9a39304e9802100938a05db89c791c63b347e60dfa288786affa` | 64,093 | `nsf25339-tab012-FY2023.csv` |

Source-of-record (xlsx) provenance — NOT staged as a deposit artifact (kept
under gitignored spike scratch); recorded so a future session can re-fetch
the same upstream xlsx, re-convert, and confirm the CSV. URLs follow the
stable pattern `https://ncses.nsf.gov/pubs/{report}/assets/data-tables/tables/{report}-tab012.xlsx`:

| xlsx SHA-256 | Bytes | Report (xlsx) | gate cross-check |
|---------|-------|------|------|
| `e4fb34bff7a0b78d9531d08f507112159e7cdd56bfa3229685a8055d68503663` | 77,170 | nsf22342 (FY2020) | == HD 3.1 §7 |
| `364f0f85d7af1f083db67d16bc00096847c1b5f9160b22c25f531d65523140e8` | 77,318 | nsf24311 (FY2021) | == HD 3.1 §7 |
| `98f2b3601b49c8054173fe7aa8c0993e54781d7fd2050915ebae2adfb89d8b1b` | 77,858 | nsf24326 (FY2022) | new (HD 3.1 had no FY2022) |
| `dea92dcecb94ba72333c5dd39b6a8b4c0046124b9e135bea01a30ac94c5b73c7` | 79,443 | nsf25339 (FY2023) | == HD 3.1 §7 (re-verified) |

xlsx→CSV conversion (one-time, at acquisition):

```powershell
# DuckDB excel extension; read the full A1:G1200 range (the A1 title band
# makes the extension auto-detect a 1-col sheet otherwise — HD 3.2 §8.1) and
# COPY to a headerless CSV the loader reads via read_csv_auto.
duckdb -c "INSTALL excel; LOAD excel;
COPY (SELECT * FROM read_xlsx('{report}-tab012.xlsx', header=false,
  all_varchar=true, range='A1:G1200', stop_at_empty=false))
TO '{report}-tab012-FY{year}.csv' (HEADER false, QUOTE '\"');"
```

## Regeneration

To recompute the checksum list (Windows PowerShell):

```powershell
Get-ChildItem data/raw/herd/ | Sort-Object Name | ForEach-Object {
  $h = (Get-FileHash -Algorithm SHA256 $_.FullName).Hash.ToLower()
  "{0}  {1}  {2}" -f $h, $_.Length, $_.Name
} | Set-Content -Encoding utf8 data/raw/herd/_checksums.txt
```

POSIX:

```bash
cd data/raw/herd && sha256sum -- * > _checksums.txt
```

If a recomputed hash diverges from this manifest, the staged file has
drifted from the NSF distribution — re-extract from `NSF_HERD.zip` and
verify against the source-archive hash above before continuing.
