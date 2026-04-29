#!/usr/bin/env python3
"""6-axis canonical-identifier rejection tests for plan-retrospective scripts.

Covers all 8 retrospective scripts migrated by TASK-3. Each script uses
``add_plan_id_arg`` (most with ``required=False`` because they support
both ``--mode live`` and ``--mode archived`` invocations), and
``compile-report.py`` additionally declares ``--session-id`` via
``add_session_id_arg``.

All scripts wrap their parser via ``parse_args_with_toon_errors`` so the
canonical TOON contract applies: malformed input emits
``status: error / error: invalid_<field>`` on stdout with exit 0.

Re-uses ``test/plan-marshall/_input_validation_fixtures.py`` for the
canonical 6-axis matrix (TASK-2 foundation).
"""

from __future__ import annotations

import pytest

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from _input_validation_fixtures import (  # type: ignore[import-not-found]
    HAPPY_VALUES,
    MALFORMED_AXES,
    assert_invalid_field,
    assert_not_invalid_field,
)

from conftest import get_script_path, run_script  # type: ignore[import-not-found]

# Script registry: each entry is (script_filename, subcommand). All eight
# retrospective scripts use the ``run`` subcommand and live under
# ``plan-retrospective/scripts/``. Filenames use hyphens — get_script_path
# resolves the literal filename, no Python-import gymnastics needed.
_SCRIPTS_WITH_PLAN_ID = (
    ('analyze-logs.py', 'run'),
    ('check-artifact-consistency.py', 'run'),
    ('check-manifest-consistency.py', 'run'),
    ('collect-fragments.py', 'init'),  # collect-fragments uses init/add/finalize, not run
    ('collect-plan-artifacts.py', 'run'),
    ('compile-report.py', 'run'),
    ('direct-gh-glab-usage.py', 'run'),
    ('summarize-invariants.py', 'run'),
)


def _resolve(script: str):
    return get_script_path('plan-marshall', 'plan-retrospective', script)


# =============================================================================
# --plan-id rejection-path tests (parametrized across all 8 scripts)
# =============================================================================


@pytest.mark.parametrize('script,subcommand', _SCRIPTS_WITH_PLAN_ID)
@pytest.mark.parametrize('axis,bad_value', MALFORMED_AXES['plan_id'])
def test_plan_id_rejected(script, subcommand, axis, bad_value):
    """Every retrospective script rejects malformed --plan-id at parse time.

    The validator runs at parse time, before any plan-directory I/O, so
    we don't need to materialize a plan tree. ``--mode live`` is supplied
    where the script's argparse declares it as required; otherwise the
    bare ``--plan-id`` is enough to trigger the type-validator path.
    """
    args = [subcommand, '--plan-id', bad_value]
    # Subcommands taking --mode need it set so the failure is
    # unambiguously attributed to --plan-id (and not to a missing
    # required arg). collect-fragments uses ``init`` with required
    # ``--mode``; the seven ``run`` scripts also accept ``--mode``.
    if subcommand in ('run', 'init'):
        args += ['--mode', 'live']

    result = run_script(_resolve(script), *args)
    assert_invalid_field(result, 'invalid_plan_id')


# =============================================================================
# compile-report.py: --session-id has its own validator
# =============================================================================


@pytest.mark.parametrize('axis,bad_value', MALFORMED_AXES['session_id'])
def test_compile_report_rejects_invalid_session_id(axis, bad_value):
    """compile-report.py declares --session-id via add_session_id_arg."""
    result = run_script(
        _resolve('compile-report.py'),
        'run',
        '--plan-id',
        HAPPY_VALUES['plan_id'],
        '--mode',
        'live',
        '--session-id',
        bad_value,
    )
    assert_invalid_field(result, 'invalid_session_id')


# =============================================================================
# Happy-path: canonical inputs MUST NOT trigger the validators
# =============================================================================


@pytest.mark.parametrize('script,subcommand', _SCRIPTS_WITH_PLAN_ID)
def test_canonical_plan_id_does_not_trigger_validator(script, subcommand, tmp_path):
    """Happy-path --plan-id MUST NOT surface invalid_plan_id.

    The script will likely fail with another error (no plan dir,
    invalid mode, etc.), but it MUST NOT mis-attribute the failure to
    the canonical identifier validator.
    """
    args = [subcommand, '--plan-id', HAPPY_VALUES['plan_id']]
    if subcommand in ('run', 'init'):
        args += ['--mode', 'live']

    result = run_script(
        _resolve(script),
        *args,
        env_overrides={'PLAN_BASE_DIR': str(tmp_path)},
    )
    assert_not_invalid_field(result, 'invalid_plan_id')


def test_compile_report_canonical_session_id(tmp_path):
    """compile-report.py with canonical --session-id MUST NOT surface invalid_session_id."""
    result = run_script(
        _resolve('compile-report.py'),
        'run',
        '--plan-id',
        HAPPY_VALUES['plan_id'],
        '--mode',
        'live',
        '--session-id',
        HAPPY_VALUES['session_id'],
        env_overrides={'PLAN_BASE_DIR': str(tmp_path)},
    )
    assert_not_invalid_field(result, 'invalid_session_id')
