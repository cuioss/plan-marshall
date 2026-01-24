# Script Verification Standard

Verification requirements for deliverables that include Python scripts. Load this standard only when at least one script is part of the process.

## When to Load

Load this standard when ANY deliverable:
- Creates a new Python script
- Modifies an existing Python script
- Renames or moves a script
- Changes script behavior or output contract

## Verification Requirements

### 1. Tests Must Be Created or Updated

For each script affected by a deliverable:

| Script Action | Test Requirement |
|---------------|------------------|
| New script | Create corresponding test file |
| Modified script | Update existing tests for changed behavior |
| Renamed script | Rename test file/directory to match |
| Deleted script | Remove corresponding tests |

**Test file naming convention**:
```
Script: marketplace/bundles/{bundle}/skills/{skill}/scripts/{script}.py
Tests:  test/{bundle}/{skill}/test_{script}.py
```

### 2. Affected Tests Must Be Run

After implementing script changes, run the affected tests:

```bash
# Run tests for specific bundle
./pw module-tests {bundle}

# Run specific test via pytest -k filter
./pw module-tests {bundle} -- -k test_{script}

# Run all tests (if changes are cross-cutting)
./pw module-tests
```

**Deliverable verification must include**:
```markdown
**Script Verification:**
- Tests: `test/{bundle}/{skill}/test_{script}.py`
- Run: `./pw module-tests {bundle}`
- Expected: All tests pass
```

### 3. Test Organization Validation

When component names change, test directories must be updated to maintain the mirror structure.

**Directory structure rule**:
```
marketplace/bundles/{bundle}/skills/{skill}/scripts/
    └── {script}.py

test/{bundle}/{skill}/
    └── test_{script}.py
```

**Validation checklist**:
- [ ] Test directory path matches `test/{bundle}/{skill}/`
- [ ] Test file name matches `test_{script}.py`
- [ ] No orphaned test files for deleted scripts
- [ ] No missing test files for new scripts

### Organization Changes

| Component Change | Required Test Change |
|------------------|----------------------|
| Skill renamed | Rename test directory |
| Script renamed | Rename test file |
| Skill moved to different bundle | Move test directory to new bundle path |
| Script moved to different skill | Move test file to new skill directory |

## Deliverable Template Addition

When a deliverable includes scripts, add this section to the deliverable:

```markdown
**Script Verification:**
- Tests: Create/update `test/{bundle}/{skill}/test_{script}.py`
- Run: `./pw module-tests {bundle}`
- Organization: Verify test path matches `test/{bundle}/{skill}/`
- Expected: All tests pass, no orphaned tests
```

## Integration with plugin-script-architecture

For script implementation details, testing patterns, and output contracts:

```
Skill: pm-plugin-development:plugin-script-architecture
```

This provides:
- Python implementation patterns
- Test structure standards
- Output contract definitions
- Argument parsing patterns

## Example: New Script Deliverable

```markdown
### 3. Create validation script

**Metadata:**
- change_type: create
- execution_mode: automated
- domain: plan-marshall-plugin-dev
- module: pm-workflow
- depends: 1

**Profiles:**
- implementation

**Affected files:**
- `marketplace/bundles/pm-workflow/skills/manage-tasks/scripts/validate-task.py`

**Change per file:** Create new validation script for task file format

**Verification:**
- Command: `/pm-plugin-development:plugin-doctor --component marketplace/bundles/pm-workflow/skills/manage-tasks`
- Criteria: No quality issues detected

**Script Verification:**
- Tests: Create `test/pm-workflow/manage-tasks/test_validate_task.py`
- Run: `./pw module-tests pm-workflow`
- Organization: Verify test path matches component structure
- Expected: All tests pass

**Success Criteria:**
- Script validates task TOON format
- Returns structured JSON output
- Tests cover success and error cases
```

## Example: Renamed Script Deliverable

```markdown
### 2. Rename goal script to deliverable script

**Metadata:**
- change_type: refactor
- execution_mode: automated
- domain: plan-marshall-plugin-dev
- module: pm-workflow
- depends: none

**Profiles:**
- implementation

**Affected files:**
- `marketplace/bundles/pm-workflow/skills/manage-goals/scripts/manage-goal.py` → `manage-deliverable.py`

**Change per file:** Rename script file and update internal references

**Verification:**
- Command: `/pm-plugin-development:plugin-doctor --component marketplace/bundles/pm-workflow/skills/manage-goals`
- Criteria: No quality issues detected

**Script Verification:**
- Tests: Rename `test/pm-workflow/manage-goals/test_manage_goal.py` → `test_manage_deliverable.py`
- Run: `./pw module-tests pm-workflow`
- Organization: Remove old test file, verify new test file path
- Expected: All tests pass, no orphaned `test_manage_goal.py`

**Success Criteria:**
- Script renamed consistently
- All references updated
- Tests renamed and passing
```
