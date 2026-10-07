envelope_version=1
sender_type=plan
sender_id=plan-12-tool-triage
epic=process-compliance
kind=finding
created=2026-09-29T13:43:59Z

# One inline self-review loop-back re-fires every earlier head-dependent settle step

## Observed

plan-12-tool-triage finalize, loop-back iteration 1: `pre-submission-self-review` (order 8) looped back with
8 findings; the fix commit (dbc7673c5, 5 files — docs, one docstring, two test modules) advanced HEAD. On the
item-1 re-entry every head-dependent step recorded earlier in the settle band had to be re-decided, and the
verdict-currency classifier returned `invalidated / verdict_inputs_undeclared` for ALL of them:

- `project:finalize-step-lessons-housekeeping` (order 4) — its classification reads the plan outcome, not the
  five touched files;
- `default:finalize-step-simplify` (order 5) — re-reviews the whole 42-file changeset;
- `project:finalize-step-plugin-doctor` (order 6) — its own doc records why it cannot declare `verdict_inputs`.

So a one-round, five-file inline fix costs three extra dispatches (plus the self-review re-fire and its
verifier) before the pipeline even reaches the step that looped back — about 350K tokens in this run's
measured per-step figures — and each further loop-back round repeats the whole cascade.

## Why it matters

`verdict_inputs` is opt-in and fail-closed by design, which is correct. But no settle-band step declares it,
so in practice the classifier never preserves a verdict: the mechanism introduced to stop "re-run to re-confirm
the identical answer" currently changes nothing. The steps that loop back most (self-review, order 8) sit
AFTER the steps that pay to re-fire (4-6), so the cost lands on every self-review round.

## Suggested fix

Declare `verdict_inputs` where it is sound (lessons-housekeeping reads references + request, not source;
simplify's surface is the plan footprint), and consider ordering the loop-back-prone reviewer before the
expensive re-reviewers, or scoping a self-review-originated re-entry to steps whose inputs the fix touched.
