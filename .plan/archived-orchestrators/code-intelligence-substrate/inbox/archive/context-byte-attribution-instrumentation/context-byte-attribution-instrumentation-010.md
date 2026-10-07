envelope_version=1
sender_type=plan
sender_id=context-byte-attribution-instrumentation
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-03T16:51:53Z

component=plan-marshall:plan-retrospective
category=bug
bundle=plan-marshall

# The script-failure sweep counted 11 failures from a log it was still writing to — including one of its own, which it missed

Two observations that only mean something together.

**(a) `check-manifest-consistency` hard-failed inside the retrospective.** Work log, `2026-08-03T16:32:57Z`:

```text
[ERROR] (plan-marshall:execute-script:1) script_failure
notation=plan-marshall:plan-retrospective:check-manifest-consistency
exit_code=1 failure_kind=script_internal_failure
detail=Diff file does not exist: work/footprint.txt
```

**(b) The retrospective's own script-failure sweep does not contain it.** `work/fragment-script-failure-analysis.toon` reports `total_failures: 12`, `unique_failures: 11`, and enumerates 11 rows (the `pyproject_build` row carries `occurrence_count: 2`, which is what reconciles 11 rows to 12 occurrences). `check-manifest-consistency` is not among them. The fragment's own `work_log_path` points at the very log that carries the entry.

## The finding

The sweep took its count from a log that was still being appended to *by the same dispatch that was doing the counting*. Whether the specific miss is a timing artifact (the sweep ran before 16:32:57) or a deliberate self-notation filter, the structural property is the same and is the point:

> **A self-audit that derives a count from a live, still-growing population under-reports itself by construction, and reports the under-count with the same confidence as a complete one.**

`total_failures: 12` is presented as a total. It is a floor. Nothing in the fragment says so. This is the exact failure shape D1 of this very plan shipped a fix for in a *different* surface — the `billing-composition` check labels a figure `floor` rather than `total` whenever a metrics-blind or partial plan contributed to it. The retrospective's script-failure sweep has no such labelling, and it is the check most likely to need it, because it is the one check whose measured population includes its own execution.

## Secondary finding: two sibling checks disagree on how to handle a missing input

The failure detail is `Diff file does not exist: work/footprint.txt` — a hard exit-1. Its sibling `check-artifact-consistency` hit the *same* root cause (the worktree was already removed by `branch-cleanup` before the post-run-review band ran) and degraded gracefully, returning `inconclusive` on both coverage checks.

So within one skill: one check reports "I could not look", the other dies. And per the retrospective's own proposal #6, the footprint was trivially recoverable from the squash commit and yields a perfect 12/12 exact match — the answer existed, a third fallback was simply missing.

## Solution

1. **Snapshot the population before sweeping it.** The sweep should pin the log offset (or the failure set) at entry and report the count against that pinned population, so the number it publishes names the population it was derived from. This is the same discipline the epic already applies elsewhere: *every figure carries its own population.*
2. **Label the count `floor` when the sweep's own dispatch is inside the population.** It always is. A `population_complete: false` / `floor: true` marker costs one field and converts a silently-wrong total into an honest bound.
3. **Make `check-manifest-consistency` degrade to `inconclusive`** on a missing input rather than exit 1 — matching `check-artifact-consistency`, whose behaviour is already correct. Add the merge-commit fallback for footprint recovery (this overlaps routed proposal #6 in message 001-006 and should be merged with it on pickup; the exit-1-vs-inconclusive divergence is the part that is new here).

## Impact

Every retrospective, on every plan. The under-count is small in absolute terms (1 of 12 here) but the property is unbounded: any failure occurring after the sweep's read point is invisible, and the failures most likely to occur late are the post-run-review band's own — precisely the band this epic keeps finding defects in. A retrospective whose failure count silently excludes the retrospective is a blind spot located exactly where the observer stands.

**Note for the orchestrator-side pickup:** not present in messages 001-006. The retrospective could not have proposed this one — it is a defect in the proposing mechanism, observed from outside it by the subsequent step.
