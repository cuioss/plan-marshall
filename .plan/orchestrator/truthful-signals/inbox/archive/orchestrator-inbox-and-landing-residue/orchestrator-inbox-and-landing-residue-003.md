envelope_version=1
sender_type=plan
sender_id=orchestrator-inbox-and-landing-residue
epic=truthful-signals
kind=candidate-lesson
created=2026-08-24T16:52:47Z

component=plan-marshall:manage-references
category=bug
confidence=high
source_plan=orchestrator-inbox-and-landing-residue
source_aspects=request_result_alignment,artifact_consistency

# affected_files diverges from the landing in both directions

## Context

`references.affected_files` is documented by the request-result-alignment aspect as a diff ("`affected_files` is a diff, so a path the deliverable declared it would only read can never appear in it"). For this plan it is not a diff in either direction.

Declared (`references.affected_files`): 13 entries.
Landed (`git diff --name-only 9999f4d87 77db1a0d3`): 16 files.

**Declared but never landed (3):**

- `marketplace/bundles/plan-marshall/skills/persona-plan-orchestrator/standards/orchestration-model.md`
- `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/manage-execution-manifest.py`
- `test/plan-marshall/manage-execution-manifest/test_reconcile.py`

**Landed but never declared (6):**

- `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-finalize-step.md`
- `marketplace/bundles/plan-marshall/skills/extension-api/standards/marshal-json-reference.md`
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md`
- `marketplace/bundles/plan-marshall/skills/plan-marshall/standards/effort-roles.md`
- `marketplace/bundles/plan-marshall/skills/plan-orchestrator/SKILL.md`
- `marketplace/bundles/plan-marshall/skills/plan-orchestrator/workflow/analyze.md`

So the list is simultaneously **unsound** (names work that did not happen) and **incomplete** (misses work that did). Any consumer grading coverage from it both over-counts and under-counts, in a way no single number reveals.

The under-recording direction is a recurrence: the same archetype was previously observed at 19-recorded-vs-37-landed. This instance is 13-vs-16 with an additional 3 stale entries the earlier observation did not surface.

## Root cause

`affected_files` is written during outline/plan from declared intent and is not reconciled against the realized diff at any later point. Nothing in the lifecycle compares the two, so the divergence is never observable — and the two deliverables whose declared files never landed (D7 at 50% coverage, D9 at 33%) passed their tasks as `done` without that shortfall surfacing anywhere.

The divergence compounds the footprint gap: when the resolver cannot produce a realized footprint, `affected_files` is the legacy fallback tier, so a consumer that reaches that tier is grading against a list that is wrong in both directions and has no marker saying so.

## Proposed action

- Add `manage-references diff-footprint --plan-id --against {sha}` emitting `declared_not_landed[]` and `landed_not_declared[]` as two separate lists (the asymmetry is the signal; a single count hides it).
- Run it as part of the retrospective's artifact-consistency aspect and surface both directions in the report.
- Where `affected_files` is consumed as a realized-footprint fallback, label the tier on the output so a reader knows the figure came from a declaration and not from a diff.

## Evidence

- aspect: request_result_alignment — `footprint_oracle.note: "references.affected_files (13 entries) ... names 3 files the landing never touched and omits 6 files the landing did touch, so it is an aspiration list, not a diff"`
- aspect: request_result_alignment — deliverable 7 coverage 0.50, deliverable 9 coverage 0.33, both from declared mutation files that never landed
- `manage-references read` → `affected_files: 13 items`; `git diff --name-only 9999f4d87 77db1a0d3` → 16 files
