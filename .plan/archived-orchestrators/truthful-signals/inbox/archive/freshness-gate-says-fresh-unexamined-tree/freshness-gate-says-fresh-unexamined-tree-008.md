envelope_version=1
sender_type=plan
sender_id=freshness-gate-says-fresh-unexamined-tree
epic=truthful-signals
kind=candidate-lesson
created=2026-09-06T17:28:34Z

component=plan-marshall:phase-3-outline
category=improvement
confidence=medium
source_plan=freshness-gate-says-fresh-unexamined-tree
source_pr=1425

# Deliverable 4 closed done at 62.5 pct declared-file coverage with no gate

## Context

Deliverable 4 of this plan was "Correct the describe-only documents that still state
the collapsed contract". It declared **8** documents, all `intent: write-replace`, and
its own verification criteria said "The `--paths` list covers all eight declared
files, so a correction landing in a conditional member is gated by the same run."

**5 of the 8 were modified.** Three were not:

- `marketplace/bundles/plan-marshall/skills/manage-config/SKILL.md`
- `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/execution.md`
- `marketplace/bundles/plan-marshall/skills/extension-api/standards/build-systems-common.md`

All three still reference `pre-commit-verify-freshness` (1, 1 and 2 matches
respectively) and none carries the new `ledger-verified` basis token that the
corrected documents now carry. The task reached `done`; the deliverable reached
62.5 pct declared-file coverage, below the 70 pct `fulfilled` bar.

Whether the omission was a considered decision (those three describe the verb without
stating the collapsed contract) or an oversight was recorded nowhere this
retrospective can read.

## Root cause

Two things had to both hold for this to close silently:

1. Nothing gates task completion on declared-file coverage. A task whose deliverable
   named 8 files and touched 5 reaches `done` the same as one that touched all 8.
2. The one aspect that measures it — `check-artifact-consistency` — graded the set
   mismatch `warn`, downgraded it to `info`, and forwarded it to an aspect with no
   matching check. (Filed separately against `plan-marshall:plan-retrospective`.)

The plan's whole purpose was to stop a contract being misstated. Three of the eight
documents it itself identified as misstating that contract still do.

## Proposed action

1. On task completion, compare the deliverable's modification-intent declarations
   against the task's realized change set and require an explicit disposition for each
   declared file not touched — "already correct", "out of scope on inspection",
   "deferred" — recorded on the task record.
2. A disposition is cheap (one line per file) and turns an invisible gap into a
   decision a reader can audit. It does not block: an undelivered file with a recorded
   reason is fine; an undelivered file with no reason is the defect.
3. Immediate follow-up for this epic: read the three documents above and either
   correct them or record why they need no correction.

## Evidence

- aspect: request_result_alignment — deliverable 4 `partial`, 5 of 8 (62.5 pct), below the 70 pct bar
- aspect: artifact_consistency — `affected_files_recall` 83.3 pct plan-wide, `outline_only[3]` naming exactly these files
- aspect: outline_vs_shipped — realized footprint 17 paths, none of the three present
- `architecture search --content --literal --pattern "pre-commit-verify-freshness"` — all three still match; `--pattern "ledger-verified"` — none of the three match
