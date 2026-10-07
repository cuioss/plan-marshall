envelope_version=1
sender_type=plan
sender_id=architecture-store-query-truthfulness
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-09-15T07:51:35Z

component=plan-marshall:workflow-integration-git
category=bug

# The merge-tree parser defect emits a second synthetic path per conflicted file

Source: Q-Gate finding 341b23 (2-refine, resolution=taken_into_account).

The second duplicate artifact of the same single manage-locks/SKILL.md conflict, this
one carrying file_path
"CONFLICT (content): Merge conflict in marketplace/.../manage-locks/SKILL.md".
Finding b95a9d carries the "Auto-merging ..." fragment and 69d10b carries the real
path — three findings, one conflicted file.

## Solution

This record is filed separately from b95a9d deliberately: the recurrence is the
evidence. One conflicted file reliably produces three findings, so any consumer that
counts baseline-reconcile findings as "number of conflicting files" is wrong by a
fixed multiplier rather than occasionally. Fix the parser; do not teach consumers to
divide by three.

## Impact

Any gate or report that reads a baseline-reconcile finding count as a file count.
