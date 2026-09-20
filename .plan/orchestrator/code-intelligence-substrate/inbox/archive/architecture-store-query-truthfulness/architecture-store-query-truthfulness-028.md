envelope_version=1
sender_type=plan
sender_id=architecture-store-query-truthfulness
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-09-15T07:54:02Z

component=plan-marshall:manage-tasks
category=bug

# The function whose docstring argues for population honesty committed the population loss

Source: Q-Gate finding 02c4a7 (6-finalize, self-review; fixed in cc4e8cf1b).
Defect class duplicate_claimable_key — 3 findings in this class this round.

check_declared_set_closure at _qgate_closure.py:299 builds by_number by subscript-
assigning each deliverable under its number with no duplicate-key disposition. This is
the most severe of the three sites because this function PUBLISHES a completeness claim:
its own docstring at lines 270-285 argues at length that exempt, scanned and unmapped
must stay distinguishable so a population never overstates what it covered.

A duplicate deliverable number silently removes one deliverable from by_number, so its
declared set is never run through the closure while population_complete still reports
True.

## Solution

The measured-looking-verdict-over-an-unexamined-surface defect the module exists to
report, committed against itself. A docstring arguing for an invariant is not an
implementation of it — when a function's contract is "this count is honest", the
collision policy on every index it builds is part of that contract and should be
asserted by a test, not narrated.

## Impact

The highest-severity of the three sites, and the one whose false verdict is most
authoritative.
