#!/usr/bin/env python3
"""
Tests for manage-solution-outline script.

Tier 2 (direct import) tests with 2-3 subprocess tests for CLI plumbing.
Solution outlines are written directly by agents, then validated via this script.
"""

import importlib.util
from argparse import Namespace

import pytest

from conftest import get_script_path, run_script

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
cmd_get_field = _mod.cmd_get_field
SCOPE_ESTIMATE_VALUES = _mod.SCOPE_ESTIMATE_VALUES

# Import toon_parser - conftest sets up PYTHONPATH
from toon_parser import parse_toon  # type: ignore[import-not-found]  # noqa: E402

# Sample valid solution outline with ASCII diagram (contract-compliant)
VALID_SOLUTION = """# Solution: JWT Validation Service

plan_id: test-plan
created: 2025-01-01T00:00:00Z
compatibility: breaking — Clean-slate approach, no deprecation nor transitionary comments

## Summary

Implement JWT validation service for authentication.

## Solution Metadata

- scope_estimate: surgical

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
- `src/main/java/de/cuioss/jwt/JwtValidationService.java` (write-new)

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
- `src/main/resources/application.properties` (write-replace)

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
- `src/test/java/de/cuioss/jwt/JwtValidationServiceTest.java` (write-new)

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


def _get_field_ns(plan_id='test-plan', field='scope_estimate'):
    """Build Namespace for cmd_get_field."""
    return Namespace(plan_id=plan_id, field=field)


# =============================================================================
# Tier 2: Validate Command
# =============================================================================


def test_validate_success(plan_context):
    """Test validating a well-formed solution document."""
    (plan_context.plan_dir_for('solution-valid') / 'solution_outline.md').write_text(VALID_SOLUTION)

    result = cmd_validate(_validate_ns(plan_id='solution-valid'))
    assert result['status'] == 'success'
    assert 'validation' in result
    assert result['validation']['deliverable_count'] == 3
    assert '1. Create JwtValidationService class' in result['validation']['deliverables']


def test_validate_extracts_compatibility(plan_context):
    """Test that validate extracts compatibility from header metadata."""
    (plan_context.plan_dir_for('solution-compat') / 'solution_outline.md').write_text(VALID_SOLUTION)

    result = cmd_validate(_validate_ns(plan_id='solution-compat'))
    assert result['status'] == 'success'
    assert 'compatibility' in result['validation']
    compat = result['validation']['compatibility']
    assert 'breaking' in compat


def test_validate_without_compatibility(plan_context):
    """Test that validate succeeds when compatibility header is absent."""
    solution_no_compat = VALID_SOLUTION.replace(
        'compatibility: breaking \u2014 Clean-slate approach, no deprecation nor transitionary comments\n', ''
    )
    (plan_context.plan_dir_for('solution-no-compat') / 'solution_outline.md').write_text(solution_no_compat)

    result = cmd_validate(_validate_ns(plan_id='solution-no-compat'))
    assert result['status'] == 'success'
    # compatibility should not be present when header lacks it
    assert 'compatibility' not in result.get('validation', {})


def test_validate_missing_overview(plan_context):
    """Test validation fails when Overview section is missing."""
    (plan_context.plan_dir_for('solution-missing-overview') / 'solution_outline.md').write_text("""# Solution: Test

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


