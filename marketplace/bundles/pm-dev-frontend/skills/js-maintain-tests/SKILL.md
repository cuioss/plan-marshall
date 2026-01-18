---
name: js-maintain-tests
description: Execute systematic JavaScript test quality improvement with NO production code changes
user-invocable: true
allowed-tools: Skill, Read, Write, Edit, Glob, Grep, Bash, Task, SlashCommand
---

# JavaScript Test Maintain Skill

Orchestrates systematic JavaScript test quality improvement workflow while ensuring NO production code changes except confirmed bugs (with user approval).

## CONTINUOUS IMPROVEMENT RULE

If you discover issues or improvements during execution, record them:

1. **Activate skill**: `Skill: plan-marshall:manage-lessons`
2. **Record lesson** with:
   - Component: `{type: "command", name: "js-maintain-tests", bundle: "pm-dev-frontend"}`
   - Category: bug | improvement | pattern | anti-pattern
   - Summary and detail of the finding

## PARAMETERS

- **workspace** - Workspace name for single workspace test maintenance (optional, processes all if not specified)
- **priority** - Priority filter: `high`, `medium`, `low`, `all` (default: `all`)

## WORKFLOW

### Step 0: Parameter Validation

**Validate parameters:**
- If `workspace` specified: verify workspace exists
- Validate `priority` is one of: high, medium, low, all
- Set defaults if not provided

### Step 1: Load Maintenance Standards

```
Skill: cui-javascript-maintenance
```

This loads comprehensive maintenance standards including:
- Test quality standards
- Test improvement prioritization framework
- Test compliance verification

**On load failure:**
- Report error
- Cannot proceed without standards
- Abort command

### Step 2: Pre-Maintenance Verification

Execute pre-maintenance checklist to establish baseline:

**2.1 Test Execution:**
```
Task:
  subagent_type: npm-builder
  description: Execute test suite
  prompt: |
    Execute test suite to verify baseline.

    Parameters:
    - command: run test
    - workspace: {workspace if specified, otherwise all}
    - outputMode: DEFAULT

    All tests must pass before test maintenance begins.
```

**On test failure:**
- Display test failures
- Prompt user: "[F]ix manually and retry / [A]bort"
- Track in `pre_verification_failures` counter
- Cannot proceed until tests pass

**2.2 Coverage Baseline:**
```
SlashCommand: /pm-dev-frontend:js-generate-coverage
Parameters: workspace={workspace if specified}
```

Store baseline coverage metrics for comparison after improvement.

**2.3 Test File Identification:**

If `workspace` parameter not specified:
- Use Glob to identify all JavaScript test files
- Determine processing order
- Display test file list to user

If `workspace` parameter specified:
- Verify workspace exists
- Process test files in single workspace only

### Step 3: Test Quality Audit

Analyze test files using cui-javascript-maintenance test-quality-standards.md:

```
Task:
  subagent_type: Explore
  model: sonnet
  description: Identify test quality issues
  prompt: |
    Analyze test files using cui-javascript-maintenance test-quality-standards.md.
    Workspace: {workspace or 'all workspaces'}
    Return structured findings: issue type, location, description, priority (HIGH/MEDIUM/LOW)
```

Store findings for prioritization. On analysis failure, prompt user: "[R]etry / [A]bort"

### Step 4: Prioritize Test Improvements

Apply test prioritization framework from maintenance-prioritization.md:

1. **Categorize findings** by type:
   - HIGH: Business logic tests missing/inadequate
   - MEDIUM: Utility function tests, anti-patterns
   - LOW: Configuration tests, minor improvements

2. **Assign priorities** using framework:
   - HIGH: Critical functionality without tests, security-sensitive code
   - MEDIUM: Test anti-patterns, mock issues, moderate coverage gaps
   - LOW: Minor test improvements, style consistency

3. **Filter by priority parameter** if specified:
   - If priority=high: only HIGH priority items
   - If priority=medium: HIGH and MEDIUM items
   - If priority=low: Only LOW items
   - If priority=all: all items

4. **Sort within each priority** by impact

5. **Display prioritized list** to user:
   ```
   Prioritized Test Quality Issues Found:

   HIGH Priority (X items):
   - [Type] Location: Description

   MEDIUM Priority (Y items):
   - [Type] Location: Description

   LOW Priority (Z items):
   - [Type] Location: Description

   Processing order: HIGH → MEDIUM → LOW
   ```

