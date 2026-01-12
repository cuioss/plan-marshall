---
name: js-enforce-eslint
description: Enforce ESLint standards by fixing violations systematically
allowed-tools: Skill, Read, Edit, Glob, Grep, Bash, SlashCommand
---

# CUI ESLint Enforce Command

Orchestrates systematic ESLint violation fixing workflow with standards compliance.

## CONTINUOUS IMPROVEMENT RULE

If you discover issues or improvements during execution, record them:

1. **Activate skill**: `Skill: plan-marshall:lessons-learned`
2. **Record lesson** with:
   - Component: `{type: "command", name: "js-enforce-eslint", bundle: "pm-dev-frontend"}`
   - Category: bug | improvement | pattern | anti-pattern
   - Summary and detail of the finding

## PARAMETERS

- **files** - (Optional) Specific files to fix; if unset, analyze all lintable files
- **workspace** - (Optional) Workspace name for monorepo projects
- **fix-mode** - `auto` (ESLint --fix) or `manual` (agent fixes); default: `auto`

## WORKFLOW

### Step 1: Run ESLint

**Execute lint command:**
```bash
npm run lint > target/npm-lint-output.log 2>&1
# Or with workspace:
npm run lint --workspace={workspace} > target/npm-lint-output.log 2>&1
```

**Parse output for structured violations:**
```bash
python3 .plan/execute-script.py pm-dev-frontend:cui-javascript-project:npm-output parse-npm-output \
    --log target/npm-lint-output.log --mode structured
```

### Step 2: Auto-Fix (if fix-mode=auto)

**Execute lint with --fix:**
```bash
npm run lint -- --fix > target/npm-lint-fix-output.log 2>&1
```

Re-run lint to check remaining issues.

### Step 3: Manual Fix (for unfixable violations)

For each remaining violation:

```
SlashCommand: /pm-dev-frontend:js-implement-code task="Fix ESLint violation: {violation.message}

Rule: {violation.rule}
Line: {violation.line}

Apply appropriate fix following ESLint and CUI standards.
Verify build after changes." files="{violation.file}"
```

### Step 4: Verify Clean Lint

**Execute final lint check:**
```bash
npm run lint > target/npm-lint-verify.log 2>&1
```

**Parse output to verify zero violations:**
```bash
python3 .plan/execute-script.py pm-dev-frontend:cui-javascript-project:npm-output parse-npm-output \
    --log target/npm-lint-verify.log --mode errors
```

### Step 5: Return Summary

```
ESLINT ENFORCE COMPLETE

Violations Fixed:
- Auto-fixed: {auto_count}
- Manually fixed: {manual_count}
- Total: {total_count}

Files Modified: {count}

Lint Status: {CLEAN|PARTIAL}
```

## RELATED

- Skill: `pm-dev-frontend:cui-javascript-project` - Parse npm Build Output workflow
- Skill: `pm-dev-frontend:cui-javascript-linting` - ESLint standards
- Command: `/js-implement-code` - Fixes manual violations