def test_validate_no_deliverables(plan_context):
    """Test validation fails when no numbered deliverables found."""
    (plan_context.plan_dir_for('solution-no-deliverables') / 'solution_outline.md').write_text("""# Solution: Test

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


def test_validate_document_not_found(plan_context):
    """Test validation fails when document doesn't exist."""
    result = cmd_validate(_validate_ns(plan_id='no-solution'))
    assert result['error'] == 'document_not_found'


# =============================================================================
# Tier 2: List Deliverables Command
# =============================================================================


def test_list_deliverables(plan_context):
    """Test listing deliverables from solution document."""
    (plan_context.plan_dir_for('solution-list') / 'solution_outline.md').write_text(VALID_SOLUTION)

    result = cmd_list_deliverables(_list_deliverables_ns(plan_id='solution-list'))
    assert result['status'] == 'success'
    assert result['deliverable_count'] == 3
    assert len(result['deliverables']) == 3
    # Check structure of deliverables
    first = result['deliverables'][0]
    assert first['number'] == 1
    assert first['title'] == 'Create JwtValidationService class'
    assert first['reference'] == '1. Create JwtValidationService class'
    # affected_files surfaces the {path, intent} shape for phase-4-plan
    assert first['affected_files'] == [
        {'path': 'src/main/java/de/cuioss/jwt/JwtValidationService.java', 'intent': 'write-new'}
    ]


def test_validate_rejects_missing_intent_marker(plan_context):
    """validate reports a hard error for an Affected files entry with no intent marker."""
    bad = VALID_SOLUTION.replace(
        '- `src/main/java/de/cuioss/jwt/JwtValidationService.java` (write-new)',
        '- `src/main/java/de/cuioss/jwt/JwtValidationService.java`',
    )
    (plan_context.plan_dir_for('solution-no-intent') / 'solution_outline.md').write_text(bad)

    result = cmd_validate(_validate_ns(plan_id='solution-no-intent'))
    assert result['status'] == 'error'
    assert any('missing intent marker' in e for e in result['issues'])


def test_validate_rejects_invalid_intent_marker(plan_context):
    """validate reports a hard error for an Affected files entry with an invalid intent."""
    bad = VALID_SOLUTION.replace(
        '- `src/main/java/de/cuioss/jwt/JwtValidationService.java` (write-new)',
        '- `src/main/java/de/cuioss/jwt/JwtValidationService.java` (rewrite)',
    )
    (plan_context.plan_dir_for('solution-bad-intent') / 'solution_outline.md').write_text(bad)

    result = cmd_validate(_validate_ns(plan_id='solution-bad-intent'))
    assert result['status'] == 'error'
    assert any('invalid intent marker' in e for e in result['issues'])


def test_list_deliverables_empty(plan_context):
    """Test list-deliverables with no deliverables section."""
    (plan_context.plan_dir_for('solution-empty') / 'solution_outline.md').write_text("""# Solution: Test

## Summary

Just summary, no deliverables section
""")

    result = cmd_list_deliverables(_list_deliverables_ns(plan_id='solution-empty'))
    assert result['error'] == 'section_not_found'


# =============================================================================
# Tier 2: Read Command
# =============================================================================


def test_read(plan_context):
    """Test reading a solution document."""
    (plan_context.plan_dir_for('solution-read') / 'solution_outline.md').write_text(VALID_SOLUTION)

    result = cmd_read(_read_ns(plan_id='solution-read'))
    assert result['status'] == 'success'
    # Content is a nested dict with parsed sections
    assert 'content' in result
    assert 'summary' in result['content']
    assert 'overview' in result['content']
    assert 'deliverables' in result['content']


def test_read_not_found(plan_context):
    """Test read fails when document doesn't exist."""
    result = cmd_read(_read_ns(plan_id='no-solution'))
    assert result['error'] == 'document_not_found'


def test_read_deliverable_by_number(plan_context):
    """Test reading a specific deliverable by number."""
    (plan_context.plan_dir_for('deliverable-num') / 'solution_outline.md').write_text(VALID_SOLUTION)

    result = cmd_read(_read_ns(plan_id='deliverable-num', deliverable_number=1))
    assert result['status'] == 'success'
    assert result['deliverable']['number'] == 1
    assert 'JwtValidationService' in result['deliverable']['title']


def test_read_deliverable_by_number_second(plan_context):
    """Test reading the second deliverable by number."""
    (plan_context.plan_dir_for('deliverable-num-2') / 'solution_outline.md').write_text(VALID_SOLUTION)

    result = cmd_read(_read_ns(plan_id='deliverable-num-2', deliverable_number=2))
    assert result['status'] == 'success'
    assert result['deliverable']['number'] == 2
    assert 'configuration properties' in result['deliverable']['title']


def test_read_deliverable_not_found(plan_context):
    """Test reading non-existent deliverable number."""
    (plan_context.plan_dir_for('deliverable-notfound') / 'solution_outline.md').write_text(VALID_SOLUTION)

    result = cmd_read(_read_ns(plan_id='deliverable-notfound', deliverable_number=999))
    assert result['error'] == 'deliverable_not_found'
    assert 'available' in result  # Should list available deliverable numbers


def test_read_section_summary(plan_context):
    """--section summary returns the Summary section body in the content field."""
    (plan_context.plan_dir_for('section-summary') / 'solution_outline.md').write_text(VALID_SOLUTION)

    result = cmd_read(_read_ns(plan_id='section-summary', section='summary'))
    assert result['status'] == 'success'
    assert result['section'] == 'summary'
    assert result['requested_section'] == 'summary'
    assert 'Implement JWT validation service' in result['content']
    # Body should be the section body only, with no ## heading and no subsequent sections
    assert '## Summary' not in result['content']
    assert '## Overview' not in result['content']


def test_read_section_overview(plan_context):
    """--section overview returns the Overview section body (diagram)."""
    (plan_context.plan_dir_for('section-overview') / 'solution_outline.md').write_text(VALID_SOLUTION)

    result = cmd_read(_read_ns(plan_id='section-overview', section='overview'))
    assert result['status'] == 'success'
    assert result['section'] == 'overview'
    assert result['requested_section'] == 'overview'
    # Overview contains the ASCII diagram's box-drawing text
    assert 'JwtConfiguration' in result['content']


def test_read_section_case_insensitive(plan_context):
    """--section matching is case-insensitive."""
    (plan_context.plan_dir_for('section-case') / 'solution_outline.md').write_text(VALID_SOLUTION)

    result = cmd_read(_read_ns(plan_id='section-case', section='Summary'))
    assert result['status'] == 'success'
    assert result['section'] == 'summary'
    assert result['requested_section'] == 'Summary'


def test_read_section_not_found(plan_context):
    """--section for a section that does not exist returns section_not_found."""
    (plan_context.plan_dir_for('section-missing') / 'solution_outline.md').write_text(VALID_SOLUTION)

    result = cmd_read(_read_ns(plan_id='section-missing', section='does-not-exist'))
    assert result['status'] == 'error'
    assert result['error'] == 'section_not_found'
    assert result['requested_section'] == 'does-not-exist'
    assert 'does-not-exist' in result['message']


# =============================================================================
# Tier 2: Exists Command
# =============================================================================


def test_exists_present(plan_context):
    """Test exists returns true when document exists."""
    (plan_context.plan_dir_for('solution-exists') / 'solution_outline.md').write_text(VALID_SOLUTION)

    result = cmd_exists(_exists_ns(plan_id='solution-exists'))
    assert result['status'] == 'success'
    assert result['exists'] is True


def test_exists_absent(plan_context):
    """Test exists returns success with exists=false when document doesn't exist."""
    result = cmd_exists(_exists_ns(plan_id='no-solution'))
    assert result['status'] == 'success'
    assert result['exists'] is False


# =============================================================================
# Tier 2: Resolve Path Command
# =============================================================================


def test_resolve_path(plan_context):
    """Test resolve-path returns correct path."""
    result = cmd_resolve_path(_resolve_path_ns(plan_id='solution-resolve'))
    assert result['status'] == 'success'
    assert result['plan_id'] == 'solution-resolve'
    assert 'solution_outline.md' in result['path']
    assert result['exists'] is False

    # Write a file and check exists becomes True
    (plan_context.plan_dir_for('solution-resolve') / 'solution_outline.md').write_text(VALID_SOLUTION)
    result = cmd_resolve_path(_resolve_path_ns(plan_id='solution-resolve'))
    assert result['exists'] is True


# =============================================================================
# Tier 2: Write Command (validates file on disk)
# =============================================================================


def test_write_new(plan_context):
    """Test validating a new solution outline written to disk."""
    (plan_context.plan_dir_for('solution-write') / 'solution_outline.md').write_text(VALID_SOLUTION)

    result = cmd_write(_write_ns(plan_id='solution-write'))
    assert result['status'] == 'success'
    assert result['file'] == 'solution_outline.md'
    assert 'validation' in result
    assert result['validation']['deliverable_count'] == 3


def test_write_includes_compatibility(plan_context):
    """Test that write output includes compatibility when present in header."""
    (plan_context.plan_dir_for('solution-write-compat') / 'solution_outline.md').write_text(VALID_SOLUTION)

    result = cmd_write(_write_ns(plan_id='solution-write-compat'))
    assert result['status'] == 'success'
    assert 'compatibility' in result['validation']
    assert 'breaking' in result['validation']['compatibility']


def test_write_validates_existing_file(plan_context, monkeypatch):
    """Test that write detects validation errors in file on disk."""
    # Pin HOME and credentials dir for defense-in-depth against any
    # path resolution that might hit real ~/.plan-marshall-credentials.
    monkeypatch.setenv('HOME', str(plan_context.fixture_dir))
    monkeypatch.setenv('PLAN_MARSHALL_CREDENTIALS_DIR', str(plan_context.fixture_dir / 'creds'))
    (plan_context.plan_dir_for('solution-invalid') / 'solution_outline.md').write_text('# Just a title\n\nNo required sections here.')

    result = cmd_write(_write_ns(plan_id='solution-invalid'))
    assert result['error'] == 'validation_failed'


def test_write_file_not_found(plan_context):
    """Test that write fails when file not on disk."""
    result = cmd_write(_write_ns(plan_id='solution-missing'))
    assert result['error'] == 'document_not_found'


# =============================================================================
# Tier 2: Update Command (validates file on disk)
# =============================================================================


def test_update_existing(plan_context):
    """Test validating an updated solution outline."""
    updated_solution = VALID_SOLUTION.replace(
        'Implement JWT validation service for authentication.',
        'Implement enhanced JWT validation with key rotation support.',
    )
    (plan_context.plan_dir_for('solution-update') / 'solution_outline.md').write_text(updated_solution)

    result = cmd_update(_update_ns(plan_id='solution-update'))
    assert result['status'] == 'success'
    assert result['action'] == 'updated'
    assert result['validation']['deliverable_count'] == 3


def test_update_nonexistent(plan_context):
    """Test that update fails when solution outline does not exist."""
    result = cmd_update(_update_ns(plan_id='solution-no-update'))
    assert result['error'] == 'document_not_found'


# =============================================================================
# Tier 2: module_testing Profile Warning
# =============================================================================


def test_validate_warns_module_testing_without_test_files(plan_context):
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
- `src/main/resources/application.properties` (write-replace)""",
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
- `src/main/resources/application.properties` (write-replace)""",
    )
    (plan_context.plan_dir_for('solution-warn-profile') / 'solution_outline.md').write_text(solution_with_bad_profile)

    result = cmd_validate(_validate_ns(plan_id='solution-warn-profile'))
    assert result['status'] == 'success'
    # Should have a warning about module_testing without test files
    assert 'warnings' in result
    assert any('module_testing profile but no test files' in w for w in result['warnings'])


