envelope_version=1
sender_type=plan
sender_id=architecture-store-query-truthfulness
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-09-15T07:56:25Z

component=plan-marshall:manage-tasks
category=bug

# The DAG check lost task identities and still published an authoritative verdict

Source: PR #1489 CodeRabbit inline finding acbc9f (resolution=fixed, TASK-039).

Unusable task numbers are dropped and duplicate task numbers collapse into one in_degree
key. Neither loss reaches the mechanical result's population state, so completeness is
claimed over a shortened set.

The corroborating evidence is INTERNAL and is the sharpest part of this record: the
sibling written by this same plan, _qgate_closure.index_unique_by_number, already returns
duplicate_numbers and documents that every caller must treat a non-empty value as a
population defect. The DAG check is the one site in that pair not following the rule its
own sibling states.

## Solution

Publish dropped identities and duplicate numbers, and let either make the result
ambiguous; replace the duplicate-number test's clean-pass assertion with a disclosure
check.

A set-guarding detector must disclose collisions and must not claim completeness over a
shortened population. When a plan introduces that rule in one module, sweep the module's
other index builders in the same change — the rule is not established by being written
down.

## Impact

Major-severity; the fix had to reach both the detector and the test that had been
pinning its clean pass.
