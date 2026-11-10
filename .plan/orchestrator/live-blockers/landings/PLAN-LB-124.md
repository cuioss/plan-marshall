# Landing Analysis: PLAN-LB-124 — The push gate and the Maven guard stop passing or blocking wrongly

epic: live-blockers
workstream: WS-01
pr: #1938 (https://github.com/cuioss/plan-marshall/pull/1938)

> Landing record for one shipped plan. Written by the `analyze` verb after verifying claims against ground truth.
> Merge commit `19da7ed840c22aa37c1bdf69b9210754e0b2f1e7`, a merge-queue squash with ONE parent `3839835ccf560f67ec743e27ea71859db7cd6bfd`
> (the PLAN-LB-115 merge), read with git before the leaf prompt named it. `ci pr view` reports `state: merged` with that merge commit.
> Lane: runbook, harness `opencode`, model `deepseek-v4.1-flash/high`, `total_tokens` unknown. The inbox message is `complete: false`,
> `missing_keys: total_tokens` (out of scope per the focus rule). The lane's review history, CI and merge-queue claims were not re-read.
> The plan carried eight deliverables on the operator's word (above the six-deliverable guard; split order D8, D7, D6 recorded in the spec).

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 scope judged before the canonical | shipped-modified | `_row_refusal` answers scope first (`_freshness_crosscheck.py:802-809`), the measured-zero check stays last (`:812`); the Done-when cases are delivered, but the reorder also changes the verdict for multi-token payloads (L3-1) |
| D2 trailing executor flag read, remedy that works | shipped-modified | `build_record` gains `command_args`, the executor template records it from argv, `_row_payload_tokens` prefers it (`:608-636`); delivered, with the gaps L3-3 and L3-4 |
| D3 zero-test guard: collected nothing vs summary not visible | shipped-modified | report files read, anchored markers, both gates name the route; two gaps (L3-2, L3-6) |
| D4 module outside the root's reactor gets a command that runs, or none | shipped-as-specified | empty command map for an out-of-reactor module; the resolve seam refuses before enrichment (`_cmd_client_query.py:932-936`) |
| D5 unreadable POM is a named stop | shipped-modified | discovery carries `pom_error` and grants no canonical; the "gate record names it" half is a document obligation plus a doc-text test only (L3-7) |
| D6 guard false negatives and reactor under-grants | shipped-modified | marker line-anchored, fully-qualified goal, `-Dit.test`, `<subprojects>`, `pom.xml` entries; the exit-0 Failsafe miss under `verify` is still undetected when any unit test ran (L3-8) |
| D7 refusal hints and bounded probe | shipped-as-specified | `--waive-refire` named (`pre_merge_gate.py:591-592`), probe at the first non-cleared record (`:552-553`), `record_merge` checks keys; one gap (L3-9); one unrequested refusal (`upstream_count_without_action`) |
| D8 documentation items | shipped-as-specified | direct reads per the PR; history wording remains in four places (L3-10) |

## Three-Layer Analysis

Read by one read-only leaf (`execution-context-level-5`). The orchestrator re-read the points marked "re-read"; the rest are unverified leads.

- **Dispatch:** one read-only leaf per landing — reason: reading the merged push-gate and Maven-guard code is the depth the Dispatch Decision Rule exists for.
- **Verdict:** layer 1 findings (info); layer 2 findings; layer 3 findings — **one major (L3-1)**.

### Layer 1 — Specified

| Finding | Claim | Verdict | Polarity | Evidence |
|---------|-------|---------|----------|----------|
| L1-1 | spec D1's premise "a readable scope decides first" assumes the tokens after the canonical are scope; that holds for pyproject only. For Maven chains, npm `run X` and Gradle task lists they are goals, and the Done-when has no control for a multi-token payload | checked | refutes | `_freshness_crosscheck.py:683-731` (re-read: first non-flag is the canonical, the remaining non-flags are scope); `_npm_cmd_discover.py:350-381` (re-read) |
| L1-2 | spec D4's Done-when ("a command that runs, or none") does not force declining Maven 4 implicit child discovery; the lane's reason for declining CodeRabbit's major is overstated; the decline is an under-grant and fails closed | checked | confirms | `_maven_cmd_discover.py:317-321` (not re-read) |

**Layer 1 verdict:** findings — 1 (L1-1 is the spec gap that produces L3-1).

### Layer 2 — Implemented

