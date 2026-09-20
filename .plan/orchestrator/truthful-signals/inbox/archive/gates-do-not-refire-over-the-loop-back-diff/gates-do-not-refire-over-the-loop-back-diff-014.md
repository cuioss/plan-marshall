envelope_version=1
sender_type=plan
sender_id=gates-do-not-refire-over-the-loop-back-diff
epic=truthful-signals
kind=candidate-lesson
created=2026-08-01T19:48:12Z

component=plan-marshall:plan-retrospective
category=bug

# The retrospective's coverage checks report confident verdicts over an input they cannot measure

## Observation

Three coupled defects in `plan-retrospective`'s declared-vs-achieved coverage aspect, all observed on PLAN-TRUTH-001's own retrospective run.

**1. `affected_files_recall` reported `fail` at 0% recall. The measured truth is 100%.**

The outline declared 17 affected files, of which 16 carry `intent: write-*` and one carries `intent: read`. All 16 write-intent files are in the merged diff of PR #1073. Recall over write-intent declarations is 16/16.

The check reported `Recall 0% below 70% threshold` and listed all 17 as missing.

**2. The failure is structural, not incidental.** `_resolve_footprint` has three tiers: live worktree diff, the legacy `references.modified_files` key, then empty. But `execution.toon` orders `plan-marshall:plan-retrospective` at position 17, **after** `branch-cleanup` at position 16 — and branch-cleanup removes the worktree. Tier 1 can therefore never resolve on a live plan. Tier 2 was removed from live plans with the ledger. Tier 3 (empty) is the **guaranteed** path for every live plan that reaches this aspect through the normal order.

So `affected_files_recall` is a permanently-red check whose redness carries zero information — and it fails **loudly**, at 0%, naming every declared file as missing.

**3. The sibling check in the same file already learned this lesson.** `check_affected_files_exact_match` carries this docstring:

> A both-empty comparison substantiates nothing — two empty sets are trivially equal whether the plan really touched no files or the parser and the footprint resolver both failed — so it reports `inconclusive` rather than a vacuous `pass`.

The two checks are declared peers ("strict variant, peer to recall", "both checks must agree on the source of truth"). One returns `inconclusive` on unmeasurable input. The other returns a confident `fail`.

**4. The deferral that was supposed to catch the drift is dead.** When `execution.toon` exists, `exact_match`'s `warn` is downgraded to `info` with the message `Set mismatch — deferred to manifest aspect (see check-manifest-consistency)`. `check-manifest-consistency.py` implements four rules — M1 docs-only, M2 early-terminate, M3 tests-only, M4 branch-cleanup-changes. **None of them compares the declared `Affected files` set against the actual diff.** The comparison is not deferred; it is dropped.

On this plan it dropped real drift: `standards/push.md` and `test/plan-marshall/phase-6-finalize/test_architecture_refresh.py` were both changed and neither was declared in any deliverable.

**5. The aspect it defers to is itself running on an empty diff.** SKILL.md's documented aspect-12 invocation is:

```
check-manifest-consistency run --plan-id {plan_id} --mode {live|archived} > work/fragment-manifest-decisions.toon
```

Neither `--diff-file` nor `--base-ref`. `load_diff_files` returns `([], 'unknown')` when `base_ref` is falsy — no error, no warning. The canonical-invocations block claims "`--base-ref` is required when `--diff-file` is absent", but argparse does not enforce it. So M1 and M3 evaluate `culprits = [p for p in [] if ...]` → `[]` → **`pass`**, with messages like `all 0 non-bookkeeping diff entries are docs-shaped`.

M4 was hardened against exactly this — it skips when `base_label == 'unknown' or raw_files_total == 0`, with the comment "the absence of changes is an artefact of missing diff input, not a real defect, so emitting a fail would be a false positive". M1, M2 and M3 were not.

## Root cause

The same asymmetry twice: one check in a sibling set was taught to distinguish *unmeasurable* from *measured-and-clean*, and its peers were left reporting a confident verdict over the same unmeasurable input. In both cases the hardened member's own docstring or comment states the reasoning that the peers needed.

The compounding is what makes it invisible: the loud false RED (recall 0%) is easy to dismiss as noise once you know the worktree is gone, the true signal is silently downgraded to `info`, and the aspect it points at both fails to implement the check and runs on an empty diff. Four layers, each of which alone would be noticed.

## Proposed action

1. Give `check_affected_files_recall` an `inconclusive` verdict for the `actual == set()` case, mirroring `check_affected_files_exact_match`. Distinguish "footprint resolved and nothing matched" from "footprint could not be resolved".
2. Add a fourth footprint tier: when the worktree is absent and `references.json` carries a `pr_number`, resolve from the merge commit. This makes the post-branch-cleanup position measurable rather than merely honest about being unmeasurable.
3. Either implement the declared-vs-actual set comparison in `check-manifest-consistency` (as rule M5), or delete the `deferred to manifest aspect` downgrade and let `exact_match` keep its `warn`. A deferral to a check that does not exist is worse than no deferral.
4. Make `--base-ref` genuinely required in argparse when `--diff-file` is absent, and give M1/M2/M3 the same missing-diff skip guard M4 already has.
5. Teach the bullet parser to read the `intent` field so `intent: read` declarations are excluded from the expected-to-be-modified set. On this plan that alone moves the declared denominator from 17 to 16.

## Evidence

- aspect: artifact_consistency — `affected_files_recall,fail,Recall 0% below 70% threshold`, `declared: 17, found: 0, recall_pct: 0.0`
- aspect: artifact_consistency — `affected_files_exact_match,info,Set mismatch — deferred to manifest aspect (see check-manifest-consistency)`
- aspect: manifest_decisions — `checks[5]` contains no declared-vs-actual comparison; `docs_only_diff,skip`, `early_terminate_diff,skip`, `tests_only_diff,skip`
- aspect: request_result_alignment — 16/16 write-intent declarations realized; 2 undeclared changes (`standards/push.md`, `test_architecture_refresh.py`)
- `execution.toon` `phase_6.steps` — `branch-cleanup` at index 15, `plan-marshall:plan-retrospective` at index 16
- `check-artifact-consistency.py:113-149` (`_resolve_footprint` three-tier), `:326-352` (`check_affected_files_exact_match` inconclusive branch)
- `check-manifest-consistency.py:143-182` (`load_diff_files` empty-on-missing-base-ref), `:345-384` (M4's skip guard)
