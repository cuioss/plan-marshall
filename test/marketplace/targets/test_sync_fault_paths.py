# SPDX-License-Identifier: FSL-1.1-ALv2
"""Fault-path tests for marketplace/targets/sync.py.

Covers a filesystem fault in a single-target component-tree run and the
remedy the ``behind`` summary names per repin outcome.
"""

from __future__ import annotations

import pytest
from toon_parser import parse_toon

from marketplace.targets.sync import (
    REPIN_COMMAND,
    REPIN_FAILED,
    REPIN_SKIPPED_DRY_RUN,
    _behind_summary,
    main,
)

REPIN_REMEDY = 're-run the sync with --repin'


@pytest.mark.parametrize('target_name', ['opencode', 'antigravity'])
def test_filesystem_fault_in_a_single_target_run_is_an_error_document(
    target_name: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    """A filesystem fault raised by a component-tree deploy is reported, not propagated."""

    def _raise(*_args: object, **_kwargs: object) -> None:
        raise PermissionError('denied')

    monkeypatch.setattr('marketplace.targets.sync._deploy_target', _raise)

    exit_code = main(['--target', target_name])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.err == ''
    data = parse_toon(captured.out)
    assert f'{target_name} sync failed: PermissionError: denied' in data.pop('summary_message')
    assert data == {'status': 'error'}


@pytest.mark.parametrize(
    ('repin', 'names_apply', 'names_repin'),
    [
        ({}, True, True),
        ({'repin': REPIN_FAILED, 'repin_message': 'boom'}, True, False),
        ({'repin': REPIN_SKIPPED_DRY_RUN}, False, False),
    ],
    ids=['repin-not-requested', 'repin-failed', 'repin-skipped-by-dry-run'],
)
def test_behind_summary_names_only_a_remedy_not_already_tried(
    repin: dict[str, str], names_apply: bool, names_repin: bool
):
    summary = _behind_summary('synced 1 bundle(s)', ('0.1.100', '0.1.200'), repin)

    assert 'pinned 0.1.100, synced 0.1.200' in summary
    assert (REPIN_COMMAND in summary) is names_apply
    assert (REPIN_REMEDY in summary) is names_repin
