envelope_version=1
sender_type=plan
sender_id=spec-corpus-review-and-cleanup-entry-point
epic=truthful-signals
kind=candidate-lesson
created=2026-08-22T16:16:35Z

component=plan-marshall:phase-6-finalize
category=bug
confidence=high
source_plan=spec-corpus-review-and-cleanup-entry-point
source_aspects=request_result_alignment,chat_history_analysis,plan_efficiency

# Scope added after the outline never propagates back into references.affected_files

## Context

Mid-finalize, the operator was asked how to disposition finding `5b1178`, which was blocking the finalize boundary, and chose "Fix it in this plan" (declared cost: +1 execute cycle, +3 orchestrator-tier builds, finalize delayed). That decision created deliverable 9, *Make the architecture-hints reader reachable at phase-3-outline for `use_worktree` plans*, whose two declared files are:

- `marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/manage-solution-outline.py`
- `test/plan-marshall/manage-solution-outline/test_get_module_context.py`

Both files are in the solution outline, both are in the tasks, and both are in the landing. Neither is in `references.json`.

The resulting divergence, measured against the realized 16-file landing footprint:

| Direction | Count | Paths |
|-----------|------:|-------|
| Outline declared, absent from `references` | 2 | deliverable 9's two files |
| In `references`, absent from the landing | 1 | `manage-status/SKILL.md` (declared `intent: read` — a read can never appear in a diff) |
| In the landing, absent from `references` | 3 | deliverable 9's two files, plus `manage-solution-outline/SKILL.md` |

`references.affected_files` recall against the actual landing is 13/16 = **81.25%**.

## Root cause

`references.affected_files` is written once, early, and is never reconciled against the outline afterwards. Scope that arrives *after* that write — which is exactly what a finalize-time fix-in-plan disposition produces — has no path back into it. A second, smaller defect rides along: the list does not distinguish declared intent, so a `read`-intent path sits in it indistinguishable from a mutation-intent one and permanently depresses any recall measured against a diff.

## Proposed action

1. Make the fix-in-plan disposition path write its new deliverable's mutation-intent files back into `references.affected_files`. The data is already structured — `manage-solution-outline list-deliverables` emits per-path `intent` — so the write-back is a set union over machine-readable input, not a judgement.
2. Either exclude `intent: read` paths from `affected_files`, or carry the intent alongside each path so consumers can filter. A path the plan declared it would only read must not be counted as an expected modification.
3. Consider a deterministic reconcile verb that set-diffs `references.affected_files` against the union of every deliverable's declared paths, partitioned by intent, and reports the three-way divergence above. That check would have caught this at plan time; instead it took a hand comparison during the retrospective.

## Evidence

- aspect: request_result_alignment — `references_recall_vs_landing_pct: 81.25`; `declared_union_not_in_references[2]`, `references_not_in_landing[1]`, `landing_not_in_references[3]`
- aspect: chat_history_analysis — the operator gate `"Finding 5b1178 blocks the finalize boundary"` → `"Fix it in this plan"` is the direct cause of deliverable 9
- aspect: plan_efficiency — the metrics `files_modified` denominator persisted as **14** (the declared list) rather than the realized **16**, so every per-file ratio in the efficiency report is overstated by roughly 14%
- corroborating: `manage-solution-outline/SKILL.md` was modified with no declaring deliverable at all — the documentation half of deliverable 9 arrived undeclared even in the outline
