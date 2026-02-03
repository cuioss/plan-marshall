#!/usr/bin/env python3
"""
Tests for manage-solution-outline script.

Solution outlines are written directly by agents, then validated via this script.
"""

import sys
from pathlib import Path

# Import shared infrastructure
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from conftest import PlanContext, get_script_path, run_script

# Get script path
SCRIPT_PATH = get_script_path('pm-workflow', 'manage-solution-outline', 'manage-solution-outline.py')

# Import toon_parser - conftest sets up PYTHONPATH
from toon_parser import parse_toon  # type: ignore[import-not-found]  # noqa: E402

# Alias for backward compatibility
TestContext = PlanContext


# Sample valid solution outline with ASCII diagram (contract-compliant)
VALID_SOLUTION = """# Solution: JWT Validation Service

plan_id: test-plan
created: 2025-01-01T00:00:00Z
compatibility: breaking — Clean-slate approach, no deprecation nor transitionary comments

## Summary

Implement JWT validation service for authentication.

## Overview

```
┌─────────────────────┐
│  JwtConfiguration   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ JwtValidationService│
└─────────────────────┘
```

## Deliverables

### 1. Create JwtValidationService class

Implement the main validation logic.

**Metadata:**
- change_type: feature
- execution_mode: automated
- domain: java
- module: jwt-service
- depends: none

**Profiles:**
- implementation
- module_testing

**Affected files:**
- `src/main/java/de/cuioss/jwt/JwtValidationService.java`

**Verification:**
- Command: `mvn test -Dtest=JwtValidationServiceTest`
- Criteria: All tests pass

**Success Criteria:**
- Service validates JWT tokens correctly

### 2. Add configuration properties

Add JWT configuration to application.properties.

**Metadata:**
- change_type: feature
- execution_mode: automated
- domain: java
- module: jwt-service
- depends: 1

**Profiles:**
- implementation

**Affected files:**
- `src/main/resources/application.properties`

**Verification:**
- Command: `mvn verify`
- Criteria: Application starts successfully

**Success Criteria:**
- JWT properties are configurable

### 3. Implement unit tests

Create comprehensive test coverage.

**Metadata:**
- change_type: feature
- execution_mode: automated
- domain: java
- module: jwt-service
- depends: 1

**Profiles:**
- module_testing

**Affected files:**
- `src/test/java/de/cuioss/jwt/JwtValidationServiceTest.java`

**Verification:**
- Command: `mvn test`
- Criteria: All tests pass with >80% coverage

**Success Criteria:**
- Test coverage above 80%

## Approach

Use standard JWT libraries with Quarkus integration.

## Dependencies

- jose4j library
- Quarkus security extensions

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Key rotation | Implement key cache refresh |
"""


# =============================================================================
# Test: Validate Command
# =============================================================================


def test_validate_success():
    """Test validating a well-formed solution document."""
    with TestContext(plan_id='solution-valid') as ctx:
        (ctx.plan_dir / 'solution_outline.md').write_text(VALID_SOLUTION)

        result = run_script(SCRIPT_PATH, 'validate', '--plan-id', 'solution-valid')
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert 'validation' in data
        assert data['validation']['deliverable_count'] == 3
        assert '1. Create JwtValidationService class' in data['validation']['deliverables']


def test_validate_extracts_compatibility():
    """Test that validate extracts compatibility from header metadata."""
    with TestContext(plan_id='solution-compat') as ctx:
        (ctx.plan_dir / 'solution_outline.md').write_text(VALID_SOLUTION)

        result = run_script(SCRIPT_PATH, 'validate', '--plan-id', 'solution-compat')
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert 'compatibility' in data['validation']
        compat = data['validation']['compatibility']
        assert 'breaking' in compat


def test_validate_without_compatibility():
    """Test that validate succeeds when compatibility header is absent."""
    solution_no_compat = VALID_SOLUTION.replace(
        'compatibility: breaking \u2014 Clean-slate approach, no deprecation nor transitionary comments\n', ''
    )
    with TestContext(plan_id='solution-no-compat') as ctx:
        (ctx.plan_dir / 'solution_outline.md').write_text(solution_no_compat)

        result = run_script(SCRIPT_PATH, 'validate', '--plan-id', 'solution-no-compat')
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        # compatibility should not be present when header lacks it
        assert 'compatibility' not in data.get('validation', {})


def test_validate_missing_overview():
    """Test validation fails when Overview section is missing."""
    with TestContext(plan_id='solution-missing-overview') as ctx:
        (ctx.plan_dir / 'solution_outline.md').write_text("""# Solution: Test

## Summary

Brief summary

## Deliverables

### 1. First deliverable

Description
""")

        result = run_script(SCRIPT_PATH, 'validate', '--plan-id', 'solution-missing-overview')
        assert not result.success, 'Expected failure for missing Overview'
        data = parse_toon(result.stdout)
        assert data['status'] == 'error'
        assert data['error'] == 'validation_failed'
        assert any('Overview' in issue for issue in data['issues'])


