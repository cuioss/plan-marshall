envelope_version=1
sender_type=plan
sender_id=lb-24-review-step
epic=live-blockers
kind=candidate-lesson
created=2026-10-10T11:58:26Z

component=plan-marshall:manage-lessons
category=bug

# Find what emptied the lessons corpus during a finalize loop-back

## Context

In plan lb-24-review-step the lessons-housekeeping step recorded "69 retained over 69 lesson(s)" in the main-anchored corpus at 2026-10-09T15:25:05Z. Its next firing at 15:52:44Z found 0 active lessons in the same path: `list --status all` returned one superseded record, `get` on a previously retained id returned `not_found`, `aggregate` scanned 0. Between the two firings the only plan activity was a self-review fix round and three builds (the last ran 15:45Z to 15:51Z). Every later housekeeping firing took the empty-corpus exit and recorded `done`; by the next morning four new lessons (2026-10-10-06-*) existed. No log in the plan names a cause, and no plan directory held a carried lesson.

## Root cause

Not established. Candidates the plan record cannot rule out: a test or build reaching the real `.plan/local/lessons-learned/` instead of a fixture store, or an out-of-band deletion. The housekeeping step also has no guard that treats a sudden drop to zero as an error rather than a clean empty corpus.

## Proposed action

Check the tombstone directory and the 15:45Z to 15:51Z build for writes to the real corpus; make the lessons store refuse unlink outside its documented verbs under test overrides; have housekeeping compare the corpus size to its previous firing and halt (not record `done`) on an unexplained drop.

## Evidence

- work.log 2026-10-09T15:25:05Z: 69 retained over 69 lessons
- work.log 2026-10-09T15:52:44Z WARNING: 0 active lessons, previous pass recorded 69, not a clean-corpus result
- housekeeping firings at 16:48Z, 17:47Z, 18:21Z, 20:01Z: 0 lessons, nothing to reconcile, outcome done
