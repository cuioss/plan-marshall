envelope_version=1
sender_type=plan
sender_id=misconfigured-reviewer-name-reads-missing-review
epic=review-apparatus
kind=candidate-lesson
created=2026-09-03T23:43:12Z

# The composed manifest ran plan-retrospective (order 995) before lessons-capture (order 991), so the orchestration verdict was never resolved before its first consumer

**Component**: `plan-marshall:phase-6-finalize`
**Category**: bug
**Source plan**: `misconfigured-reviewer-name-reads-missing-review` (PR #1392, merged `cc5ea40a1a6e600e3a7a7b957eace9e085e21129`)

## Context

This plan is orchestrated (epic `review-apparatus`, spec PLAN-PR-044). Its
`plan-marshall:plan-retrospective` step nonetheless ran with `orchestrated=false` /
`epic=""`, took the non-orchestrated branch exactly as its contract requires, and filed
six lessons plus two recurrence merges into the **global** lessons store. The epic inbox
received nothing from this plan until this step. See the sibling candidate for the index
of what is now epic-invisible.

## What is verified

Three primary-source readings, each independently checkable:

1. **The declared orders are what the docs say, in both source and plugin cache.**
   `phase-6-finalize/workflow/lessons-capture.md` frontmatter `order: 991`;
   `plan-retrospective/SKILL.md` frontmatter `order: 995`. The
   `marketplace/bundles/` copy and the `target/claude/` cached copy agree, so this is
   not cache skew.

2. **The composed manifest is out of ascending order at exactly this pair.**
   `manage-execution-manifest read --plan-id misconfigured-reviewer-name-reads-missing-review`
   returns `phase_6.steps[23]` with, at positions 17 and 18:

   ```text
   - "plan-marshall:plan-retrospective"     # order 995
   - lessons-capture                        # order 991
   ```

   Every other neighbouring pair in that list is ascending. This one inverts.

3. **The dispatch actually followed that inverted order.** The manifest
   `execution_log` records `"plan-marshall:plan-retrospective",6-finalize,executed`
   at `2026-09-03T23:36:50Z`, and carries **no** `lessons-capture` row at all —
   lessons-capture is the step writing this message, running after it.

## Why that is fatal rather than cosmetic

`phase-6-finalize/SKILL.md` Step 3 item **4b.a0** is the single resolution site for the
once-per-run orchestration verdict. It is nested inside the lessons-capture Signal Gate:
item 4b is introduced as *"run BEFORE dispatching the step if `step_id == "lessons-capture"`"*.
Its own justification for serving the other consumers is an ordering argument:

> "All four run at or after `order: 991`, so the verdict resolved here is available to each of them."

That argument is sound only if the runtime order matches the declared order. Here it does
not, so the producer of the verdict ran **after** its first consumer. With no reading
available at dispatch time, the dispatcher supplied an assertion (`orchestrated=false`,
`epic=""`), and the retrospective — forbidden by its own input contract from re-deriving
it — obeyed.

Note also SKILL.md's own statement that the dispatcher "iterates the list as written and
does NOT re-sort or validate `order` at runtime — the persisted order is the runtime
order." Nothing downstream of compose can catch this.

## Root cause: located, mechanism NOT established

The inversion is located at compose time, but **which** compose-layer behaviour produced
it is not established by this plan and should not be assumed. Two leads, both cheap to
settle and neither yet tested:

- SKILL.md states the ordering is "resolved through the single choke-point
  `_manifest_validation._sort_steps_by_frontmatter_order`, consumed by BOTH the plan-local
  manifest composer AND `manage-config steps-sort`", and that "the ascending-order
  validator asserts the barrier holds". An invariant that is documented as asserted, and
  is observably violated in a live manifest, is either not asserted over this range or not
  asserted at all.
- SKILL.md also says a step's `order` comes from different sources per step type —
  frontmatter for `default:` steps, "the return-dict `order` field" for
  extension-contributed `bundle:skill` steps. `plan-marshall:plan-retrospective` is the
  only `bundle:skill` step in this neighbourhood. If its order is resolved through a
  different path than lessons-capture's, the two may never have been compared on the
  same key.

The same inversion is present in tracked `.plan/marshal.json`'s
`plan.phase-6-finalize.steps` keyed map (`plan-marshall:plan-retrospective` precedes
`default:lessons-capture`), which `marshall-steward` is documented to write in sorted
order — so whatever the mechanism is, it is not confined to this one plan's compose.

## Proposed action

1. Settle the mechanism first: determine whether the ascending-order validator covers the
   whole roster, and whether `bundle:skill` steps and `default:` steps have their `order`
   resolved through the same key before sorting.
2. Make the ascending-order violation **loud at compose time**. A composed manifest that
   disagrees with its own declared frontmatter order is a defect the composer can see and
   the dispatcher structurally cannot.
3. Do not fix this by hand-editing the roster order. The persisted order was produced by
   the sort; correcting the output without correcting the producer re-opens on the next
   `marshall-steward` run.

## Evidence

- artifact: `manage-execution-manifest read --plan-id misconfigured-reviewer-name-reads-missing-review` — `phase_6.steps` positions 17/18, and `execution_log` (33 rows, retrospective at `2026-09-03T23:36:50Z`, no lessons-capture row)
- source: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/lessons-capture.md` frontmatter `order: 991`
- source: `marketplace/bundles/plan-marshall/skills/plan-retrospective/SKILL.md` frontmatter `order: 995`
- source: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md` Step 3 items 4b and 4b.a0 (the gate nesting and the ordering justification), and the "persisted order is the runtime order" statement
- config: `manage-config plan phase-6-finalize get --field steps` — the same inversion in the tracked roster
- sibling candidate: the structural half (why the wrong verdict was undetectable at the consumer) and the index of the eight epic-invisible corpus entries
