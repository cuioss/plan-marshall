envelope_version=1
sender_type=plan
sender_id=path-attribution-seam
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-01T20:48:38Z

component=plan-marshall:manage-metrics
category=bug
bundle=plan-marshall

# `record-dispatch-boundary` documents 6 of its 11 enum values — and the undocumented ones carry the majority of live rows — while its four context-load columns are zero on every row ever written

## What happened

Two separate defects in one verb, both found by reading this plan's own dispatch-boundary artifacts against the SKILL that documents them.

### Defect 1 — the documented enum is a strict subset that misses most real usage

`manage-metrics/SKILL.md` documents `--termination-cause` in two places (the Operations section and the Canonical invocations block), both listing **six** values:

```text
voluntary_checkpoint | task_complete_returned_verbatim | budget_yield |
harness_cancellation | error | clean_exit_queue_empty
```

The live argparse surface accepts **eleven**:

```text
$ manage-metrics record-dispatch-boundary --help
--termination-cause {voluntary_checkpoint,task_complete_returned_verbatim,budget_yield,
  harness_cancellation,error,clean_exit_queue_empty,step_complete,blocked_user_review,
  blocked_session_restart,task_batch_complete,agent_returned}
```

Five values — `step_complete`, `blocked_user_review`, `blocked_session_restart`, `task_batch_complete`, `agent_returned` — exist in code and appear nowhere in the doc.

This is not a cosmetic omission. On PLAN-CIS-023, **10 of 16 recorded rows** used two of the five undocumented values:

| Phase | Rows | Causes used |
|-------|-----:|-------------|
| `4-plan` | 1 | `task_batch_complete` (undocumented) |
| `5-execute` | 6 | `budget_yield`, `voluntary_checkpoint` ×3, `clean_exit_queue_empty` ×2 |
| `6-finalize` | 9 | `step_complete` ×9 (undocumented) |

The documented enum describes a **minority** of actual traffic. Anyone reading the SKILL to interpret a boundary file, or to write a consumer over it, will not recognise the value on 62% of this plan's rows. The SKILL's own prose compounds it by asserting the enum is closed — *"missing or unrecognised causes are script errors"* — which reads as a completeness guarantee for the six listed values.

### Defect 2 — the four context-load columns are zero on 16 of 16 rows

`record-dispatch-boundary` accepts `--input-tokens`, `--output-tokens`, `--cache-read-input-tokens`, and `--cache-creation-input-tokens`, described as "the per-DISPATCH counterpart to the per-PHASE four-field view". Every one of this plan's 16 rows, across all three phases, carries:

```text
input_tokens=0, output_tokens=0, cache_read_input_tokens=0, cache_creation_input_tokens=0
```

No dispatch site supplies them. They are declared, defaulted to `0`, appended to every row, and never populated — so the per-dispatch context-load view is dead on arrival.

The defaulting is what makes this quiet: a column that defaults to `0` renders a never-supplied value **identically** to a genuinely-measured zero. There is no way for a consumer to tell "this dispatch loaded no context" from "nobody ever wrote this field", so the emptiness is invisible in the artifact and only shows up when you notice that *every* row in *every* plan is zero.

## The rules

**Do X — when a flag's values are enumerated in a `## Canonical invocations` block, the block must enumerate the argparse `choices` exactly.** This is the index-completeness obligation applied to an enum: a partial list misrepresents the set as smaller than it is, and the omission is invisible at the list site because the list reads as complete.

**Do X — make this structural.** A plugin-doctor rule that parses the argparse `choices=[...]` for any flag whose values appear in the owning SKILL's canonical block, and asserts set equality, catches the whole class at edit time. The `ARGUMENT_NAMING_*` cluster is the natural home.

**Do X — a numeric column that defaults to the same value a missing measurement would produce needs a distinct absent marker, or a producer-coverage assertion.** Either write `null` for unsupplied, or add a test asserting at least one dispatch site passes each field.

**Not Y — do not add optional flags to a recorder ahead of the producers that fill them.** The four columns shipped with a documented purpose and no caller; the artifact has been accumulating zeros since.

## Detection

Both are mechanical. Defect 1: `set(argparse choices) != set(documented values)`. Defect 2: for any dispatch-boundary file, `all(row[c] == 0 for c in the four columns for every row)` across a corpus of plans is a producer-coverage failure, not a measurement.

## Why it is worth acting on

The termination-cause enum is the input to the retrospective's re-dispatch correlation, and the four columns are the input to per-dispatch cost attribution. Both are measurement surfaces for the epic's own instrumentation. An enum whose doc omits the values that dominate real traffic, and a set of columns that has never carried a non-zero value, are both cases of instrumentation that looks present and measures nothing.
