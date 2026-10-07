envelope_version=1
sender_type=plan
sender_id=plan-truth-157
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T21:03:02Z

component=pm-plugin-development:ext-self-review-plan-marshall
category=bug
bundle=pm-plugin-development

# A grant is a CLAUSE, not a sentence — a negation-suppressed guard goes blind at exactly its load-bearing site

`_NEGATION_RE` was applied at SENTENCE scope via `_SENTENCE_SPLIT_RE`, which splits
only on period, bang, and question mark. `_leaf_write_grants` therefore dropped the
whole sentence when any of not/never/no/none/nothing/cannot/without/outside appeared
ANYWHERE in it — so a genuine grant sharing a sentence with any negation was
silently unreported.

Example that should be reported and was not: "The leaf may call the orchestrator
queue to append the row, and no other write is permitted." It carries the leaf, the
forbidden target, and the affirmatives "may" and "call" — and is dropped solely by
the word "no" in "no other".

This is not hypothetical. The ONE sentence in `orchestration-model.md` that states
the boundary is SEMICOLON-joined and already mixes a grant clause ("a drafting leaf
MAY compose a document body") with a prohibition ("it MAY NOT call Write/Edit inside
the epic tree") — and `_SENTENCE_SPLIT_RE` does not split on a semicolon. Adding a
grant clause into that one sentence leaves `test_no_dispatch_doc_grants_a_leaf_a_
write_path` green: the guard is blindest precisely where the contract is stated.

The existing controls covered only the opposite arm.
`test_a_prohibition_is_not_read_as_a_grant` pins the false-POSITIVE direction, and
no control pinned a grant carrying a co-located negation.

Source record: Q-Gate finding `5a3725`, phase `6-finalize`, defect_class
`regex_overfit`, resolution `fixed` in commit `04f12a22b`.

## Solution

- Scope the negation to the CLAUSE holding the affirmative verb and the target:
  split on semicolon and em-dash as well, or require that no negation appear
  BETWEEN the affirmative and the target.
- Add the matched control for the missing direction — a grant co-located with a
  negation.
- When choosing a suppression scope, check it against the single most load-bearing
  sentence in the corpus being scanned, not against a synthetic fixture.

## Impact

Two generalizable rules: a syntactic scope chosen for convenience (sentence) rather
than for semantics (clause) becomes a suppression channel; and a guard with controls
on only one direction has an untested arm by construction.
