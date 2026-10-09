#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Tests for the ``changed-paths`` verb of ``scripts/verdict_currency.py``.

The verb reads a finalize step's own ``6-finalize`` record and reports which
paths differ between the commit that record is anchored to and the live HEAD.
Its contract is asymmetric, and the tests pin it in that shape: ``changed_paths``
exists on the ``computed`` outcome ONLY. The three other outcomes compared
nothing, so each is asserted to carry no ``changed_paths`` key at all — an empty
list there would be indistinguishable from a measured "nothing changed".

Every test runs against a REAL temporary git repository. Only the status
document is substituted (through the ``read_status`` seam); the record lookup
(``find_step_record``), the HEAD resolution and the tree difference all run for
real.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

import _status_core
from toon_parser import parse_toon

from conftest import load_script_module

_mod = load_script_module('plan-marshall', 'phase-6-finalize', 'verdict_currency.py', 'verdict_currency')

_PLAN_ID = 'changed-paths-plan'
_STEP = 'pre-push-quality-gate'


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ['git', '-C', str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout.strip()


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """A minimal repository with deterministic identity and no signing."""
    if shutil.which('git') is None:
        pytest.skip('git is not available')
    repo = tmp_path / 'repo'
    repo.mkdir()
    _git(repo, 'init', '--quiet')
    _git(repo, 'config', 'user.email', 'test@example.invalid')
    _git(repo, 'config', 'user.name', 'Test')
    _git(repo, 'config', 'commit.gpgsign', 'false')
    return repo


def _commit(repo: Path, files: dict[str, str]) -> str:
    """Write ``files`` and commit them together, returning the new HEAD."""
    for relative, body in files.items():
        target = repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding='utf-8')
        _git(repo, 'add', relative)
    _git(repo, 'commit', '--quiet', '-m', 'commit')
    return _git(repo, 'rev-parse', 'HEAD')


def _status_with(record: dict[str, Any] | None) -> dict[str, Any]:
    """A status document in the persisted shape, holding ``record`` for the step."""
    steps = {} if record is None else {_STEP: record}
    return {'title': 'changed-paths', 'metadata': {'phase_steps': {'6-finalize': steps}}}


def _patch_status(monkeypatch: pytest.MonkeyPatch, status: dict[str, Any]) -> None:
    monkeypatch.setattr(_status_core, 'read_status', lambda _plan_id: status)


def _done_record(head: str, **extra: Any) -> dict[str, Any]:
    return {'outcome': 'done', 'display_detail': 'gate green', 'head_at_completion': head, **extra}


def test_done_firing_reports_exactly_the_paths_one_commit_touched(git_repo: Path, monkeypatch):
    recorded = _commit(git_repo, {'src/app.py': 'x = 1\n'})
    live = _commit(git_repo, {'src/app.py': 'x = 2\n', 'doc/notes.md': 'notes\n'})
    _patch_status(monkeypatch, _status_with(_done_record(recorded)))

    payload = _mod.changed_paths_for_step(_PLAN_ID, _STEP, str(git_repo))

    assert payload['status'] == 'success'
    assert payload['step'] == _STEP
    assert payload['outcome'] == _mod.OUTCOME_COMPUTED
    assert payload['recorded_head'] == recorded
    assert payload['live_head'] == live
    assert sorted(payload['changed_paths']) == ['doc/notes.md', 'src/app.py']


def test_computed_paths_equal_the_shared_tree_difference(git_repo: Path, monkeypatch):
    """The verb adds no second derivation: it reports what the shared seam reports."""
    recorded = _commit(git_repo, {'src/app.py': 'x = 1\n'})
    live = _commit(git_repo, {'src/app.py': 'x = 2\n', 'doc/notes.md': 'notes\n'})
    _patch_status(monkeypatch, _status_with(_done_record(recorded)))
    expected, ok = _mod.resolve_changed_paths(str(git_repo), recorded, live)

    payload = _mod.changed_paths_for_step(_PLAN_ID, _STEP, str(git_repo))

    assert ok is True
    assert payload['changed_paths'] == expected


def test_unmoved_head_is_computed_with_an_empty_list(git_repo: Path, monkeypatch):
    """Equal trees are a MEASURED empty difference, so the key is present."""
    recorded = _commit(git_repo, {'src/app.py': 'x = 1\n'})
    _patch_status(monkeypatch, _status_with(_done_record(recorded)))

    payload = _mod.changed_paths_for_step(_PLAN_ID, _STEP, str(git_repo))

    assert payload['outcome'] == _mod.OUTCOME_COMPUTED
    assert payload['changed_paths'] == []


