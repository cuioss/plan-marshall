envelope_version=1
sender_type=plan
sender_id=plan-07-session-identity
epic=finalize-machinery
kind=candidate-lesson
created=2026-09-18T20:15:48Z

# Token/worked figures unmeasured on transcript-less targets leave efficiency blind

## Context

The plan-07-session-identity retrospective reconciled metrics to totals 0/6 for tokens, tool uses, and worked time, with wall-only measurement (1h52m over 5 closed phases). On the OpenCode target enrichment is a documented no-op, so the efficiency aspect could score no token anchor.

## Root cause

An unenriched total reads as zero unless the gap flag publishes its population; the enrich-skip gap flag this plan shipped is the structural fix, but no lesson names the unmeasured-vs-zero read for future retrospectives.

## Proposed action

Keep the gap-flag discipline this plan introduced; consider a lessons entry only if the corpus lacks one naming the unmeasured-vs-zero read.

## Evidence

- aspect: plan_efficiency — totals_tokens 0 with population_count 0/6, wall 1h52m at 5/6
- plan: plan-07-session-identity, PR #1530
