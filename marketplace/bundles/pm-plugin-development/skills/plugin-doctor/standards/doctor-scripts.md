# Doctor Scripts Workflow

Analyze and fix script quality issues.

## Parameters

- `scope` (optional, default: "marketplace"): "marketplace" | "global" | "project"
- `script-name` (optional): Analyze specific script
- `--no-fix` (optional): Diagnosis only, no fixes

## Step 1: Load Prerequisites and Standards

```
Skill: plan-marshall:ref-development-standards
Skill: pm-plugin-development:plugin-architecture
Skill: pm-plugin-development:plugin-script-architecture
Read references/fix-catalog.md
```

## Step 2: Discover Scripts

```
Glob: pattern="scripts/*.{sh,py}", path="marketplace/bundles/*/skills"
```

## Step 3: Analyze Each Script

- Verify SKILL.md documentation
- Check test file exists
- Verify --help output
- Check stdlib-only compliance

## Step 4: Categorize and Fix

Same pattern with script-specific checks.

## Step 5: Verify and Report

Same pattern with script-specific checks.