def test_renamed_file_is_listed_under_both_its_old_and_its_new_path(git_repo: Path, monkeypatch):
    """A rename removes one path and adds another, and BOTH differ.

    With git's default rename detection the old path would be folded into the
    new one and vanish from the list, so a reader keyed on the old path would
    see no change to a file that no longer exists.
    """
    recorded = _commit(git_repo, {'src/old.py': 'x = 1\ny = 2\nz = 3\n'})
    _git(git_repo, 'mv', 'src/old.py', 'src/new.py')
    _git(git_repo, 'commit', '--quiet', '-m', 'rename')
    _patch_status(monkeypatch, _status_with(_done_record(recorded)))

    payload = _mod.changed_paths_for_step(_PLAN_ID, _STEP, str(git_repo))

    assert payload['outcome'] == _mod.OUTCOME_COMPUTED
    assert sorted(payload['changed_paths']) == ['src/new.py', 'src/old.py']


def test_path_git_would_quote_is_listed_verbatim(git_repo: Path, monkeypatch):
    """A non-ASCII or space-bearing name comes back as the path, not a quoted form of it."""
    recorded = _commit(git_repo, {'src/app.py': 'x = 1\n'})
    _commit(git_repo, {'doc/überblick.md': 'notes\n', 'doc/release notes.md': 'notes\n'})
    _patch_status(monkeypatch, _status_with(_done_record(recorded)))

    payload = _mod.changed_paths_for_step(_PLAN_ID, _STEP, str(git_repo))

    assert payload['outcome'] == _mod.OUTCOME_COMPUTED
    assert sorted(payload['changed_paths']) == ['doc/release notes.md', 'doc/überblick.md']


def test_no_prior_firing_is_first_firing_without_a_changed_paths_key(git_repo: Path, monkeypatch):
    live = _commit(git_repo, {'src/app.py': 'x = 1\n'})
    _patch_status(monkeypatch, _status_with(None))

    payload = _mod.changed_paths_for_step(_PLAN_ID, _STEP, str(git_repo))

    assert payload['status'] == 'success'
    assert payload['outcome'] == _mod.OUTCOME_FIRST_FIRING
    assert payload['recorded_head'] == 'none'
    assert payload['live_head'] == live
    assert 'changed_paths' not in payload


def test_unresolvable_recorded_commit_is_diff_unavailable_without_a_changed_paths_key(git_repo: Path, monkeypatch):
    _commit(git_repo, {'src/app.py': 'x = 1\n'})
    unreachable = 'deadbeef' * 5
    _patch_status(monkeypatch, _status_with(_done_record(unreachable)))

    payload = _mod.changed_paths_for_step(_PLAN_ID, _STEP, str(git_repo))

    assert payload['status'] == 'success'
    assert payload['outcome'] == _mod.OUTCOME_DIFF_UNAVAILABLE
    assert payload['recorded_head'] == unreachable
    assert 'changed_paths' not in payload


def test_unresolvable_live_head_is_diff_unavailable(git_repo: Path, monkeypatch):
    """A repository with no commit yet has an unborn HEAD — nothing to diff against.

    An unborn HEAD rather than a non-repository directory: the temp directory may
    itself sit inside a checkout, where git would resolve the ENCLOSING repo's HEAD.
    """
    _patch_status(monkeypatch, _status_with(_done_record('cafe' * 10)))

    payload = _mod.changed_paths_for_step(_PLAN_ID, _STEP, str(git_repo))

    assert payload['outcome'] == _mod.OUTCOME_DIFF_UNAVAILABLE
    assert payload['live_head'] == 'none'
    assert 'changed_paths' not in payload


def test_failed_record_is_last_firing_not_done_without_a_changed_paths_key(git_repo: Path, monkeypatch):
    recorded = _commit(git_repo, {'src/app.py': 'x = 1\n'})
    _commit(git_repo, {'doc/notes.md': 'notes\n'})
    record = {'outcome': 'failed', 'display_detail': 'gate timed out', 'head_at_completion': recorded}
    _patch_status(monkeypatch, _status_with(record))

    payload = _mod.changed_paths_for_step(_PLAN_ID, _STEP, str(git_repo))

    assert payload['status'] == 'success'
    assert payload['outcome'] == _mod.OUTCOME_LAST_FIRING_NOT_DONE
    assert payload['recorded_head'] == recorded
    assert 'changed_paths' not in payload


