envelope_version=1
sender_type=plan
sender_id=context-byte-attribution-instrumentation
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-03T16:51:01Z

component=plan-marshall:manage-architecture
category=improvement
bundle=plan-marshall

# The structured index cannot answer for `.claude/skills/` — so "structured queries first" silently degrades to a whole-tree fallback

`pre-push-quality-gate` emitted, at `2026-08-03T11:59:33Z`:

```text
[WARNING] (plan-marshall:pre-push-quality-gate) Footprint paths resolved to no registered
module: .claude/skills/audit-archived-plan-retrospectives/SKILL.md,
.claude/skills/audit-archived-plan-retrospectives/checks/billing-composition.md,
.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py
— proceeding whole-tree. Scoped coverage for these paths is not determinable.
```

3 of this plan's 12 footprint files — **a quarter of the change** — resolve to no registered module. The same 3 files are then filtered out of the manifest cross-check, so they are invisible to two different gates for the same underlying reason.

## Why this belongs to `code-intelligence-substrate` specifically

`CLAUDE.md` and `persona-plan-marshall-agent` both carry **"Structured queries first"** as a hard rule: consult `architecture files --module X` / `which-module --path P` / `find --pattern P` before reaching for Glob/Grep. The rule is premised on the index being able to answer.

For the entire project-local `.claude/skills/` tree, it cannot. And the failure mode is the dangerous one: `which-module --path .claude/skills/...` does not return "this surface is outside the inventory" — it returns *no module*, which is structurally indistinguishable from "no such file" and from "file in no module". A caller obeying the hard rule gets a zero and cannot tell **which kind of zero** it is.

That is this epic's recurring theme in its purest form: *a zero meaning "could not look" and a zero meaning "looked, found nothing" do not share a representation.* The inbox-envelope drain contract already solves exactly this problem with its `inbox_state` discriminator (`epic_not_found` / `missing` / `present`+`count: 0`). The architecture inventory has no equivalent.

## Downstream cost, observed in this run

1. **Gate scope collapses.** `pre-push-quality-gate` abandoned scoping and ran whole-tree. Whole-tree `module-tests` then timed out at 462s against the daemon budget, which is precisely the cost the scoping exists to avoid. The unregistered paths caused the timeout, transitively.
2. **Coverage becomes undeterminable, not merely unscoped.** The warning says so in its own words: "Scoped coverage for these paths is not determinable." The gate passed, but it passed without being able to state what it covered.
3. **`plugin-doctor` narrowed in the same direction** — its scoped run gated skill-local rules over 3 skill dirs only and warned that cross-skill invariants whose counterpart lives outside `--paths` were not evaluated, surfacing first at whole-tree CI (the PR #915 class).

## Solution

1. **Register the `.claude/skills/` tree in the architecture inventory** so `which-module` / `files` / `find` answer for it. These are first-class project-local skills with real Python under `scripts/` — `audit.py` alone is >7800 lines and carries 24 audit checks. It is not a scratch directory.
2. **Give the path-resolution verbs a "could not look" discriminator**, so an unregistered *surface* is distinguishable from an unmatched *file*. Without this, fix (1) closes today's gap but leaves the general failure mode intact for the next unregistered tree.
3. Until (1) lands, `pre-push-quality-gate`'s whole-tree fallback is correct behaviour and should stay — the WARNING is honest and should not be softened.

## Impact

Any plan whose footprint touches `.claude/skills/` — which includes every plan that edits the retrospective auditor, and therefore a large share of this epic's own work. The instrumentation this epic is building lives substantially in `.claude/skills/audit-archived-plan-retrospectives/`, so **the epic's own changes are the ones the index cannot scope.**

**Note for the orchestrator-side pickup:** `plan-retrospective` surfaced this at medium confidence and withheld it from the inbox at its confidence bar (`work/fragment-lessons-proposal.toon`, `medium_confidence_reported_not_recorded[3]`). Routed here because the gate warning sits in this step's signal population and because the which-kind-of-zero framing is squarely this epic's theme. Not a duplicate of messages 001-006.
