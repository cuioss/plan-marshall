# PLAN-202: Compose-time subtractions drop verification steps nobody authorised

epic: truthful-signals
workstream: WS-01

## Objective

`manage-execution-manifest compose` subtracts steps from `phase_6.steps` on implicit predicates. Two
observed subtractions were wrong, in different ways, and **one of them silently reversed an explicit
operator decision**. Derive every compose-time subtraction, and make a subtraction that contradicts
an operator answer — or that fires on an unknowable input — impossible or loud.

⭐ **PLAN-112 (#1055) already fixed ONE instance of this** — the security-class gate. It removed the
`change_type` leg and made the drop loud for that step class. **The general mechanism is still live
for every other step**, and PLAN-112's own run is evidence: it dropped its security audit *despite an
operator-chosen full posture*. This plan generalises what that one fixed pointwise.

## Defect A — the scope gate silently reversed an explicit operator override

Observed on the PLAN-109 run, from its own decision log:

```
[13:35:00] (phase-1-init) Execution-profile posture: auto (projected=minimal, lane_selection=ask)
           - operator overrode upward to retain pre-submission-self-review and simplify
[14:02:35] (compose) scope_gated_finalize subtraction - scope_estimate=surgical,
           dropped pre-submission-self-review from phase_6.steps
```

The operator was asked, answered, and **named `pre-submission-self-review` specifically**. Twenty-seven
minutes later an implicit gate removed exactly that step. **The operator was never told.**

⛔ **The sharp part — the remedy already exists and fired in the same second:**

```
[14:02:35] scope_gated_finalize immunity - kept plan-marshall:plan-retrospective despite
           scope_estimate=surgical: the step declares an explicit non-auto lane override,
           which the implicit scope gate must not silently override
```

**A step's own config is protected from the scope gate. A human's recorded answer is not.** The
immunity mechanism is keyed on a step's declared `lane`, not on operator intent.

⚠ **The operator is billed for the decision (the upward posture) and does not receive the
verification.** It is recoverable only by reading two log entries 27 minutes apart and noticing they
contradict; every summary surface shows a clean manifest.

## Defect B — a footprint predicate that is empty at compose time by construction

`compose` drops the pre-push build gate on a "plan footprint is empty" predicate. **The footprint is
empty for every plan at compose time, because compose precedes worktree materialization.** The
predicate is therefore vacuous: it does not test what it reads as testing.

⚠ **It survived only because this project pins `finalize.qgate=always`.** A consumer project without
that pin loses its pre-push build gate silently. ⭐ **The masking pin is why this went unnoticed —
the defect is invisible in the one project most likely to find it.**

⭐ Same family as this epic's four-instance rule: **an unmeasurable quantity must not be read as a
measured one.** An empty footprint at compose time means *unknown*, not *nothing to build*.

## Deliverables

1. **D1 — GATE (mutates nothing): DERIVE every compose-time subtraction.** Enumerate every predicate
   by which `compose` removes a step from any phase's step list. For each, record: the input it reads,
   whether that input is knowable at compose time, and what authorises the removal. ⛔ **A and B are a
   SAMPLE.** PLAN-112 already found a third (the security-class gate) — **three known instances means
   the population is the finding, not the instances.**
2. **D2 — an operator decision is a first-class immunity input.** Persist the operator's
   profile-override answer in the same shape the step-level `lane` override already uses, so
   `scope_gated_finalize` skips any step the operator named. ⭐ **Do not invent a mechanism — extend
   the one that already works.** The immunity path exists, is proven in-run, and is merely keyed on
   the wrong thing.
3. **D3 — no silent subtraction, ever.** Any subtraction that cannot be made impossible MUST emit a
   warning naming the step and the decision it reverses, on an operator-visible surface — not only in
   the decision log. ⛔ PLAN-112's `security_class_omitted[{step, reason}]` + `[STATUS]` line is the
   shipped reference form. **Reuse it; do not build a second reporting convention.**
4. **D4 — a predicate that reads an unknowable input must not fire.** Fix Defect B at the predicate,
   not at the pin: an empty footprint at compose time resolves to *unknown*, and *unknown* never drops
   a gate. ⚠ **Verify the fix with `finalize.qgate` UNPINNED**, or the masking that hid it will hide
   the fix's failure too.
5. **D5 — tests, each verified to FAIL pre-fix.** (a) An operator-named step survives a `surgical`
   scope estimate. (b) A subtraction that reverses an operator answer emits an operator-visible
   warning. (c) The pre-push build gate survives compose with an empty footprint and
   `finalize.qgate` unpinned. (d) The subtraction population from D1 is derived, non-empty, and
   contains all three known members.

## Claim Labels

- OBSERVED (first-party, PLAN-109 run decision log, quoted verbatim above): both log lines, 27 minutes
  apart; the immunity carve-out firing in the same second on `lane`.
- OBSERVED (first-party, PLAN-109 retrospective): the compose-time footprint predicate is empty for
  every plan; `finalize.qgate=always` is what masks it here.
- OBSERVED (orchestrator, PLAN-112 landing #1055): a security audit dropped despite an operator-chosen
  full posture — the third instance, already fixed pointwise.
- HYPOTHESIS: exactly three compose-time subtraction predicates exist — **confirm/refute at D1.
  Assume MORE until the derivation says otherwise.** Confirm/refute artifact: the compose
  implementation's step-list mutation sites.
- ⚠ No line numbers asserted: the evidence is log-derived. **Establish every site by SYMBOL at D1.**

## Expected Surface

- HYPOTHESIS: `manage-execution-manifest/scripts/**` — the compose step-list subtraction sites
  (verify-at-outline)
- HYPOTHESIS: the phase-1-init execution-profile persistence path, for D2's immunity input
- OBSERVED: tests under `test/plan-marshall/manage-execution-manifest/**`

## Dependencies and Sequencing

- Depends on: none. ⚠ **Read PLAN-112's landing (`landings/PLAN-112.md`) first** — it fixed the third
  instance and its derived-population and loud-omission patterns are the reference this plan
  generalises.
- Overlaps with: ⚠ `manage-execution-manifest` is also named by **PLAN-TRUTH-003**'s shim sweep — verify
  before pairing. Disjoint from `phase-6-finalize` plans (PLAN-TRUTH-001; and the transferred PLAN-117 /
  PLAN-119, now `review-apparatus`'s PLAN-PR-009 / PLAN-PR-008) at the file level, but
  **both concern which finalize steps run** — sequence if either is in flight.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-202-compose-time-subtractions-drop-steps-nobody-authorised.md"
```

## Write-Boundary

This plan MUST NOT create or edit any file under `.plan/local/orchestrator/`. Its only channels back
to the epic are its PR and its `inbox/` OUTBOX.
