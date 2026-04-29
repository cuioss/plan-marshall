#!/usr/bin/env python3
"""6-axis identifier-validation rejection-path tests for ``architecture.py``.

In-scope flags from TASK-1 (architecture-specific identifier vocabulary):
``--module``, ``--name``, ``--package``, ``--domain``.

Each subprocess invocation targets a subcommand whose only required
identifier flag is the one under test. The script-CLI boundary (``main()``
+ ``parse_args_with_toon_errors``) MUST translate validator failures into
``status: error / error: invalid_<field>`` TOON on stdout with exit code
0 — the canonical ``parse_args_with_toon_errors`` contract.
"""

from __future__ import annotations

import pytest
from _input_validation_fixtures import (  # type: ignore[import-not-found]
    HAPPY_VALUES,
    MALFORMED_AXES,
    assert_invalid_field,
)

from conftest import get_script_path, run_script  # type: ignore[import-not-found]

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-architecture', 'architecture.py')


# =============================================================================
# --module (used by `module`, `commands`, `resolve`, `siblings`,
# `suggest-domains`, plus several `enrich` subcommands)
# =============================================================================


@pytest.mark.parametrize('axis,bad_value', MALFORMED_AXES['module'])
def test_module_subcommand_rejects_invalid_module(axis, bad_value):
    """``architecture module --module <bad>`` produces invalid_module TOON."""
    result = run_script(SCRIPT_PATH, 'module', '--module', bad_value)
    assert_invalid_field(result, 'invalid_module')


def test_module_subcommand_accepts_canonical_module():
    """Canonical ``--module`` value passes the validator (may still fail
    downstream, but never with ``invalid_module``)."""
    result = run_script(SCRIPT_PATH, 'module', '--module', HAPPY_VALUES['module'])
    assert result.returncode == 0
    if result.stdout.strip():
        from toon_parser import parse_toon  # type: ignore[import-not-found]

        data = parse_toon(result.stdout)
        assert data.get('error') != 'invalid_module'


# =============================================================================
# --name (used by `enrich module --name`)
# =============================================================================


@pytest.mark.parametrize('axis,bad_value', MALFORMED_AXES['name'])
def test_enrich_module_rejects_invalid_name(axis, bad_value):
    """``architecture enrich module --name <bad> --responsibility ...`` rejects."""
    result = run_script(
        SCRIPT_PATH,
        'enrich',
        'module',
        '--name',
        bad_value,
        '--responsibility',
        'desc',
    )
    assert_invalid_field(result, 'invalid_name')


# =============================================================================
# --package (used by `enrich package`)
# =============================================================================


@pytest.mark.parametrize('axis,bad_value', MALFORMED_AXES['package'])
def test_enrich_package_rejects_invalid_package(axis, bad_value):
    """``architecture enrich package --package <bad> ...`` rejects with invalid_package."""
    result = run_script(
        SCRIPT_PATH,
        'enrich',
        'package',
        '--module',
        HAPPY_VALUES['module'],
        '--package',
        bad_value,
        '--description',
        'desc',
    )
    assert_invalid_field(result, 'invalid_package')


# =============================================================================
# --domain (used by `enrich add-domain`)
# =============================================================================


@pytest.mark.parametrize('axis,bad_value', MALFORMED_AXES['domain'])
def test_enrich_add_domain_rejects_invalid_domain(axis, bad_value):
    """``architecture enrich add-domain --domain <bad> ...`` rejects with invalid_domain."""
    result = run_script(
        SCRIPT_PATH,
        'enrich',
        'add-domain',
        '--module',
        HAPPY_VALUES['module'],
        '--domain',
        bad_value,
        '--rationale',
        'why',
    )
    assert_invalid_field(result, 'invalid_domain')
