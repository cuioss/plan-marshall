# Doctor Agents Workflow

Follows the common workflow pattern (see SKILL.md). Reference guide: `agents-guide.md`.

## Parameters

- `scope` (optional, default: "marketplace"): "marketplace" | "global" | "project"
- `agent-name` (optional): Analyze specific agent
- `--no-fix` (optional): Diagnosis only, no fixes

## Agent-Specific Checks

**Check against agents-guide.md**:
- Tool fit score >= 70% (good) or >= 90% (excellent)
- No agent-task-tool-prohibited violations (agents cannot use Task tool)
- No agent-maven-restricted violations (only maven-builder can use Maven)
- No agent-lessons-via-skill violations (must use manage-lessons skill, not self-invoke)

**Bloat thresholds** (component-type specific):

| Component | NORMAL | LARGE | BLOATED | CRITICAL |
|-----------|--------|-------|---------|----------|
| Agents | <300 | 300-500 | 500-800 | >800 |
| Commands | <100 | 100-150 | 150-200 | >200 |
| Skills | <400 | 400-800 | 800-1200 | >1200 |

## Agent-Specific Fix Categories

**Risky fixes** (always prompt):
- agent-task-tool-prohibited violations (requires architectural refactoring)
- agent-maven-restricted violations (Maven usage restriction)
- agent-lessons-via-skill violations (self-invocation)
- Bloat issues (agents >500 lines)
