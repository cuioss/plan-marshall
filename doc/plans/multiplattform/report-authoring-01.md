# Run report — multiplattform epic authoring (run 01)

**Date (UTC):** 2026-08-17  **Branch:** `claude/refactor-multiplatform-planning-xurgnn`
**PR:** #1275  **Outcome:** completed

> **This run authored an epic and retired its source material; it did not execute a plan.** The
> `cloud-plan-lane` contract assumes one plan per run, so two of its steps have no counterpart
> here and are reported as not-applicable rather than narrated as done — see § Contract check.
> Following the `test-quality` precedent (`doc/plans/test-quality/report-authoring-01.md`), this
> report lives at the epic root: every plan in this epic is a flat `{NNN}-{slug}.md`, which the
> tree's status model defines as "authored and waiting", so no plan directory exists to own it.
> That location is a deliberate, disclosed deviation.

## Skills loaded

| Skill | Route |
|---|---|
| `.claude/skills/cloud-plan-lane` | loaded as the first action |
| `.claude/skills/author-cloud-plan` | loaded at authoring time — this run's governing judgement |
| `plan-marshall:ref-code-quality` | not loaded — see below |
| `pm-plugin-development:plugin-script-architecture` | not loaded — see below |

The two "always" skills were not loaded, disclosed as a deviation rather than narrated as done:
the diff is documentation-only (plans, reference docs, link rewiring — no production code, no
script, no skill body authored), so the work-identity and script-architecture content had no
surface to govern in this run. The four plans this run authored will each load them per the
lane's Step 1 when they execute.

## Deliverables

The requested outcome: verify `doc/refactor`'s ground truth against the tree, transfer everything
still relevant into a new epic at `doc/plans/multiplattform` (plans + a reference sub-directory
for non-plan material), adversarially review it with a clean sub-agent, and remove `doc/refactor`
entirely — current-state prose only.

| Artifact | Commits | State |
|---|---|---|
| `doc/plans/multiplattform/README.md` — baseline, plannable-vs-gated boundary, concurrency contract | `cfee28c`, `d73fcfd` | complete |
| Plans `010`–`040` (runtime seam neutrality; target-scoped components; Claude-literal residuals; sync-opencode inner loop) | `cfee28c`, `d73fcfd`, `fcb43e3` | complete |
| `reference/principles.md`, `reference/coupling-inventory.md`, `reference/opencode-validation-protocol.md` | `cfee28c`, `d73fcfd`, `fcb43e3` | complete |
| `doc/refactor/` removed (11 files); external references rewired (`AGENTS.md` ×2, ADR-011 citations, `doc/developer/repository-layout.adoc`, `marketplace/targets/opencode/transforms.md`) | `6e0c6bc` | complete |

**Ground-truth verification before authoring.** Three parallel read-only sub-agents verified
every load-bearing `doc/refactor` claim against the tree (build-target side, runtime side,
residuals/docs). Corrections that shaped the epic: the `Runtime` ABC carries 24 operations (the
source material said 18); a third build target (`pr-agent`) is already registered; the idiom
registry carries four dispositions (a `Monitor` entry beyond the documented three);
`manage-metrics` has fully migrated to runtime-normalized tokens; the layout ops and memoised
helpers are routed by the major resolvers; `doc/developer/distribution.adoc` contradicts the live
two-entry publish matrix (became plan `040` D4); `_BASH_CEILING_SECONDS` no longer exists as a
duplicated literal (single-sourced as `HARNESS_BASH_CEILING_SECONDS`, registered in the inventory
as a runtime-fact-in-core). Work `doc/refactor` recorded as open that verification confirmed
still open became the four plans' deliverables; work it recorded as open that is in fact landed
was stated as baseline instead.

## Build gate

`git diff --name-only origin/main...HEAD` (after re-fetching `origin/main` — the stale local ref
initially inflated the diff) → documentation and markdown only, no `*.py`. No buildable
footprint; local build skipped per the lane's `*.py`-only gate; the merge queue's `merge_group`
run is the net.

## Findings

