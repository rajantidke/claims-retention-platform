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

## Template for future entries

## YYYY-MM-DD — Week N, Step X: <short description>

**What was attempted**

**What broke / issue faced**

**Root cause**

**Fix**

**Status / what's next**
