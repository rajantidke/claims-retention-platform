# Progress Log

Running log of work done, issues hit, and how they were resolved.
Kept as a debugging trail and a memory aid across sessions — not a polished doc.

---

## 2026-09-01 — Week 2, Step 0-1: Preflight + repo scaffold

**Environment**
- Python 3.12.8, git 2.43.0, WSL2 (Ubuntu), repo kept under `/mnt/c/...` by choice
  (native-Linux move considered and declined; will symlink `data/` to native fs
  later if ingest I/O turns out too slow).
- Installed `uv` 0.12.9 via astral.sh installer.

**Repo init**
- `git init` defaulted to `master` branch — renamed to `main` via `git branch -m main`.
- Directory skeleton created. First `mkdir -p ... experiments/{simulation, observational} ...`
  attempt failed silently: space after the comma inside `{}` broke brace expansion,
  producing literal dirs `{simulation,` and `observational}` instead of expanding.
  Re-ran without the space; cleaned up stray dirs manually (`rm -r`).

**.gitignore**
- Hand-typed instead of pasted; introduced two typos that would have silently
  broken ignoring: `__pychache__/` (should be `__pycache__/`) and `.gagster/`
  (should be `.dagster/`). Fixed via `sed`.
- Known latent issue (not yet fixed, intentional — revisit in Step 5): the
  `!data/samples/*.csv` negation won't work as written because the earlier
  `data/` line excludes the whole directory before git evaluates the negation.
  Needs `!data/samples/` added before the wildcard negation once the CI fixture
  actually exists.

**Secret scanning**
- Installed `pre-commit`, `detect-secrets`, `ruff` via `uv pip install`.
- First `detect-secrets scan` output was accidentally redirected to `.secret.baseline`
  (missing the `s` in `secrets`) — renamed to match the filename referenced in
  `.pre-commit-config.yaml`.
- `.pre-commit-config.yaml` created, `pre-commit install` succeeded
  → hook live at `.git/hooks/pre-commit`.

**pyproject.toml / uv pip install -e ".[dev]"**
- First install attempt failed: setuptools flat-layout auto-discovery choked
  because top-level dirs like `data/`, `notebooks/`, `reports/` sit alongside
  real packages (`ingest/`, `models/`, `experiments/`, `tests/`), and it
  refused to guess which were packages.
  Fix: added explicit `[tool.setuptools.packages.find]` with `include =
  ["ingest*", "models*", "experiments*", "tests*"]`.
- Retried, succeeded — 102 packages installed in ~3m52s (slow due to `/mnt/c`
  I/O, one-time cost, not a recurring concern).
- Verified imports: duckdb 1.5.5, polars 1.44.1, pandas 3.0.5 — all resolve
  correctly in editable install.

**Status:** Step 1 environment fully set up. Not yet committed to git.

---

## 2026-09-01 — Week 2, Step 1 (cont.): First commit + GitHub push

**Issue: trailing-whitespace hook blocked first commit attempt**
- `.gitignore` had trailing spaces on a couple of inline-comment lines.
  pre-commit's `trailing-whitespace` hook auto-fixed and blocked the commit
  for review (expected/correct behavior — hooks don't silently modify staged
  content past you).
- While reviewing the fix, noticed `^M` (CRLF) characters in the diff — the
  file had Windows-style line endings, likely from hand-typing through a
  Windows-side WSL terminal/clipboard interaction.
- Fixed properly rather than just re-committing: added `.gitattributes`
  (`* text=auto eol=lf`) to force LF repo-wide going forward, and normalized
  `.gitignore` with `sed -i 's/\r$//'`. Committed `.gitattributes` separately
  since it was missed in the first pass.

**Issue: egg-info directory almost got committed**
- `uv pip install -e ".[dev]"` generates `claims_retention_platform.egg-info/`
  as build metadata. Caught it in `git status` before committing — added
  `*.egg-info/` to `.gitignore`.

**GitHub auth**
- `gh` wasn't installed; installed via `apt` (not `snap` — snap can be
  unreliable under WSL due to systemd quirks).
- `gh auth login` browser auto-open failed (no `xdg-open`/`wslview` in WSL
  PATH) — expected, worked fine by manually opening
  github.com/login/device and entering the one-time code.
- First login attempt hit GitHub's rate limit (`slow_down`) from firing
  `gh auth login` twice in quick succession — second attempt after a short
  wait succeeded.

**Result**
- Repo live and public: https://github.com/rajantidke/claims-retention-platform
- 3 commits on `main`: scaffold + gitattributes fix + this log entry.

**Status:** Step 1 complete. Next: Step 2 — read SynPUF documentation
(Data Users Document, codebook, FAQ) before writing any ingest code.

---

## 2026-09-20 — Week 2, Step 3 (cont.): Formalized Sample 1/20 check as pytest

- The Sample 1 vs Sample 20 verification was originally run as a disposable
  terminal one-off (see prior entry). The runbook explicitly calls for this
  to be written as a pytest test, not a manual check — missed that the first
  time round.
- Added `tests/test_sample_integrity.py`: parametrized beneficiary-count
  check against codebook Table 2 figures (2008/2009/2010) plus the
  2010-overlaps-with-2008 check, both now automated and rerunnable via
  `pytest` / the Makefile's `make test` target.
- One typo caught on first run (`excepted` for `expected` — a NameError,
  not a logic bug) and fixed via sed.
- All 4 tests passing against the actual downloaded data, confirming the
  earlier manual result (Sample 1 confirmed, not Sample 20).

**Status:** Step 3 fully complete, now with a durable regression test.
Next: Step 4 — load raw CSVs into DuckDB.

## 2026-09-20 — Week 2, Step 4: Load raw CSVs into DuckDB

