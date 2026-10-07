envelope_version=1
sender_type=plan
sender_id=plan-truth-157
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T21:03:04Z

component=pm-plugin-development:ext-self-review-plan-marshall
category=bug
bundle=pm-plugin-development

# Anchor a presence pattern to the STATEMENT it verifies — an unrelated pre-existing phrase satisfied half a conjunct

`_SELECTION_RULE_RE` was the bare phrase "selection rule" with no anchor to the
constraint it was supposed to verify. In `analyze.md` it was satisfied by an
unrelated, pre-existing phrase: Step 5 item 4 reads "under the same `orchestrate.md`
selection rules AND the same `auto_emit` gate", and "selection rules" contains
"selection rule" as a substring. So the pattern matched regardless of the
monotonic-resource paragraph it was meant to check.

Verified consequence against the live worktree file: delete the sentence "The draft
states the SELECTION RULE" from `analyze.md` while keeping "monotonic resource", and
`test_every_spec_body_draft_carries_the_monotonic_resource_constraint` stays GREEN.
Half of the conjunct it asserts cannot fail for that document, while the assertion
message claims the doc was checked for "the monotonic-resource constraint AND the
selection rule it substitutes".

`_MONOTONIC_CONSTRAINT_RE` is sound by contrast: "monotonic resource" appears in
each doc only inside the guarded paragraph, and the nearby "a monotonic revision"
does not satisfy it. The difference is that one phrase is distinctive in context and
the other is not.

Source record: Q-Gate finding `e55504`, phase `6-finalize`, defect_class
`regex_overfit`, resolution `fixed` in commit `04f12a22b`.

## Solution

Anchor the pattern to the STATEMENT rather than to the topic — "states the selection
rule" matches the two intended sites and not the Step 5 emit prose. Before trusting
a bare-phrase presence check, search the target documents for that phrase and
confirm every hit is inside the region being guarded. A phrase that appears
elsewhere in the same file is not a presence check; it is a constant `True` for that
file.

## Impact

The asymmetry inside one test is the transferable observation: a conjunctive
assertion is only as strong as its weakest conjunct, and a conjunct that cannot fail
makes the assertion's own message a false claim about what was measured.
