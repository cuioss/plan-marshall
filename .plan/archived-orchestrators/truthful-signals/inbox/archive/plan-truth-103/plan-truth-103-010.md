envelope_version=1
sender_type=plan
sender_id=plan-truth-103
epic=truthful-signals
kind=candidate-lesson
created=2026-09-13T12:09:09Z

# Candidate lesson (RECURRENCE + one new sub-rule): deletion terminates a self-seeded chain — and when the restatement is a NUMBER, delete the number and keep the structural claim

**Source plan**: plan-truth-103 (PR #1475)
**Evidence**: first-party 6-finalize Q-Gate findings `c52749` → `9bacd8` (self-seeded), and the `80e378` / `b4d82a` / `82f5bf` cohort, plus `0892c4`.
**Dedup note**: not among the 10 findings already routed this run.

## ⚠ This is a RECURRENCE, not a new discovery — merge, do not duplicate

PLAN-TRUTH-089 (shipped, PR #1399) already established the governing rule: **the only terminating move is to replace the restatement with a POINTER at its source** — correcting authors a new claim, deleting under-declares. This run reproduced that result independently (5 of 5 convergent fixes were a deletion or a pointer, zero were a corrective restatement), which is corroboration of an existing lesson. The orchestrator should treat the bulk of this message as a `## Recurrence` arm on the existing lesson.

One increment below is genuinely new.

## Corroboration: the chain on this run

- `c52749` — a repository-wide absence claim ("every regex **in this repository** …") whose sibling section bounded the SAME measurement narrowly. Fixed by narrowing to the substrate actually swept, plus a pointer at the sibling section for the bound.
- `9bacd8` — **self-seeded by the fix for `c52749`**. The narrowing routed the bound THROUGH a table, and the table's row mixed two populations: substrate `.claude/** remainder (46 files)` came from a git enumeration while its `43 read / 3 skipped as non-text .pyc` partition came from a filesystem walk. `43+3=46` was an arithmetic coincidence across two different populations — `git ls-files .claude` returns 47 tracked entries, not one a `.pyc`. Fixed by stating the substrate as a reproducible RULE (`git ls-files .claude` less the row above) rather than a count, and **deleting the `.pyc` skip line outright** because it described files the stated substrate never contained.
- `0892c4` — a docstring asserting "the mutating side is NOT this one" while six `get_settings_path(args.target)` call sites (two with `project` as the argparse default, both followed by `save_settings`) mutated exactly the shadowed file. Fixed by **deleting the universal claim** and pointing at the sibling docstring seven lines away that already stated the boundary correctly.

## The new sub-rule: delete the decorative integer

Two of the cohort's terminating deletions removed a **number** whose only fault was that it tracked churn outside the plan's control.

- `b4d82a` — the doc claimed sweeping the unescaped `Write(` returns "a larger but wrong set — **39 files**". At HEAD the same sweep returned 38. The STRUCTURAL claim was untouched and still true (the set is larger and still omits `permission_doctor.py` entirely); only the bare integer no longer re-derived. The branch had absorbed 5 upstream commits at rebase, so the integer tracked inventory churn. **Correcting 39→38 would have re-seeded the identical finding on the next inventory change.** Fixed by deleting the integer: "returns a larger set that omits `permission_doctor.py` entirely" — the structural claim the number was only decorating, and which re-derives on any inventory.
- `80e378` — a row restated a pre-fix zero (`0 Edit\( matcher sites`) untensed, while re-running its own method at HEAD returned the exact inverse (16 `Edit\(` sites, 0 `Write\(`). The claim already had a correctly temporally-hedged home elsewhere. Fixed by **deletion rather than re-tensing**, so the claim has one home and cannot invert again.

**The sub-rule**: when the restatement under repair is a measured quantity, ask whether the number is load-bearing or decorative. A number that decorates a structural claim, and that tracks a population outside the change's control, must be **deleted**, not corrected — correcting it schedules the same finding for the next run. If the number IS load-bearing, replace it with the reproducible rule that derives it (`9bacd8`'s remedy), never with a fresher literal.

This is the intersection of two already-recorded archetypes — "derive completeness, never assert it" and "stale count-prose" — and the actionable residue is the *disposition rule* above, which neither states: **correct nothing; delete, or publish the derivation.**

## Honest limit

All five chains here are documentation-layer claims in one bundle's standards docs. The sub-rule is stated generally, but its evidence base on this run is narrow, and the orchestrator should weigh whether it generalizes beyond prose-with-counts before promoting it into a governing skill.
