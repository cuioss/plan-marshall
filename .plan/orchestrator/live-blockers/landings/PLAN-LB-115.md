# Landing Analysis: PLAN-LB-115 — The routed-build carry cannot refuse a build outside the move-back window, and the routed fault reports what the child said

epic: live-blockers
workstream: WS-04
pr: #1932 (https://github.com/cuioss/plan-marshall/pull/1932)

> Landing record for one shipped plan. Written by the `analyze` verb after verifying claims against ground truth.
> Merge commit `3839835ccf560f67ec743e27ea71859db7cd6bfd`, a merge-queue squash with ONE parent `420415c7c22081c7804a0c3221d1dd8da8b73793`
> (the Dependabot mypy merge, PR 1926), read with git before the leaf prompt named it. `ci pr view` reports `state: merged` with that
> merge commit. Lane: runbook, harness `opencode`, model `deepseek-v4.1-flash/high`, `total_tokens` unknown. The inbox message is
> `complete: false`, `missing_keys: total_tokens` (out of scope per the focus rule). The lane's review history, CI and merge-queue
> claims were not re-read; the merge state and merge commit were.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 a stale executor cannot turn a routed plan build outside the window into a refusal | shipped-as-specified | `_carry_resolved_tree` appends the carry only when `_child_resolves_plan_itself` is false (`_build_execute_factory.py:1167-1173`, predicate `1176-1220`, `realpath` on both sides); plan id, mutual exclusion and the unresolvable-tree error unchanged; `TestStaleExecutorCarry` pins both windows |
| D2 a routed fault reports what the child said | shipped-as-specified | `ChildFault.message` replaces `corrective` (no reader of the old name remains); formatter whitelist carries `resolved_project_dir` and `plan_id` (`_build_format.py:46-47`); per-block reader (`_build_server_protocol.py:1283-1337`); `BuildQueueUnavailable` / `DirectoryLockUnavailable` raised at `_build_queue_slot.py:385,425,619` and caught in `cmd_run` (`_build_execute_factory.py:1942-1949`) |
| D3 tests say what they test, comments state current behaviour | shipped-modified | the named transitional phrases are gone; four deliverable or past-state labels remain in touched modules (L3-5); one renamed test cannot tell per-block from last-value reading (L2-2) |
| D4 the routed-result mapping is decided and pinned | shipped-as-specified | docstring now matches `_RESULT_STATUS_TO_WIRE` (`_build_server_protocol.py:200-207`); timeout and killed fixtures send the rows the supervisor sends; no mapping code changed |

## Three-Layer Analysis

Read by one read-only leaf (`execution-context-level-5`, the resolved `orchestrator.analyze` level). One leaf per landing, as the dispatch rule requires; reading merged code is the depth the rule exists for. The orchestrator re-read the points marked "re-read" below at their `file:line`; points not listed there are unverified leads.

- **Dispatch:** one read-only leaf per landing — reason: reading the merged routed-build code is the depth the Dispatch Decision Rule exists for, and the other two landings of this drain each got their own leaf.
- **Verdict:** layer 1 clean; layer 2 findings (2, minor); layer 3 findings (minor and info only). No blocker and no major.

### Layer 1 — Specified

The premises hold: before the landing the carry was appended to every argv naming a real plan, and the spec's closed `--plan-id` abbreviation bullet needed no change (`allow_abbrev=False`, `_build_cli.py:208`). One spec wording is looser than what is possible: D2 asks for the diagnostic fields to reach "the TOON and the JSON path", but the carried-tree refusal has no JSON rendering (`_build_cli.py:754`, re-read: `format_toon` is the only route). The "either the whitelist or another path" alternative the spec allows is met by the whitelist.

| Finding | Claim | Verdict | Polarity | Evidence |
|---------|-------|---------|----------|----------|
| L1-1 | the carry was unconditional before | checked | confirms | `_build_execute_factory.py:1168-1173` (re-read) |
| L1-2 | spec D2 "both TOON and JSON" has no JSON route for this refusal | checked | refutes | `_build_cli.py:754`, `_build_format.py:88-93` (re-read) |

