#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""6-axis canonical-identifier rejection tests for plan-retrospective scripts.

Covers all 8 retrospective scripts migrated by TASK-3. Each script uses
``add_plan_id_arg`` (most with ``required=False`` because they support
both ``--mode live`` and ``--mode archived`` invocations), and
``compile-report.py`` additionally declares ``--session-id`` via
``add_session_id_arg``.

All scripts wrap their parser via ``parse_args_with_toon_errors`` so the
canonical TOON contract applies: malformed input emits
``status: error / error: invalid_<field>`` on stdout with exit 0.

Re-uses ``test/plan-marshall/_pm_input_validation_fixtures.py`` for the
canonical 6-axis matrix (TASK-2 foundation).
"""

from __future__ import annotations

import pytest

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from _pm_input_validation_fixtures import (  # type: ignore[import-not-found]
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


# =============================================================================
# Cross-cutting OSError fail-closed regression (D1 verdict-path guard)
# =============================================================================
#
# The two gate-verb scripts — check-artifact-consistency.py and
# check-manifest-consistency.py — perform live filesystem reads of plan
# artifacts that passed an .exists() probe. A path that passes .exists() but
# raises OSError on read_text() (permission denied, the path resolving to a
# directory, a mid-read deletion race) MUST be caught at the I/O boundary so
# the gate verb fails closed (a structured verdict) rather than propagating an
# uncaught OSError that crashes the verdict path.
#
# This is the cross-cutting end-to-end sentinel for the D1 OSError guards
# added to both scripts. It exercises the real verdict path through the
# executor-style subprocess runner (not an importlib unit). Reverting any D1
# guard turns this red: the uncaught OSError surfaces as an `internal_error`
# TOON with a non-zero exit, which both assertions below reject.

from _plan_retrospective_fixtures import build_happy_plan_dir  # type: ignore[import-not-found]  # noqa: E402


def _make_dir_at(path) -> None:
    """Replace ``path`` with a directory of the same name.

    Portable OSError injection: ``Path.exists()`` returns ``True`` for a
    directory while ``Path.read_text()`` raises ``IsADirectoryError`` (an
    ``OSError`` subclass). Needs no permission bits and behaves identically for
    root and non-root test runners.
    """
    if path.exists():
        path.unlink()
    path.mkdir()


def _build_live_plan(tmp_path):
    """Materialize a happy-path live plan under ``tmp_path`` and return its dir."""
    base = tmp_path / 'base'
    base.mkdir()
    plan_dir = base / 'plans' / 'oserror-verdict'
    build_happy_plan_dir(plan_dir)
    return base, plan_dir


def test_artifact_consistency_verdict_path_fails_closed_on_oserror(tmp_path):
    """check-artifact-consistency.py fails closed when solution_outline.md is unreadable.

    End-to-end regression for the D1 guard on the artifact gate verb. With
    ``solution_outline.md`` replaced by a directory, the script must still exit
    cleanly with ``status: success`` and a FAIL ``solution_outline_present``
    check — never an ``internal_error`` crash. Reverting the D1 OSError wrap
    flips this red.
    """
    base, plan_dir = _build_live_plan(tmp_path)
    _make_dir_at(plan_dir / 'solution_outline.md')

    result = run_script(
        _resolve('check-artifact-consistency.py'),
        'run',
        '--plan-id',
        'oserror-verdict',
        '--mode',
        'live',
        env_overrides={'PLAN_BASE_DIR': str(base)},
    )
    assert result.success, result.stderr
    data = result.toon()
    assert data['status'] == 'success'
    assert data.get('error') != 'internal_error'
    present = next((c for c in data['checks'] if c.get('name') == 'solution_outline_present'), None)
    assert present is not None
    assert present['status'] == 'fail'
    assert 'read_failed' in present['message']


def test_manifest_consistency_verdict_path_fails_closed_on_oserror(tmp_path):
    """check-manifest-consistency.py fails closed when execution.toon is unreadable.

    End-to-end regression for the D1 guard on the manifest gate verb. With
    ``execution.toon`` replaced by a directory, ``load_manifest`` degrades to
    the missing-manifest skip sentinel rather than crashing — the script exits
    cleanly with ``status: skipped`` / ``manifest_present: False`` and no
    ``internal_error`` code. Reverting the D1 OSError wrap flips this red.
    """
    base, plan_dir = _build_live_plan(tmp_path)
    # A real manifest exists (so the path is not the missing-manifest branch),
    # then is turned into a directory to inject the read OSError.
    (plan_dir / 'execution.toon').write_text(
        'manifest_version: 1\nplan_id: oserror-verdict\n',
        encoding='utf-8',
    )
    _make_dir_at(plan_dir / 'execution.toon')

    result = run_script(
        _resolve('check-manifest-consistency.py'),
        'run',
        '--plan-id',
        'oserror-verdict',
        '--mode',
        'live',
        env_overrides={'PLAN_BASE_DIR': str(base)},
    )
    assert result.success, result.stderr
    data = result.toon()
    assert data['status'] == 'skipped'
    assert data['manifest_present'] is False
    assert data.get('error') != 'internal_error'
