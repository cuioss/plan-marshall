envelope_version=1
sender_type=plan
sender_id=one-coherent-automated-review-contract
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T05:03:57Z

component=plan-marshall:execution-context
category=bug
bundle=plan-marshall

# A dispatched leaf has no content-search capability, so population-first verification cannot run where the work runs

## Observation

Three times in one plan (`one-coherent-automated-review-contract`, PLAN-92), a dispatched
`execution-context` leaf was blocked from completing a documented obligation because no
content-search tool exists inside the envelope:

1. `logs/work.log:63` — phase-3-outline: "Blocked on 2 of 3 fix items -- no search tool available
   for population-first sweeps."
2. `logs/work.log:221` — phase-5-execute: "[BLOCKED] Coverage gap for TASK-5 criterion: the
   word-boundary sweep for `enabled_bots` across `marketplace/` and `test/` cannot be run in this
   envelope. Grep and Glob are not granted to the leaf, `architecture find` is path/symbol-scoped
   not content-scoped, and bash grep is barred by the project file-operation hard rule."
3. The plan-retrospective leaf itself hit the identical wall while trying to enumerate `[DISPATCH]`
   lines and read the dispatched-vs-inline roster for aspect 11's inverse-coverage check.

The three escape hatches are each closed by design, and they are closed *simultaneously*:
`Grep`/`Glob` are declared in `allowed-tools` but not granted at runtime; `architecture find` is
structurally path/symbol-scoped; and bash `grep` is blocked unconditionally by the project
file-operation hard rule and its enforcement hook. There is no fourth option.

## Why this is severe rather than annoying

This plan's own deliverables D2 and D3 made word-boundary sweeps their **verification criteria** —
"a word-boundary sweep for `enabled_bots` returns ONLY this explicit allow-list", "no symbol named
`_CODERABBIT_BOT_LOGINS` remains anywhere in the tree". A criterion that can only be evaluated by
the orchestrator, while the work that must satisfy it happens in the leaf, means the leaf can
never self-verify its own completeness. The recurring `volume-read-as-coverage` and
`sample-is-not-an-enumeration` archetypes are downstream of exactly this gap: when a leaf cannot
enumerate a population, it substitutes the sample it can reach.

## Do this instead

- Give the leaf a **content-search seam that is not a file-operation escape hatch** — e.g. a
  `manage-architecture` or `tools-file-ops` verb that takes a pattern plus a path scope and returns
  match paths + line numbers, implemented in Python so it is subject to the same script contract as
  every other `.plan`-adjacent capability. This satisfies "structured queries first" rather than
  fighting it.
- Until that exists, any deliverable whose verification criterion is a population sweep MUST be
  planned with the sweep assigned to an orchestrator-tier step, not left implicit in a leaf task.
  Phase-4 should reject a criterion the executing tier provably cannot evaluate.
- The correct leaf behaviour when the gap is hit is what this plan did: emit `[BLOCKED]` and
  escalate. Never silently narrow the criterion to what the granted tools can reach.

## Recurrence context

Epic theme `truthful-signals`: the failure mode is a leaf that reports a criterion satisfied on
evidence it was structurally incapable of gathering. Here it was caught three times because the
leaf escalated honestly — but the capability gap is what forces the choice in the first place.
