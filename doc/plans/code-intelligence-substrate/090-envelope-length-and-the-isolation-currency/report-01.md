# Run report — 090-envelope-length-and-the-isolation-currency (run 01)

**Date (UTC):** 2026-08-12 (source: harness `currentDate` context; exact wall-clock not available to the agent)
**Branch:** `claude/envelope-length-isolation-currency-kmo78n` (harness-assigned cloud branch, kept as-is per lane contract)
**PR:** _pending_
**Outcome:** _in progress_

## Skills loaded

- `cloud-plan-lane` — the working contract (loaded first, before reading the plan).
- `plan-marshall:ref-code-quality` — always-load (read from bundle path).
- `pm-documents:ref-asciidoc` — `.adoc` documentation surface (read from bundle path).

`pm-plugin-development:plugin-script-architecture` (an always-load) was **not** loaded: this run edits
no scripts and no bundle skills — the only change is a concept `.adoc` and its diagram SVG, both under
`doc/`. Recorded here rather than silently skipped.

## D0 gate — is an instrumented population reachable in this clone?

**Resolved: no instrumented population is reachable.** The measurements the plan rests on come from
archived run-metrics records under `.plan/`, which is machine-local, git-ignored state (`CLAUDE.md`
§ "Standalone Plan Lane": `.plan/` "lives only on the machine that created it, so a cloud session at
claude.ai/code clones the repository and has none of it"). This is a fresh cloud clone, so the corpus
is absent. Established from that structural fact — **not** by searching for the records, per D0's
explicit ⛔.

**Consequence per D0:** D1, D3, and D4's selection are **blocked on corpus availability**. **D2 is
shippable** — it is a documentation correction whose evidence is the argument itself, not the corpus.
No population was fabricated.

## Deliverables

| Deliverable | State | Notes |
|---|---|---|
| D0 — gate | **done** | Resolved: no population reachable (above). |
| D1 — publish the two factors | **blocked** | Requires the instrumented population (absent). Cannot derive resident-context / turns per phase without the corpus; no figure fabricated. |
| D2 — restate `token-management.adoc` § 6 in the measured currency | **in progress** | See below. |
| D3 — settle the creation/read inversion | **blocked** | D0 halts D3: the inversion's phase is identified from the population, which is absent. Cannot name the phase, so cannot read the mechanism for _that_ phase. No mechanism inferred from a ratio (there is no ratio to read). |
| D4 — one envelope-length lever, chosen by D1 | **blocked** | D0 halts D4's selection: the split is chosen by D1, which is blocked. |

### D2 — detail

The correction target is `doc/concepts/token-management.adoc` § 6 "Per-dispatch context isolation",
whose defense of isolation rests on the phrase _"independent — and never additive"_ — the
orchestrator-context currency the plan identifies as the mismatch. The same figures and the same
currency error are baked into the section's diagram, `doc/resources/diagrams/context-isolation.svg`
(its right-column caption `~5 K + 3 × ~300 ≈ 6 K` presents orchestrator-context size _as the cost_).

Actions:
1. Rewrite § 6's argument in billing-weight / turns-resident currency: a byte is billed at creation
   and re-billed on every turn it stays resident; isolation does not make a byte cheaper and each
   dispatch's context **is** additive to the bill — what isolation bounds is **residency** (how many
   turns a byte is re-read for). Recommendation kept intact: isolation remains "the biggest single
   token-management lever".
2. Remove § 6's unverifiable numeric figures (`10-15 K`, `30-50 K`, `~6 K`, `~200-500 tokens`).
   D1 is blocked, so they cannot be re-derived; per the plan's "delete rather than correct" guidance
   for a moving system, they are removed rather than restated.
3. Correct the diagram (`context-isolation.svg`) in lock-step: remove the same figures and recast the
   `≈ 6 K` orchestrator-cost caption into the residency framing, so a cold reader of § 6 (prose _and_
   diagram) sees the argument in the measured currency.

## Build gate

_To be recorded after the diff is complete._ Expectation: `git diff --name-only origin/main...HEAD --
'*.py'` is empty (the change is `doc/**` only), so no local build runs — the merge queue's
`merge_group` run verifies the docs-only change.

## Findings

_Pending the pre-PR verification sub-agent (Step 6), CI, and PR review._

## Reviewer participation

_Pending PR creation._

## Cost

- **Tokens:** not available to the agent in this session.
- **Wall-clock:** not separately available; run performed in one interactive cloud session on
  2026-08-12 (UTC).
- **Population:** this single Claude Code cloud session's usage. **Not comparable** to a plan-marshall
  `metrics.toon` total, which counts the orchestrator-plus-agent dispatch tree under plan-marshall's
  own per-task billing boundary that a single interactive cloud session does not share.

## Contract check (Step 9)

_To be completed as the final pre-merge action._

## What have we learned (Step 9)

_To be completed._

## Residue

- D1, D3, D4 remain blocked on corpus availability; they should be picked up in a session/run that has
  a reachable instrumented population (a local run against a machine that holds the archived
  `.plan/` metrics, or after the WS-04 emission plan publishes the two factors).
- Pre-existing duplicate figure: `doc/concepts/token-management.adoc` § "Where Plan Marshall
  deliberately spends more" (the Q-Gate bullet) restates `~10-15 K tokens of variant context`. This is
  the same skill-body figure removed from § 6, but it lives in a **different** section that is out of
  D2's stated § 6 scope, and this edit does not make it false. Left in place and flagged here rather
  than expanding scope with an undeclared collateral change.
