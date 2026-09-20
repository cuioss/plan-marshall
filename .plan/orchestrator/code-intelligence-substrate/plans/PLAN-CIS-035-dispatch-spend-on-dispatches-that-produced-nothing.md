# PLAN-CIS-035: A Third Of Finalize's Dispatch Spend Went To Dispatches That Terminated In Error

epic: code-intelligence-substrate
workstream: WS-04

> Staged 2026-08-03 from the PLAN-CIS-001 landing (#1084), **first-party to this epic's own run**.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.

## Objective

On PR #1084, **32% of `6-finalize`'s recorded dispatch spend went to dispatches that terminated in
`error` or `blocked_session_restart`** — dispatches that produced no deliverable, no finding, and no
decision. The phase burned **3.6M tokens against `5-execute`'s 0.82M (4.4×)**.

Make a failed dispatch cheap: detect the terminal-failure classes early, stop paying full context
cost for a dispatch that cannot complete, and **report the waste as a first-class figure** rather
than leaving it inside an aggregate.

## ⭐⭐ Why this is the RIGHT KIND of token lever — it is on the correct side of the anti-goal

The epic's binding anti-goal (measured 2026-08-03 over the #1069 effort raise) is that **lowering
examination depth is not a sanctioned saving** — cost per defect-found *improved* when effort rose, so
any lever whose mechanism reduces to *"examine less"* is rejected on that ground.

⭐ **This lever is the opposite shape and is the clearest instance yet of the legitimate target.** A
dispatch that terminates in `error` or `blocked_session_restart` **examined nothing and returned
nothing.** Removing its cost removes **zero** detection capability — it is precisely the *"bytes that
buy nothing"* the effort analysis identified as where the savings actually are.

⛔ **And it must not drift into the anti-goal at outline.** *"Retry less"* and *"give up earlier on
hard dispatches"* are examination reductions wearing this plan's clothes. The target is the **cost of
a failure**, never the willingness to attempt.

## Why this is ours

Measurement and dispatch mechanics of our own runs — routing test 2, no PR/review surface, so not
`review-apparatus`'s. Distinct from `PLAN-CIS-031`: **CIS-031 is about full-surface re-sweeps that DO
examine (the finalize self-review loop); this is about dispatches that produced nothing at all.**
Different mechanism, different fix, and **neither subsumes the other.**

## Deliverables

1. **D1 — GATE: derive the population and the cost, first-party (mutates nothing).** The 32% is ONE
   run. Sweep the archived corpus for dispatch records whose terminal state is `error` or
   `blocked_session_restart`, report their count and token cost as a share of dispatch spend, **and
   report the population size**. ⛔ **Do not build on a single plan's figure** — lesson
   `2026-08-03-06-002`, which this epic has now violated once and must not again.
   ⚠ **Derive the terminal-state vocabulary from the schema, not from these two names** — `error` and
   `blocked_session_restart` are the two observed on one run and are a **sample**, not the enum.
2. **D2 — separate RETRYABLE from TERMINAL.** A dispatch blocked by a session restart is
   infrastructure; one that errored may be deterministic. ⛔ **They need different remedies and
   conflating them produces a fix for the wrong half.** Report them as distinct classes.
3. **D3 — make the waste a reported figure, not a derivable one.** Failed-dispatch spend gets its own
   field in the metrics surface, so a reader sees it without reconstructing it from a ledger.
   ⭐ This is the epic's own standing rule applied here: **a quantity nobody publishes is a quantity
   nobody acts on.**
4. **D4 — reduce the cost of a failure where the class permits it.** Only after D1/D2 say which class
   dominates. ⛔ **If D1 shows the corpus share is materially below 32%, this deliverable narrows to
   reporting and the plan says so** rather than manufacturing a fix for a one-run artifact.

Four deliverables (D1 a gate) — below the ~6 split guard, no split rationale owed.

## ⛔⛔ D0 — GATE BEFORE D1: populate the four per-dispatch columns, or drop them (folded 2026-08-03 from `…-001`, PR #1086)

**This plan cannot compute a share of dispatch spend until this is settled, so it runs FIRST.**

Confirmed three ways now: `truthful-signals` measured **19 rows across three ledgers all `0` on all
four columns**; PR #1086's own retrospective found **all 15 of its dispatch-boundary rows carry
zeroes**; and the filing plan's conclusion is that **no producer writes those columns anywhere in the
tree.** ⇒ They are not sparse, they are **unproduced** — and they default to `0` and persist **as
though measured**.

⇒ ⛔ **The choice is binary and both arms are acceptable; silence is not.** Either **populate** them
at the dispatch boundary, or **drop them from the schema** so nothing reads a manufactured zero.
⭐ **A schema slot is not a measurement**, and a column that is always zero is worse than an absent
one because it answers a question it never asked.

⚠ **Note the asymmetry with `PLAN-CIS-030`'s shipped decision**: that plan deliberately emits its
attribution group unconditionally so that *"a zero is a MEASURED zero"*. **That reasoning is sound
only while an absent field and a zero field remain distinguishable on disk.** These four columns are
the case where that already failed. **Whichever arm D0 takes must state how a reader tells a measured
zero from an unproduced one.**

## Claim Labels

- **OBSERVED (first-party, PLAN-CIS-001 / #1084)**: 32% of `6-finalize` recorded dispatch spend
  terminated in `error` or `blocked_session_restart`; `6-finalize` 3.6M vs `5-execute` 0.82M.
- **HYPOTHESIS**: that the 32% generalises beyond this run. **D1 is this verification**
  (verify-at-outline).
- ⛔ **Verify-first clause, inherited and BINDING**: the per-dispatch token columns
  (`input_tokens`, `output_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens`) are
  **structurally empty** — `truthful-signals` measured **19 rows across three ledgers, all `0` on all
  four, uniformly rather than sparsely**, because every producer omits the flags and the defaults
  persist **as though measured**. ⇒ **If D1's cost attribution reads those columns, it reads zeros.**
  Settle which field actually carries dispatch cost before computing any share. **A schema slot is
  not a measurement.**
- ⛔ **Verify-first clause**: `[STEP]`/marker-derived counts are a **FLOOR, not a count** (9 of 16
  steps carry markers), and the #1084 run rendered **`17 of 9 dispatch(es) recorded — complete`** —
  a denominator smaller than its numerator, stamped *complete*. **Do not compute a share against a
  denominator until that is settled** (owned by **`PLAN-CIS-037`** since the 2026-08-08 split — it was
  `PLAN-CIS-011` D8 when this clause was written).

## Expected Surface

- **HYPOTHESIS**: `record-dispatch-boundary` and the dispatch ledger it writes (verify-at-outline)
- **HYPOTHESIS**: the `phase-6-finalize` dispatcher's terminal-state handling (verify-at-outline)
- **HYPOTHESIS**: `manage-metrics` for D3's reported field — resolve via `architecture which-module`
  at outline rather than assuming

## Dependencies and Sequencing

- ⛔ **Never pair with `PLAN-CIS-030`** — same dispatch/metrics ledger surface.
- ⛔⛔ **BLOCKER CORRECTED 2026-08-08 — IT IS `PLAN-CIS-037`, NOT `PLAN-CIS-011`. Do not re-derive the
  old dependency.** `PLAN-CIS-011` was split; the `17 of 9` denominator defect (its former D8) and the
  missing-dispatch-class defect (former D10/D11) moved to **`PLAN-CIS-037`**, which is now the plan that
  must land before this one's D1 asserts any share. ⭐ **This plan therefore unblocks EARLIER than the
  ledger previously said** — CIS-037 is a five-deliverable focused plan rather than an eleven-deliverable
  one.
- ⛔ **Never pair with `PLAN-CIS-037`** (it owns this plan's denominator) — and, as WS-04 members, never
  pair with `PLAN-CIS-011`, `PLAN-CIS-034`, `PLAN-CIS-038` or `PLAN-CIS-020` either.
- ⛔ **Never pair with `PLAN-CIS-031` or `PLAN-CIS-034`** — the WS-04 `plan-retrospective` /
  finalize serialization class. **WS-04 is effectively serial; this plan is in it.**
- **Adjacent, cross-epic**: `PLAN-TRUTH-055` (re-entered rows are arithmetically impossible). If D1
  computes anything per-phase, that precondition binds here exactly as it binds CIS-030.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/code-intelligence-substrate/plans/PLAN-CIS-035-dispatch-spend-on-dispatches-that-produced-nothing.md"
```

## ⛔⛔⛔ THE HEADLINE PREMISE IS REFUTED — READ THIS BEFORE SCOPING ANYTHING (folded 2026-08-09 from inbox `self-review-resweeps-full-surface-every-round-010`)

**This plan rests on reading `termination_cause=error` as "the dispatch produced nothing".
That reading is FALSE, measured first-party on PR #1126.**

`work/metrics-dispatch-boundaries-6-finalize.toon`:

```text
2026-08-09T00:48:38Z,error,250626,...          <- self-review round 1: found 5 defects, returned
2026-08-09T01:08:07Z,error,279701,...          <- round 2: found 5, returned
2026-08-09T01:19:40Z,error,200373,...          <- round 3: found 2, returned
2026-08-09T01:30:14Z,error,233141,...          <- round 4: found 3, returned
2026-08-09T01:45:37Z,error,284719,...          <- round 5: found 4, returned
2026-08-09T01:57:22Z,step_complete,279636,...  <- round 6: clean, done
```

⇒ **Five of six `error`-stamped dispatches are the plan's MOST PRODUCTIVE dispatches.** Each
found defects, filed Q-Gate findings, and returned for a loop-back. They are stamped with the
token the taxonomy reserves for *"the dispatch raised a fatal error"*.

**Root cause**: `DISPATCH_TERMINATION_CAUSES` — `voluntary_checkpoint`,
`task_complete_returned_verbatim`, `budget_yield`, `harness_cancellation`, `error`,
`clean_exit_queue_empty`, `step_complete`, `blocked_user_review`, `blocked_session_restart`,
`task_batch_complete`, `agent_returned` — **has no member expressing "returned with findings"**.
The taxonomy models how a dispatch *stopped* but not the *verdict* a review-shaped dispatch
returns. A findings-bearing return is a success of the step and a non-completion of the loop, and
**only the second half has a token**, so the loop-back path falls to `error`.

### ⛔ Consequence for THIS plan, binding

**D1's founding figure — *"32% of #1084's 6-finalize dispatch spend went to dispatches
terminating in `error` or `blocked_session_restart`"* — is measured over a MIXED population and
cannot be read as spend that produced nothing.** ⇒ **D0/D1 must re-derive the denominator
against the finding-yield of each `error`-stamped dispatch before any share is quoted.** A
dispatch that returned findings is the opposite of this plan's target: removing its cost removes
real detection capability, which is the rejected examine-less shape.

⭐ **The plan is not invalidated — its target is.** "A failed dispatch examined nothing and
returned nothing, so removing its cost removes zero detection capability" remains exactly right.
What is refuted is the **proxy**: `error` is not that population. ⛔ **Fix the proxy before
sizing the lever**, or this plan reproduces the sample-is-not-a-population error the epic exists
to detect.

### The prerequisite deliverable

Add a `returned_with_findings` (or `loop_back`) member and route the finalize loop-back path to
it. ⭐ `mark-step-done` already has a `loop_back` outcome with a `--loop-back-target` classifier;
**the dispatch ledger has no counterpart.** ⚠ Same shape as the `budget_yield` carve-out already
documented in `logging-gap-analysis.md` — a deterministic, legitimate termination counted as the
failure mode until it got its own member. This is the next instance of that lesson.

⛔ **And widening the taxonomy alone fixes only half of it**: the `DISPATCH_TERMINATION_CAUSE`
logging-gap rule is **scoped to `metrics-dispatch-boundaries-5-execute.toon` only**. The
6-finalize file — 12 rows, 2,507,354 tokens, 51% of #1126 — **is read by no rule at all.**
Widen the rule's scope in the same deliverable.

⚠ **Ownership**: the taxonomy member is a `manage-metrics` change and `PLAN-CIS-037` owns the
boundary-ledger arithmetic. **Coordinate — do not ship two writers for one vocabulary.**

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and
edits NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message —
the orchestrator owns every other ledger write — and reports its outcome through its PR and its
inbox message. See `persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger
Write-Boundary.
