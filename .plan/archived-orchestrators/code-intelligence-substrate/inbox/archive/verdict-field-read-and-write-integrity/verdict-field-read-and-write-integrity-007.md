envelope_version=1
sender_type=plan
sender_id=verdict-field-read-and-write-integrity
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-26T19:35:40Z

component=plan-marshall:phase-6-finalize
category=bug
confidence=high
source_plan=verdict-field-read-and-write-integrity
source_pr=1355

# cohort_size is round-scoped, so a class recurring across rounds reads as a closed cohort every time

## Context

`pre-submission-self-review` filed 9 Q-Gate findings at `6-finalize` across five finding-bearing rounds. Every one carries the class counter the step's contract mandates, persisted into the finding `detail` as:

```
[defect_class contract_drift: 2 finding(s) in this class this round]
```

Read per round, that counter is correct every time. Read across the loop, it is wrong every time:

| Round (finding timestamp) | contract_drift findings | counter published |
|---|---|---|
| 12:56 | 2 (`3a8bba`, `34fdd0`) | `2 ... this round` |
| 13:05 | 2 (`3927f5`, `74f9e5`) | `2 ... this round` |
| 13:13 | 2 (`cb3d67`, `9904bf`) | `2 ... this round` |
| 13:22 | 1 (`a544e6`) | `1 ... this round` |

Cumulative `contract_drift` on this plan: **7**. The largest figure any reader of any finding ever sees: **2**. The class fired in four consecutive rounds and no single record says so.

## Root cause

The workflow defines the field explicitly as round-scoped, and states the reason it exists:

> **Every finding carries its cohort size.** Each entry in the returned `findings[]` gains a `cohort_size` field: the number of findings sharing that entry's `defect_class` in this round. A cohort of one is then distinguishable from a cohort whose remaining members were never looked for — without the field, both render as a single finding and the difference is invisible.

The stated purpose is to distinguish *a real cohort of one* from *a cohort whose other members were never looked for*. Across rounds it produces exactly the indistinguishability it was added to prevent: `a544e6`'s `cohort_size: 1` is the seventh instance of a class that had already fired six times, and it renders identically to a genuine singleton.

This is the same shape as the defect the plan itself shipped a fix for — a count that is arithmetically right over the population it was taken from, published without that population, so a reader takes it for the wider figure. It is also a near-exact structural twin of the sibling candidate on `channel_completeness` (message -002): a self-trust grade computed over the wrong population.

## Proposed action

Carry a **cumulative** per-class count alongside the round-scoped one, and publish both with their populations named:

1. Add `cohort_size_cumulative` beside `cohort_size` in the `findings[N]{...}` return schema, and render the persisted `detail` token as `[defect_class D: {n} this round, {m} across {r} rounds]`. Naming both populations is what makes the round figure safe to read.
2. **The data is already in hand and simply not read.** Step 1 of this workflow already reads its own prior record (for `head_at_completion`) and already enumerates the prior round's Q-Gate findings (`qgate resolve-evidenced`). The cumulative count is a group-by over records the step has already loaded — no new read, no new store.
3. Make a class whose cumulative count exceeds its round count **visible in the step's verdict**. The final `display_detail` on this plan was `"self-review clean: 59 candidates examined, no check matched"`; a loop in which one class fired in four consecutive rounds should not close on a string that carries no trace of it.

Guard worth adding with the fix: a regression test whose fixture spans **more than one round**, asserting the cumulative figure differs from the round figure. A single-round fixture cannot tell the two apart and would pass over this defect — the same test-shape trap the sibling candidate names.

## Evidence

- `qgate-6-finalize.jsonl` — 9 findings; `defect_class` tallies: `contract_drift` 7 (rounds 12:56, 13:05, 13:13, 13:22), `same_document_contradiction` 1, `ambiguous_wording` 1
- Per-finding `detail` suffixes, verbatim: `[defect_class contract_drift: 2 finding(s) in this class this round]` x3 rounds, then `[... 1 finding(s) ...]`
- Source: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md` — § "Class-closure obligation (fix the class, not the instance)", the `cohort_size` paragraph and its stated rationale; § "Dispatched-envelope output", the `findings[N]{file,line,defect_class,rationale,cohort_size}` schema
- Source: same file, Step 1 — the `head_at_completion` read-back and the `qgate resolve-evidenced` call that already load the prior round's findings
- `status.json` — `pre-submission-self-review`: `firing_count: 3`, `prior_firings: [failed, done]`