def test_validate_no_warning_module_testing_with_test_files(plan_context):
    """Test that module_testing profile with test file paths does not generate a warning."""
    (plan_context.plan_dir_for('solution-no-warn-profile') / 'solution_outline.md').write_text(VALID_SOLUTION)

    result = cmd_validate(_validate_ns(plan_id='solution-no-warn-profile'))
    assert result['status'] == 'success'
    # D3 has module_testing + test file path, so no warning expected for it
    warnings = result.get('warnings', [])
    d3_warnings = [w for w in warnings if 'D3' in w and 'module_testing' in w]
    assert len(d3_warnings) == 0, f'Unexpected module_testing warning for D3: {d3_warnings}'


# =============================================================================
# Tier 2: Invalid Plan IDs (require_valid_plan_id calls sys.exit)
# =============================================================================


def test_invalid_plan_id_uppercase(plan_context):
    """Test that uppercase plan IDs are rejected."""
    with pytest.raises(SystemExit) as exc_info:
        cmd_validate(_validate_ns(plan_id='My-Plan'))
    assert exc_info.value.code == 0


def test_invalid_plan_id_underscore(plan_context):
    """Test that underscores in plan IDs are rejected."""
    with pytest.raises(SystemExit) as exc_info:
        cmd_validate(_validate_ns(plan_id='my_plan'))
    assert exc_info.value.code == 0


