# PLAN-LB-73: The runbook lane's text is consistent and its qualifying-review signal is reliable

epic: live-blockers
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-73-lb-72-completion.md` and is queued as one row file, `queue/PLAN-LB-73.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged from the adversarial landing analysis of PLAN-LB-72 (#1819, `cf28a05db`),
> `landings/PLAN-LB-72.md` § Deliverable Fidelity. Priority is **low**: nothing here blocks a run.
> **Each deliverable is its own outline deliverable, and each Done-when is its own success
> criterion. Do not merge them.** A Done-when says "fails at `cf28a05db`" only where the behaviour
> is new at that sha; a clause that already holds says "holds at `cf28a05db`". Grade each deliverable
> against THIS spec's Done-when text; an outline that rewrites a Done-when must say so and why.

## Objective

PLAN-LB-72 added the evidence-order rules, the classifier and the flat-identity error to the
runbook lane. Its edits left the lane text contradicting itself in four places, kept a
qualifying-review rule that a clean CodeRabbit review can never satisfy (which cost an unnecessary
91-minute operator question), and left three tests that cannot fail for the reason they name. This
plan closes those, each against a fixture that fails at `cf28a05db`, and adds the start-of-run guard a
lane needs against an executor older than the lane text it reads (D3). PLAN-LB-78 then rewrote the build
gate; its text names an executor worktree creation does not supply and contradicts itself on routing, so D4
makes that text and its `resolve` say only what is true.

## Deliverables

1. **The lane text states each rule once and the qualifying-review signal counts a clean review.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-implementer
   - The branch row (`SKILL.md:80`) states one set: the canonical `feature/`, `fix/` and `chore/`
     plus the project's configured `working_prefixes`, and no sentence in the row makes
     `working_prefixes` the sole set.
   - The §0a progress template carries the `order` slot per Done-when and no longer words a
     `mutation-after` or `none` entry as "failed before fix".
   - One place (§1) states how a Done-when is graded by order: `test-first` is met; `mutation-after`
     is met with the order stated; `none` on a "fails at" clause is `not met as written`. §3 and §6
     refer to it and do not restate it, and §1 and §3 no longer mandate test-first as the only valid
     order.
   - §6 requires the failing run's commit and output identifier only where `order` is not `none`.
   - §4's docs-only branch states whether `test-compile` applies to a docs-only head.
   - §7's "qualifying review" for a quota-limited reviewer counts a formal review AND the reviewer's
     marker-bearing summary comment that names the head with `kind=reviewed`, because CodeRabbit
     publishes a clean review only in that form (`coderabbit.md:311-316`). A reviewer that is not
     quota-limited keeps needing a review of the current head and is not affected.
   - The "base moved" step before the enqueue (`git merge origin/{base_branch}`) supplies the resolved
     `{commit_trailer}` line on the merge commit it creates, so the Commit trailer rule (every commit ends
     with exactly that line) has no exception the lane itself instructs (folded from `landings/PLAN-LB-48.md`,
     where the merge commit `092bc1a38` carried no trailer; PLAN-LB-77's `06610bd71` is the first instance).

   *Done when:* each of these fails at `cf28a05db`:
   - a doc test asserts the branch row names one set and does not contain the sentence that makes
     `working_prefixes` the sole source;
   - a doc test asserts the §0a template has an `order` slot and that no template line says "failed
     before fix" without it;
   - a doc test asserts §1 states the grading by order and that §3 and §6 do not restate it;
   - a doc test asserts §6 requires the failing-run identifier only for the orders that have one;
   - a doc test asserts §4 states the docs-only `test-compile` rule;
   - a doc test asserts §7 names the marker-bearing summary comment as a qualifying review for a
     quota-limited reviewer and keeps the current-head rule for a reviewer that is not;
   - a doc test asserts §7 requires the run to re-read the review surfaces (`ci pr comments`,
     `ci pr reviews`, the reviewer's summary comment) in the same step as the merge-gate question and
     again immediately before the enqueue, to put into the question only facts read in that step,
     and to treat a review of the current head that arrived after the question was asked as
     invalidating the answer (folded from `landings/PLAN-LB-70.md`, where a question stated that a
     head had not been reviewed 64 seconds after its review landed);
   - a doc test asserts §7 states that an unresolved review thread or an unhandled outside-diff
     finding on the merge head blocks the standing authorization;
   - the PLAN-LB-72 merge-gate state (both bots clean, `ci pr reviews` empty, CodeRabbit's summary
     comment covering the head) is a fixture a doc-level gate test treats as qualifying;
   - a doc test asserts the "base moved" step's merge instruction supplies the `{commit_trailer}` line
     (a bare `git merge origin/{base_branch}` with no message fails it).

2. **The tests of the existence check, the timeout and the evidence rule can fail for the reason they name.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-implementer
   - The timeout test makes the real `_cmd_client._augment_resolved` raise (or return no stamp) by
     patching what it reads, not by replacing the function with a stub, so a raising real function
     falls back to 1800 and the test fails. An in-test stub that returns a fixed value is not used.
   - The probed-layout test builds a versioned nested cache fixture (`{cache}/plan-marshall/0.1.0/…`)
     and asserts the versioned probe path, not the unversioned fallback.
   - The `test-compile` evidence test asserts a `test-compile` token beside the sha placeholder in the
     landing template, not the pre-existing `{sha}` text.
   - The glob helper's absence and any non-`ImportError` failure at import both make every path build
     with a named reason, and each has a test.

   *Done when:*
   - mutating the real `_augment_resolved` to raise fails the timeout test; at `cf28a05db` that
     mutation passes it (this Done-when is `mutation-after` by construction);
   - the probed-layout test fails when the versioned nested probe is dropped from the error;
   - the `test-compile` evidence test fails when the `test-compile` token is removed from the landing
     template. This clause **holds at** `cf28a05db` (the token is present and the old test passed on
     the `{sha}` text alone), so it is `mutation-after` by construction;
   - an unavailable glob helper reports `glob helper unavailable: ImportError` and every path builds
     (this behaviour holds at `cf28a05db` and is untested there: the test is new);
   - a non-`ImportError` exception at import reports a named reason and every path builds; at
     `cf28a05db` it propagates.

3. **The lane refuses to start when the executor maps `runbook_lane` older than the lane text it read.**
   - Skills: pm-plugin-development:plugin-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-implementer
   - §0 states a check that runs BEFORE `resolve`: the version the executor maps
     `plan-marshall:runbook-lane:runbook_lane` to is compared with the version of the lane text the run
     read, and a mismatch stops the run as **blocked** naming both versions and the remedy (regenerate the
     executor). The check cannot live inside `resolve`: a stale executor runs the stale `resolve`, which is
     the code that lacks the check, so the guard is a step of the lane text, which the harness loads from
     the installed plugin and so is current when the executor is not.
   - The comparison reads the executor's mapping with the shared `plugin_registry` reader; it does not
     parse the executor by hand and does not shell out to `grep`.
   - A comparison that cannot be made (executor unreadable, lane text version not derivable) is reported
     as **could not check** and asks the operator; it is never read as "no skew".

   *Done when:* each of these fails at `cf28a05db`:
   - a doc test asserts §0 contains the skew check before the `resolve` call and that it names the
     blocked outcome and the regenerate remedy;
   - a unit test of the comparison returns `skew` for an executor mapping older than the lane text,
     `match` for equal versions and `could_not_check` for an unreadable executor, and the last is not
     the same value as `match`.

   Source: consumer-epic evidence in `inbox/pm-mcp-core-m2-m4-001` (its title says five opencode landings,
   its body details four, in which the lane ran against an executor older than the registry:
   `unknown_verb` for `build-classify`, a `resolve`
   without `base_branch`, `build_timeout_seconds` and `guard_log`, and Maven phase names that Maven
   rejected; in one the Maven gates never ran). The cause named there is stale executors, not a lane bug;
   `resolve` at `d7e351419` returns all three keys and `build-classify` exists.

4. **The build-gate text and the `resolve` PLAN-LB-78 shipped state only what is true.** (Folded from
   `landings/PLAN-LB-78.md` § Code defects, #1834 at `9a23d41e9`.)
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester, pm-documents:ref-documentation
   - Persona: plan-marshall:persona-implementer
   - **The routed build has an executor to run (high).** `SKILL.md` §2 and §4 say a routed job re-runs the
     worktree's own `.plan/execute-script.py`, "which worktree creation supplies"; worktree creation supplies
     none (`git-workflow.py` `_materialize_local_dir` docstring: the executor is moved in by `prepare_execute`,
     which the lane never runs), and the routing submits without checking, so the job ends terminal (exit 2)
     and no fallback runs. Decide at outline whether the lane materialises the executor in the worktree or
     checks for it before the first routed build and records `executor_absent_from_worktree` with the build
     run in-process; record why. The sentence and the doc test that pins it (`test_skill_does_not_forbid_the_build_daemon`)
     are rewritten to what is true.
   - **The text states routing once.** `SKILL.md` §4 (auto "runs in-process otherwise") and §2 (a down setup may
     still route, the build preflights again) agree; §2 no longer prescribes `--execution-mode in_process` where
     §2 and §4 say default routing; "Shell timeout, in-process fallback only" states that a routed build also
     holds the call and what the lane does on a harness whose default shell timeout is shorter; the merge gate's
     "`verify` green on the current head" names what the lane does when the project publishes no `verify` or the
     routed `verify` hit the daemon's bound.
   - **`resolve` is exact about what it could not do.** A project that publishes only one gate canonical is
     accepted and the missing one is named in the result; the unresolvable error returns `canonicals` as a list;
     a missing or broken architecture reports as such and not as `build_command_unresolvable`; the Maven `split`
     is empty or absent where it cannot be shorter than `verify`, and §4 says so; the relative worktree path is
     absolute in the routed command, or the routing is shown to resolve it (verify first: the only relative
     routed job failed earlier on the missing executor).
   - **The runtime stamp is not silently degraded.** `resolve` carries the collector's `model_omission_reason`
     as `runtime_stamp_reason` (OpenCode with no session id today returns `unknown` with no reason); on Claude
     and Antigravity `resolve` passes the model and effort the run reports itself to the seam
     (`collect_runtime_info` accepts them, `runtime_info.py` L605-616; PLAN-LB-49 (#1833) moved this file by about −76 lines, so re-read the reference) or states why it cannot; decide at outline
     and record why, because this is the operator ruling whether a self-report may stand in for a measurement.
   - **The lane text is re-read after every point the harness drops it.** §0a states that the lane text is
     re-read in full after a compaction, a server restart and an idle gap, and records the re-read in the
     progress file with its timestamp. The run that shipped PLAN-LB-78 loaded the text once and worked 14 hours
     past its last full load; the rule is lane text, so a doc test asserts it.
   - **Landing honesty.** §8 states that the rule check counts the shell file operations the run itself issued
     (read-class included, not only the guard's refusals), every routed build including a failed one, and every
     operator message including a model switch, and that a count taken from the guard log alone is labelled as
     such. The refusals are attributed by the run's own session tree and never by a time window: PLAN-LB-79's
     section 7 listed a refusal that belongs to the PLAN-LB-49 run (`landings/PLAN-LB-79.md` § Report
     Contradictions 1), and it also reported no server restart although one killed a self-review round
     (the round was re-run), so §8 requires every restart, killed sub-agent and re-dispatch to be listed.

   *Done when:* each of these fails at `9a23d41e9`:
   - a doc test asserts `SKILL.md` no longer says worktree creation supplies the executor and states the check
     (or the materialisation) before the first routed build, and a unit test shows a routed build whose
     executor is absent is recorded and run in-process rather than failing terminal;
   - a doc test asserts §2 and §4 do not contradict each other on routing and that §4 states the routed-build
     shell-timeout rule and the no-`verify` merge-gate rule;
   - `resolve` for a project publishing only `quality-gate` (and one publishing only `verify`) succeeds and names the
     missing canonical; the unresolvable error's `canonicals` is a list; a missing architecture does not return
     `build_command_unresolvable`;
   - `resolve` for OpenCode with no `OPENCODE_SESSION_ID` returns `runtime_stamp_reason`;
   - a doc test asserts §0a requires the full re-read after a compaction, a restart and an idle gap, and the
     progress template carries a slot for it;
   - a doc test asserts §8's rule-check paragraph names read-class shell file operations, failed routed builds,
     operator model switches, and every restart or killed sub-agent with its re-dispatch.

   Split guard: four deliverables, all in the runbook lane's text, `resolve` and its tests. Proceeding unsplit:
   D4 shares D1's sections and the executor-skew guard D3 adds sits in §0 beside them.

## Claim Labels

- OBSERVED: the branch row says the prefix set is closed and that `working_prefixes` is "its only extension, never a replacement", and in the same sentence that the prefix "must be one the project's configured `working_prefixes` declares" — `marketplace/bundles/plan-marshall/skills/runbook-lane/SKILL.md` L80.
- OBSERVED: the §0a template line `D{n} test: … — failed before fix ({evidence}), passed after` has no `order` slot — `SKILL.md` L139.
- OBSERVED: §1 and §3 step 2 mandate test-first while §6 and §8 accept `mutation-after` and `none` — `SKILL.md` L162-163, L300-301, L382-386, L515-522 (audit of PLAN-LB-72).
- OBSERVED: §7 excludes a summary comment from "qualifying review", while a clean CodeRabbit review is published only as a marker-bearing summary comment — `SKILL.md` L423-425 and `marketplace/bundles/plan-marshall/skills/automatic-review/standards/coderabbit.md` L311-316.
- OBSERVED: the timeout test replaces `_cmd_client._augment_resolved` with a lambda — `test/plan-marshall/runbook-lane/test_runbook_lane.py` L1363-1367.
- OBSERVED: `ci pr reviews` returned `review_count: 0` on PR #1819 although both required bots reviewed the merge head through comments (orchestrator check, `landings/PLAN-LB-72.md`).
- HYPOTHESIS: the Guide issue comments of cuioss-review-bot are an adequate head-coverage signal for that reviewer and need no change — confirm at `automatic-review/standards/cuioss-review-bot.md` § the reviewer's published artifacts (verify-at-outline).
- OBSERVED: the lane's "Immediately before enqueue" step tells the run to `git -C {worktree} merge origin/{base_branch}` with no message and no trailer, while the Commit trailer rule requires every commit to end with `{commit_trailer}`; the merge commits `06610bd71` (PLAN-LB-77) and `092bc1a38` (PLAN-LB-48) carry none (`git log --format='%(trailers)'`).
- OBSERVED: at `d7e351419` `runbook_lane.py` `build-classify` (L926) and a `resolve` that returns `build_timeout_seconds`, `base_branch` and `guard_log` (L998-1005) exist; the consumer-epic landings that met `unknown_verb` and a short `resolve` therefore ran an older lane than the text they read (orchestrator read of `runbook_lane.py`; the consumer-side executor mapping itself `0.1.1961` against a registry pin `0.1.1977` is the plan-reported figure of `inbox/pm-mcp-core-m2-m4-001`, not observed here).
- OBSERVED: `cleanup restart-check` already reports registry-versus-executor parity (`_registry_parity_signal`, `orchestrator.py` L5512-5575: `not_ready` when the registry is behind, `indeterminate` with a regenerate hint when it is ahead), so the sibling's `registry_parity: indeterminate` is that arm's answer for a registry ahead of the executor. The gap is that nothing in the lane's start consults it.
- HYPOTHESIS: the executor's mapping for `plan-marshall:runbook-lane:runbook_lane` can be read for its version by `plugin_registry.read_executor_version` or an adjacent reader — confirm at `script-shared` `plugin_registry` before D3 names a seam; if only the executor's own `MARSHALL_VERSION` is readable, compare that and say so (verify-at-outline).
- OBSERVED: `git-workflow.py` `_materialize_local_dir` creates `worktree/.plan/local` and nothing else; the executor is moved in by `prepare_execute` (`marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git-workflow.py` L1912-1928, read by the orchestrator at `9a23d41e9`), while `runbook-lane/SKILL.md` L304-305 and L344-345 say worktree creation supplies it.
- OBSERVED: the PLAN-LB-78 run's first routed build (job `57636f43`, 2026-10-21T16:01:06Z) ended `status: error`, exit 2, "can't open file '<worktree>/.plan/execute-script.py'", with no in-process fallback (landing analysis of PLAN-LB-78, from the OpenCode session store read by the corroboration).
- OBSERVED: the same run loaded the lane text at 15:53:55Z, re-read it in full once (17:08:28Z, after a compaction), and not after the third compaction, a server restart or a 524-minute idle gap; it ran 14 h 10 min past its last full load (landing analysis of PLAN-LB-78, from the session store).
- OBSERVED: the Maven root publishes no `module-tests`/`test-compile` and its `quality-gate` is `verify -Ppre-commit` (`_maven_cmd_discover.py` L925, L935-943, L956-960, from the corroboration, not re-read), so the lane's Maven `split` cannot be shorter than `verify`.
- HYPOTHESIS: `_route_to_daemon` submits a routed job without checking that the executor exists (`script-shared/scripts/build/_build_execute_factory.py` L909-933) — confirm at outline, because the fix is either a check in the lane or a check in the routing (verify-at-outline) (D4).
- HYPOTHESIS: `resolve` returns the worktree as a relative path that the routing forwards unchanged (`runbook_lane.py` `worktree = f'.plan/local/worktrees/{plan_id}'`, `_build_execute_factory.py` L918) — unverified, the only relative routed job failed earlier (verify-at-outline) (D4).
- Verify-first clause: confirm the marker text CodeRabbit's clean-review summary carries (`<!-- recent_review_start -->` and the `sourceCommitId` / `coveredCommitId` / `kind` fields) against a live comment before D1 names them, and record the source.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/runbook-lane/SKILL.md` — the branch row, §0a, §1, §2, §3, §4, §6, §7, §8 (D1, D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/runbook-lane/scripts/runbook_lane.py` — the glob-helper import guard (D2); `_resolve_build`, `_resolve_runtime_stamp`, the worktree path (D4)
- OBSERVED: `test/plan-marshall/runbook-lane/test_runbook_lane.py` — the doc tests of D1, D3 and D4 and the tests of D2 and D4
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/coderabbit.md` — read only, the marker (verify-at-outline) (D1)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/plugin_registry.py` — read only unless the mapping reader is missing (verify-at-outline) (D3)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_execute_factory.py` — only if the missing-executor check belongs in the routing and not the lane (verify-at-outline) (D4)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git-workflow.py` — read only, unless the lane materialises the executor through it (verify-at-outline) (D4)

## Dependencies and Sequencing

- Depends on: PLAN-LB-72 (shipped, `cf28a05db`).
- Overlaps with: PLAN-LB-78 (shipped, `9a23d41e9`) on `runbook-lane/SKILL.md`, `runbook_lane.py` and `test_runbook_lane.py`; this plan is the fix-forward for it and now unblocked. Re-read the line references at outline: #1834 moved every section D1 and D4 name.
- Adjacent to:
  - PLAN-LB-69 D4 takes the Done-when authoring rule ("fails at" versus "holds at") on the
    orchestrator side; this plan does not touch it.
  - The classifier's architecture fallback can still say `docs-only` for a path a reusable CI workflow
    would build. That is an operator ruling, not a deliverable here.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-73-lb-72-completion.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
