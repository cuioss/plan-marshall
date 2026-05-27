#!/usr/bin/env python3
# ruff: noqa: I001, E402, F811
"""Tests for phase_handshake phase_steps_complete invariant.

Split from test_phase_handshake.py: covers the required-steps parser /
resolver, the _capture_phase_steps_complete invariant, and its integration
through cmd_capture / cmd_verify.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from _handshake_fixtures import (
    _ns,
    _write_required_steps,
    cmds,
    inv,
    store,
    # Fixtures (imported so pytest can resolve them):
    only_phase_steps_invariant,  # noqa: F401
    required_steps_path,  # noqa: F401
    stub_metadata,  # noqa: F401
)


# --- parser ---------------------------------------------------------------


def test_parse_required_steps_bullet_format(tmp_path: Path) -> None:
    f = tmp_path / 'required-steps.md'
    _write_required_steps(
        f,
        '# Required steps\n\n- commit-push\n- create-pr\n- record-metrics\n',
    )
    assert inv._parse_required_steps(f) == ['commit-push', 'create-pr', 'record-metrics']


def test_parse_required_steps_ignores_blank_and_comments(tmp_path: Path) -> None:
    f = tmp_path / 'required-steps.md'
    _write_required_steps(
        f,
        '\n# Header line\n\nSome prose description.\n\n- one\n\n- two\n\nAnother paragraph.\n- three\n',
    )
    assert inv._parse_required_steps(f) == ['one', 'two', 'three']


def test_parse_required_steps_strips_inline_code(tmp_path: Path) -> None:
    f = tmp_path / 'required-steps.md'
    _write_required_steps(f, '- `commit-push`\n- `create-pr`\n')
    assert inv._parse_required_steps(f) == ['commit-push', 'create-pr']


def test_parse_required_steps_empty_file(tmp_path: Path) -> None:
    f = tmp_path / 'required-steps.md'
    _write_required_steps(f, '')
    assert inv._parse_required_steps(f) == []


def test_parse_required_steps_no_bullets(tmp_path: Path) -> None:
    f = tmp_path / 'required-steps.md'
    _write_required_steps(f, '# Title\n\nJust prose, no bullet list at all.\n')
    assert inv._parse_required_steps(f) == []


def test_parse_required_steps_missing_file_returns_empty(tmp_path: Path) -> None:
    f = tmp_path / 'does-not-exist.md'
    assert inv._parse_required_steps(f) == []


# --- resolver -------------------------------------------------------------


def test_resolve_required_steps_path_exists(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    bundles = tmp_path / 'bundles'
    target = bundles / 'plan-marshall' / 'skills' / 'phase-6-finalize' / 'standards' / 'required-steps.md'
    _write_required_steps(target, '- commit-push\n')
    monkeypatch.setattr(inv, 'find_marketplace_path', lambda: bundles)
    resolved = inv._resolve_required_steps_path('6-finalize')
    assert resolved == target


def test_resolve_required_steps_path_missing_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    bundles = tmp_path / 'bundles'
    (bundles / 'plan-marshall' / 'skills' / 'phase-9-ghost' / 'standards').mkdir(parents=True)
    monkeypatch.setattr(inv, 'find_marketplace_path', lambda: bundles)
    assert inv._resolve_required_steps_path('9-ghost') is None


def test_resolve_required_steps_path_no_marketplace(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(inv, 'find_marketplace_path', lambda: None)
    assert inv._resolve_required_steps_path('6-finalize') is None


# --- capture --------------------------------------------------------------


def test_capture_phase_steps_all_done(required_steps_path: Path) -> None:
    metadata = {
        'phase_steps': {
            '5-execute': {
                'step-a': {'outcome': 'done', 'display_detail': None},
                'step-b': {'outcome': 'done', 'display_detail': None},
            }
        }
    }
    result = inv._capture_phase_steps_complete('pid', metadata, '5-execute')
    assert isinstance(result, str)
    assert len(result) == 16


def test_capture_phase_steps_missing_step(required_steps_path: Path) -> None:
    metadata = {'phase_steps': {'5-execute': {'step-a': {'outcome': 'done', 'display_detail': None}}}}
    with pytest.raises(inv.PhaseStepsIncomplete) as excinfo:
        inv._capture_phase_steps_complete('pid', metadata, '5-execute')
    assert excinfo.value.missing == ['step-b']
    assert excinfo.value.not_done == []
    assert excinfo.value.legacy_format == []


def test_capture_phase_steps_skipped_fails(required_steps_path: Path) -> None:
    metadata = {
        'phase_steps': {
            '5-execute': {
                'step-a': {'outcome': 'done', 'display_detail': None},
                'step-b': {'outcome': 'skipped', 'display_detail': None},
            }
        }
    }
    with pytest.raises(inv.PhaseStepsIncomplete) as excinfo:
        inv._capture_phase_steps_complete('pid', metadata, '5-execute')
    assert excinfo.value.missing == []
    assert excinfo.value.not_done == [{'step': 'step-b', 'outcome': 'skipped'}]
    assert excinfo.value.legacy_format == []


def test_capture_phase_steps_legacy_bare_string_fails(required_steps_path: Path) -> None:
    metadata = {
        'phase_steps': {
            '5-execute': {
                'step-a': 'done',
                'step-b': {'outcome': 'done', 'display_detail': None},
            }
        }
    }
    with pytest.raises(inv.PhaseStepsIncomplete) as excinfo:
        inv._capture_phase_steps_complete('pid', metadata, '5-execute')
    assert excinfo.value.legacy_format == ['step-a']
    assert excinfo.value.missing == []
    assert excinfo.value.not_done == []


def test_capture_phase_steps_no_required_file_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(inv, '_resolve_required_steps_path', lambda _p: None)
    result = inv._capture_phase_steps_complete('pid', {}, '5-execute')
    assert result is None


def test_capture_phase_steps_empty_required_file_returns_none(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    f = tmp_path / 'required-steps.md'
    _write_required_steps(f, '# Only prose, no bullets\n')
    monkeypatch.setattr(inv, '_resolve_required_steps_path', lambda _p: f)
    result = inv._capture_phase_steps_complete('pid', {}, '5-execute')
    assert result is None


def test_capture_phase_steps_no_phase_entry(required_steps_path: Path) -> None:
    metadata = {'phase_steps': {}}
    with pytest.raises(inv.PhaseStepsIncomplete) as excinfo:
        inv._capture_phase_steps_complete('pid', metadata, '5-execute')
    assert set(excinfo.value.missing) == {'step-a', 'step-b'}


# --- cmd_capture / cmd_verify integration --------------------------------


def test_cmd_capture_phase_steps_success(
    plan_context, only_phase_steps_invariant, stub_metadata, required_steps_path: Path
) -> None:
    stub_metadata['phase_steps'] = {
        '5-execute': {
            'step-a': {'outcome': 'done', 'display_detail': None},
            'step-b': {'outcome': 'done', 'display_detail': None},
        }
    }
    result = cmds.cmd_capture(_ns(plan_id='psc-ok', phase='5-execute'))
    assert result['status'] == 'success'
    assert 'phase_steps_complete' in result['invariants']
    row = store.get_row('psc-ok', '5-execute')
    assert row is not None
    assert row['phase_steps_complete'] != ''


def test_cmd_capture_phase_steps_incomplete_returns_error(
    plan_context, only_phase_steps_invariant, stub_metadata, required_steps_path: Path
) -> None:
    stub_metadata['phase_steps'] = {'5-execute': {'step-a': {'outcome': 'done', 'display_detail': None}}}
    result = cmds.cmd_capture(_ns(plan_id='psc-fail', phase='5-execute'))
    assert result['status'] == 'error'
    assert result['error'] == 'phase_steps_incomplete'
    assert result['missing'] == ['step-b']
    assert store.get_row('psc-fail', '5-execute') is None


def test_cmd_capture_phase_steps_skipped_returns_error(
    plan_context, only_phase_steps_invariant, stub_metadata, required_steps_path: Path
) -> None:
    stub_metadata['phase_steps'] = {
        '5-execute': {
            'step-a': {'outcome': 'done', 'display_detail': None},
            'step-b': {'outcome': 'skipped', 'display_detail': None},
        }
    }
    result = cmds.cmd_capture(_ns(plan_id='psc-skip', phase='5-execute'))
    assert result['status'] == 'error'
    assert result['error'] == 'phase_steps_incomplete'
    assert result['not_done'] == [{'step': 'step-b', 'outcome': 'skipped'}]
    assert store.get_row('psc-skip', '5-execute') is None


def test_cmd_capture_phase_steps_legacy_returns_error(
    plan_context, only_phase_steps_invariant, stub_metadata, required_steps_path: Path
) -> None:
    stub_metadata['phase_steps'] = {
        '5-execute': {
            'step-a': 'done',
            'step-b': {'outcome': 'done', 'display_detail': None},
        }
    }
    result = cmds.cmd_capture(_ns(plan_id='psc-legacy', phase='5-execute'))
    assert result['status'] == 'error'
    assert result['error'] == 'phase_steps_incomplete'
    assert result['legacy_format'] == ['step-a']
    assert store.get_row('psc-legacy', '5-execute') is None


def test_cmd_verify_phase_steps_drift_when_step_regresses(
    plan_context, only_phase_steps_invariant, stub_metadata, required_steps_path: Path
) -> None:
    stub_metadata['phase_steps'] = {
        '5-execute': {
            'step-a': {'outcome': 'done', 'display_detail': None},
            'step-b': {'outcome': 'done', 'display_detail': None},
        }
    }
    cap = cmds.cmd_capture(_ns(plan_id='psc-drift', phase='5-execute'))
    assert cap['status'] == 'success'
    stub_metadata['phase_steps'] = {
        '5-execute': {
            'step-a': {'outcome': 'done', 'display_detail': None},
            'step-b': {'outcome': 'skipped', 'display_detail': None},
        }
    }
    result = cmds.cmd_verify(_ns(plan_id='psc-drift', phase='5-execute'))
    assert result['status'] == 'drift'
    diff_names = {d['invariant'] for d in result['diffs']}
    assert 'phase_steps_complete' in diff_names
