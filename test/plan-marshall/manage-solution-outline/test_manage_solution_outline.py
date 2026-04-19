#!/usr/bin/env python3
"""
Tests for manage-solution-outline script.

Tier 2 (direct import) tests with 2-3 subprocess tests for CLI plumbing.
Solution outlines are written directly by agents, then validated via this script.
"""

import importlib.util
from argparse import Namespace

import pytest

from conftest import PlanContext, get_script_path, run_script

# Script path for remaining subprocess (CLI plumbing) tests
SCRIPT_PATH = get_script_path('plan-marshall', 'manage-solution-outline', 'manage-solution-outline.py')

# Tier 2 direct imports via importlib (script filename has hyphens)
_spec = importlib.util.spec_from_file_location('manage_solution_outline', str(SCRIPT_PATH))
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

cmd_validate = _mod.cmd_validate
cmd_list_deliverables = _mod.cmd_list_deliverables
cmd_read = _mod.cmd_read
cmd_exists = _mod.cmd_exists
cmd_resolve_path = _mod.cmd_resolve_path
cmd_write = _mod.cmd_write
cmd_update = _mod.cmd_update

# Import toon_parser - conftest sets up PYTHONPATH
from toon_parser import parse_toon  # type: ignore[import-not-found]  # noqa: E402

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
# Namespace Builders
# =============================================================================


def _validate_ns(plan_id='test-plan'):
    """Build Namespace for cmd_validate."""
    return Namespace(plan_id=plan_id)


def _list_deliverables_ns(plan_id='test-plan'):
    """Build Namespace for cmd_list_deliverables."""
    return Namespace(plan_id=plan_id)


def _read_ns(plan_id='test-plan', raw=False, deliverable_number=None, section=None):
    """Build Namespace for cmd_read."""
    return Namespace(plan_id=plan_id, raw=raw, deliverable_number=deliverable_number, section=section)


def _exists_ns(plan_id='test-plan'):
    """Build Namespace for cmd_exists."""
    return Namespace(plan_id=plan_id)


def _resolve_path_ns(plan_id='test-plan'):
    """Build Namespace for cmd_resolve_path."""
    return Namespace(plan_id=plan_id)


def _write_ns(plan_id='test-plan', force=False):
    """Build Namespace for cmd_write."""
    return Namespace(plan_id=plan_id, force=force)


def _update_ns(plan_id='test-plan'):
    """Build Namespace for cmd_update."""
    return Namespace(plan_id=plan_id)


# =============================================================================
# Tier 2: Validate Command
# =============================================================================


def test_validate_success():
    """Test validating a well-formed solution document."""
    with PlanContext(plan_id='solution-valid') as ctx:
        (ctx.plan_dir / 'solution_outline.md').write_text(VALID_SOLUTION)

        result = cmd_validate(_validate_ns(plan_id='solution-valid'))
        assert result['status'] == 'success'
        assert 'validation' in result
        assert result['validation']['deliverable_count'] == 3
        assert '1. Create JwtValidationService class' in result['validation']['deliverables']


def test_validate_extracts_compatibility():
    """Test that validate extracts compatibility from header metadata."""
    with PlanContext(plan_id='solution-compat') as ctx:
        (ctx.plan_dir / 'solution_outline.md').write_text(VALID_SOLUTION)

        result = cmd_validate(_validate_ns(plan_id='solution-compat'))
        assert result['status'] == 'success'
        assert 'compatibility' in result['validation']
        compat = result['validation']['compatibility']
        assert 'breaking' in compat


def test_validate_without_compatibility():
    """Test that validate succeeds when compatibility header is absent."""
    solution_no_compat = VALID_SOLUTION.replace(
        'compatibility: breaking \u2014 Clean-slate approach, no deprecation nor transitionary comments\n', ''
    )
    with PlanContext(plan_id='solution-no-compat') as ctx:
        (ctx.plan_dir / 'solution_outline.md').write_text(solution_no_compat)

        result = cmd_validate(_validate_ns(plan_id='solution-no-compat'))
        assert result['status'] == 'success'
        # compatibility should not be present when header lacks it
        assert 'compatibility' not in result.get('validation', {})