def test_done_record_without_an_anchor_is_last_firing_not_done(git_repo: Path, monkeypatch):
    """A ``done`` with no ``head_at_completion`` was never anchored to a tree."""
    _commit(git_repo, {'src/app.py': 'x = 1\n'})
    _patch_status(monkeypatch, _status_with({'outcome': 'done', 'display_detail': 'gate green'}))

    payload = _mod.changed_paths_for_step(_PLAN_ID, _STEP, str(git_repo))

    assert payload['outcome'] == _mod.OUTCOME_LAST_FIRING_NOT_DONE
    assert payload['recorded_head'] == 'none'
    assert 'changed_paths' not in payload


def test_recorded_facts_are_echoed(git_repo: Path, monkeypatch):
    recorded = _commit(git_repo, {'src/app.py': 'x = 1\n'})
    facts = {'lessons_examined': '3', 'footprint': 'realized'}
    _patch_status(monkeypatch, _status_with(_done_record(recorded, facts=facts)))

    payload = _mod.changed_paths_for_step(_PLAN_ID, _STEP, str(git_repo))

    assert payload['recorded_facts'] == facts


def test_record_without_facts_carries_no_recorded_facts_key(git_repo: Path, monkeypatch):
    recorded = _commit(git_repo, {'src/app.py': 'x = 1\n'})
    _patch_status(monkeypatch, _status_with(_done_record(recorded)))

    payload = _mod.changed_paths_for_step(_PLAN_ID, _STEP, str(git_repo))

    assert 'recorded_facts' not in payload


def test_prefixed_step_key_finds_the_canonical_record(git_repo: Path, monkeypatch):
    recorded = _commit(git_repo, {'src/app.py': 'x = 1\n'})
    _patch_status(monkeypatch, _status_with(_done_record(recorded)))

    payload = _mod.changed_paths_for_step(_PLAN_ID, f'default:{_STEP}', str(git_repo))

    assert payload['step'] == _STEP
    assert payload['outcome'] == _mod.OUTCOME_COMPUTED


def test_unknown_plan_is_a_named_error_not_a_first_firing(git_repo: Path, monkeypatch):
    """No status at all is "could not look", which must not read as "no record"."""
    _commit(git_repo, {'src/app.py': 'x = 1\n'})
    _patch_status(monkeypatch, {})

    payload = _mod.changed_paths_for_step(_PLAN_ID, _STEP, str(git_repo))

    assert payload['status'] == 'error'
    assert payload['error'] == _mod.ERROR_PLAN_NOT_FOUND
    assert 'outcome' not in payload
    assert 'changed_paths' not in payload


def test_unreadable_status_is_a_named_error(git_repo: Path, monkeypatch):
    _commit(git_repo, {'src/app.py': 'x = 1\n'})

    def _raise(_plan_id: str) -> dict[str, Any]:
        raise OSError('status.json is unreadable')

    monkeypatch.setattr(_status_core, 'read_status', _raise)

    payload = _mod.changed_paths_for_step(_PLAN_ID, _STEP, str(git_repo))

    assert payload['status'] == 'error'
    assert payload['error'] == _mod.ERROR_STATUS_UNREADABLE
    assert 'changed_paths' not in payload


def test_cli_emits_the_computed_payload_and_exits_zero(git_repo: Path, monkeypatch, capsys):
    """The verb through its real parser: the three flags, TOON out, exit 0."""
    recorded = _commit(git_repo, {'src/app.py': 'x = 1\n'})
    _commit(git_repo, {'src/app.py': 'x = 2\n', 'doc/notes.md': 'notes\n'})
    _patch_status(monkeypatch, _status_with(_done_record(recorded)))
    monkeypatch.setattr(
        sys,
        'argv',
        [
            'verdict_currency.py',
            'changed-paths',
            '--plan-id',
            _PLAN_ID,
            '--step',
            _STEP,
            '--worktree-path',
            str(git_repo),
        ],
    )

    exit_code = _mod.main()

    parsed = parse_toon(capsys.readouterr().out)
    assert exit_code == 0
    assert parsed['outcome'] == _mod.OUTCOME_COMPUTED
    assert sorted(parsed['changed_paths']) == ['doc/notes.md', 'src/app.py']


def test_cli_exits_zero_on_a_non_computed_outcome(git_repo: Path, monkeypatch, capsys):
    _commit(git_repo, {'src/app.py': 'x = 1\n'})
    _patch_status(monkeypatch, _status_with(None))
    monkeypatch.setattr(
        sys,
        'argv',
        [
            'verdict_currency.py',
            'changed-paths',
            '--plan-id',
            _PLAN_ID,
            '--step',
            _STEP,
            '--worktree-path',
            str(git_repo),
        ],
    )

    exit_code = _mod.main()

    parsed = parse_toon(capsys.readouterr().out)
    assert exit_code == 0
    assert parsed['outcome'] == _mod.OUTCOME_FIRST_FIRING
    assert 'changed_paths' not in parsed
