envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-18T10:23:51Z

component=plan-marshall:phase-6-finalize
category=improvement
created=2026-10-18

# Scope a review fix to the broken invariant, not only to the cited line

## Context

In plan-20-job-runner the code review of SubprocessJobRunner looped back five times, and the operator granted two extra rounds after the loop-back budget was spent. Every round found a narrower case of the same invariant ("every path that removes a job from the running map settles it, and a cancel answered true is the cause that settles it"):

- a86981: a runtime exception while composing or starting the launch leaves the job running with no supervisor
- 94a78a: a failed post-spawn write drops the job from the running map without settling it
- 957198: supervise removes the job without settling when the parser or an earlier step throws
- a1a9fe (CodeRabbit, fixed by TASK-25): settleUnlaunched ignores a cancel that cancel() already answered true
- 207f76: a cancel answered true between reading the cause and leaving the running map is lost
- c19dad: for a launched job, a cancel answered true can still lose to the natural exit

Each fix task closed the cited site. The next round then found the same invariant broken on a neighbouring path.

## Root cause

The finding names a file and line range, and the fix task takes that as its scope. Nothing asks the fixer to list every path that can break the same invariant and to test the invariant on all of them at once.

## Proposed action

When a code-review or functional-review finding breaks a stated invariant (an "on every path" or atomicity claim), the fix task should (1) restate the invariant, (2) list every code path that removes, settles or answers for the same state, and (3) add one test per path, or name why a path cannot break it. The verifier of the next round can then check the list rather than find the next path.

## Evidence

- qgate 6-finalize a86981, 94a78a, 957198, 207f76, c19dad (code-review rule)
- pr-comment a1a9fe (fixed, TASK-25)
- chat_history_analysis: "Two extra code-review rounds were granted by the operator after the loop-back budget was spent; each found a narrower form of the same cancel/settlement race"
- plan_efficiency: 65% of tokens went to 6-finalize; code review fired 9 times
