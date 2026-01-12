---
name: js-fix-jsdoc
description: Fix JSDoc errors and warnings from build/lint with content preservation
allowed-tools: Skill, Read, Edit, Glob, Grep, Bash, SlashCommand
---

# CUI JSDoc Fix Command

Orchestrates systematic JSDoc violation fixing workflow with standards compliance.

## CONTINUOUS IMPROVEMENT RULE

If you discover issues or improvements during execution, record them:

1. **Activate skill**: `Skill: plan-marshall:lessons-learned`
2. **Record lesson** with:
   - Component: `{type: "command", name: "js-fix-jsdoc", bundle: "pm-dev-frontend"}`
   - Category: bug | improvement | pattern | anti-pattern
   - Summary and detail of the finding

## PARAMETERS

- **files** - (Optional) Specific files to fix; if unset, analyze all JavaScript files
- **workspace** - (Optional) Workspace name for monorepo projects

## WORKFLOW

### Step 1: Identify JSDoc Violations

**Load skill and execute workflow:**
```
Skill: pm-dev-frontend:cui-jsdoc
Execute workflow: Analyze JSDoc Violations
```

Or run script directly:
```bash
# Analyze directory
python3 .plan/execute-script.py pm-dev-frontend:cui-jsdoc:jsdoc analyze --directory src/

# Analyze specific file
python3 .plan/execute-script.py pm-dev-frontend:cui-jsdoc:jsdoc analyze --file {files}
```

Script returns structured JSON with violations categorized by severity (CRITICAL, WARNING, SUGGESTION).

### Step 2: Prioritize Violations

Categorize by severity:
- CRITICAL: Exported/public API without JSDoc (fix first)
- WARNING: Internal functions without JSDoc
- SUGGESTION: Optional improvements

### Step 3: Fix Violations Systematically

For each violation (CRITICAL → WARNING):

```
SlashCommand: /pm-dev-frontend:js-implement-code task="Add JSDoc documentation for {violation.target}.

Type: {violation.type}
Line: {violation.line}
Fix suggestion: {violation.fix_suggestion}

Follow cui-jsdoc standards.
Verify build after changes." files="{violation.file}"
```

Track: `fixes_applied`, `fixes_failed`

### Step 4: Verify Build

**Execute lint command:**
```bash
npm run lint > target/npm-lint-output.log 2>&1
```

**Parse output to verify no JSDoc errors remain:**
```bash
python3 .plan/execute-script.py pm-dev-frontend:cui-javascript-project:npm-output parse-npm-output \
    --log target/npm-lint-output.log --mode errors
```

### Step 5: Return Summary

```
JSDOC FIX COMPLETE

Violations Fixed:
- Critical: {critical_fixed}/{critical_total}
- Warnings: {warnings_fixed}/{warnings_total}

Files Modified: {count}

Build Status: {SUCCESS|PARTIAL}

Result: {summary}
```

## RELATED

- Skill: `pm-dev-frontend:cui-jsdoc` - Analyze JSDoc Violations workflow
- Skill: `pm-dev-frontend:cui-javascript-project` - Parse npm Build Output workflow
- Command: `/js-implement-code` - Fixes violations
