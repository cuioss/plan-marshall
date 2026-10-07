envelope_version=1
sender_type=plan
sender_id=gates-do-not-refire-over-the-loop-back-diff
epic=truthful-signals
kind=candidate-lesson
created=2026-08-01T19:10:53Z

component=plan-marshall:manage-execution-manifest
category=bug

# Duplicate finalize-step order: `default:finalize-step-security-audit` and `default:architecture-refresh` both declare order 9

## Observation

Two registered finalize steps declare the **same** `order` value:

- `default:finalize-step-security-audit` — `order: 9`
- `default:architecture-refresh` — `order: 9`

**Pre-existing on main.** PLAN-TRUTH-001 did not introduce it; the plan's head-dependence derivation walked all 25 registered steps and surfaced it as a side effect of enumerating the population.

## Why it matters

`order` is the step-sequencing key. A duplicate makes the relative sequence of these two steps **dependent on registry iteration order** — i.e. on dict/filesystem ordering rather than on a declared intent. The consequences:

- The sequence is **stable-by-accident**, not stable-by-contract. It can silently flip on a registry change, a rename, or a platform difference, with no diff that explains the flip.
- One of these two steps is `architecture-refresh`, whose ride-along ordering PLAN-TRUTH-001 just corrected against the live registry (the doc claimed 25, the registry says 9). So this step's ordering has *already* been a source of documented drift.
- A security audit whose position relative to another step is non-deterministic is a poor property for a security gate specifically.

## Why this belongs to `truthful-signals`

The registry presents an `order` field that reads as a total ordering and is in fact a **partial** one, with the tie broken invisibly. Nothing reports the ambiguity — there is no duplicate-order validation — so the manifest confidently states a sequence it does not actually determine.

## Suggested shape of the fix

1. Assign one of the two a distinct `order`, chosen from the declared intent rather than from whatever the current iteration order happens to produce.
2. Add a **duplicate-`order` validation** to manifest composition so the class cannot recur silently. This is the durable half — the single reassignment is a one-off; the validator is what makes the ordering contract real.

Note the detector must be **population-derived** over all registered steps, in both directions (declared order set ↔ registered step set), rather than a spot-check of the two known offenders.

## Not actioned

Pre-existing on main, out of PLAN-TRUTH-001's scope. Handed to the epic.