def test_validate_missing_overview():
    """Test validation fails when Overview section is missing."""
    with PlanContext(plan_id='solution-missing-overview') as ctx:
        (ctx.plan_dir / 'solution_outline.md').write_text("""# Solution: Test

## Summary

Brief summary

## Deliverables

### 1. First deliverable

Description
""")

        result = cmd_validate(_validate_ns(plan_id='solution-missing-overview'))
        assert result['status'] == 'error'
        assert result['error'] == 'validation_failed'
        assert any('Overview' in issue for issue in result['issues'])


def test_validate_no_deliverables():
    """Test validation fails when no numbered deliverables found."""
    with PlanContext(plan_id='solution-no-deliverables') as ctx:
        (ctx.plan_dir / 'solution_outline.md').write_text("""# Solution: Test

## Summary

Brief summary

## Overview

Architecture diagram here

## Deliverables

Some text but no ### N. Title items
""")

        result = cmd_validate(_validate_ns(plan_id='solution-no-deliverables'))
        assert result['status'] == 'error'
        assert any('numbered deliverables' in issue for issue in result['issues'])


def test_validate_document_not_found():
    """Test validation fails when document doesn't exist."""
    with PlanContext(plan_id='no-solution'):
        result = cmd_validate(_validate_ns(plan_id='no-solution'))
        assert result['error'] == 'document_not_found'


# =============================================================================
# Tier 2: List Deliverables Command
# =============================================================================


def test_list_deliverables():
    """Test listing deliverables from solution document."""
    with PlanContext(plan_id='solution-list') as ctx:
        (ctx.plan_dir / 'solution_outline.md').write_text(VALID_SOLUTION)

        result = cmd_list_deliverables(_list_deliverables_ns(plan_id='solution-list'))
        assert result['status'] == 'success'
        assert result['deliverable_count'] == 3
        assert len(result['deliverables']) == 3
        # Check structure of deliverables
        first = result['deliverables'][0]
        assert first['number'] == 1
        assert first['title'] == 'Create JwtValidationService class'
        assert first['reference'] == '1. Create JwtValidationService class'


def test_list_deliverables_empty():
    """Test list-deliverables with no deliverables section."""
    with PlanContext(plan_id='solution-empty') as ctx:
        (ctx.plan_dir / 'solution_outline.md').write_text("""# Solution: Test

## Summary

Just summary, no deliverables section
""")

        result = cmd_list_deliverables(_list_deliverables_ns(plan_id='solution-empty'))
        assert result['error'] == 'section_not_found'


# =============================================================================
# Tier 2: Read Command
# =============================================================================


def test_read():
    """Test reading a solution document."""
    with PlanContext(plan_id='solution-read') as ctx:
        (ctx.plan_dir / 'solution_outline.md').write_text(VALID_SOLUTION)

        result = cmd_read(_read_ns(plan_id='solution-read'))
        assert result['status'] == 'success'
        # Content is a nested dict with parsed sections
        assert 'content' in result
        assert 'summary' in result['content']
        assert 'overview' in result['content']
        assert 'deliverables' in result['content']


def test_read_not_found():
    """Test read fails when document doesn't exist."""
    with PlanContext(plan_id='no-solution'):
        result = cmd_read(_read_ns(plan_id='no-solution'))
        assert result['error'] == 'document_not_found'


def test_read_deliverable_by_number():
    """Test reading a specific deliverable by number."""
    with PlanContext(plan_id='deliverable-num') as ctx:
        (ctx.plan_dir / 'solution_outline.md').write_text(VALID_SOLUTION)

        result = cmd_read(_read_ns(plan_id='deliverable-num', deliverable_number=1))
        assert result['status'] == 'success'
        assert result['deliverable']['number'] == 1
        assert 'JwtValidationService' in result['deliverable']['title']


def test_read_deliverable_by_number_second():
    """Test reading the second deliverable by number."""
    with PlanContext(plan_id='deliverable-num-2') as ctx:
        (ctx.plan_dir / 'solution_outline.md').write_text(VALID_SOLUTION)

        result = cmd_read(_read_ns(plan_id='deliverable-num-2', deliverable_number=2))
        assert result['status'] == 'success'
        assert result['deliverable']['number'] == 2
        assert 'configuration properties' in result['deliverable']['title']


