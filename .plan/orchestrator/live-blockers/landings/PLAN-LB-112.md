# Landing Analysis: PLAN-LB-112 — a routed build keeps its tree and reports its own faults

epic: live-blockers
workstream: WS-04
pr: #1910

> Landing record for one shipped plan. Lives at `landings/PLAN-LB-112.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Merge commit `7d4182f46af8d2ea4e6ddf1db43c1f46897b6cc0`, read through the `ci` abstraction as `state: merged` on `fix/lb-112-routed-build-worktree-fault-truth`. Landing message `rb-lb-112-routed-build-worktree-fault-truth-001.md` (runbook lane; harness opencode, model `deepseek-v4.1-flash/high`). `landing-check` reports `complete: false`, missing `total_tokens` only (the known gap; the message says `unknown`, which is an unobserved fact and not a zero). The diff touches 10 files, 1256 insertions and 36 deletions: six production files, three test files and one standards bullet.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — reproduce or refute before changing | shipped-modified | Verdict `reproduced`, recorded in the PR body. The reproduction is fixture-level (the build server was down for the whole run, so no routed run existed), which the PR says. The fixture's child log is hand-written and the strict gate is modelled (see L2-1). |
| D2 — the child resolves the tree the routing process resolved | shipped-modified | The carry candidate was chosen (`--resolved-project-dir`), not the sibling-lookup one. It needed `_build_cli.py` and `resolve_project_dir.py`, which the spec marked untouched or did not list. |
| D3 — a pre-tool fault reaches the caller as itself | shipped-as-specified | `PRE_TOOL_FAULT_ERRORS` + `ChildFault` in `_build_result.py` / `_build_server_protocol.py`; re-emit in `_build_shared.py:795-806`. Goes beyond the spec's wording: a JSON-format fallback reader, `queue_saturated`, `invalid_invocation` and `carried_tree_outside_daemon_job` are classified too. |
| D4 — the factory docstring states the invariant that holds | shipped-as-specified | `_build_execute_factory.py:981-988` states the carry; the old sentence survives only in the test that asserts its absence and in the inbox finding that quotes it. |
| not a deliverable | added-unplanned | `_build_cli.py`, `resolve_project_dir.py`, `test_build_cli.py`, the `build-api-reference.md` bullet (all D2), and `_build_server_protocol.py` (D3, 201 lines — not in the lane's drift list, see L2-3). |

## Three-Layer Analysis

The landing was read on three layers — the spec, the deliverable trace, and the merged code — by one read-only leaf (`execution-context-level-5`, resolved on `orchestrator.analyze`), and the orchestrator re-read the points recorded as `checked` below at their `file:line` before writing them here. The reading is by reading, no build, no test run, no write. The leaf had no Grep or Glob in its envelope; it worked from Read and read-side git.

- **Dispatch:** one read-only leaf per landing — reason: reading merged code is depth work, and this landing's read must not share context with any other.
- **Verdict:** layer 1 findings (minor); layer 2 findings (minor); layer 3 findings (one major not shown by reading, six minor, three info), no blocker.
- **Orchestrator re-read:** every L3 row, L2-1 to L2-5 and L1-1 to L1-6 below were re-read at the cited lines. One leaf line number was wrong and is corrected here (the flag import is at `_build_execute_factory.py:49`, not `:346`). Points not re-read are named as unverified leads.

### Layer 1 — Specified

| Finding | Claim | Verdict | Evidence (file:line) |
|---------|-------|---------|----------------------|
| L1-1 | D1's branch logic closes D2 to D4 when the routed run reports `worktree_resolution_failed` as itself. That outcome refutes only the reporting hypothesis (D3); the child still cannot resolve the plan, so D2's cause would stand. | checked | `plans/PLAN-LB-112-…md:36-38` |
| L1-2 | The spec lists `_build_cli.py` as adjacent and "left untouched", but D2's first candidate (carry the tree in the re-run command) needs the child's parser to declare a new flag. | checked | `plans/PLAN-LB-112-…md:50-51,157-158` |
| L1-3 | D1 asks for a routed run, but the standing constraint and the Done-when accept a fixture, so D1 can pass with no routed run at all. | checked | `plans/PLAN-LB-112-…md:33-44,100-102` |
| L1-4 | The Objective states the routed failure as fact while the Claim Labels mark the same claims HYPOTHESIS. | checked | `plans/PLAN-LB-112-…md:21-25,125-130` |
| L1-5 | D3's "Both are red at HEAD for the first case" is garbled: the matched control is green at HEAD by design. | checked | `plans/PLAN-LB-112-…md:73-75` |
| L1-6 | The spec did not foresee that the carry is a new flag a pre-change executor surface refuses; no D2 Done-when can catch it. This is the spec-side cause of L3-1. | checked | `plans/PLAN-LB-112-…md:46-60` |
| L1-7 | The OBSERVED line references agree with the pre-image hunks. | not_shown_by_reading | leaf-only; not re-read |

**Layer 1 verdict:** findings — 6 (minor/info). The premise of the plan held: the finding's code facts were true and the fixture reproduces the window.

### Layer 2 — Implemented

| Deliverable | Code trace | Test that can fail | Unexplained file / unborne claim | Verdict |
|-------------|------------|--------------------|---------------------------------|---------|
| D1 | `test_build_execute_routing.py:939-966` | `test_the_routed_result_reaches_the_caller_as_the_child_reported_it` | L2-1: the test requests `moved_back_window` but its body never uses it; the child's log comes from the hand-written `_child_fault_job_log`. The modelled strict gate (fixture near L855-872) was not re-read. | checked |
| D2 | `_build_execute_factory.py:1036-1039`, `_build_cli.py:745-756` | the carry and tripwire tests in `test_build_cli.py` | L2-2: the lane's "met" for D2's "D1 fixture green for a routed build with `--plan-id` after move-back, and the result is the build's own" is read from several separate tests, not one moved-back child run (`test_build_cli.py:409` not re-read; lead). | not_shown_by_reading |
| D3 | `_build_shared.py:795-806`, `_build_server_protocol.py:1292-1304` | `TestPreToolFaultPassThrough` | L2-4: the slot-refusal test pins a log shape no producer emits. L2-5: the "one spelling" test cannot fail. | checked |
| D4 | `_build_execute_factory.py:981-988` | `test_the_old_identical_resolution_claim_is_gone` | none (the pickaxe result that the sentence went in `42b421ff2` and out in `7d4182f46` is the leaf's; not re-run) | checked |

- **L2-3 (unexplained file):** `_build_server_protocol.py` (201 lines changed) is explained by D3 and is named in the PR body's Changes section, but it is absent from the lane message's "Surface drift: none beyond" list (message L127-131) and from the PR's "Surface drift" section. A file the diff touched that the declared drift omits.
- **L2-4:** `test_build_execute_routing.py:1190-1213` writes `reason: max_retries` + `message:` for `queue_saturated`; the producer `_emit_queue_timeout` (`_build_execute_factory.py:1247-1255`) writes `message`, `tool`, `command`, `max_retries`, `plan_id` and no `reason`. The behaviour is right either way (the reader falls back from `reason` to `message`), but the test does not pin the real shape and its docstring mixes up the executor's `invalid_invocation` shape with the queue refusal.
- **L2-5:** `test_build_execute_factory.py:1554-1563` compares `factory._RESOLVED_PROJECT_DIR_FLAG` with the constant it was imported from (`_build_execute_factory.py:49`), so it cannot fail, and its docstring "declared in two modules" is false.
- Red-at-HEAD runs and their log identifiers, the `xfail(strict)` intermediate commit, and the green runs are `not_shown_by_reading`.

**Layer 2 verdict:** findings — 5 (minor/info).

### Layer 3 — Correct

| Defect | File:line | Triggering input | Effect | Severity |
|--------|-----------|------------------|--------|----------|
| L3-1 | `_build_execute_factory.py:1036-1039` (carry), `_build_result.py:290-299` (docstring), `_build_execute_factory.py:1588-1619` (no fallback after a routed result) | The daemon is up and a project's executor was generated before this change: it still matches its script digest, applies its old surface and refuses `--resolved-project-dir` as `unknown_flag`. | The carry is appended to every routed build with a real `--plan-id`, not only those in the move-back window. Every such build is refused (reported as `invalid_invocation`, not as a red build) until the executor is regenerated, with no in-process fallback. The lane discloses the regeneration as owed after merge. Whether a stale executor is in use anywhere was not shown. | major (not shown by reading) |
| L3-2 | `resolve_project_dir.py:294-301`, `_build_server_protocol.py:1302-1304`, `_build_execute_factory.py:824-830` | A routed child's `worktree_resolution_failed` body, which carries its text in `message`. | The routed result carries the text in `reason` and drops `message` (the corrective is empty when it equals the reason). A consumer that reads `message` gets nothing on the routed path; the direct path carries it. | minor |
| L3-3 | `_build_cli.py:752`, `resolve_project_dir.py:331-332`, `_build_format.py:41-58` | A carry outside `MARSHALLD_JOB`. | The refusal goes through the whitelisting formatter, whose field list has neither `resolved_project_dir` nor `plan_id`, so the fields the emitter documents as echoed for diagnosis never reach the output. | minor |
| L3-4 | `_build_server_protocol.py:1275-1284,1300-1304` | A job log with an earlier column-zero `reason:` line, then a pre-tool body that carries only `message:`. | Each key is last-wins across the whole log and `ChildFault` is built without the verdict block in view, so a stale earlier `reason` can take the child's slot and the child's own text is demoted to the corrective. Whether real job logs carry such a line was not shown. | minor |
| L3-5 | `_build_execute_factory.py:833`, `_build_shared.py:758,795` | The daemon reports a job failure with exit code -1 and the log holds a pre-tool body. | `exit_code or 2` passes -1 through and the launch-fault branch runs before the pre-tool branch, so the child's name is lost and the fault reads `execution_failed`. Whether the daemon can produce -1 with such a log was not shown. | minor |
| L3-6 | `_build_queue_slot.py:339`, `_build_execute_factory.py:1668` | In a daemon child, the machine-global build queue cannot be reached. | `acquire` raises `RuntimeError`, not `BuildQueueTimeout`, and `cmd_run` catches only the latter. What the wrapper emits then, and so whether the routed result collapses to `build_failed` plus the synthetic row, was not shown. Not in the lane's residue list. | minor (not shown by reading) |
| L3-7 | `_build_execute_factory.py:1653-1667` | The carried child runs from the worktree cwd where the plan directory is absent. | The child still performs plan-id-keyed work there (queue slot and its liveness, the work log, the build-results path). It may recreate `.plan/local/plans/{id}` in the worktree or fail. No D2 test exercises it. | minor (not shown by reading) |
| L3-8 | `_build_shared.py:748-749,806` | A pre-tool fault. | The function's docstring says it returns 0 or 1; the new branch returns the child's own code (2). | info |
| L3-9 | `_build_execute_factory.py:1595-1603` | A routed pre-tool fault. | A `kind=build` ledger row is still appended with `status=error`, exit 2 and no error class, so a reader of the ledger cannot tell a routing fault from a red build. Fails closed (never green). | info |
| L3-10 | `_build_execute_factory.py:1042-1064` | An argparse-abbreviated `--plan X`, if the executor surface accepts it. | The routing process resolves the plan but appends no carry, so the window fault returns (now reported as itself). Whether the surface accepts an abbreviation was not shown. | info (not shown by reading) |
| L3-11 | `resolve_project_dir.py:304-333` | Any process in a daemon job's tree. | `MARSHALLD_JOB` is an ambient variable a job's descendants inherit, so a hand-written carry there is honoured. The emitter's own docstring says it is "not a credential". | info |

Leaf findings I did not re-read, recorded as unverified leads: `_last_json_object` is O(n²) on unterminated-string input and the "only the failure path pays" docstring is inaccurate (`_build_server_protocol.py:1318-1366`); the JSON guards match the TOON guards; the argv carry is safe because the daemon receives `json.dumps(list)`.

**Layer 3 not shown by reading:** L3-1 (whether a stale executor is in use, and the digest-match mechanism that lets it through), L3-6, L3-7, L3-10 — each needs a run.

**Layer 3 verdict:** findings — 11 (1 major not shown by reading, 6 minor, 4 info); no blocker.

### Conformance to the Project's Own Rules

| Rule source | Rule | Verdict | Evidence |
|-------------|------|---------|----------|
| CLAUDE.md Documentation Standards | Current state only, no transitional information | deviates | `_build_result.py:290-299` ("This branch adds a flag … generated before this change"); `_build_execute_factory.py:986-987` ("the pre-carry behaviour") |
| plugin-script-architecture | TOON output contracts | deviates | `_build_cli.py:752` (L3-3) |
| PLAN-LB-112 Standing Constraints | A routing fault is never a red build | deviates | holds for the five classified names; residual collapses at L3-5, L3-6 and the admitted unstructured argparse rejection (`_build_result.py:297-299`) |
| PLAN-LB-112 Standing Constraints | Leave routing alone; keep the strict `get-worktree-path` gate; fail closed | conforms | `_status_query.py` is not in the diff; `_build_cli.py:750-769` refuses a carry outside a job and returns 2 on a resolution error |
| plugin-script-architecture | Stdlib-only; tests state their purpose | conforms | leaf, not re-read |
| plugin-script-architecture | Tests use the `PLAN_MARSHALL_HOME` fixture; no reads of real `~/.plan-marshall` | not_shown_by_reading | leaf: isolation rests on suite-level conftest |
| PLAN-LB-112 Standing Constraints | New tests shown red at HEAD where the Done-when says so | not_shown_by_reading | only the lane's log identifiers exist |
| CLAUDE.md Commit Trailer | Assistant commits end with the plan-marshall trailer | conforms | leaf: `7d4182f46` ends with it |

## Metrics and Anomalies

- Tokens: `unknown` (the harness measured none; recorded as an unobserved fact, not a zero). Token work is out of scope.
- Duration: not recorded in the message.
- Anomalies: five self-review rounds (rounds 4 and 5 past the lane's three-round limit, operator-authorised); one whole-tree `module-tests` bound expiry at 1643 s, re-run green on a raised bound; two environment flakes, both green in isolation; zero routed builds (the build server was unreachable for the whole run, so every build was an in-process fallback and the daemon side was never run).

## Routing and Merge Behavior

- Review: CodeRabbit (required, quota-limited) reviewed `eada532bf` and `1cb7b8bb1`; every finding was fixed or answered. The last push `d014fd73c` was refused on quota, so the standing review authorisation applies and is not a question. Sourcery refused on its own budget (optional).
- CI/merge: `state: merged`, merge commit `7d4182f46`. The lane reports CI green on the final head.
- Sonar: not enabled for this project; `n/a` and ignored.

## Reconciliation Actions

- [ ] row `status` → `shipped` — `orchestrator queue --transition PLAN-LB-112 --status shipped`
- [ ] row `pr` stamped — `orchestrator queue --set-row PLAN-LB-112 --field pr --value 1910`
- [ ] row `landing` stamped — `orchestrator queue --set-row PLAN-LB-112 --field landing --value landings/PLAN-LB-112.md`
- [ ] row `plan_marshall_plan_id` stamped — `orchestrator queue --set-row PLAN-LB-112 --field plan_marshall_plan_id --value lb-112-routed-build-worktree-fault-truth`
- [ ] epic.md narrative reconciled (queue annotation with the layer summaries; Open Defect for the incomplete landing message; Watch for the owed executor regeneration)
- [ ] resume anchor updated in `resume_anchor.md`
- [ ] `queue-view.md` regenerated

## Follow-Ups

- **Layer-3 findings L3-1 to L3-7 are reported to the operator and not fixed.** A fix plan is staged only on the operator's word. L3-1 is partly an operator action (regenerate the executor), which the lane owes as post-merge.
- **PLAN-LB-108 (staged, overlaps this plan on `_build_execute_factory.py` and `test_build_execute_routing.py`)** must re-read the function and line references of `_route_to_daemon` at its outline, since this landing moved them. Recorded as a Queue annotation on that row.
- **Post-merge, owed:** regenerate the executor in every project before a routed plan build can use the carry; a live routed check in the move-back window.