Two adversarial review rounds ran against the persisted epic, each by a clean sub-agent with no
authoring context, before the PR was opened. Round 1: 1 BLOCKER, 4 MAJOR, 7 MINOR, 3 NIT.
Round 2 (verifying the fixes): 0 BLOCKER/MAJOR/MINOR, 2 NIT. All findings fixed except the two
noted rejections; per-instance detail in the fix commits (`d73fcfd`, `fcb43e3`).

### The findings that mattered

1. **BLOCKER — the inventory's completeness claim was false.** Four verified-still-open coupling
   clusters recorded in `doc/refactor` had no home in the epic and would have become unrecorded
   open work on deletion: the plugin-doctor analyzers' segment-wise `.claude/skills` anchors,
   `permission_web.py`'s grammar rendering + settings I/O, the plan-retrospective chat-signal
   transcript parsers, and `generate_executor.py`'s `discover_local_scripts` single-root anchor +
   session-cache write — the last actively buried under an over-broad "sanctioned" entry. Fixed:
   all registered in the inventory with a drawn-by column separating plan-scoped entries from
   recorded-but-unplanned ones; the `generate_executor.py` sanction narrowed to the embedded
   resolver only.
2. **MAJOR — two "it is recorded in the inventory" claims were false** (plan 010's waiting
   non-migration pointer; plan 030's doctor/standards exclusion pointer). Fixed by making the
   records exist: a "Deliberate non-migrations" section and a §B permission-grammar-knowledge
   entry.
3. **MAJOR — a wrong count carried an OBSERVED label**: "exactly five" target-enumerating ABC
   docstrings, where the tree has eleven. Fixed by replacing the count with the class description
   plus a re-derive instruction; round 2 independently confirmed all eleven hits fall inside the
   described classes.
4. **MAJOR — every plan's relative links would dangle after the lane's Step-3 move** (plans move
   one directory deeper; the reference docs do not). Fixed: plans carry full repo paths with the
   reason stated.
5. **MAJOR — the README baseline overstated layout-op adoption**, contradicting plan 030's own
   premise. Fixed to name the two open exceptions explicitly.

### Rejected, with reason

| Finding | Reason |
|---|---|
| NIT — "multiplattform" is a German spelling | The epic name is the operator's own naming of the requested directory; renaming it would break the request it fulfils. |
| MINOR (round 1, partial) — the steward wizard split and reference-file scoping "should be planned, not just recorded" reading | Scoping them into plans now would double plan `020`'s size against an unproven mechanism; the inventory's drawn-by column records them as open work awaiting a future plan, which is the registration the reviewer's own BLOCKER asked for. |

### Verification-loop convergence

Stopped by judgement after round 2, disclosed per the lane: round 2's findings were two
wording-level NITs confined to the epic's own prose (both fixed in `fcb43e3`), no finding in the
round changed a deliverable's meaning, and the round's method (independent re-verification of
every fix plus tree-level spot-checks of every newly registered entry) named what it checked.
Assume residue of the same wording-level class may remain.

## Reviewer participation

Population derived from configuration — the `author_login` of each
`marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md` registry doc:
`cuioss-review-bot`, `coderabbitai`, `sourcery-ai`.

| Reviewer (`author_login`) | Verdict | Reopens? | Body evidence / reason |
|---|---|---|---|
| `cuioss-review-bot` | *pending — filled from the stored bodies at the merge gate* | | |
| `coderabbitai` | *pending — filled from the stored bodies at the merge gate* | | |
| `sourcery-ai` | *pending — filled from the stored bodies at the merge gate* | | |

Verdicts are derived from the stored bodies across all three comment surfaces (`get_reviews`,
`get_comments`, `get_review_comments`), never from check states; the table is completed before
this report's final pre-merge commit.

## Cost

- **Tokens:** not available to the agent in this session for the main loop. The six dispatched
  sub-agents self-reported: three ground-truth verifiers 72,516 / 81,972 / 71,232 tokens (25 /
  41 / 38 tool calls); adversarial round 1: 217,649 tokens (84 tool calls); round 2: 96,187
  tokens (39 tool calls).
- **Wall-clock:** not separately instrumented; sub-agent durations self-reported between ~114 s
  and ~621 s each.
- **Population:** the figures count only those dispatched sub-agents, as self-reported by each.
  They are **not** comparable to a plan-marshall `metrics.toon` total, which counts an
  orchestrator-plus-agent dispatch tree under a per-task billing boundary this interactive cloud
  session does not share. No session total is reported because none was available.

## Contract check (Step 9)

| Step | Verdict |
|---|---|
| 1 Skills loaded | **partial, disclosed** — lane + authoring skill loaded; the two "always" skills deliberately not loaded for a docs-only authoring run (see § Skills loaded) |
| 2 Branch | **done** — harness-assigned `claude/refactor-multiplatform-planning-xurgnn`, kept as-is; clean tree asserted at start; branch pushed to `origin` before any work |
| 3 Plan directory | **not applicable** — this run authored plans; a flat `{NNN}-{slug}.md` is the tree's "authored and waiting" state, and creating plan directories would falsely signal started runs |
| 4 Implement | **done** — commits `cfee28c`, `d73fcfd`, `6e0c6bc`, `fcb43e3` plus any review-cycle fixes and this report's commit, each with the trailer; pushed after every commit |
| 4 Per-commit gate | **not applicable** — no commit touched `*.py` |
| 5 Build gate | **done** — no `*.py` in the branch diff; build skipped, recorded above |
| 6 Verification sub-agent | **done** — two adversarial rounds pre-PR; findings and dispositions above |
| 7 PR cycle | PR #1275 open; all three comment surfaces read and every comment dispositioned before the merge gate; participation table above completed from the stored bodies at that point |
| 8 Merge gate | conditions 1–3 checked at arming; auto-merge armed after this report's commit; landing read back from the PR |
| 8 Bridge | **done** — no status or bookkeeping write under `doc/plans/` outside this epic; the `AGENTS.md`/ADR/layout-doc/transforms-doc edits are declared deliverables of the removal, not bookkeeping |
| 9 This check | **done** — this table |
| 9 What have we learned | **done** — below |

**GitHub access path:** the GitHub MCP server (no `gh` CLI in this session).
**Branch form:** harness-assigned.
**Plugin cache sync:** not owed — a cloud run never performs or records one.

**Commit trailer deviation, disclosed.** The lane specifies `Co-Authored-By: Claude
<noreply@anthropic.com>` with no other footer; this session's harness additionally mandates a
`Claude-Session:` trailer line. Both were included; the model-identifier-free form of the
co-author trailer was chosen where the two instructions conflicted.

## What have we learned (Step 9)

One contract observation, presented to the operator rather than applied (the lane forbids
self-approving a change to the contract that governs the run):

- **The lane's Step 1 "always" skills assume an implementation run.** An epic-authoring run with
  a documentation-only surface has no use for `ref-code-quality` or
  `plugin-script-architecture`, yet the contract states them unconditionally, so every authoring
  run must either spend the context or disclose a deviation (this run and the `test-quality`
  authoring run both chose disclosure — the precedent report loaded them and recorded that no
  conditional skill applied). Proposal: scope the "always" set to runs whose plan touches code,
  the same way the conditional table already keys on surface. *Evidence: this run's Step 1.*

No other contract change proposed: the remaining steps fit an authoring run once the two
documented not-applicables are accepted, and the `test-quality` precedent already records the
same shape.

## Residue

- **The landing itself.** Auto-merge armed after this commit; the squash SHA is read back from
  the PR and reported to the operator, not embedded here.
- **`doc/plans/truthful-signals/130-…/plan.md` names `doc/refactor/README.md` in its Expected
  surface** (a D6 lead). That plan belongs to another epic, so this run did not edit it; its run
  will find the file absent and should treat the lead as resolved-by-removal. Historical run
  reports under `doc/plans/**` also mention `doc/refactor` — they are dated records and were
  deliberately left untouched.
- **Inventory entries with no drawn-by plan** (plugin-doctor anchors, `permission_web.py`, the
  chat-signal cluster, `discover_local_scripts` + session-cache write, the §C vocabulary set,
  three §D candidates) are recorded open work awaiting future plans — by design, not omission.
- **The OpenCode live-validation protocol** waits on an operator with a live install; its
  post-validation section stages the follow-up plans (install-path pin, user/developer docs,
  validation-framing upgrades).