**Layer 1 verdict:** clean (L1-2 is a spec wording, not a defect).

### Layer 2 — Implemented

| Deliverable | Code trace | Test that can fail | Unexplained file / unborne claim | Verdict |
|-------------|------------|--------------------|----------------------------------|---------|
| D1 | `_build_execute_factory.py:1167-1220` | `TestStaleExecutorCarry`, the carry-only-when-needed test, `test_a_tree_whose_record_names_another_tree_still_gets_the_carry` | none | checked |
| D2 | `_build_server_protocol.py:1283-1337`, `_build_queue_slot.py:385,425,619`, `_build_format.py:46-47` | `TestPreToolFaultPassThrough`, `TestFactoryCmdRunLimiterFaults` | none | checked |
| D3 | comments in the touched modules | the slot-refusal test, the child-parser argv test | labels remain (L3-5) | checked |
| D4 | docstring `_build_execute_factory.py:703-768` | timeout and killed fixtures | `Returns` overstates two cases (L2-3) | checked |

- **L2-1 (info):** `uv.lock` (+42/-42 lines) is in the squash. The hunk is only the mypy 2.4.0 to 2.4.1 relock plus the `requires-dev` specifier (re-read with `git diff 420415c7c 3839835cc -- uv.lock`). It fixes a real inherited mismatch, because the Dependabot merge before it changed only `pyproject.toml`. No deliverable and no line of the squash message explains it, and the lane's claim of "its own explained `chore(deps)` commit" is a branch-commit claim the squash cannot show. It is the lane's own build churn recorded honestly in the message, so no drift in behaviour.
- **L2-2 (minor):** the renamed `test_the_bound_is_read_from_the_block_that_holds_the_verdict` cannot fail on what its name says. The verdict block's `330` / `learned` are also the last values in the file, so a last-wins reader passes it (`test_build_server_protocol.py:913-928`, re-read). Per-block reading is pinned elsewhere (`test_a_key_from_another_block_cannot_supply_the_verdict`).
- **L2-3 (minor):** `test_outside_the_window_a_stale_executor_runs_the_build` models the stale executor only as a check on the submitted argv (`test_build_execute_routing.py:1357`, re-read); its success comes from the scripted fake wait. Only the "no carry appended" half of "runs and returns the build's own result" can fail.
- **L2-4 (minor):** the new `Returns` rule says a killed result carries "the bound that fired" and an unrecognised job status carries "the producer's own message"; the code carries the bound that applied and this client's own sentence (`_build_execute_factory.py:758-767`, `864-873`; the first re-read, the second unverified).
- **Surface:** `test/plan-marshall/script-shared/test_build_cli.py` is declared and untouched; its tests went into `test_build_execute_routing.py`. `test_build_server_protocol.py` is outside the declared surface (D2 and D3 explain it); `uv.lock` as above. `resolve_project_dir.py` and `build-api-reference.md`, both hypothesis entries, carry a one-line doc change each.

**Layer 2 verdict:** findings — 3 minor, 1 info.

### Layer 3 — Correct