# =============================================================================
# Tier 2: scope_estimate (Solution Metadata) — read, validate, get-field
# =============================================================================


SOLUTION_NO_METADATA = """# Solution: No Metadata

## Summary

Brief summary

## Overview

Diagram here

## Deliverables

### 1. First deliverable

**Metadata:**
- change_type: feature
- execution_mode: automated
- domain: java
- module: jwt-service
- depends: none

**Profiles:**
- implementation

**Affected files:**
- `src/main/java/Foo.java` (write-new)

**Verification:**
- Command: `mvn test`
- Criteria: All tests pass

**Success Criteria:**
- Works
"""


def _solution_with_scope(value: str) -> str:
    """Return a VALID_SOLUTION variant with the scope_estimate replaced."""
    return VALID_SOLUTION.replace('- scope_estimate: surgical', f'- scope_estimate: {value}')


def test_validate_surfaces_scope_estimate(plan_context):
    """Validate exposes scope_estimate from the Solution Metadata block."""
    (plan_context.plan_dir_for('scope-surface') / 'solution_outline.md').write_text(VALID_SOLUTION)

    result = cmd_validate(_validate_ns(plan_id='scope-surface'))
    assert result['status'] == 'success'
    assert result['validation']['scope_estimate'] == 'surgical'
    # solution_metadata listed first in sections_found
    assert 'solution_metadata' in result['validation']['sections_found']


