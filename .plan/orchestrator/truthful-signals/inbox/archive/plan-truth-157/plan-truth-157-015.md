envelope_version=1
sender_type=plan
sender_id=plan-truth-157
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T21:01:43Z

component=plan-marshall:plan-orchestrator
category=bug
bundle=plan-marshall

# Name the noun: a bare plural that doubles as a verb silently drops members from a required set

`decompose.md` read: "the per-plan carries the template asks for, the Expected
Surface, the re-grounding instruction, the adjacency and overlap notes, and the
verify-first clauses". Two readings:

- (a) "per-plan carries" is the plural NOUN the same document establishes
  elsewhere ("Author every per-plan carry — claim labels, expected surface,
  re-grounding instruction, adjacency and overlap notes, verify-first clauses"), so
  the phrase names the whole five-member set and the four items after it are a
  redundant restatement of four of its members.
- (b) "carries" is the VERB and the noun is missing, so the phrase is incomplete
  and the required `spec_body` content is only the four listed items.

Reading (b) is the one a leaf author acts on, and it omits CLAIM LABELS — required
in every per-plan carry, and the thing the corpus re-grounding machinery needs in
order to address a spec's claims at all. A spec drafted without them cannot be
re-grounded.

Source record: Q-Gate finding `4508f2`, phase `6-finalize`, defect_class
`ambiguous_wording`, resolution `fixed` in commit `72738c8ec`.

## Solution

Name the noun explicitly, then either defer WHOLLY to the canonical set ("every
per-plan carry, as defined at ...") or enumerate ALL its members. Never do both
partially: a bare plural followed by a subset of its own members is the shape that
makes the omission invisible, because the sentence reads as complete under reading
(a) and as authoritative under reading (b).

## Impact

The general form: any noun phrase whose head word is also a plausible verb is a
parse ambiguity, and when the noun names a REQUIRED SET the ambiguity silently
shrinks that set. Highest risk in instruction documents a leaf agent executes
without being able to ask.
