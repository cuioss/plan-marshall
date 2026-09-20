envelope_version=1
sender_type=plan
sender_id=orchestrator-inbox-and-landing-residue
epic=truthful-signals
kind=candidate-lesson
created=2026-08-24T16:54:59Z

component=plan-marshall:plan-retrospective
category=bug
confidence=high
source_plan=orchestrator-inbox-and-landing-residue
source_aspects=plan_efficiency,log_analysis

# Billing-weighted cost is structurally unmeasured at retrospective order 995

## Context

The plan-efficiency aspect is instructed to read `billing_weighted_total` as a first-class `Billing (cost)` column with its own total. At `plan-retrospective`'s `order: 995`, that column is empty and cannot be anything else:

- `manage-metrics generate` returns `totals_billing_weighted_total: 0` with `totals_billing_weighted_total_population_count: 0`.
- `metrics.md` renders `-` in the `Billing (cost)` cell of all six phase rows and of the Total.
- No phase row carries `input_tokens` / `output_tokens` / `cache_read_input_tokens` / `cache_creation_input_tokens` at all.

`billing_weighted_total` is written per phase only by `manage-metrics enrich`, which walks the parent and subagent transcripts. Nothing in the retrospective workflow calls `enrich`, and whatever calls it in finalize runs at a later `order` than 995.

## Root cause

This is the same ordering shape the workflow already documents and fixes for a sibling field. Step 2.5 exists precisely because "the retrospective reads an unclosed accumulator" (recorded as R2 in the plan that introduced it), and its remedy is to call `manage-metrics generate` inside the retrospective rather than rely on a later step's ordering.

`billing_weighted_total` has the identical problem and no equivalent remedy: `generate` reconciles the durable accumulators, but it does not run the transcript walk, so the four-field view stays absent and the derived cost stays zero. A reader of the report sees a `Billing (cost)` column of dashes and has nothing telling them whether the run was cheap or unmeasured.

The `population_count: 0` companion is doing its job — it says the zero was computed over an empty population — but it is reported inside the `generate` TOON, not rendered next to the dashes in `metrics.md`, so the report surface does not carry the discriminator.

## Proposed action

- Extend Step 2.5 to run `manage-metrics enrich --plan-id {plan_id} --session-id {session_id}` before the plan-efficiency aspect reads `metrics.md`, on the same reasoning that already justifies the `generate` call there. `enrich` leaves a dispatched `total_tokens` byte-identical (explicit-wins), so the reconcile is non-destructive.
- Note the session-set interaction: `enrich` takes one `--session-id`, and this plan recorded two. A single-session enrich will attribute only that session's transcripts, so the same session-coverage fix proposed for the chat-history aspect applies here.
- Render the population qualifier next to the column: a `Billing (cost)` total of `-` should read as `- (n=0/6, unmeasured)` so a dash is not mistaken for zero cost.

## Evidence

- `manage-metrics generate --plan-id orchestrator-inbox-and-landing-residue` → `totals_billing_weighted_total: 0`, `totals_billing_weighted_total_population_count: 0`
- `metrics.md` Phase Breakdown — `Billing (cost)` column is `-` on every row
- aspect: plan_efficiency — `billing_weighted.note: "population_count=0 ... manage-metrics enrich never ran for this plan. The derived-cost column is UNMEASURED, not zero."`
- `plan-retrospective/SKILL.md` § Step 2.5 — the precedent: an order-995 reader must close its own inputs rather than depend on an order-998 writer
