#!/usr/bin/env python3
"""6-axis identifier-validation rejection-path tests for ``manage-interface.py``.

In-scope flags from TASK-5: ``--field`` (the ``update`` subcommand).

The 6 axes mirror the canonical fixture set established by TASK-2:

    * empty, path-separator, glob-meta, traversal, overlong (rejection)
    * happy-path (passes validator)

The ``--field`` validation chain (``add_field_arg`` type-validator ->
``parse_args_with_toon_errors`` -> ``invalid_field`` TOON) is exercised
IN-PROCESS against a minimal argparse parser that reproduces the
``manage-interface update`` surface — the exact pipeline the script runs,
asserted without one interpreter cold-start per axis. One subprocess smoke
(``test_update_field_validation_smoke``) keeps the end-to-end CLI plumbing
covered.
"""

from __future__ import annotations

import argparse
import io
import sys
from contextlib import redirect_stdout
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from _input_validation_fixtures import (  # type: ignore[import-not-found]  # noqa: E402
    HAPPY_VALUES,
    MALFORMED_AXES,
    parse_toon_output,
)

# input_validation lives on the conftest-managed PYTHONPATH (every skill's
# scripts/ dir is added). The validator + TOON-error wrapper are the in-process
# surface under test.
from input_validation import (  # type: ignore[import-not-found]  # noqa: E402
    add_field_arg,
    parse_args_with_toon_errors,
)

from conftest import get_script_path, run_script  # type: ignore[import-not-found]  # noqa: E402

SCRIPT_PATH = get_script_path('pm-documents', 'manage-interface', 'manage-interface.py')


def _validate_field_inprocess(value: str) -> tuple[int, dict]:
    """Run the ``--field`` validation chain in-process.

    Reproduces the ``manage-interface update --field <value>`` surface: a
    parser with ``add_field_arg`` (the ``validate_field_name`` type-validator)
    wrapped by ``parse_args_with_toon_errors`` (which maps a validator
    ``ValueError`` to the ``invalid_field`` TOON and ``sys.exit(0)``).

    Returns ``(exit_code, parsed_toon_or_empty)``. On a validator rejection the
    wrapper prints TOON and raises ``SystemExit(0)``; on a happy-path value the
    parser returns a namespace (no rejection TOON), reported as exit 0 + empty
    dict.
    """
    parser = argparse.ArgumentParser(prog='manage-interface', allow_abbrev=False)
    add_field_arg(parser, required=False)

    # parse_args_with_toon_errors() delegates to parser.parse_args() with no
    # explicit argv, so it reads sys.argv[1:]. Under pytest that would be
    # pytest's own argv (no --field → the value under test never reaches the
    # validator). Set sys.argv to supply --field explicitly for the parse;
    # the value is always passed (even the empty-string axis) so the
    # required=False flag still drives the validator.
    original_argv = sys.argv
    sys.argv = ['manage-interface', '--field', value]
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            parse_args_with_toon_errors(parser)
    except SystemExit as exc:
        code = 0 if exc.code is None else int(exc.code) if isinstance(exc.code, int) else 2
        out = buf.getvalue()
        data = parse_toon_output(out) if out.strip() else {}
        return code, data
    finally:
        sys.argv = original_argv
    return 0, {}


@pytest.mark.parametrize('axis,bad_value', MALFORMED_AXES['field'])
def test_update_rejects_invalid_field(axis, bad_value):
    """``manage-interface update --field <bad>`` → ``invalid_field`` TOON (in-process).

    The ``empty`` axis is the omit-the-flag case: ``add_field_arg`` is
    ``required=False``, so an empty value is supplied explicitly to drive the
    validator.
    """
    code, data = _validate_field_inprocess(bad_value)
    assert code == 0, f'identifier-validator failure must exit 0, got {code}'
    assert data.get('status') == 'error', f'expected status=error, got {data.get("status")!r}'
    assert data.get('error') == 'invalid_field', f'expected error=invalid_field, got {data.get("error")!r}'


def test_update_accepts_canonical_field():
    """Canonical ``--field`` value passes the validator (in-process).

    A happy-path value must NOT trigger ``invalid_field``.
    """
    code, data = _validate_field_inprocess(HAPPY_VALUES['field'])
    assert code == 0
    assert data.get('error') != 'invalid_field', f'happy-path value triggered invalid_field: {data!r}'


def test_update_field_validation_smoke():
    """End-to-end CLI smoke: a malformed ``--field`` emits invalid_field TOON.

    One subprocess retained to cover the full ``manage-interface.py`` argparse
    plumbing; per-axis coverage lives in the in-process tests above.
    """
    result = run_script(
        SCRIPT_PATH,
        'update',
        '--number',
        '1',
        '--field',
        'foo/bar',
        '--value',
        'irrelevant',
    )
    assert result.returncode == 0, f'expected exit 0, got {result.returncode}\nstderr={result.stderr!r}'
    data = parse_toon_output(result.stdout)
    assert data.get('status') == 'error'
    assert data.get('error') == 'invalid_field'
