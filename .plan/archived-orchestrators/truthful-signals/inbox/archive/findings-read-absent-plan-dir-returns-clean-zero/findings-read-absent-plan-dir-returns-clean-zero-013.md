envelope_version=1
sender_type=plan
sender_id=findings-read-absent-plan-dir-returns-clean-zero
epic=truthful-signals
kind=candidate-lesson
created=2026-08-30T14:16:51Z

component=pm-plugin-development:ext-self-review-plan-marshall
category=anti-pattern
disposition=reinforcement
source_plan=findings-read-absent-plan-dir-returns-clean-zero
source_pr=1369
source_findings=837c61,319dc9,56fc2f,a40f0f,d6fe8a,5aefc1,969f45

# Five assert-completeness defects in one run, every one of them in prose written to correct earlier prose — and the converging fix was DELETE the cardinal, 5 out of 5 times

## What the run produced

Six Q-Gate findings in one plan were the same archetype: a set, count, or partition asserted rather
than derived.

| Finding | The claim | Reality |
|---|---|---|
| `837c61` | heading "the Three Store States" | four states, on four independent enumerations |
| `319dc9` | argument-validation rejection at five flags | nine pre-store rejection sites |
| `56fc2f` | write-verb enumeration of 9, closed "not A … or I" | 10 — **`add`**, the most-used write verb, omitted from a security guarantee |
| `a40f0f` | "the three cross-skill consumers" | five; two of them (`github_pr.py`, `gitlab_pr.py`) **unhardened**, silently receiving an empty list on a refusal payload |
| `d6fe8a` | "the three cross-check routes" | four — the change **added two routes and incremented the count by one** |
| `5aefc1` | a guarantee deleted from 2 of its 3 sites | third site (a function docstring) still asserted it verbatim |

## The mechanism worth recording: the corrections self-seed

`969f45`'s resolution states it plainly, from inside the run:

> This plan has produced count and over-claim errors in **five separate places, every one of them
> in prose written to correct earlier prose**, and each correction round cost a full re-run of the
> head-dependent gates.

`5aefc1` is the sharpest instance: commit `a51aa8b4f` deleted a refuted guarantee from two of its
three sites and left the third — an **incomplete deletion introduced by the deletion itself**.

This is the same self-reproducing shape sibling message L2 records for the **vacuous-guard**
archetype in test code (a negative control, written to prove a fix, that could not itself fail).
L2 is the test-code half; this is the **prose half of the same phenomenon**. Both reproduce through
their own remediation. Filing separately because the surfacer each implies is different, and the
epic should see that the archetype is not confined to one medium.

## The converging remedy, validated 5/5

Every one of these was resolved by **deleting the cardinal, not by correcting it**:

- "the Three Store States" → "the Store States"
- the five-flag list → the class name alone
- the 9-verb enumeration → stated as the **complement** of the five reads already enumerated above
- "the three consumers" → a universal, made derivable
- "the three cross-check routes" → "every cross-check route"

The rule, stated for reuse: **a cardinal in prose is a claim that must be re-derived on every
change, and almost never is. Prefer a formulation that cannot go stale** — the class name, the
complement of an already-derived set, or a universal — over a number that will be correct exactly
until the next change. "Four" goes stale when a fifth state arrives; "the Store States" never does.

Note the asymmetry that makes this cheap: deleting a cardinal costs one edit and removes a
maintenance obligation permanently. Correcting one costs the same edit and re-arms the trap.

## The measured cost

Each correction round required **a full re-run of the head-dependent gates**. That is the argument
for a pre-emptive surfacer rather than a review-time catch: the defect class is cheap to detect
mechanically and expensive to catch late.

## Candidate surfacer for ext-self-review-plan-marshall

A `stale count-prose` surfacer already exists in the declared candidate set. Its recall on this run
was **zero for all six instances** — every one reached the Q-Gate stage. Two concrete widenings:

1. **Closed enumerations, not just cardinals.** `56fc2f` and `319dc9` carry no number at all — they
   are "not A, B, … or I" lists. Surface any closed enumeration in a normative sentence whose
   members are also enumerable from the argparse surface or a module constant, and diff the two.
2. **Cardinal-vs-sibling-enumeration disagreement in one document.** `d6fe8a` contradicted itself
   four lines earlier; `837c61` had "three" and "four" in the same sentence. A same-document
   cardinal that disagrees with a nearby prose enumeration is decidable without any cross-file
   join, and it caught nothing here.

## Relationship to the existing corpus

This reinforces the standing rule *"derive completeness, never assert it."* The new content is not
the rule — it is **(a)** the recurrence count in a single run (six), **(b)** the observation that
the corrections are the seed, and **(c)** the 5/5-validated fix direction (delete, do not correct),
which the rule does not currently carry.
