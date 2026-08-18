# Verification — 430-a-timeout-is-not-a-red-test-and-a-kill-is-not-a-timeout

**Verified against:** commit `af417166dd9f64704fe738720d716c38515061be`   **Landed as:** PR #1193, commit `d4ae2e81ad04c6daf7cb04f59e49e270fce4bb44`   **Verdict:** implemented-with-gaps

> **Adversarially reviewed.** An independent agent re-checked this document against the tree and
> corrected it in place. All six original gaps were upheld; three were added or split out (G7, G8,
> G9); several figures, quotes and SHAs did not re-derive and are corrected inline. The full record
> — including what could **not** be re-checked — is § Adversarial review at the end.

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
touched. Re-derived during adversarial review and **corrected** — the original
attribution was wrong in three places:

- `_build_shared.py` **and** `_build_format.py` were later touched by `fa452e0c`
  (#1229). The original text named only `_build_shared.py`.
- `_cmd_pre_commit_verify_freshness.py`, `manage-tasks/SKILL.md`,
  `phase-5-execute/SKILL.md`, `push.md` and `build-systems-common.md` were touched
  by `e2b6665b` (#1279) — and by **no** other commit after `d4ae2e81` except as
  noted below. `aeab5ab5` (#1283) touched **none** of them: its 44-file write-set
  contains exactly one file relevant here, the *test* module
  `test/plan-marshall/manage-tasks/test_pre_commit_verify_freshness.py`. The
  original text's attribution of these five files to `aeab5ab5` does not re-derive.
- `push.md` was additionally touched by `308528d6` (#1211) and `60e5fd81` (#1206),
  both after `d4ae2e81`; the original text named neither.
- `workflow/execution.md` by `1da26b13` (#1200) and `9135f275` (#1287); the
  original text named only the latter.

Every one of them **extended** this plan's work (more `stale` reasons, more
consumer rows) rather than reverting it — verified by reading the current text of
each, both originally and again on adversarial review.

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
| D0 | Enumerate what daemon + harness already emit, and which consumer reads which field; publish the population | Vocabulary and per-consumer reads enumerated, population published | **yes** | **yes** | **yes** | **no — the published population is short by one** | `marketplace/bundles/plan-marshall/skills/extension-api/standards/build-systems-common.md:126-186` — three-condition table, 11-row consumer table, transitive-derivation rule, three failure shapes. Population (11 gates, 11/11 read a status field) published in `report-01.md` § D0, but re-derived on adversarial review as **12**: `plan-retrospective/scripts/analyze-logs.py` imports `_ledger_core.read_entries` and filters `kind == 'build'` — the derivation's own stated import set — and appears in neither list → **G7**. Vocabulary incomplete → **G6**. Boundary honoured: `classify_terminal` body byte-identical; `manage-change-ledger.py` carries no code change (`git show --stat d4ae2e81`) |
| D1 | Three conditions distinguishable at EVERY consuming gate | A timeout cannot be presented as a test failure; a harness kill cannot be presented as a timeout | **yes** | **yes** | **yes** | **yes** (for the two stated directions) | Gate-by-gate below, every row re-opened at HEAD on adversarial review. All 11 published gates present and extended, not reverted, by #1279 / #1287 (**not** #1283 — see the corrected Supersession block). A twelfth consumer exists and is not in the set → **G7** |
| D2 | Settle the subset/superset inversion; diagnose, do not adjust | The mechanism is named | **yes** | **yes** | **yes** | **yes** | `manage-run-config/standards/run-config-standard.md` § "What `timeout_seconds` actually measures" — three named properties. No bound changed: `SAFETY_MARGIN=1.25`, `HIGHER_WEIGHT=0.80`, `MINIMUM_TIMEOUT_SECONDS=120` (`run_config.py:25-27`), `MIN_TIMEOUT=60`/`MAX_TIMEOUT=1800` (`_build_execute.py:106,111`), `DEFAULT_BUILD_TIMEOUT=300` (`_build_shared.py:205`), `PYTEST_OUTER_FLOOR_SECONDS=330` (`_pyproject_execute.py:64`) — none appears in the landed diff |
| D3 | Regression tests with matched controls, each verified RED pre-fix | Red test still fails; timeout does not; kill does not — **read as "is not presented as a red test", not as "does not refuse"**; see the note below the table | **yes** | **mostly** | **yes** | **partial** | 50 cases in `test_non_finish_discrimination.py` all pass (re-derived on adversarial review: `--collect-only` → 50 collected, `-q` → 50 passed); two independent mutations (above) go RED with their controls staying green. One totality test is vacuous — see G3 |

⚠ **D3's done-when needs its reading stated, because the literal one is not what shipped.**
The plan says a timeout and a kill must *not* fail the gate. What shipped is that neither is
ever presented as a **red test** — no findings stored, no synthesised `errors[]` row, no
learner update, its own status carried verbatim (`test_non_failure_stores_no_findings`,
`test_non_failure_synthesises_no_error_row`, `test_kill_is_not_presented_as_a_timeout`).
Both still **refuse** the freshness gate, which admits only `status == 'success'`
(`_cmd_pre_commit_verify_freshness.py:465-471`), with a distinct `reason` naming which
non-finish it was. That is the correct resolution — a fix that let a non-finish pass the
freshness gate would be the "every non-finish benign" failure the plan's own ⛔ forbids — but
the original table asserted the literal condition without recording that it holds only under
this reading.

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
  the population to be published; the report does publish it, so *that* is noted,
  not faulted.
- **The figure itself is wrong.** Re-derived on adversarial review by re-running the
  derivation's own stated method — `grep -rn "read_entries" --include=*.py
  marketplace/` — the ledger surface has three readers of `kind=build` rows, not
  two: `manage-change-ledger.py`, `_cmd_pre_commit_verify_freshness.py`, and
  `plan-retrospective/scripts/analyze-logs.py` (`:49` imports `read_entries`,
  `:178` filters `kind != 'build'`, `:173` hard-codes the five-value status
  vocabulary). The third is in neither the standard's table nor the report's
  population. The plan flagged "every consuming gate is identified" as its
  highest-risk asserted-**completeness** claim; the original pass verified all
  eleven published rows and did not re-derive the set, so it inherited the claim
  rather than checking it. → **G7**, and the concrete thing that consumer already
  drops → **G8**.

### D1 — verified per gate at HEAD

| Gate | Verified how |
|---|---|
| #1 `_derive_build_status` | `execute-script.py.template:484-490`; parametrised cases `[status: killed\n-0-killed]`, `[status: unknown\n-0-unknown]`, `[status: totally-made-up\n-0-unknown]`, `[status: indeterminate\n-0-unknown]` all collected and passing |
| #2 `run_job` narrowing | `_marshalld_supervisor.py:305`; **mutation-confirmed RED** (see Method) |
| #3 `_daemon_result_to_direct` | `_build_execute_factory.py:408-494` + `_result_for_log_verdict:497-543`; aliased `WIRE_STATUS_KILLED`/`RESULT_STATUS_KILLED` imports (lines 63, 69-71, with the two-vocabularies hazard comment at 73-78) confirm N8's fix; catch-alls return `indeterminate_result`, not `error` |
| #4 `cmd_run_common` | `_build_shared.py:669-720` — `killed` branch precedes `indeterminate` precedes `timeout`, all ahead of the build-failure path; `message` propagated rather than reconstructed; `timeout_used_seconds` preserved on the kill |
| #5 `_render_job_status` | `build-server-client/scripts/build_server.py:278-301` — unchanged, and correct: `job_status == STATUS_KILLED` attaches `_KILLED_MESSAGE` |
| #6 `classify-outcome` | `manage-change-ledger.py:219-224` — the `killed`-row branch is reachable now that `killed ∈ WRAPPER_CLAIMABLE_BUILD_STATUSES` (`_ledger_core.py:62`). See G5 for the one direction it still collapses |
| #7 `pre-commit-verify-freshness` | `_cmd_pre_commit_verify_freshness.py:135-233` (`_STALE_BY_STATUS`, `_stale_reason`) and `:485-499` (caller). `observed_status` is omitted on **three** documented routes, not two — `worktree_mutated`, the no-readable-status `build_indeterminate` sub-case, **and both cross-check refusals** (`_verdict_for_candidates`'s `REFUTED` arm, `:300-322`, which never emits the field because every candidate there was `success`). All three are named in the canonical reason table at `manage-tasks/SKILL.md:302-306`; the original "exactly the two documented routes" was scoped to `_stale_reason`'s own docstring and undercounted the verb. `key == 'success'` is unreachable because `_stale_reason` runs only when the success-candidate list is empty, and that list's predicate (`kind == build` ∧ `status == 'success'` ∧ `sha == current`) is a strict refinement of `_stale_reason`'s own (`kind == build` ∧ `sha == current`), so an empty candidate list forbids `matching[-1]['status'] == 'success'` — re-derived at `:465-471` vs `:222-231` on adversarial review, checked rather than assumed |
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

1. **§ D3: "`test/plan-marshall/script-shared/test_non_finish_discrimination.py` (44 cases)"** — the file at HEAD is byte-identical to the file at `d4ae2e81` (`diff` against `git show d4ae2e81:…` → identical) and collects **50** cases (35 test functions, 7 `parametrize` decorators). Re-derived at the moment of writing by running the file: `50 passed in 0.23s`. Re-derived a second time on adversarial review, independently: `--collect-only` → `50 tests collected`, `-q` → `50 passed`. → **G4**.
2. **§ D1 gate #7 and § D3: "12 cases in `test_pre_commit_verify_freshness.py`"** — the landed diff adds **7** test functions, one of which carries a 5-way `parametrize`, i.e. **11** collected cases, not 12 (`git show d4ae2e81 -- test/plan-marshall/manage-tasks/test_pre_commit_verify_freshness.py | grep '^+.*def test_'` → 7; a single `+@pytest.mark.parametrize` with five tuples). Re-derived on adversarial review from the same diff: 7 and 5, so 11. → **G9** (split out of G4, because it is a different figure at different sites).

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

## Adversarial review

**Reviewed by:** an independent agent that did not write this document, working from the tree at
`d958307c` (both `af417166` and the landed `d4ae2e81` are ancestors of it; the plan directory was
clean, `git status --porcelain` showed no modification to any file under it).

**Checked — and by what means.**

*Every gap (all six), including both mediums and every `high`* — there are no `high` gaps, so every
gap was checked:

- **G1** — opened `test_executor_runtime.py:595-610` (the header comment) and `:705-745` (the
  parametrisation), confirming the comment's clause (3) contradicts `('status: killed\n', 0,
  'killed')` at `:726` and the template's own rule 3 at `execute-script.py.template:444-454`.
  Re-ran the diff check: `git show d4ae2e81 -- …test_executor_runtime.py | grep '^[-+]'` shows the
  commit removed the *inline* comment (`- # 'status: killed' at exit 0 stamps error`) and left the
  header block in neither the `+` nor the `-` set. Ran the **broader** sweep the gap's Done-when
  now records (`grep -rn --binary-files=without-match "derived-only" test/ marketplace/`, then
  filtered for `killed`, then again over `DERIVED_ONLY_BUILD_STATUSES` /
  `WRAPPER_CLAIMABLE_BUILD_STATUSES` across `*.py`, `*.md`, `*.template`): exactly one stale
  instance, plus one correct statement at `error-handling.md:435` that must not be changed, plus
  `test_build_class_stamp_discriminator.py:717-745` which was read and is current. **Upheld.**
- **G2** — **executed** the function on the argument the clause is about:
  `wire_status_from_result('indeterminate')` → `'indeterminate'`; `… in TERMINAL_STATUSES` →
  `False`; `sorted(_RESULT_STATUS_TO_WIRE)` → `['error','killed','success','timeout']`;
  `wire_status_from_result('totally-made-up')` → `'totally-made-up'`. Then confirmed **every link of
  the asserted mechanism at its own file and symbol**, because a compatible callee is not
  confirmation: `read_log_verdict:701-734` parses any column-0 `status:` line with no vocabulary
  check; `run_job:305` feeds `verdict.status` into it; `marshalld._execute:534` records the payload;
  `_is_terminalized:499` and `_wait:453` both gate on `TERMINAL_STATUSES`; `_wait` falls through to
  `_running_status:461-475`, which returns `STATUS_RUNNING` **unconditionally** whatever the journal
  entry holds; `build_server._render_job_status:292-293` maps daemon `status` → `job_status`; and
  `_route_to_daemon:600-606` `continue`s the `while True` on `job_status == 'running'`. The loop is
  real. `git show d4ae2e81 -- _marshalld_supervisor.py` confirms `- status = 'failure'` → `+ status
  = wire_status_from_result(verdict.status)`, so the plan did introduce the path. `_marshalld_audit`
  `FATE_UNKNOWN` bucketing confirmed at `:311`. **Upheld, mechanism confirmed end-to-end, severity
  `medium` upheld** — the path is latent, so it is not shipped wrong behaviour today.
- **G3** — **proved vacuous without needing a mutation.** The class docstring asserts "Every
  `_build_result` status has an explicit wire row". `STATUS_INDETERMINATE` exists
  (`_build_result.py:153`) and is the fifth member of the `DirectCommandResult.status` `Literal`
  (`:112`); `_RESULT_STATUS_TO_WIRE` has four keys (executed above). So the property the class
  names is **false at HEAD**, and the suite nonetheless reports `50 passed`. A test that is green
  while the property it asserts is violated is vacuous by demonstration. **Upheld.**
- **G4 / G9** — re-derived both figures. `test_non_finish_discrimination.py` at HEAD is
  byte-identical to `git show d4ae2e81:…` (`diff -q` → identical) and collects **50** (35 test
  functions, 7 `parametrize` decorators; `--collect-only` → `50 tests collected`, `-q` → `50
  passed`). The freshness diff adds **7** test functions and exactly one `parametrize` with 5
  tuples → **11**, not 12. **Both upheld; G4 was SPLIT** — two distinct wrong figures at three
  sites, either correctable without the other, so the 12→11 figure is now **G9**.
- **G5** — opened `manage-change-ledger.py:195-240`: the chain is `killed`/`killed`-row/`timeout`/
  `success`/`else → undecidable`, and `status: error` reaches the `else`. Confirmed the severity
  rationale **at its cited symbol**: `await-long-running.md:24` does say `classify-outcome`
  "remains only for any residual detached-build path that is not daemon-served", and
  `grep -rn "classify-outcome"` across `marketplace/` finds no script call site. **Upheld at `low`**
  — but two supporting details were wrong and are corrected: the report quote "yes (already
  correct)" does not exist (the actual cell is "yes — but its killed-row branch was unreachable for
  an inner kill", `report-01.md:67`), and the docstring reference `:207-210` is `:208-210`.
- **G6** — `grep -n "indeterminate" build-systems-common.md` returns **nothing** (exit 1), while
  `build-execution.md:51,63,71,88,92,93,425,426,436` and `build-api-reference.md:22` both document
  five statuses. **Upheld.**

*Every clean-pass row and every behavioural done-when in the deliverable table:*

- **D1, all eleven published gates, re-opened at HEAD** — `execute-script.py.template:484-490`
  (and its rule-3 docstring); `_marshalld_supervisor.py:305` + `_terminal_payload:180-225`;
  `_build_execute_factory._daemon_result_to_direct:408-494`, `_result_for_log_verdict:497-543`,
  and the aliased `WIRE_STATUS_*`/`RESULT_STATUS_KILLED` imports at `:63,69-71` with the hazard comment
  at `:73-78`; `_build_shared.cmd_run_common:669-725` (branch order `killed` → `indeterminate` →
  `timeout` → `success`, `message` and `timeout_used_seconds` propagated); `build_server.py:292-301`;
  `manage-change-ledger.py:219-233`; `_cmd_pre_commit_verify_freshness.py:135-233`, `:262-322`,
  `:436-500`; `build-api-reference.md:22`; `execution.md:368-378` (five-way table + the ⛔ on
  triaging a non-finish); `phase-5-execute/SKILL.md:1065`; `push.md:49,52,58`.
- **The emit choke point is genuinely single** — `grep -rn "cmd_run_common"` finds exactly one
  caller module (`_build_execute_factory.py:967,1024`), so no build wrapper has a second emit path
  that could bypass the `killed`/`indeterminate` branches. This was not checked on the first pass.
- **`_build_format.EXTRA_FIELDS`** read at `:41-50`: both `message` **and** `timeout_used_seconds`
  are whitelisted, so the kill's propagated bound is not silently dropped by the TOON formatter.
  Also not checked on the first pass.
- **D2** — `run-config-standard.md:573-611` read in full; all three named properties confirmed
  against code, not just against prose: the doubling at `_build_execute.py:342`
  (`min(timeout_seconds * 2, MAX_TIMEOUT)`) and the retrieval margin at `run_config.py:272`
  (`int(persisted * SAFETY_MARGIN)`) are property 1 as described. All seven bounds re-read at HEAD
  (`1.25 / 0.80 / 120 / 60 / 1800 / 300 / 330`) and `git show d4ae2e81 | grep '^[-+].*<constant>'`
  returns only report prose — **no constant changed**. `classify_terminal` likewise appears in the
  diff only in comments and report text. Arithmetic re-run: `642`, `611`, `44.89`, `3077` all hold.
- **Every SHA in the Method section re-derived** with `git log --oneline -3` per file. Three
  attributions did not survive — see the corrected Supersession block above.

*Every "swept the tree, clean" claim, re-run with a broader pattern than the original:*

- The no-blind-retry duplication: swept `grep -rn "blind-retry"` across `marketplace/`, `test/` and
  `doc/developer/` rather than for the constant names. **Four literal code copies** (`:185`, `:180`,
  `:102`, `:152`) — the stated figure holds; the ~25 further hits are prose restatements in docs and
  tests, a different thing. **Upheld.**
- The `~/.plan-marshall` sandbox residue: derived both sets and diffed them —
  `grep -rln "home_root" test/` (6 files) minus `grep -rln "PLAN_MARSHALL_HOME" test/` (25 files)
  leaves exactly `test/conftest.py`, whose only `home_root` occurrence is a docstring line
  (`:1069`). The claim "every test module referencing `home_root` also sets `PLAN_MARSHALL_HOME`"
  **holds**, and the "no global sandbox in conftest" caveat is accurate.
- The consumer-set derivation: re-ran it from the import set rather than reading the published
  table — this is what produced **G7** and **G8**.
- The diff's write-set: `git show --name-only d4ae2e81` re-counted → 28 files, 10 production
  (including the executor template) + 6 test = the stated 16 Python-bearing files ✓, and exactly
  `plan.md` + `report-01.md` under `doc/plans/` ✓.

**What was NOT re-checked.**

- **The two mutations could not be replicated.** Both were attempted; the sandbox's command
  classifier refused to run `pytest` while a production file was modified, so the mutation was
  reverted immediately (`git diff --quiet -- _build_execute.py` → exit 0, clean) and the approach
  abandoned. The originally reported mutation results are therefore **not independently confirmed**
  — but they are *structurally* corroborated: `TestRunJobNarrowingPreservesTheNonFinish:271-296`
  drives the real `run_job` against a real child and asserts `payload['status'] == 'killed'` /
  `'timeout'` with a positive control asserting `'failure'`, so it cannot be green under `status =
  'failure'`. Treat this as reasoning, not as replication.
- **Everything the original pass listed as unverifiable stays unverifiable** — the D2 wall-clock
  measurements, the per-round suite totals, PR #1193's CI conclusions, the reviewer-participation
  table, the sub-agent token self-reports, and the `.plan/`-provenance ~642 s / ~618 s timings.
- **G2's runtime reachability** was not proved either way; no daemon was run. The static argument is
  unchanged and remains the whole of the evidence.
- **The four remaining Residue-carried-forward rows** were re-checked only to the extent noted
  above; the "subset/superset measurement is a single pair" row was not re-measured.
- **The 19 + 12 sub-agent finding tables** were not re-enumerated beyond the sample the original
  pass took.

| Item | Original claim | Verdict | Evidence |
|---|---|---|---|
| G1 | Stale pre-fix rule in `test_executor_runtime.py:604-606`; `medium` | **upheld**, Done-when rewritten | Header comment contradicts `:726` and the template rule at `:444-454`; the landed diff touched the inline comment only. Broader sweep found no second instance |
| G2 | `indeterminate` has no wire row; non-terminal wire status hangs the client; `medium` | **upheld**, mechanism confirmed link-by-link | Function **executed**: `wire_status_from_result('indeterminate')` → `'indeterminate'`, not in `TERMINAL_STATUSES`. `_wait:453` → `_running_status:461-475` returns `running` unconditionally → `_route_to_daemon:600-606` re-polls forever. `git show` confirms the plan replaced a hard-coded terminal `'failure'` |
| G3 | Totality test hard-codes its population; `medium` | **upheld**, proved by demonstration | The asserted property is false at HEAD and the suite is green (`50 passed`). No mutation required |
| G4 | Two wrong counts in `report-01.md`; `low` | **upheld but SPLIT** | 50 (re-derived twice) and 11 (re-derived from the diff) are two distinct figures at three sites; the 12→11 figure is now **G9**, per one-row-per-instance |
| G5 | `status: error` → `undecidable` at classify-outcome; `low` | **upheld**, two supporting details corrected | Chain read at `:219-233`; the quoted report cell does not exist and was replaced with the real text; docstring ref `:207-210` → `:208-210`. Severity citation `await-long-running.md:24` is exact; `low` stands |
| G6 | `indeterminate` absent from the canonical section; `low` | **upheld** | `grep -n "indeterminate"` on that file returns nothing; the other two standards document five |
| G7 | *(new)* D0's published consumer population of 11 is short by one | **added**, `medium` | `analyze-logs.py:49,173,178` reads `kind=build` `status` through `_ledger_core.read_entries` — the derivation's own import set — and is in neither the standard's table nor the report's population |
| G8 | *(new)* `analyze-logs` folds undetermined builds into `unknown` and then drops the key | **added**, `low` | `:173-174` keys five statuses, `:183` folds into `unknown`, `:193-196` returns only four; `log-analysis.md:22-28` mirrors the omission. `build_count` no longer equals the sum of the reported buckets |
| G9 | *(split from G4)* "12 cases in `test_pre_commit_verify_freshness.py`" | **added**, `low` | 7 added test functions, one with a 5-way `parametrize` → 11 |
| Verdict `implemented-with-gaps` | headline | **upheld** | All four deliverables are implemented; D0 and D3 are incomplete, none is unimplemented, so `partially-implemented` would be wrong |
| D0 row `Complete: partial` | deliverable table | **re-severitied to `no`** | The shortfall is not only vocabulary (G6) — the published population itself does not re-derive (G7) |
| D3 done-when | "timeout does not fail the gate" | **rewritten** | Literally false against the freshness gate, which refuses on `timeout`/`killed` by design; the condition holds only as "is not presented as a red test". Now stated |
| Supersession SHAs | `aeab5ab5` (#1283) touched five files | **refuted** | Its 44-file write-set contains none of them — only the *test* module. `_build_format.py` (`fa452e0c`) and `push.md` (`308528d6`, `60e5fd81`) were also omitted |
| Gate #7 "two documented routes" | `observed_status` omission | **corrected to three** | The `REFUTED` arm at `:300-322` is a third; all three are named at `manage-tasks/SKILL.md:302-306` |
| `key == 'success'` unreachable | gate #7 | **upheld, with the derivation now stated** | The candidate predicate is a strict refinement of `_stale_reason`'s, so an empty candidate list forbids a `success` last-row |
| "44 cases" / "12 cases" contradictions | Report accuracy | **upheld** | Both re-derived independently |
| Bounds / `classify_terminal` unchanged | Out-of-scope compliance | **upheld** | All seven constants re-read at HEAD; `git show d4ae2e81 | grep` finds them only in report prose |
| No-blind-retry duplicated four times | Residue | **upheld under a broader sweep** | Swept on the sentence, not the constant names: four code copies, the rest prose |
| `~/.plan-marshall` residue | Residue | **upheld** | Set difference of the two greps leaves only `test/conftest.py`, and its hit is a docstring |

**Documents corrected.**

- `gaps.md`: open items 6 → **9**. **G7** and **G8** added (the missed consumer and the count it
  drops). **G4 split**, with the freshness figure carried out to **G9**. G1's Done-when rewritten to
  a mechanically decidable check that names the one line which must *not* change. G5's fabricated
  quote replaced with the actual `report-01.md:67` cell text and its docstring line reference
  corrected; its `where` narrowed to `:219-233`. G8's and G7's line references verified individually.
  A `## Refuted during adversarial review` section added recording that **no gap was refuted**, and
  what was corrected instead.
- `verification.md`: the **Supersession** block rewritten — the `aeab5ab5` attribution does not
  re-derive and two later commits were missing. The **D0 row** moved from `Complete: partial` to
  `Complete: no` with G7 named. A second D0 shortfall bullet added for the population figure. The
  **D3 done-when** annotated with the reading under which it holds. **Gate #7**'s "two documented
  routes" corrected to three, and the `key == 'success'` unreachability argument spelled out rather
  than asserted. This section appended.

**Residual doubt — what a third reviewer should look at first.**

1. **The mutation evidence is now single-sourced.** Neither mutation could be re-run here. A
   reviewer with an unrestricted sandbox should replay both and confirm the reported RED/GREEN
   split; if either fails to go red, D3's headline collapses and G3 stops being the only vacuous
   guard.
2. **G7 may not be the last missing consumer.** The re-derivation covered the *ledger* surface's
   import set. The other three surfaces — wrapper TOON, daemon wire, freshness verdict — were
   verified row-by-row against the published table but were **not** independently re-derived from
   their own import sets (`read_log_verdict`, `job_status`, and every reference to
   `pre-commit-verify-freshness`). The same method that found G7 has not yet been applied to them.
3. **The `indeterminate` reachability question.** `_build_shared.cmd_run_common:700-712` prints a
   column-0 `status: indeterminate` line, and `read_log_verdict` reads exactly such lines out of a
   job log. Whether a daemon-supervised child can ever reach that print — the re-entrancy guard says
   no, nothing enforces it — decides whether G2 is latent or live, and nobody has run a daemon to
   find out.
