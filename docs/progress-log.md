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

## 2026-09-21 — Week 2, Step 5: 1k-person CI fixture

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

## 2026-09-21 — Week 2, Step 6: The 12 crucial question EDA (interim checkpoint)

**Build**
- Built `notebooks/01_raw_profiling.ipynb` — question-by-question structure,
  each chart displayed inline after its analysis(notebook is scratch; `docs/data_quality_report.md` is the real   deliverable, not yet written).
- Confirmed JupyterLab kernel correctly resolves to this project's `.venv`
  (`which jupyter` → `.venv/bin/jupyter`; `python3` kernel auto-registered
  from the venv install) before starting.

**Status: all 12 EDA questions answered, all 4 required charts built.**

**Key findings (full detail in the notebook) :**

1. **Row counts, beneficiary overlap, orphan claims — all clean.** Row
   counts match codebook Table 2 exactly; 0 orphan claims across all 4
   claims tables; Sample 1 (not Sample 20) reconfirmed a third time.
2. **Severe right-censoring from ~Jan 2010, worsening through Nov 2010** —
   all 4 claims tables show a 70-80% volume drop from their 2008-2009
   plateau by the final month. Diagnosed as a claims-lag/reporting-delay
   artifact, not real discontinuation. Flagged as the most consequential
   single finding — has direct design implications for persistence/
   adherence logic in later weeks (index dates and outcome windows near
   the end of 2010 will need explicit censoring treatment).
3. **Individual PDE product codes (`PROD_SRVC_ID`) do not reliably track
   real drug identity.** Format is preserved (valid 11-digit NDC structure,
   leading zeros intact) but individual-code fill volume is nearly flat
   (top code = 0.0037% of all fills) and a manual 39-fill sequence read for
   one beneficiary showed zero repeated product codes. 5-digit labeler
   (manufacturer) code, by contrast, shows real concentration (top labeler
   = 11% of all fills). Refill *timing/cadence* looks realistic; product
   *identity* does not. Directly affects feasibility of any planned
   NDC-to-drug-class therapy cohort definition — likely needs a coarser
   (labeler-level) or empirical (this-dataset's-own-rankings) approach
   instead of a real-world crosswalk.
4. **Chronic condition prevalence runs 1.6-2.4x higher than real Medicare**
   across all 11 flags, systematically (not random) — independently
   reproduced the codebook's own published figures to the decimal, then
   confirmed against real-Medicare reference rates with a chart.
5. **Correlation-degradation pattern found via 3 variable pairs, with a
   coherent explanatory mechanism**: age↔chronic-condition-count fell to
   r=0.086 (essentially broken, with a concrete non-monotonic dip at ages
   60-69); inpatient-admissions↔IP-reimbursement held at r=0.643
   (mechanical/claim-level relationship, survives synthesis); chronic-
   condition-count↔total-reimbursement landed at r=0.553 (real clinical
   signal, partially preserved). Pattern: relationships internal to a
   single claim survive; relationships requiring preserved structure
   *across* independently-synthesized parts of a record degrade.
6. **14.5% of beneficiaries have zero PDE fills across all 3 years** —
   relevant to Module A's funnel/activation framing.
7. Deviated from the runbook's suggested Q12 third pair (diabetes flag vs.
   antidiabetic fills) — not answerable given finding #3 above — substituted
   chronic-condition-count vs. total-reimbursement instead, with the
   substitution explicitly justified in the notebook.

**Status:** Steps 1-6 all complete except the written report (Step 7).
Evaluating the findings to reshape strategy before proceeding, in case any
of the above (especially #2 right-censoring and #3 product-code
unreliability) changes sequencing or scope for Weeks 3+. Report assembly
resumes after that check-in.

---

## 2026-09-23 — Week 2, Steps 6 and 7: Strategy review, six fidelity gates, spec v2, fidelity_audit.md

**Strategy review caught two real analysis errors before anything was
written down permanently**
- Q12 Pair 1 (age vs. chronic condition count) was misread as "broken
  by synthesis." The 60-69 age dip is real Medicare structure — under-65
  beneficiaries qualify via disability/ESRD and are systematically sicker
  than people who "aged in" normally at 65. Recomputed on 65+ only using
  Spearman: 0.159, clean monotonic increase across decade buckets
  (1.70 → 2.23 → 2.67 → 2.80), no dip. Weaker in magnitude than the
  qualitative trend suggests, but genuinely real and no longer "broken."
