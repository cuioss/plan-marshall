envelope_version=1
sender_type=plan
sender_id=identifier-vocabulary-decision
epic=orchestrator-refactor
kind=candidate-lesson
created=2026-09-20T08:31:25Z

component=plan-marshall:persona-plan-marshall-agent
category=anti-pattern
bundle=plan-marshall

# A closed-vocabulary rule's escape hatch must place the out-of-scope case OUTSIDE the set, not assign it a set member

Source signal: PR-comment finding `fe553a` — CodeRabbit inline comment on PR #1543 at
`doc/adr/023-Entity_identifying_CLI_parameters_use_one_typed_vocabulary.adoc:265`,
reviewed commit `2bf9214`, resolution `fixed`, responded on the PR.

## The defect

ADR-023 establishes Rule 1: entity-identifying CLI arguments draw their suffix from a
**closed** set (`-id` / `-number` / `-slug`). The Risks section then had to handle
`--epic`, which on one surface carries an epic *specification body* rather than an epic
identity. The mitigation as authored said that flag "takes a suffix" from the closed
set — but **none of the three suffixes denotes content**. The escape hatch assigned an
out-of-scope case a member of the very set it falls outside.

The fix reworded it the other way round: a content-bearing flag is not
entity-identifying, so it sits outside the closed vocabulary entirely, and bare
`--epic` stays reserved for epic identity.

## The generalizable shape

When a rule closes a vocabulary over a *scoped* population ("entity-identifying
arguments"), the exception handling has exactly two correct moves:

1. Show the case is **in** scope and give it a real member of the set, or
2. Show the case is **out** of scope and say what governs it instead.

Reaching for a set member *because the case was awkward* is the failure — it silently
widens the set's meaning ("`-slug` now also means content") and destroys the property
that made closing it worth doing. The tell is a mitigation sentence that names a
suffix without being able to say what that suffix denotes for this case.

## Why it is worth recording

⭐ This is the **slipped-then-caught** class. `default:pre-submission-self-review` ran
on this plan and marked `done` before push; the defect sat in a document whose entire
subject is a closed vocabulary, and the reviewer that caught it was CodeRabbit, after
the PR was open. A self-review pass over an ADR that *defines* a closed set is exactly
where a "does every exception resolve inside or outside the set?" check would pay, and
it did not fire.

## Question for the epic

`orchestrator-refactor` is landing a vocabulary decision across several plans. Worth
checking whether the sibling plans that consume ADR-023 (the canonical-forms table
rewrite, the plugin-doctor `ARGUMENT_NAMING_*` rules) restate the closed set anywhere
with the same in-set-vs-out-of-scope ambiguity — a rule restated in N places can be
corrected in one and left wrong in the other N-1.
