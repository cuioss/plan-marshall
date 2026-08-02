#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for build_result.py module."""

import importlib.util
from pathlib import Path

import pytest
from file_ops import get_build_results_dir
from marketplace_paths import NO_PLAN_SENTINEL

_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'script-shared'
    / 'scripts'
    / 'build'
)


def _load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_build_result_mod = _load_module('_build_result', '_build_result.py')

ERROR_BUILD_FAILED = _build_result_mod.ERROR_BUILD_FAILED
ERROR_EXECUTION_FAILED = _build_result_mod.ERROR_EXECUTION_FAILED
ERROR_LOG_FILE_FAILED = _build_result_mod.ERROR_LOG_FILE_FAILED
ERROR_TIMEOUT = _build_result_mod.ERROR_TIMEOUT
ERROR_WRAPPER_NOT_FOUND = _build_result_mod.ERROR_WRAPPER_NOT_FOUND
REQUIRED_FIELDS = _build_result_mod.REQUIRED_FIELDS
STATUS_ERROR = _build_result_mod.STATUS_ERROR
STATUS_SUCCESS = _build_result_mod.STATUS_SUCCESS
STATUS_TIMEOUT = _build_result_mod.STATUS_TIMEOUT
TIMESTAMP_FORMAT = _build_result_mod.TIMESTAMP_FORMAT
create_log_file = _build_result_mod.create_log_file
error_result = _build_result_mod.error_result
success_result = _build_result_mod.success_result
timeout_result = _build_result_mod.timeout_result
validate_result = _build_result_mod.validate_result


#: Plan id used by the placement tests. Resolves under the autouse
#: ``_plan_base_dir_sandbox`` PLAN_BASE_DIR redirect, so every log this module
#: creates lands in the per-test sandbox rather than the real plan store.
_PLAN_ID = 'build-result-placement-plan'


def test_timestamp_format():
    """TIMESTAMP_FORMAT has expected pattern."""
    assert TIMESTAMP_FORMAT == '%Y-%m-%d-%H%M%S'


def test_status_constants():
    """Status constants have expected values."""
    assert STATUS_SUCCESS == 'success'
    assert STATUS_ERROR == 'error'
    assert STATUS_TIMEOUT == 'timeout'


def test_error_constants():
    """Error constants have expected values."""
    assert ERROR_BUILD_FAILED == 'build_failed'
    assert ERROR_TIMEOUT == 'timeout'
    assert ERROR_EXECUTION_FAILED == 'execution_failed'
    assert ERROR_WRAPPER_NOT_FOUND == 'wrapper_not_found'
    assert ERROR_LOG_FILE_FAILED == 'log_file_failed'


def test_required_fields():
    """REQUIRED_FIELDS contains all required fields."""
    expected = {'status', 'exit_code', 'duration_seconds', 'log_file', 'command'}
    assert REQUIRED_FIELDS == expected


def test_create_log_file_creates():
    """Creates log file in expected location."""
    log_file = create_log_file('maven', 'default', plan_id=_PLAN_ID)
    assert log_file is not None
    assert Path(log_file).exists()


def test_create_log_file_creates_directories():
    """Creates intermediate directories."""
    log_file = create_log_file('maven', 'core-api', plan_id=_PLAN_ID)
    assert log_file is not None
    assert Path(log_file).parent.name == 'core-api'


def test_create_log_file_lands_under_resolving_plans_build_results():
    """The log lands under ``{plan_dir}/build-results/{scope}/`` for a real plan.

    The placement assertion for the relocation: the result belongs to the plan
    that caused the build, so the path must be the one
    :func:`file_ops.get_build_results_dir` owns for that plan id — not a shared
    temp tree. Fails against the pre-relocation code, which resolved the base
    from the project directory and never consulted the plan id at all.
    """
    # Arrange
    expected_base = get_build_results_dir(_PLAN_ID).resolve()

    # Act
    log_file = create_log_file('maven', 'core-api', plan_id=_PLAN_ID)

    # Assert
    assert log_file is not None
    path = Path(log_file).resolve()
    assert path.parent == expected_base / 'core-api'
    assert path.parent.parent.name == 'build-results'
    assert path.parent.parent.parent.name == _PLAN_ID


def test_create_log_file_lands_under_sentinel_plan_dir_for_no_plan():
    """A plan-less build's log lands under the ``NO_PLAN`` sentinel plan dir.

    The sentinel is a real attribution, not an absent one: the result still has
    an owning directory, resolved by the same single owner of the path.
    """
    # Arrange
    expected_base = get_build_results_dir(NO_PLAN_SENTINEL).resolve()

    # Act
    log_file = create_log_file('maven', 'default', plan_id=NO_PLAN_SENTINEL)

    # Assert
    assert log_file is not None
    path = Path(log_file).resolve()
    assert path.parent == expected_base / 'default'
    assert NO_PLAN_SENTINEL in path.parts


