#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""In-process tests for the manage-status.py CLI dispatcher (``main``)."""


import json

from _manage_status_main_dispatch_fixtures import _PHASES, _parse, _run

# =============================================================================
# create -> read roundtrip through the dispatcher
# =============================================================================


def test_main_create_then_read_roundtrip(plan_context, monkeypatch, capsys):
    """create then read dispatch successfully and round-trip the plan title."""
    # Arrange / Act: create
    code, out, _ = _run(
        monkeypatch, capsys, ['create', '--plan-id', 'ms-disp-rt', '--title', 'Dispatch RT', '--phases', _PHASES]
    )
    # Assert: create succeeded with exit 0
    assert code == 0
    assert _parse(out)['status'] == 'success'

    # Act: read the just-created plan
    code, out, _ = _run(monkeypatch, capsys, ['read', '--plan-id', 'ms-disp-rt'])

    # Assert: read returns the persisted title
    assert code == 0
    data = _parse(out)
    assert data['status'] == 'success'
    # cmd_read nests the persisted status under the 'plan' key.
    assert data['plan']['title'] == 'Dispatch RT'


def test_main_list_returns_success(plan_context, monkeypatch, capsys):
    """The ``list`` subcommand dispatches and reports success on an empty store."""
    code, out, _ = _run(monkeypatch, capsys, ['list'])

    assert code == 0
    assert 'status: success' in out


# =============================================================================
# route / self-test (no plan required)
# =============================================================================


def test_main_route_returns_skill_for_known_phase(plan_context, monkeypatch, capsys):
    """``route --phase 1-init`` returns the routed skill for that phase."""
    code, out, _ = _run(monkeypatch, capsys, ['route', '--phase', '1-init'])

    assert code == 0
    data = _parse(out)
    assert data['status'] == 'success'
    assert data['phase'] == '1-init'
    assert data['skill']  # a non-empty skill notation is routed


def test_main_route_unknown_phase_reports_error(plan_context, monkeypatch, capsys):
    """An unroutable phase yields a status: error TOON but still exits 0."""
    code, out, _ = _run(monkeypatch, capsys, ['route', '--phase', '99-bogus'])

    assert code == 0
    data = _parse(out)
    assert data['status'] == 'error'
    assert data['error'] == 'invalid_phase'


def test_main_self_test_passes(plan_context, monkeypatch, capsys):
    """``self-test`` dispatches and reports all internal health checks passing."""
    code, out, _ = _run(monkeypatch, capsys, ['self-test'])

    assert code == 0
    data = _parse(out)
    assert data['status'] == 'success'
    assert int(data['failed']) == 0
    assert int(data['passed']) >= 1


# =============================================================================
# metadata / title-token / update-phase / progress
# =============================================================================


def test_main_metadata_set_then_get(plan_context, monkeypatch, capsys):
    """metadata --set persists a field that metadata --get reads back."""
    _run(monkeypatch, capsys, ['create', '--plan-id', 'ms-disp-md', '--title', 'MD', '--phases', _PHASES])

    code, out, _ = _run(
        monkeypatch, capsys, ['metadata', '--plan-id', 'ms-disp-md', '--set', '--field', 'change_type', '--value', 'feature']
    )
    assert code == 0
    assert _parse(out)['status'] == 'success'

    code, out, _ = _run(
        monkeypatch, capsys, ['metadata', '--plan-id', 'ms-disp-md', '--get', '--field', 'change_type']
    )
    assert code == 0
    data = _parse(out)
    assert data['status'] == 'success'
    assert data['value'] == 'feature'


def test_main_title_token_set_then_clear(plan_context, monkeypatch, capsys):
    """title-token set persists the structured record through the real CLI
    dispatch; the matching owner-scoped clear removes it.

    The round trip is driven through ``main`` so the argparse surface (including
    the ``--owner`` flag on BOTH verbs) is exercised, not just the command body.
    """
    _run(monkeypatch, capsys, ['create', '--plan-id', 'ms-disp-tt', '--title', 'TT', '--phases', _PHASES])

    code, out, _ = _run(
        monkeypatch,
        capsys,
        [
            'title-token', 'set', '--plan-id', 'ms-disp-tt',
            '--state', 'build-busy', '--owner', 'build-hook',
        ],
    )
    assert code == 0
    status_file = plan_context.plan_dir_for('ms-disp-tt') / 'status.json'
    stored = json.loads(status_file.read_text(encoding='utf-8'))['title_token']
    assert stored['state'] == 'build-busy'
    assert stored['owner'] == 'build-hook'
    assert stored['set_at']

    code, out, _ = _run(
        monkeypatch,
        capsys,
        ['title-token', 'clear', '--plan-id', 'ms-disp-tt', '--owner', 'build-hook'],
    )
    assert code == 0
    assert _parse(out)['status'] == 'success'
    cleared = json.loads(status_file.read_text(encoding='utf-8'))
    assert 'title_token' not in cleared


def test_main_title_token_rejects_unknown_state(plan_context, monkeypatch, capsys):
    """An out-of-enum --state is an argparse rejection (exit 2)."""
    code, _, _ = _run(
        monkeypatch, capsys, ['title-token', 'set', '--plan-id', 'ms-disp-tt2', '--state', 'not-a-state']
    )

    assert code == 2


def test_main_title_token_rejects_unknown_owner(plan_context, monkeypatch, capsys):
    """An out-of-enum --owner is likewise an argparse rejection (exit 2).

    The owner vocabulary is as closed as the state vocabulary: an unrecognised
    owner recorded on the token would produce a record no writer could clear.
    """
    code, _, _ = _run(
        monkeypatch,
        capsys,
        [
            'title-token', 'set', '--plan-id', 'ms-disp-tt3',
            '--state', 'build-busy', '--owner', 'not-an-owner',
        ],
    )

    assert code == 2
