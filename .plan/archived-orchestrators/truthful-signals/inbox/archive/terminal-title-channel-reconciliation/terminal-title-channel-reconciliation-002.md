envelope_version=1
sender_type=plan
sender_id=terminal-title-channel-reconciliation
epic=truthful-signals
kind=candidate-lesson
created=2026-07-27T19:53:38Z

component=plan-marshall:phase-6-finalize
category=bug
source_plan=terminal-title-channel-reconciliation
source_pr=1023
source_finding=005699

# Every finalize gate is module-scoped, and module-scoped quality-gate skips the marketplace-wide sweep by design

## Observation (first-party, PLAN-79 / PR #1023)

CI went red on the static-analysis rule `no-historical-prose-in-skills` after every local
finalize gate had reported green. Not a flake and not a race — every gate that ran was
scoped narrower than the rule set that failed:

- `build.py:cmd_quality_gate` invokes `doctor-marketplace.py quality-gate` (the
  marketplace-wide invariants) **only when `module is None`**. Its own docstring states it:
  *"Module-scoped quality-gate skips the marketplace-wide sweep because it is scoped to a
  single bundle."*
- `pre-push-quality-gate` derives per-bundle targets and calls `quality-gate {bundle}` — a
  module-scoped invocation — so it takes exactly that skip path.
- `project:finalize-step-plugin-doctor` likewise runs **scoped to the skills the plan
  touched** (`display_detail: "plugin-doctor clean: 6 skills gated"`).

The offending rule is a whole-tree rule: it fires on skills the plan did not touch, so
neither scoped run can see it by construction. Both gates were *correctly* green.

## ⚠ Correction to an earlier framing of this same finding

An earlier draft of this finding (and the `005699` finding text on the archived plan) claimed
this was a **local-vs-CI capability gap** — that "the only evaluator of these rules is CI".
**That is false and should not be carried forward.** The whole-tree form is fully runnable
locally and was in fact run locally to confirm the fix:
`pyproject_build run --command-args "verify"` (no module arg) reported
`plugin-doctor total_issues: 0` plus 15466 passed. The gap is *scope selection*, not
capability or environment.

Related naming correction: `pm-plugin-development:plugin-doctor` (the LLM skill, local and
interactive) and `doctor-marketplace.py quality-gate` (the deterministic static analyzer
`build.py` invokes) are different surfaces sharing a name. CI runs the analyzer, never the
skill — "CI runs plugin-doctor" is not an accurate sentence.

## Why this generalises

This is the scoped-green / whole-tree-red archetype, but for **static rules** rather than
tests. The tests half of this archetype is already understood (a scoped test run cannot see
a cross-module regression); the static-rule half was not, because plugin-doctor's scoping is
an efficiency optimisation that reads as a completeness guarantee at the gate's display
surface. `"plugin-doctor clean: 6 skills gated"` is a truthful statement about 6 skills that
is routinely read as a truthful statement about the rule set.

## Corrective rule

For any gate whose scope is narrower than the rule set it runs:

1. The gate's `display_detail` MUST name its scope in a way that cannot be read as coverage
   (`"6 of N skills gated — whole-tree rules NOT evaluated"`, not `"plugin-doctor clean"`).
2. The pre-push gate MUST evaluate the whole-tree rule set at least once. The mechanism is
   already there and costs nothing to reach — a single no-module `quality-gate` invocation
   alongside the existing per-bundle loop. Static analysis over the marketplace tree is
   seconds, not minutes. Alternatives: classify each rule scoped-safe vs whole-tree-only and
   sweep only the latter, or make the scoped run fail closed when a whole-tree-only rule is
   in the active rule set.

The current state is not "CI is the only evaluator" — it is "the only invocation anyone
makes pre-push is the one that skips the sweep". That is a cheaper problem to fix and a
different one to reason about: no new capability is needed, only a second invocation.

## Truthful-signals relevance

A gate that is structurally incapable of evaluating part of its own rule set, while
reporting `clean`, is a confident signal hiding a caveat. The signal is not false; its
scope is silently narrower than its name.
