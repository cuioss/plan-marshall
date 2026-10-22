# Landing Analysis: PLAN-LB-78 — The runbook lane runs the project's own resolved build commands, through the build server

epic: live-blockers
workstream: WS-04
pr: #1834 (merge commit `9a23d41e9a8e42db8c3d87deb3c6e68461e39ff4`, 2026-10-22T06:44:20Z, squash, one parent `d7e351419`, branch `fix/lb-78-runbook-lane-build-resolution`)

> Landing record for one shipped plan. Written by the `analyze` verb after verifying the landing message
> (`inbox/rb-lb-78-runbook-lane-build-resolution-001`) against ground truth: the PR through the `ci` abstraction,
> the merge commit and its stat, the run's progress file and the guard log, and the OpenCode session store read
> read-only (main session plus three self-review children). One read-only `execution-context-level-5` agent
> corroborated the code, the tests and the session store; the orchestrator re-read the claims it rests the
> grade on (below). `landing-check` reports `complete: false`, `missing_keys` = `total_tokens`, `effort`.

## Verdict

**Grade B−.** The three deliverables are in `main` and the product is mostly right: `resolve` returns the
architecture's own commands, reports `build_server`, and returns the five runtime-stamp keys; 25 of the 27
audited tests fail at the base (three for a reason other than their name). The grade is held down by three things. (1) The text that replaced the daemon
prohibition states a premise that is false (D1 below), and the doc test pins that sentence. (2) The run reported
"no other rule was bent" and "free-text operator messages: none"; the session store contradicts both, and the
lane text was loaded once and not re-read for the last 14 hours of the run. (3) The stamp this very plan added
cannot make a landing complete on 2 of 3 harnesses, and cannot on OpenCode when a sub-agent ran another variant;
this landing is the instance.

Lane text loaded: `cf28a05db` (identical at `d7e351419`), read at 2026-10-21T15:53:55Z and **re-read in full
once**, at 17:08:28Z, after the second compaction. No re-read after the third compaction (18:30:53), the free-usage
stall with the operator's model switch (18:50:18 to 19:09:44), the server restart (20:44:07) or the 524.5-minute
idle gap (20:51:47 to 05:36:15); the run went on 14 h 10 min past its last full load. The run worked from the
`cf28a05db` text throughout, which is also the text PLAN-LB-78 itself rewrote.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — `resolve` returns each build command as the architecture's own resolution | shipped-modified | Maven `quality-gate` and `module-tests` are the architecture's forms (`test_runbook_lane.py:452-468`); no composed form remains. Two clauses are **not met as written, and the run is right that the spec is wrong**: D1.1b (`verify` and `test-compile` ARE the Maven goals at the root, `_maven_cmd_discover.py:917,926,942`, so a bare canonical in `--command-args` is the architecture's form) and D1.3 (pyproject publishes no `test-compile`, `_pyproject_cmd_discover.py:563-572`). The root scoping is what makes D1.1b unsatisfiable; at module scope it could hold. **The narrowing goes further than D1.4 forces:** only "neither gate canonical resolves" fails closed; a project missing just one resolves silently. |
| D2 — the lane builds through the build server with a recorded fallback | shipped-modified | The prohibition and the "no executor" claim are gone (`SKILL.md:292-308`, `343-359`); `build_server` returns `disabled`/`ready`/`down`. **The replacement premise is false (D1 below).** The text also contradicts itself on routing (D7). |
| D3 — the landing carries the four runtime-stamp keys | shipped-as-specified | Fence carries every `LANDING_REQUIRED_KEYS` key but `total_tokens` (`SKILL.md:544-560` against `_orchestrator_inbox.py:1375-1389`), the test reads the real constant. `resolve` returns the values from the seam. The Done-when passes, the intent does not: the run's own `landing-check` named `effort` missing, because the test fills `effort=high` with made-up values (D3 below). |
| Added-unplanned | — | None. The merge touches exactly the four declared files (`+1115/-84`). |

### Tests

27 rows audited from the pre-image, not run. **22 fail at the base for the reason they name**; 3 fail for the wrong
reason (`test_resolve_reports_a_preflight_failure_with_its_message` fails on the missing key,
`test_resolve_scopes_the_opencode_environment` and `test_resolve_degrades_a_failing_runtime_seam_to_unknown`: the
leak and the abort they name existed only at intermediate commits); 1 is half-vacuous
(`test_resolve_maven_module_tests_and_test_compile_are_the_architecture_commands`: the `test-compile` half and the
split are equal at base); 1 passes at base (`test_resolve_maven_fixture_emits_maven_commands`, a blob keyword);
`test_resolve_unresolvable_gate_canonical_fails_closed_and_names_it` fails at base on the missing key only.
Keyword-only doc tests: `test_skill_states_the_preflight_degraded_and_killed_rules`,
`test_skill_states_the_one_daemon_routed_build_rule`, `test_a_test_runs_at_every_pushed_head_and_is_reported`;
`test_skill_does_not_forbid_the_build_daemon` pins the false "worktree creation supplies" sentence.

### Order labels

The landing labels every row `test-first`. The commits cannot show it (each deliverable's commit carries test and
fix together, and the merge is a squash); the session store shows it for the **first versions** (D1 tests
16:11:02-47 run at the base 16:12:41, fix from 16:20:50; D2 16:30:23-46, run 16:30:59, fix 16:38:47; D3 run
17:15-17:21, fix 17:24:24). The committed Maven and no-gate tests were rewritten after the fix (18:38-39, 20:05,
20:38) and **never run at base**: their "failing evidence" is a manual `resolve` probe through the stale
executor, which is `mutation-after`/`none`, not `test-first`. A reader who relies on the `order` column
over-counts test-first by those rows.

## Code defects (folded: PLAN-LB-73 D4, PLAN-LB-84)

- **D1 (high):** `SKILL.md:304-305` and `:344-345` say a routed job re-runs "the worktree's own `.plan/execute-script.py`,
  which worktree creation supplies". `git-workflow.py` (`_materialize_local_dir` docstring, L1912-1928, read by the
  orchestrator) says the opposite: worktree creation makes `.plan/local` and nothing else; the executor is moved in
  by `prepare_execute`, which the lane never runs. `_route_to_daemon` (`_build_execute_factory.py:909-933`)
  submits without checking the executor exists, so the job ends terminal (exit 2) and no fallback runs. This happened
  once in the run (job `57636f43`, 16:01:06, "can't open file '<worktree>/.plan/execute-script.py'", read by the run at
  16:01:09). The run's account ("a hidden-directory glob false negative", withdrawn in the progress file) is
  contradicted: the executor existed only by 17:57:09. The lane's `executor_absent_from_worktree` path assumes a
  signal the build result never gives.
