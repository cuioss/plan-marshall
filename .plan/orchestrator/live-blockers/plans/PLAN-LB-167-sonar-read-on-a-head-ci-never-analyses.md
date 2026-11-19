# PLAN-LB-167: A Sonar read on a head the project's CI never analyses is decided from the last analysed head, never left `undecidable` for ever

epic: live-blockers
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.
> Staged on the operator's word after the operator reported the symptom on a consumer project (pm-mcp-clients, PR #500) and said it has been seen several times. Source: the Open Defect "A Sonar read is `undecidable` on every docs-only head of a consumer project whose CI skips the build there" in `epic.md`.
> Shares one file, `runbook_lane.py`, with PLAN-LB-168 in different functions: a single shared file sequences nothing.

## Objective

The runbook lane treats a Sonar read that answers `undecidable` as a blocker and tells the run to retry. On a head the project's CI deliberately never analyses, a retry can never succeed. In the consumer project pm-mcp-clients, `skip-on-docs-only` defaults to on in the reusable build workflow: on a docs-only head the `build` and `sonar-build` jobs are skipped, Sonar's pull-request analysis stays on the earlier head, and the PR-scoped read compares that revision with the head and answers `undecidable` (`stale_analysis: analysed {sha} != head {sha}`). Every docs-only head of such a project is then blocked, and the only way through is the operator accepting an unknown read.

This plan gives that case its own, fail-closed answer: when the analysis is of an earlier head AND the change from that head to the current one is one the project's own footprint rule does not build, the open-finding read of the analysed head is the read for this head, reported under a distinct, named reason. Anything the lane cannot place stays `undecidable`. A bare `0` is never produced.

## Deliverables

1. The lane decides a `stale_analysis` read from the analysed head when the delta since it is not built. When the Sonar read is `undecidable` with the stale-analysis reason and both revisions are present, the lane resolves the analysed revision in the routed checkout, lists the paths changed from it to the head, and classifies them with the project's own footprint rule. When every path is a path the project does not build, the read is carried forward from the analysed head: the verdict is not `undecidable_read` but a distinct, named reason that states both revisions and that the delta was not built. When the analysed revision cannot be resolved locally, a path cannot be placed, the rule cannot be read, or the diff cannot be listed, the verdict stays `undecidable_read`. The outline settles the evidence the decision rests on (see the verify-first clause): the lane's classifier, the CI check-runs of the head, or both.
   - Skills: plan-marshall:ref-code-quality, pm-dev-python:python-core, plan-marshall:runbook-lane
   - Persona: implementer
2. The carried-forward read is an enumeration, not an assumption. The open findings of the analysed head (issues plus the security hotspots still to review, with their keys and rules) are read through the same plan-less read the lane already uses, so the count, the key set and the rules the gate and the landing facts take are measured, and a carried-forward `0` is a confirmed zero of the analysed head. Where the read cannot enumerate on a stale analysis today, the outline decides the smallest change that lets it, inside the Sonar read verb and its contract, without weakening the stop it applies to every other stale analysis.
   - Skills: plan-marshall:ref-code-quality, pm-dev-python:python-core, plan-marshall:workflow-integration-sonar
   - Persona: implementer
3. The documents state the rule. The lane skill's Sonar step no longer says "retry the read" for a stale analysis the project's CI will never refresh: it states the carry-forward rule, its named reason, and that an unplaceable change stays a blocker. The Sonar integration skill's contract states the same for the read verb, and the landing facts record the figure as measured at the analysed head, naming the analysed revision beside it, so a carried-forward figure never reads like a measurement of the head.
   - Skills: plan-marshall:ref-code-quality, pm-documents:ref-documentation
   - Persona: documenter
4. Tests pin D1 to D3, written against the unfixed tree first: a stale analysis whose delta is documentation only is decided from the analysed head, for a confirmed zero and for a non-zero count with its keys; a stale analysis whose delta contains one buildable path stays `undecidable_read`; an unresolvable analysed revision, an unplaceable path, an unreadable footprint rule and a failed diff each stay `undecidable_read`; and the unchanged paths hold, that a stale analysis never enumerates through the read verb alone and that a non-PR read keeps its CE-state contract.
   - Skills: plan-marshall:ref-code-quality, pm-dev-python:python-core, pm-dev-python:pytest-testing
   - Persona: module-tester

## Standing Constraints

- Fail closed. A carried-forward read exists only when every changed path since the analysed head is positively classified as not built by the project's own rule. A path the classifier cannot place, a rule it could not read and a revision it could not resolve all leave the read `undecidable`.
- Never a bare `0`. A carried-forward figure is the measured enumeration of the analysed head and is reported with its reason and both revisions; an `undecidable` read still carries `unknown` into the landing facts.
- A stale analysis whose delta contains buildable code is unchanged: it stays `undecidable`, because the analysed head is not the head.
- The lane never records a dismissal itself and `sonar-gate --dismissed-keys` stays refused; a carried-forward read with open findings is gated by the same operator-selection rule as any confirmed read.
- A project that does not analyse with Sonar is unchanged (`not_configured` admits), and a non-PR read keeps its CE-state contract with both revisions blank.
- Order inside the plan: deliverables 1 to 3, then deliverable 4 written against the unfixed tree.
- No file outside the runbook lane, the Sonar integration skill and their tests is touched. No change under `.plan/orchestrator/` other than the plan's own inbox message.
- Scope-bloat note: four deliverables, under the presumptive-split guard.

