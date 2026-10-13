envelope_version=1
sender_type=plan
sender_id=lb-37-functional-review
epic=live-blockers
kind=candidate-lesson
created=2026-10-13T13:51:58Z

component=plan-marshall:plan-retrospective
category=bug
title=Resolve the realized footprint across every PR of a stacked landing

# Resolve the realized footprint across every PR of a stacked landing

## Context

lb-37-functional-review landed as a stack of five squash-merged PRs (#1754, #1755, #1757, #1758, #1759). The shared footprint resolver returned only the 31 paths of the last squash (PR #1759), so artifact-consistency reported recall 11% (21 of 195 declared files) and outline-vs-shipped reported 179 of 200 included assessments as unrealised, although the earlier parts shipped them.

## Root cause

The post-merge tiers of `_footprint_resolver.py` (merge-commit, PR-landing) read one merge commit / one PR number from references, which a stacked landing overwrites with the final part.

## Proposed action

Record every landed PR / merge commit of a plan (or the stack's first-parent range on main) and union their diffs in the resolver; until then, mark the footprint `partial` when the plan recorded more than one PR so coverage aspects report inconclusive instead of a confident low recall.

## Evidence

- aspect: artifact_consistency - affected_files_recall 10.8% (21/195), footprint_resolved true
- aspect: outline_vs_shipped - include_unrealised 179/200 over a 31-path footprint
- aspect: request_result_alignment - coverage verdicts had to fall back to task status