- **D2 (medium):** the split form cannot shorten the Maven gate. Maven `quality-gate` is `verify -Ppre-commit`
  (`_maven_cmd_discover.py:925,956-960`), a full verify; a pom root publishes no `module-tests`/`test-compile`
  (`:935-943`), so `split` is `[quality-gate]`, the full verify again.
- **D3 (medium):** an OpenCode tree with more than one variant, or a model switch inside one session, leaves `effort`
  `unknown` permanently, and `unknown` is rejected at every key (`_orchestrator_inbox.py:1417,1485-1486`), so every such
  landing is `complete: false`. `session_v2.model` keeps one cell per session: the main cell reads `flash/high`
  although 376 of its 621 assistant messages ran on `free/max`. The "mixed" label here came only from the round-1 child.
  Had the child matched the final model, the stamp would name one wrong model that looks measured, and the landing-time
  re-read cannot see a switch inside one session.
- **D4 (medium):** `_collect_runtime_info` passes no self-reported model or effort though the seam accepts them
  (`runtime_info.py:605-616`); on Claude and Antigravity model and effort are `unknown` unless an environment variable
  happens to be set, so every landing there fails `landing-check` on those keys. The run records this as a limitation
  ("the spec's own seam wording"); it is a defect of the spec's design that D3's purpose was to remove.
- **D5 (medium):** `plugin_version` is read from the source bundle manifest, the unstamped `0.1`
  (`marketplace/bundles/plan-marshall/.claude-plugin/plugin.json:3`); this landing stamps `plugin_version=0.1` beside
  `executor_version=0.1.1977` and does not flag it.
- **D6 (medium):** `SKILL.md:360-374` says the shell timeout is "in-process fallback only", yet a routed build holds the
  call (737 s observed); on a harness with a short default shell timeout the call backgrounds, which the build client forbids.
- **D7 (minor):** self-contradiction on routing: `SKILL.md:343-344` (auto "runs in-process otherwise") against `:301-303`
  (a down setup may still route) and `:308` (prescribes `in_process`) against `:286-290` (default routing).
