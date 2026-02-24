# Command Quality Standards

Commands are user-facing orchestrators invoked via `/command-name`. They coordinate agents, skills, and tools.

**Architecture**: Command (thin wrapper, ~50-100 lines) → Skill (workflow logic) → Script (computational logic).

## Required Structure

Commands are pure Markdown (no YAML frontmatter). Required sections:

| Section | Content |
|---------|---------|
| Title + description | One-sentence purpose |
| PURPOSE | Detailed purpose statement |
| PARAMETERS | All params with types, defaults, descriptions |
| WORKFLOW | Step-by-step execution via skill invocation |
| CONTINUOUS IMPROVEMENT RULE | Lessons-learned pattern via `manage-lessons` skill |

Optional: RELATED, EXAMPLES, NOTES.

## The 9 Anti-Bloat Rules

### command-thin-wrapper

Commands delegate all workflow logic to skills. Commands contain only parameter docs, skill invocation, and brief examples. No step-by-step logic, analysis algorithms, or validation rules.

```markdown
## Workflow
Activate `bundle:my-skill` and execute the **My Workflow** workflow.
```

### command-delegate-to-agents

Delegate complex operations (analysis, validation, code generation) to agents via Task tool. Keep only simple orchestration inline (parameter validation, Glob, JSON parsing, AskUserQuestion).

### command-use-task-tool

Use Task tool for any non-trivial operation. Complex = file analysis, validation logic, code generation, multi-step reasoning.

### command-no-duplicate-logic

Do not duplicate logic from agents. If an agent already implements analysis/validation, invoke it instead of reimplementing.

### command-clear-parameters

Document all parameters with type, default, description. Example:
```markdown
**scope** (optional, default: "marketplace") — Values: "marketplace" | "global" | "project"
```

### command-bundle-orchestration

For multi-component processing: group by bundle, process sequentially. Complete all steps for one bundle before proceeding to the next.

### command-progressive-disclosure

Load skills/resources on-demand, not all upfront. Load specific skills only when needed in particular steps.

### command-completion-checks

After fixes: run `git status --short`, compare claimed vs actual changes, report PASS/FAIL. Verify all components analyzed, issues categorized, fixes verified before proceeding.

### command-no-embedded-standards

No standards documentation blocks in commands. Standards belong in skills or reference guides.

## Bloat Thresholds

| Classification | Lines | Action |
|---------------|-------|--------|
| IDEAL | < 100 | Proper thin wrapper |
| ACCEPTABLE | 100-150 | Minor logic OK |
| BLOATED | 150-200 | Needs refactoring |
| CRITICAL | > 200 | Immediate refactoring |

If command > 100 lines, logic should move to a skill.

## Orchestration Patterns

| Pattern | Use Case | Key Behavior |
|---------|----------|-------------|
| Single Component | Analyze one component by name | Glob for specific file, verify 1 match |
| Scope-Based Discovery | Analyze by scope param | marketplace (inventory), global (~/.claude), project (.claude) |
| Bundle-by-Bundle | Process multiple components | Group by bundle, sequential processing, completion checks |
| Parallel Within Bundle | Analyze multiple components in same bundle | Launch agents in parallel within bundle, sequential between bundles |
| Two-Phase Fix | Categorize then apply fixes | Safe fixes auto-applied, risky fixes prompt via AskUserQuestion |
| Progressive Loading | Load skills on-demand | Core skills first, additional skills only when needed |

## Reference Format

- **SlashCommand**: no bundle prefix (`/command-name`)
- **Task**: bundle prefix required (`subagent_type="bundle:agent"`)
- **Skill**: bundle prefix required (`Skill: bundle:skill-name`)

## CONTINUOUS IMPROVEMENT RULE

Commands use the `manage-lessons` skill pattern:
```markdown
## CONTINUOUS IMPROVEMENT RULE
If you discover issues during execution:
1. Activate `Skill: plan-marshall:manage-lessons`
2. Record lesson with component, category, and detail
```

## Common Issues

| Issue | Symptom | Fix |
|-------|---------|-----|
| Bloat > 200 lines | CRITICAL classification | Extract logic to skill/agent |
| Missing PARAMETERS | No parameter docs | Add section with types and defaults |
| No bundle orchestration | Parallel without grouping | Refactor to bundle-by-bundle pattern |
| Missing verification | No git status after fixes | Add POST-FIX VERIFICATION step |
| Wrong bundle prefix | Prefix on SlashCommand or missing on Task/Skill | Fix per reference format rules |
| Embedded standards | Large standards blocks | Move to skill or reference guide |

## Summary Checklist

- Thin wrapper delegating to skill (< 100 lines ideal, < 150 acceptable)
- No workflow logic in command (all in skill)
- Delegates to agents for complex operations
- Clear PARAMETERS section
- Bundle-by-bundle orchestration (if multi-component)
- Progressive disclosure (skills loaded on-demand)
- Completion checks and POST-FIX VERIFICATION
- No embedded standards
- Proper bundle prefix usage
- CONTINUOUS IMPROVEMENT RULE present
