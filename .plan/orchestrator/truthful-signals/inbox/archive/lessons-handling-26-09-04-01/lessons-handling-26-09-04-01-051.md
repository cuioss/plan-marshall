envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-04-01
epic=truthful-signals
kind=candidate-lesson
created=2026-09-10T17:28:32Z

component=plan-marshall:manage-change-ledger
category=bug

Relayed from Token-Sheriff PLAN-09 (PR #731 / `b6b1a94d`). ⚠ Provenance-shaped: a build ledger row that cannot name its plan cannot be attributed, which is the same class as the session-attribution gap relayed alongside it.

component=plan-marshall:manage-architecture
category=bug
bundle=plan-marshall

# Architecture-resolved build `executable` omits `--plan-id`, so build ledger rows stamp `plan=NO_PLAN` and freshness reports stale

The build command resolved through the architecture API does not carry
`--plan-id`. Consequences observed in this run:

1. The `kind=build` row appended to the change ledger stamps `plan=NO_PLAN`
   instead of the plan that actually ran the build.
2. `pre-commit-verify-freshness` looks for a ledger row attributed to the current
   plan, finds none, and reports the tree as **stale for a build that did run**.

The build was real, its result was real, and the freshness verdict was wrong. The
failure is silent in the direction that matters: it produces a false negative
("stale") rather than a false positive, so it does not corrupt anything — but it
does cause redundant rebuilds and, worse, teaches the operator to distrust or
route around the freshness gate.

## Solution

Thread the plan id into the architecture-resolved build `executable` so the
ledger row is attributed to the plan that invoked it. Whichever surface composes
that executable is the fix site — the freshness check itself is behaving
correctly given the data it is handed, so patching the check would be treating
the symptom.

Until then, a `plan=NO_PLAN` build row next to a stale freshness verdict should
be read as this defect, not as a genuinely unbuilt tree.

## Impact

Every plan whose verification step runs the architecture-resolved build command
in a project where `pre-commit-verify-freshness` is active. Recurs on every run,
not just this one.