| Defect | File:line | Triggering input | Effect | Severity |
|--------|-----------|------------------|--------|----------|
| L3-1 | `_build_execute_factory.py:1171,1204` (re-read) | a job still queued when the 300 s hand-back returns, started after `integrate_into_main` moved the plan record back | the predicate was evaluated at submit time, so the child runs without the carry and refuses with `worktree_resolution_failed` (exit 2); fails closed and is reported as itself | minor |
| L3-2 | `_build_execute_factory.py:1204-1209` (re-read) | a tree whose plan record sits under a parent `.plan/local`, or a relative persisted path | the predicate reads only `{tree}/.plan/local/plans/{id}/status.json`; every mismatch and every read error appends the carry (the fail-safe direction), so a stale executor can still be refused where the child could have resolved the plan itself | info |
| L3-3 | `_build_queue_slot.py:385,425` (re-read) | an error result with no `error` key | `str(result.get('error'))` writes the text `None` into the fault message | info |
| L3-4 | `_build_shared.py:817` | the carried-tree refusal through a routed hop | `ChildFault` keeps only error, reason and message, so `resolved_project_dir` and `plan_id` do not survive the hop; reachable only when a daemon that does not stamp `MARSHALLD_JOB` runs a current child | info |
| L3-5 | `_build_execute_factory.py:472,1619`, `_build_shared.py:475`, `_build_format.py:196` (re-read) | the documentation standard | labels that point at deliverables or past state remain ("D5", "deliverable 9", "pre-existing requirement"); `_build_format.py:200` also ends a comment with an unmatched `)` | minor |

**Layer 3 not shown by reading:** whether an executor generated before the flag really refuses `--resolved-project-dir` as `invalid_invocation` / `unknown_flag` and not as a bare argparse error with no TOON; the tests model it with `_stale_executor_refusal`. Whether the limiter-fault tests read the live `marshal.json` through `_resolve_max_retries` was not read.

**Layer 3 verdict:** findings — 2 minor, 3 info; no blocker, no major.

### Conformance to the Project's Own Rules

| Rule source | Rule | Verdict | Evidence |
|-------------|------|---------|----------|
| CLAUDE.md § Documentation Standards | current state only | deviates | labels at `_build_execute_factory.py:472,1619`, `_build_shared.py:475`, `_build_format.py:196` |
| CLAUDE.md § Script Execution | scripts run via the executor | conforms | routed child command is the executor plus notation |
| spec standing constraints | routing, strict gate, marker gate, adjacent surfaces untouched, a routing fault is never a red build | conforms | `_build_cli.py:752-755` unchanged; `_append_gate_build_row` absent from the diff |
| CLAUDE.md § tests use the isolated home | limiter-fault tests | not_shown_by_reading | see above |

## Metrics and Anomalies

- Tokens: `unknown` (not measured; out of scope per the focus rule).
- Anomalies: five CodeRabbit quota refusals from 13:02Z to 22:01Z, each followed by a full 90-minute wait; self-review `budget-exhausted` (3 rounds plus one operator-authorised confirmation round; the last three test-comment fixes were verified by reading); two whole-tree runs red, one on an environment race (eight xdist workers racing the one-shot target-tree generation) and one on a real regression the scoped runs missed, fixed in `0662039ff`.

## Routing and Merge Behavior

- Review: CodeRabbit (required, quota-limited) reviewed and re-reviewed; four findings, all fixed and answered, final review "no actionable comments" on the merged head `1e485c7b9` (lane's claim, not re-read). Sourcery (optional) refused on its own budget.
- CI/merge: merge queue, merge-group run `42430506005` success (lane's claim); the merge state and commit were re-read.
- Sonar: `n/a` (Sonar is not enabled for this project).

## Reconciliation Actions

- [x] row `status` → `shipped`
- [x] row `pr` stamped `1932`
- [x] row `landing` stamped `landings/PLAN-LB-115.md`
- [x] row `plan_marshall_plan_id` stamped `rb-lb-115-routed-build-carry-and-fault-corrections`
- [x] epic.md narrative reconciled (the mid-flight note replaced by this landing's entry)
- [x] `queue-view.md` regenerated

## Follow-Ups

- Layer-3 minors L3-1 and L3-5 and the layer-2 minors: recorded as one Watch in epic.md; not staged (no major, and the focus rule's stop rule does not warrant a fix plan). The comment labels ride the next plan that touches `_build_execute_factory.py`.
- Owed outside the plan, operator-run: the executor regeneration in every project and a live routed check in the move-back window; the harness sync (the merge touched bundle files). A reconcile of the build daemon is owed for the routed child to run the merged code.
