#!/usr/bin/env python3
"""6-axis identifier-validation rejection-path tests for ``profiles.py``.

In-scope flags from TASK-5: ``--module`` (the ``list`` subcommand). The
``--profile-id`` flag is OUT OF SCOPE per TASK-5 notes — it is not yet
backed by a canonical validator from ``input_validation.py``.

The 6 axes mirror the canonical fixture set established by TASK-2:

    * empty, path-separator, glob-meta, traversal, overlong (rejection)
    * happy-path (passes validator)

The ``--module`` validation chain (``add_module_arg`` type-validator ->
``parse_args_with_toon_errors`` -> ``invalid_module`` TOON) is exercised
IN-PROCESS against a minimal argparse parser that reproduces the
``profiles list`` surface. This is the exact pipeline ``profiles.py`` runs;
asserting it in-process avoids one interpreter cold-start per axis. One
subprocess smoke (``test_list_module_validation_smoke``) keeps end-to-end
CLI plumbing covered.
"""

from __future__ import annotations

import argparse
import io
import sys
from contextlib import redirect_stdout
from pathlib import Path

import pytest

# The sibling _fixtures.py lives next to this file. Make it importable
# without requiring conftest plumbing.
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
    add_module_arg,
    parse_args_with_toon_errors,
)

from conftest import get_script_path, run_script  # type: ignore[import-not-found]  # noqa: E402

SCRIPT_PATH = get_script_path('pm-dev-java', 'manage-maven-profiles', 'profiles.py')


def _validate_module_inprocess(value: str) -> tuple[int, dict]:
    """Run the ``--module`` validation chain in-process.

    Reproduces the ``profiles list --module <value>`` surface: a parser with
    ``add_module_arg`` (the ``validate_module_name`` type-validator) wrapped by
    ``parse_args_with_toon_errors`` (which maps a validator ``ValueError`` to
    the ``invalid_module`` TOON and ``sys.exit(0)``).

    Returns ``(exit_code, parsed_toon_or_empty)``. On a validator rejection the
    wrapper prints TOON and raises ``SystemExit(0)``; on a happy-path value the
    parser returns a namespace (no rejection TOON), reported as exit 0 + empty
    dict.
    """
    parser = argparse.ArgumentParser(prog='profiles', allow_abbrev=False)
    add_module_arg(parser)

    # parse_args_with_toon_errors() delegates to parser.parse_args() with no
    # explicit argv, so it reads sys.argv[1:]. Under pytest that would be
    # pytest's own argv (no --module → argparse "required" error, exit 2).
    # Set sys.argv to the surface under test for the duration of the parse.
    original_argv = sys.argv
    sys.argv = ['profiles', '--module', value]
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
    # Parsed successfully — no rejection.
    return 0, {}


@pytest.mark.parametrize('axis,bad_value', MALFORMED_AXES['module'])
def test_list_rejects_invalid_module(axis, bad_value):
    """``profiles list --module <bad>`` → ``invalid_module`` TOON (in-process)."""
    code, data = _validate_module_inprocess(bad_value)
    assert code == 0, f'identifier-validator failure must exit 0, got {code}'
    assert data.get('status') == 'error', f'expected status=error, got {data.get("status")!r}'
    assert data.get('error') == 'invalid_module', f'expected error=invalid_module, got {data.get("error")!r}'


def test_list_accepts_canonical_module():
    """Canonical ``--module`` value passes the validator (in-process).

    A happy-path value must NOT trigger ``invalid_module``.
    """
    code, data = _validate_module_inprocess(HAPPY_VALUES['module'])
    assert code == 0
    assert data.get('error') != 'invalid_module', f'happy-path value triggered invalid_module: {data!r}'


def test_list_module_validation_smoke():
    """End-to-end CLI smoke: a malformed ``--module`` emits invalid_module TOON.

    One subprocess retained to cover the full ``profiles.py`` argparse
    plumbing; per-axis coverage lives in the in-process tests above.
    """
    result = run_script(SCRIPT_PATH, 'list', '--module', 'foo/bar')
    assert result.returncode == 0, f'expected exit 0, got {result.returncode}\nstderr={result.stderr!r}'
    data = parse_toon_output(result.stdout)
    assert data.get('status') == 'error'
    assert data.get('error') == 'invalid_module'