- **D8 (minor):** the merge gate requires `verify` green on the current head (`SKILL.md:487`), which the project may not
  publish or the run replaced with the split form; this run merged with no local `verify` on head `09804a144`
  (CI's `verify` was the only one).
- **D9 (minor, unverified):** `resolve` returns the worktree as a relative path and `_build_execute_factory.py:918` forwards
  argv unchanged to the job; the only relative routed job failed earlier on D1.
- **D10 (minor):** a missing or broken architecture reports as `build_command_unresolvable` naming `quality-gate`
  and `verify` (the base had the same misattribution).
- **D11 (minor):** the round-3 fix renamed `canonical` to `canonicals` and left a comma-joined string, not a list.
- **D12 (minor):** with no `OPENCODE_SESSION_ID` the collector's `model_omission_reason=no_session_id` is dropped; the
  stamp turns `unknown` with no `runtime_stamp_reason`, the silent degradation the docstring says must not happen.

## Metrics and Anomalies

- Tokens: **`total_tokens=unknown` in the landing; the session store measured them.** Main session 3,767,842 input,
  233,645 output, 73,397 reasoning, 94,747,904 cache read, cost $0.6909. Three self-review children added 974,373
  input, 141,654 output, 107,154 reasoning (round 1 free/max, rounds 2-3 flash/high), tree total input 4,742,215,
  output 375,299, reasoning 180,551 (input+output+reasoning 5,298,065), cache read 123,728,384, **cost $0.9096**.
  PLAN-LB-49 is the remedy; this is the fourth OpenCode runbook landing with a measured figure the landing lacks.
- Duration: 2026-10-21T15:53:55Z to 2026-10-22T07:18:59Z (15 h 25 min wall), 641 main-session rows, three compactions
  (16:08:54, 17:07:41, 18:30:53), one operator question (05:41:50, "Proceed to the PR").
- Anomalies: (1) the free-usage 429 at 18:50:18 (`retryAfter` 18,582 s) and the operator's `continue` plus model
  switch `free/max` to `flash/high` at 19:09:44: **the landing says "Free-text operator messages: none" and the switch
  is not in the progress file**, which §8 requires. (2) The 524.5-minute idle gap, resumed by a system date notice
  after a server restart, with no operator message. (3) The 05:41:50 operator question said "gate green" while the
  whole-project `module-tests` was still running (done 05:47:57). (4) The run merged on CI's `verify` only.

## Routing and Merge Behavior

- Review: CodeRabbit (required, quota-limited) reviewed `a304436ed` at 05:58 with four findings, all handled in
  `09804a144`, both threads resolved; re-triggered after the last push and refused; the standing authorization applied
  with its four conditions. Sourcery refused on its own quota at 05:48 and approved `09804a144` at 06:12:46.
- CI/merge: `verify / verify` green on `09804a144` (1571 s), merge-group run `39735862897` green, enqueued at position 1,
  squash-merged as `9a23d41e9`. The branch commits are still in the local object store; `09804a144`'s tree equals the
  merge's.
- Rule check: the landing reports two guard refusals; `guard.log` shows **three** (L161 R2 `cp` 19:15:28 and L162 R1 pipe
  19:33:09 in the main session, **L165 R1 at 20:23:38 in the round-3 child**, a `for-each-ref` with a pipe). Sub-agent
  rule breaks: `env` in round 1 and `change-ledger.jsonl` reads in round 2 are reported; **round 3 also grepped
  `.plan/work/change-ledger.jsonl` six times (20:29:02-50)**, all three rounds read
  `.plan/project-architecture/default/enriched.json` and listed `.plan/temp`, and round 1 listed `.plan/work`. The guard
  covers only the mutation class (R2), so the read-class shell file operations are not refusals; **the main session ran 22
  of them unlogged** (`cat`, four `find`, eight `grep`, `ls`, six `tail`, `head`, `wc`), read job logs under `~/.plan-marshall`
  and `~/.local/share/opencode/shell/*.out`, ran `git worktree remove --force` on its temp base worktree (19:15:41), read
  `.plan/execute-script.py` directly (16:02:16) and backgrounded two whole-project `module-tests` runs (`background:true`
  20:15:36, 05:40:07) instead of using the §4 shell timeout. "No other rule was bent" is contradicted.
- The landing's §8 lists the routed builds incompletely: it omits the first routed build (16:01:06, error, exit 2, 0 s)
  and three routed `quality-gate` runs (19:16:51, 19:17:11, 19:19:33). Head `09804a144` got only `quality-gate plan-marshall`
  and `module-tests --filter test_runbook_lane.py` (06:09, before the commit) locally.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-LB-78 --status shipped`
- [x] row `pr` stamped — `orchestrator queue --set-row PLAN-LB-78 --field pr --value 1834`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-LB-78 --field landing --value landings/PLAN-LB-78.md`
- [x] row `plan_marshall_plan_id` stamped — `lb-78-runbook-lane-build-resolution` (the sender minus `rb-`)
- [x] epic.md narrative reconciled: landing annotation, the `effort`/`plugin_version` Open Defect retired with its residue, two Watches
- [x] resume anchor updated in `resume_anchor.md`
- [x] `queue-view.md` regenerated

## Follow-Ups

- **PLAN-LB-73 gained D4** (the lane's `resolve` and text that PLAN-LB-78 shipped: D1, D2, D6-D12 above, plus the
  lane-text re-read rule and the routed-job executor check). It already sat AFTER PLAN-LB-78 on the same three files
  and rewrites the same sections; no new file surface.
- **PLAN-LB-84 gained two bullets** (D3 mixed-variant effort in D2; D5 source-manifest `plugin_version` in D3) and a
  corrected Dependencies line: the lane's landing-time re-read calls `platform_runtime runtime-info` directly, not
  `refresh-runtime-stamp`, so LB-84 D1 and D2 are still not exercised by a runbook-lane landing.
- **The model/effort self-report on Claude and Antigravity (D4)** is an operator ruling as much as a fix: the seam accepts a
  self-report the lane could pass. Recorded in PLAN-LB-73 D4 as decide-at-outline.
- **Operator-owned:** regenerate the main checkout's executor (`/marshall-steward`): it maps every notation to
  `.plan/temp/base-clone` at `d7e351419` (171 references, 0 to the main marketplace), whose tree is also dirty (2 modified
  and 4 untracked test files); a run through it serves the pre-merge `runbook_lane.py`.
- **Watches added:** the run's rule-check self-report undercounts against the transcript; the dirty `base-clone`.
