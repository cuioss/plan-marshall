# Run report — multiplattform epic authoring (run 02)

**Date (UTC):** 2026-08-17  **Branch:** `claude/refactor-multiplatform-planning-xurgnn`
(restarted from `origin/main` at `bb85899` after run 01's PR #1275 merged)
**PR:** — (filled at PR creation)  **Outcome:** in progress

> Epic-authoring run at the epic root, per the run-01 precedent and its disclosed deviation.

## Skills loaded

`cloud-plan-lane` (first action, carried from the session), `author-cloud-plan`. The two
"always" skills deliberately not loaded for a docs-only authoring run — same disclosed deviation
as run 01.

## Deliverables

A thorough whole-marketplace audit for Claude-specific structures in the existing skills, with
every finding handled as part of the epic's plans.

| Artifact | State |
|---|---|
| `reference/marketplace-audit.md` — the audit registry, clusters §M1–§M11 with placement homes and drawn-by dispositions | complete |
| Plans `050` (structural directive coverage), `060` (authoring-surface target-awareness), `070` (runtime-fact prose and single sources) | complete |
| `reference/coupling-inventory.md` — audit pointer + two new §D candidates | complete |
| `README.md` — plans/graph/concurrency extended to seven plans | complete |

**Audit method.** Three parallel read-only sub-agents partitioned the 11 bundles (plan-marshall;
pm-plugin-development + pm-documents + pm-requirements; the six pm-dev-* + pm-code-intelligence),
each running a 12-pattern battery (layout literals in both quote styles and segment-wise,
`CLAUDE_CODE_*`, hook events, permission DSL, transcript format, model identifiers,
slash-command emission, `CLAUDE.md` normativity, `mcp__` names, Claude-as-runtime prose,
tool-name directives, runtime-fact statements), diffing every hit against the inventory and
reading each nominated file. Zero-finding patterns are recorded in the registry so the negative
is auditable; each agent stated what it could not fully inspect (the plan-marshall agent's
tool-name-vocabulary footprint note is folded into inventory §C's scope).

**Headline findings.** The `Read:` full-line directive is an unregistered structural-vocabulary
gap (~130 occurrences, invisible to the fail-closed check); a full `AskUserQuestion` call-schema
block ships as workflow; the authoring toolchain's generator/validator/fix surfaces are
Claude-only against a target-aware fixer; `manage-terminal-title` hosts a Claude channel
specification its own contract disclaims; the effort table is restated on five surfaces; and
`/marshall-steward` is emitted from over a dozen general scripts and persisted into `.gitignore`.

## Build gate

Docs-only diff (plans + reference markdown), no `*.py` — build skipped per the gate; the merge
queue is the net.

## Findings

Pre-PR verification round(s) recorded here with dispositions before the merge gate.

## Reviewer participation

Filled from the stored bodies at the merge gate.

## Cost

Sub-agent self-reports: auditors 158,598 / 148,786 / 97,423 tokens (40 / 40 / 27 tool calls).
Main-loop tokens not available. Population: the three dispatched auditors only — not comparable
to a `metrics.toon` total.

## Contract check (Step 9)

Completed at the merge gate; branch form: harness-assigned name restarted from `origin/main`
after the prior PR merged (the remote branch had been auto-deleted, so the restart published as
a plain push). No `/sync-plugin-cache` owed.

## What have we learned (Step 9)

Recorded at the merge gate.

## Residue

- The §M10 repo-scoping references and §M11 candidates are registered without a drawing plan —
  deliberate, awaiting the `020` mechanism and a repo-scoping design.
- The `LEVEL_TABLE`/`model_map` cross-target import direction is recorded in plan `070` D4 as a
  proposal; the fix is `marketplace/targets` work no current plan owns.