- Q12 Pair 2 (inpatient admissions vs. IP reimbursement) had a real bug:
  admissions counted across all 3 years, joined to 2008-only
  reimbursement. Fixed to restrict both sides to 2008. Correlation rose
  from a buggy 0.643 to a corrected 0.828, and the average cost per
  admission became clinically plausible ($8,503 vs. the old, implausible
  $1,994) — strengthens rather than weakens the original mechanism-based
  explanation (claim-internal relationships survive synthesis intact).
- The "claims lag" explanation for the 2010 decline was also flagged as
  wrong — real claims lag only softens the last few months of a dataset,
  it doesn't start in January and deepen for eleven months. Confirmed via
  Gate 4 below.

**Six fidelity gates built in the notebook, each with a decision
pre-committed for every possible outcome before running:**
1. Population-wide refill-pair check: 0.06% of (beneficiary, product)
   pairs ever repeat; 17.78% at the labeler level. Confirms the Q9 finding
   generalizes across the whole file, not just one beneficiary.
2. Labeler concentration vs. shuffle null: real and shuffled distributions
   statistically indistinguishable (mean 0.2162 vs 0.2158). No real
   person-level manufacturer-clustering signal exists.
3. 90-day-share vs. shuffle null: real but modest signal (KS=0.051,
   p=4.22e-113; means 0.1162 vs 0.1073). Statistically real, practically
   small.
4. Monthly plateau threshold: Feb 2010 already 15% below the 2009 plateau
   (1.349 vs 1.418 threshold); Dec 2010 at 25% of plateau. Decisively
   rules out claims lag as the explanation — sets Feb 2010 as the hard
   cutoff for the clean analysis window.
5. FDA NDC Directory lookup on top 5 labeler codes by fill volume: zero
   matches. Two labelers further down the ranking (55289, 51079) are real
   companies, one a repackager (PD-Rx) — wording softened per review to
   note the directory only covers currently-marketed products, so this is
   supporting evidence, not conclusive; Gate 2 is the stronger proof.
6. Timing structure, three sub-tests, restricted to the clean (pre-Feb 2010) window:
   - Test 1: days-supply vs. next-fill-gap — real diff 1.0 day, shuffled
     diff 2.0 days. Fails; PDC unreliable as a metric.
   - Test 2: fill-count-preserving date redraw — real vs. redrawn
     statistically identical on CV of gaps, 60+-day-gap share, and
     resume-within-90-days rate. Fails, decisively — a long gap in this
     file is arithmetic (fill count ÷ window), not a real behavioral stop.
   - Test 3: file connectivity (fill count vs. chronic conditions,
     ρ=0.240; vs. admissions, ρ=0.120). Passes on the stronger correlation
     — PDE is meaningfully connected to the rest of the record, plasmode
     simulation can use real linked covariates.

**Verdict from strategy review: project confirmed viable.** The four
"dataset" findings (drug identity, labeler clustering, the drug-class
comparator, and the withdrawn 90-day design) all trace to one mechanism —
claim-level attributes are synthesized nearly independently of the person
— not a climbing rate of unrelated problems. Spec patched to v2 (v1
archived) as a result:
- Module A: primary metric moved from PDC to monthly-active engagement
  (any fill that month); PDC still computed, reported as unreliable.
  Utilization mart promoted from optional to core.
- Module C: drug-class active-comparator design replaced with a plasmode
  simulation on a real hospitalization cohort (real covariates, washout,
  index date, Table 1; simulated treatment/outcome with known truth;
  200 reps/scenario; includes a hidden-confounder scenario to validate
  the E-value against a known answer).
- Module D: snapshot-based temporal split (train Jan 1 2009, test Jul 1
  2009), non-overlapping labels by construction; Jul 2010 snapshot
  reserved to demonstrate the drift monitor firing.
- Module E: fixed so claims and clinical definitions are measured on the
  same Synthea patients.
- Analysis index window: beneficiaries with a relevant event ~July 2008 –
  July 2009, outcomes measured before the Feb 2010 data-quality cutoff.


**Gate code and report written up as permanent deliverables**
- All 6 gates ported from notebook cells into `audit/fidelity.py`
  (one function per gate/sub-test, a `main()` that runs and prints all of
  them), with a `make audit` target added to the Makefile. Verified the
  module reproduces every notebook number exactly (Gate 6 Test 2's numbers
  differ by ~0.1% between runs due to randomization order, not a
  discrepancy — same conclusion either way).
- Wrote `docs/fidelity_audit.md`: the full writeup, in order (project →
  data → EDA findings → the six gates → constraints → what changed in the
  spec as a result). Built section by section over several passes to get
  the tone right — plain, first-person, no unnecessary jargon-heavy
  phrasing — rather than reading like a compliance document.
