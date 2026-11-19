# PLAN-LB-171: PLAN-LB-167 completion — a delegating consumer's docs-only head is decided, the carry-forward binds itself in code, and every runbook lane gets its own PR body slot

epic: live-blockers
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.
> Staged on the operator's word. Source: `landings/PLAN-LB-167.md` (layer-1 finding L1-1, layer-2 findings L2-1 to L2-3, layer-3 findings L3-1 to L3-3, one leaf, the majors re-read by the orchestrator at the merge commit `c35f23c12`), the Open Defect "A Sonar read is `undecidable` on every docs-only head of a consumer project whose CI skips the build there" and the Open Defect of the PLAN-LB-167 landing in `epic.md`.
> Shares one file, `runbook_lane.py`, with PLAN-LB-168 in different functions: a single shared file sequences nothing.

## Objective

PLAN-LB-167 merged the carry-forward mechanism: when a Sonar analysis is of an earlier head and the project's own footprint rule does not build the change since, the read of the analysed head stands for the current one. It did not fix the case it was staged for. A consumer whose CI only delegates to a reusable workflow (no `paths-ignore` of its own, no architecture documentation module, the shape of pm-mcp-clients PR #500) still ends at `delta_buildable` and `undecidable_read` on a docs-only head, and the lane text still tells the run to "retry the read", which can never succeed there. Around the decision verb, the read licence, the gate's carried-forward pair and the marking of a carried-forward figure do not bind each other in code, so the property "fail closed" holds in lane prose only. And the PR that carried the merge, #2028, was created with another plan's body: the runbook lane allocates its PR body through one shared slot.

This plan finishes the job: the delegating consumer's docs-only head is decided from the rule the CI actually applies, the carry-forward cannot reach the gate or the landing facts unmarked, and no two callers share a PR body slot.

## Deliverables

1. The lane decides a docs-only delta for a consumer that delegates its build to a reusable workflow. Today the footprint rule is read from the checkout's own workflow files (`_read_footprint_rule`, `runbook_lane.py` lines 1341-1365 at `c35f23c12`); a delegation yields no `paths-ignore` (`_paths_ignore_globs` returns `None`, lines 1375-1412), the source becomes the architecture, and with no architecture documentation module every path is `buildable` (lines 1583-1589, 1665-1671, `_is_project_doc` at 1453). The outline settles what the decision rests on, given that the PLAN-LB-167 clause "a refutation of (a) loops back to re-scope" has now fired: (a) the rule the CI applies, read where it lives (the called reusable workflow at the ref the `uses:` line pins, read-only through the CI abstraction, together with the consumer's own overrides such as an `extra-buildable` input or a project configuration key); (b) the CI check-runs of the head (the build jobs skipped while the change-detection job succeeded); or (c) both, one corroborating the other. Whatever it chooses stays fail-closed: a skip for any reason other than the footprint gate (a failed or cancelled job, a Dependabot skip, a conditional) is not a carried-forward delta; no job name is guessed; an unreadable, unpinned or unreachable rule stays `undecidable_read` under a named reason; and every other refusal of PLAN-LB-167's decision verb is unchanged.
   - Skills: plan-marshall:ref-code-quality, pm-dev-python:python-core, plan-marshall:runbook-lane
   - Persona: implementer
2. The carry-forward binds itself in code. (a) The read licence (`_licenses_stale_analysis`, `sonar.py` lines 999-1015) names the analysed revision only, which the verb's own `undecidable` output discloses, so a caller supplying that revision gets a `confirmed` carried-forward read for a head whose delta was never classified; the licence is bound to the head the decision verified (or to the decision's verdict), and a read whose head differs is refused. (b) The gate's carried-forward pair (`--carried-forward-analysis-revision`, `--carried-forward-head-revision`, `runbook_lane.py` lines 2048-2092) is supplied by the caller and tied to no read or verdict, and the marking is opt-in: without the pair the gate answers a plain `no_open_issues` (lines 2189-2198) and without `--analysed-revision` the facts carry no marker (lines 2482-2493), so a carried-forward figure can read like a measurement of the head, against PLAN-LB-167's D3. The read's own `carried_forward: true` travels to the gate and to the facts verb, and a carried-forward count that arrives without its marking is refused; the outline settles the smallest mechanism (the marker passed through, or the pair derived from the verdict) and records why.
   - Skills: plan-marshall:ref-code-quality, pm-dev-python:python-core, plan-marshall:runbook-lane, plan-marshall:workflow-integration-sonar
   - Persona: implementer
