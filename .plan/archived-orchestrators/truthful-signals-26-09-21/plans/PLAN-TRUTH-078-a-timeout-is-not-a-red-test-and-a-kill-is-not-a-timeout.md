# PLAN-TRUTH-078: a timeout is not a red test, and a harness kill is not a timeout

epic: truthful-signals
workstream: WS-01

> Staged 2026-08-09 from the evening drain: `runtime-007`, its own correction `runtime-010`, and
> `metrics-012`. ⭐ **The correction is part of the evidence, not a caveat on it** — see § Claim Labels.

## Objective

A build that does not finish produces **three** distinguishable conditions — a **harness kill**, a
**daemon adaptive-budget timeout**, and a **genuinely failing test** — and the consuming gates collapse
them. Each collapse degrades a gate in a different direction.

## OBSERVED — three reports across two plans, and one self-correction

| Source | Observation |
|---|---|
| `metrics-012` (#1129) | *"a build-daemon adaptive-budget TIMEOUT is not a red test — reading it as one manufactures a failure."* The #1129 run substituted **scoped `module-tests` for whole-tree** after the budget timed out **twice**, and correctly recorded a **timeout status, not a red test** |
| `runtime-007` (#1132) | *"separate a harness-killed background build from a real budget timeout before degrading a gate"* |
| `runtime-010` (#1132) | ⭐ **A CORRECTION TO `-007` BY ITS OWN FILER**: the timeout discriminator **WAS** consulted — the daemon logs were read and both reported `status: timeout` at **642 s / 618 s** |
| `-070`'s `d0cd33` | whole-tree `module-tests` at **642 s** exceeds its learned daemon timeout **while the superset `verify` completes in 215–537 s** |

⇒ **n≥3 for the underlying timeout, across two plans, plus an operator-visible gate substitution.**

### ⭐⭐ The correction narrows the defect, and the narrowed version is the interesting one

`runtime-007` as first written implied the discriminator was **absent**. `runtime-010` establishes it
was **present and consulted**. ⇒ **The defect is not "we cannot tell a kill from a timeout" — it is that
knowing the difference did not change what the gate did.** A discriminator that is read and then not
acted on is worth less than an absent one, because it makes the gate *look* discriminating.

⛔ **Scope accordingly**: this plan must NOT re-add a discriminator that already exists. **D0 establishes
what is already emitted before anything is built.**

### ⛔ The subset/superset inversion is the sharpest single fact

`module-tests` (642 s) **times out** while `verify` — which **contains it** — completes in 215–537 s.

⇒ A learned per-command budget that can time out on a **strict subset** of a command that succeeds is
not measuring what it claims to. ⭐ **This is falsifiable and cheap to re-check**, and it is the fact
most likely to identify the real mechanism (mis-keyed budget lookup, a cold-vs-warm cache asymmetry, or
a budget learned from a different command shape).

## Deliverables

1. **D0 — GATE: enumerate what the daemon and the harness ALREADY emit for each of the three
   conditions**, and which consumer reads which field. ⛔ **`runtime-010` proves at least one
   discriminator exists and is consulted** — building a second one is the failure mode this gate exists
   to prevent. ⚠ Publish the population: how many consuming gates, how many read the status field.
2. **D1 — make the three conditions distinguishable AT EVERY CONSUMING GATE**, not just in the log. A
   `timeout` must not be presentable as a test failure, and a harness kill must not be presentable as a
   timeout. ⭐ Per the standing rule, an unresolvable case is **`indeterminate`**, never folded into
   either neighbour.
3. **D2 — settle the subset/superset inversion.** Why does `module-tests` (642 s) exceed its learned
   budget while the superset `verify` (215–537 s) does not? ⛔ **Diagnose before adjusting** — raising
   the budget would hide the mechanism, and this epic's standing rule is that a correction applied to an
   error whose sign is unknown launders a suspect figure into a "corrected" one.
4. **D3 — regression tests with matched controls**: a genuine red test must still fail the gate; a
   timeout must not; a harness kill must not; and each verified RED pre-fix.

**Four deliverables, one component family (`manage-build-server` / `build-pyproject` / the consuming
finalize gates).**

## Claim Labels

- **OBSERVED (reporting plans, first-party to them)**: the 642 s / 618 s daemon `status: timeout`
  readings; the 642 s vs 215–537 s subset/superset figures; that #1129 substituted scoped tests after
  two timeouts. ⚠ **Second-hand to this orchestrator — NOT re-derived.** Re-verify the timings at
  outline; a learned budget is by definition a moving value.
- ⭐ **OBSERVED, and load-bearing for scope**: `runtime-010` corrects `runtime-007` — the discriminator
  **was** consulted. **The uncorrected version of `-007` is not evidence for this plan** and must not be
  cited as such.
- **HYPOTHESIS**: that the three conditions are collapsed at a *consuming gate* rather than at the
  daemon. Confirm/refute against the daemon's result construction and each consuming gate's read —
  **verify-at-outline**; D0 is exactly this.
- ⛔ **NOT ESTABLISHED**: that any gate ever produced a *wrong merge decision* from the collapse. #1129's
  substitution was an operator-visible deviation, correctly recorded. **Do not claim damage taken.**

## Expected Surface

- **HYPOTHESIS**: `manage-build-server` — the daemon's result/status construction (D0 names the symbol)
- **HYPOTHESIS**: `build-pyproject` — the learned-budget lookup, for D2
- **HYPOTHESIS**: the consuming finalize gates that degrade on a non-green build
- ⛔ **NOT** the test suite under measurement — this plan changes how a non-finish is *classified*, never
  what the build runs.

## Dependencies and Sequencing

- ⚠ **Adjacent to `PLAN-TRUTH-005`** (marshalld self-reload) — same bundle, different surface.
  ⛔ `-005` is currently **withheld** pending the registry repair; if it is released first, serialize.
- **Disjoint from `-074`** (the only running plan) at file level. ⛔ Re-verify at emit from live file
  lists, not from this line — **a pre-merge worktree diff is a forecast, not a landing.**

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-078-a-timeout-is-not-a-red-test-and-a-kill-is-not-a-timeout.md"
```

## Write-Boundary

Touches only its own repository source and tests. Creates and edits NO file under
`.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
