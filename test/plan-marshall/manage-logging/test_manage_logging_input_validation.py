#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""6-axis identifier-validation rejection-path tests for ``manage-logging.py``.

In-scope flags from TASK-1: ``--plan-id``, ``--phase``.

The CLI rejection tests below are complemented by the ``get_log_path``
containment tests at the bottom of this module: the CLI is only one of the
entry points that turns a caller-supplied ``plan_id`` into a log file path, so
the shared path resolver carries its own guard and its own tests.
"""

from __future__ import annotations

import plan_logging
import pytest
from _input_validation_fixtures import (
    HAPPY_VALUES,
    MALFORMED_AXES,
    assert_invalid_field,
    assert_plan_id_axis_rejected,
)
from input_validation import NO_PLAN_SENTINEL

from conftest import get_script_path, run_script

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-logging', 'manage-logging.py')


# =============================================================================
# --plan-id (work / decision / script / separator / read)
# =============================================================================


@pytest.mark.parametrize('axis,bad_value', MALFORMED_AXES['plan_id'])
def test_work_rejects_invalid_plan_id(axis, bad_value):
    """``manage-logging work --plan-id <bad> --level INFO --message m`` → invalid_plan_id TOON."""
    assert_plan_id_axis_rejected(
        SCRIPT_PATH, 'work', bad_value, extra_args=('--level', 'INFO', '--message', 'msg')
    )


@pytest.mark.parametrize('axis,bad_value', MALFORMED_AXES['plan_id'])
def test_read_rejects_invalid_plan_id(axis, bad_value):
    """``manage-logging read --plan-id <bad> --type work`` → invalid_plan_id TOON."""
    assert_plan_id_axis_rejected(SCRIPT_PATH, 'read', bad_value, extra_args=('--type', 'work'))


# =============================================================================
# --phase (read --phase)
# =============================================================================


def test_read_rejects_invalid_phase():
    """``manage-logging read --plan-id <ok> --type work --phase <bad>`` → invalid_phase TOON."""
    result = run_script(
        SCRIPT_PATH,
        'read',
        '--plan-id',
        HAPPY_VALUES['plan_id'],
        '--type',
        'work',
        '--phase',
        'unknown-phase',
    )
    assert_invalid_field(result, 'invalid_phase')


# =============================================================================
# get_log_path — shared plan_id containment point (Python API, not the CLI)
# =============================================================================

#: Malformed plan ids whose entire point is that they would escape the plan
#: tree if they ever reached path resolution. ``get_store_dir('plans', …)``
#: joins its entry id straight onto the base dir with no traversal check, so
#: ``get_log_path`` is the one place a client-supplied identifier is contained.
_ESCAPING_PLAN_IDS = ('../../etc', '/tmp/evil', 'a/b')


class TestGetLogPathPlanIdContainment:
    """``get_log_path`` guards ``plan_id`` for every entry point that resolves a log path."""

    @pytest.fixture
    def plan_base(self, tmp_path, monkeypatch):
        """Redirect ``PLAN_BASE_DIR`` at a base dir this test knows the path of.

        The autouse ``_plan_base_dir_sandbox`` already isolates every test, but
        its sandbox path is not exposed; a test that asserts *where* the resolved
        log lands needs a base dir of its own.
        """
        monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
        return tmp_path

    @pytest.mark.parametrize('bad_plan_id', _ESCAPING_PLAN_IDS)
    def test_rejects_a_plan_id_that_would_escape_the_plan_tree(self, bad_plan_id):
        """A traversal / absolute / separator-bearing plan_id raises before any path is built."""
        with pytest.raises(ValueError) as excinfo:
            plan_logging.get_log_path(bad_plan_id, 'work')

        assert 'invalid plan_id' in str(excinfo.value), (
            f'guard must name the rejected identifier, got: {excinfo.value}'
        )

    def test_none_plan_id_still_resolves_to_the_global_log(self, plan_base):
        """No-regression guard: the legitimate global-fallback path is unaffected."""
        path = plan_logging.get_log_path(None, 'work')

        assert path.parent == plan_base / 'logs', f'expected the global log dir, got {path}'
        assert path.name.startswith('work-'), f'expected a dated global work log, got {path.name}'
        assert path.suffix == '.log', f'expected a .log file, got {path.name}'

    def test_no_plan_sentinel_still_resolves(self, plan_base):
        """The NO_PLAN sentinel is carved out by validate_plan_id, so it survives the guard."""
        path = plan_logging.get_log_path(NO_PLAN_SENTINEL, 'work')

        assert path.parent == plan_base / 'logs', f'expected the global log dir, got {path}'
        assert path.name.startswith('work-'), f'expected a dated global work log, got {path.name}'

    def test_log_entry_drops_a_malformed_plan_id_without_raising_or_writing(self, tmp_path, monkeypatch):
        """End-to-end: the best-effort writer drops the entry — it does not fall back to global."""
        plan_base = tmp_path / 'base'
        plan_base.mkdir()
        monkeypatch.setenv('PLAN_BASE_DIR', str(plan_base))

        plan_logging.log_entry('work', '../../evil', 'INFO', 'msg')

        assert [p.name for p in tmp_path.iterdir()] == ['base'], (
            f'a malformed plan_id created a path outside PLAN_BASE_DIR: {list(tmp_path.iterdir())}'
        )
        assert list(plan_base.rglob('*.log')) == [], (
            'the entry must be dropped, not written to the global log'
        )