def test_create_log_file_path_pattern():
    """Log file follows expected path pattern."""
    log_file = create_log_file('maven', 'default', plan_id=_PLAN_ID)
    path = Path(log_file)

    assert 'build-results' in path.parts
    assert '/default/' in str(path)
    assert path.name.startswith('maven-')
    assert path.suffix == '.log'


def test_create_log_file_different_build_systems():
    """Works with different build system names."""
    maven_log = create_log_file('maven', 'default', plan_id=_PLAN_ID)
    gradle_log = create_log_file('gradle', 'default', plan_id=_PLAN_ID)
    npm_log = create_log_file('npm', 'default', plan_id=_PLAN_ID)

    assert 'maven-' in maven_log
    assert 'gradle-' in gradle_log
    assert 'npm-' in npm_log


def test_create_log_file_different_scopes():
    """Creates files in different scope directories."""
    default_log = create_log_file('maven', 'default', plan_id=_PLAN_ID)
    core_log = create_log_file('maven', 'core-api', plan_id=_PLAN_ID)

    assert '/default/' in default_log
    assert '/core-api/' in core_log


def test_create_log_file_separates_results_by_plan():
    """Two plans' results land in two different directories.

    The point of the relocation is attribution: a build run by one plan must
    not deposit its log in another plan's directory.
    """
    # Act
    first = create_log_file('maven', 'default', plan_id='plan-alpha')
    second = create_log_file('maven', 'default', plan_id='plan-beta')

    # Assert
    assert first is not None
    assert second is not None
    assert Path(first).parent != Path(second).parent
    assert 'plan-alpha' in Path(first).parts
    assert 'plan-beta' in Path(second).parts


def test_create_log_file_returns_absolute():
    """Returns absolute path."""
    log_file = create_log_file('maven', 'default', plan_id=_PLAN_ID)
    assert Path(log_file).is_absolute()


def test_create_log_file_rejects_parent_escape_scope():
    """A ..-escape scope is rejected: no log dir is created outside the base.

    The containment guard survives the relocation — the base it constrains is
    now the plan's ``build-results`` directory, but an escaping scope must
    still fail closed with ``None`` rather than climbing out of it.
    """
    # Arrange: base is {plan_dir}/build-results, so a three-level ``..`` climb
    # lands at {base_dir}/escaped — outside the sanctioned base.
    base = get_build_results_dir(_PLAN_ID).resolve()
    escaped = base.parent.parent.parent / 'escaped'

    # Act
    log_file = create_log_file('maven', '../../../escaped', plan_id=_PLAN_ID)

    # Assert: guard fails closed and nothing was created outside the base.
    assert log_file is None
    assert not escaped.exists()


def test_create_log_file_rejects_absolute_scope(tmp_path):
    """An absolute-path scope is rejected and creates no file outside the base.

    An absolute ``scope`` replaces the base entirely under ``Path`` join
    semantics, so the guard must reject it rather than let the log land at the
    attacker's absolute path.
    """
    # Arrange: a tmp-scoped absolute path we can inspect for non-creation.
    evil_target = tmp_path / 'evil_target'

    # Act
    log_file = create_log_file('maven', str(evil_target), plan_id=_PLAN_ID)

    # Assert: guard fails closed and the escaping absolute dir was not created.
    assert log_file is None
    assert not evil_target.exists()


def test_create_log_file_legitimate_scope_stays_contained():
    """A legitimate single-segment scope still resolves strictly under the base."""
    # Arrange
    base = get_build_results_dir(_PLAN_ID).resolve()

    # Act
    log_file = create_log_file('maven', 'core-api', plan_id=_PLAN_ID)

    # Assert
    assert log_file is not None
    assert base in Path(log_file).resolve().parents


def test_create_log_file_requires_plan_id_keyword():
    """``plan_id`` is keyword-only and mandatory — no positional third argument.

    Pins the signature change itself: a build result with no owning plan is not
    a valid state, so a caller cannot omit the attribution, and the old
    ``create_log_file(system, scope, project_dir)`` positional form must no
    longer be accepted.
    """
    with pytest.raises(TypeError):
        create_log_file('maven', 'default')

    with pytest.raises(TypeError):
        create_log_file('maven', 'default', '/some/project/dir')


def test_success_result_basic():
    """Returns dict with all required fields."""
    result = success_result(45, '/path/to/log', './mvnw clean verify')

    assert result['status'] == STATUS_SUCCESS
    assert result['exit_code'] == 0
    assert result['duration_seconds'] == 45
    assert result['log_file'] == '/path/to/log'
    assert result['command'] == './mvnw clean verify'


