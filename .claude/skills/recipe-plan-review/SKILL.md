---
name: recipe-plan-review
description: Recipe skill that reviews a recently landed (archived) plan against its original request and surfaces fix-worthy gaps
user-invocable: false
allowed-tools: Read, Glob, Bash, AskUserQuestion, Skill
implements: plan-marshall:extension-api/standards/ext-point-recipe
---

# Recipe: Review and Improve a Recently Landed Plan

Recipe skill that reviews a recently landed (archived) plan against its original request and the implementation that actually merged, then surfaces gaps for the user. The recipe is **analytical only** — its sole mutating action is, on user agreement, kicking off a separate `/plan-marshall task="…"` fix plan (the standard fix workflow, not part of this recipe). Loaded by phase-3-outline when this recipe is selected.

## Input Parameters

| Parameter | Source |
|-----------|--------|
| `plan_id` | From phase-3-outline |
| `recipe_domain` | `plan-marshall-plugin-dev` |

`recipe_profile` and `recipe_package_source` are not needed by this analytical recipe and are omitted — the recipe creates no implementation/test deliverables of its own.

## Enforcement

**Execution mode**: Read-only analytical review with a pinned coverage cell. Select an archived plan, compare its original request against the merged implementation, surface gaps, and — only on explicit user agreement — kick off a separate fix plan.

**Prohibited actions:**
- NEVER mutate any source file. The recipe writes no source — its single mutating action is the user-agreed `/plan-marshall task="…"` fix-plan kickoff, which is a separate workflow.
- Do NOT ask the user about the coverage cell — it is pinned (`T5` × `overall`). The gather step of the coverage-gathering contract is deliberately skipped.
- Do NOT fall back to a backing script for the analytical request-vs-landed comparison — the recipe is LLM-driven by design (matching the sibling `recipe-plugin-compliance`).

**Constraints:**
- Strictly comply with all rules from `dev-agent-behavior-rules`, especially tool usage and workflow step discipline.

## Workflow

### Step 0: Pin and expand the coverage cell (no gather)

This recipe implements the [coverage-gathering contract](../../../marketplace/bundles/plan-marshall/skills/dev-agent-behavior-rules/standards/coverage-gathering-contract.md)'s **consume** obligation but deliberately skips the **gather** (`AskUserQuestion`) step: the whole point of the recipe is thorough, high-coverage verification, so the cell is pinned rather than asked. Pin `thoroughness=T5, scope=overall` (exhaustive/adversarial depth + whole-corpus-of-aspects breadth). The coupling constraint (`reject thoroughness ≥ T4 ∧ scope < component`) is satisfied because `overall ≥ component`.

Expand the pinned cell once and persist BOTH the identifier and the expanded instruction to `status.json` metadata (this recipe is plan-bound):

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config coverage expand --thoroughness T5 --scope overall
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata --plan-id {plan_id} --set --field coverage_thoroughness --value T5
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata --plan-id {plan_id} --set --field coverage_scope --value overall
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata --plan-id {plan_id} --set --field coverage_instruction --value {expanded_instruction}
```

Consume the **expanded instruction** (NOT the raw cell) in Steps 3–5 below to govern review depth and breadth. Do NOT restate the `thoroughness.md` ladders or the contract's cell→instruction table here — cross-reference them.

### Step 1: List archived plans newest-first

Glob the archived-plan corpus for directory entries:

```
Glob: .plan/local/archived-plans/*
```

Archived-plan directories are date-prefixed (`YYYY-MM-DD-…`), so reverse-sort the entry names to present them newest-first.

### Step 2: User selects the plan to review

Present the newest-first list and have the user pick one via `AskUserQuestion`. The selected directory is the review target for the remaining steps.

### Step 3: Read the plan's intent and landed surface

For the selected plan directory, read:
- `request.md` — the original intent (what the plan set out to do).
- `references.json` `modified_files` — the landed surface (which files actually changed when the plan merged).

```
Read: .plan/local/archived-plans/{selected}/request.md
Read: .plan/local/archived-plans/{selected}/references.json
```

### Step 4: Request-vs-landed comparison

Perform the thorough, high-coverage comparison the pinned coverage cell (Step 0) mandates:
- Verify every aspect of the original request was **completely** done — not partially, not approximately.
- Verify side aspects are thoroughly implemented: **configuration**, **documentation**, and **tests** for the requested change.
- Trace each requested aspect to the landed surface and note any aspect that was requested but not delivered, or delivered incompletely.

### Step 5: Spot-check artifacts on disk

Spot-check **≥10%** of the `modified_files` against their on-disk state, reading each sampled artifact in full:

```
Read: {sampled modified file path}
```

Confirm the landed change matches what the request asked for and that no obfuscation or stub-only implementation slipped through.

### Step 6: Present findings and discuss

Gather all findings from Steps 4–5 into a concise gap report and present it to the user. Discuss which gaps (if any) are worth a follow-up fix.

### Step 7: Hand off a fix plan (only on user agreement)

This is the recipe's **single** mutating action, and it is a separate workflow. ONLY on explicit user agreement, kick off a standard fix plan describing the agreed gaps:

```
/plan-marshall task="<description of the agreed gaps to fix>"
```

The recipe itself writes no source — the fix plan is the standard plan-marshall workflow that the user opts into. If the user does not agree to any fix, the recipe ends with the findings report and no mutation.

## Related

- [coverage-gathering-contract.md](../../../marketplace/bundles/plan-marshall/skills/dev-agent-behavior-rules/standards/coverage-gathering-contract.md) — the consume obligation, the pinned-cell expand/persist mechanism, and the cross-reference target this recipe consumes.
- [ext-point-recipe.md](../../../marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-recipe.md) — the recipe discovery/registration contract that governs project-local `recipe-*` auto-discovery.
- `recipe-plugin-compliance` — sibling project-local, LLM-driven recipe; the convention template for frontmatter, the `recipe_domain` table row, and the coverage-cell step.
- `audit-archived-plan-retrospectives` — reads the same `.plan/local/archived-plans/` corpus for a complementary retrospective audit.
