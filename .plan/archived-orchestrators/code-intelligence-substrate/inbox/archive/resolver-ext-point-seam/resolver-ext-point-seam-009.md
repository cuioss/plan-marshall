envelope_version=1
sender_type=plan
sender_id=resolver-ext-point-seam
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-07-30T15:20:15Z

component=plan-marshall:plan-marshall
category=bug
title=A monitor armed with a token that cannot match reports timeout indistinguishably from still-waiting

# A monitor armed with a token that cannot match reports timeout indistinguishably from still-waiting

Found by `plan-retrospective` on PR #1067 via the session transcript. Not remediated.

## What happened

Two orchestrator-side monitors were armed during this plan. Both reported:

```
[Monitor timed out — re-arm if needed.]
```

Both were wrong. In each case the awaited condition had **already occurred** before the
timeout fired:

| Monitor | Armed to match | Reality | Actual state at timeout |
|---|---|---|---|
| "merge lock availability for resolver-ext-point-seam" | `status: available` | the lock store emits `status: free` | lock had been acquired — `lock-owned` at 13:08:51, and again at 14:30:42 |
| "PR 1067 merge-queue state" | `pr view --pr-number` | that verb takes `--head`, not `--pr-number` | the PR had already reached its queue state |

The first watcher polled for a token string the producer never emits. The second invoked a
verb with a flag the verb does not accept, so the probe returned nothing to match against.
Neither watcher could ever have succeeded.

## The finding

A monitor has two failure modes that are operationally opposite and textually identical:

1. **"I waited and the thing did not happen"** — real information; re-arming is reasonable.
2. **"I cannot observe the thing at all"** — a defect in the watcher; re-arming is a
   guaranteed repeat of the same non-observation.

Both emit `[Monitor timed out — re-arm if needed.]`. The operator, reading a timeout, has
no way to tell which they got, and the natural reading of silence is "still waiting" —
i.e. progress is being made. In both instances here, progress had in fact already
completed and the plan stalled on a watcher that was structurally blind.

Note the shape: this is the same defect as `hard_quota`-vs-size-cap in the sibling finding
from this plan. In both cases a taxonomy collapses **"not yet"** into the same bucket as
**"never, given this configuration"**, destroying the one bit that determines what to do
next. Two independent instances of one archetype inside a single plan.

## Root cause

Match tokens and probe invocations are supplied at arm time as free text and are never
validated against the surface they will poll. Nothing checks that `status: available` is a
value the lock store can emit, or that `--pr-number` is a flag the `pr view` verb accepts —
even though the second is a plain argparse surface that would reject the call immediately
if it were ever executed against a real parser.

## Proposed action

1. **Validate at arm time, fail loudly.** A monitor should resolve its probe command
   through the same argparse surface the executor uses and reject an unrecognised flag
   before arming, rather than discovering it via a silent 10-minute non-observation.
2. **Validate the match token against the producer's declared value set.** The merge-lock
   store's status enum is a closed set; `available` is not in it. An arm-time membership
   check is trivial and would have caught this.
3. **Give a blind watcher a distinct terminal event.** `[Monitor could not observe its
   target — probe invalid]` is actionable; `[Monitor timed out]` is not.
4. Standing rule: **a wait that cannot observe its target is not a wait, and must not be
   reported as one.**

## Evidence

- Session transcript `f20a92f3-d4ad-4240-9e9c-36ecefea517d`, reduced turns 9 and 10 — both
  task-notification events carrying the identical timeout string.
- `logs/work.log:428-430` and `:508` — `lock-waiting` at 12:37:35, `lock-owned` at
  13:08:51, cleared 13:09:48, `lock-owned` again at 14:30:42. The lock lifecycle completed
  normally throughout the period the watcher reported as an unresolved wait.
- The same session's six bare `retry` operator turns — the operator was manually driving
  restarts that the monitoring layer should have been surfacing.