## Claim Labels

- OBSERVED (read at `main` `46d3308ea` on 2026-11-19): `workflow-integration-sonar/scripts/sonar.py` § `_verify_analysis_revision` (lines 433-480) answers `undecidable` with the reason `stale_analysis: analysed {sha} != head {sha}` and both revisions when they differ, and `cmd_read_open_issues` (lines 999-1128) returns that verdict through `_undecidable_read` before any enumeration, so a stale read carries `open_issue_count: None` and no keys.
- OBSERVED (read at `main` `46d3308ea`): `runbook_lane.py` § `_sonar_gate_verdict` (lines 1743-1878) answers `merge_allowed: false`, reason `undecidable_read`, for any `count_status: undecidable`, and `runbook-lane/SKILL.md` lines 826-829 say "retry the read, and if it stays undecidable do not merge".
- OBSERVED (live read on 2026-11-19): on pm-mcp-clients PR #500 the check-runs `build / build`, `build / sonar-build` and `build / quarkus-alignment` are SKIPPED while `build / check-changes` and `build / conclusion` are SUCCESS. The reusable workflow's `skip-on-docs-only` input defaults to `true` (`cuioss-organization/.github/workflows/reusable-maven-build.yml` line 41-45), pm-mcp-clients' `.github/project.yml` sets no such key, and `sonar-build` runs only when `should-build != 'false'`.
- OBSERVED (read on 2026-11-19): `runbook_lane build-classify` run against `/home/oliver/git/pm-mcp-clients` for `doc/adr/001-specifications-of-the-clients.adoc` answers `source: architecture`, `kind: buildable`. That ADR is a documentation file the consumer's CI treated as not built.
- HYPOTHESIS: the `buildable` answer above comes from a classifier that, for a consumer whose footprint rule lives in a reusable workflow the checkout does not hold, falls back to the architecture's documentation module and finds none (the architecture data being absent or without a documentation module on that checkout). Confirm or refute at `runbook_lane.py` § `_read_footprint_rule`, `_architecture_module_prefixes`, `_architecture_documentation_surfaces` and `_classify_path` (verify-at-outline).
- HYPOTHESIS: the live reason string of the #500 read is `stale_analysis`, inferred from the skipped `sonar-build` job and not read from the provider. Settle it with a read-only `read_open_issues` against the consumer's pull request, or from the lane's own progress record of that run (verify-at-outline).
- HYPOTHESIS: Sonar's pull-request analysis for #500 still names an earlier head whose read was clean; confirm before relying on a carried-forward zero for that run (verify-at-outline).
- Verify-first clause: the outline settles (a) what the decision rests on, given the classifier's `buildable` answer above: the lane's classifier made correct for a consumer whose rule it cannot read, the CI check-runs of every head after the analysed one (the CI abstraction reads them), or both, choosing the smaller change that is still fail-closed for a head whose Sonar analysis was skipped for another reason (a failed or cancelled job, Dependabot skip); (b) whether the analysed revision is present in the routed checkout and how it is fetched; (c) which verb enumerates the analysed head's findings and what it needs; (d) every consumer of `count_status`, `analysis_revision` and `head_revision` (the gate, the facts verb, the scan-summary marker, the landing payload), so none reads a carried-forward read as a measurement of the head. A refutation of (a) loops back to re-scope.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/runbook-lane/scripts/runbook_lane.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/runbook-lane/SKILL.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-sonar/scripts/sonar.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-sonar/SKILL.md`
- OBSERVED: `test/plan-marshall/runbook-lane/test_runbook_lane_sonar.py`
- OBSERVED: `test/plan-marshall/runbook-lane/test_runbook_lane_sonar_landing.py`
- OBSERVED: `test/plan-marshall/workflow-integration-sonar/test_sonar_analysis_revision.py`
- OBSERVED: `test/plan-marshall/workflow-integration-sonar/test_read_open_issues.py`

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: PLAN-LB-168 in `marketplace/bundles/plan-marshall/skills/runbook-lane/scripts/runbook_lane.py`, one file, in different functions (the Sonar gate and classifier here, the review-body parser there). PLAN-LB-168 declares no other file of this surface. Neither plan edits the other's functions; whichever merges second takes the other's `runbook_lane.py` hunk through an ordinary rebase.
- Adjacent to: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/sonar-roundtrip.md`, the plan lifecycle's own consumer of `count_status == confirmed`, which stays untouched: the carry-forward is a lane decision, and the lifecycle keeps requiring a confirmed read of its own head.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-167-sonar-read-on-a-head-ci-never-analyses.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits NO file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox message.