def test_read_deliverable_not_found():
    """Test reading non-existent deliverable number."""
    with PlanContext(plan_id='deliverable-notfound') as ctx:
        (ctx.plan_dir / 'solution_outline.md').write_text(VALID_SOLUTION)

        result = cmd_read(_read_ns(plan_id='deliverable-notfound', deliverable_number=999))
        assert result['error'] == 'deliverable_not_found'
        assert 'available' in result  # Should list available deliverable numbers


def test_read_section_summary():
    """--section summary returns the Summary section body in the content field."""
    with PlanContext(plan_id='section-summary') as ctx:
        (ctx.plan_dir / 'solution_outline.md').write_text(VALID_SOLUTION)

        result = cmd_read(_read_ns(plan_id='section-summary', section='summary'))
        assert result['status'] == 'success'
        assert result['section'] == 'summary'
        assert result['requested_section'] == 'summary'
        assert 'Implement JWT validation service' in result['content']
        # Body should be the section body only, with no ## heading and no subsequent sections
        assert '## Summary' not in result['content']
        assert '## Overview' not in result['content']


def test_read_section_overview():
    """--section overview returns the Overview section body (diagram)."""
    with PlanContext(plan_id='section-overview') as ctx:
        (ctx.plan_dir / 'solution_outline.md').write_text(VALID_SOLUTION)

        result = cmd_read(_read_ns(plan_id='section-overview', section='overview'))
        assert result['status'] == 'success'
        assert result['section'] == 'overview'
        assert result['requested_section'] == 'overview'
        # Overview contains the ASCII diagram's box-drawing text
        assert 'JwtConfiguration' in result['content']


def test_read_section_case_insensitive():
    """--section matching is case-insensitive."""
    with PlanContext(plan_id='section-case') as ctx:
        (ctx.plan_dir / 'solution_outline.md').write_text(VALID_SOLUTION)

        result = cmd_read(_read_ns(plan_id='section-case', section='Summary'))
        assert result['status'] == 'success'
        assert result['section'] == 'summary'
        assert result['requested_section'] == 'Summary'


def test_read_section_not_found():
    """--section for a section that does not exist returns section_not_found."""
    with PlanContext(plan_id='section-missing') as ctx:
        (ctx.plan_dir / 'solution_outline.md').write_text(VALID_SOLUTION)

        result = cmd_read(_read_ns(plan_id='section-missing', section='does-not-exist'))
        assert result['status'] == 'error'
        assert result['error'] == 'section_not_found'
        assert result['requested_section'] == 'does-not-exist'
        assert 'does-not-exist' in result['message']


# =============================================================================
# Tier 2: Exists Command
# =============================================================================


def test_exists_present():
    """Test exists returns true when document exists."""
    with PlanContext(plan_id='solution-exists') as ctx:
        (ctx.plan_dir / 'solution_outline.md').write_text(VALID_SOLUTION)

        result = cmd_exists(_exists_ns(plan_id='solution-exists'))
        assert result['status'] == 'success'
        assert result['exists'] is True


def test_exists_absent():
    """Test exists returns success with exists=false when document doesn't exist."""
    with PlanContext(plan_id='no-solution'):
        result = cmd_exists(_exists_ns(plan_id='no-solution'))
        assert result['status'] == 'success'
        assert result['exists'] is False


# =============================================================================
# Tier 2: Resolve Path Command
# =============================================================================


def test_resolve_path():
    """Test resolve-path returns correct path."""
    with PlanContext(plan_id='solution-resolve') as ctx:
        result = cmd_resolve_path(_resolve_path_ns(plan_id='solution-resolve'))
        assert result['status'] == 'success'
        assert result['plan_id'] == 'solution-resolve'
        assert 'solution_outline.md' in result['path']
        assert result['exists'] is False

        # Write a file and check exists becomes True
        (ctx.plan_dir / 'solution_outline.md').write_text(VALID_SOLUTION)
        result = cmd_resolve_path(_resolve_path_ns(plan_id='solution-resolve'))
        assert result['exists'] is True


