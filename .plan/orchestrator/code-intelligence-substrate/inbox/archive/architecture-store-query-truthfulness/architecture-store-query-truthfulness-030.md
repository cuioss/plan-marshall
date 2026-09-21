envelope_version=1
sender_type=plan
sender_id=architecture-store-query-truthfulness
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-09-15T07:54:05Z

component=plan-marshall:execute-task
category=bug

# Adding a third state invalidated an `iff` clause the same hunk carried through verbatim

Source: Q-Gate finding d82cb9 (6-finalize, self-review; fixed in cc4e8cf1b).
Defect class touched_claim_unverified — 2 findings in this class this round.

The hunk added the tri-state qualification to assert_test_identifiers.py's Returns block
at line 218 but carried the pre-existing clause "passed is True iff missing is empty"
through unchanged. The new None state invalidates it: on the could-not-look path
`missing` is the EMPTY tuple — stated outright by the DiffResult attribute doc at lines
177-180 — while `passed` is None, not True. The iff is false in exactly the direction
this module exists to prevent, inviting the None-to-True collapse the warning at lines
171-173 forbids.

Two sibling sites carried the mirror defect and had to be fixed in the same pass: the
DiffResult attribute doc at 168-170 and the module docstring Contract bullet both said
"False iff at least one was not found", which the could-not-look input also satisfies
while the value is None.

## Solution

State the None case FIRST, then define True/False over the measured path only. When a
binary becomes a tri-state, every `iff` in the surrounding contract is invalidated by
construction — enumerate them rather than editing the one the diff happened to touch.

## Impact

Three sites, one change, all reachable through the same could-not-look input.
