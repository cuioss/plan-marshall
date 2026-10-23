envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-10-23T08:24:25Z

# Finalize verification integrity: CI-failure triage contract, finding attribution, root-level guards

Severity: high. Bundle: **plan-marshall** (`verification-feedback`, `phase-6-finalize` ci-verify, `tools-integration-ci`, pre-push quality gate). Filed under RULING 2026-10-09 (a).

## Sources

- corpus `2026-10-11-16-001`, `2026-10-11-16-002`, `2026-10-11-16-003`

## Consolidated statement

Three defects in the CI/verification evidence path, each of which either blocks triage or lets a red build reach CI:

1. **Producer contract gap.** `phase-6-finalize/standards/ci-verify.md` dispatches `verification-feedback` with `producer: ci-verify-build` (and `ci-verify-policy`, …), but Step 1 of `plan-marshall/workflow/verification-feedback.md` accepts only `build-runner`, `sonar`, `pr-comment`, `plugin-doctor`, `pr-state`, `finalize-feedback`. The leaf returns `error: unknown_producer` and triages nothing; four `type: triage` findings were left for the orchestrator, which had to route the CI failure itself.
2. **Findings attributed to the wrong run, with empty log pointers.** Two CI runs failed at the same HEAD; ci-verify filed all four findings under the first run's artifact path, although two belonged to the other. In the same pass `ci checks status` returned empty `log_file` / `filtered_log_file` for every failing check, so the triage leaf had to fall back to `ci checks logs --job … --match …`.
3. **Root-level guards skipped before push.** `test/test_harness_shape_guards.py` sits at the root of `test/`, outside the `plan-marshall` module, so `module-tests plan-marshall` never runs it; the pre-push gate resolved `divergence_possible=false` and skipped its whole-tree run. CI then failed on rule R5 (runtime-derived `parametrize` without a guard). The same class recurred in a second plan (three new bindings, pre-push failed twice on the same rule) and in a third (stopped unmerged); a leaf had to run the R5 predicate through `python3 -c` because the build wrapper has no narrow form for root-level guards. A no-historical-prose violation in a doc edit was likewise caught only by the whole-tree test.

## What is asked

- Add the `ci-verify-*` producer family to the verification-feedback accept-set with its finding-type mapping, or dispatch an accepted producer with an explicit `finding_type`; add a contract test that every producer string a dispatcher names is in the workflow's accept-set.
- Key each ci-verify finding's `file_path` on the run id of its own check; populate `log_file` / `filtered_log_file` for failing checks, or report why not; add a two-run fixture test.
- Always include the root-level `test/*.py` shape and marketplace-wide guards in a scoped `module-tests` run (or unconditionally in the pre-push gate whenever a plan adds or edits test files); expose them as a selectable build target; record the excluded population so a scoped green run states what it did not cover.

## Evidence

As recorded by the senders. Not re-verified against HEAD in this run.