# =============================================================================
# Tier 2: Write Command (validates file on disk)
# =============================================================================


def test_write_new():
    """Test validating a new solution outline written to disk."""
    with PlanContext(plan_id='solution-write') as ctx:
        (ctx.plan_dir / 'solution_outline.md').write_text(VALID_SOLUTION)

        result = cmd_write(_write_ns(plan_id='solution-write'))
        assert result['status'] == 'success'
        assert result['file'] == 'solution_outline.md'
        assert 'validation' in result
        assert result['validation']['deliverable_count'] == 3


def test_write_includes_compatibility():
    """Test that write output includes compatibility when present in header."""
    with PlanContext(plan_id='solution-write-compat') as ctx:
        (ctx.plan_dir / 'solution_outline.md').write_text(VALID_SOLUTION)

        result = cmd_write(_write_ns(plan_id='solution-write-compat'))
        assert result['status'] == 'success'
        assert 'compatibility' in result['validation']
        assert 'breaking' in result['validation']['compatibility']


def test_write_validates_existing_file(monkeypatch):
    """Test that write detects validation errors in file on disk."""
    with PlanContext(plan_id='solution-invalid') as ctx:
        # Pin HOME and credentials dir for defense-in-depth against any
        # path resolution that might hit real ~/.plan-marshall-credentials.
        monkeypatch.setenv('HOME', str(ctx.fixture_dir))
        monkeypatch.setenv('PLAN_MARSHALL_CREDENTIALS_DIR', str(ctx.fixture_dir / 'creds'))
        (ctx.plan_dir / 'solution_outline.md').write_text('# Just a title\n\nNo required sections here.')

        result = cmd_write(_write_ns(plan_id='solution-invalid'))
        assert result['error'] == 'validation_failed'


def test_write_file_not_found():
    """Test that write fails when file not on disk."""
    with PlanContext(plan_id='solution-missing'):
        result = cmd_write(_write_ns(plan_id='solution-missing'))
        assert result['error'] == 'document_not_found'


# =============================================================================
# Tier 2: Update Command (validates file on disk)
# =============================================================================


def test_update_existing():
    """Test validating an updated solution outline."""
    with PlanContext(plan_id='solution-update') as ctx:
        updated_solution = VALID_SOLUTION.replace(
            'Implement JWT validation service for authentication.',
            'Implement enhanced JWT validation with key rotation support.',
        )
        (ctx.plan_dir / 'solution_outline.md').write_text(updated_solution)

        result = cmd_update(_update_ns(plan_id='solution-update'))
        assert result['status'] == 'success'
        assert result['action'] == 'updated'
        assert result['validation']['deliverable_count'] == 3


def test_update_nonexistent():
    """Test that update fails when solution outline does not exist."""
    with PlanContext(plan_id='solution-no-update'):
        result = cmd_update(_update_ns(plan_id='solution-no-update'))
        assert result['error'] == 'document_not_found'


# =============================================================================
# Tier 2: module_testing Profile Warning
# =============================================================================


def test_validate_warns_module_testing_without_test_files():
    """Test that module_testing profile with production-only paths generates a warning."""
    solution_with_bad_profile = VALID_SOLUTION.replace(
        """### 2. Add configuration properties

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
- `src/main/resources/application.properties`""",
        """### 2. Add configuration properties

Add JWT configuration to application.properties.

**Metadata:**
- change_type: feature
- execution_mode: automated
- domain: java
- module: jwt-service
- depends: 1

**Profiles:**
- implementation
- module_testing

**Affected files:**
- `src/main/resources/application.properties`""",
    )
    with PlanContext(plan_id='solution-warn-profile') as ctx:
        (ctx.plan_dir / 'solution_outline.md').write_text(solution_with_bad_profile)

        result = cmd_validate(_validate_ns(plan_id='solution-warn-profile'))
        assert result['status'] == 'success'
        # Should have a warning about module_testing without test files
        assert 'warnings' in result
        assert any('module_testing profile but no test files' in w for w in result['warnings'])


