envelope_version=1
sender_type=plan
sender_id=rb-lb-167-sonar-read-on-a-head-ci-never-analyses
epic=live-blockers
kind=landing
created=2026-11-19T20:53:28Z

```landing-facts
schema=landing-facts/1
plan_id=rb-lb-167-sonar-read-on-a-head-ci-never-analyses
epic=live-blockers
pr=#2028
merge_state=merged
cleanup_owed=false
deliverables_total=4
deliverables_done=3
total_tokens=unknown
harness=opencode
model=deepseek-v4.1-flash/high
effort=high
plugin_version=0.1
executor_version=0.1.2155
steps=setup:done,implement:done,build-gate:done,self-review:clear,pr:done,reviews:done,merge:done
unresolved_review_threads=0
review_body_findings_total=4
review_body_findings_handled=4
sonar_open_new_issues=n/a
step.sonar-roundtrip.open_issue_rules=n/a
```

## 1. Deliverables

**D1 — the lane decides a stale analysis from the analysed head.** Commit `673bf4873`, hardened by `9cead0b9d`, `a7ee50b09`, `98d5a8863`.

| Done-when | Verdict | Test | Order | Failing run | Commit |
|---|---|---|---|---|---|
| resolves the analysed revision, lists the delta, classifies it with the project's own footprint rule | met | `test_the_project_own_rule_decides_a_real_docs_only_delta`, `test_a_docs_only_delta_is_carried_forward_from_the_analysed_head` | mutation-after | `55f0f7810`, job `56c349fea4334de3a2542b1d9a6759d8` | `673bf4873` |
| every path not built → carried forward, under a distinct named reason stating both revisions | met | `test_a_docs_only_delta_is_carried_forward_from_the_analysed_head` | mutation-after | same | `673bf4873` |
| unresolvable revision / unplaceable path / unreadable rule / failed diff stay `undecidable_read` | met | `test_an_unresolvable_analysed_revision_stays_undecidable`, `test_an_unresolvable_head_revision_stays_undecidable`, `test_a_failed_diff_stays_undecidable`, `test_an_unreadable_footprint_rule_stays_undecidable`, `test_an_unplaceable_path_stays_undecidable`, `test_a_revision_the_checkout_does_not_hold_stays_undecidable` | mutation-after | same | `673bf4873` |
| "The outline settles the evidence the decision rests on … the classifier made correct for a consumer whose rule it cannot read, the CI check-runs, or both" | **not met as written** | — | none | — | — |

The last clause is the one open gap: see §9. The mutation run's log is `/home/oliver/.plan-marshall/marshalld/job-logs/56c349fea4334de3a2542b1d9a6759d8.log`; the mutation forced `carry_forward` to `False`, forced the read licence to `False`, and renamed the verb in § 6 of the lane text, and six named tests failed. Mutations were reverted and `git status --porcelain` was clean before the green run.

**D2 — the carried-forward read is an enumeration.** Commit `a2b03dd6d`, hardened by `93cc52854`.

| Done-when | Verdict | Test | Order | Failing run | Commit |
|---|---|---|---|---|---|
| enumeration through the same plan-less read; count, keys and rules measured; a carried-forward `0` is a confirmed zero of the analysed head | met | `test_the_named_analysed_revision_enumerates_the_analysed_head`, `test_a_licensed_read_enumerates_the_keys_of_the_analysed_head`, `test_the_named_revision_carries_the_read_forward` | mutation-after | `55f0f7810`, job `56c349fe…` | `a2b03dd6d` |
| smallest change inside the read verb, the stop unchanged for every other stale analysis | met | `test_a_different_named_revision_keeps_the_stop`, `test_a_licence_cannot_cover_an_unreported_revision`, `test_a_licence_cannot_cover_an_unresolvable_head`, `test_a_stale_analysis_never_enumerates_through_the_read_alone`, `test_a_licence_without_a_pull_request_is_refused` | mutation-after | same | `a2b03dd6d` |

**D3 — the documents state the rule.** Commit `4885fa95e`, corrected by `a66a122a9`, `b871434c4`, `93cc52854`.

