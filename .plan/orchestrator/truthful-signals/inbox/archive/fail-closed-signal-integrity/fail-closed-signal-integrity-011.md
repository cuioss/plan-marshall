envelope_version=1
sender_type=plan
sender_id=fail-closed-signal-integrity
epic=truthful-signals
kind=candidate-lesson
created=2026-08-02T22:06:49Z

component=plan-marshall:ref-workflow-architecture
category=bug
bundle=plan-marshall

# `[DISPATCH]` is emitted on first fire only, and `resolve-target` emits nothing at all

The dispatch audit's two evidence surfaces are, respectively, systematically incomplete and
entirely empty. The audit therefore reports clean for the same reason a healthy plan would.

## Surface A — `[DISPATCH]` lines under-count envelopes by ~35%

15 `[DISPATCH]` lines in `logs/work.log` against roughly 23 execution-context envelopes that are
independently evidenced by their own `(plan-marshall:execution-context.{name})` log prefixes.
Every gap is a **re-fire**:

| Step | Envelopes observed | `[DISPATCH]` lines |
|------|-------------------:|-------------------:|
| `pre-submission-self-review` | 5 (14:11, 14:48, 15:00, 15:51, 19:08) | 1 (13:59:11Z) |
| `automatic-review` | 3 (16:26, 19:44, 20:52) | 1 (16:25:23Z) |
| `wait-region-unified-triage` | 2 (16:33, 20:05) | 1 (16:32:16Z) |
| `phase-5-execute` loop-back re-entry | 2 (17:56, 20:07) | 0 |
| `lessons-capture` | 1 (21:07) | 0 |

`lessons-capture` is the cleanest single case: `decision.log` entry `fb8d5c` at 21:06:42Z ends
with the literal word **"Dispatching"**, `work.log` at 21:07:55Z carries
`[SKILL] (plan-marshall:execution-context.lessons-capture) Loaded …`, the step is recorded
`outcome=done` — and no `[DISPATCH]` line exists anywhere for it. Under the audit's own
`dispatch_coverage_violation` rule that is indistinguishable from having run the step inline.

`pre-submission-self-review` iteration 5 is the cleanest re-fire case: `decision.log` `69d6d2`
says in as many words that the re-fire's "cognitive phase runs in this dispatched envelope", with
no paired emission.

## Surface B — zero `effort resolve-target` records exist

The audit's documented pairing rule is: pair a `decision.log` `effort resolve-target` entry with
the next chronologically-following `[DISPATCH]` line carrying the same `role`; an unmatched
resolve is a `shape_violation`. Across **125 decision-log entries there is not one
`resolve-target` record.** With Surface B empty, that check can only ever return zero — it is
structurally incapable of reporting a violation.

The three `shape_violation`s the retrospective did report were found by pairing Surface A against
the `execution-context.{name}` prefix in `[SKILL]`/`[STATUS]` lines — i.e. by going **outside** the
documented rule. The documented rule found nothing and could not have.

## Why this belongs to this epic

The audit exists to catch dispatch-discipline defects. Its primary intent surface is unpopulated
and its observable surface skips every retry path. It is a confident green produced by an empty
input — the epic's flagship archetype, sitting inside the tool built to detect that archetype.

## Solution

1. **Move the emission into the seam.** Emit `[DISPATCH]` from the dispatcher itself (or from
   `effort resolve-target`, which today logs nothing), so a code path cannot skip it by forgetting
   to restate a hand-written logging step. A re-fire that reuses the envelope must still emit.
2. **Make `resolve-target` log its intent.** One `decision.log` line per resolve, carrying the
   role key and the resolved target. Without it the pairing rule has no left-hand side.
3. **Make the audit fail closed on an empty surface.** When Surface B has zero records, the
   `shape_violation` check must report `status: indeterminate`, never `0 findings`. "I found
   nothing" and "I had nothing to look at" must not be the same output — clause (b) of the
   standard this plan just shipped.
