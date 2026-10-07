envelope_version=1
sender_type=plan
sender_id=plan-truth-157
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T21:03:09Z

component=plan-marshall:plan-orchestrator
category=bug
bundle=plan-marshall

# Two cardinal collections returned by ONE envelope need an explicit correlation key — ordering is not a contract

CodeRabbit on PR #1494: `analyze.md`'s contract returns
`proposals[N]{message,disposition,rationale}` and `spec_drafts[M]{plan_slug,body}`
from ONE envelope that may process multiple messages, and Step 5b defined no
ordering, no one-draft constraint, and no shared key. `plan_slug` exists only on the
draft; `message` exists only on the proposal. So two or more `stage` proposals in a
single firing leave the orchestrator with no way to select the intended spec body.

Source record: pr-comment finding `23cefc`, PR #1494, bot `coderabbit`, inline at
`analyze.md:48`, resolution `fixed` (remediated in-run by TASK-007).

## Solution

Carry the proposal's own message identifier onto each `spec_drafts` row, rather than
relying on ordering or on positional correspondence between the two collections.

The one-envelope-not-per-message contract itself is deliberate and stays as is — the
correlation key is what makes it safe. That separation matters: the reviewer's
finding could have been misread as an argument against the batching contract, when
what was actually missing was the join key.

General rule: whenever one envelope returns two or more cardinal collections whose
rows relate to each other, an explicit correlation key is part of the contract.
Absent a key, the only available join is array position — which no envelope contract
in this system guarantees.

## Impact

This is the review-bot finding class worth recording even though it was caught and
fixed in-run: it is a CONTRACT defect in a dispatch return shape, the same family as
the internally-found `landing_report` cardinality drift on the same file. Two
independent reviewers found two different defects in one bullet group, which suggests
the group itself warrants a structural check rather than per-line review.