- Also produced `docs/progress-log.md` companion note: a proposed
  clustering-based EDA extension (k-means on beneficiary/claims data
  against condition flags and ICD codes) was considered mid-report-writing
  and deliberately deferred rather than added — the gates already answer
  the relevant questions with sharper, hypothesis-driven tests, and
  clustering would be a step backward in rigor for this specific purpose.

**Status: Week 2 is complete.** Repo scaffolded, data downloaded/verified/
loaded, CI fixture built, 12-question EDA answered, 2 real analysis
mistakes caught and fixed, 6 independently-designed fidelity gates run
and ported into a reusable module, project viability confirmed, spec
patched to v2, and the full findings written up in `docs/fidelity_audit.md`.
Next: Week 3/4 — dbt initialization and staging models.

---
## 2026-09-25 — Week 3 close-out: dbt initialization

**Part 0 review fixes (all 7 items) closed out first** : see prior entries
for the detailed determinism fixes, figures/JSON output, evidence table,
tone edits, bucket relabel, and the new automated determinism test suite
in `tests/test_audit_determinism.py`.

**dbt scaffold built by hand** (not `dbt init`, which would have fought the
existing `transform/` layout):
- `dbt-core>=1.8,<2.0` and `dbt-duckdb>=1.8,<2.0` installed (resolved to
  1.12.5 / 1.11.0).
- `transform/dbt_project.yml`: model-paths/seed-paths/etc. declared,
  analysis-boundary vars (`clean_window_end`, `study_start`, `gap_days`,
  `washout_days`) centralized rather than hardcoded per-model, and default
  materializations set per folder (staging=view, intermediate/marts=table).
- `transform/packages.yml` + `dbt deps`: installed `dbt_utils` 1.4.1 for
  its test/utility macros, needed by Week 4's reconciliation tests.
- `transform/profiles.yml`: `dev` (full DB) and `ci` (1k-fixture) targets,
  plus a v1.1 Snowflake placeholder block using only `env_var()` — no real
  credentials ever required. `.gitignore`'s bare `profiles.yml` exclusion
  negated specifically for `transform/profiles.yml` (verified working via
  `git add` + `git status`, not just `git check-ignore -v`, since that
  command's exit-code semantics were confusingly ambiguous on a
  negation-matched file during testing).
- `transform/models/staging/_sources.yml`: the 5 raw tables declared as
  dbt sources, with a description noting the all-VARCHAR loading choice.

**Two real mistakes caught before committing, not invented independently:**
- `clean_window_end` was initially set to `2010-02-01` (the first *bad*
  day per Gate 4) instead of `2010-01-31` (the last *good* day): would
  have silently included one day of already-unreliable February data in
  every "clean" query.
- The Makefile's dbt invocation used `cd transform && dbt build`, which is
  inconsistent with `profiles.yml`'s repo-root-relative paths
  (`data/claims.duckdb`, not `../data/claims.duckdb`). Rebuilt the
  Makefile around a `$(DBT)` variable using `--project-dir`/
  `--profiles-dir` flags, run from the repo root — this is also what the
  runbook specifies and what `dbt build --target ci` will expect to work
  consistently with later.
- Along the way: `dbt`'s CLI wanted `--project-dir`/`--profiles-dir`
  placed *after* the subcommand (`dbt build --project-dir ...`), not
  before (`dbt --project-dir ... build`) — a version-specific CLI quirk,
  not a config error.

**Verification**
- `dbt debug`: all checks passed, connection confirmed.
- `dbt list --resource-type source`: all 5 sources correctly recognized.
- Smoke test: one throwaway model `select count(*) from
  {{ source('raw','pde') }}`) built successfully via `make build`
  (`PASS=1 WARN=0 ERROR=0`), then deleted, confirming the full profile →
  project → source → model chain works end-to-end before writing any
  real model.

**Status: Week 3 is now fully closed**: the fidelity audit (main
substance of Week 3) was completed earlier; this closes out the
carried-over dbt-initialization portion. Next: Week 4: staging
models, seeds, and intermediate models.

---
## 2026-09-27 — Week 4, Part 2: Staging models — grain discovery on inpatient/outpatient

**Build**
- `stg_beneficiary`, `stg_pde` built cleanly on first pass (after two dbt
  test-syntax deprecation fixes, `accepted_values` and `equal_rowcount`
  both needed arguments nested under a new `arguments:` key in dbt 1.12).
- `stg_inpatient`/`stg_outpatient`: initial `unique` test on `claim_id`
  failed, 68 duplicates in inpatient, 10,975 in outpatient.

