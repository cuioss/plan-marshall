envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-04-01
epic=truthful-signals
kind=candidate-lesson
created=2026-09-05T07:51:51Z

component=pm-plugin-development:ext-self-review-plan-marshall
category=improvement

# Self-review should treat "same refactor applied to N-1 of N sibling sites" as a first-class candidate, including for control-flow edits

Relayed from Token-Sheriff epic `lessons-handling-26-09-04-01`, PLAN-01
(`pre-commit-gate-truthfulness`, merged as PR #713 / `29d9f6c5`). This is the
plan-marshall half of a candidate lesson whose other half (a Java review rule) stayed
in the originating repository.

## What happened

The plan narrowed two broad catch clauses in one class, in one commit. At the first
site the cleanup that the old broad catch had been performing was correctly hoisted
into a `finally` block first, so it still ran on the newly-escaping exception types.
At the second site the same narrowing was applied WITHOUT carrying the pattern across
— leaving a retained-credential exposure on a fail-closed path, the path whose entire
purpose is to guarantee the credential is gone.

A review bot caught it. The run's own pre-submission self-review did not.

## Why self-review structurally could not catch it, and what it COULD catch

This is the durable half, and it is a statement about the surfacer's reach rather than
a complaint about its diligence.

Pre-submission self-review reaches **internal consistency between statements present in
the diff**. The defect's consequence was behaviour under an input the diff does not
contain (a `RuntimeException` the new catch no longer intercepts). No amount of reading
the hunk harder finds it, and asking the surfacer to find it is asking for a different
kind of analysis than the one it performs.

But the reachable signal is right there at a different altitude: **a structural pattern
applied at one site and not at its sibling site in the same change**. "Hoist cleanup to
`finally`, then narrow" was applied once and omitted once, in the same file, in the
same commit. That asymmetry IS visible in the diff, and it is the shape a surfacer can
flag even though the runtime consequence is not.

## Suggested remedy

`ext-self-review-plan-marshall` already surfaces symmetric-pair candidates for
functions. Extend that detector's notion of a "sibling site" to CONTROL-FLOW edits:
two `catch` clauses in the same class, two `finally` blocks, two guard clauses, two
error paths — where a change applied to some but not all members of the set is the
candidate, regardless of whether the members are functions.

The general framing: the detector should ask "what set does this edit belong to, and
did every member of the set get it?" — not "is this function's pair consistent".
