#!/usr/bin/env python3
"""Sibling fixtures helper for ``pm-dev-java/maven-profile-management`` tests.

This module mirrors the canonical 6-axis matrix exposed by
``test/plan-marshall/_input_validation_fixtures.py``. It is duplicated here
(rather than imported via cross-bundle PYTHONPATH) because pytest only
adds ``test/plan-marshall`` and ``test/pm-plugin-development`` to
``sys.path`` (see ``test/conftest.py``). Per ``dev-general-module-testing``
the canonical convention for bundle-scoped helpers is a sibling
``_fixtures.py``.

Only the subset needed by ``profiles.py`` rejection-path tests is included
(``module`` flag + assertion helpers).
"""

from __future__ import annotations

from typing import Any

# 5 malformed axes shared with the canonical matrix.
_BASE_MALFORMED = [
    ('empty', ''),
    ('path-separator', 'foo/bar'),
    ('glob-meta', 'foo*bar'),
    ('traversal', '../parent'),
    ('overlong', 'a' * 300 + '!'),
]


# Happy-path canonical value satisfying MODULE_NAME_RE.
_HAPPY: dict[str, str] = {
    'module': 'my-module',
}


MALFORMED_AXES: dict[str, list[tuple[str, str]]] = {
    field: list(_BASE_MALFORMED) for field in _HAPPY
}


HAPPY_VALUES: dict[str, str] = dict(_HAPPY)


def parse_toon_output(stdout: str) -> dict[str, Any]:
    """Parse a TOON document from script stdout."""
    from toon_parser import parse_toon  # type: ignore[import-not-found]

    return parse_toon(stdout)


def assert_invalid_field(result: Any, expected_error: str) -> None:
    """Assert ``status: error / error: <code>`` TOON on stdout (exit 0)."""
    assert result.returncode == 0, (
        f'expected exit 0 for identifier-validator failure '
        f'(got {result.returncode})\nstdout={result.stdout!r}\n'
        f'stderr={result.stderr!r}'
    )
    data = parse_toon_output(result.stdout)
    assert data.get('status') == 'error', (
        f'expected status=error, got {data.get("status")!r}\n'
        f'stdout={result.stdout!r}'
    )
    assert data.get('error') == expected_error, (
        f'expected error={expected_error!r}, got {data.get("error")!r}\n'
        f'stdout={result.stdout!r}'
    )


def assert_not_invalid_field(result: Any, error_code: str) -> None:
    """Assert the script did NOT reject input with ``error: <code>``.

    For happy-path inputs: the script may still return another error
    (missing data, unknown module, etc.), but it MUST NOT report the
    canonical identifier validator as the failure cause.
    """
    if result.returncode == 0 and result.stdout.strip():
        try:
            data = parse_toon_output(result.stdout)
        except Exception:
            return  # not parseable as TOON — definitely not the validator path
        assert data.get('error') != error_code, (
            f'happy-path value triggered {error_code} unexpectedly\n'
            f'stdout={result.stdout!r}'
        )