6. **Prompt user for confirmation**:
   - "[P]roceed with test improvement / [M]odify priorities / [A]bort"

### Step 5: Execute Test Improvements

Process test improvements systematically file-by-file or workspace-by-workspace:

**For each workspace/batch of test files in processing order:**

**5.1 Workspace/Test File Focus:**
```
Current Workspace: {workspace-name or 'batch N'}
Test improvements: {count} ({HIGH/MEDIUM/LOW distribution})
```

**5.2 Implement Test Improvements:**

For each test improvement in priority order (HIGH → MEDIUM → LOW):

```
SlashCommand: /pm-dev-frontend:js-implement-tests task="Improve test quality using cui-javascript-maintenance test-quality-standards.md:

Issue: {issue description}
Location: {test file}:{line}
Type: {issue type}
Priority: {priority}

Apply appropriate improvements:
- If complex setup: extract to helper functions or beforeEach
- If hardcoded data: create test factories or fixtures
- If missing async: add async/await handling
- If no cleanup: add afterEach cleanup
- If shared state: ensure test independence
- If framework violations: use proper patterns (AAA, describe blocks)
- If mock issues: implement proper mock management
- If coverage gaps: add tests for business logic
- If E2E issues: apply Cypress best practices

**CRITICAL: Make NO production code changes.**
**If you discover production bugs, STOP and ask user for approval.**" files="{test file}"
```

Track in `improvements_applied` counter.

**On implementation error:**
- Log error details
- Track in `improvements_failed` counter
- Prompt user: "[S]kip this improvement / [R]etry / [A]bort workspace"

**On production bug discovery:**
- **STOP immediately**
- Document bug details (location, issue, impact)
- Ask user: "[F]ix production bug / [S]kip and continue test-only work / [A]bort"
- If approved to fix:
  - Track in `production_bugs_fixed` counter
  - Fix bug and create separate commit
- If not approved:
  - Document bug for later
  - Continue with test-only improvements

**5.3 Workspace/Batch Verification:**

After all improvements for workspace/batch:

```
Task:
  subagent_type: npm-builder
  description: Verify test improvements
  prompt: |
    Execute tests for workspace.

    Parameters:
    - command: run test
    - workspace: {workspace-name}
    - outputMode: DEFAULT

    All tests must pass.
```

**On verification failure:**
- Increment `workspace_verification_failures` counter
- Attempt to rollback workspace changes
- Prompt user: "[R]etry / [S]kip workspace / [A]bort"

**5.4 Workspace Coverage Check:**

```
SlashCommand: /pm-dev-frontend:js-generate-coverage
Parameters: workspace={workspace-name}
```

**Compare to baseline:**
- If coverage decreased: ERROR - test work should not decrease coverage
- If coverage same: WARN - expected improvement
- If coverage increased: OK

**5.5 Workspace Commit:**

Commit workspace changes:
```
Bash: git add {workspace test files}
Bash: git commit -m "test: {workspace-name} - improve test quality and coverage"
```

If production bugs were fixed, create separate commit:
```
Bash: git add {production files}
Bash: git commit -m "fix: {workspace-name} - {bug description} (discovered during test maintenance)"
```

Track in `workspaces_completed` counter.

**Continue to next workspace/batch.**

### Step 6: Final Verification

After all workspaces/test files processed:

**6.1 Full Test Suite:**
```
Task:
  subagent_type: npm-builder
  description: Final test verification
  prompt: |
    Execute complete test suite.

    Parameters:
    - command: run test

    All tests must pass.
```

**6.2 Coverage Verification:**
```
SlashCommand: /pm-dev-frontend:js-generate-coverage
```

Compare final coverage to baseline:
- Display coverage change
- Should show improvement, not regression

**6.3 Test Quality Verification:**

Verify sample of improved test files using cui-javascript-maintenance quality checklist. Report compliance status.

### Step 7: Display Summary

