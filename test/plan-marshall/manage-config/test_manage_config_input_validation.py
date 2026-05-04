#!/usr/bin/env python3
"""6-axis identifier-validation rejection-path tests for ``manage-config.py``.

In-scope flags from TASK-1: ``--field``, ``--domain``.

The script-CLI boundary translates argparse type-validator failures into
``status: error / error: invalid_<field>`` TOON on stdout (exit 0).
"""

from __future__ import annotations

import pytest
from _input_validation_fixtures import (  # type: ignore[import-not-found]
    HAPPY_VALUES,
    MALFORMED_AXES,
    assert_invalid_field,
)

from conftest import get_script_path, run_script  # type: ignore[import-not-found]

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-config', 'manage-config.py')


# =============================================================================
# --domain (skill-domains get)
# =============================================================================


@pytest.mark.parametrize('axis,bad_value', MALFORMED_AXES['domain'])
def test_skill_domains_get_rejects_invalid_domain(axis, bad_value):
    """``manage-config skill-domains get --domain <bad>`` → invalid_domain TOON."""
    result = run_script(SCRIPT_PATH, 'skill-domains', 'get', '--domain', bad_value)
    assert_invalid_field(result, 'invalid_domain')


# =============================================================================
# --field (plan {phase} get --field, retention set --field, etc.)
# =============================================================================


@pytest.mark.parametrize('axis,bad_value', MALFORMED_AXES['field'])
def test_plan_phase_get_rejects_invalid_field(axis, bad_value):
    """``manage-config plan phase-1-init get --field <bad>`` → invalid_field TOON."""
    result = run_script(SCRIPT_PATH, 'plan', 'phase-1-init', 'get', '--field', bad_value)
    assert_invalid_field(result, 'invalid_field')


def test_skill_domains_get_accepts_canonical_domain():
    """Canonical ``--domain`` value passes validator (downstream may still error)."""
    result = run_script(SCRIPT_PATH, 'skill-domains', 'get', '--domain', HAPPY_VALUES['domain'])
    assert result.returncode == 0
    if result.stdout.strip():
        from toon_parser import parse_toon  # type: ignore[import-not-found]

        data = parse_toon(result.stdout)
        assert data.get('error') != 'invalid_domain'
