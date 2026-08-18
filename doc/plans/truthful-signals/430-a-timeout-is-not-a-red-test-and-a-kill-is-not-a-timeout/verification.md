# Verification — 430-a-timeout-is-not-a-red-test-and-a-kill-is-not-a-timeout

**Verified against:** commit `af417166dd9f64704fe738720d716c38515061be`   **Landed as:** PR #1193, commit `d4ae2e81ad04c6daf7cb04f59e49e270fce4bb44`   **Verdict:** implemented-with-gaps

## Method

What was actually done, so that an empty finding list is distinguishable from a check that examined nothing.

**Read in full:** `plan.md`, `report-01.md`, and the landed commit message and diff
(`git show --stat d4ae2e81`, plus the per-file diffs for `_build_execute.py`,
`_build_execute_factory.py`, `_build_shared.py`, `_build_result.py`,
`_build_server_protocol.py`, `_build_format.py`, `_ledger_core.py`,
`_marshalld_supervisor.py`, `_cmd_pre_commit_verify_freshness.py`,
`execute-script.py.template`, `build-systems-common.md`, `build-execution.md`,
`build-api-reference.md`, `run-config-standard.md`, `manage-change-ledger/SKILL.md`,
`manage-tasks/SKILL.md`, `phase-5-execute/SKILL.md`, `push.md`,
`plan-marshall/workflow/execution.md`, `error-handling.md`, and all six test files).

**Read at HEAD (current tree, not the diff):** `_build_result.py` (statuses,
`killed_result`, `indeterminate_result`, `KILLED_MESSAGE` docstring),
`_build_shared.py` (`_non_finish_evidence`, `cmd_run_common` branch order),
`_build_execute_factory.py` (`_daemon_result_to_direct`, `_result_for_log_verdict`,
`_route_to_daemon` wait loop), `_build_server_protocol.py`
(`_RESULT_STATUS_TO_WIRE`, `TERMINAL_STATUSES`, `wire_status_from_result`,
`LogVerdict`, `read_log_verdict`), `_marshalld_supervisor.py` (`_terminal_payload`,
`run_job`), `marshalld.py` (`_wait`, `_is_terminalized`, `_execute`),
`build_server.py` (`_render_job_status`), `manage-change-ledger.py`
(`classify-outcome`), `_cmd_pre_commit_verify_freshness.py` (`_STALE_BY_STATUS`,
`_stale_reason`, the caller), `_ledger_core.py` (the three status sets), and the
executor template's `_derive_build_status`.

