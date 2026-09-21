envelope_version=1
sender_type=plan
sender_id=architecture-store-query-truthfulness
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-09-15T07:53:59Z

component=plan-marshall:manage-tasks
category=bug

# A bare subscript insert keyed on a caller-supplied number is silent last-write-wins

Source: Q-Gate finding f2f66e (6-finalize, self-review; fixed in cc4e8cf1b).
Defect class duplicate_claimable_key — 3 findings in this class this round.

_cmd_qgate_mechanical.py:186 builds prose_by_number keyed by deliverable number with a
bare subscript insert and no duplicate-key disposition, so two blocks carrying the same
heading number collapse and the last silently wins. Nothing upstream rejects duplicate
deliverable numbers: extract_deliverables and the check-3c validator guard PATHS, not
number uniqueness.

The first block's prose then vanishes from the keyword-drift haystack while the
mechanical pass still reports ambiguous=False — an authoritative clean verdict over a
deliverable it never saw.

## Solution

Record a duplicate-number disposition (reject, or report and mark the result ambiguous)
instead of last-write-wins. The general rule: wherever a dict is keyed on a value the
caller supplies rather than the code derives, the insert needs a stated collision
policy, because the collapse is invisible at the insert site and the loss surfaces as a
CLEAN verdict.

## Impact

Three sites in this one module shared the pattern; see the sibling candidates for the
other two.