def test_validate_rejects_missing_solution_metadata(plan_context):
    """Validate fails when the Solution Metadata section is absent."""
    (plan_context.plan_dir_for('scope-missing-section') / 'solution_outline.md').write_text(SOLUTION_NO_METADATA)

    result = cmd_validate(_validate_ns(plan_id='scope-missing-section'))
    assert result['status'] == 'error'
    assert result['error'] == 'validation_failed'
    assert any('Solution Metadata' in issue for issue in result['issues'])


def test_validate_rejects_missing_scope_estimate_field(plan_context):
    """Validate fails when Solution Metadata exists but scope_estimate is absent."""
    no_field = VALID_SOLUTION.replace(
        '## Solution Metadata\n\n- scope_estimate: surgical',
        '## Solution Metadata\n\n- something_else: foo',
    )
    (plan_context.plan_dir_for('scope-missing-field') / 'solution_outline.md').write_text(no_field)

    result = cmd_validate(_validate_ns(plan_id='scope-missing-field'))
    assert result['status'] == 'error'
    assert any('Missing scope_estimate' in issue for issue in result['issues'])


def test_validate_rejects_invalid_scope_estimate_enum(plan_context):
    """Validate fails when scope_estimate is not in the enum."""
    bad_value = _solution_with_scope('huge')
    (plan_context.plan_dir_for('scope-bad-enum') / 'solution_outline.md').write_text(bad_value)

    result = cmd_validate(_validate_ns(plan_id='scope-bad-enum'))
    assert result['status'] == 'error'
    joined = ' '.join(result['issues'])
    assert "Invalid scope_estimate 'huge'" in joined
    for v in SCOPE_ESTIMATE_VALUES:
        assert v in joined


def test_write_rejects_missing_scope_estimate(plan_context):
    """write rejects a document missing the scope_estimate field."""
    (plan_context.plan_dir_for('scope-write-missing') / 'solution_outline.md').write_text(SOLUTION_NO_METADATA)

    result = cmd_write(_write_ns(plan_id='scope-write-missing'))
    assert result['status'] == 'error'
    assert result['error'] == 'validation_failed'
    # Either Solution Metadata section absent OR scope_estimate missing
    assert any('scope_estimate' in issue or 'Solution Metadata' in issue for issue in result['issues'])


def test_update_rejects_invalid_scope_estimate_enum(plan_context):
    """update rejects a document whose scope_estimate is out of enum."""
    (plan_context.plan_dir_for('scope-update-bad') / 'solution_outline.md').write_text(_solution_with_scope('massive'))

    result = cmd_update(_update_ns(plan_id='scope-update-bad'))
    assert result['status'] == 'error'
    assert result['error'] == 'validation_failed'
    assert any("Invalid scope_estimate 'massive'" in issue for issue in result['issues'])


def test_read_surfaces_scope_estimate(plan_context):
    """Reading the full document surfaces scope_estimate at the top level."""
    (plan_context.plan_dir_for('scope-read') / 'solution_outline.md').write_text(VALID_SOLUTION)

    result = cmd_read(_read_ns(plan_id='scope-read'))
    assert result['status'] == 'success'
    assert result['scope_estimate'] == 'surgical'


def test_get_field_scope_estimate_success(plan_context):
    """get-field returns the persisted scope_estimate value."""
    (plan_context.plan_dir_for('get-field-ok') / 'solution_outline.md').write_text(VALID_SOLUTION)

    result = cmd_get_field(_get_field_ns(plan_id='get-field-ok', field='scope_estimate'))
    assert result['status'] == 'success'
    assert result['field'] == 'scope_estimate'
    assert result['value'] == 'surgical'


