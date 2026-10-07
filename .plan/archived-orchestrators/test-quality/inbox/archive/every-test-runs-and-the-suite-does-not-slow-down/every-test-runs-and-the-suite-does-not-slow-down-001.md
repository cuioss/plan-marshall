envelope_version=1
sender_type=plan
sender_id=every-test-runs-and-the-suite-does-not-slow-down
epic=test-quality
kind=finding
created=2026-09-05T19:14:52Z

# Run conditions are now measurable off the canonical command

PLAN-110 (`every-test-runs-and-the-suite-does-not-slow-down`) closed the epic's
two unmeasured run conditions. Both now ride the ONE canonical `module-tests`
invocation — no wrapper change, no new flag, no pytest-args passthrough. Mirror
both commands into the epic ledger's run-conditions note.

## The mechanism

`pyproject.toml` → `[tool.pytest.ini_options]` → `addopts` gains `-rsfE`
alongside the existing `--durations=25`.

⛔ The value is `-rsfE`, never a bare `-rs`. `-r` is a STORE option, not an
accumulating one, so a later `-rs` REPLACES pytest's `fE` default and drops the
`FAILED <path>::<test>` short-summary lines. `build-pyproject`'s
`_PYTEST_FAILED_PATTERN` parses those lines to file per-test `test-failure`
findings, so losing them would collapse a failing build into one synthetic
`build_failure` row and take the per-test triage surface with it.

## Condition 1 — how many tests did not run, and which

```text
python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args "module-tests"
```

Read the `SKIPPED` short-summary block. An empty block means every test ran. Each
entry must be on the residual skippable set (`_SKIP_EXCEPTIONS` in
`test/conftest.py`); the session-finish gate — now ALWAYS ON, its opt-in
`PLAN_MARSHALL_STRICT_NO_SKIP` flag deleted — fails the run on any that is not.
The set's size prints in the session header:
`residual skippable set: 11 nodeid(s) permitted to skip`.

## Condition 2 — how long, and where it went

Same command. Read the `--durations=25` table for per-test attribution and the
trailing total for suite wall clock:

```text
================ 24564 passed, 11 skipped in 199.27s (0:03:19) =================
```

## Also corrected

`doc/developer/measurement-protocol.adoc` line 50 carried
`./pw module-tests {bundle} -- --durations=25`, which is **not runnable**: the
`module-tests` subparser declares only `module`, `--parallel` and
`--no-parallel`, and parses strictly. It is now the plain canonical invocation,
which needs no flag because `--durations=25` is in `addopts`.

## Epic-level premise corrections worth carrying

- `.github/workflows/` holds **EIGHT** files, not seven. The stale count is gone
  rather than corrected — the claim it supported was deleted with the flag.
- `test/conftest.py`'s `collect_ignore` had **FOUR** entries, not five; **THREE**
  remain after PLAN-110 removed the `test_analyze_manage_invocation_smoke.py`
  entry.
- The residual skippable set is **11 nodeids from 4 guard sites**, not the 9
  source sites the plan brief assumed: `test_lsp_integration.py` carries one
  MODULE-LEVEL guard covering seven tests, not one guard covering one.
- `scope_creep_check` returns `could_not_look` / `no_baseline_sha` for this plan
  (`references.json` carries no `plan_creation_sha`), so **no scope-creep
  measurement was taken on any task**. `residual_count` is absent, not zero.
