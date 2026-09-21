envelope_version=1
sender_type=plan
sender_id=implement-plan-08-slug-semantics-model-compliance
epic=tooling-truthfulness
kind=candidate-lesson
created=2026-09-14T08:10:38Z

# Review-caught defects fixed in-run on PR #1487 (6 findings)

## Context

CodeRabbit filed 7 actionable findings across three review rounds on PR #1487
(non-string slug TypeError, non-list plans AttributeError, admission-gate bypass in
decompose Step 5, unguarded plans consumers, detector asymmetry, refusal
side effects, non-canonical byte rewrite). All 6 finding records remediated in-run
(resolution fixed across loop-back iterations at 4563a61, 899473de, 2942c7a);
85.7% resolved-as-fixed with zero false positives.

## Root cause

Slipped-then-caught: the defects passed the in-house gates (quality-gate green at
4563a61) and were caught only by review-bot iteration.

## Proposed action

No fix proposed at plan level; the per-finding fixes already landed. Recorded as the
slipped-then-caught class lessons-capture exists to capture, for the orchestrator to
weigh (e.g. whether a gate could have covered the refusal-persistence shape).

## Evidence

- manage-findings list --type pr-comment --resolution fixed: filtered_count 6 (hashes 3b4ffe, bddf62, eb1fad, 78b8b3, d0fb4a, 97ccca)
- review-retrospective.md: 1 reviewer measured, 7 actionable, 85.7% fixed
- review-versus-gate delta verdict: excluded (gate_tree_unsubstantiated — mixed reviewed heads)
