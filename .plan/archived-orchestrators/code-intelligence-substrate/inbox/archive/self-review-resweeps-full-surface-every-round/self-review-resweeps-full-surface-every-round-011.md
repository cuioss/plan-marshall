envelope_version=1
sender_type=plan
sender_id=self-review-resweeps-full-surface-every-round
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-09T03:24:36Z

component=plan-marshall:plan-retrospective
category=improvement
bundle=plan-marshall
confidence=medium
source_plan=self-review-resweeps-full-surface-every-round
source_aspects=artifact-consistency,routing-decisions,llm-to-script-opportunities

# Resolve a landed plan's footprint from its merge commit when the worktree is gone

`check-artifact-consistency` on the merged PR #1126 reported:

```toon
  affected_files_recall,inconclusive,"Plan footprint could not be resolved (no live worktree diff and no modified_files key) - recall is unmeasurable, not 0%"
  affected_files_exact_match,inconclusive,"...the comparison substantiates no verdict"
```

Both of the aspect's coverage checks — the deterministic *declared-vs-achieved* half of the thoroughness dial — are unavailable, because its only two footprint sources are (a) a live worktree diff and (b) the retired `references.modified_files` key. A post-merge retrospective has neither: `branch-cleanup` removed the worktree, and the key no longer exists on current plans.

`check-routing-decisions` has the same hole from the other side: its `mis_prune` predicates need `--diff-file`, and nothing in the retrospective produces one.

## Root cause

The footprint resolver assumes it runs *before* branch-cleanup. The retrospective runs at order 995 — **after** it.

## Solution

Add a third fallback: resolve the footprint from the plan's landing commit. `git show --name-only --pretty=format: {merge_sha}` against a squash merge yields the exact set (verified: it returned the 19 paths for `72982d3d4`), and the SHA is recoverable from the `branch-cleanup` step record or the PR. Feed the same resolved list to `check-routing-decisions --diff-file` so both aspects recover together.

## Impact

Every orchestrated finalize runs `plan-retrospective` after `branch-cleanup`, so **every post-merge retrospective loses both coverage checks**. This one recovered the footprint by hand and found the numbers worth having: 19 realized paths against 14 declared in `references.affected_files` — a 5-path under-declaration whose 3 non-architecture members are real test modules the plan's own change forced.

That under-declaration is the recurring `affected_files` archetype, and it is exactly what the recall check exists to measure. Today the check reports `inconclusive` on precisely the runs where the answer is knowable and useful.

Filed `medium` rather than `high`: the fix direction is clear and verified, but the SHA-recovery seam (which step record carries the landing SHA, and what happens on a non-squash merge) has not been designed.
