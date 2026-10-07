envelope_version=1
sender_type=plan
sender_id=correct-review-scores-as-maximally-wrong
epic=review-apparatus
kind=candidate-lesson
created=2026-08-02T12:58:44Z

component=plan-marshall:automatic-review
category=bug
bundle=plan-marshall

# A store used as both a work queue and an evidence record breaks when one consumer starts dropping from it

## What happened

Two truthful-signal guards in `automatic-review` shared one substrate — the findings store:

1. **D1 contentless-review classification** decided a bot review was boilerplate-only and
   therefore **dropped the comment from the findings store** (the correct behaviour for a work
   queue: noise should not become work).
2. **`_has_update_movement` / `participation_requires_update`** read its *first-presence
   evidence* from that same findings store — "have we ever seen a comment from this bot?"

Fixing (1) silently broke (2). Once the contentless comment was dropped, the participation guard
could no longer observe first presence for `pr-agent`, so `participation_requires_update` became
**permanently satisfied** for that bot. A bot that posted only boilerplate — the exact case the
epic cares about — now read as a fully participating reviewer forever.

Neither guard was wrong in isolation. The defect lived in the shared substrate: the store was
doing double duty as a *mutable work queue* and as an *append-only evidence record*, and those
two roles have opposite deletion semantics.

## How it was caught

By **pre-submission self-review**, not by any test and not by CI. Nothing failed. The broken
guard's failure mode is to return the *satisfied* answer, so it is invisible to any check that
only asserts the happy path.

## Rule

- **Never read evidence-of-occurrence out of a store that another consumer prunes.** A work queue
  answers "what is still to do"; an evidence record answers "what ever happened". A single store
  cannot answer both once anything deletes from it.
- **When a change adds a deletion to a shared store, enumerate every reader of that store** and
  ask, for each, whether it reads *remaining* items or *ever-present* items. The readers that
  need "ever-present" must be moved off the store before the deletion lands.
- **The dangerous direction is fail-open.** A guard that loses its evidence source does not error —
  it reports "satisfied". Check the polarity of every guard's degraded answer: if losing input
  makes it pass, it needs an explicit "evidence unavailable" state distinct from "condition met".

## Fix

TASK-4 of `correct-review-scores-as-maximally-wrong` (PR #1078) introduced an **observation
sidecar** carrying the first-presence evidence independently of the findings-store lifecycle, so
D1's drop no longer removes the participation guard's input.

## Archetype

"A fix for one truthful-signal defect broke a neighbouring one." Worth tracking as its own
archetype in the epic: within a cluster of guards over shared state, a repair is a *change of
state semantics*, and every sibling guard reading that state is in the blast radius.
