# Run report — 380-test-suite-false-confidence (run 01)

**Date (UTC):** 2026-08-14    **Branch:** claude/test-suite-false-confidence-t9mfb1 (harness-assigned)    **PR:** [#1229](https://github.com/cuioss/plan-marshall/pull/1229)    **Outcome:** completed — auto-merge armed, landing delegated to the merge queue + orchestrator collect

## Skills loaded

Loaded via bundle path (the `plan-marshall` plugin route was not needed):

- `plan-marshall:ref-code-quality`
- `pm-plugin-development:plugin-script-architecture`
- `pm-dev-python:pytest-testing`
- `pm-dev-python:python-core`
- `plan-marshall:persona-implementer`

## GitHub access path

GitHub MCP server (cloud path).

## Claim re-derivation (source of truth for every claim label)

Every count in the plan was a stated LEAD; re-derived from source:

| Plan claim (HYPOTHESIS) | Re-derived verdict |
|---|---|
| Runner treats exit 0 as pass; most files run zero tests under it | **CONFIRMED.** `test/run-tests.py::run_test` (line 116-119) runs `[sys.executable, str(test_file)]` and returns `result.returncode == 0` as success. Only **2** of **765** `test_*.py` files invoke `pytest.main`; only ~12 have any `__main__` block. Plan's "~10 of ~545" LEAD re-derived to **2 pytest-invoking of 765**. |
| Canonical CI path is pytest via build command (developer trap, not CI hole) | **CONFIRMED.** CI runs `./pw verify` → pytest; `run-tests.py` is never invoked by any workflow. |
| Green build clears test-failure findings even when no tests ran | **CONFIRMED from source.** `script-shared/scripts/build/_build_shared.py::cmd_run_common` line 717 gate `if test_summary is None or test_summary.failed == 0:` → `_reconcile_pending_build_findings` clears `('build-error','test-failure','lint-issue')`. Zero-test run → `test_summary is None` → treated as success → clears. No executed-test count ever consulted. |
| Module stubs are guaranteed no-ops (conftest pre-imports real modules) | **CONFIRMED.** conftest lines 187-188 pre-import real `plan_logging`/`run_config`; `sys.modules.setdefault(...)` in **6** files is therefore a no-op. Plan's "five" LEAD re-derived to **6** (`build-npm/test_npm_execute`, `build-maven/test_maven_execute`, `build-pyproject/test_pyproject_execute`, `build-pyproject/test_pyproject_routing`, `build-gradle/test_gradle_execute`, `script-shared/test_build_config_contract`). The 7th `setdefault` (`manage-solution-outline/test_get_module_context.py:67`) registers a REAL module under a custom name — not a dead mock, out of D3 scope. |
| Developer paths in fixtures | **CONFIRMED.** `/Users/oliver/` (real username) in `test/pm-dev-java/fixtures/sample-build-*.log`; `/Users/dev/` (generic placeholder) in `test/plan-marshall/build-npm/fixtures/**`. |
| Pollution guard snapshots real state before/after every test | **CONFIRMED.** `_pollution_guard` (conftest 690-743) is `@pytest.fixture(autouse=True)`; snapshots `~/.plan-marshall/credentials/` + `.plan/local/`. |
| It was already narrowed once for a performance regression | **CONFIRMED.** `_snapshot_real_plan_local` docstring (conftest 660-667) records the recursive-walk regression that "dominated the whole suite's wall-clock". |
| Two overlapping mechanisms mutate the same globals | **CONFIRMED.** Autouse `_plan_base_dir_sandbox` (monkeypatch) vs manual `PlanContext`/`BuildContext` `os.environ`/`_config_core` save-restore. |

## Deliverables

Per deliverable: what was done, in which commit, and its verification state.

- **D1 — Kill the false-green runner:** DONE (commit `771ea1c`). Deleted `test/run-tests.py`. Updated the developer-facing docs that instructed running it (`testing-standards.md` ×5 spots, `cross-skill-integration.md`, `test/pm-dev-frontend/README.md`) to the canonical `module-tests` build command; dropped the stale reference from a `test_detection.py` comment. The conftest/PlanContext references to the runner were cleaned up in D6 (which reworks that region). No code imports the runner, so deletion is safe. Verified: quality-gate green (plugin-doctor accepted the executor invocations).
- **D2 — Finding-clearing requires executed-test evidence:** DONE (commit `85372c6`). `cmd_run_common` in `_build_shared.py` now computes `tests_run` (the parsed executed-test count = `test_summary.total`, 0 when no summary parsed) and passes it to `_reconcile_pending_build_findings`, which clears `build-error`/`lint-issue` on any green build but `test-failure` ONLY when `tests_run > 0`. The population is published: on the success result as the `tests_run` field (added to the `EXTRA_FIELDS` whitelist so TOON and JSON agree) and stamped into the resolution detail. Verified: zero-test green build retains a seeded test-failure finding; a test-running green build clears it and publishes a non-empty population (2081 build-code tests green). Updated `build-api-reference.md` success-output schema (stale-claim sweep).
- **D3 — Delete dead module-stubbing mocks:** DONE (commit `9f70ea5`). Removed the no-op `sys.modules.setdefault('plan_logging'/'run_config', MagicMock(...))` from 6 files (re-derived from the plan's "five" lead) plus their now-unused `sys`/`MagicMock` imports. The 7th `setdefault` (`test_get_module_context.py`) registers a real module under a custom name — not a dead mock, out of scope. Verified: 135 tests in the 6 files pass against the real (pre-imported) modules.
- **D4 — Normalise developer paths out of fixtures:** DONE (commit `63effe4`). `/Users/oliver/project` → `/home/dev/project` (3 pm-dev-java logs); `/Users/dev/` → `/home/dev/` (4 build-npm logs). No test asserts on these path strings (verified). Placeholder root `/home/dev/` chosen to avoid the real `/home/user/` on the runner. Re-derived: only `oliver` was a real username; `dev` was already a placeholder, normalised too for consistency with the named surface.
- **D6 — Retire manual environment save/restore:** DONE (commit `f65ea10`). `PlanContext`, `BuildContext` (conftest) and `EmptyPlanContext` (`test_manage_files.py`) each hand-rolled a save/restore of process-global `PLAN_BASE_DIR`/`PLAN_DIR_NAME` (+ `_config_core` attrs for PlanContext) — a second mechanism overlapping the autouse `_plan_base_dir_sandbox` monkeypatch. Replaced each with a `pytest.MonkeyPatch()` instance reverted atomically by `undo()`. **Interpretation note:** the plan's literal "migrate remaining users to the fixture" (i.e. delete the classes, move ~60+ call sites to fixtures) was NOT taken; instead the classes keep their `with X()` API but now use the fixture's *mechanism* (monkeypatch). Evidence for the deviation: 60+ call sites make wholesale class deletion high-risk churn, and the done-when — "one mechanism owns those globals" — is met because monkeypatch now owns PLAN_BASE_DIR in the autouse sandbox, the `plan_context` fixture, and all three context managers. Verified: 291 context-manager tests pass, zero call-site changes.
- **D7 — Falsifiability control:** DONE (commit `3dbf711`). `test/test_runner_falsifiability.py`: a deliberately failing test reddens the canonical runner (pytest, non-zero exit); a passing test stays green (so the red is a real verdict); the same failing file run AS A SCRIPT exits 0 (documents the retired defect). Verified: 3/3 pass.
- **D5 — Scope the pollution guard via a marker:** DONE (commit `e29b537`). Introduced the `touches_real_state` marker (registered in `pyproject.toml`; the "complete set of custom markers" comment updated five→six). `pytest_collection_modifyitems` auto-applies it to every `plan_context` user (3330 tests / 189 files); the `_pollution_guard` runs its before/after real-path snapshot only for marked tests and skips it otherwise. **Measured suite time (full `module-tests`, xdist, this cloud runner), same 19623 passed / 14 skipped both runs:** before (guard on every test) **398.59s**; after (guard scoped) **369.09s** — **~29.5s (~7.4%) faster**. The guard was NOT cheap: the delta aligns with the per-test double snapshot removed from ~16,300 non-`plan_context` tests (the `.plan/local/` tree exists in this session — the build harness writes telemetry there — so each snapshot is a real `iterdir`, not a no-op). Single before/after pair, so some is run-to-run variance, but the magnitude matches the guard's mechanism. Refutes the "it is cheap now" claim the plan flagged for measurement.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` is non-empty (production + test
`*.py` changed), so the full path was taken. **`./pw verify` — SUCCESS**: quality-gate
(ruff + mypy production, SPDX, plugin-doctor), test-compile (mypy over 733 test files),
and module-tests (**19623 passed, 14 skipped in 369.09s**, whole-tree pytest) all green.
`UV_HTTP_TIMEOUT=600` was set on every `./pw` call.

## Findings

Verification sub-agent (independent `general-purpose`, read-only) verified all seven
deliverables against `plan.md` and swept beyond the diff for stale claims. Two real
findings, both fixed; one artifact rejected. Per instance:

| # | Source | Finding | Disposition |
|---|---|---|---|
| 1 | sub-agent (D4) | **Real username `/Users/oliver/git/…` survives in `test/plan-marshall/build-maven/fixtures/log-test-data/{README.md, maven-success-real.log, maven-failure-real.log}`** (14 occurrences) — a fixture tree I never swept. D4's done-when ("no fixture contains a real user's home path") is unconditional; I under-derived the population (the exact "asserted absence is the higher-risk half" trap the plan flagged). | **FIXED.** Normalised `/Users/oliver/git` → `/home/dev/git` in all 3 files. Re-verified: `grep /Users/oliver test/` and `/home/oliver` → **0**. 245 build-maven tests still pass (no test asserts on the paths). |
| 2 | sub-agent (D2) | Stale in-code comment `_build_shared.py:263-265` above `BUILD_FINDING_TYPES` still said a green build "terminalizes every pending finding of these types" — now false for `test-failure`. | **FIXED.** Comment rewritten to state the split (build-error/lint-issue clear on any green build; test-failure only when `tests_run > 0`). |
| 3 | sub-agent (D5) | Report's D5 measurement "IN PROGRESS" / Build-gate "pending". | **REJECTED (artifact).** The agent read the report before the `./pw verify` completed; the before/after measurement (398.59s → 369.09s) was recorded immediately after. Not a code gap. |

The sub-agent verified D1, D2 (core), D3, D6, D7 clean from source and confirmed the
out-of-scope assessment: every `marketplace/bundles/**` change is justified as the D2
finding-clearing path + its publish-the-population plumbing, or a D1 doc update — no
unjustified change to tested code. **Re-dispatch note:** after fixing findings 1-2, the
maven consumers were re-run (245 pass) and the `oliver` absence re-derived to 0; a full
re-verify runs before the merge gate.

CI / PR-review findings: **none actionable.** `cuioss-review-bot` reported "No major issues
detected / No security concerns / PR contains tests"; `coderabbitai` and `sourcery-ai` posted
only rate-limit notices (no findings); no inline review threads. CI at PR time: `verify / gate`,
`dependency-review`, `generate-check` green; `verify / verify` (the required whole-suite build)
in progress — landing is gated on it by the merge queue (§ Merge gate).

## Reviewer participation

Expected reviewer population, derived from the `author_login` of each
`marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md`
registry doc (cross-named by `.github/workflows/pr-agent.yml`): **M = 3** —
`cuioss-review-bot` (pr-agent), `coderabbitai` (coderabbit), `sourcery-ai` (sourcery).

| Reviewer (`author_login`) | Verdict | Body evidence / reason |
|---|---|---|
| `coderabbitai` | `rate-limited` | Commit-status "CodeRabbit": state `success`, description **"Review rate limited"** — engaged but did not review this diff. |
| `sourcery-ai` | `rate-limited` | Review body: **"you have reached your weekly rate limit of 500000 diff characters."** |
| `cuioss-review-bot` | `reviewed` | Issue-comment "PR Reviewer Guide 🔍": **"🧪 PR contains tests · 🔒 No security concerns identified · ⚡ No major issues detected."** No inline review threads (`get_review_comments` empty), no requested changes. |

**Coverage: 1 of 3.** `cuioss-review-bot` reviewed the code and found nothing actionable;
`coderabbitai` and `sourcery-ai` were both rate-limited and did not review this diff. **No
actionable review comment exists on any of the three surfaces** (issue comments, review
summaries, inline threads all read), so Step 7's "handle every comment" is satisfied with
nothing to fix. The § Step 8 shortfall disclosure below fired: **"Review coverage 1 of 3 —
`cuioss-review-bot` reviewed (no issues); `coderabbitai` rate-limited (resets ~39 min);
`sourcery-ai` rate-limited (weekly quota)."** Rate limits are routine and outside our
control; per the contract the shortfall is disclosed, not blocked on.

## Cost

- **Tokens:** not available to the agent in this session — this Claude Code cloud session exposes no token counter to the running agent, so any figure would be fabricated.
- **Wall-clock:** one interactive cloud session on 2026-08-14 (UTC); precise start/end timestamps are not exposed to the agent. Concrete measured build figures: baseline `module-tests` **398.59s**; D5-scoped `module-tests` inside `./pw verify` **369.09s** (`0:06:09`); several `./pw quality-gate` runs (~1 min each, warm cache) gated the per-deliverable commits.
- **Population:** this single Claude Code cloud session's activity. ⛔ NOT comparable to a plan-marshall `metrics.toon` total — that counts the orchestrator-plus-agent dispatch tree under plan-marshall's per-task billing boundary, which a single interactive cloud session does not share. No comparable figure exists, so none is presented.

## Contract check (Step 9)

| Step | Verdict |
|---|---|
| 1 Skills loaded | **Done.** Bundle-path loads: ref-code-quality, plugin-script-architecture, pytest-testing, python-core, persona-implementer (§ Skills loaded). |
| 2 Branch | **Done.** Kept the harness-assigned `claude/test-suite-false-confidence-t9mfb1` (not run-created); it was absent on origin, so publishing it was the first action. |
| 3 Plan directory | **Done.** `.../380-test-suite-false-confidence/plan.md` exists (git mv from the flat file); opens with the first-instruction block. |
| 4 Implement | **Done.** Every commit carries the `Co-Authored-By: Claude <noreply@anthropic.com>` trailer; all 7 deliverables addressed. |
| 4 Per-commit gate | **Done.** Every `*.py`-touching commit was preceded by a clean `./pw quality-gate` (`issues[0]` empty, coverage COMPLETE). Paths staged explicitly (never `git add -A`); no stray lockfile churn observed. |
| 4 Pushed | **Done.** Every deliverable commit pushed; this report finalization is the last pre-merge push. |
| 5 Build gate | **Done.** `git diff --name-only origin/main...HEAD -- '*.py'` non-empty → full `./pw verify`: SUCCESS (19623 passed, 14 skipped; quality-gate + test-compile[733] + module-tests). |
| 6 Verification sub-agent | **Done.** Independent general-purpose sub-agent; 2 real findings fixed, 1 artifact rejected (§ Findings). |
| 7 PR cycle | **Done.** PR #1229; all three comment surfaces read; no actionable comment; per-reviewer verdicts recorded. |
| 8 Merge gate | Conditions 1-3 met; auto-merge armed; landing delegated to the merge queue + orchestrator collect (a cloud session cannot block-until-landed). Coverage shortfall (1-of-3) disclosed (§ Merge gate). |
| 8 Bridge | **Clean.** No status/bookkeeping write landed under `doc/plans/` outside this plan's own directory; report carries the PR # and per-deliverable outcome. |
| 9 This check | This table + § What have we learned. |
| GitHub access | GitHub MCP server (cloud path). |
| Branch form | Harness-assigned `claude/*`, kept as-is. |
| Plugin cache | Per the loaded cloud-plan-lane contract, a cloud run **neither performs nor owes** `/sync-plugin-cache` (it reads git-ignored `target/` and writes `~/.claude/`, which the lane may not touch); the `marketplace/bundles/` edits are authoritative in git. (CLAUDE.md's standalone-lane prose says to *record a sync is owed*; the loaded contract supersedes it per the first-instruction precedence rule — noted, not owed.) |

## What have we learned (Step 9)

**No contract change proposed.** The run exercised the cloud-plan-lane contract end to end and it held:

- The independent Step-6 sub-agent caught the one material defect I introduced — an under-derived D4 fixture population (I swept only the plan's *named* surface, and a real-username leak survived in build-maven's `log-test-data` tree). That is exactly the failure the sub-agent exists to catch, and it did. No contract gap — a diligence gap, caught by the designed backstop.
- The three-surface comment read (`get_comments` / `get_reviews` / `get_review_comments`) mattered: `cuioss-review-bot`'s "no issues" verdict lives in an issue comment, the two rate-limit notices in a commit status and a review body. Reading only one surface would have misreported coverage. The contract's insistence on all three was load-bearing.
- The D5 cloud measurement — which I expected to be noise-level (empty watched dirs) — showed a real ~29.5s / ~7.4% delta, because `.plan/local/` exists in-session (build-harness telemetry) so each snapshot is a real `iterdir`. The contract's "measure, don't assume" was right to insist.

The only adjacent observation is **plan-authoring**, not lane-contract: the plan's "Expected surface" named pm-dev-java + build-npm, but the unconditional D4 done-when reached build-maven too — an expected-surface list is a *lead*, not a population. That belongs to `author-cloud-plan` guidance, not this contract, so it is recorded here rather than proposed as a lane-contract edit.

## Merge gate (Step 8)

- **Condition 1 (required contexts):** at the gate, `verify / gate`, `dependency-review`, `generate-check` were green; the required whole-suite `verify / verify` was still `in_progress`, and `mergeable_state` was still `unknown` (GitHub computing). The full `./pw verify` was green locally (19623 passed) and the only change after it is this doc-only report commit, so the required build is expected green. Per the contract, on a merge-queue repo the queue is the enforcer: arming defers the required-green gate to the queue (which re-verifies on `merge_group`) rather than blocking here — this run arms with `verify` in flight and records that.
- **Condition 2 (comments handled):** met — no actionable comment on any of the three surfaces.
- **Condition 3 (report finalized + pushed):** this commit — pushed as the last pre-merge commit, before arming.
- **Condition 4 (coverage disclosure, NOT a block):** fired — "Review coverage 1 of 3: `cuioss-review-bot` reviewed (no issues); `coderabbitai` rate-limited (~39 min); `sourcery-ai` rate-limited (weekly quota)." Rate limits are routine; disclosed, not blocked on.
- **Action:** auto-merge armed (`enable_pr_auto_merge`, SQUASH). A cloud session cannot block-until-landed (no reliable self-confirm inside the turn), so the landing is **delegated** to the merge queue and read by the orchestrator's collect from the PR merge event. A self-wake check-in was scheduled to confirm `state: MERGED` and record the squash SHA to the operator. **This is a completed run, not partial** (§ Step 8: arm-and-hand-off).

## Residue

- **Generic `/Users/dev/` placeholders remain** in `test/plan-marshall/build-gradle/` (mocks + fixtures) and `test/plan-marshall/build-maven/fixtures/sample-maven-*.log`. These are NOT a D4 done-when violation — `dev` is a generic placeholder, not a real user's home path — and they sit outside the plan's named surface (pm-dev-java, build-npm) and outside the accepted finding. Left unchanged to avoid scope creep. A future consistency pass could unify every build fixture on the single `/home/dev/` root (build-npm was normalised to it as part of the named surface); filed here rather than done.
- **`pyproject.toml` line ~112 still cites "14794 tests"** in the `filterwarnings` rationale; the actual whole-tree count is now 19623 passed + 14 skipped = 19637. This drift is pre-existing (the suite grew independently of this plan) and was NOT introduced by any deliverable here, so it was left alone; noted for whoever next edits that comment.