| Done-when | Verdict | Test | Order | Commit |
|---|---|---|---|---|
| the lane's Sonar step states the carry-forward rule, its named reason, and that an unplaceable change stays a blocker | met | `test_the_lane_text_states_the_carry_forward_rule` (failed in the mutation run) | mutation-after | `4885fa95e` |
| the Sonar integration skill's contract states the same for the read verb | met | file read: `workflow-integration-sonar/SKILL.md` § `sonar.py read_open_issues` | none | `4885fa95e` |
| the landing facts record the figure as measured at the analysed head, naming the revision | met | `test_the_analysed_revision_rides_beside_a_carried_forward_count`, `test_an_analysed_revision_on_a_failed_read_is_refused`, `test_a_project_without_sonar_refuses_an_analysed_revision` | none | `4885fa95e` (`--analysed-revision` shipped in `673bf4873`, same file) |

**D4 — tests pin D1 to D3.** Commit `55f0f7810`.

The eight cases the deliverable names are all present and passing: docs-only carry-forward for a confirmed zero and for a non-zero count with its keys; one buildable path refusing; unresolvable revision, unplaceable path, unreadable rule and failed diff refusing; a stale analysis never enumerating through the read verb alone; a non-PR read keeping its CE-state contract. Order `mutation-after`, failing run `55f0f7810` with the fix mutated, output `56c349fea4334de3a2542b1d9a6759d8`. Per-head test runs: full `module-tests` green at `55f0f7810` (973 s), `b871434c4` (1231 s) and `5829f1e86` (816 s); `module-tests plan-marshall --filter sonar` green at `a66a122a9` (312), `9cead0b9d` (314), `a7ee50b09` (318), `98d5a8863` (321).

## 2. Personas and skills

| Step | Persona | Skills |
|---|---|---|
| D1, D2 (production code) | `persona-implementer` | `plan-marshall:ref-code-quality`, `pm-dev-python:python-core`, `plan-marshall:runbook-lane` (D1), `plan-marshall:workflow-integration-sonar` (D2) |
| D3 (documentation) | `persona-documenter` | `plan-marshall:ref-code-quality`, `pm-documents:ref-documentation` |
| D4 (tests) | `persona-module-tester` | `plan-marshall:ref-code-quality`, `pm-dev-python:python-core`, `pm-dev-python:pytest-testing` |
| self-review rounds, PR-comment triage | `persona-code-reviewer` | — |

No skill was added for surface drift: every changed path is on the spec's Expected Surface.

## 3. Hypotheses

- *The classifier's `buildable` answer for a documentation file comes from the architecture fallback finding no documentation module* — **confirmed in mechanism, unverified for the consumer**. `cmd_build_classify` fell back to `_architecture_module_prefixes(project_dir) or ['']` (`runbook_lane.py:1671` before the change), so a checkout with no architecture makes every path buildable, and `_is_project_doc` needs a module whose `build_systems` carries `documentation` (`runbook_lane.py:1453`). The consumer's own checkout is outside this repository and was not read.
- *The live reason string of pm-mcp-clients #500 is `stale_analysis`* — **not settled**. The consumer's pull request is outside this repository; the decision does not depend on it.
- *Sonar's analysis for #500 still names a head whose read was clean* — **not settled**, for the same reason.

## 4. Findings

Self-review round 1 (sub-agent, `persona-code-reviewer`): one blocker (the footprint rule cannot place a path on the motivating consumer) and one should-fix (the carried-forward marking is opt-in) escalated to the operator; three nits, one docstring drift and two doc/code mismatches fixed in `a66a122a9`. Round 2: no new defect; three further nits fixed in `b871434c4`. Round 3: no defect; only the operator-decided items remained.

CodeRabbit (four body findings, all disposed):