def test_validate_no_deliverables():
    """Test validation fails when no numbered deliverables found."""
    with TestContext(plan_id='solution-no-deliverables') as ctx:
        (ctx.plan_dir / 'solution_outline.md').write_text("""# Solution: Test

## Summary

Brief summary

## Overview

Architecture diagram here

## Deliverables

Some text but no ### N. Title items
""")

        result = run_script(SCRIPT_PATH, 'validate', '--plan-id', 'solution-no-deliverables')
        assert not result.success, 'Expected failure for no numbered deliverables'
        data = parse_toon(result.stdout)
        assert data['status'] == 'error'
        assert any('numbered deliverables' in issue for issue in data['issues'])


def test_validate_document_not_found():
    """Test validation fails when document doesn't exist."""
    with TestContext(plan_id='no-solution'):
        result = run_script(SCRIPT_PATH, 'validate', '--plan-id', 'no-solution')
        assert not result.success, 'Expected failure for missing document'
        data = parse_toon(result.stdout)
        assert data['error'] == 'document_not_found'


# =============================================================================
# Test: List Deliverables Command
# =============================================================================


def test_list_deliverables():
    """Test listing deliverables from solution document."""
    with TestContext(plan_id='solution-list') as ctx:
        (ctx.plan_dir / 'solution_outline.md').write_text(VALID_SOLUTION)

        result = run_script(SCRIPT_PATH, 'list-deliverables', '--plan-id', 'solution-list')
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['deliverable_count'] == 3
        assert len(data['deliverables']) == 3
        # Check structure of deliverables
        first = data['deliverables'][0]
        assert first['number'] == 1
        assert first['title'] == 'Create JwtValidationService class'
        assert first['reference'] == '1. Create JwtValidationService class'


def test_list_deliverables_empty():
    """Test list-deliverables with no deliverables section."""
    with TestContext(plan_id='solution-empty') as ctx:
        (ctx.plan_dir / 'solution_outline.md').write_text("""# Solution: Test

## Summary

Just summary, no deliverables section
""")

        result = run_script(SCRIPT_PATH, 'list-deliverables', '--plan-id', 'solution-empty')
        assert not result.success, 'Expected failure for missing Deliverables section'
        data = parse_toon(result.stdout)
        assert data['error'] == 'section_not_found'


# =============================================================================
# Test: Read Command
# =============================================================================


def test_read():
    """Test reading a solution document."""
    with TestContext(plan_id='solution-read') as ctx:
        (ctx.plan_dir / 'solution_outline.md').write_text(VALID_SOLUTION)

        result = run_script(SCRIPT_PATH, 'read', '--plan-id', 'solution-read')
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        # Content is a nested object - verify it exists and has expected sections
        assert 'content:' in result.stdout
        assert 'summary:' in result.stdout
        assert 'overview:' in result.stdout
        assert 'deliverables:' in result.stdout


def test_read_raw():
    """Test reading a solution document in raw mode."""
    with TestContext(plan_id='solution-raw') as ctx:
        (ctx.plan_dir / 'solution_outline.md').write_text(VALID_SOLUTION)

        result = run_script(SCRIPT_PATH, 'read', '--plan-id', 'solution-raw', '--raw')
        assert result.success, f'Script failed: {result.stderr}'
        # Raw mode outputs the actual markdown
        assert '# Solution: JWT Validation Service' in result.stdout
        assert '## Overview' in result.stdout
        assert '## Deliverables' in result.stdout
        assert '### 1. Create JwtValidationService class' in result.stdout


def test_read_not_found():
    """Test read fails when document doesn't exist."""
    with TestContext(plan_id='no-solution'):
        result = run_script(SCRIPT_PATH, 'read', '--plan-id', 'no-solution')
        assert not result.success, 'Expected failure for missing document'
        data = parse_toon(result.stdout)
        assert data['error'] == 'document_not_found'


def test_read_deliverable_by_number():
    """Test reading a specific deliverable by number."""
    with TestContext(plan_id='deliverable-num') as ctx:
        # Write valid solution with multiple deliverables
        (ctx.plan_dir / 'solution_outline.md').write_text(VALID_SOLUTION)

        # Read deliverable 1
        result = run_script(
            SCRIPT_PATH,
            'read',
            '--plan-id',
            'deliverable-num',
            '--deliverable-number',
            '1',
        )
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['deliverable']['number'] == 1
        assert 'JwtValidationService' in data['deliverable']['title']


def test_read_deliverable_by_number_second():
    """Test reading the second deliverable by number."""
    with TestContext(plan_id='deliverable-num-2') as ctx:
        (ctx.plan_dir / 'solution_outline.md').write_text(VALID_SOLUTION)

        # Read deliverable 2
        result = run_script(
            SCRIPT_PATH,
            'read',
            '--plan-id',
            'deliverable-num-2',
            '--deliverable-number',
            '2',
        )
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['deliverable']['number'] == 2
        assert 'configuration properties' in data['deliverable']['title']


