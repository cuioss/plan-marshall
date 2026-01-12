---
name: js-refactor-code
description: Execute systematic JavaScript refactoring with standards compliance verification
allowed-tools: Skill, Read, Write, Edit, Glob, Grep, Bash, Task, SlashCommand
---

# CUI JavaScript Refactor Command

Orchestrates systematic JavaScript code refactoring and maintenance workflow with comprehensive standards compliance verification.

## CONTINUOUS IMPROVEMENT RULE

If you discover issues or improvements during execution, record them:

1. **Activate skill**: `Skill: plan-marshall:lessons-learned`
2. **Record lesson** with:
   - Component: `{type: "command", name: "js-refactor-code", bundle: "pm-dev-frontend"}`
   - Category: bug | improvement | pattern | anti-pattern
   - Summary and detail of the finding

## PARAMETERS

- **workspace** - Workspace name for single workspace refactoring (optional, processes all if not specified)
- **scope** - Refactoring scope: `full` (default), `standards`, `unused`, `modernize`, `documentation`
- **priority** - Priority filter: `high`, `medium`, `low`, `all` (default: `all`)

## CRITICAL CONSTRAINTS

**Functionality Preservation:**
- **NO BEHAVIOR CHANGES** unless fixing confirmed bugs
- All existing tests must continue to pass
- API compatibility maintained for public APIs
- Browser compatibility maintained

**Safety Protocols:**
- Incremental changes (workspace-by-workspace or file-by-file)
- Continuous verification after each workspace/batch
- Ability to rollback at workspace level
- User confirmation before major changes

**File-by-File/Workspace Strategy:**
- Process one workspace/batch completely before next
- Verify and commit each workspace independently
- Maintain build stability after each workspace
- Process in dependency order if applicable

## WORKFLOW

### Step 0: Parameter Validation

- If `workspace` specified: verify workspace exists
- Validate `scope` and `priority` parameters
- Set defaults if not provided

### Step 1: Load Maintenance Standards

```
Skill: cui-javascript-maintenance
```

This loads comprehensive maintenance standards including:
- Refactoring trigger criteria (detection)
- Prioritization framework (HIGH/MEDIUM/LOW)
- Compliance verification checklist
- Test quality standards
- Scope definitions (full, standards, unused, modernize, documentation)
- Priority filter behavior

**On load failure:** Report error and abort command.

### Step 2: Pre-Maintenance Verification

**2.1 Build Verification:**

```
Task:
  subagent_type: npm-builder
  description: Verify build before refactoring
  prompt: |
    Execute npm build to verify build health.
    Workspace: {workspace if specified, otherwise all}
    Build must pass before proceeding.
```

**On build failure:** Display errors, prompt "[F]ix / [A]bort", track in `pre_verification_failures`.

**2.2 Test Execution:**

```
Task:
  subagent_type: npm-builder
  description: Execute test suite
  prompt: |
    Execute complete test suite.
    Workspace: {workspace if specified, otherwise all}
    All tests must pass.
```

**On test failure:** Display failures, prompt "[F]ix / [A]bort", track in `pre_verification_failures`.

**2.3 Coverage Baseline:**

```
SlashCommand: /pm-dev-frontend:js-generate-coverage
Parameters: workspace={workspace if specified}
```

Store baseline coverage metrics for post-refactor comparison.

**2.4 Workspace/File Identification:**

If `workspace` not specified:
- Use Glob to identify all JavaScript files/workspaces
- Determine processing order (dependencies first)
- Display list and order to user

### Step 3: Standards Compliance Audit

Analyze codebase for violations using Explore agent:

```
Task:
  subagent_type: Explore
  model: sonnet
  description: Identify standards violations
  prompt: |
    Analyze codebase using cui-javascript-maintenance trigger criteria.

    Workspace: {workspace or 'all workspaces'}
    Scope: {scope parameter}

    Apply detection criteria from refactoring-triggers.md:
    - Vanilla JavaScript enforcement opportunities
    - Test/mock code in production files
    - Modularization issues
    - Package.json problems
    - JSDoc gaps (if scope=documentation or full)
    - Legacy patterns (if scope=modernize or full)
    - Unused code (if scope=unused or full)

    Return structured findings with violation type, location, description, suggested priority.
```

**Store findings** for prioritization.

**On analysis failure:** Track in `analysis_failures`, prompt "[R]etry / [A]bort".

### Step 4: Prioritize Violations

Apply prioritization framework from cui-javascript-maintenance skill:

1. **Categorize findings** by type (library issues, organization, vanilla JS, package mgmt, quality, docs)
2. **Assign priorities** using framework (HIGH: critical/security, MEDIUM: maintainability, LOW: style)
3. **Filter by priority parameter** as defined in skill
4. **Sort within priorities** by impact and dependencies
5. **Display prioritized list** to user
6. **Prompt confirmation:** "[P]roceed / [M]odify / [A]bort"

### Step 5: Execute Refactoring

Process violations systematically workspace-by-workspace:

**For each workspace/batch in processing order:**

**5.1 Workspace Focus:**

Display workspace name and violation count/distribution.

**5.2 Implement Fixes:**

For each violation in priority order (HIGH → MEDIUM → LOW):

