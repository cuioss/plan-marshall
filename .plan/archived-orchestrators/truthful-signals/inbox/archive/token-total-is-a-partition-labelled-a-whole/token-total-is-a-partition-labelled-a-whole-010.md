envelope_version=1
sender_type=plan
sender_id=token-total-is-a-partition-labelled-a-whole
epic=truthful-signals
kind=candidate-lesson
created=2026-08-03T12:54:53Z

component=plan-marshall:manage-metrics
category=anti-pattern
bundle=plan-marshall

# Four context-load columns exist on every dispatch-boundary row, are written by no caller, and are uniformly zero — a schema slot is not a measurement

## What was observed

`record-dispatch-boundary` accepts and persists four per-dispatch context-load fields — `input_tokens`, `output_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens` — documented as *"the per-DISPATCH counterpart to the per-PHASE four-field view `enrich` writes"*.

Across this plan's three dispatch-boundary ledgers — `4-plan` (1 row), `5-execute` (5 rows), `6-finalize` (13 rows) — **all four columns are `0` on all 19 rows.** Not sparse, not partially populated: uniformly zero. Every producer call site omits the flags, so the columns default to `0` and persist as though measured.

Zero is indistinguishable from unmeasured here. A consumer reading `cache_read_input_tokens: 0` cannot tell whether this dispatch re-read no context (impossible for a dispatch that consumed 541,951 tokens) or whether nobody passed the value. The schema promises a measurement the pipeline never takes.

This matters more than a normal empty column because **context load is where the cost is**. A byte costs 1.25x on entry and 0.1x on every later turn; `cache_read` dominates billing. These four columns are the only per-dispatch view of that, and they are structurally empty.

## The same shape, two more instances in the same surface

1. **`termination_cause` values that are not in the documented enum.** The documented set is `voluntary_checkpoint | task_complete_returned_verbatim | budget_yield | harness_cancellation | error | clean_exit_queue_empty`, and the contract states unrecognised values *"are rejected as script errors (there is no implicit fallback)"*. The ledgers contain `task_batch_complete` (1 row) and `step_complete` (13 rows) — **14 of 19 rows carry a cause absent from the enum**, and the analyzer reports `unknown_count: 0` for all of them. Either the enum is stale or the rejection is not enforced; both readings mean the documented contract is not the operative one.
2. **A report section with a renderer, a registry key, and no producer.** `compile-report` recognises the aspect key `dispatch_boundaries` and renders a `Phase Dispatch Boundaries` section, but no aspect in the documented Step 3 dispatch table emits a fragment under that key. The section is therefore omitted on every run and reported as benign. (This one is a **recurrence** — the producerless `dispatch_boundaries` row is already known to this epic; it is confirmed still live.)

## The generalisable rule

**A field that no producer writes is not a measurement — it is a claim that one exists.** Defaulting an unwritten numeric field to `0` converts "we never looked" into "we looked and found nothing", which is the strongest possible false signal because it is silent and looks like data.

Three checks worth making standing practice:

1. **Default absent numerics to absent, not to zero.** If a caller did not supply the value, omit the key or write `null`. Reserve `0` for a measured zero. This makes "unmeasured" queryable instead of invisible.
2. **Assert every declared column has at least one producer.** A population-derived check — for each persisted field, find a call site that supplies it — is cheap and catches the whole class at edit time. Note this plan *touched* `record-dispatch-boundary` and its test file and still did not notice, because the tests exercise the script's own flag handling, never the set of real callers.
3. **When a doc declares a closed enum with hard rejection, test the corpus against it, not just the parser.** The enum here is contradicted by 74% of the live rows; a single scan of the on-disk ledgers would have surfaced it.

## Impact

Direct epic-theme fit and directly load-bearing on the token-reduction priority: the per-dispatch context-load view is the natural instrument for finding where context spend actually goes, and it currently reports zero everywhere. Any analysis built on it would conclude — confidently and wrongly — that cache read is negligible.
