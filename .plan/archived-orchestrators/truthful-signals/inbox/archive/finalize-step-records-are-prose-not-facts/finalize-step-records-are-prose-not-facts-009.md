envelope_version=1
sender_type=plan
sender_id=finalize-step-records-are-prose-not-facts
epic=truthful-signals
kind=candidate-lesson
created=2026-08-02T12:18:10Z

component=plan-marshall:plan-retrospective
category=bug
confidence=high
source_plan=finalize-step-records-are-prose-not-facts
source_pr=1076
source_aspects=artifact_consistency,request_result_alignment,routing_decisions

# affected_files_recall reports 0% as a coverage failure when the footprint source is gone

## Context

`check-artifact-consistency` returned:

```
affected_files_recall,fail,Recall 0% below 70% threshold
details.affected_files_recall: declared: 12, found: 0, recall_pct: 0.0
```

with all 10 change-intent declared paths listed under `missing[]`.

The true recall is 11 of 12. Deriving the footprint by hand from the landed merge (`git diff --name-only b5477589c a83d575cc`) yields 12 files, 11 of which are declared; the twelfth declared path (`_cmd_assert_step_recorded.py`) was declared `intent: read` and correctly did not change.

`check-routing-decisions` has the same dependency and was only able to run because a footprint file was supplied by hand.

## Root cause

`plan-retrospective` carries `order: 995` and runs after `branch-cleanup`, which removes the worktree. The footprint is derived live from the worktree (`{base}...HEAD` union porcelain), with a fallback only to the legacy `references.modified_files` key that no longer exists for current plans. With the worktree gone and no legacy key, the derivation yields the empty set — and the check divides by the declared count and reports 0%.

The failure mode is not the 0% itself. It is that **measurement absence is rendered as a measured coverage failure**. `fail: Recall 0% below 70% threshold` and `skip: no footprint source available` are different claims, and only the second one is true. As written, this check can never pass for a worktree plan, so its green is unreachable and its red carries no information.

## Proposed action

1. Add a landed-merge fallback: when no worktree is on disk, resolve the PR number from `status.metadata.phase_steps["6-finalize"]["create-pr"].display_detail` (or from `handshakes.toon`) and derive the footprint from the merge commit range.
2. Emit a `footprint_source` field on the fragment (`worktree` / `landed_merge` / `unavailable`) so the report always states which source produced the number.
3. When the source is `unavailable`, emit `status: skip` with reason `footprint_source_unavailable` — never a `fail` with a computed percentage.
4. Exclude `intent: read` affected-file declarations from the recall denominator; a read-intent path that did not change is a correct outcome, not a miss.

## Evidence

- aspect: artifact_consistency — `affected_files_recall,fail,Recall 0% below 70% threshold`; `declared: 12, found: 0`
- aspect: request_result_alignment — realized footprint 12 files, 11 of 12 declared, derived from `git diff --name-only b5477589c a83d575cc`
- aspect: routing_decisions — required `--diff-file` to be supplied by hand for its prune-predicate re-evaluation to run at all
- `plan-retrospective/SKILL.md` frontmatter `order: 995`; `execution.toon` `phase_6.steps` places `plan-marshall:plan-retrospective` after `branch-cleanup`
