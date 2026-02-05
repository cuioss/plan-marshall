# Doctor Metadata Workflow

Analyze and fix plugin.json quality issues.

## Parameters

- `scope` (optional, default: "marketplace"): "marketplace" | "global" | "project"
- `--no-fix` (optional): Diagnosis only, no fixes

## Step 1: Load Prerequisites and Standards

```
Skill: plan-marshall:ref-development-standards
Read references/metadata-guide.md
Read references/fix-catalog.md
```

## Step 2: Discover plugin.json Files

```
Glob: pattern="**/plugin.json", path="marketplace/bundles"
```

## Step 3: Analyze Each plugin.json

- Verify JSON syntax
- Check required fields (name, version, description)
- Validate component arrays (commands, skills, agents)
- Cross-check declared components vs actual files

## Step 4: Categorize and Fix

**Safe fixes**:
- Missing required fields
- Extra entries (files don't exist)
- Missing entries (files exist but not listed)

## Step 5: Verify and Report

Same pattern with metadata-specific checks.
