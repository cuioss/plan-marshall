# Run report — multiplattform epic authoring (run 02)

**Date (UTC):** 2026-08-17  **Branch:** `claude/refactor-multiplatform-planning-xurgnn`
(restarted from `origin/main` at `bb85899` after run 01's PR #1275 merged)
**PR:** #1277  **Outcome:** completed

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

**Pre-PR verification round** (clean sub-agent): 3 MAJOR, 3 MINOR, 2 NIT — all fixed in
`bad5aca`. The substantive ones: the ext-triage set is seven skills, not six (including
`ext-triage-plugin` in pm-plugin-development, forcing an explicit 050/060 surface carve-out); the
D3 done-when was unsatisfiable as written (files differ outside the escalation blocks); the
concurrency table was asymmetric across the 050/060/070 rows. Ground truths (a)–(f) all
confirmed against the tree.

**PR review**: CodeRabbit posted 3 actionable comments. Two fixed (060's Expected surface now
carries the ext-triage-plugin exclusion; 050's Problem count corrected to seven). One
**rejected with reason**: an executable validator for the epic's surface contract — the epic
follows the standalone-epic precedent (hand-written leads + gating, halting per-run
re-derivation), and a `doc/plans/**` contract validator is new tooling for its own change;
recorded as a proposal in § Residue and answered on the thread.

## Reviewer participation

| Reviewer (`author_login`) | Verdict | Reopens? | Body evidence / reason |
|---|---|---|---|
| `cuioss-review-bot` | reviewed | — | Issue-comment body: "PR Reviewer Guide 🔍 — No relevant tests / No security concerns identified / No major issues detected". |
| `coderabbitai` | reviewed | — | First attempt errored ("Review failed"); first `@coderabbitai review` re-trigger rate-limited; second re-trigger after the window produced the full review ("Actionable comments posted: 3") with a partial-clone warning noted in its walkthrough. All comments dispositioned. |
| `sourcery-ai` | rate-limited | yes — weekly quota reset, not within this run | Review-summary body: "you have reached your weekly rate limit of 500000 diff characters". |

**Coverage: 2 of 3**, derived from the stored bodies across all three surfaces, never from check
states. No reviewer was `silent`. The § Step 8 disclosure fired: the run proceeds with
`sourcery-ai` unreviewed (weekly-quota refusal, outside this run's control).

## Cost

Sub-agent self-reports: auditors 158,598 / 148,786 / 97,423 tokens (40 / 40 / 27 tool calls).
Main-loop tokens not available. Population: the three dispatched auditors only — not comparable
to a `metrics.toon` total.

## Merge gate

Condition 1 **met** (on the pre-report head: `verify / conclusion` success, `verify / gate`
success, `verify / verify` skipped by the docs-only footprint gate, `dependency-review` and
`review / review` success; this report's commit re-triggers verify and auto-merge defers
required-green to the queue). Condition 2 **met** (three surfaces read; three actionable
findings dispositioned — two fixed, one answered on the thread). Condition 3 **met** — this
commit. Disclosure fired: coverage 2 of 3, stated above and to the operator before arming.

## Contract check (Step 9)

Steps 1–8 as in run 01's pattern: skills loaded (lane + authoring; "always" pair deliberately
skipped for a docs-only run, disclosed); branch = harness-assigned name restarted from
`origin/main` after the prior PR merged (remote branch auto-deleted, plain push); plan-directory
step not applicable (authoring run); commits `76a1504`, `bad5aca`, plus the review-fix and this
report commit, each with the trailer, pushed after every commit; no `*.py` → build skipped;
verification sub-agent round done (findings above); PR cycle done; merge gate above; no
bookkeeping writes outside this epic; no `/sync-plugin-cache` owed.

## What have we learned (Step 9)

None proposed beyond run 01's recorded observation (the Step-1 "always" skills assume an
implementation run) — this run exercised the same authoring path and surfaced no new contract
gap. The reviewer-retry sequence (failed → rate-limited → successful re-trigger) worked exactly
as the participation contract's recovery check intends.

## Residue

- The §M10 repo-scoping references and §M11 candidates are registered without a drawing plan —
  deliberate, awaiting the `020` mechanism and a repo-scoping design.
- The `LEVEL_TABLE`/`model_map` cross-target import direction is recorded in plan `070` D4 as a
  proposal; the fix is `marketplace/targets` work no current plan owns.
- An executable validator for `doc/plans/**` surface contracts (README table vs. each plan's
  Expected surface, failing on overlap/omission/concurrency drift) — proposed by PR review,
  deferred as its own tooling change; the per-run halting re-derivation remains the guard.
