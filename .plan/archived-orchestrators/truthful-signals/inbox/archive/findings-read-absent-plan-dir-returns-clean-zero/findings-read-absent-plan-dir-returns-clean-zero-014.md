envelope_version=1
sender_type=plan
sender_id=findings-read-absent-plan-dir-returns-clean-zero
epic=truthful-signals
kind=candidate-lesson
created=2026-08-30T14:16:56Z

component=plan-marshall:manage-lessons
category=bug
disposition=reinforcement
severity=high
source_plan=findings-read-absent-plan-dir-returns-clean-zero
source_pr=1369
source_finding=3cf3d8
related_message=findings-read-absent-plan-dir-returns-clean-zero-004

# Increment to L4: the vanished lesson is a RECURRENCE (n >= 2) of a known destructive-remove defect, not a one-off

## Why this is a separate message and not a duplicate

Sibling message **L4** carries the full evidence for the disappearance of lesson
`2026-08-27-16-001`, and carries it correctly — including its careful refusal to claim this run
destroyed it. Do not re-read that evidence here.

Q-Gate finding `3cf3d8` was filed at **14:10:11Z**, *after* L4 was written (14:08:32Z), on an
independent re-verification. It carries **one fact L4 does not**, and that fact changes how the
epic should scope the remedy. This message is that fact alone.

## The increment

The disappearance matches a **previously recorded destructive defect**: `manage-lessons remove`
destroyed a lesson while returning `not_found` and wrote no tombstone — 2026-08-27, lesson
`2026-08-25-05-001`. That prior instance is the origin of the standing rule **"never retry a
lessons operation on `not_found`, because on this defect the refusal comes AFTER the destruction."**

**n is now at least 2.**

## Why the count changes the scoping

L4 read alone supports a remedy of the *detect-it* shape: add a corpus-integrity check, make the
housekeeping count derivable. Those remain right. But a defect at n >= 2, with the same signature
(file gone, no tombstone, an operation reporting a non-destructive outcome), is not an anomaly to
detect after the fact — it is a **live data-loss path to close**.

The prior instance also tells us where to look: the removal path can reach a state where the file
is unlinked and the tombstone is not written, and the caller is told `not_found`. That is a
**non-atomic removal**, and L4's own remedy 2 ("either a non-`remove` path deletes lesson files, or
`remove` can fail after unlinking and before writing") is now answered in the second direction by
the prior instance rather than left as an open pair.

## Why nothing was recovered or re-added in-run

Stated so the epic does not retry it:

- **Not recoverable.** Without a tombstone there is no id-resolution record to restore from. The
  content survives only because L4 re-filed it.
- **Deliberately not re-added under a fresh id.** That would create a second lesson with the same
  content and no link to the original id that other records still reference — and this run has no
  evidence about *which* operation removed it. A guess codified as a corpus entry is worse than
  the gap.
- **No `manage-lessons remove` call was made** anywhere in this run's retrospective or capture
  steps, per the standing hazard rule. The corpus was treated as read-mostly throughout.

**Treat inbox message L4 as the recovery source for the lost content.**

## Remedy increment (for the epic to scope)

Make removal **tombstone-or-refuse, atomically**: write the tombstone first, and treat a failure to
write it as a refusal to unlink. A removal that can destroy before it records is unauditable by
construction, and it has now done so twice.
