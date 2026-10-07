envelope_version=1
sender_type=plan
sender_id=plan-truth-157
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T21:00:25Z

component=pm-plugin-development:ext-self-review-plan-marshall
category=anti-pattern
bundle=pm-plugin-development

# Never index a subset of an enumeration POSITIONALLY — name the members

The seven-dispatch index in `orchestration-model.md` stated "The last four are
drafting dispatches". Positionally the last four are entries 4-7, which INCLUDES
entry 6 (`decompose.md` Step 2 on-disk-corpus read / candidate mapping / prior-art
search — a READ dispatch, not drafting) and EXCLUDES entry 3 (`analyze.md` Step 4
item 1 landing-report body draft — which IS drafting). The real drafting set is
entries 3, 4, 5, 7, corroborated by `analyze.md` ("the one landing corroboration,
the three drafting sub-steps, and the untrusted-text extraction") and
`decompose.md` (one `spec_body` draft).

A second drift rode the same sentence: entry 7 was indexed as "`decompose.md` Step
4 plan-spec body draft", but `decompose.md` lists the Step 4 Write as inline-only
on write-freedom and returns `spec_body` from the Step 2 dispatch. A reader
following the index to Step 4 finds an explicitly inline-only write, not a
dispatchable draft.

Source record: Q-Gate finding `7bf5af`, phase `6-finalize`, defect_class
`contract_drift` (2 findings in this class this round), resolution `fixed` in
commit `72738c8ec`.

## Solution

A positional claim over an enumeration ("the last four", "the first two", "all but
the last") silently re-binds every time a member is inserted, removed, or
reordered — and the re-binding is invisible at the claim site because the sentence
still reads as true. Name the members (entries 3, 4, 5, 7) or derive the subset
from a property, never from position. Re-point every index entry at the step that
actually holds the thing being indexed.

## Impact

Applies to any hand-maintained index over an ordered set — dispatch indexes, rules
cards, step tables, candidate lists. This is the positional-claim sibling of the
index-completeness rule already in the agent-behavior standard.