```
SlashCommand: /pm-dev-frontend:js-implement-code task="Fix violation using cui-javascript standards.

Violation: {description}
Location: {file}:{line}
Type: {type}
Priority: {priority}

Apply appropriate fix pattern from cui-javascript skill.
Verify build after changes." files="{file}"
```

Track in `fixes_applied`.

**On implementation error:** Log details, track in `fixes_failed`, prompt "[S]kip / [R]etry / [A]bort".

**5.3 Workspace Verification:**

```
Task:
  subagent_type: npm-builder
  description: Verify workspace changes
  prompt: |
    Execute build and tests for workspace {workspace-name}.
    All must pass.
```

**On verification failure:** Track in `workspace_verification_failures`, attempt rollback, prompt "[R]etry / [S]kip / [A]bort".

**5.4 Workspace Coverage Check:**

```
SlashCommand: /pm-dev-frontend:js-generate-coverage
Parameters: workspace={workspace-name}
```

Compare to baseline. If coverage decreased, warn user and ask if acceptable.

**5.5 Workspace Commit:**

```
Bash: git add {workspace files}
Bash: git commit -m "$(cat <<'EOF'
refactor(js): {workspace-name} - standards compliance improvements

Violations fixed:
- HIGH: {count}
- MEDIUM: {count}
- LOW: {count}

Coverage: {baseline}% → {final}%

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

Track in `workspaces_completed`. Continue to next workspace.

### Step 6: Final Verification

**6.1 Complete Build:**

```
Task:
  subagent_type: npm-builder
  description: Final build verification
  prompt: |
    Execute complete build to verify all changes.
    Full build must pass.
```

**6.2 Full Test Suite:**

```
Task:
  subagent_type: npm-builder
  description: Final test verification
  prompt: |
    Execute complete test suite.
    All tests must pass.
```

**6.3 Lint Verification:**

```
Task:
  subagent_type: npm-builder
  description: Lint verification
  prompt: |
    Execute lint checks.
    All must pass.
```

**6.4 Coverage Verification:**

```
SlashCommand: /pm-dev-frontend:js-generate-coverage
```

Display coverage change from baseline and ensure no significant regression.

**6.5 Standards Compliance Verification:**

Apply compliance checklist from cui-javascript-maintenance skill for sample of refactored files. Report compliance status.

### Step 7: Display Summary

```
╔════════════════════════════════════════════════════════════╗
║          Refactoring Summary                               ║
╚════════════════════════════════════════════════════════════╝

Scope: {scope}
Priority Filter: {priority}

Workspaces Processed: {workspaces_completed} / {total_workspaces}
Violations Found: {total_violations}
  - HIGH Priority: {high_count}
  - MEDIUM Priority: {medium_count}
  - LOW Priority: {low_count}

Fixes Applied: {fixes_applied}
Fixes Failed: {fixes_failed}
Fixes Skipped: {fixes_skipped}

Coverage:
  - Baseline: {baseline_coverage}%
  - Final: {final_coverage}%
  - Change: {coverage_delta}%

Build Status: {SUCCESS/FAILURE}
Tests: {passing_count} / {total_tests} passed
Lint: {SUCCESS/FAILURE}

Compliance: {compliant_categories} / {total_categories} categories compliant

Time Taken: {elapsed_time}
```

## STATISTICS TRACKING

Track throughout workflow:
- `pre_verification_failures` - Pre-maintenance verification failures
- `analysis_failures` - Standards audit failures
- `workspaces_completed` / `workspaces_failed` - Workspace processing
- `fixes_applied` / `fixes_failed` / `fixes_skipped` - Individual fixes
- `workspace_verification_failures` - Workspace verification failures
- `coverage_baseline` / `coverage_final` - Coverage metrics
- `elapsed_time` - Total execution time

Display all statistics in final summary.

## ROLLBACK STRATEGY

**Workspace-level rollback:**
```
Bash: git reset HEAD~1  # Rollback workspace commit
Bash: git checkout -- {workspace}  # Restore workspace files
```

**Complete rollback:**
```
Bash: git reset --hard {initial_commit}  # Restore to pre-refactor state
```

## USAGE EXAMPLES

```
# Full refactoring (all workspaces, all priorities)
/js-refactor-code

# Single workspace refactoring
/js-refactor-code workspace=frontend

# Only high priority violations
/js-refactor-code priority=high

# Modernize code only
/js-refactor-code scope=modernize

# Remove unused code
/js-refactor-code scope=unused priority=medium

# Documentation improvements only
/js-refactor-code scope=documentation workspace=core

# Combination
/js-refactor-code workspace=ui scope=standards priority=high
```

## ARCHITECTURE

Orchestrates agents and commands:
- **cui-javascript-maintenance skill** - Standards for detection, prioritization, verification
- **Explore agent** - Codebase analysis for violation detection
- **`/js-implement-code` command** - Self-contained code fixes (Layer 2)
- **npm-builder agent** - Build and verification
- **`/javascript-coverage-report` command** - Coverage analysis

## RELATED

- `cui-javascript-maintenance` skill - Standards this command implements
- `/js-implement-code` command - Implementation fixes (Layer 2)
- `npm-builder` agent - Build verification
- `/javascript-coverage-report` command - Coverage analysis
- `cui-javascript` skill - Implementation patterns
- `cui-task-planning` skill - For refactoring task planning
