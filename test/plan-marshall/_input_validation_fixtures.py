#!/usr/bin/env python3
"""Shared fixtures for 6-axis identifier-validation rejection-path tests.

Used by every plan-marshall manage-* script test module that exercises
canonical identifier flags (--plan-id, --lesson-id, --session-id,
--task-number, --task-id, --component, --hash-id, --phase, --memory-id,
--field, --module, --package, --domain, --name).

The 6 axes mirror the canonical fixture set from
``test/plan-marshall/tools-input-validation/test_input_validation.py``:

    * empty            — ``""``
    * path-separator   — contains ``/``
    * glob-meta        — contains ``*`` (or other metachars)
    * traversal        — ``../parent``
    * overlong         — > 256 chars
    * happy-path       — canonical valid value

This file is intentionally a sibling helper (``_fixtures.py`` style) and
is NOT a ``conftest.py`` — placing a ``conftest.py`` under
``test/plan-marshall/`` would silently shadow the top-level
``test/conftest.py`` and disable shared fixtures.

Usage::

    from _input_validation_fixtures import (
        REJECTION_AXES,
        assert_invalid_field,
    )

    @pytest.mark.parametrize('axis,bad_value', REJECTION_AXES['plan_id'])
    def test_invalid_plan_id_rejected(axis, bad_value):
        result = run_script(SCRIPT_PATH, 'list', '--plan-id', bad_value)
        assert_invalid_field(result, 'invalid_plan_id')
"""

from __future__ import annotations

from typing import Any

# =============================================================================
# Canonical malformed input matrix (excludes happy-path, which is per-flag)
# =============================================================================

# The malformed fixtures reused across most flags. Each entry is
# ``(axis_name, value)``. Fields that DO accept ``/``, ``.`` or other
# characters (e.g. ``--component`` accepts ``:``) override these via the
# per-flag table below.
_BASE_MALFORMED = [
    ('empty', ''),
    ('path-separator', 'foo/bar'),
    ('glob-meta', 'foo*bar'),
    ('traversal', '../parent'),
    # ``overlong`` combines size with an invalid character so the value
    # fails the canonical regex even when the regex has no length cap.
    # SESSION_ID_RE caps at 128 chars; every other identifier regex
    # rejects the trailing ``!``.
    ('overlong', 'a' * 300 + '!'),
]


# Happy-path canonical values per flag — these MUST satisfy the canonical
# regex in ``input_validation.py``. They will not necessarily produce a
# successful script run (the script may still return ``status: error`` for
# missing-plan, unknown-task, etc.) but they MUST NOT produce
# ``invalid_<field>``.
_HAPPY: dict[str, str] = {
    'plan_id': 'my-plan',
    'lesson_id': '2026-04-29-08-001',
    'session_id': 'sess_abc123',
    'task_number': '1',
    'task_id': 'TASK-1',
    'component': 'plan-marshall:manage-tasks',
    'hash_id': 'abcdef12',
    'phase': '1-init',
    'memory_id': 'mem_abc',
    'field': 'my_field',
    'module': 'my-module',
    'package': 'com.example.foo',
    'domain': 'java',
    'name': 'my-name',
}


def _malformed_for(field: str) -> list[tuple[str, str]]:
    """Return the malformed-input axes for a flag.

    Some flags legitimately accept characters that other flags reject
    (``--component`` accepts ``:``; ``--package`` accepts ``.``). The
    base matrix is conservative — it picks values that fail every
    canonical regex in ``input_validation.py``. No per-flag overrides are
    needed today.
    """
    return list(_BASE_MALFORMED)


# Canonical 6-axis matrix per flag: 5 malformed axes + 1 happy-path.
# The happy-path entry is included so the test parametrization can assert
# that canonical input passes the validator at the script-CLI boundary.
REJECTION_AXES: dict[str, list[tuple[str, str]]] = {
    field: _malformed_for(field) + [('happy-path', _HAPPY[field])] for field in _HAPPY
}


# Just the malformed axes (drop happy-path) — for tests that only assert
# rejection.
MALFORMED_AXES: dict[str, list[tuple[str, str]]] = {field: _malformed_for(field) for field in _HAPPY}


HAPPY_VALUES: dict[str, str] = dict(_HAPPY)


# =============================================================================
# Assertion helpers
# =============================================================================


def parse_toon_output(stdout: str) -> dict[str, Any]:
    """Parse a TOON document from script stdout.

    Subprocesses produce TOON on stdout when an identifier validator
    fires (``parse_args_with_toon_errors`` calls ``sys.exit(0)`` after
    emitting the error). This helper handles the common case of a
    single-document TOON payload.
    """
    from toon_parser import parse_toon  # type: ignore[import-not-found]

    return parse_toon(stdout)


def assert_invalid_field(result: Any, expected_error: str) -> None:
    """Assert a script invocation produced ``status: error / error: <code>``.

    The ``parse_args_with_toon_errors`` helper exits with code 0 after
    emitting the canonical TOON error to stdout (so the wrapper does
    not surface argparse's exit-code-2 contract to the caller).
    """
    assert result.returncode == 0, (
        f'expected exit 0 for identifier-validator failure '
        f'(got {result.returncode})\nstdout={result.stdout!r}\n'
        f'stderr={result.stderr!r}'
    )
    data = parse_toon_output(result.stdout)
    assert data.get('status') == 'error', f'expected status=error, got {data.get("status")!r}\nstdout={result.stdout!r}'
    assert data.get('error') == expected_error, (
        f'expected error={expected_error!r}, got {data.get("error")!r}\nstdout={result.stdout!r}'
    )


def assert_not_invalid_field(result: Any, error_code: str) -> None:
    """Assert the script did NOT reject input with ``error: <code>``.

    For happy-path inputs: the script may still return another error
    (missing plan, unknown task, etc.), but it MUST NOT report the
    canonical identifier validator as the failure cause.
    """
    if result.returncode == 0 and result.stdout.strip():
        try:
            data = parse_toon_output(result.stdout)
        except Exception:
            return  # not parseable as TOON — definitely not the validator path
        assert data.get('error') != error_code, (
            f'happy-path value triggered {error_code} unexpectedly\nstdout={result.stdout!r}'
        )