```
╔════════════════════════════════════════════════════════════╗
║          Test Maintenance Summary                          ║
╚════════════════════════════════════════════════════════════╝

Workspaces Processed: {workspaces_completed} / {total_workspaces}
Test Issues Found: {total_issues}
  - HIGH Priority: {high_count}
  - MEDIUM Priority: {medium_count}
  - LOW Priority: {low_count}

Improvements Applied: {improvements_applied}
Improvements Failed: {improvements_failed}
Improvements Skipped: {improvements_skipped}

Production Bugs Discovered: {bugs_found}
Production Bugs Fixed: {production_bugs_fixed}

Coverage:
  - Baseline: {baseline_coverage}%
  - Final: {final_coverage}%
  - Change: +{coverage_delta}%

Test Status: {SUCCESS/FAILURE}
Tests: {passing_count} / {total_tests} passed

Test Quality: {compliant_categories} / {total_categories} categories compliant

Time Taken: {elapsed_time}
```

## STATISTICS TRACKING

Track throughout workflow:
- `pre_verification_failures`: Pre-maintenance verification failures
- `analysis_failures`: Test quality audit failures
- `workspaces_completed`: Workspaces successfully improved
- `workspaces_failed`: Workspaces that failed verification
- `improvements_applied`: Individual test improvements applied
- `improvements_failed`: Individual improvements that failed
- `improvements_skipped`: Improvements skipped by user
- `workspace_verification_failures`: Workspace verification failures
- `bugs_found`: Production bugs discovered during testing
- `production_bugs_fixed`: Production bugs fixed with approval
- `coverage_baseline`: Initial coverage percentage
- `coverage_final`: Final coverage percentage
- `elapsed_time`: Total execution time

Display all statistics in final summary.

## CRITICAL CONSTRAINTS

**Production Code Protection:**
- **NO PRODUCTION CHANGES** except confirmed bugs with user approval
- **Bug Discovery Process:**
  1. Stop immediately when production bug found
  2. Document bug details
  3. Ask user for approval to fix
  4. Wait for confirmation before proceeding
  5. Create separate commit for bug fix
- Focus solely on test improvement
- All existing tests must continue to pass

**Test-Only Changes:**
- Refactor test code only
- Improve test patterns
- Add missing tests
- Fix test anti-patterns
- Improve coverage

**Coverage Requirement:**
- Coverage must NOT decrease
- Expected to increase with improvements
- If coverage decreases, investigate immediately

**Safety Protocols:**
- Incremental changes (workspace-by-workspace or file-by-file)
- Continuous verification after each workspace
- Ability to rollback at workspace level
- User confirmation before production changes

## TEST IMPROVEMENT CATEGORIES

Test priorities are applied in Step 4 using cui-javascript-maintenance prioritization framework:
- **HIGH**: Business logic, critical functionality (90%+ coverage target)
- **MEDIUM**: Utilities, helpers, custom hooks (80%+ coverage target)
- **LOW**: Configuration, simple utilities (60%+ coverage acceptable)

## ERROR HANDLING

**Test Failures**: Display details, do not proceed, rollback if introduced
**Implementation Errors**: Log failure, skip on user request, continue with others
**Coverage Regression**: Error if decreased, investigate, rollback changes
**Production Bug Discovery**: Stop, document, get user approval, separate commit if fixed

**Rollback**: Workspace-level (`git reset HEAD~1`) or complete (`git reset --hard {initial_commit}`)

## USAGE EXAMPLES

**Full test maintenance (all workspaces, all priorities):**
```
/js-maintain-tests
```

**Single workspace test maintenance:**
```
/js-maintain-tests workspace=frontend
```

**Only high priority test improvements:**
```
/js-maintain-tests priority=high
```

**Medium and high priority improvements:**
```
/js-maintain-tests priority=medium
```

**Specific workspace, high priority only:**
```
/js-maintain-tests workspace=core priority=high
```

## ARCHITECTURE

Orchestrates agents and commands:
- **cui-javascript-maintenance skill** - Test quality standards and prioritization
- **Explore agent** - Test quality analysis
- **`/js-implement-tests` command** - Self-contained test improvements (Layer 2)
- **npm-builder agent** - Test execution and verification (Layer 3)
- **`/javascript-coverage-report` command** - Coverage analysis

## RELATED

- `cui-javascript-maintenance` skill - Test quality standards this command implements
- `/js-implement-tests` command - Test implementation and improvement (Layer 2)
- `npm-builder` agent - Test execution and verification
- `/javascript-coverage-report` command - Coverage analysis
- `cui-javascript-unit-testing` skill - Jest testing patterns
- `cui-cypress` skill - E2E testing patterns
- `cui-task-planning` skill - For test improvement planning
