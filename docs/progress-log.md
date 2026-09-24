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
## Template for future entries

## YYYY-MM-DD — Week N, Step X: < short description>

**What was attempted**

**What broke / issue faced**

**Root cause**

**Fix**

**Status / what's next**
