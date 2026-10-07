> ⛔⛔ **SUPERSEDED 2026-08-08 — MERGED INTO `PLAN-TRUTH-059`.**
> Absorbed under the raised 12-deliverable cap, grouped by COMPONENT so that plans on different
> components stay parallel-safe. The receiving spec carries the merge rationale and this plan's
> deliverables. **Do not implement. Do not emit.** Retained as the record — *close freezes, never deletes.*

# PLAN-TRUTH-039: the argparse-rejection log discards the only part that cannot be recovered later

epic: truthful-signals
workstream: WS-01

## Objective

Every `failure_kind=argparse_rejection` entry embeds the rejected script's **full usage banner** and
then truncates `detail=` at a fixed length. argparse prints the banner **first** and the actionable
`error: …` line **last**, so the truncation systematically removes the only informative part.

⇒ **The retained ~90% is recoverable at any time via `--help`. The discarded ~10% is the one line that
cannot be recovered after the fact.**

## ⭐ VERIFIED FIRST-PARTY — the mechanism is in our tree

`tools-script-executor/templates/execute-script.py.template`:

```python
detail = detail[:_DISPATCH_FAILURE_DETAIL_LIMIT] + '...[truncated]'
```

**Head-retained, tail-dropped**, against a fixed `_DISPATCH_FAILURE_DETAIL_LIMIT`. This is exactly the
reported shape, confirmed at the implementing source rather than taken on report.

⛔ **The failure is systematic, not incidental**: any rejection whose usage banner exceeds the budget
loses its `error:` line — so **scripts with the widest argument surfaces, precisely those whose call
shape is easiest to get wrong, always lose it.**

## ⛔⛔ Why this is the highest-value item in its round: it hid a live fail-open for two days

The reporting epic's item 6 is a **review quorum gate that was structurally absent while its step
recorded `outcome: done`**. Its root cause — `--in-progress-bots ""` making the executor drop the empty
value, so argparse sees a flag with no argument — went **undiagnosed across four occurrences and two
days**, and was recovered only by re-running the constructed argv by hand.

**The reason it stayed undiagnosed is this defect.** All four occurrences truncated at `error: a` —
the argument name gone. ⇒ ⭐ **The two items are a closed loop: the diagnostic elision hid the caller
bug.** A defect in a *log* is normally low severity; this one bought a fail-open two days of cover.

## Deliverables

1. **D0 — GATE: derive the population.** Every `failure_kind` whose payload is head-heavy and
   tail-actionable, not just `argparse_rejection`. ⛔ **Both directions**: kinds that truncate away the
   signal, AND kinds where head-truncation would be equally wrong. **A fix aimed only at argparse
   leaves the class open.**
2. **D1 — preserve the actionable line independently of the `detail=` budget.** Preference order from
   the filer, and it is the right order: (a) split on the last `: error: ` and record a dedicated
   `argparse_error=` field surviving the budget independently; (b) truncate from the **head** for this
   failure kind; (c) drop the banner entirely for this kind. ⭐ **(a) is preferred because it does not
   trade one loss for another** — (b) discards the invocation context, which some kinds need.
3. **D2 — tests, verified to FAIL pre-fix.** (a) A rejection whose banner exceeds the budget still
   records its `error:` line. (b) A `--flag ""` rejection records the **argument name**. (c) The D0
   population is asserted non-empty. ⛔ **(d) A control assertion**: a short rejection is unchanged —
   **a fix that reformats every entry is a different change**.

## Claim Labels

- **OBSERVED (first-party, this orchestrator)**: the truncation call in the executor template, and that
  it retains the head.
- **REPORTED, not re-derived**: the four `6a8227` occurrences, the `error: a` cut point, the
  `manage-status` `invalid choice: 'phase_handshake'` instance, and the `--in-progress-bots ""` root
  cause. ⚠ **Bundle 0.1.1276; our tree has moved.** Re-confirm the cut point at D0.
- **HYPOTHESIS**: `_DISPATCH_FAILURE_DETAIL_LIMIT` is the only truncation site. **DERIVE** — a second
  site would make a single-point fix vacuous.
- **Verify-first clause**: D1(a) assumes `: error: ` is a stable argparse marker across the Python
  versions this project supports. **Confirm before making it the split token**; if not, (b) is the
  fallback and the choice must be recorded.

## Expected Surface

- **OBSERVED**: `tools-script-executor/templates/execute-script.py.template` — the truncation site
- **HYPOTHESIS**: `tools-script-executor` SKILL.md / standards — the `failure_kind` contract
- ⛔ **NEVER edit the generated executor directly** — standing repo rule; the template is the source.

## Dependencies and Sequencing

- ⛔ **SERIALIZATION PAIR with `PLAN-TRUTH-010`** (RUNNING) — 010 owns the executor template's
  fail-closed classifier and `kind=build` row. **Same file. Cannot run concurrently; re-ground after
  010 lands.**
