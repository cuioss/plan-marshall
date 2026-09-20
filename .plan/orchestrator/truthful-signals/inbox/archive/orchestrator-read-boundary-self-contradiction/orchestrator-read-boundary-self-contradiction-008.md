envelope_version=1
sender_type=plan
sender_id=orchestrator-read-boundary-self-contradiction
epic=truthful-signals
kind=candidate-lesson
created=2026-07-28T20:44:57Z

component=plan-marshall:manage-status
category=improvement
created=2026-07-28
bundle=plan-marshall

# A plan-time heuristic emits a confident point estimate with no honest "unknown" output

## What happened

Two plan-time classifiers in `1-init` produced confident categorical outputs from
evidence that did not support them. Both are recorded in `decision.log`.

**Instance 1 — request-aspect classification at 5.5% confidence.**

```
(plan-marshall:phase-1-init) Request aspect classified: implementation
  (confidence=0.055, below 0.7 threshold - conservative fallback)
```

A confidence of `0.055` against a `0.7` threshold is not weak evidence, it is
*no* evidence. Yet the run does not record "unclassified" — it records
`request_aspect: implementation` into `status.metadata`, where every downstream
consumer reads it as a fact with no confidence attached. The phrase
"conservative fallback" makes the outcome sound *safer* than an abstention, when
what actually happened is that a coin-flip was promoted to a stored attribute.

**Instance 2 — scope estimate off by 7×.**

```
(manage-status:scope-estimate-heuristic) Classified scope_estimate=surgical
  (distinct_paths=1, glob=False) — pre-route coarse guess
(manage-status:planning-lane) Routed planning_lane=light (predicate=signal_set, ...)
```

The plan touched **seven** files. `distinct_paths=1` because the heuristic counts
paths in structured fields and does not see paths written in backticked prose —
the operator's own escalation note says exactly that: *"scope heuristic undercounted
paths buried in backticked prose"*. On that count the router chose the **light**
lane.

Only a manual operator escalation to `deep` prevented that route. And the deep lane
is what ran the outline Q-Gate that found `doc/concepts/orchestration.adoc:31` —
the third live restatement, outside the request's stated constraints, that the fix
needed. **The light lane would have shipped an incomplete fix**, and nothing
automated would have said so.

## Solution

**Rule:** a heuristic whose output routes control flow must be able to say
*"I don't know"*, and its consumers must handle that value.

1. **Abstain below threshold.** When a classifier lands below its own stated
   threshold, persist `unknown` (or omit the field), not the argmax label. A label
   stored without its confidence loses the only information that qualified it — the
   confidence lives in the decision log, the label lives in `status.metadata`, and
   only the label is read downstream.
2. **Report the input basis alongside the estimate.** `distinct_paths=1` is the
   falsifiable part of the scope claim and it is already logged; make the router
   treat a *low path count derived from a request containing many backticked paths*
   as a low-confidence estimate rather than a `surgical` verdict. The mismatch
   between "paths in structured fields" and "paths mentioned anywhere" is detectable
   without solving the general parsing problem — a backtick-token count is enough to
   flag the disagreement.
3. **Escalate on abstention, don't default.** A one-way ratchet to the wider lane
   on `unknown` is the safe direction; the current behaviour defaults to the
   *narrower* lane on the weakest evidence.

## Impact

On theme, and both instances are of the shape the epic is chasing: a categorical
output that reads as a determination but is a guess, with the caveat parked in a
log line nobody downstream reads.

The scope instance is the more expensive one, because it is *load-bearing for
coverage*. The lane choice decides whether the outline Q-Gate runs, and the Q-Gate
is what caught the missing file. A confidently-wrong `surgical` therefore does not
merely mis-size the plan — it removes the check that would have caught the
mis-sizing. That is a self-sealing failure: the wrong answer disables its own
detector.

Human intervention was the only thing standing between this plan and an incomplete
fix. That should not be the control.
