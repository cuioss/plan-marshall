---
name: js-generate-coverage
description: Self-contained command for coverage generation and analysis
allowed-tools: Skill, Read, Glob, Grep, Bash
---

# JavaScript Coverage Report Command

Self-contained command that generates test coverage reports and analyzes results.

## CONTINUOUS IMPROVEMENT RULE

If you discover issues or improvements during execution, record them:

1. **Activate skill**: `Skill: plan-marshall:lessons-learned`
2. **Record lesson** with:
   - Component: `{type: "command", name: "js-generate-coverage", bundle: "pm-dev-frontend"}`
   - Category: bug | improvement | pattern | anti-pattern
   - Summary and detail of the finding

## PARAMETERS

- **files** - (Optional) Specific files to check coverage for
- **workspace** - (Optional) Workspace name for monorepo projects

## WORKFLOW

### Step 1: Generate Coverage

**Execute npm coverage command:**
```bash
npm run test:coverage > target/npm-coverage-output.log 2>&1
# Or with workspace:
npm run test:coverage --workspace={workspace} > target/npm-coverage-output.log 2>&1
```

**Parse build output (if needed):**
```bash
python3 .plan/execute-script.py pm-dev-frontend:cui-javascript-project:npm-output parse-npm-output \
    --log target/npm-coverage-output.log --mode structured
```

This generates coverage reports in coverage/ directory.

### Step 2: Analyze Coverage

**Load skill and execute workflow:**
```
Skill: pm-dev-frontend:cui-javascript-unit-testing
Execute workflow: Analyze Coverage
```

Or run script directly:
```bash
python3 .plan/execute-script.py pm-dev-frontend:cui-javascript-unit-testing:js-coverage analyze --report coverage/coverage-summary.json
# Or for LCOV format:
python3 .plan/execute-script.py pm-dev-frontend:cui-javascript-unit-testing:js-coverage analyze --report coverage/lcov.info --format lcov
```

Script returns structured JSON with overall_coverage, by_file, and low_coverage_files.

### Step 3: Return Coverage Results

```json
{
  "overall_coverage": {
    "line_coverage": 87.3,
    "branch_coverage": 82.1
  },
  "low_coverage_files": [...],
  "summary": {...}
}
```

## RELATED

- Skill: `pm-dev-frontend:cui-javascript-unit-testing` - Analyze Coverage workflow
- Skill: `pm-dev-frontend:cui-javascript-project` - Parse npm Build Output workflow
- Command: `/js-implement-tests` - Add tests for low-coverage areas
