# SPDX-License-Identifier: FSL-1.1-ALv2
"""A missing retrospective fragment is a structured refusal, never a crash.

``collect-fragments add`` and ``register`` report a fragment path that names no
file as ``error: fragment_missing`` at exit 0, naming the aspect and the resolved
path and leaving the bundle byte-identical; ``compile-report run`` reports a
missing bundle as ``error: fragments_file_missing`` at exit 0 and writes no
report. Both fragment verbs resolve a relative path through one resolver, and a
cwd-relative path that already names the plan directory is used as that
location instead of being anchored under the plan directory a second time.
"""

from __future__ import annotations

import os
from pathlib import Path

from _collect_fragments_fixtures import (
    SCRIPT_PATH,
    _ArgsNS,
    _init_bundle,
    _load_module,
    _valid_fragment_body,
    _write_fragment,
)
from _compile_report_fixtures import SCRIPT_PATH as COMPILE_REPORT_PATH
from _plan_retrospective_fixtures import setup_live_plan

from conftest import run_script

_ASPECT = 'log-analysis'
_OTHER_ASPECT = 'artifact-consistency'


def _bundle_bytes(plan_dir: Path) -> bytes:
    return (plan_dir / 'work' / 'retro-fragments.toon').read_bytes()


def _add_args(plan_id: str, fragment_file: str) -> _ArgsNS:
    return _ArgsNS(
        plan_id=plan_id, archived_plan_path=None, aspect=_ASPECT, fragment_file=fragment_file, overwrite=False
    )


def _register_args(plan_id: str, items: list[str]) -> _ArgsNS:
    return _ArgsNS(plan_id=plan_id, archived_plan_path=None, item=items, overwrite=False)


class TestMissingFragmentRefusal:
    """A fragment path naming no file is refused with the bundle untouched."""

    def test_add_reports_fragment_missing_at_exit_zero(self, tmp_path, monkeypatch):
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        _init_bundle(plan_id)
        missing = tmp_path / 'fragment-log-analysis.toon'
        before = _bundle_bytes(plan_dir)

        result = run_script(
            SCRIPT_PATH, 'add', '--plan-id', plan_id, '--aspect', _ASPECT, '--fragment-file', str(missing)
        )

        assert result.success, result.stderr
        data = result.toon()
        assert data['status'] == 'error'
        assert data['error'] == 'fragment_missing'
        assert data['aspect'] == _ASPECT
        assert data['fragment_path'] == str(missing)
        assert _bundle_bytes(plan_dir) == before

    def test_register_refuses_the_whole_batch_at_exit_zero(self, tmp_path, monkeypatch):
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        _init_bundle(plan_id)
        present = _write_fragment(tmp_path, 'present.toon', _valid_fragment_body(_OTHER_ASPECT))
        missing = tmp_path / 'fragment-log-analysis.toon'
        before = _bundle_bytes(plan_dir)

        result = run_script(
            SCRIPT_PATH,
            'register',
            '--plan-id',
            plan_id,
            '--item',
            f'{_OTHER_ASPECT}={present}',
            '--item',
            f'{_ASPECT}={missing}',
        )

        assert result.success, result.stderr
        data = result.toon()
        assert data['status'] == 'error'
        assert data['error'] == 'fragment_missing'
        assert data['aspect'] == _ASPECT
        assert data['fragment_path'] == str(missing)
        # All-or-nothing: the present fragment in the same batch did not land.
        assert _bundle_bytes(plan_dir) == before

    def test_cwd_relative_capture_is_refused_naming_the_plan_anchored_path(self, tmp_path, monkeypatch):
        # A relative path that does not resolve from the cwd into the plan
        # directory is anchored to the plan directory, and the refusal names
        # the anchored path — the location the registration actually looked at.
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        module = _load_module()
        module.cmd_init(_ArgsNS(plan_id=plan_id, mode='live', archived_plan_path=None))
        assert not Path.cwd().resolve().is_relative_to(plan_dir.resolve())

        result = module.cmd_add(_add_args(plan_id, 'work/fragment-log-analysis.toon'))

        assert result['status'] == 'error'
        assert result['error'] == 'fragment_missing'
        assert result['fragment_path'] == str(plan_dir.resolve() / 'work' / 'fragment-log-analysis.toon')


def _cwd_relative(path: Path) -> str:
    """Spell ``path`` relative to the cwd, the form a caller in another directory writes."""
    return os.path.relpath(path.resolve(), Path.cwd().resolve())


class TestOneResolverForBothVerbs:
    """``add`` and ``register`` resolve a fragment path identically."""

    def test_same_relative_path_resolves_to_the_same_location(self, tmp_path, monkeypatch):
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        module = _load_module()
        module.cmd_init(_ArgsNS(plan_id=plan_id, mode='live', archived_plan_path=None))
        relative = 'work/fragment-absent.toon'

        add_result = module.cmd_add(_add_args(plan_id, relative))
        register_result = module.cmd_register(_register_args(plan_id, [f'{_ASPECT}={relative}']))

        assert add_result['error'] == 'fragment_missing'
        assert register_result['error'] == 'fragment_missing'
        assert add_result['fragment_path'] == register_result['fragment_path']
        assert add_result['fragment_path'] == str(plan_dir.resolve() / relative)

    def test_add_uses_a_cwd_relative_path_inside_the_plan_dir_without_doubling(self, tmp_path, monkeypatch):
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        module = _load_module()
        module.cmd_init(_ArgsNS(plan_id=plan_id, mode='live', archived_plan_path=None))
        fragment = plan_dir / 'work' / 'fragment-log-analysis.toon'
        fragment.write_text(_valid_fragment_body(_ASPECT), encoding='utf-8')
        relative = _cwd_relative(fragment)

        result = module.cmd_add(_add_args(plan_id, relative))

        assert result['status'] == 'success', result
        assert result['aspects'] == [_ASPECT]

    def test_register_uses_a_cwd_relative_path_inside_the_plan_dir_without_doubling(self, tmp_path, monkeypatch):
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        module = _load_module()
        module.cmd_init(_ArgsNS(plan_id=plan_id, mode='live', archived_plan_path=None))
        fragment = plan_dir / 'work' / 'fragment-log-analysis.toon'
        fragment.write_text(_valid_fragment_body(_ASPECT), encoding='utf-8')
        relative = _cwd_relative(fragment)

        result = module.cmd_register(_register_args(plan_id, [f'{_ASPECT}={relative}']))

        assert result['status'] == 'success', result
        assert result['aspects'] == [_ASPECT]


class TestCompileReportMissingBundle:
    """A missing fragments bundle is refused before any report is written."""

    def test_run_reports_fragments_file_missing_at_exit_zero(self, tmp_path, monkeypatch):
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        missing = tmp_path / 'retro-fragments.toon'

        result = run_script(
            COMPILE_REPORT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live', '--fragments-file', str(missing)
        )

        assert result.success, result.stderr
        data = result.toon()
        assert data['status'] == 'error'
        assert data['error'] == 'fragments_file_missing'
        assert data['fragments_file'] == str(missing)
        assert not (plan_dir / 'quality-verification-report.md').exists()