| Finding | Disposition |
|---|---|
| `inline-1` — read the footprint rule from the target revision | fixed: `worktree_not_at_head` in `9cead0b9d`, then `worktree_dirty` in `a7ee50b09`, then `worktree_ignored_inputs` in `98d5a8863`, each with a real-repository regression |
| `inline-2` — compare the reread head with the head the delta checked | fixed in the lane text, `9cead0b9d` |
| `inline-3` — re-check the analysis revision after the hotspot fetch | fixed in `93cc52854`, including the empty-recheck refusal |
| `inline-4` — validate the head revision during the final check | fixed in `93cc52854` with a head-only-movement regression |

Sourcery refused on quota twice (optional bot, no merge gate).

## 5. Reviewers

| Reviewer | State | Heads reviewed | Trigger and wait history |
|---|---|---|---|
| `coderabbit` (required, `quota_limited`, `review_complete_after_handling`) | reviewed | formal review on `b871434c4`; marker review (`kind=reviewed`) on `a7ee50b09` | triggered once at 17:34; three follow-up rounds of findings answered commit-by-commit; no re-trigger after the later heads, which the done-exemption covers |
| `sourcery` (optional, `quota_limited`) | refused, then skipped | none | triggered once at 17:34; two quota notices answering in 1 day 17 hours; later heads report the check as SKIPPED |

Standing review authorization not used: the done-exemption applied instead, and `review-gate --required-reviewer coderabbit` answered `merge_allowed: true`.

## 6. Operator questions

1. "How should D1's evidence gap land?" — options *ship and report D1 not fully met* / *add a configured build-job name* / *add CI check-run evidence with a heuristic*; selected **ship and report D1 not fully met**.
2. "How strict should the carried-forward marking be?" — options *accept as documented residual* / *add a `carried_forward` count_status* / *require the pair whenever the progress file records one*; selected **accept as documented residual**.

No free-text operator messages.

## 7. Rule check

`guard: present` on this harness. Guard refusals by this run's own session: two — `R7` (an `edit` of `marketplace/.../runbook_lane.py` in the main checkout, re-issued in the worktree) and `R1` (a shell chain using a pipe, re-issued as one command).

Self-reported breaks of this lane's own shell rule: `ls` on two test directories at the start, `grep -n -E` on five build logs, `tail -n 20` on one test file, and `file` on one skill file. No repository file was created or edited outside the worktree; no workaround followed a guard refusal.

Builds: every one routed with the default mode and reported `mechanism=daemon_longpoll`, 14 `module-tests` and 14 `quality-gate` invocations. No `killed` job. One `module-tests` run hit the daemon's learned bound (1137 s, `timeout_source: learned`) and was re-run in the split form with `--timeout 1705`, which passed.

`executor-skew`: **not_applicable** — the lane text lives in this source checkout, so the executor maps the checkout's own scripts. The spec was read from `ledger_worktree`; `spec_differ` was not reported.

## 8. Build server

Setup preflight: `ready` (project registered, version 1). Every build used the daemon (`daemon_longpoll`), none degraded and none needed a launch-fault retry. No `killed` job. `runtime_stamp_reason` was absent, so the runtime stamp was measured in full.

## 9. Residue

- **D1's evidence clause is not met as written, by operator decision.** The decision rests on the project's own footprint rule, and that rule cannot place a path on a checkout that holds only a delegation to a reusable workflow and reports no architecture documentation module — the motivating consumer (pm-mcp-clients #500) is such a checkout. Closing it needs either an invented doc-glob list or a CI check-run rule that cannot tell a build job from another job without guessing its name; both are fail-open, and the spec's fail-closed constraint forbids either. The carry-forward works for a project that holds its `paths-ignore` or declares a documentation module; a head the lane cannot place stays `undecidable`, exactly as before.
- **The carried-forward marking is opt-in, by operator decision.** The lane text binds it and the gate refuses a half-supplied, equal-revision or non-confirmed pair, but a run that omits the flags renders an indistinguishable confirmed read.
- **A short/full-SHA alias of one commit still yields a false "!=" sentence** in the gate, which has no worktree to resolve revisions in. Accepted: the read reports full SHAs, so the lane never produces the alias.
- CodeRabbit's pre-merge *Title check* is inconclusive because it read unrelated objectives text; the change set is the Sonar carry-forward named in the title.
