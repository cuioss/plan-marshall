envelope_version=1
sender_type=plan
sender_id=runtime-edge-paths-crash-or-silently-lose-data
epic=truthful-signals
kind=candidate-lesson
created=2026-08-09T20:25:46Z

component=plan-marshall:plan-retrospective
category=anti-pattern
confidence=high
source_plan=runtime-edge-paths-crash-or-silently-lose-data
source_aspects=script_failure_analysis

# Step 3 aspect labels do not match the collect-fragments registry keys

## Context

`plan-retrospective/SKILL.md` Step 3 presents the aspect table with an `Aspect` column, and the
per-aspect capture pattern immediately below instructs:

```bash
collect-fragments add --plan-id {plan_id} --aspect {name} --fragment-file work/fragment-{aspect}.toon
```

Row 3 of that table is labelled **"Invariant outcomes"**. Following the instruction literally
with `--aspect invariant-outcomes` is rejected:

```
error: "Unregistered aspect key: 'invariant-outcomes'. It is not in the canonical section
registry nor any domain-contributed aspect set, so compile-report would silently drop its
section."
```

The registry key is `invariant-summary`. Row 11 has the same shape — labelled
"Execution-context dispatch audit", registry key `execution-context-dispatch-audit` — which
happens to kebab-case cleanly, so it works by luck rather than by contract.

## Root cause

The table's `Aspect` column is prose, and the capture pattern treats it as an identifier.
Nothing binds the two. The seventeen registry keys live in the `collect-fragments` script; the
labels live in the SKILL table; no test compares them.

## Proposed action

Add the exact registry key to the Step 3 table as its own column (or replace the prose label
with the key and move the prose to the description), and add a contract test asserting set
equality between the Step 3 table's key column and the `collect-fragments` registry — the same
shape as the existing `DISPATCH_TERMINATION_CAUSES` guard in `manage-metrics`, which discovers
every enumeration occurrence in its own SKILL.md and fails until each matches the tuple.

## Evidence

- observed in this run: `collect-fragments add --aspect invariant-outcomes` rejected, retried as `invariant-summary`, succeeded
- the rejection lists all 17 valid keys, so the registry is introspectable and a test has a source to compare against

## What went right

The guard is excellent and should be preserved exactly as is. It refused the unregistered key
rather than accepting the fragment and letting `compile-report` drop the section silently, and
its error message named the consequence ("compile-report would silently drop its section") and
enumerated the valid set. This is a fail-loud boundary doing precisely its job — the anti-
pattern is only that the SKILL text walks the caller into it.
