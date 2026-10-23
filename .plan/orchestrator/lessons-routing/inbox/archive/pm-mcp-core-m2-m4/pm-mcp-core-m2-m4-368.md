envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-19T17:28:52Z

# Reuse a HEAD-bound merge consent after a barrier loop-back at the same HEAD

- Source: plan-retrospective (chat-history-analysis, status.json phase_steps)
- Plan: plan-37-ported-primitive-tests (pm-mcp-core)
- Candidate component: plan-marshall:phase-6-finalize
- Category: improvement
- Confidence: high

## Context

The operator confirmed the merge of PR #106 at HEAD 1a4bd84. The pre-merge comment barrier then looped branch-cleanup back (a new sourcery budget notice to triage, accepted with no code change), and the operator was asked to confirm the merge a second time at the same HEAD, with nothing changed on main. branch-cleanup shows firing_count 3 (loop_back, then done). The merge-authorization record is already HEAD-bound and gap-class-bound.

## Root cause

The pre-merge confirmation gate asks again after a barrier loop-back even when the HEAD and gap class are unchanged and the loop-back produced no commit, so a valid HEAD-bound consent is not reused.

## Proposed action

When a barrier loop-back ends with no new commit and the stored merge authorization still matches HEAD and gap class, reuse it instead of asking again; ask only when HEAD moved or a new blocking gap appeared.

## Evidence

- aspect: chat-history-analysis -- two "Yes, merge" answers at HEAD 1a4bd84
- status.json: merge_authorizations.pre-merge-consent granted_over "second confirmation after the barrier loop-back"; branch-cleanup prior_firings loop_back then done
- caller note: the first merge-group run then failed on a Maven Central surefire resolution error; the second enqueue landed as ebcf128 (infrastructure, not part of this lesson)