3. No two callers share a PR body slot. The lane text allocates its body with `pr prepare-body --plan-id NO_PLAN` and `pr create --plan-id NO_PLAN` (`runbook-lane/SKILL.md` lines 777-782), and the slot those return is one file, `.plan/local/plans/NO_PLAN/work/ci-bodies/pr-create-default.md`, which the orchestrator's `land` verb also writes (`plan-orchestrator/workflow/land.md`, Step 4). The PR body and the squash commit message of #2028 are PLAN-LB-169's text; the observed route is that shared slot, and the race between two lanes that wrote it is a hypothesis the outline settles. Both verbs already accept `--slot` (`pr prepare-body [--slot SLOT]`, `pr create [--slot SLOT]`, default `default`). The lane text and `land.md` name a slot per caller (the lane's derived name, `land` for the ledger land) at every `prepare-body`, `prepare-comment` and consuming call, and the outline decides whether the CI abstraction also refuses or warns on the shared default slot under `NO_PLAN`, so the next caller that forgets the slot cannot silently cross-feed.
   - Skills: plan-marshall:ref-code-quality, pm-plugin-development:plugin-architecture, plan-marshall:tools-integration-ci
   - Persona: implementer
4. The documents state what the code does. `runbook-lane/SKILL.md` lines 853-857 and 947 still say "retry the read, and if it stays undecidable do not merge" for a stale analysis the carry-forward refused, which for a refusal such as `delta_buildable` can never succeed; the text names what a refusal means and what the run does instead (it is a blocker, and what is next is the operator's or a rebuild's). Lines 828-829 say the analysis "stays on a head the CI does not build", which inverts the cause: it is the current head the CI does not build. The Sonar integration skill's contract states the head-bound licence, and the lane text states the marker travelling to the gate and the facts.
   - Skills: plan-marshall:ref-code-quality, pm-documents:ref-documentation
   - Persona: documenter
5. Tests pin D1 to D4, written against the unfixed tree first: a recorded red run on the unfixed tree for each new behaviour, not a mutation run after the fix. One test runs the delegating shape through the real classifier (a workflow holding only a `uses:` delegation, no architecture documentation module, the PLAN-LB-167 case): a docs path is decided and a source path stays `undecidable_read`, plus a skip for another reason (a failed job, a Dependabot skip) staying undecidable if check-runs are used; a licensed read whose head differs from the verified one is refused; a carried-forward count reaching the gate or the facts verb without its marking is refused; the lane text and `land.md` each name a slot and a test pins it. The controls hold at `main` `c35f23c12`: the workflow-rule docs-only carry-forward, the buildable-delta refusal, the unresolvable-revision refusal and the non-PR read keep their present answers. The two PLAN-LB-167 tests that stub `_classify_paths` (`test_an_unplaceable_path_stays_undecidable`, `test_an_unreadable_footprint_rule_stays_undecidable`) are kept and a real-classifier twin is added beside each.
   - Skills: plan-marshall:ref-code-quality, pm-dev-python:python-core, pm-dev-python:pytest-testing
   - Persona: module-tester

## Standing Constraints

- Fail closed. A carried-forward read exists only when every changed path since the analysed head is positively classified as not built by the rule the CI actually applies; an unreadable, unpinned or unreachable rule, a path the rule does not place and a skip with another cause leave the read `undecidable`. A bare `0` is never produced.
- The fix does not decide a project's rule by guessing: no invented documentation-glob list, no build-job name guessed from a check-run list.
- A stale analysis whose delta contains buildable code stays `undecidable`; `--dismissed-keys` stays refused; a project without Sonar and a non-PR read keep their present contracts.
- The plan does not edit the body or the history of #2028; a corrected body is the operator's call.
- Order inside the plan: deliverables 1 to 4, then deliverable 5 written against the unfixed tree.
- No file outside the runbook lane, the Sonar integration skill, the CI abstraction's body-slot path, `land.md` and their tests is touched. The minors the landing records (the SHA alias, the empty-delta wording, the dirty-tree and symlink guards, the quoted-path handling, the function sizes, the flag spellings) stay in the Watch and are not taken here. No change under `.plan/orchestrator/` other than the plan's own inbox message.
- Scope-bloat note: five deliverables, under the presumptive-split guard; the operator's rule is as few plans as possible, and one slot is free. Deliverable 3 lives in another module (`tools-integration-ci` and `land.md`) and shares no function with the others; the rationale for keeping it here is recorded as an epic decision.

## Claim Labels

- OBSERVED (re-read at `c35f23c12` on 2026-11-19): `runbook_lane.py` lines 1284-1297 (a literal `skip-on-docs-only: true` is the only opt-in), 1375-1412 (a delegation yields `None`), 1583-1589 and 1665-1671 (the fallback and the `['']` prefix), 1453 (`_is_project_doc` needs a documentation module), 1933-1967 (the decision verb), 2189-2198 and 2482-2493 (the unmarked paths); `sonar.py` lines 999-1015 (the licence names the analysed revision only); `runbook-lane/SKILL.md` lines 826-857.
- OBSERVED (re-read through the CI abstraction and `git show` on 2026-11-19): the body of PR #2028 and the squash message of `c35f23c12` describe PLAN-LB-169's change; PR #2029, PLAN-LB-169's own, carries nearly the same body; PRs #2027 and #2030 carry their own bodies. `pr prepare-body` and `pr create` both declare `--slot` (live `--help`). `runbook-lane/SKILL.md` lines 777-782 use `--plan-id NO_PLAN` with no slot.
- OBSERVED (live read on 2026-11-19, from the PLAN-LB-167 analysis): on pm-mcp-clients PR #500 the check-runs `build / build`, `build / sonar-build` and `build / quarkus-alignment` are SKIPPED while `build / check-changes` and `build / conclusion` are SUCCESS; the reusable workflow's `skip-on-docs-only` input defaults to `true`.
- OBSERVED (leaf reading, not re-read): the delta listing is `git diff --name-only --no-renames A B` (`:1829`); the guards `worktree_not_at_head`, `worktree_dirty`, `worktree_ignored_inputs` are at `:1795-1931`; the post-enumeration recheck is at `sonar.py:1156-1190`.
- HYPOTHESIS: two lanes wrote the shared body slot between one lane's `prepare-body` and `pr create`, so `pr create` consumed the wrong body; whether `prepare-body` hands every caller the same path, and whether `pr create` reads the file at consume time, was not read in `ci_base.py` (verify-at-outline, deliverable 3).
- HYPOTHESIS: the footprint rule of a delegating consumer can be read from the reusable workflow at the ref its `uses:` line pins, through the CI abstraction, with the consumer's own overrides; neither the reusable workflow's content nor the override surface was read in this analysis (verify-at-outline, deliverable 1).
- Verify-first clause: the outline settles (a) which of deliverable 1's sources (the called workflow's rule, the head's check-runs, or both) is fail-closed for a head whose Sonar analysis was skipped for another reason, and reads the real shape before choosing; (b) the smallest mechanism that binds the licence and the marker (deliverable 2); (c) whether the shared slot is the whole cause of the #2028 body (deliverable 3), and whether the default slot under `NO_PLAN` is refused or warned on; (d) every consumer of `count_status`, `analysis_revision`, `head_revision` and `carried_forward` after the change, so none reads a carried-forward read as a measurement of the head. A refutation of (a) loops back to re-scope.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/runbook-lane/scripts/runbook_lane.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/runbook-lane/SKILL.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-sonar/scripts/sonar.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-sonar/SKILL.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/workflow/land.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-integration-ci/scripts/ci_base.py`
- OBSERVED: `test/plan-marshall/runbook-lane/test_runbook_lane_sonar.py`
- OBSERVED: `test/plan-marshall/runbook-lane/test_runbook_lane_sonar_landing.py`
- OBSERVED: `test/plan-marshall/workflow-integration-sonar/test_sonar_analysis_revision.py`
- OBSERVED: `test/plan-marshall/workflow-integration-sonar/test_read_open_issues.py`
- OBSERVED: `test/plan-marshall/tools-integration-ci/test_ci_base_cli.py`

## Dependencies and Sequencing

- Depends on: none (PLAN-LB-167 is merged).
- Overlaps with: PLAN-LB-168 in `marketplace/bundles/plan-marshall/skills/runbook-lane/scripts/runbook_lane.py`, one file, in different functions (the Sonar gate, the classifier and the build rule here, the review-body parser there; PLAN-LB-167's merge touched no parser function, and a conflict could arise only if PLAN-LB-168 also edits `main`'s argparse block). PLAN-LB-168 declares no other file of this surface. Neither plan edits the other's functions; whichever merges second takes the other's `runbook_lane.py` hunk through an ordinary rebase.
- Adjacent to: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/workflow/analyze.md` and `handle-open.md`, which PLAN-LB-170 edits and this plan does not touch; `phase-6-finalize/workflow/sonar-roundtrip.md`, the plan lifecycle's own consumer of `count_status == confirmed`, which stays untouched.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-171-lb-167-completion-delegating-checkout-gate-binding-body-slot.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits NO file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox message.