- ⚠ Adjacent to `PLAN-TRUTH-008` (executor preflight stamp) — same skill, different concern.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-039-argparse-rejection-log-discards-the-only-recoverable-part.md"
```

## ⭐ THIRD-PARTY CORROBORATION 2026-08-03 (API-Sheriff #149) — and a NEW half this plan does not yet own

A consumer repo's doc-only plan filed **three argparse-rejection clusters sharing ONE root cause**:
**a verb-scoped flag guessed at top level.** The reporter adds that they **hit the same class twice
themselves during the run, on `ci pr view`.**

⭐⭐ **And so did this orchestrator, in this session**: `ci pr view --pr-number 1082` →
`unrecognized arguments: --pr-number`. **Same verb, same class.** ⇒ **At least five instances across two
repositories and three actors, on one flag-scoping shape.**

### ⛔ The new half — a rejection is not learnable, so it recurs in a fresh context

> **One cluster recurred 80 minutes later in a RE-ENTERED CONTEXT that had not seen the first failure.**

⇒ **A rejection is recorded nowhere a later context reads.** This plan makes the rejection *readable
when it happens*; ⛔ **it does not make it readable to the NEXT actor**, and a resumed or dispatched
context starts blind.

⚠ **Deliberately NOT folded as a deliverable** — it is a different mechanism (persistence/learning, not
truncation) and this plan is correctly scoped to the log line. ⭐ **But state it in the landing**, because
a reader will otherwise assume a readable rejection prevents recurrence. **It prevents re-derivation
within one context, not across contexts.**

⚠ **The flag-scoping root cause itself is `PLAN-TRUTH-012`'s** (declared-vs-live argparse surface) —
cite, do not absorb.

## ⭐⭐ FOLDED IN 2026-08-08 — THE CORPUS SCALE IS NOW MEASURED, AND A DETECTOR REPORTS ZERO OVER IT

From `archived-plan-audit-26-08-08-001` (a 58-plan archived-corpus audit) and the six
script-failure candidate-lessons of PR #1115 (`a-rule-that-is-green…-020` … `-025`). This is the
first time this class has been **counted** rather than instanced.

- **OBSERVED (filer's figures, one audit run, corpus n=58 — re-derive before pinning a test):**
  **463 unfiled argparse/contract-drift signatures across 48 of 58 plans** in
  `quality-verification-report`, and **178 errors** in `global-log-analysis` (`ERROR=160`,
  `WARNING=71` over 74,712 log lines). The audit calls it **the corpus's largest waste class**.
- ⛔⛔ **AND THE DETECTOR BUILT TO FIND IT REPORTS ZERO**: `recurring-pattern-detector` scores the
  argparse signature at **0** at threshold 3, against 463 signatures spanning 48 plans. ⭐ **This
  is not a tuning problem — it is this epic's thesis inside the very instrument that would have
  raised the alarm.** A class large enough to be the corpus's biggest waste sink is invisible to
  the recurrence detector, so nobody was ever going to be told. **D-new: the detector's zero over
  this class must be explained or fixed before this plan claims the class is handled.**
- **OBSERVED — the recurring source notations (≥3 plans)**: `manage-solution-outline` (**~30
  plans — the single most persistent**), `manage-findings`, `manage-status`, `manage-references`,
  `manage-files`, `manage-logging`, `manage-architecture:architecture`, `manage-change-ledger`,
  `manage-execution-manifest`, `tools-integration-ci`. The signature shapes are already
  classified: *argparse rejection*, *invented flag drift*, *missing required flag*, *invented
  subcommand drift*, *script-internal error*.
- **The six PR #1115 instances, per-instance as required** — each an *invention*, not a typo:
  `manage-status` called with a non-existent top-level subcommand (`-020`); `qgate query`
  invented for the canonical `qgate list` (`-021`); `--deliverable N` invented where the verb
  declares no such flag (`-022`); a top-level `read` invented where the verb is the `request`
  noun's sub-verb (`-023`); `phase_handshake` reporting drift twice, both times from a finding
  count falling (`-024`); `collect-fragments` failing on a missing bundle file **while the
  retrospective completed** (`-025`).
- ⭐ **`-025` and `-024` are the sharp ones**: a step failed and the run reported completion. Those
  two belong to this plan's *swallow* half, not its *log-format* half — do not let the volume of
  `-020`…`-023` (which are caller inventions) hide that two of the six are the fail-open.

⚠ **Scope guard**: this fold adds evidence and one deliverable (the detector's zero), NOT a
mandate to fix ~30 plans' worth of `manage-solution-outline` callers. **Fix the swallow and the
record; the caller inventions are the symptom this plan exists to make visible.**

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message. Qualifiers
are in `persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

## ⚠ 2026-08-03 — `review-apparatus` declined absorption, deliberately. Recorded so it is not re-offered.

They evaluated folding this into their rejection-handling work and **declined with a reason**:
**"your fix does not fix ours and ours does not fix yours."** ⇒ Two different defects that merely both
surface as an unreadable rejection.

⭐ **They carry it as an OUTLINE HINT instead**, and it is worth having in this spec too:

> *If you cannot see why a dispatched rejection happened, suspect the truncation before the caller.*

⭐⭐ **And they supplied a case that sharpens this plan's value.** Their item 6 root cause:
`--in-progress-bots ""` — **the executor drops the empty value**, so argparse sees a flag with no
argument and rejects it. ⛔ **The caller's argv is CORRECT and still rejected**, which means no
documentation change can fix it — and the rejection detail is exactly what this plan makes readable.
⇒ **A third rejection cause, and the strongest argument yet that a truncated rejection log costs real
debugging time rather than merely reading badly.**

⚠ Not folded as a deliverable — **the executor's empty-value handling is a separate defect** and belongs
with whoever owns the executor argv path. **Record it; do not silently widen this plan's scope.**