**Supersession checks:** `git log --oneline -3` on every production file the plan
touched. `_build_shared.py` was later touched by `fa452e0c` (#1229);
`_cmd_pre_commit_verify_freshness.py`, `manage-tasks/SKILL.md`,
`phase-5-execute/SKILL.md`, `push.md`, `build-systems-common.md` by `e2b6665b`
(#1279) and `aeab5ab5` (#1283); `workflow/execution.md` by `9135f275` (#1287).
Every one of them **extended** this plan's work (more `stale` reasons, more
consumer rows) rather than reverting it — verified by reading the current text of
each.

**Tests executed:**

- `uv run python -m pytest test/plan-marshall/script-shared/test_non_finish_discrimination.py -o addopts="" -q` → **50 passed**
- `uv run python -m pytest test/plan-marshall/build-server/test_marshalld_supervisor.py -o addopts="" -q` → **21 passed**
- `uv run python -m pytest test/plan-marshall/manage-tasks/test_pre_commit_verify_freshness.py --collect-only` → 39 collected
- `uv run python -m pytest test/plan-marshall/tools-script-executor/test_executor_runtime.py -k derived_status --collect-only` → 11 cases, including `[status: killed\n-0-killed]` and `[status: indeterminate\n-0-unknown]`

**Function executed directly** (`uv run python -c …` against the real module):
`wire_status_from_result('indeterminate')` → `'indeterminate'`;
`'indeterminate' in TERMINAL_STATUSES` → `False`;
`sorted(_RESULT_STATUS_TO_WIRE)` → `['error', 'killed', 'success', 'timeout']`.

**Mutations applied** (each preceded by `git diff --quiet -- <path>`, exit 0 = clean;
each restored from a byte copy taken before the edit, re-verified clean afterwards;
no `git checkout`/`restore`/`stash` used):

1. `_marshalld_supervisor.py:305` — `status = wire_status_from_result(verdict.status)`
   reverted to `status = 'failure'`. Result: **RED** —
   `TestRunJobNarrowingPreservesTheNonFinish::test_exit_zero_with_killed_toon_is_wire_killed_not_failure`
   and `…_timeout_toon_is_wire_timeout_not_failure` both failed
   (`assert 'failure' == 'timeout'`), control
   `test_control_exit_zero_with_error_toon_is_still_wire_failure` stayed green.
   Restored, `git diff --quiet` clean.
2. `_build_execute.py` — `if result.returncode < 0:` neutered to `if False:`.
   Result: **RED** — 4 failures
   (`test_negative_returncode_is_killed_not_error[9|15|2]` and
   `test_killed_run_does_not_teach_the_adaptive_learner`, the latter with
   `Expected 'timeout_set' to not have been called. Called 1 times.`); the three
   matched controls stayed green. Restored, `git diff --quiet` clean.

No other file was modified. The two files written by this verification are the only
additions.

## Deliverable-by-deliverable

| # | Deliverable | Done-when condition | Implemented? | As documented? | Correct? | Complete? | Evidence (file:line / symbol / command + result) |
|---|---|---|---|---|---|---|---|
| D0 | Enumerate what daemon + harness already emit, and which consumer reads which field; publish the population | Vocabulary and per-consumer reads enumerated, population published | **yes** | **yes** | **yes** | **partial** | `marketplace/bundles/plan-marshall/skills/extension-api/standards/build-systems-common.md:126-186` — three-condition table, 11-row consumer table, transitive-derivation rule, three failure shapes. Population (11 gates, 11/11 read a status field) published in `report-01.md` § D0. Boundary honoured: `classify_terminal` body byte-identical; `manage-change-ledger.py` carries no code change (`git show --stat d4ae2e81`) |
| D1 | Three conditions distinguishable at EVERY consuming gate | A timeout cannot be presented as a test failure; a harness kill cannot be presented as a timeout | **yes** | **yes** | **yes** | **yes** (for the two stated directions) | Gate-by-gate below. All 11 gates present at HEAD and extended, not reverted, by #1279/#1283/#1287 |
| D2 | Settle the subset/superset inversion; diagnose, do not adjust | The mechanism is named | **yes** | **yes** | **yes** | **yes** | `manage-run-config/standards/run-config-standard.md` § "What `timeout_seconds` actually measures" — three named properties. No bound changed: `SAFETY_MARGIN=1.25`, `HIGHER_WEIGHT=0.80`, `MINIMUM_TIMEOUT_SECONDS=120` (`run_config.py:25-27`), `MIN_TIMEOUT=60`/`MAX_TIMEOUT=1800` (`_build_execute.py:106,111`), `DEFAULT_BUILD_TIMEOUT=300` (`_build_shared.py:205`), `PYTEST_OUTER_FLOOR_SECONDS=330` (`_pyproject_execute.py:64`) — none appears in the landed diff |
| D3 | Regression tests with matched controls, each verified RED pre-fix | Red test still fails; timeout does not; kill does not | **yes** | **mostly** | **yes** | **partial** | 50 cases in `test_non_finish_discrimination.py` all pass; two independent mutations (above) go RED with their controls staying green. One totality test is vacuous — see G3 |

### D0 — complete only up to the vocabulary it publishes

The durable artifact is real and matches the report: `build-systems-common.md` carries
the 11-gate consumer table, the transitive-derivation rule, and the three failure
shapes. Two shortfalls:

- The section enumerates **four** conditions (`error`, `timeout`, `killed`, and
  `unknown` as the unresolvable one) and never names `indeterminate`, which is the
  fifth `DirectCommandResult` status this very plan introduced
  (`_build_result.py:153`, `DirectCommandResult.status` `Literal` at
  `_build_result.py:112`). A reader who walks this table to update the vocabulary
  starts from an incomplete vocabulary. → **G6**.
- The published population figure (11, 11/11) lives only in `report-01.md`; the
  standard publishes the rows but not the counts. The plan's Verification asked for
  the population to be published; the report does publish it, so this is noted, not
  faulted.

### D1 — verified per gate at HEAD

| Gate | Verified how |
|---|---|
| #1 `_derive_build_status` | `execute-script.py.template:484-490`; parametrised cases `[status: killed\n-0-killed]`, `[status: unknown\n-0-unknown]`, `[status: totally-made-up\n-0-unknown]`, `[status: indeterminate\n-0-unknown]` all collected and passing |
| #2 `run_job` narrowing | `_marshalld_supervisor.py:305`; **mutation-confirmed RED** (see Method) |
| #3 `_daemon_result_to_direct` | `_build_execute_factory.py:455-494` + `_result_for_log_verdict:521-543`; aliased `WIRE_STATUS_KILLED`/`RESULT_STATUS_KILLED` imports (lines 63-77) confirm N8's fix; catch-alls return `indeterminate_result`, not `error` |
| #4 `cmd_run_common` | `_build_shared.py:669-720` — `killed` branch precedes `indeterminate` precedes `timeout`, all ahead of the build-failure path; `message` propagated rather than reconstructed; `timeout_used_seconds` preserved on the kill |
| #5 `_render_job_status` | `build-server-client/scripts/build_server.py:278-301` — unchanged, and correct: `job_status == STATUS_KILLED` attaches `_KILLED_MESSAGE` |
| #6 `classify-outcome` | `manage-change-ledger.py:219-224` — the `killed`-row branch is reachable now that `killed ∈ WRAPPER_CLAIMABLE_BUILD_STATUSES` (`_ledger_core.py:62`). See G5 for the one direction it still collapses |
| #7 `pre-commit-verify-freshness` | `_cmd_pre_commit_verify_freshness.py:135-233` (`_STALE_BY_STATUS`, `_stale_reason`) and `:485-499` (caller). `observed_status` omitted on exactly the two documented routes. `key == 'success'` is unreachable because `_stale_reason` runs only when the success-candidate list is empty (`:472-480`) — checked, not assumed |
| #8 the LLM agent | `build-api-reference.md:22` enumerates all five statuses with the no-blind-retry instruction |
| #9 orchestrator-tier phase-5 | `plan-marshall/workflow/execution.md:371-378` — five-way table plus the explicit prohibition on triaging a non-finish |
| #10 `phase-5-execute` Step 12a | `phase-5-execute/SKILL.md:1063,1065,1091` — `reason`/`observed_status` on both non-`fresh` branches and on the `--force` audit line |
| #11 `push.md` freshness precondition | `push.md:49,52,58` — `reason`/`observed_status` in `display_detail`; the reconciliation section scoped to `worktree_mutated` |

Both enabling changes are present: `killed ∈ WRAPPER_CLAIMABLE_BUILD_STATUSES` with
`DERIVED_ONLY_BUILD_STATUSES == {'unknown'}` (`_ledger_core.py:62,74`), and `message ∈
EXTRA_FIELDS` with the silent-whitelist hazard documented (`_build_format.py:41-63`).

D1's two stated done-when directions hold. One direction the plan did **not** state is
still open at gate #6 — see G5.

### D3 — the controls are real, one totality assertion is not

Every non-finish property in `test_non_finish_discrimination.py` has a matched control
that asserts positively on the red side (`test_control_red_build_still_reports_its_errors`
asserts `status: error` **and** `errors[` **and** the parsed message;
`test_control_red_build_still_stores_findings` asserts `store.assert_called_once()`;
`test_control_positive_returncode_is_still_error` and the two learner controls likewise).
Both mutations I applied produced RED on the property and GREEN on the control, so the
suite is not vacuous as a whole.

`TestVocabularyTranslationIsTotal` (`test_non_finish_discrimination.py:477-517`) is the
exception. Its name and docstring claim every `_build_result` status has an explicit wire
row, but the parametrisation hard-codes the four pre-`indeterminate` statuses, so the one
status the same commit added is the one the totality check cannot see. → **G3**, and the
hole it fails to catch is **G2**.

## Report accuracy

Contradicted by the tree:

1. **§ D3: "`test/plan-marshall/script-shared/test_non_finish_discrimination.py` (44 cases)"** — the file at HEAD is byte-identical to the file at `d4ae2e81` (`diff` against `git show d4ae2e81:…` → identical) and collects **50** cases (35 test functions, 7 `parametrize` decorators). Re-derived at the moment of writing by running the file: `50 passed in 0.23s`.
2. **§ D1 gate #7 and § D3: "12 cases in `test_pre_commit_verify_freshness.py`"** — the landed diff adds **7** test functions, one of which carries a 5-way `parametrize`, i.e. **11** collected cases, not 12 (`git show d4ae2e81 -- test/plan-marshall/manage-tasks/test_pre_commit_verify_freshness.py | grep '^+.*def test_'` → 7; a single `+@pytest.mark.parametrize` with five tuples).

Checked and **not** contradicted:

- "3 in `test_marshalld_supervisor.py`" — exactly 3 added, in `TestRunJobNarrowingPreservesTheNonFinish`.
- "16 Python-bearing files (10 production including the executor template, 6 test)" — re-counted from `git show --name-only`: 10 production (`_marshalld_supervisor.py`, `_ledger_core.py`, `_cmd_pre_commit_verify_freshness.py`, `_build_execute.py`, `_build_execute_factory.py`, `_build_format.py`, `_build_result.py`, `_build_server_protocol.py`, `_build_shared.py`, `execute-script.py.template`) + 6 test = 16. ✓
- "`manage-change-ledger.py` carries no code changes at all (only its `SKILL.md` prose was corrected)" — ✓, the file is absent from the diff.
- "`classify_terminal` itself is unchanged … byte-identical" — ✓, the only occurrences of that symbol in the diff are docstring/comment references.
- "No bound, margin, floor, or cap changed … all byte-identical" — ✓, all seven constants re-read at HEAD and none appears in the diff.
- D2 arithmetic: `int(513.6 × 1.25) == 642` ✓; `int(489 × 1.25) == 611` ✓; `488.85 − 443.96 == 44.89` ✓; `19 231 − 16 154 == 3 077` ✓.
- "`killed` fails every gate `error` fails, so nothing fails open" — ✓, the freshness gate admits only `status == 'success'` (`_cmd_pre_commit_verify_freshness.py:468-471`).
- The N-series dispositions I could re-check are genuine: N2/N3 (`build-execution.md:425`, `:600-621` — `error` is its own arm, the `else` reports an unrecognised status), N7 (`_marshalld_supervisor._terminal_payload` — `failure` is now its own arm), N8 (aliased imports), N10 (`KILLED_MESSAGE` docstring names every copy), N12 (`[status: indeterminate\n-0-unknown]` case present).
- F7/F8/F9/F10/F11/F12 all verified fixed at HEAD by opening each site.

Not verifiable from the tree, and therefore neither confirmed nor faulted: the two
D2 wall-clock measurements (488.85 s / 443.96 s, 16 154 / 19 231 tests), the per-round
suite totals (19 276 / 19 293 / 19 298), the CI check conclusions, the reviewer
participation table, and the two sub-agent token self-reports. The report itself
labels the `.plan/`-provenance timings as not re-derived, which is accurate.

## Out-of-scope compliance

Honoured on all three declared boundaries.

- **No discriminator re-added.** `classify_terminal` and `classify-outcome` are
  byte-identical; what changed is downstream narrowing and reachability. The new
  `STATUS_INDETERMINATE` is a fifth value in an existing vocabulary, not a second
  classifier beside an existing one.
- **The test suite under measurement was not changed.** No file under a build's
  measured surface was touched; the diff changes classification only.
- **The learned budget was not raised.** Verified constant-by-constant above.

Collateral in the landed diff, all declared in the report: the F12 hermeticity fixture
in `test_build_execute_factory.py`, the `message` whitelist in `_build_format.py`, and
`manage-run-config/standards/run-config-standard.md` — the last is outside the plan's
"Expected surface" list (which named `build-pyproject/**` for the D2 budget lookup),
but it is where the learned-budget contract actually lives, and D2's diagnosis had to
be documented somewhere. `build-pyproject/**` itself was not touched at all, which is
consistent with D2 being a diagnosis rather than an adjustment. No undeclared change
found.

No bookkeeping write landed under `doc/plans/` outside this plan's own directory
(`git show --name-only d4ae2e81` lists exactly `plan.md` and `report-01.md` there).

## Residue carried forward

| report-01.md residue | Status in today's tree |
|---|---|
| The no-blind-retry sentence duplicated four times (N10) | **STILL OPEN.** Re-derived: `_build_result.KILLED_MESSAGE:185`, `manage-change-ledger._NO_BLIND_RETRY_MESSAGE:180`, `build_server._KILLED_MESSAGE:102`, and the differently-punctuated variant in `_cmd_pre_commit_verify_freshness.py:152`. The docstring at `_build_result.py:186-200` still correctly names all of them. |
| Other tests still write to the real `~/.plan-marshall` | **PARTIALLY CLOSED / not fully re-derivable.** Every test module at HEAD that references `home_root` also sets `PLAN_MARSHALL_HOME` (`test_providers_core.py`, `test_marketplace_paths.py`, `test_build_execute_factory.py`, `test_build_server_registry.py`, `test_build_queue.py`). There is **no** global `PLAN_MARSHALL_HOME` sandbox in `test/conftest.py`, so the class is closed by convention rather than by construction; the specific `plan-x` writer the report observed could not be attributed to a module without running the suite against a real home, which I declined to do. |
| The subset/superset measurement is a single pair | **STILL OPEN by construction.** The structural half (properties 1 and 2) is derivable from `run_config.py` and was re-read; the cache-state half still rests on the one reported pair. |
| The sibling-plan sequencing note could not be evaluated | **N/A here.** Nothing in the tree records a serialization requirement, and no later commit reverted this plan's surface. |

## What could NOT be verified

- The D2 measurements themselves (build durations, test counts, cache state). Re-running `./pw verify` and `./pw module-tests plan-marshall` was out of proportion to this check and would in any case measure a different tree.
- The per-round suite totals, the CI conclusions on PR #1193, the reviewer-participation table, and the token/wall-clock figures — all GitHub- or session-provenance, none reachable from the tree.
- Whether the two verification sub-agents raised exactly the 19 + 12 findings tabulated. The dispositions I could sample (V6-V14, N2, N3, N7, N8, N10, N12) are all genuinely present at HEAD, so the tables are consistent with the tree wherever they touch it.
- The `.plan/`-provenance ~642 s / ~618 s timings, which the report itself declines to re-derive.
- The runtime reachability of the `indeterminate` wire-status hole (G2) beyond the static argument recorded there: I confirmed the re-entrancy guard (`_build_execute_factory.py:561`) and the daemon setting `MARSHALLD_JOB_ENV` on the child (`_marshalld_supervisor.py:257`), which together make the path latent today, but I did not run a daemon to prove it unreachable.