**Investigation before fixing (per runbook: "don't work around it, record the actual grain")**
- Queried the duplicate `claim_id`s directly: every one had exactly 2 rows,
  split across `SEGMENT` values 1 and 2 — not a data error, a real second
  grain dimension.
- Checked the codebook before implementing anything: `SEGMENT` represents
  CMS's claim-line-segment mechanism (one segment per 45 revenue lines),
  but the codebook also states it was capped at 2 and suppressed as part
  of disclosure treatment, same category of caution as the other fields
  the fidelity audit already flagged (product codes, days-supply, chronic
  conditions). Worth checking before writing the fix, not after.

**Fix**
- True grain is `(claim_id, segment)`, not `claim_id` alone. Added
  `claim_segment` to both staging models, replaced the single-column
  `unique` test with `dbt_utils.unique_combination_of_columns` on
  `[claim_id, claim_segment]`.
- Documented `claim_segment` in both model descriptions as grain-completing
  only, not a trustworthy analytical variable in its own right, same
  treatment as `product_service_id`/`days_supply` elsewhere.

**Status:** All 4 staging models built (beneficiary, pde, inpatient,
outpatient), 21/21 tests passing including composite-key reconciliation.
Next: stg_carrier (minimal, per runbook's trim guidance), then the seed
file and intermediate models.

---
## 2026-09-27 — Week 4, Part 2 (cont.): int_fill_events and int_member_months

**int_fill_events**
- Built on `stg_pde`: added `in_clean_window` (Gate 4's Feb 2010 cutoff,
  read from the `clean_window_end` var rather than hardcoded),
  `is_zero_days_supply`, and `coverage_start`/`coverage_end` (null when
  zero days-supply). First model to actually consume the `vars` block set
  up in Part 1, and the first to use `ref()` instead of `source()`.
- 35/35 tests passing, `equal_rowcount` against `stg_pde` confirmed 1:1.

**int_member_months — the fiddly one**
- Month spine (`generate_series`, 2008-01 through 2010-12, 36 months)
  cross-joined against all distinct beneficiaries (~116k × 36 ≈ 4.19M rows
  expected), joined back to `stg_beneficiary` on `(beneficiary_id,
  source_year = month_year)` to pull the correct year's demographic/
  coverage snapshot per month.
- Built in ~3 seconds despite the row count, DuckDB handled the
  cross-join efficiently, no performance concerns.
- `has_full_year_part_d` encodes the real enrollment-precision limitation:
  DE-SynPUF gives coverage-month *counts* per year, not *which* months,
  so month-level analysis is only trustworthy for beneficiaries with all
  12 months of coverage in a given year.
- **Exclusion size, now measured as the runbook required**: of 116,352
  total beneficiaries, 94,564 (81.3%) have at least one full year of Part D
  coverage; 21,788 (18.7%) do not and are excluded from month-level
  enrollment-precision analysis. This number goes in the README once
  written and will need restating whenever a reviewer asks about the
  denominator.
- Composite uniqueness test on `(beneficiary_id, month_start)` and a
  singular test (`assert_no_alive_months_after_death`) both passing —
  confirms no beneficiary is marked "alive" for a month after their
  recorded death date.

**Status:**  7 models total (5 staging + 2 intermediate), 40/40 tests
passing. Next: `int_coverage_spells` (gaps-and-islands merge, deliberately
non-recursive per the Gate 6 PDC-demotion reasoning), then closing out
Week 4.

---
## 2026-09-27 — Week 3 + Week 4 complete: dbt foundation, staging, intermediate

**Full scope closed in this stretch:** the six review fixes carried over
from the strategy session (Part 0), the dbt initialization outstanding
from Week 3 (Part 1), and all of Week 4's staging/seed/intermediate
modeling (Part 2). See prior entries for Part 0's detail; this entry
covers Parts 1-2.

**Part 1 — dbt initialization**
- Installed `dbt-core`/`dbt-duckdb` (1.12.5 / 1.11.0), scaffolded
  `transform/` by hand rather than `dbt init`.
- Caught two real gaps against the runbook before committing: `clean_window_end`
  was initially set to `2010-02-01` (first bad day) instead of `2010-01-31`
  (last good day per Gate 4); the Makefile's dbt invocation was
  inconsistent with `profiles.yml`'s repo-root-relative paths. Both fixed
  before any model was built on top of them.
- Also resolved along the way: a stale `ruff-pre-commit` git tag (`v0.6.9`
  no longer resolvable, bumped to `v0.16.4`), and a `.pre-commit-config.yaml`
  structural bug (a missing `- repo:` line had merged two hook blocks into
  one, causing pre-commit to check out the wrong tag for the wrong repo).
- `dbt debug`, source listing, and a throwaway smoke test all confirmed
  the full profile → project → source → model chain before real modeling
  began.

**Part 2 — staging layer (5 models)**
- `stg_beneficiary`, `stg_pde`, `stg_carrier` built per spec, each with
  `equal_rowcount` reconciliation against its raw source.
- `stg_inpatient`/`stg_outpatient`: initial `unique` test on `claim_id`
  failed (68 and 10,975 duplicates respectively). Investigated rather than
  worked around — every duplicate had exactly 2 rows split across
  `SEGMENT` values 1/2. Checked the actual DE-SynPUF codebook before
  fixing: `SEGMENT` is a real CMS claim-line mechanism, but was itself
  capped at 2 and suppressed as part of disclosure treatment — so it's
  used here only to complete the true grain `(claim_id, segment)`, not
  treated as a trustworthy analytical variable. Composite-key test via
  `dbt_utils.unique_combination_of_columns` replaces the single-column test.
- Closed two gaps found on review against the full runbook spec after
  staging was "done": added `labeler_cd` to `stg_pde` (documented as
  derived-for-convenience only, given Gate 2 already showed no real
  person-level signal there) and a `dbt_utils.accepted_range` test on
  `days_supply` (0-365).
- `seed_code_lists.csv` (2 concepts, ICD9+ICD10) loaded via `dbt seed`,
  with an `accepted_values` schema test and a singular test
  (`assert_code_lists_have_both_systems`) guaranteeing every concept has
  both coding systems — the check that makes "swap in a modern extract,
  the pipeline stays valid" a real, tested claim rather than aspirational.
- Created `FUTURE_WORK.md`: logged the Week 2 clustering-as-EDA idea
  (deferred, gates already answer the relevant questions more rigorously)
  and, later, the `int_coverage_spells` stockpiling approximation.

**Part 2 — intermediate layer (3 models)**
- `int_fill_events`: derived `in_clean_window` (first real use of the
  `clean_window_end` var), `is_zero_days_supply`, `coverage_start`/
  `coverage_end`. First model using `ref()` instead of `source()`.
- `int_member_months`: month spine (`generate_series`, 36 months) cross-joined
  against all beneficiaries (~4.19M rows), joined back to `stg_beneficiary`
  on `(beneficiary_id, source_year = month_year)`. Built in ~3-4s despite
  row count. Measured the full-year-Part-D exclusion the runbook flagged
  as something "every reviewer asks": **94,564 of 116,352 beneficiaries
  (81.3%) have at least one full year of Part D coverage; 21,788 (18.7%)
  are excluded from month-level enrollment-precision analysis.** Composite
  uniqueness test on `(beneficiary_id, month_start)` plus a singular test
  confirming no beneficiary is marked alive after their recorded death
  date — both passing.
- `int_coverage_spells`: non-recursive gaps-and-islands merge (running-max
  window function + cumulative-sum spell numbering), deliberately not
  modeling stockpiling. Built correctly on first attempt. Sanity-checked:
  451,775 spells across 99,393 beneficiaries (16,959 zero-fill
  beneficiaries, consistent with the ~14.5% zero-fill rate from the
  original Week 2 EDA), median spell length 54 days, 12.03 average fills
  per spell — no implausible values, no sign of a broken merge. Fill-count
  reconciliation against `int_fill_events` (excluding zero-days-supply
  fills) passing via a singular test. Stockpiling tradeoff documented in
  both the model description and `FUTURE_WORK.md`.

**Final state:** 8 models (5 staging + 3 intermediate), 1 seed, 44/44 tests
passing, full lineage graph generated and captured
(`reports/figures/dbt_lineage_graph.png`).

**Status:** Weeks 3 and 4 are both fully complete. Next: Week 5 — metrics
marts, the v0.5 tag (first resume-facing version), and the terminal-stop
check (the last open design question, deciding Module D's discontinuation
target definition).

---
## 2026-09-27 — Week 4 leftovers: staging tests tightened, Week 5 sanity checks

**Staging gaps closed (found by re-reading the runbook, not by a failure)**
- I had described staging as "matching the runbook exactly" when it
  didn't: `stg_beneficiary` lacked the `(beneficiary_id, source_year)`
  uniqueness test, sex-code `accepted_values`, and `not_null` on the
  flags; `stg_pde` lacked `not_null` on `fill_date`.
- The `not_null` test on `has_diabetes` could never have failed as first
  written: `("SP_DIABETES" = '1')` turns any unexpected value into
  `false`, not `null`. Replaced with a `yn_flag()` macro (1 -> true,
  2 -> false, else null) so the test can actually catch a recode miss.
  ESRD handled separately (Y / 0 per codebook BEN-6).
- Result: 59/59 tests, and `not_null` passing on all 12 flags proves every
  source value is inside the codebook's coding. Nothing computed earlier
  changes. The old logic gave the same answers on this data.
- Added `staging_conventions` docs block (`_staging.md`).

**Week 5 sanity checks**
- 93,919 beneficiaries (80.7%) have >=1 fill in the clean window.
- June 2009 monthly active rate: 70.6% (56,462 / 79,938), denominator =
  alive, full-year-Part-D members. Likely overstates the all-beneficiary
  rate given the restricted denominator (unmeasured).
- Spell lengths: p10/25/50/75/90/99 = 29/29/54/139/323/966 days, max
  1,183, 35.9% single-fill spells. p10 = p25 = 29 is exactly what
  single 30-day fills produce.

**Mistake caught:** I told myself a spell longer than the ~700-day clean
window meant a broken merge. Wrong: spells are intentionally unclipped
(full 36 months + up to 90 days of supply = ~1,186 ceiling). It does
expose a Week 5 issue: spells and coverage_end can extend past Jan 31,
2010, so anything feeding Modules C/D must filter or clip explicitly.

**Status:** Week 4 runbook fully closed. PR step dropped by decision
(solo project, direct-to-main). Next: strategy check-in, then Week 5.

---
## 2026-09-28 — Correction: Gate 4 figures

The Week 2 entry above (gate 4) says "Feb 2010 already 15% below the 2009
plateau (1.349 vs 1.418 threshold)". That mixed two denominators: 1.349 is
15% below neither figure it names, and 1.418 is the 90% threshold, not the
plateau.

Corrected, and normalised to a 30-day month so February's length can't pass
for decline: the 2009 plateau is 1.554 fills per enrolled beneficiary per
30 days. Feb 2010 is 93.0% of it, March 2010 (89.9%) is the first month under
the 90% line, and Dec 2010 is 24.2%. At the front of the file, Apr 2008 is
the first month above the line (analysis_start = 2008-04-01). The upper edge
of the clean window stays at 2010-01-31, deliberately a month conservative.
The decline conclusion is unchanged, but the evidence is now the twelve-month
slide, not "already 15% below in February". See docs/fidelity_audit.md Part B.

---
## 2026-09-28 — Note for the fct_utilization_monthly entry (Week 5, Part 1)

Checked before building the mart: does CLM_PMT_AMT repeat across a claim's
two segments rather than split between them? No. For the 68 inpatient and
10,975 outpatient claims with two segments, segment 1 and segment 2 have
different sums and different averages in both tables (e.g. inpatient
segment 1 averages $17,823.53, segment 2 averages $18,789.71). A plain
sum() over both segments is correct; no deduplication needed. Query and
full numbers to be folded into the real fct_utilization_monthly entry when
that model is built.

---
## 2026-09-29 — Week 5, Part 0: bridge closed, Gate 4 renormalised

**Second correction to Gate 4's clean-window wording.** The 2026-09-28
correction entry above fixed the numbers but kept "conservative" with no
stated rule for `clean_window_end`. Per strategy review: "conservative" invites "by
how much, against what rule?" Fixed properly this time: the 90% rule
applied symmetrically to the far side of the file gives Feb 28, 2010 as
the last qualifying month; Jan 31 is used instead, one month tighter,
because the 2010 series is already declining monotonically before it
breaches the threshold, so proximity to the breach is itself evidence of
contamination. Both numbers and the reason are now in
`docs/fidelity_audit.md` (Part B, Part E, and Constraints — three
instances, all reconciled to the same wording).

**The argument against claims lag changed shape, not conclusion.** With
February no longer the breach point (93.0% of plateau, clears the line),
the case against claims lag now rests on the twelve-month monotonic
decline (already -14% by April, 24.2% by December) rather than on
February's depth. Run-out has a sharp elbow in the final 1-3 months of an
extract and is flat before it; a year-long slide starting in January is
harder to explain as ordinary lag than one deep month was.

**2008 annual summary fields flagged as not comparable across years.**
Same under-observation that thins Jan-Mar 2008 depresses the beneficiary
file's annual reimbursement totals for that year. Covariate-only impact
for Module C; 2008 spend must not be compared directly against 2009.
Recorded in the audit's Constraints section.

**Fixture database fixed at the source (§0.3).** `load_fixture_db.py` was
storing `source_year` as text, the root cause of the earlier Gate 4
`SchemaError` that got patched downstream with a `CAST`. Cast at load
instead; removed the now-unnecessary `CAST` from
`gate4_monthly_plateau_threshold`, confirmed `test_gate4_deterministic`
still passes on the small database without it. Added a `build-ci`
Makefile target; `dbt build --target ci` now gives `PASS=59`, same as the
full database — the small database supports a full dbt build for the
determinism suite for the first time.

**Three boundaries, one macro file (§0.4).** `dbt_project.yml` gained
`analysis_start` (2008-04-01) alongside `study_start` and
`clean_window_end`. `transform/macros/clean_window.sql` adds
`in_clean_window()`, `in_analysis_window()`, and `clip_to_clean_window()`
(the last not yet used). Replaced the hand-written comparisons in both
`int_fill_events` and `int_member_months` with `in_clean_window()`;
checked each change against the old inline logic directly (0 rows
disagreed in either model) before committing.

**Denominator policy (§0.5).** Added `has_full_year_part_ab` to
`int_member_months` (`part_a_coverage_months = 12 and
part_b_coverage_months = 12`), alongside `has_full_year_part_d`. 97,112 of
116,352 beneficiaries (83.5%) have a full A/B year in 2008 — a larger
share than Part D typically shows, consistent with A/B being closer to
universal coverage. `fct_utilization_monthly` will use A/B for medical
amounts and Part D for rx, not Part D for both.

**Segment payment check:** already logged above (2026-09-28 entry) —
`CLM_PMT_AMT` differs across a claim's two segments rather than
duplicating, so `sum()` is correct with no deduplication needed. Numbers
also in `docs/metrics_reference.md`.

**Retention pre-commit table (§0.6) correctly deferred to Part 1.**
 Single endpoint (pooled month-6 retention), threshold
`T = max(3pp, 0.15 × null_median_month6)`, both nulls and the threshold
committed to `audit_results.json` before the real curve is computed.
Belongs inside `fct_cohort_retention` (`audit/retention_null.py`), not a
Part 0 item.


**Status:** Week 5, Part 0 fully closed. `make build` and `make build-ci`
both green at 59/59. Next: Part 1, `fct_monthly_active`.

---
## 2026-09-29 — Week 5, Part 1: fct_monthly_active

**Build.** One row per beneficiary per month, left join from
`int_member_months` to fills aggregated by `date_trunc('month', fill_date)`.
`coalesce(f.n_fills, 0)` before deriving `is_active`, since a left join
with no match gives `null`, not zero, and `null > 0` in SQL is neither
true nor false. Built as a table per the marts materialization default.
Deliberately keeps every month behind `in_clean_window` rather than
filtering, since it's the base table the other rate/utilization marts
read from.

**A real column-loss bug found before the build even ran into it.** The
§0.5 edit that added `has_full_year_part_ab` to `int_member_months`
replaced the existing `has_full_year_part_d` line instead of adding
beside it, and nothing caught it: that table had already been rebuilt and
committed twice since, and all 59 tests passed both times, since nothing
tests for a specific column's presence, only `not_null` on the two grain
columns. It surfaced only when this mart tried to reference the missing
column and dbt's binder error named it directly. Restored the line;
confirmed via `distinct beneficiary_id where has_full_year_part_d` that
the count is still 94,564, the same population as when the column was
first built — so the earlier commits never produced a wrong number, they
just silently carried a table with fewer columns than intended.

**Numbers.** Active share, clean window (Apr 2008-Jan 2010), full-year
Part D members: 72.4% (1,297,519 / 1,792,334 beneficiary-months). Close
to, not identical to, June 2009's single-month 70.6% from Week 4 — a
pooled multi-month rate and one month's rate aren't expected to match
exactly, and the two are close enough to be reassuring. Both numbers now
in `docs/metrics_reference.md`.

**Test coverage gap worth naming.** No test in this project currently
checks that a model has a specific expected column; only `not_null` on
named columns already present. A model can silently lose a column and
every test still passes, provided nothing downstream references it yet.
Not fixing this now, just recording it as a real limitation of the
current test suite.

**Status:** `fct_monthly_active` built, 65/65 tests passing project-wide.
Next: `fct_engagement_rate_monthly`.

---

## 2026-09-29 — Week 5, Part 1: fct_engagement_rate_monthly

**Build.** One row per calendar month, filtered to the analysis window,
aggregating `fct_monthly_active` into two denominators side by side:
`n_enrolled_all`/`rate_all` (every beneficiary) and
`n_enrolled_strict`/`rate_strict` (only those with a full year of Part D
that year), plus `strict_share` so the exclusion can be quoted straight
from the mart. This is the fix for the earlier complaint that the 18.7%
exclusion figure understated the monthly reality — a reviewer now gets
the real monthly share, not a beneficiary-level annual figure standing in
for it.

**A real bug caught by comparing against a known number, not by a failed test.** First build gave `rate_all` = 51.0% and, more tellingly,
`n_enrolled_strict` = 80,486 for June 2009 — 548 more than the 79,938
`docs/progress-log.md` already had on record from Week 4. All dbt tests
passed regardless, since nothing checked the value against the earlier
number, only that `month_start` was not-null and unique. The mart had no
`is_alive` filter; Week 4's manual query did. The 548-person gap is
beneficiaries with a full 2009 Part D year who had already died by June
2009 and were still counting toward the denominator. Added `and is_alive`
to the `where` clause. Rebuilt: `n_enrolled_strict` = 79,938 exactly,
`rate_strict` = 70.6%, both matching Week 4 to the number. `fct_monthly_active`
itself needed no equivalent fix — it deliberately carries `is_alive` as a
column for downstream marts to filter on rather than filtering itself, per
its own description.

**Second time in two marts this exact bug shape has appeared**: build
succeeds, every test passes, and the number is wrong until checked against
something already known. Both times the same fix (an `is_alive` filter)
and both times only caught by comparing against a number recorded earlier
in this log, not by the test suite. Worth treating "does this new number
match a previously recorded one" as a standing habit for every new mart in
this project, not just a nice-to-have.

**Status:** `fct_engagement_rate_monthly` built, 68/68 tests passing.
Both new marts logged in `docs/metrics_reference.md`. Next:
`fct_cohort_retention`.

---
## 2026-09-30 — Week 5, Part 1: fct_cohort_retention, entry cohort and person-month grid

**Entry cohort.** New-user definition: first fill after a `washout_days`
gap (or a beneficiary's first-ever fill), restricted to entries between
`analysis_start + washout_days` and 2009-07-31. The lower bound derives to
2008-09-28, three days tighter than the runbook's literal "Oct 1": used
the derived date rather than rounding to the literal, since the project's
own standard is to state the actual rule, not an approximation of it.
Verified standalone before wiring into dbt: 99,393 distinct beneficiaries
produce at least one entry candidate, exactly matching the count of
beneficiaries with any coverage spell from Week 4 — nobody with zero
qualifying fills slipped through. Final cohort after the window filter and
taking each person's first qualifying entry: 20,260 beneficiaries,
earliest and latest entry dates land exactly on the derived bounds
(2008-09-28, 2009-07-31).

**Person-month grid.** One row per beneficiary per month since their own
entry, built with `generate_series` + `unnest`, reaching from each
cohort's entry month to `clean_window_end`. First draft of this CTE had a
real scoping bug (an alias, `ma`, referenced before it was defined, and a
column reused as both a list name and a scalar name across CTEs), caught
before running, not after.

**Two assumptions corrected while verifying the grid, neither a bug in the
SQL:**
- `generate_series(0, n)` in DuckDB is inclusive on both ends, producing
  n+1 values, not n. Expected a 15-month span to produce 15 values; it
  correctly produces 16 (0 through 15). No fix needed — the SQL was
  right, the mental check of it was wrong.
- Assumed the earliest cohort month was October 2008, since the derived
  entry floor (Sep 28, 2008) is close to October. It isn't: `entry_month`
  truncates to the *start* of the entry date's calendar month, and Sep 28
  truncates to Sep 1, not Oct 1. The earliest cohort is therefore
  September 2008, one month earlier than assumed, which is also why the
  grid's `max(months_since_entry)` across all cohorts is 16, not 15 —
  traced and confirmed against `datediff('month', '2008-09-01',
  '2010-01-31')` = 16 before accepting it as correct.

Both assumption errors were caught by checking the grid's output against
independent arithmetic rather than trusting dbt's green build, the same
discipline that caught the two `is_alive` bugs in the previous two marts.
Worth stating plainly: the entry cohort window, by calendar month, is
September 2008 through July 2009, not October as the runbook's original
literal phrasing implied — any later documentation or resume language
describing this window should say September.

**Status:** entry-cohort and person-month-grid logic verified standalone
(not yet run through `dbt build`, no schema file or tests yet). Next:
collapse the grid to cohort-level retention rates, then the retention
pre-commit table and null overlay from Step 0.6.

---

## Template for future entries

## YYYY-MM-DD — Week N, Step X: < short description>

**What was attempted**

**What broke / issue faced**

**Root cause**

**Fix**

**Status / what's next**
