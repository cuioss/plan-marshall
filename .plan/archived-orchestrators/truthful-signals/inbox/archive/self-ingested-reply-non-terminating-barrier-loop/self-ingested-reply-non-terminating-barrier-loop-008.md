envelope_version=1
sender_type=plan
sender_id=self-ingested-reply-non-terminating-barrier-loop
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T10:18:45Z

component=plan-marshall:plan-retrospective
category=bug
bundle=plan-marshall

# The dispatch audit's shape_violation check cannot fire — its evidence surface does not exist

## Observation

`standards/execution-context-dispatch-audit.md` defines four checks. The `shape_violation` check is specified as:

> A `(plan-marshall:manage-config)` `effort resolve-target` entry exists in `decision.log` for a given `role` value but no subsequent `[DISPATCH]` line carrying the same `role` appears in `work.log`

and Surface B is documented as *"every `(plan-marshall:manage-config)` line whose body names a resolved role-key, captured by the resolver script when callers invoke `effort resolve-target`."*

**No such line can ever be written.** `manage-config effort resolve-target` declares exactly three flags:

```
usage: manage-config.py effort resolve-target [-h] [--role ROLE] [--phase PHASE] [--default]
```

There is no `--plan-id`. The verb has no way to identify which plan's `decision.log` to write to, and it writes none. This plan's `decision.log` carries 77 entries and **zero** from `manage-config`, against 21 real `[DISPATCH]` emissions in `work.log`.

## Why it matters

`shape_violation: 0` is currently reported as a clean result. It is not a result at all — the pairing rule has one populated side and one structurally empty side, so the check returns 0 for every plan regardless of whether any dispatch went unlogged. This is the fifth-plus instance of the vacuous-guard archetype the epic tracks, and it is in the aspect whose entire job is to prove dispatch discipline.

Note the standard is internally aware of the tension: the roster doc's "Resolver-lookup completeness invariant" explicitly says the declared lookup column *"is **not** an explanation for any past missed `[DISPATCH]` emission — the emission obligation is fused to the dispatch branch."* If the emission obligation lives in the dispatch branch, then a *resolve* record is not the right evidence surface for a *missing emission* in the first place.

## Corrective rule

Either:

- **Give the resolver a plan-scoped log write** (`--plan-id` + a `decision.log` emission), making Surface B real; or
- **Retire `shape_violation` and replace it** with a check anchored on evidence that exists — e.g. pair each `[DISPATCH]` line against the `phase_steps` record it should produce, which is the direction `dispatch_coverage_violation` already takes.

What is not acceptable is leaving a check in the contract that reports `0` from an empty universe while reading as a passed assertion.

## Evidence

- `python3 .plan/execute-script.py plan-marshall:manage-config:manage-config effort resolve-target --help` — three flags, no `--plan-id`.
- `standards/execution-context-dispatch-audit.md` § Inputs, Surface B; § Detection Logic, `shape_violation` row; § Pairing rule.
- This plan: 21 `[DISPATCH]` lines in `work.log`, 77 `decision.log` entries, 0 from `manage-config`.
