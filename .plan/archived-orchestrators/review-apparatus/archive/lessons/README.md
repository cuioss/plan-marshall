# Lessons absorbed into this epic

epic: review-apparatus

Each file here is a lesson body copied **verbatim** out of the global corpus
(`.plan/local/lessons-learned/`) before that lesson was retired from it. The filename prefix is the
bucket the triage assigned: `carry-`, `stale-`, `duplicate-`, `covered-`.

⛔ **These are records, not a working queue.** The live obligation lives in the staged spec or the
practice section named in the Destination column below; this directory is where the original wording
stays readable after the corpus entry is gone. Every id also carries a tombstone in the corpus's
`.tombstones/`, with the removal verdict and reason.

**Population**: 36 of 172 active lessons were in-epic (26.2% of the corpus was read; 45 bodies read,
127 excluded on title alone). The corpus went 172 → 136. The selection rule and the per-lesson
evidence are in the epic's `decision.log` entry for 2026-09-18.

## carry — in-epic, not covered, incorporated into the ledger (13)

| id | Defect in one clause | Destination |
|---|---|---|
| 2026-09-08-22-002 | `await_fresh_review` credits another bot's review as a per-bot completion signal; `_match_review` has NO author gate at HEAD, by a recorded design decision | `PLAN-PR-056` D11 |
| 2026-09-06-16-001 | `pr merge-queue` reports `enqueued=true` corroborated only by the branch rule being active, with no post-condition read | `PLAN-PR-064` D11 |
| 2026-09-08-20-002 | `review_commitments reconcile` derives its population from `pr-comment` findings only, excluding every qgate finding by construction | `PLAN-PR-062` D4 amendment |
| 2026-09-05-07-007 | the same verb runs at finalize order 9, before every producer of the findings it reconciles — an ordering defect, not a legibility one | `PLAN-PR-062` D4 amendment |
| 2026-09-04-08-015 | a triage remedy whose whole artifact is a sentence is deleted by a later correct accuracy pass, voiding a decision with nothing noticing | `PLAN-PR-063` amendment |
| 2026-09-05-07-001 | `false_positives_count` conflates administrative rejections with refuted premises, over- and under-reporting at once | `PLAN-PR-063` D8 amendment |
| 2026-09-08-22-003 | the `--measured-diff-size` crash shipped undeclared in #1473; the SKILL.md empty-argument guarantee scope and its sweep did not | `PLAN-PR-058` D0/D7 amendment |
| 2026-08-27-16-004 | the in-run self-review gate and the external bot have complementary blind spots; the Class-A predicate was never ported into the surfacer | `review-practice.md` § 6 |
| 2026-09-13-09-002 | the epic's most-exercised standing rule — carry a review-pipeline detector defect forward, never fix it in the landing PR — was unwritten | `review-practice.md` § 7 |
| 2026-09-13-20-006 | rewriting a guard's claim to match its narrower reality is a deferral that hands the close to the reviewer | `review-practice.md` § 4 |
| 2026-09-05-07-009 | two readers of `required_bots`/`optional_bots` take opposite dispositions on the same unregistered token | `PLAN-PR-061` amendment |
| 2026-09-03-16-001 | a finding's diagnosis and its resolution are separately falsifiable, and so is the triager's own claim | `review-practice.md` § 8 |
| 2026-09-04-17-001 | `pr_intent_section` truncates at a byte offset, and the three surrounding properties compose into an unrepairable trap | `PLAN-PR-064` D3 amendment |

### Second pass — the self-review surface (5 more, absorbed the same day)

`PLAN-PR-062` absorbs `PLAN-PR-049` whole and declares `_self_review_detectors.py`,
`_self_review_patterns.py` and that skill's SKILL.md on its Expected Surface, so that component is
in-epic for this pass. Seven were examined; five are here.

| id | Defect in one clause | Destination |
|---|---|---|
| 2026-08-27-16-006 | a closed-set literal beside the named symbol defining the same set escapes every advertised candidate class; 4 of 5 instances are not count-prose | `PLAN-PR-062` D5 amendment + `review-practice.md` § 6 |
| 2026-09-04-08-011 | a claim falsified only by ABSENT behaviour has no second diff site, so a pair-scoped surfacer is structurally blind to it | `review-practice.md` § 6 (needs an admissibility ruling first) |
| 2026-09-04-08-013 | a count-or-kind claim in prose owes the derivation the metric beside it already receives | `PLAN-PR-062` D5 amendment |
| 2026-09-05-16-001 | 27% of one loop's findings were self-seeded across five chains, one oscillating; the loop reports no such tally | `PLAN-PR-062` D8 amendment |
| 2026-09-15-06-001 (dup) | a roster label classifying a STEP does not classify its sub-steps — keeper `2026-09-03-16-001` | `review-practice.md` § 8 |

⛔ **Two of the seven were NOT absorbed and are NOT archived here** — they stay in the global corpus,
routed to `truthful-signals` by inbox message, because they fail the PR test (neither is about the
PR-review pipeline; both are about the in-run self-review instrument, and both carry that epic as their
`source_epic`): `2026-09-13-20-003` (self-application pass when the plan's subject is a defect
archetype) and `2026-09-15-06-002` (six vacuity modes in a self-review guard). ⭐ The surface-level
obligation they imply for `PLAN-PR-062` D0 is recorded in that spec; the LESSON is not ours.
⚠ A ledger cannot see a duplicate in another ledger — do not re-absorb them later without checking
`truthful-signals` first.

## stale — claim no longer reproduces at HEAD (3)

Each was verified against a symbol read first-party at `main`; the removal reason names it.
`2026-08-31-08-002`'s reusable half (write a guard's test from its PURPOSE, with a matched negative
control) was carried into `review-practice.md` § 8 before retirement.

## duplicate — retired in favour of a named keeper (3)

`2026-09-06-07-001` → keeper `2026-09-06-17-001`; `2026-09-05-11-001` → keeper `2026-09-08-22-003`;
`2026-09-05-23-001` → keeper `2026-09-08-20-002`. Both keepers were themselves retired in this pass
(covered / carried), so the archive holds all six bodies.

## covered — already carried by a staged spec, a landing, or the practice (17)

Each removal names its covering clause and the concrete input that clause resolves, in the tombstone.
⚠ Twelve of the seventeen are covered by a **staged** spec rather than a shipped one: if a spec is
retired without shipping, re-read that spec's covering deliverable here before assuming the lesson's
defect is closed.
