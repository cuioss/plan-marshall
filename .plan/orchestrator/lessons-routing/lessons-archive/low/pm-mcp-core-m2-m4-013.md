envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-10T15:10:01Z

# Candidate lesson: Route every ad-hoc hand-off through the level-resolve call

- Component: plan-marshall:plan-marshall
- Category: bug
- Origin: pm-mcp-core lessons store, lesson 2026-10-10-07-021 (created 2026-10-10), epic pm-mcp-core-m2-m4

## Source

Retrospective of plan primitive-spi-and-validators (logging gaps, hand-off audit, plan efficiency). Read from the work log and the decision log.

## Context

After merge consent the orchestrator handed the update of the documentation pull request to a subagent. The work log shows it only through the leaf's own lines: two `[SKILL] (plan-marshall:execution-context.documentation-pr-update)` lines at 06:40:52Z and 06:40:53Z and a `[STATUS] ... Complete` line at 06:45:20Z. There is no `[DISPATCH]` line for it, no `effort resolve-target` record in the decision log between 06:34:19Z and 06:47:38Z, and no row in `work/metrics-dispatch-boundaries-6-finalize.toon`.

## Root cause

The hand-off was issued with inline instructions and without the resolve call that carries `--workflow`, `--plan-id` and `--caller`. That call is the only writer of both audit surfaces, so a hand-off that skips it is absent from both at once.

## Evidence

- Work log lines at 06:40:52Z, 06:40:53Z, 06:45:20Z; decision log 72429e records the result (pull request 20) but no resolve.
- The hand-off audit of this plan reports 0 findings over 28 resolve records and 28 hand-off lines. It could not see this hand-off; the clean result is a lower bound.
- The 6-finalize accumulator exceeds the boundary rows by 884545 tokens; 196785 of that is not explained by the loop-back execute steps and fits this hand-off. That is a fit, not a reading.
- The hand-off ran while the merge lock was held (lock 06:41:07Z to 06:47:21Z).

## Not established

Which level the subagent ran at, and whether it was a plain execution-context envelope: nothing recorded it.

## Proposed action

An ad-hoc hand-off inside a phase resolves its level through `effort resolve-target` with the dispatch context like any step, using the calling phase's default slot, and records a boundary row on return. A phase-6 hand-off without a resolve record should be refused by the orchestrator's own checklist, since the audit cannot find it afterwards.
