envelope_version=1
sender_type=plan
sender_id=token-total-is-a-partition-labelled-a-whole
epic=truthful-signals
kind=candidate-lesson
created=2026-08-03T12:32:54Z

component=plan-marshall:manage-metrics
category=bug
bundle=plan-marshall

# A fix that removes a mislabel can reintroduce the same mislabel on its own second run — check the fix for idempotency against its own target defect

## What was observed

PLAN-TRUTH-035 exists to remove one defect: *no rendered figure may present a main-context measurement under a dispatched-population label.* The fix it shipped reproduced that exact defect on a second invocation.

`cmd_enrich` in `manage-metrics.py` keyed the inline fold on the presence of `total_tokens`:

```python
inline_main_context = _inline_main_context_sum(phase_row)
if not phase_row.get('total_tokens'):
    # Inline-only signature: no dispatched total exists to preserve.
    if inline_main_context:
        phase_row['total_tokens'] = inline_main_context
        phase_row['inline_main_context_tokens'] = inline_main_context
        phase_row['total_tokens_population'] = POPULATION_INLINE
    else:
        phase_row['total_tokens_population'] = POPULATION_DISPATCHED
elif inline_main_context:
    phase_row['inline_main_context_tokens'] = inline_main_context
    phase_row['total_tokens_population'] = POPULATION_MIXED
```

Run 1 on an inline-only phase (e.g. `1-init`): `total_tokens` is empty, the inline sum is folded in, row is stamped `inline`. Correct.

Run 2 on the same file: `total_tokens` is now truthy — **because run 1 wrote it** — so the guard is false, control falls to `elif`, and the row is re-stamped `mixed`. The fold is then indistinguishable from a dispatched total. Two consequences, both silent:

1. `_eligible_dispatched_measures` stops excluding the folded main-context `total_tokens`, so a main-context figure can win the dispatched maximum and carry the `main-context-window` marker.
2. `cmd_generate` stops collecting the row into `inline_population_phases`, so the **Total row silently loses its `(spans populations)` marker** — the precise marker this plan was built to add.

The guard's own comment (*"no dispatched total exists to preserve"*) was true only of a never-enriched row. It read a value the function itself had written as though it came from somewhere else.

## Who caught it

Not the plan. Not its self-review. Two review bots, independently, on the same lines:

- **CodeRabbit**, inline at `manage-metrics.py:2352`, with the correct fix (key off the `total_tokens_population` discriminator via an `already_inline` test).
- **pr-agent** (`cuioss-review-bot`), as a "State Mutation Bug" focus area in its PR Reviewer Guide, with the same trace.

Fixed on-branch by TASK-14. CodeRabbit's review body separately flagged that no test drove an `inline` row carrying a competing dispatched measure through `cmd_generate` — the coverage gap and the defect were the same surface, which is why the defect was reachable.

## The generalisable rule

**A write-then-read-your-own-write guard is not idempotent.** When a function's branch condition tests a field that the same function populates, the second invocation takes a different branch than the first — and if the two branches assign different labels, the function is a mislabel generator on re-entry.

Two checks worth making standing practice:

1. **Run the fix twice.** For any function that stamps a classification onto a persisted record, assert `f(f(x)) == f(x)`. Cheap, mechanical, and it would have caught this before review.
2. **When a plan's purpose is to eliminate a defect class, test the plan's own output against that class.** This plan added a discriminator to distinguish populations and then wrote a code path that corrupted the discriminator. The strongest available test was the plan's own acceptance criterion, applied to the plan's own artefact.

## Impact

`manage-metrics enrich` is re-runnable by design and is invoked from more than one finalize path, so the second-run branch was live, not hypothetical. Any archived plan enriched more than once carries a `mixed` label on a row that is `inline`, and its Total is missing `(spans populations)`.

Beyond `manage-metrics`: the archetype is *the fix reproduces its target defect*, previously seen on PLAN-86 (`phase-4-plan` Step 8 silently dropping a rejected persist at a call site the plan itself created). This is now at least the second instance. It is worth treating as a named pre-submission check rather than as two coincidences.