**Build**
- Wrote `ingest/load_raw.py`: loads all 8 raw CSVs into `data/claims.duckdb`
  under a `raw` schema, zero transformation, `all_varchar=true` throughout
  to protect leading-zero codes (NDC, ICD-9, county codes) from type
  inference. Beneficiary years unioned with a `source_year` tag; carrier
  segments A/B unioned without one (both already span all 3 years).
- Walked through the script chunk-by-chunk before running rather than
  running it blind, specifically to build real understanding of DuckDB's
  `read_csv_auto`, schemas, and `UNION ALL BY NAME` — not just to get a
  working pipeline.

**Bugs caught on manual transcription (hand-typing from the walkthrough
into VS Code, not copy-paste)**
- 2010 beneficiary block copy-pasted with `source_year = 2009` (leftover
  from the 2009 block above it) — a silent data bug, would not have thrown
  an error, would have mislabeled every 2010 row as 2009 and left
  `source_year = 2010` empty. Caught on review before running.
- Carrier Sample B filename typed as `Sample_1b.csv` (lowercase) vs actual
  file `Sample_1B.csv` (uppercase) — would have crashed with file-not-found
  on Linux's case-sensitive filesystem. Caught on review before running.

**Result — all row counts match codebook Table 2 (Sample 1) exactly**
- beneficiary: 343,644 (116,352 + 114,538 + 112,754 across 2008/2009/2010)
- inpatient: 66,773
- outpatient: 790,790
- pde: 5,552,421
- carrier: 4,741,335 (A+B combined)
- Runtime: ~1 minute end to end, faster than the worst-case `/mnt/c` I/O
  estimate from Step 0.

**Status:** Step 4 complete, all 8 raw tables loaded and row-count-verified.
Next: Step 5 — build the 1k-person CI fixture from `data/samples/`.

## 2026-09-21 — Week 2, Step 4 (cont.): Makefile added; .gitignore negation fixed

**Makefile**
- Runbook's Step 4 includes a Makefile (`setup`, `download`, `ingest`, `test`,
  `clean` targets). Added it since CI (Week 8) and the fixture step both assume
  `make` targets exist.
- Adjusted `download` target: runbook's version shells to
  `python -m ingest.download`, but that script was never written (manual
  download was the deliberate call in Step 3). `download` is now a stub
  that prints where the files actually came from, and `ingest` no longer
  depends on it.
- Verified `make test` runs the pytest suite correctly; `make ingest` rebuilds
  the DuckDB tables cleanly via `CREATE OR REPLACE`.

**.gitignore — samples negation bug fixed (flagged since Step 1)**
- `!data/samples/*.csv` was present since Step 1 but non-functional: `data/`
  excluded the whole directory before git would evaluate the negation, and
  `*.csv` appearing *after* the negation lines re-excluded everything anyway
  (later rules win in .gitignore precedence).
- Fixed by adding `!data/samples/` (un-excludes the directory itself) and
  reordering so both negations come after all broad exclude patterns, not
  before.
- Verification pending: will confirm with `git check-ignore -v` once sample
  CSVs exist (Step 5).

**Status:** Makefile and .gitignore fix complete. Proceeding to Step 5 —
build the 1k-person CI fixture.

## 2026-09-XX — Week 2, Step 5: 1k-person CI fixture

**Build**
- Wrote `ingest/build_fixture.py`: samples 1,000 distinct DESYNPUF_IDs via
  reservoir sampling (fixed seed for reproducibility), registers them as a
  DuckDB temp table, and joins against each of the 5 raw tables to extract
  every row belonging to sampled beneficiaries, writing each to
  `data/samples/*.csv`.
- First attempt used `bernoulli` sampling, which failed: DuckDB's bernoulli
  method only accepts a percentage, not a fixed row count. Switched to
  `reservoir`, which supports exact counts directly.

**Result**
- 1,000 beneficiaries sampled; 2,945 / 656 / 7,532 / 45,798 / 44,241 rows
  extracted for beneficiary / inpatient / outpatient / pde / carrier
  respectively. Total fixture size: 28MB (carrier alone: 22MB, due to its
  142-column width).

**`.gitignore` — root cause of the samples-negation bug finally found and fixed**
- Confirmed via an isolated test repo that git's ignore-matching short-circuits
  at the directory level: once `data/` is excluded as a whole directory, no
  negation pattern for anything inside it (`!data/samples/`, etc.) can ever
  override that, regardless of ordering. This is documented git behavior,
  not a bug in our pattern.
- Fixed by removing the blanket `data/` exclude entirely and instead
  excluding `data/raw/` and `data/interim/` specifically by name, plus
  `*.duckdb`/`*.zip`. `data/samples/` is never mentioned in an exclude
  pattern, so nothing needs to be negated.
- Verified with `git check-ignore -v` against all three cases: samples CSV
  (not ignored, correctly), raw CSV (ignored), and the .duckdb file (ignored).

**Pre-commit tooling adjustments**
- `check-added-large-files` default of 5MB was too low for the carrier
  fixture (22MB, due to its wide 142-column schema) — raised to 30MB rather
  than shrinking the beneficiary sample, since 1,000 people already gives
  good edge-case coverage and 30MB still comfortably blocks any accidental
  full-size raw file commit.
- `detect-secrets` took 3-5 minutes scanning the large CSVs' cell contents
  for entropy on first commit — added `exclude: '^data/'` to the hook config
  so future commits touching `data/samples/` don't pay this cost repeatedly.
  No actual secrets risk in claims-code data, so excluding it is safe.

**Status:** Step 5 complete. Next: Step 6 — the 12-question EDA.
---
## Template for future entries

## YYYY-MM-DD — Week N, Step X: <short description>

**What was attempted**

**What broke / issue faced**

**Root cause**

**Fix**

**Status / what's next**
