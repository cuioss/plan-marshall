envelope_version=1
sender_type=plan
sender_id=gates-do-not-refire-over-the-loop-back-diff
epic=truthful-signals
kind=candidate-lesson
created=2026-08-01T19:10:25Z

component=plan-marshall:build-server-client
category=bug

# Routed build wrapper reports duration_seconds=0 / exit_code=-1 on the outer TOON while the inner job log records a 330s timeout

## Observation

During PLAN-TRUTH-001 a routed build produced two disagreeing records of the same run:

| Surface | `status` | `duration_seconds` | `exit_code` |
|---------|----------|:------------------:|:-----------:|
| Outer wrapper TOON | (failure) | **0** | **-1** |
| Inner job log | `timeout` | **330** | — |

The outer TOON **loses the real duration** and reads as an *instant* failure. An instant failure and a 5.5-minute timeout call for opposite responses: the first says "the invocation was rejected, check the command"; the second says "the work ran and did not finish, check the budget or the workload".

## Why this belongs to `truthful-signals`

The outer status is the surface an operator and an automated consumer actually read, and it is **the lossy one**. The truthful record exists — it is just one layer down and nobody is looking at it. `duration_seconds: 0` is not "unknown duration"; it is a **confident, specific, wrong** number, which is worse than an absent field.

`exit_code: -1` compounds it by colliding with the generic "no exit code available" sentinel, so a genuine timeout is indistinguishable from a harness-level failure to launch.

## Known-adjacent prior art in this corpus

The corpus already carries **both polarities** of this defect:

- a GREEN verify reported as `timeout/-1` (lesson 2026-07-27-00-001);
- a routed build whose outer status must never be trusted, with implausible duration as the tell.

This sighting is the third, and the first where the inner truth was confirmed present and correct at the same moment the outer surface was wrong. That makes it a **propagation** bug, not a measurement bug — the data is captured, then discarded on the way out.

## Suggested shape of the fix

Propagate the inner job record's `status` and `duration_seconds` onto the outer TOON verbatim. Where the outer layer genuinely has no measurement, emit **absent/null**, never `0`. Reserve `exit_code: -1` for "process never started" and give timeout its own discriminator.

## Not actioned

Out of PLAN-TRUTH-001's scope. Handed to the epic.
