#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the report of the ``cleanup restart-check`` verb: shape, floor, boundaries.

Exercises the readiness seam against a SCAFFOLDED FIXTURE EPIC under
``PLAN_BASE_DIR`` isolation — never the live ``truthful-signals`` tree.

The verb's whole value is that it refuses to state a confident verdict it cannot
support. This module covers the report as a whole:

- **Shape** — every signal row carries a verdict, an evidence field, and the
  population it was derived from, and the report carries the sample instant
  beside the verdict. A row missing any of the four is a bare score.
- **Floor** — the overall verdict is the floor over every row. One
  ``indeterminate`` among otherwise-``ready`` rows floors the report, and a
  ``not_ready`` row floors it further.
- **Boundaries** — the verb writes nothing, and the CLI reports the same shape.

The per-signal matched controls, the git seam's read-only contract and the
``registry_parity`` arm each have a module of their own beside this one; the
fixture builders all of them share live in ``_restart_check_fixtures``.
"""

import pytest
from _restart_check_fixtures import (
    _RESTART_CHECK_ARGS,
    CLEAN_SHA,
    INDETERMINATE,
    NOT_READY,
    OWNED_SIGNALS,
    READINESS_ORDER,
    READY,
    SCRIPT_PATH,
    SLUG,
    _epic_dir,
    _git_stub,
    _make_inbox,
    _orch,
    _ready_epic,
    _row,
    _run,
    _signal_row,
    _variant,
    _verdicts,
    _write_spec,
    _write_status,
    cmd_cleanup_restart_check,
    install_parity_stores,
    write_registry,
)

from conftest import run_script

readiness_floor = _orch._readiness_floor


@pytest.fixture(autouse=True)
def parity_stores(tmp_path, monkeypatch):
    """Point the parity arm of every test at fixture stores that are in parity."""
    return install_parity_stores(tmp_path, monkeypatch)


# =============================================================================
# Report shape — no bare scores, and the sample instant rides the verdict
# =============================================================================


class TestRestartCheckShape:
    def test_should_return_one_row_per_signal(self, plan_context, monkeypatch):
        """Non-empty-population guard: the signal roster must materialize."""
        _ready_epic(plan_context, monkeypatch)

        result = _run()

        assert result['status'] == 'success'
        assert result['operation'] == 'cleanup-restart-check'
        assert sorted(row['signal'] for row in result['signals']) == sorted(OWNED_SIGNALS)
        assert result['signals_total'] == len(result['signals']) == len(OWNED_SIGNALS)

    def test_every_signal_carries_a_verdict_evidence_and_a_population(self, plan_context, monkeypatch):
        _ready_epic(plan_context, monkeypatch)

        result = _run()

        for row in result['signals']:
            assert set(row) == {'signal', 'verdict', 'evidence', 'population'}
            assert row['verdict'], f'{row["signal"]} carries no verdict'
            assert row['evidence'].strip(), f'{row["signal"]} carries no evidence'
            assert row['population'].strip(), f'{row["signal"]} carries no population'

    def test_each_population_names_what_it_counted(self, plan_context, monkeypatch):
        # A population is only useful if it names the set — a bare integer would
        # be another unattributed number.
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')
        _make_inbox(plan_context, queued=0, archived=3)
        monkeypatch.setattr(_orch, '_git_read', _git_stub())

        result = _run()

        assert 'queue rows: 1 row(s) scanned and 0 unreadable' == _signal_row(result, 'running_plans')['population']
        assert '1 queue row(s) and 1 spec file(s)' == _signal_row(result, 'corpus_reconciliation')['population']
        assert 'inbox/: 0 live of 0 total and 0 closed and 0 invalid' == _signal_row(result, 'inbox')['population']
        assert CLEAN_SHA in _signal_row(result, 'worktree')['population']

    def test_should_carry_the_sample_instant_beside_the_verdict(self, plan_context, monkeypatch):
        _ready_epic(plan_context, monkeypatch)

        result = _run()

        assert result['sampled_at'].endswith('Z')
        assert result['verdict'] in READINESS_ORDER

    def test_should_score_every_signal(self, plan_context, monkeypatch):
        # No row sits outside the floor: the scored count is the total.
        _ready_epic(plan_context, monkeypatch)

        result = _run()

        assert result['signals_total'] == len(OWNED_SIGNALS)
        assert result['signals_scored'] == result['signals_total']
        assert {row['verdict'] for row in result['signals']} <= set(READINESS_ORDER)

    def test_should_error_when_the_epic_has_no_store_tree(self, plan_context):
        result = cmd_cleanup_restart_check(_variant(_RESTART_CHECK_ARGS, slug='absent-restart-epic'))

        assert result['status'] == 'error'
        assert result['error'] == 'not_found'

    def test_should_reject_invalid_slug(self, plan_context):
        result = cmd_cleanup_restart_check(_variant(_RESTART_CHECK_ARGS, slug='../evil'))

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_slug'


# =============================================================================
# The floor
# =============================================================================


class TestReadinessFloor:
    def test_every_ready_signal_yields_a_ready_report(self, plan_context, monkeypatch):
        # The matched control for the two degraded floors below: nothing is
        # degraded, so the report is ready.
        _ready_epic(plan_context, monkeypatch)

        result = _run()

        assert set(_verdicts(result).values()) == {READY}
        assert result['verdict'] == READY

    def test_one_indeterminate_signal_floors_an_otherwise_ready_report(self, plan_context, monkeypatch):
        # Exactly one signal is degraded — the absent inbox/ — and it is the
        # unobservable kind, so the report may not claim ready.
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')
        monkeypatch.setattr(_orch, '_git_read', _git_stub())

        result = _run()

        verdicts = _verdicts(result)
        assert verdicts['inbox'] == INDETERMINATE
        assert {verdicts[name] for name in OWNED_SIGNALS if name != 'inbox'} == {READY}
        assert result['verdict'] == INDETERMINATE

    def test_a_not_ready_signal_floors_below_an_indeterminate_one(self, plan_context, monkeypatch):
        # Both degraded kinds are present at once; the definite hazard wins.
        _write_status(plan_context, [_row('PLAN-01', status='running')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')
        monkeypatch.setattr(_orch, '_git_read', _git_stub())

        result = _run()

        verdicts = _verdicts(result)
        assert verdicts['running_plans'] == NOT_READY
        assert verdicts['inbox'] == INDETERMINATE
        assert result['verdict'] == NOT_READY

    def test_the_floor_over_no_participating_signal_is_indeterminate(self):
        # Nothing observed is not the same as everything fine.
        assert readiness_floor([]) == INDETERMINATE

    def test_the_floor_is_the_worst_participating_verdict(self):
        assert readiness_floor([READY, READY]) == READY
        assert readiness_floor([READY, INDETERMINATE]) == INDETERMINATE
        assert readiness_floor([READY, INDETERMINATE, NOT_READY]) == NOT_READY


# =============================================================================
# Read-only boundary
# =============================================================================


class TestRestartCheckReadOnlyBoundary:
    def test_restart_check_leaves_the_fixture_tree_byte_identical(self, plan_context, monkeypatch):
        _ready_epic(plan_context, monkeypatch)
        root = _epic_dir(plan_context)
        before = {path: path.read_bytes() for path in sorted(root.rglob('*')) if path.is_file()}
        assert before, 'fixture tree did not materialize'

        result = _run()

        after = {path: path.read_bytes() for path in sorted(root.rglob('*')) if path.is_file()}
        assert after == before
        assert result['status'] == 'success'

    def test_restart_check_leaves_the_parity_stores_byte_identical(self, plan_context, monkeypatch, parity_stores):
        # The parity arm reads another component's registry; it must not write it.
        _ready_epic(plan_context, monkeypatch)
        paths = (parity_stores.registry, parity_stores.executor)
        before = {path: path.read_bytes() for path in paths}
        cache_before = sorted(parity_stores.cache_root.rglob('*'))

        _run()

        assert {path: path.read_bytes() for path in paths} == before
        assert sorted(parity_stores.cache_root.rglob('*')) == cache_before


# =============================================================================
# CLI boundary (constructed argv at the subprocess boundary)
# =============================================================================


class TestRestartCheckCli:
    def test_should_report_through_cli(self, plan_context, parity_stores):
        # The subprocess observes the REAL repository through the git seam, so
        # the assertions here are structural: the overall verdict legitimately
        # varies with the host tree and is asserted in-process instead.
        #
        # A subprocess cannot inherit the in-process redirection of the parity
        # stores, so it is given the fixture home directory instead. The fixture
        # registry is rewritten to hold no plan-marshall entry: the row's
        # evidence then proves the subprocess read THAT registry, through the
        # reader's own home-relative location, and not the operator's.
        env = {'PLAN_BASE_DIR': str(plan_context.fixture_dir), 'HOME': str(parity_stores.home)}
        write_registry(parity_stores, {})
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')
        _make_inbox(plan_context)

        result = run_script(SCRIPT_PATH, 'cleanup', 'restart-check', '--slug', SLUG, env_overrides=env)

        assert result.returncode == 0
        assert 'status: success' in result.stdout
        assert 'operation: cleanup-restart-check' in result.stdout
        assert f'signals_total: {len(OWNED_SIGNALS)}' in result.stdout
        assert f'signals_scored: {len(OWNED_SIGNALS)}' in result.stdout
        assert 'registry_parity' in result.stdout
        assert 'plan-marshall is not installed through the plugin registry' in result.stdout