def test_success_result_extra_fields():
    """Extra fields are included."""
    result = success_result(45, '/path/to/log', './mvnw clean verify', wrapper='./mvnw')
    assert result['wrapper'] == './mvnw'


def test_success_result_validates():
    """Result passes validation."""
    result = success_result(45, '/path/to/log', './mvnw clean verify')
    valid, missing = validate_result(result)
    assert valid
    assert missing == []


def test_error_result_basic():
    """Returns dict with all required fields."""
    result = error_result(ERROR_BUILD_FAILED, 1, 23, '/path/to/log', './mvnw clean verify')

    assert result['status'] == STATUS_ERROR
    assert result['error'] == ERROR_BUILD_FAILED
    assert result['exit_code'] == 1
    assert result['duration_seconds'] == 23
    assert result['log_file'] == '/path/to/log'
    assert result['command'] == './mvnw clean verify'


def test_error_result_wrapper_not_found():
    """Handles wrapper_not_found error."""
    result = error_result(ERROR_WRAPPER_NOT_FOUND, -1, 0, '', 'mvnw clean verify')
    assert result['error'] == ERROR_WRAPPER_NOT_FOUND
    assert result['exit_code'] == -1


def test_error_result_extra_fields():
    """Extra fields are included."""
    result = error_result(
        ERROR_BUILD_FAILED,
        1,
        23,
        '/path/to/log',
        './mvnw clean verify',
        errors=[{'file': 'Main.java', 'line': 15, 'message': 'error'}],
    )
    assert 'errors' in result
    assert len(result['errors']) == 1


def test_error_result_validates():
    """Result passes validation."""
    result = error_result(ERROR_BUILD_FAILED, 1, 23, '/path/to/log', './mvnw clean verify')
    valid, missing = validate_result(result)
    assert valid
    assert missing == []


def test_timeout_result_basic():
    """Returns dict with all required fields."""
    result = timeout_result(300, 300, '/path/to/log', './mvnw clean verify')

    assert result['status'] == STATUS_TIMEOUT
    assert result['error'] == ERROR_TIMEOUT
    assert result['exit_code'] == -1
    assert result['timeout_used_seconds'] == 300
    assert result['duration_seconds'] == 300
    assert result['log_file'] == '/path/to/log'
    assert result['command'] == './mvnw clean verify'


def test_timeout_result_extra_fields():
    """Extra fields are included."""
    result = timeout_result(300, 300, '/path/to/log', './mvnw clean verify', wrapper='./mvnw')
    assert result['wrapper'] == './mvnw'


def test_timeout_result_validates():
    """Result passes validation."""
    result = timeout_result(300, 300, '/path/to/log', './mvnw clean verify')
    valid, missing = validate_result(result)
    assert valid
    assert missing == []


def test_validate_result_valid():
    """Returns True for valid result."""
    result = {
        'status': 'success',
        'exit_code': 0,
        'duration_seconds': 45,
        'log_file': '/path/to/log',
        'command': './mvnw clean verify',
    }
    valid, missing = validate_result(result)
    assert valid
    assert missing == []


def test_validate_result_missing_one():
    """Returns False with one missing field."""
    result = {
        'status': 'success',
        'exit_code': 0,
        'duration_seconds': 45,
        'log_file': '/path/to/log',
    }
    valid, missing = validate_result(result)
    assert not valid
    assert missing == ['command']


def test_validate_result_missing_multiple():
    """Returns False with multiple missing fields."""
    result = {'status': 'success'}
    valid, missing = validate_result(result)
    assert not valid
    assert 'command' in missing
    assert 'duration_seconds' in missing
    assert 'exit_code' in missing
    assert 'log_file' in missing


def test_validate_result_empty():
    """Returns False for empty dict."""
    valid, missing = validate_result({})
    assert not valid
    assert len(missing) == 5


def test_validate_result_non_dict():
    """Returns False for non-dict."""
    valid, missing = validate_result('not a dict')
    assert not valid
    assert len(missing) == 5


def test_validate_result_missing_sorted():
    """Missing fields are sorted alphabetically."""
    result = {'status': 'success'}
    valid, missing = validate_result(result)
    assert missing == sorted(missing)


def test_validate_result_extra_fields_ok():
    """Extra fields don't affect validation."""
    result = {
        'status': 'success',
        'exit_code': 0,
        'duration_seconds': 45,
        'log_file': '/path/to/log',
        'command': './mvnw clean verify',
        'extra': 'field',
    }
    valid, missing = validate_result(result)
    assert valid
    assert missing == []
