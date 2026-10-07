envelope_version=1
sender_type=plan
sender_id=exploration-share-is-unmeasured
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T07:28:12Z

component=plan-marshall:plan-retrospective
category=bug
title=check-artifact-consistency reports 0% recall as a confident FAIL when the worktree is gone, instead of reporting unknown

# A coverage check reported 0% because its input was unavailable — the exact inversion of the exclusion rule the same plan shipped

## Observation

Running the retrospective on plan `exploration-share-is-unmeasured` after merge, `check-artifact-consistency` returned:

```
affected_files_recall,fail,Recall 0% below 70% threshold
details.affected_files_recall: declared: 21, found: 0, recall_pct: 0.0
```

The true recall, measured against the actual merge commit `bef5b29d`, is **95.2%** — 20 of the 21 declared paths landed. The realized footprint is 22 files; one declared path was not touched (`test/plan-marshall/platform-runtime/test__claude_runtime_impl.py`) and two undeclared SKILL.md files were.

The 0% is a pure **measurement artifact**. The aspect derives the footprint live from the plan's worktree (`{base}...HEAD` ∪ porcelain). `branch-cleanup` had already removed the worktree, so the derivation returned an empty set — and **empty was reported as zero**, with a `fail` verdict and a threshold comparison, exactly as if the plan had genuinely shipped none of its declared files.

## Why this is the sharpest instance

This plan's deliverable D3 is *the rule that prevents this*: absent counters **exclude** a plan from the exploration-share corpus and are never counted as zero exploration. The team implemented that rule correctly, used it to produce an honest `not-yet-measurable` outcome for D5, and explicitly documented that they refused to manufacture a verdict from missing data.

One aspect over, in the retrospective that audits that very plan, the identical failure mode is live and unfixed.

## Rule

- **Footprint derivation must be tri-state**: `derived` / `genuinely-empty` / `input-unavailable`. Only the middle state may produce a `0%` verdict. `input-unavailable` must emit `status: skip` with a reason token — never a threshold comparison.
- A coverage check whose input source can disappear (a worktree removed at branch-cleanup, an archived plan, a pruned ref) MUST detect the disappearance rather than infer content from silence.
- **Grade-to-the-floor does not mean grade-the-absence.** A floor of zero over an unread population is not a conservative reading; it is a fabricated one, and it is louder than the truth.

## Practical trigger

Every retrospective invoked *after* `branch-cleanup` — which is the normal ordering when the retrospective step sits late in the finalize sequence, and the universal case for any post-merge or orchestrator-driven retrospective run — hits this. The 0%-recall FAIL is therefore not rare; it is the default outcome, which also means the signal has been carrying no information for some time.

## Residue

Not fixed. Owed: the tri-state derivation plus a fallback to the merge commit / PR base when the worktree is absent (the data IS recoverable — `git diff --name-only bef5b29d^ bef5b29d` produced the true 22-file footprint in one call).
