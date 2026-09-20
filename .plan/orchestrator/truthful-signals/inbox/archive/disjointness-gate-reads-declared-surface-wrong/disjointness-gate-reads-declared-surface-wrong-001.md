envelope_version=1
sender_type=plan
sender_id=disjointness-gate-reads-declared-surface-wrong
epic=truthful-signals
kind=candidate-lesson
created=2026-08-30T10:34:07Z

component=plan-marshall:persona-plan-marshall-agent
category=anti-pattern
source_plan=disjointness-gate-reads-declared-surface-wrong
source_pr=1366

# A completeness claim about a semantic class cannot be discharged by enumeration or by string matching

## What happened

`pre-submission-self-review` ran six rounds on PLAN-TRUTH-113. One defect class — a
"the two consumers resolve the SAME set" over-claim — was asserted closed twice, and
refuted both times by the next round.

- **Round 4** closed the class **by enumeration**, naming four carriers and fixing
  each (finding `eadeaf`, commit `5c206c480`). **Round 5** found three more carriers
  *inside a file round 4 had already edited* (finding `db9686`).
- **Round 5** then closed it **by string sweep**, recording as evidence "a content
  search over 5270 files returns these three as the only remaining wrong-form
  carriers" (commit `9d4266292`). **Round 6** found a carrier that states the claim
  in none of the swept strings (finding `581db5`, `script-shared/SKILL.md:29`).

Round 6's finding diagnosed the failure precisely: the sweep "matched the claim
STRINGS (SAME set / identical / agree) and this site states the claim in none of
them". Three full rounds (1, 4 and 5) had that line in scope.

## The discriminator is the question, not the instrument

The same 5270-file sweep was used **soundly** in the same run, hours later, to refute
CodeRabbit finding `382544`: "`def classify_spec` occurs in exactly one file over
5270 scanned". That is an **existence question about a literal token**, and a string
search decides it.

"Does any statement of this KIND remain?" is a **semantic-class question**, and a
regex over known phrasings is not merely incomplete for it — it is **incapable**,
because the class is closed under rephrasing and the sweep enumerates phrasings.

Enumeration fails the same way for a different reason: an enumeration is a snapshot
of the carriers you found, and closing a class by it asserts that the set you found
is the set that exists.

## Rule

Do not assert that a semantic class is closed. Instead:

1. **State the surface actually read** ("every doc and docstring carrier in the
   23-file plan surface, read").
2. **Mark everything outside that surface explicitly unknown.**
3. Reserve enumeration and string search for questions about **literal tokens**,
   where the instrument can decide the question asked.

This is what round 6's commit message did, and it is the only round whose closure
statement survived.

## Related recurrence

The identical shape appeared one layer down in the same run: the round-1 triage fix
`f17c36` offered `claimed_count` as a standalone alternative to `claimed[]`
membership, so a correction adding the *wrong* path passes the check with the
required path still absent (CodeRabbit `c3ddfb`). Cardinality cannot discharge a
membership requirement — see the sibling candidate lesson.
