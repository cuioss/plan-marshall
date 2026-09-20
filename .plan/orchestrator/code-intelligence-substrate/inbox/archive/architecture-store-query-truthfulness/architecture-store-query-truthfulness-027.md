envelope_version=1
sender_type=plan
sender_id=architecture-store-query-truthfulness
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-09-15T07:54:01Z

component=plan-marshall:manage-tasks
category=bug

# The keyword-drift check compares tasks against a deliverable set one member short

Source: Q-Gate finding ee092d (6-finalize, self-review; fixed in cc4e8cf1b).
Defect class duplicate_claimable_key — 3 findings in this class this round.

_check_keyword_drift at _cmd_qgate_mechanical.py:555 builds by_number by
subscript-assigning each deliverable under its number with no duplicate-key disposition,
so two deliverables sharing a number collapse to the last one. Every task pointing at
that number is then evaluated against the SURVIVING deliverable only, and the dropped
one is never compared — silent under-coverage reported as a pass.

## Solution

Same class as the prose_by_number site at line 186 and the closure site in
_qgate_closure.py:299; all three had to be fixed together, because fixing one leaves the
same population loss reachable through the other two.

That co-location is itself the lesson: when a collapsing-key pattern is found once,
enumerate every sibling index built the same way in the same module before declaring the
class closed.

## Impact

A drift check that under-covers is worse than one that fails, because it publishes a
pass.
