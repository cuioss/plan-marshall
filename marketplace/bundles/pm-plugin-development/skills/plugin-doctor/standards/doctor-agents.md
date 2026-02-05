# Doctor Agents Workflow

Analyze and fix agent quality issues.

## Parameters

- `scope` (optional, default: "marketplace"): "marketplace" | "global" | "project"
- `agent-name` (optional): Analyze specific agent
- `--no-fix` (optional): Diagnosis only, no fixes

## Step 1: Load Prerequisites and Standards

```
Skill: plan-marshall:ref-development-standards
Skill: pm-plugin-development:plugin-architecture
Read references/agents-guide.md
Read references/fix-catalog.md
```

## Step 2: Discover Agents

**marketplace scope** (default):
```
Skill: pm-plugin-development:tools-marketplace-inventory
```

**global/project scope**:
```
Glob: pattern="*.md", path="{scope_path}/agents"
```

## Step 3: Analyze Agents

Use the batch analyze command filtered to agents:

```bash
python3 .plan/execute-script.py pm-plugin-development:plugin-doctor:doctor-marketplace analyze \
  --bundles {bundle} --type agents
```

This returns JSON with per-agent analysis including markdown structure, tool coverage, and reference validation.

**Check against agents-guide.md**:
- Tool fit score >= 70% (good) or >= 90% (excellent)
- No Rule 6 violations (agents CANNOT use Task tool)
- No Rule 7 violations (only maven-builder can use Maven)
- No Pattern 22 violations (must use manage-lessons skill, not self-invoke)
- Bloat thresholds (component-type specific):
  - Agents: NORMAL (<300), LARGE (300-500), BLOATED (500-800), CRITICAL (>800)
  - Commands: NORMAL (<100), LARGE (100-150), BLOATED (150-200), CRITICAL (>200)
  - Skills: NORMAL (<400), LARGE (400-800), BLOATED (800-1200), CRITICAL (>1200)

## Step 4: Categorize and Fix

**Safe fixes** (auto-apply unless --no-fix):
- Missing frontmatter fields
- Unused tools in frontmatter
- Invalid YAML syntax

**Risky fixes** (always prompt):
- Rule 6 violations (requires architectural refactoring)
- Rule 7 violations (Maven usage restriction)
- Pattern 22 violations (self-invocation)
- Bloat issues (agents >500 lines)

## Step 5: Verify and Report

```bash
git status --short
```

Display summary using reporting-templates.md format.
