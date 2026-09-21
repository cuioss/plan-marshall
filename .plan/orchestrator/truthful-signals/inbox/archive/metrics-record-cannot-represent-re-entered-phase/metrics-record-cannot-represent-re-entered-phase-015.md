envelope_version=1
sender_type=plan
sender_id=metrics-record-cannot-represent-re-entered-phase
epic=truthful-signals
kind=candidate-lesson
created=2026-08-09T21:30:20Z

# Candidate lesson: a denominator that states WHEN it was sampled and not WHAT it counted — `files_modified` names modification and measures declaration

**Source**: PLAN-TRUTH-055 post-landing retrospective
**Defect class**: name-asserts-more-than-the-derivation-computes (the plan's own rename archetype, in the plan's own new field family)
**Theme fit**: confident-signal-hides-a-caveat — the confident signal is a field name

## The finding

D6 gave the metrics record its first denominators, each paired with a `{denominator}_sampling_point`
companion and a shared `denominators_sampled_at` timestamp. That pairing answers **WHEN** the count was
taken, and it works — see the closing section for a case where it did real work.

No denominator carries a companion answering **WHAT POPULATION** it counted. And one of the three needs
it, because its name and its derivation disagree:

> `data-format.md:501` — "`files_modified` | int | Derived by `generate` — the length of
> `references.json`'s `affected_files` list."

`affected_files` is the plan's **declared surface**. By design it includes read-only consumer surfaces
that a scope sweep enumerated and then found unchanged — which is disciplined behaviour, and this plan
did it three times, logging each sweep as *"none promoted to write-replace"*. The field silently counts
those as modifications.

## Measured on this plan

| Quantity | Value |
|----------|-------|
| `files_modified` in the record | **34** |
| Files in the merged squash `2586ef00c` | **25** |
| In both | 23 |
| Declared but never modified | 11 (spot-checked: all read-only consumer surfaces) |
| Modified but never declared | 2 |

Every ratio dividing by `files_modified` understates per-file cost by ~36%. `tokens_per_file_modified`
reads 147,549 on the declared 34 and 200,666 on the achieved 25.

## Why this is the plan's own archetype

PR #1129 renamed `partial` → `any_phase_missing_end_time` for exactly one reason, stated in its own
standard: the old name **asserted a completeness verdict the check never computed**. The rename made
the narrowness visible at the point of use.

`files_modified` asserts modification and measures declaration — and it shipped in the same change,
four sections later in the same document.

The module already owns the remedy. One section earlier, its *numerators* carry precisely this
companion: `total_tokens_population` exists because, in that field's own words, **"`total_tokens` names
a total, not a measured population"**, and a consumer "MUST read the discriminator; it may not infer a
population from the field's name." The identical sentence is true of `files_modified` and nothing on
the row says so.

## Candidate rule

> A `{denominator}_sampling_point` answers WHEN and is not sufficient. Any count whose NAME implies a
> population must also carry a `{denominator}_population` discriminator, from the same closed-vocabulary
> convention — because a reference class is fixed by two coordinates, the moment it was read AND the
> set it was read over, and stating one of them makes the figure look anchored while it is not.

> Before adding a discriminator to a field family, check whether a SIBLING family in the same module
> already carries the discriminator you are about to omit. Here the numerators had it and the
> denominators did not, in one file, in one change.

Concrete shape: emit `files_modified_population: declared_surface` today. A second value,
`achieved_footprint`, becomes available once the footprint is resolvable at retrospective time (see the
sibling finding on plan-retrospective's step ordering).

## The half that worked — worth keeping

`tasks_completed` read **10** while all **11** tasks are done: TASK-011 completed inside the re-entered
5-execute at 18:33Z, three minutes after `denominators_sampled_at` (18:30:38Z). That staleness was
**detectable only because the sampling point was recorded**. On the pre-change record the same figure
would have been an unfalsifiable 10. D6 is doing its job; the gap is that it fixed one of the two
coordinates.