def test_get_field_scope_estimate_not_found(plan_context):
    """get-field returns field_not_found when scope_estimate is absent from disk."""
    (plan_context.plan_dir_for('get-field-missing') / 'solution_outline.md').write_text(SOLUTION_NO_METADATA)

    result = cmd_get_field(_get_field_ns(plan_id='get-field-missing', field='scope_estimate'))
    assert result['status'] == 'error'
    assert result['error'] == 'field_not_found'
    assert result['field'] == 'scope_estimate'


def test_get_field_unknown_field(plan_context):
    """get-field rejects unsupported field names."""
    (plan_context.plan_dir_for('get-field-unknown') / 'solution_outline.md').write_text(VALID_SOLUTION)

    result = cmd_get_field(_get_field_ns(plan_id='get-field-unknown', field='not_a_field'))
    assert result['status'] == 'error'
    assert result['error'] == 'unknown_field'


def test_get_field_document_not_found(plan_context):
    """get-field returns document_not_found when the solution outline does not exist."""
    result = cmd_get_field(_get_field_ns(plan_id='get-field-no-doc', field='scope_estimate'))
    assert result['status'] == 'error'
    assert result['error'] == 'document_not_found'


@pytest.mark.parametrize('value', list(SCOPE_ESTIMATE_VALUES))
def test_validate_accepts_each_enum_value(plan_context, value):
    """Every documented scope_estimate enum value validates successfully."""
    plan_id = f'scope-enum-{value.replace("_", "-")}'
    (plan_context.plan_dir_for(plan_id) / 'solution_outline.md').write_text(_solution_with_scope(value))

    result = cmd_validate(_validate_ns(plan_id=plan_id))
    assert result['status'] == 'success', f"Enum value '{value}' should validate"
    assert result['validation']['scope_estimate'] == value


# =============================================================================
# Tier 3 (subprocess): CLI Plumbing Tests
# =============================================================================


def test_cli_validate_success(plan_context, monkeypatch):
    """CLI plumbing: validate subcommand works end-to-end."""
    # Pin HOME and credentials dir for the subprocess so solution-outline
    # CLI side-effects cannot touch the real host paths.
    monkeypatch.setenv('HOME', str(plan_context.fixture_dir))
    monkeypatch.setenv('PLAN_MARSHALL_CREDENTIALS_DIR', str(plan_context.fixture_dir / 'creds'))
    (plan_context.plan_dir_for('cli-validate') / 'solution_outline.md').write_text(VALID_SOLUTION)

    result = run_script(SCRIPT_PATH, 'validate', '--plan-id', 'cli-validate')
    assert result.success, f'Script failed: {result.stderr}'
    data = parse_toon(result.stdout)
    assert data['status'] == 'success'
    assert data['validation']['deliverable_count'] == 3


def test_cli_read_raw(plan_context):
    """CLI plumbing: read --raw outputs raw markdown to stdout."""
    (plan_context.plan_dir_for('cli-raw') / 'solution_outline.md').write_text(VALID_SOLUTION)

    result = run_script(SCRIPT_PATH, 'read', '--plan-id', 'cli-raw', '--raw')
    assert result.success, f'Script failed: {result.stderr}'
    # Raw mode outputs the actual markdown before the TOON result
    assert '# Solution: JWT Validation Service' in result.stdout
    assert '## Overview' in result.stdout
    assert '## Deliverables' in result.stdout
    assert '### 1. Create JwtValidationService class' in result.stdout


def test_cli_invalid_plan_id(plan_context):
    """CLI plumbing: invalid plan ID exits with code 0 and TOON error."""
    result = run_script(SCRIPT_PATH, 'validate', '--plan-id', 'My-Plan')
    assert result.success, 'Expected exit 0 with TOON error for invalid plan ID'
    data = parse_toon(result.stdout)
    assert data['error'] == 'invalid_plan_id'


def test_cli_read_section_and_deliverable_mutually_exclusive(plan_context, monkeypatch):
    """CLI plumbing: --section and --deliverable-number cannot be combined."""
    # Pin HOME and credentials dir for the subprocess so any eager
    # initialization cannot touch the real host paths.
    monkeypatch.setenv('HOME', str(plan_context.fixture_dir))
    monkeypatch.setenv('PLAN_MARSHALL_CREDENTIALS_DIR', str(plan_context.fixture_dir / 'creds'))
    (plan_context.plan_dir_for('cli-section-mutex') / 'solution_outline.md').write_text(VALID_SOLUTION)

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
