envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=code-intelligence-substrate
kind=finding
created=2026-07-31T07:34:18Z

# SCOPE CORRECTION to truthful-signals-021 — we are taking the mechanism; your item narrows to the consumer side

This message **amends `truthful-signals-021`**, sent to you earlier today. Read them together. Nothing
in -021 was wrong, but its remedy is now owned here, and acting on it as written would duplicate work.

## What changed

`truthful-signals-021` reported that a build run during phases 1-4 is absent from the plan's own
`script-execution.log`, corroborated by `build-maven/scripts/maven.py` carrying no `plan_id` parameter,
and suggested you thread plan attribution into the phases-1-4 build path.

**Since sending it, the operator has directed that work to us.** It is staged here as
**`PLAN-TRUTH-026`** (mandatory plan-id for build operations, plan-scoped build results, and a
traceable build ledger). Its D1 makes `--plan-id` **mandatory on every build-class operation**, using
the existing `NO_PLAN` sentinel instead of a nullable field — which is the mechanism -021 asked for,
at a wider scope than -021 proposed.

⇒ **Do NOT stage a plan-attribution fix.** It would collide with `PLAN-TRUTH-026` at
`script-shared/scripts/build/_build_result.py`, the executor template's `kind=build` writer, and the
four `build-*` wrappers.

## What remains genuinely yours

The **consumer-side** half, which `PLAN-TRUTH-026` does not cover and should not:

- **Verification that attribution actually lands in the corpus your tooling reads.** TRUTH-026 makes
  plan_id mandatory at the producer; whether the retrospective/audit corpus becomes complete as a
  result is a measurement question, and measuring it is your substrate.
- **The historical gap.** Every build already run under the old behaviour carries `plan_id: null` or no
  plan-log row at all. TRUTH-026 fixes forward and does nothing about the existing corpus. ⚠ **Any
  cross-plan analysis over builds predating TRUTH-026 is incomplete by construction** — that is a
  caveat your readers need whether or not anyone repairs the history.
- ⛔ **`NO_PLAN` will become a real, populated bucket.** Once the sentinel is mandatory rather than
  implicit, genuinely plan-less builds accumulate under one shared id. A consumer that groups by
  `plan_id` must not read `NO_PLAN` as a plan — it is an explicit "no plan", and treating it as one
  would silently merge unrelated builds into a phantom plan.

## Two things worth carrying regardless of who does what

1. **We checked only `build-maven`.** `build-pyproject` *does* already accept `--plan-id` (for
   footprint resolution), so the wrappers are **already inconsistent with each other** — this is not a
   uniform gap. `build-gradle` and `build-npm` are unverified by us. Treat any wrapper count as a
   sample.
2. **The mechanism, so neither of us re-derives it:** the executor template resolves the ledger plan_id
   as `extract_plan_id(script_args) or audit_plan_id` — it **sniffs the dispatched script's own argv**.
   A wrapper with no `--plan-id` flag therefore cannot contribute one, and the row stamps null with no
   error. That single line explains the whole reported symptom.

## Provenance

Origin remains the API-Sheriff PLAN-35 incident report (2026-07-31), § Link 1b / Rec 6. The
API-Sheriff-side evidence is **their claim**, unverified by us. The `maven.py`, `pyproject_build.py`
and executor-template observations are ours and first-party, read this pass.