| Deliverable | Code trace | Test that can fail | Unexplained file / unborne claim | Verdict |
|-------------|------------|--------------------|----------------------------------|---------|
| D1 | `_freshness_crosscheck.py:802-814` | the four D1 tests of the PR | the npm row is modelled as `test --workspace=pkg-a`; the real discoverer emits `run test --workspace=pkg-a` | checked |
| D2 | `_freshness_crosscheck.py:608-636`, template, `_ledger_core.py` | `test_a_row_recording_the_command_payload_certifies_a_whole_tree_change` and the writer test | none | checked |
| D3 | `_maven_execute.py:512-526,584-608` | stale / zero / no-dir controls | no control for a selector run that carries the `No tests to run.` line (L3-2) | checked |
| D6 | `_maven_execute.py`, `_maven_cmd_parse.py`, `_maven_cmd_discover.py` | per-case fixtures | `test_a_named_failsafe_miss_on_a_verify_run_is_not_a_green` drives a `status=error` run that the earlier guard already handled; it likely cannot fail against the old code and does not cover the exit-0 miss | not_shown_by_reading |

- **Surface:** undeclared files the lane did not name: `test/plan-marshall/manage-tasks/_freshness_notation_crosscheck_fixtures.py`, `test_generate_executor_behavior.py` (the declared hypothesis was `test_generate_executor.py`) and the fixtures `maven-no-test-class.log` and `maven-quiet-green-no-summary.log`. The lane named `_cmd_client_query.py`, `_maven_cmd_parse.py`, `test_narrow_unit_doc_contract.py` and the D7 tests in `test_lb55_merge_head_binding.py`; the last is in the declared surface, contrary to the lane's list. No file of the six shared build files is in the diff (constraint met).
- **Unrequested:** the `upstream_count_without_action` refusal (`pre_merge_gate.py:1572-1579`) is asked for by no deliverable; it is tested.

**Layer 2 verdict:** findings — 2 minor.

### Layer 3 — Correct

