envelope_version=1
sender_type=plan
sender_id=terminal-title-channel-reconciliation
epic=truthful-signals
kind=candidate-lesson
created=2026-07-27T20:42:10Z

# The lessons corpus is written to and never read from

**Source**: PLAN-79 plan-retrospective (PR #1023). Reported by the retrospective's own
cross-check, not by a human.

## The observation

Five of nine lesson candidates this plan produced dedup onto lessons that were **already active**
in the corpus. The two most expensive failures of the run were both predicted, in writing, before
the plan started:

- Finding `005699` — CI went red on a marketplace-wide static-analysis rule that every
  module-scoped pre-push gate skips by design. (⚠ `005699`'s own text, and an earlier wording
  here, called this a gap "no local gate covers" — **false**; see `-002` for the correction.
  The whole-tree form is runnable locally, it just is not invoked pre-push.) This is a verbatim
  recurrence of **`2026-07-17-09-002`**, filed ten days earlier:
  *"Scoped finalize plugin-doctor (touched-skills-only) misses a whole-tree rule violation that
  CI's whole-tree run catches."* It cost a full red CI cycle and a loop-back.
- "A 250-candidate pre-submission-self-review returned CLEAN, then CodeRabbit found three real
  defects" recurs **`2026-06-22-11-001`**: *"all in-house gates clean, only the PR bot caught it."*
- The manifest's contradictory adjacent log lines (`pre-push-quality-gate omitted — footprint is
  empty` immediately followed by `added pre-push-quality-gate`) recurs **`2026-07-22-00-002`**.

## Why it happens

`finalize-step-lessons-housekeeping` DOES run, and it ran in this plan (retaining 10 lessons). But
it only ever asks the retrospective question — *"did this plan close a lesson?"* It never asks the
prospective one — *"does an active lesson predict a risk on the path this plan is about to take?"*

Nothing anywhere in the lifecycle consumes the corpus prospectively. Lessons are an append-only
write surface with a housekeeping pass, not an input to planning or to gate selection.

## Why it matters for this epic

This is the epic's own theme turned on the epic's own machinery: the corpus is a confident signal
(146 lessons, actively curated, triaged three times) that hides a caveat (nothing reads it before
the fact). A lesson that predicts a failure and does not prevent it is indistinguishable, in
outcome, from a lesson that was never filed.

## Shape of a fix (not prescribed — for orchestrator triage)

A prospective consult at a decision point where the corpus could actually change behaviour: at
phase-3-outline when the surface is known, or at phase-4-plan when the gate set is composed. The
cheap version is a scoped query — "active lessons whose component intersects this plan's affected
modules" — surfaced to the outline rather than auto-applied.
