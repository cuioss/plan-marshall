# CI Log Fixtures — Provenance

These fixtures back the real-fixture assertions in
`test/plan-marshall/tools-integration-ci/test_ci_log_filter.py`. They exercise
`_ci_log_filter.filter_log` against authentic CI / build-tool output rather than
hand-written error lines.

**Honesty note:** Every fixture below was captured from a *real* tool run — none
of the error lines, tracebacks, or summary lines were fabricated. The capture
mechanism and the unavoidable substitutions (CI-runner framing, path
anonymization) are documented per-file so a reviewer can reproduce or audit them.

## How the fixtures were obtained

At capture time this repository's GitHub Actions CI (`python-verify.yml`) was
green on every reachable run, and `glab` was **not installed** on the capture
host (`ci_health status` reported `glab installed: false`), so no live GitLab
instance was reachable. A real *failing* GitHub Actions run could therefore not
be downloaded via the CI abstraction
(`plan-marshall:tools-integration-ci:ci checks logs --run-id ...`); the
abstraction's `logs` operation is failure-oriented (`gh run view --log-failed`)
and returned empty content for the confirmed-passing run `26751742775`
(PR #535, `verify / verify`).

Per the task's fallback instruction, the authentic tool output was instead
captured from **real local `pyproject_build` runs** in the plan worktree. The
underlying tools (pytest, mypy, ruff) are the exact same tools that
`./pw verify` runs inside both the GitHub Actions and a GitLab CI job for this
project — only the surrounding CI-runner framing differs between providers. The
deliberately-broken throwaway snippets used to force the failures were deleted
immediately after each capture (verified clean via `git status`).

## Files

### github/pass.log

- **Source:** Real `./pw module-tests pm-documents` run (exit 0, 76 passed).
  Captured build log:
  `.plan/temp/build-output/pm-documents/python-2026-06-01-143718.log`.
- **Substitutions:** Local venv-warning preamble dropped; `rootdir` and the
  `platform` line rewritten to a GitHub Actions runner shape
  (`/home/runner/work/...`, `platform linux`). The per-test PASSED lines and the
  `N passed in Xs` summary are verbatim from the real run (subset retained for
  fixture size).
- **Filter expectation:** Contains **no** line matching the generic heuristic
  (`ERROR|FAIL|Exception|Traceback`, case-insensitive) — every test line is
  `PASSED`. `filter_log(..., 'generic')` therefore extracts no error window and
  falls back to the trailing context lines (no-error semantics).

### github/fail.log

- **Source:** Real `./pw module-tests pm-documents` run (exit 1, 2 failed / 76
  passed) against two deliberately-broken throwaway tests (an `AssertionError`
  on a dict comparison and an `IndexError` from an out-of-range list access).
  Captured build log:
  `.plan/temp/build-output/pm-documents/python-2026-06-01-143842.log`.
- **Substitutions:** Same runner-framing rewrite as `pass.log`; the throwaway
  test's path was renamed from `_throwaway_fixture_capture/test_throwaway_failure.py`
  to a neutral `sample/test_sample.py`. The `FAILURES` section bodies
  (`AssertionError`, `Differing items`, `IndexError: list index out of range`,
  the `short test summary info` `FAILED` lines, and the `2 failed, ...` summary)
  are verbatim from the real run.
- **Filter expectation:** The real `FAILURES` block carries the error-relevant
  lines; `filter_log(..., 'generic')` extracts the windows around the
  `FAILED` / `AssertionError` / `IndexError` lines.

### gitlab/pass.log

- **Source:** Real `./pw quality-gate pm-documents` run (exit 0 — mypy clean +
  ruff clean). Captured build log:
  `.plan/temp/build-output/pm-documents/python-2026-06-01-144031.log`.
- **Substitutions:** Local venv-warning preamble dropped; wrapped in a GitLab CI
  job-trace framing (`Running with gitlab-runner`, `$ ./pw quality-gate ...`,
  `Job succeeded`). The tool-output body (`Success: no issues found in 11 source
  files`, `All checks passed!`, the `>>> compile`/`>>> quality-gate` echo lines)
  is verbatim from the real run.
- **Filter expectation:** No generic-heuristic match → no error window
  extracted (no-error semantics).

### gitlab/fail.log

- **Source:** Real `./pw quality-gate pm-documents` run (exit 1 — ruff
  `F401`/`F401`/`F841`) against a deliberately-broken throwaway module (two
  unused imports + one unused local). Captured build log:
  `.plan/temp/build-output/pm-documents/python-2026-06-01-144001.log`.
- **Substitutions:** Same GitLab job-trace framing as `pass.log`; the throwaway
  module path was renamed from `_throwaway_lint_capture.py` to a neutral
  `_sample.py` (and the docstring line trimmed to match). The ruff diagnostics
  (`F401 ... imported but unused`, `F841 Local variable ... never used`, the
  source-context carets, the `Found 3 errors.` line, and the `[*] 2 fixable`
  line) are verbatim from the real run.
- **Filter expectation:** The `Found 3 errors.` / `F841` / `ERROR: Job failed`
  lines match the generic heuristic; `filter_log(..., 'generic')` extracts the
  windows around them.

## Note on the `gitlab/` provider directory

The `gitlab/` fixtures are real tool output framed as a GitLab job trace, **not**
a log downloaded from a live GitLab instance (none was reachable — `glab` was
not installed at capture time). They are kept under `gitlab/` because
`_ci_log_filter.filter_log` is provider-agnostic: it operates on the build-tool
output content, which is identical regardless of which CI provider hosts the
job. The provider directory split exists so the test can assert filtering works
on both the GitHub-Actions-shaped and GitLab-job-trace-shaped framings.