def test_read_deliverable_not_found():
    """Test reading non-existent deliverable number."""
    with TestContext(plan_id='deliverable-notfound') as ctx:
        (ctx.plan_dir / 'solution_outline.md').write_text(VALID_SOLUTION)

        result = run_script(
            SCRIPT_PATH,
            'read',
            '--plan-id',
            'deliverable-notfound',
            '--deliverable-number',
            '999',
        )
        assert not result.success
        data = parse_toon(result.stdout)
        assert data['error'] == 'deliverable_not_found'
        assert 'available' in data  # Should list available deliverable numbers


# =============================================================================
# Test: Exists Command
# =============================================================================


def test_exists_present():
    """Test exists returns true when document exists."""
    with TestContext(plan_id='solution-exists') as ctx:
        (ctx.plan_dir / 'solution_outline.md').write_text(VALID_SOLUTION)

        result = run_script(SCRIPT_PATH, 'exists', '--plan-id', 'solution-exists')
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['exists'] is True


def test_exists_absent():
    """Test exists returns false when document doesn't exist."""
    with TestContext(plan_id='no-solution'):
        result = run_script(SCRIPT_PATH, 'exists', '--plan-id', 'no-solution')
        # Script returns exit code 1 when document doesn't exist
        assert not result.success
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['exists'] is False


# =============================================================================
# Test: Write Command
# =============================================================================


def test_write_new():
    """Test writing a new solution outline via stdin (validates automatically)."""
    with TestContext(plan_id='solution-write') as ctx:
        result = run_script(SCRIPT_PATH, 'write', '--plan-id', 'solution-write', input_data=VALID_SOLUTION)
        assert result.success, f'Script failed: {result.stderr}\nOutput: {result.stdout}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['file'] == 'solution_outline.md'
        assert 'validation' in data
        assert data['validation']['deliverable_count'] == 3
        # Verify file was created
        assert (ctx.plan_dir / 'solution_outline.md').exists()
        content = (ctx.plan_dir / 'solution_outline.md').read_text()
        assert '# Solution: JWT Validation Service' in content


def test_write_includes_compatibility():
    """Test that write output includes compatibility when present in header."""
    with TestContext(plan_id='solution-write-compat'):
        result = run_script(
            SCRIPT_PATH, 'write', '--plan-id', 'solution-write-compat', input_data=VALID_SOLUTION
        )
        assert result.success, f'Script failed: {result.stderr}\nOutput: {result.stdout}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert 'compatibility' in data['validation']
        assert 'breaking' in data['validation']['compatibility']


def test_write_exists_without_force():
    """Test that write fails if document exists and --force not specified."""
    with TestContext(plan_id='solution-exists') as ctx:
        # Create existing file with valid content
        (ctx.plan_dir / 'solution_outline.md').write_text(VALID_SOLUTION)

        result = run_script(SCRIPT_PATH, 'write', '--plan-id', 'solution-exists', input_data=VALID_SOLUTION)
        assert not result.success, 'Expected failure when file exists without --force'
        data = parse_toon(result.stdout)
        assert data['error'] == 'file_exists'


def test_write_with_force():
    """Test that write succeeds with --force when document exists."""
    with TestContext(plan_id='solution-force') as ctx:
        # Create existing file with old content
        (ctx.plan_dir / 'solution_outline.md').write_text('# Old content')

        result = run_script(SCRIPT_PATH, 'write', '--plan-id', 'solution-force', '--force', input_data=VALID_SOLUTION)
        assert result.success, f'Script failed: {result.stderr}\nOutput: {result.stdout}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        # Verify content was overwritten
        content = (ctx.plan_dir / 'solution_outline.md').read_text()
        assert '# Solution: JWT Validation Service' in content
        assert '# Old content' not in content


# =============================================================================
# Test: Invalid Plan IDs
# =============================================================================


def test_invalid_plan_id_uppercase():
    """Test that uppercase plan IDs are rejected."""
    with TestContext():
        result = run_script(SCRIPT_PATH, 'validate', '--plan-id', 'My-Plan')
        assert not result.success, 'Expected rejection of uppercase plan ID'
        data = parse_toon(result.stdout)
        assert data['error'] == 'invalid_plan_id'


def test_invalid_plan_id_underscore():
    """Test that underscores in plan IDs are rejected."""
    with TestContext():
        result = run_script(SCRIPT_PATH, 'validate', '--plan-id', 'my_plan')
        assert not result.success, 'Expected rejection of underscore plan ID'
        data = parse_toon(result.stdout)
        assert data['error'] == 'invalid_plan_id'


if __name__ == '__main__':
    import sys

    # Run tests
    test_funcs = [name for name in dir() if name.startswith('test_')]
    passed = 0
    failed = 0

    for test_name in test_funcs:
        try:
            print(f'Running {test_name}...', end=' ')
            globals()[test_name]()
            print('PASS')
            passed += 1
        except AssertionError as e:
            print(f'FAIL: {e}')
            failed += 1
        except Exception as e:
            print(f'ERROR: {e}')
            failed += 1

    print(f'\nPassed: {passed}, Failed: {failed}')
    sys.exit(0 if failed == 0 else 1)
