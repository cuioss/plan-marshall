envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-08-08-01
epic=review-apparatus
kind=finding
created=2026-08-08T16:27:27Z

## Routed lessons cluster C18 — self-review completeness (9 corpus instances)

**From**: `lessons-handling-26-08-08-01` (lessons-handling orchestrator run, 2026-08-08).
**Why you**: pre-submission self-review is review apparatus; the PR/review test wins outright.
**Suggested home**: `PLAN-PR-018` (self-review-rescans-the-whole-surface-every-round).
**You decide**: fold, restage, or decline. Nothing was written into your tree.

### The cluster

Nine active lessons about self-review failing to close the class it opened.

| Lesson | Claim |
|--------|-------|
| 2026-07-27-08-001 | self-review must enumerate every relational case a new guard/scanner/boundary-check's own condition implies, not only the case that motivated it |
| 2026-07-28-08-001 | a fix is the highest-risk moment in the pipeline; mandate a named adversarial self-re-read of every fix's own diff |
| 2026-07-29-18-006 | audit a classifier's symmetric peers for the defect's SHAPE, not its text |
| 2026-08-02-15-004 | apply the rule you are enforcing to the artifacts your own change creates |
| 2026-08-02-15-005 | a test name and docstring are a coverage claim — do not promise universal and assert existential |
| 2026-07-18-05-002 | contract-change prose mirrored across N locations: sweep all occurrences in one pass, not one-at-a-time |
| 2026-06-30-20-001 | a helper mirroring a canonical must mirror its full sibling-invariant surface (exception set, guard/error-shape flows, a parity test per shared branch) |
| 2026-07-18-14-001 | normative worked-examples are a semantic-correctness surface structural self-review misses — verify each example actually models the discipline it preaches |
| 2026-08-03-17-001 | an aggregation states its predicate precisely and leaves the set it ranges over implicit |

### Why this fits PLAN-PR-018 specifically

Your epic anchor records that `PLAN-PR-018` already absorbed the sharpest instance of this
shape — the scope-of-sweep-versus-scope-of-claim trap, where a delta-scoped pass made a claim
wider than the scope searched, and the recurrence *migrated granularity under fixing*
(round 2 missed a file, round 3 missed a clause inside the very line the fix edited, round 4
asserted a corpus-wide zero while three siblings survived in the same file).

Six of the nine members above are that same shape at a different granularity:
`2026-08-03-17-001` (predicate stated, set implicit) is the abstract form of it;
`2026-07-27-08-001` and `2026-07-29-18-006` are the guard-relational and symmetric-peer
variants. `2026-08-02-15-004` is the reflexive case your own standing rule C5 states as
"a rule applied to a sibling's work and not to my own is not yet a rule".

`2026-07-18-14-001` is the one member that is NOT the same shape — it is about worked examples
being semantically wrong rather than sweeps being narrow. It may deserve separation.

### Claim labels

- **OBSERVED**: lesson ids, components, categories, titles; `PLAN-PR-018` id/slug/status.
- **HYPOTHESIS (verify-at-outline)**: that each is still open. Confirm/refute artifact: the
  candidate-surfacer set in `ext-self-review-plan-marshall`, checked per member for whether the
  case is already surfaced.

### Provenance

Corpus snapshot: `.plan/local/orchestrator/lessons-handling-26-08-08-01/archive/{lesson_id}.md`.
Dispositions: `.plan/local/orchestrator/lessons-handling-26-08-08-01/dispositions.md`.
Nothing retired; retirement is deferred behind `PLAN-TRUTH-044`.
