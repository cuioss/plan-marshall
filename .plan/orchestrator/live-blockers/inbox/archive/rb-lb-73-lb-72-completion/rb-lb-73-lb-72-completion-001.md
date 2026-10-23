envelope_version=1
sender_type=plan
sender_id=rb-lb-73-lb-72-completion
epic=live-blockers
kind=landing
created=2026-10-23T14:03:59Z

```landing-facts
schema=landing-facts/1
plan_id=rb-lb-73-lb-72-completion
epic=live-blockers
pr=#1843
merge_state=merged
cleanup_owed=false
deliverables_total=4
deliverables_done=4
total_tokens=unknown
harness=opencode
model=deepseek-v4.1-flash/high
effort=high
plugin_version=0.1
executor_version=0.1.1989
steps=setup:done,implement:done,build-gate:done,self-review:clear,pr:done,reviews:done,merge:done
step.sonar-roundtrip.open_issue_count=0
step.sonar-roundtrip.open_issue_rules=none
```

guard: present

## Deliverables

Merged as `3873b6695` (PR #1843). All four deliverables are fully met; each Done-when is met as
written. Failing evidence was captured against the unfixed tree at base `e40f50aa1` (the PLAN-LB-72 /
PLAN-LB-78 defects are still present there) or by mutating the committed fix. Build logs are under
`.plan/local/plans/NO_PLAN/build-results/`.

### D1 — each rule stated once; a clean summary review qualifies (commit `dd589e323`)

| Done-when | Verdict | Order | Failing run |
|---|---|---|---|
| branch row names one set, no sole-source sentence | met | test-first | `e40f50aa1` / 054206: `test_branch_rule_states_one_set_of_prefixes` |
| §0a template has the `order` slot | met | test-first | `e40f50aa1` / 054206: `test_progress_template_carries_the_order_slot` |
| §1 states grading by order; §3/§6 refer, don't restate | met | test-first | `e40f50aa1` / 054206: `test_rules_state_the_order_grading_once` |
| §6 asks the failing-run identifier only when the order has one | met | test-first | `e40f50aa1` / 054206: `test_pr_body_requires_the_failing_run_only_for_orders_that_have_one` |
| §4 states the docs-only `test-compile` rule | met | test-first | `e40f50aa1` / 054206: `test_build_gate_states_the_docs_only_test_compile_rule` |
| §7 credits the marker-bearing summary comment; others keep current-head | met | test-first | `e40f50aa1` / 054206: `test_merge_gate_counts_the_marker_bearing_summary_comment` |
| §7 re-reads the review surfaces in the question step and before enqueue; late review invalidates | met | test-first | `e40f50aa1` / 054206: `test_merge_gate_question_rereads_the_review_surfaces` |
| §7 unresolved thread / outside-diff finding blocks the standing authorization | met | test-first | `e40f50aa1` / 054206: `test_merge_gate_blocks_on_an_open_thread_or_outside_diff_finding` |
| the PLAN-LB-72 gate state is a qualifying fixture | met | test-first | `e40f50aa1` / 054206: `test_the_plan_lb_72_merge_gate_state_qualifies_as_a_review` |
| base-moved merge supplies `{commit_trailer}` | met | test-first | `e40f50aa1` / 054206: `test_base_moved_merge_carries_the_commit_trailer` |

### D2 — tests that can fail for the reason they name (commit `3c38d9218`)

| Done-when | Verdict | Order | Failing run |
|---|---|---|---|
| the timeout test fails when the real `_augment_resolved` raises | met | mutation-after | `dd589e323` mutated to raise / 062010: `1800 != 1234` |
| the probed-layout test fails when the versioned probe is dropped | met | mutation-after | `3c38d9218` mutated / 062139: versioned layout not named |
| the `test-compile` evidence test fails when the token is removed | met | mutation-after | `3c38d9218` mutated / 062305: token not beside the sha |
| an absent glob helper reports `glob helper unavailable: ImportError`, every path builds | met | none (behaviour holds at base; test is new) | green 061318 |
| a non-`ImportError` at import names a reason, every path builds | met | test-first | `e40f50aa1` / 061153: `RuntimeError: translator exploded` propagated |

### D3 — refuse a stale executor (commits `9b8224395`, `756a77b1f`, `25b3eac30`)

| Done-when | Verdict | Order | Failing run |
|---|---|---|---|
| §0 has the skew check before `resolve`, naming blocked + the regenerate remedy | met | test-first | `e40f50aa1` / 062830: no `executor-skew` |
| the comparison answers skew / match / could_not_check, last ≠ match | met | test-first | `e40f50aa1` / 062830: `AttributeError: _executor_skew` |

### D4 — the build gate and `resolve` state only what is true (commits `dbd14e964`, `85a6d7c83`, `c4aff924f`, `b69e35b3a`)

| Done-when | Verdict | Order | Failing run |
|---|---|---|---|
| no creation claim; the check runs before the first routed build; a build with no executor runs in-process | met | test-first | `e40f50aa1` / 063331: `AttributeError: cmd_build_routing`; green composition test 074058 |
| §2/§4 agree on routing; §4 states the routed-build shell-timeout and the no-`verify` rule | met | test-first | `e40f50aa1` / 063331 |
| one gate canonical named; `canonicals` is a list; missing architecture is not `build_command_unresolvable` | met | test-first + mutation-after | `e40f50aa1` / 063331; guard removed → 075705 |
| OpenCode without a session id returns `runtime_stamp_reason` | met | test-first | `e40f50aa1` / 063331 |
| §0a requires the re-read after compaction/restart/idle gap, with a template slot | met | test-first | `e40f50aa1` / 063331 |
| §8's rule check names read-class shell ops, failed routed builds, model switches, restarts/killed agents | met | test-first | `e40f50aa1` / 063331 |

Per-head test runs (`module-tests`): `dd589e323` targeted green (merge_gate, order, branch_rule,
progress_template, failing_run, test_compile, base_moved_merge); `3c38d9218` targeted green
(glob_helper, probed_layout, missing_skill, build_classify, pushed_head, build_timeout); `9b8224395`
targeted green (executor_skew); `dbd14e964` full suite green 065635 (26810); `85a6d7c83` full suite
green 074217 (26811); `c4aff924f` full suite green 081128 (26811); `b69e35b3a` test-compile green
083203 and full suite green 083307; `756a77b1f` verify green 113426 (31876); `39701dea8` verify green
114738 (31940); `25b3eac30` verify green 122547 (31942); `e1b94faf4` verify green 130156 (31942).
CI `verify` was green on every pushed head after the first (the first failed on a test-module mypy
error, fixed in `b69e35b3a`).

## Personas and skills

- Every step applied `plan-marshall:persona-implementer` (the spec's declared persona) for code and
  text work, `plan-marshall:persona-module-tester` for the test work, and
  `plan-marshall:persona-code-reviewer` for the three self-review rounds and for triaging every PR
  comment.
- D1 and D2 declared: `pm-plugin-development:plugin-architecture`,
  `pm-plugin-development:plugin-script-architecture`, `pm-dev-python:python-core`,
  `plan-marshall:ref-code-quality`, `pm-dev-python:pytest-testing`,
  `plan-marshall:persona-module-tester`.
- D3 declared: `pm-plugin-development:plugin-architecture`, `pm-dev-python:python-core`,
  `plan-marshall:ref-code-quality`, `pm-dev-python:pytest-testing`,
  `plan-marshall:persona-module-tester`.
- D4 declared the D1 set plus `pm-documents:ref-documentation`.
- `skills added: none` — no deliverable touched a module outside the spec's Expected Surface.

## Hypotheses

- executor mapping version readable through `plugin_registry.read_executor_version` — **confirmed**,
  `plugin_registry.py:224-246`.
- the timeout test replaced the real `_augment_resolved` with a lambda — **confirmed** (base test).
- the probed-layout test asserted the unversioned fallback — **confirmed** (base test).
- `_route_to_daemon` submits without checking the executor — **confirmed**,
  `_build_execute_factory.py:909-933`.
- the relative worktree path is forwarded unchanged — **refuted**,
  `_build_execute_factory.py:909,918` resolves it with `Path(...).resolve()` before the command is built.
- worktree creation supplies the executor — **refuted**, `git-workflow.py:1911-1947`
  (`_ensure_worktree_plan_local_real`) creates only `.plan/local`.
- the executor maps `runbook_lane` to a versioned path that can predate the loaded text — **confirmed**
  by CodeRabbit's review of the first cut and fixed in `756a77b1f`.

## Findings

**Self-review round 1** (3 high, 3 medium-low, 6 low): routing contradiction left in §2's `down`
bullet; D4-1's unit test only asserted a decision dict; the architecture fixture was vacuous
(a crawl-based check, no build file). All three fixed in `85a6d7c83`. Also fixed there: a dangling
`coderabbit.md` section reference, the `runtime_stamp_reason` wording, the §0 field table, and the
`_augment_resolved` stub-advertisement docstring.

**Self-review round 2**: M1 (missing mutation evidence for the renamed architecture test) — fixed by
removing the guard (075705, `build_command_unresolvable`); M4 (hand-parsed `_project.json`) — fixed by
delegating to `_architecture_core.load_project_meta`; L1/L6/L7 fixed. Accepted: M2 (flat installs
answer `could_not_check`, which is the spec's own arm), L2/L3/L4/L5/L8.

**Self-review round 3**: 23/23 Done-whens met; nothing open that blocks.

**CI**: `verify` failed on `test/plan-marshall/runbook-lane/test_runbook_lane.py:1772` — mypy
`no-any-return` from a dynamically loaded module. Fixed in `b69e35b3a` (typed local); test-compile and
the suite re-run green.

**PR comments** (CodeRabbit, 4 findings, all fixed + replied + resolved):
1. `_lane_text_version` scanned `root.parts` — fixed in `756a77b1f` via `resolve_bundles_root` +
   `select_live_version_dir` (no duplicated grammar).
2. The version must come from the LIVE install, not the executing (possibly stale) script — fixed in
   `756a77b1f`, pinned by `test_executor_skew_compares_against_the_live_install_not_the_executing_script`.
3. The order test's `'order' in section` was vacuous — fixed in `756a77b1f` (backticked `` `order` ``
   and `§1`).
4. `could_not_check`'s reason conflated unreadable with read-but-empty — fixed in `25b3eac30`, with two
   unit tests.

## Reviewers

| Reviewer | Required | Result | Head | History |
|---|---|---|---|---|
| coderabbit | yes (quota-limited) | reviewed | `39701dea8` (formal COMMENTED review at 12:00:34; summary marker `coveredCommitId=39701dea8 kind=reviewed`) | triggered 08:22, 08:40 (refused), escalated 10:39, reviewed 10:47 on `b69e35b3a`; triggered 11:55 (review 12:00 on `39701dea8`); triggered 12:33 and 13:10 (both refused, "Review rate limited"); every finding handled and every thread resolved |
| sourcery | no (optional, quota-limited) | refused | — | triggered 08:22, 08:40, 11:06, 11:55; hard quota ("250,000 diff characters") throughout; does not gate |

**Standing review authorization** (quota-limited reviewer): qualifying review on `39701dea8`; every
finding from it and from the earlier review fixed in pushed commits; re-triggered after the last push
and refused at 13:10:29Z; every other gate condition green on the current head `e1b94faf4`
(CI success 13:33Z, local `verify` 130156, Sonar `merge_allowed: true`).

## Operator questions

none asked. No blocker, no rule bend, and no required reviewer was unobtainable under the quota
policy. Free-text operator messages: the restart notice instructing me to continue from where I left
off (no permission content acted on).

## Rule check

Two shell file operations I issued and one sub-agent line the guard logged:

- I ran `sed -n '1,40p' .plan/execute-script.py` once while locating the executor's
  `MARSHALL_VERSION` (it failed: the worktree's `.plan` carries no executor). Shell file read — not
  kept.
- I ran `ls -la .plan` once in the worktree to confirm the executor is absent. Shell file listing —
  not kept.
- Guard line for this run's sessions:
  `2026-10-23T07:13:23.264Z | tool=shell | rule=R1 | session=ses_e98677197ffe4V4p6hVBRC3wcS | call=call_02_okxtdbG42lFwC19kOP4n7136 | git -C ... log --format=%H%x09%s%x09%(trailers:key=Co-Authored-By,valueonly) origin/main..HEAD`
  — the self-review sub-agent's command; its rule breaks count as the run's.
- No guard refusal blocked a step; every refused-looking command was executed by the harness. No
  other section 1 rule was broken: every script went through the executor, every build through the
  resolved build commands, every CI action through `ci`, one command per call elsewhere, all repository
  edits inside the worktree, and `.plan/` writes limited to `.plan/temp/`, the `ci` body slots and the
  inbox message.

**Restarts:** one server restart at 2026-10-23T12:06Z killed the post-merge `verify`; the lane text was
re-read, the progress file reread, and the same `verify` was re-run (114738). Killed sub-agents or
re-dispatches: none (the three self-review rounds all completed).

## Build server

- Setup preflight: `ready` (project registered, daemon reachable).
- Every build ran `in_process` with `executor_absent_from_worktree`: the worktree's `.plan` carries no
  `execute-script.py`, so `build-routing`'s verdict (and the pre-D4 fallback mode used for the whole
  run) was in-process. No `degraded` result and no `killed` job.
- One learned-bound expiry: `module-tests` returned `timeout` at 556 s (`timeout_source: learned`) at
  080101; the run continued with the split form and then re-ran `verify`/`module-tests` with
  `--timeout 1283`, green.
- `runtime_stamp_reason`: none at landing — the stamp is complete
  (`harness=opencode`, `model=deepseek-v4.1-flash/high`, `effort=high`, `plugin_version=0.1`,
  `executor_version=0.1.1989`).

## Residue

- `executor-skew` answers `could_not_check` on flat, unversioned installs (OpenCode/Antigravity): the
  lane-text version cannot be derived there. This is the spec's own could-not-check arm; the lane
  reports it and asks the operator rather than reading it as no skew.
- The new verbs (`executor-skew`, `build-routing`) are not in any deployed executor's surface cache
  yet: invoking `executor-skew` through the current main-checkout executor still answers
  `unknown_verb` until the executor is regenerated. The lane text now classifies exactly that as skew
  evidence; no source change was made to silence it.
- Accepted low-severity review residue: the summary-review predicate is test-local rather than read
  from §7; §8 restates §1's grading (the criterion binds §3/§6); the probed-layout negative substring
  is broad; `_VERSION_DIR_RE` no longer exists in the lane (removed), but `version_key`'s grammar
  remains `plugin_registry`'s; a valid-but-stale `_project.json` index can still end in
  `build_command_unresolvable` (a stale index, not a missing architecture).
- A defence-in-depth executor check in `_build_execute_factory._route_to_daemon` was implemented and
  reverted: it broke 29 build-server unit tests by changing shared routing semantics, outside the
  spec's sanctioned "lane checks before the first routed build" decision. The lane-level check plus
  the composition test is what shipped.
