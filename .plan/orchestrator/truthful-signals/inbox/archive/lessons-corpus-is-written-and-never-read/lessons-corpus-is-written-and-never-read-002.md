envelope_version=1
sender_type=plan
sender_id=lessons-corpus-is-written-and-never-read
epic=truthful-signals
kind=candidate-lesson
created=2026-07-28T18:43:48Z

component=plan-marshall:phase-6-finalize
category=anti-pattern
created=2026-07-28

# SKILL.md dispatch table omits an inline Step-1 precondition, inviting a missing-field dispatch

On this plan's own finalize run, the orchestrator dispatched the
`pre-submission-self-review` step WITHOUT its required `candidates`
field on the first attempt. The dispatched leaf correctly refused with a
contract-violation error instead of fabricating a clean review — the
refusal mechanism worked exactly as designed.

The near-miss is upstream of the leaf: `phase-6-finalize/SKILL.md`'s
dispatch table lists the step's workflow doc (the pointer to
`workflow/pre-submission-self-review.md` or equivalent) but does not
name the workflow's inline Step 1 precondition (that `candidates` is a
required prompt-body field the caller must gather and forward before
dispatching). A caller reading the dispatch table alone has no signal
that the field exists, let alone that it is mandatory, so the omission
is easy to repeat on any future re-read of the table.

## Solution

Surface the precondition at the dispatch-table row itself — not only
inside the workflow doc's own Step 1 — so a caller scanning the table
sees the required-field obligation before composing the dispatch prompt.
A one-line annotation on the table row ("requires: `candidates` field,
see workflow Step 1") would have prevented this specific near-miss
without duplicating the full precondition prose.

## Impact

Any phase-6-finalize dispatch loop iteration that reads the SKILL.md
table as its sole source of the dispatch shape is exposed to the same
omission. The leaf-side refusal is a safety net, not a fix — it costs a
wasted dispatch-and-retry cycle every time the near-miss recurs.