| Defect | File:line | Triggering input | Effect | Severity |
|--------|-----------|------------------|--------|----------|
| **L3-1** | `_freshness_crosscheck.py:719-731,805-806,829-833` (re-read); `_npm_cmd_discover.py:350-381` (re-read) | a whole-tree change in an npm project; the row is the discoverer's own `run test` / `run lint` / `run build` | `parse_row_scope` reads the canonical `run` and the scope `('test',)`; `_scope_adequate` is false for a whole-tree change, so the row is `ROW_SCOPE_TOO_NARROW`, a refutation, where it was `ROW_CANONICAL_UNKNOWN`, an inability that passed. The same flip is reported (not re-read) for the Maven `clean install` canonical (`_maven_cmd_discover.py:1252`) and the Gradle multi-task canonicals (`_gradle_cmd_discover.py:502-522`). Refutations outrank inabilities in the candidate selection (`:1035-1053`, not re-read), so the push and freshness gate goes stale with `build_scope_narrow` for every npm-only commit. A false block of a gate in normal use for npm, Gradle and Maven-chain consumers | **major** |
| L3-2 | `_maven_execute.py:593-600` (re-read); `_maven_cmd_parse.py:470-482` (re-read) | a `-Dtest=...` run with `-Dsurefire.failIfNoSpecifiedTests=false` whose log carries `No tests to run.` and no summary | `selector_miss_reason` needs a named miss or a parsed summary with `total == 0`, so it returns `None`; the zero-test guard then returns `success` for the `No tests to run.` line without asking whether a selector was in play. Before the landing the same run was `indeterminate`. **Re-graded to minor:** it fails open only if Surefire prints `No tests to run.` (not a `No tests were executed` line) for a missed selector, which only a run shows, and it needs a non-default flag | minor |
| L3-3 | `_freshness_crosscheck.py:624-626` (re-read) | a row `run --command-args verify --working-dir sub` with `command_args='verify'` | the recorded field drops every executor flag outside the payload, including `--working-dir` and `--project-dir`, so the row reads as whole-tree; the joined-args reader refused it as unreadable. More permissive than before, against the standing constraint, though such calls are uncommon (the flag reach is the leaf's reading, `npm.py:47`, `pyproject_build.py:90`, `_build_cli.py:93`, not re-read) | minor |
| L3-4 | `_freshness_crosscheck.py:734-754` | a legacy row unreadable because of a flag inside the payload; or a new-executor row whose value starts with `-` (the template records `None`) | the remedy hint says to put the executor flag before `--command-args`, which does not help the first, and calls a current row one that "predates the field" in the second | minor |
| L3-5 | `_maven_execute.py:441-445,474,522-524` | a quiet run whose only class is all `@Disabled`; a back-to-back run less than about 1 s earlier | the credit counts the report's `tests` attribute (skipped included), though the docstring says "executed"; the start bound is log mtime minus the truncated duration minus 1 s, so a very recent neighbour's report can be credited; any concurrent writer's report in the same tree is credited. Not shown by reading whether this occurs in practice | minor |
| L3-6 | `_maven_execute.py:593-600` | see L3-2 | no control exists for the selector plus marker case | (with L3-2) |
| L3-7 | `_cmd_client_query.py:932-936`; `_maven_cmd_discover.py:588-593` | a reactor member with a malformed POM | resolve says the module "declares no canonicals and is not built by the root reactor", which misstates the cause; `pom_unreadable` is not in the resolve output, so the gate-record half of D5 exists only as a document obligation | minor |
| L3-8 | `build-maven/SKILL.md:90` | an exit-0 Failsafe `-Dit.test` miss under `verify` when Surefire collected any unit test | Surefire and Failsafe counts are summed, so the miss stays undetected even in a single-module `verify`; the SKILL limit names only "inside a reactor" | minor |
| L3-9 | `pre_merge_gate.py:1457-1466,1592` | a fact token with a leading space, `' merge_state=merged'` | the key check strips the key, the raw token is forwarded; `mark-step-done` does not strip, so the fact is persisted under the undeclared key `' merge_state'`; the declaration was therefore only partly enforced | minor |
| L3-10 | `_maven_cmd_parse.py:425`, `_maven_execute.py:124`, `test_discover_modules.py:785,823`, `test_freshness_notation_crosscheck.py:631` | the documentation standard | history wording ("left it unguarded", "a correction to the former", "was not enough") | minor |
| L3-11 | `pre-push-quality-gate.md:493` | branch 4 text | self-contradicts: "the whole-tree run did not finish" and "the run FINISHED and its log was read" for `indeterminate` | minor |
| L3-12 | `pre_merge_gate.py:1506-1511` | a merge already landed | `record_merge` runs the full step-population scan on every call; a failure to discover the population refuses to record a merge that has landed. Fails closed, leaves the step unrecorded | info |

**Layer 3 not shown by reading:** whether pre-push branch 6 stops on the out-of-reactor resolve error rather than passing (`_maven_cmd_discover.py:327-331`; a whole-tree root row is still scope-adequate for any change, so the freshness side can certify a module the root never builds); whether the test fixtures stay inside the isolated home (`_declared_fact_keys()` drives the production population scan, which walks plugin-cache roots; conftest isolation not read).

**Layer 3 verdict:** findings — 1 major, 9 minor, 1 info.

### Conformance to the Project's Own Rules

| Rule source | Rule | Verdict | Evidence |
|-------------|------|---------|----------|
| CLAUDE.md § Documentation Standards | current state only | deviates | L3-10 |
| CLAUDE.md § Script Execution | scripts run via the executor | conforms | no direct script path added |
| spec standing constraint | the gate gets more precise, never more permissive | deviates | L3-2, L3-3 |
| spec standing constraint | keep the split fail-direction (a refutation fails closed, an inability passes with its reason) | deviates | L3-1 moves multi-token goal payloads from inability to refutation |
| spec standing constraint | every relaxation ships a control that still blocks | deviates | no control for the selector plus marker case |
| spec standing constraint | no edit to the six shared build files | conforms | `git diff --stat 3839835cc 19da7ed84` lists none |
| spec D1 | `required_coverage` and `CANONICAL_ANALYSES` not changed | conforms | absent from the diff |
| spec D5 | malformed root POM yields the named reason in discovery and the gate record | deviates | discovery only (L3-7) |
| CLAUDE.md § tests | real Maven never invoked in tests | conforms | static logs and hand-written reports |

## Metrics and Anomalies

- Tokens: `unknown`.
- Anomalies: a pre-existing 0.05 s timing race in `test_route_hand_back_carries_queued_seconds_when_the_bound_expires` failed twice mid-run in an untouched file (the lane's note; later rewritten upstream); two self-review rounds reported 15 and 8 findings, the second round's new major (the resolve seam cascading an out-of-reactor module to the root's run) was fixed in-plan; the lane's own rule breaches (a few shell reads and one `sed -i`) are recorded in its message.

## Routing and Merge Behavior

- Review: CodeRabbit (required, quota-limited) reviewed twice (12 inline threads and 3 nitpicks; two findings declined with a reason), then hit its hourly allowance; the lane applied the standing authorization on the final head `0058c2a9a` (lane's claim, not re-read). Sourcery refused on its own budget.
- CI/merge: merged through the queue; the merge state and commit were re-read.
- Sonar: `n/a`.

## Reconciliation Actions

- [x] row `status` → `shipped`
- [x] row `pr` stamped `1938`
- [x] row `landing` stamped `landings/PLAN-LB-124.md`
- [x] row `plan_marshall_plan_id` stamped `rb-lb-124-push-gate-and-maven-guard-truth-fixes`
- [x] epic.md narrative reconciled; the layer-3 major recorded as an Open Defect, the minors as one Watch
- [x] `queue-view.md` regenerated

## Follow-Ups

- **L3-1 is reported to the operator at once and is NOT staged.** The focus rule's stop rule warrants a fix plan for a major that falsely blocks a gate in normal use; it becomes a staged spec only on the operator's word. A fix would add a control for multi-token goal payloads, and would decide whether `parse_row_scope` reads goals as scope only for the tools whose positional tokens are modules.
- Owed outside the plan, operator-run: a harness sync; an executor regeneration in every project (D2 changes the executor template, so rows written by unregenerated executors keep today's reading); a daemon reconcile so the routed child runs D3 and D6.
