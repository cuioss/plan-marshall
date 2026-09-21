envelope_version=1
sender_type=plan
sender_id=planning-lane-change-type-scope-execution-manifest
epic=truthful-signals
kind=candidate-lesson
created=2026-09-05T16:00:10Z

# Post-merge --base-ref origin/main yields an empty diff reported as diff_available true

component: plan-marshall:plan-retrospective
category: bug
confidence: high
source_plan: planning-lane-change-type-scope-execution-manifest
source_pr: 1399

## Context

Observed live while compiling this plan's retrospective, which ran on the main checkout after PR #1399 had already squash-merged as `d03ca621` and the worktree had been removed.

`plan-retrospective/SKILL.md` instructs: "Supply `--base-ref` whenever `--diff-file` is absent — it is how the script obtains a diff at all." Following that instruction:

```
check-manifest-consistency run --mode live --base-ref origin/main
```

returned `files_total: 0`, `files_kept: 0`, every `filtered_by_category` bucket zero — and alongside them `oracle_available: true`, `majority_discarded: false`, **`diff_available: true`**. It then emitted a confident `fail`:

> `branch_cleanup_changes,fail,"phase_6.steps includes branch-cleanup but the observed diff is empty — the footprint resolved to no changed path at all, so no implementation file changed"`

Re-running the identical command with `--diff-file` pointing at the 51 paths of the merge commit turned the same check into:

> `branch_cleanup_changes,pass,"branch-cleanup paired with 50 changed file(s) (1 of 51 supplied paths were filtered as bookkeeping before evaluation)"`

The plan modified 51 files. The `fail` was an artifact of the base ref, not a property of the plan.

## Root cause

On a merged plan, `origin/main..HEAD` is legitimately empty — the branch's content *is* main now. The script's own documented distinction is that "a supplied file that names nothing is a **resolved empty footprint**, not an absent one, and rules may pass on it". A post-merge `--base-ref` produces exactly that shape by accident: a genuinely resolved, genuinely empty diff that means "nothing to compare", not "this plan changed nothing".

`diff_available: true` is therefore true in the letter (a diff was obtained) and misleading in effect (the diff cannot answer the question). The rule then grades a plan that changed 51 files as having changed none, at `fail` severity, with no `indeterminate` branch reached.

The retrospective is the one caller for which this is the *normal* case: `plan-retrospective` runs at `order: 995`, after `branch-cleanup` has merged and removed the worktree, so a post-merge invocation is the default, not the edge.

## Proposed action

Add a merged-landing tier to the shared footprint resolver: when `status.metadata` or the landing record carries the squash-merge SHA, derive the footprint from that commit rather than from a `base_ref` range. `plan-retrospective/SKILL.md` should then stop advising `--base-ref` for its own aspects and let the resolver answer, as `check-artifact-consistency` already does (it resolved the footprint on this same run with no diff input at all).

Secondarily: when a `--base-ref` range resolves to zero paths *and* the plan's task/deliverable records assert modifications, report `indeterminate` with the reason rather than `fail`. A verdict over no evidence is not a clean result, and the script's own `--base-ref`-absent path already takes exactly that stance (`base: unknown`, every diff-fed rule `indeterminate`); the zero-path range should join it.

## Evidence

- aspect: manifest_decisions — `--base-ref origin/main` gave `files_total: 0`, `diff_available: true`, one `fail`; `--diff-file` with the merge commit gave `files_kept: 50`, zero findings
- aspect: artifact_consistency — the shared resolver independently reported `footprint_resolved: true` on the same run, so the capability exists and the `--base-ref` path bypasses it
- aspect: outline_vs_shipped, routing_decisions — both needed a hand-built `work/footprint.txt` on this run for the same reason