def test_validate_no_warning_module_testing_with_test_files():
    """Test that module_testing profile with test file paths does not generate a warning."""
    with PlanContext(plan_id='solution-no-warn-profile') as ctx:
        (ctx.plan_dir / 'solution_outline.md').write_text(VALID_SOLUTION)

        result = cmd_validate(_validate_ns(plan_id='solution-no-warn-profile'))
        assert result['status'] == 'success'
        # D3 has module_testing + test file path, so no warning expected for it
        warnings = result.get('warnings', [])
        d3_warnings = [w for w in warnings if 'D3' in w and 'module_testing' in w]
        assert len(d3_warnings) == 0, f'Unexpected module_testing warning for D3: {d3_warnings}'


# =============================================================================
# Tier 2: Invalid Plan IDs (require_valid_plan_id calls sys.exit)
# =============================================================================


def test_invalid_plan_id_uppercase():
    """Test that uppercase plan IDs are rejected."""
    with PlanContext():
        with pytest.raises(SystemExit) as exc_info:
            cmd_validate(_validate_ns(plan_id='My-Plan'))
        assert exc_info.value.code == 0


def test_invalid_plan_id_underscore():
    """Test that underscores in plan IDs are rejected."""
    with PlanContext():
        with pytest.raises(SystemExit) as exc_info:
            cmd_validate(_validate_ns(plan_id='my_plan'))
        assert exc_info.value.code == 0


# =============================================================================
# Tier 3 (subprocess): CLI Plumbing Tests
# =============================================================================


def test_cli_validate_success(monkeypatch):
    """CLI plumbing: validate subcommand works end-to-end."""
    with PlanContext(plan_id='cli-validate') as ctx:
        # Pin HOME and credentials dir for the subprocess so solution-outline
        # CLI side-effects cannot touch the real host paths.
        monkeypatch.setenv('HOME', str(ctx.fixture_dir))
        monkeypatch.setenv('PLAN_MARSHALL_CREDENTIALS_DIR', str(ctx.fixture_dir / 'creds'))
        (ctx.plan_dir / 'solution_outline.md').write_text(VALID_SOLUTION)

        result = run_script(SCRIPT_PATH, 'validate', '--plan-id', 'cli-validate')
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['validation']['deliverable_count'] == 3


def test_cli_read_raw():
    """CLI plumbing: read --raw outputs raw markdown to stdout."""
    with PlanContext(plan_id='cli-raw') as ctx:
        (ctx.plan_dir / 'solution_outline.md').write_text(VALID_SOLUTION)

        result = run_script(SCRIPT_PATH, 'read', '--plan-id', 'cli-raw', '--raw')
        assert result.success, f'Script failed: {result.stderr}'
        # Raw mode outputs the actual markdown before the TOON result
        assert '# Solution: JWT Validation Service' in result.stdout
        assert '## Overview' in result.stdout
        assert '## Deliverables' in result.stdout
        assert '### 1. Create JwtValidationService class' in result.stdout


def test_cli_invalid_plan_id():
    """CLI plumbing: invalid plan ID exits with code 0 and TOON error."""
    with PlanContext():
        result = run_script(SCRIPT_PATH, 'validate', '--plan-id', 'My-Plan')
        assert result.success, 'Expected exit 0 with TOON error for invalid plan ID'
        data = parse_toon(result.stdout)
        assert data['error'] == 'invalid_plan_id'


def test_cli_read_section_and_deliverable_mutually_exclusive(monkeypatch):
    """CLI plumbing: --section and --deliverable-number cannot be combined."""
    with PlanContext(plan_id='cli-section-mutex') as ctx:
        # Pin HOME and credentials dir for the subprocess so any eager
        # initialization cannot touch the real host paths.
        monkeypatch.setenv('HOME', str(ctx.fixture_dir))
        monkeypatch.setenv('PLAN_MARSHALL_CREDENTIALS_DIR', str(ctx.fixture_dir / 'creds'))
        (ctx.plan_dir / 'solution_outline.md').write_text(VALID_SOLUTION)

        result = run_script(
            SCRIPT_PATH,
            'read',
            '--plan-id',
            'cli-section-mutex',
            '--section',
            'summary',
            '--deliverable-number',
            '1',
        )
        # argparse mutually exclusive group errors exit with code 2
        assert not result.success, 'Expected failure when combining --section and --deliverable-number'
