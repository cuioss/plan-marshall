#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: E402
"""In-process behavioral tests for determine_mode.py mode/doc/structure logic.

The existing marshall-steward suites cover the worktree guard and the
finalize-step detection helpers. This module fills the remaining gaps with
direct, in-process calls into the mode-determination, project-architecture
structure check, documentation-content checks/fixes, working-prefix drift
detection, and the command-handler wrappers — including the ``main()`` dispatch
that constructs the argparse surface. All fixtures use ``tmp_path`` and explicit
paths, so no plan-marshall runtime state is touched.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from conftest import MARKETPLACE_ROOT, load_script_module

# Ensure manage-config scripts are importable so determine_mode's lazy
# ``_config_defaults`` import (used by working-prefix drift detection) resolves.
_MANAGE_CONFIG_SCRIPTS = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'manage-config' / 'scripts'
if str(_MANAGE_CONFIG_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_MANAGE_CONFIG_SCRIPTS))

dm = load_script_module(
    'plan-marshall', 'marshall-steward', 'determine_mode.py', 'determine_mode_behavior_cov'
)


# =============================================================================
# determine_mode
# =============================================================================


def test_determine_mode_wizard_when_executor_missing(tmp_path: Path):
    """determine_mode returns wizard/executor_missing when the shim is absent."""
    mode, reason = dm.determine_mode(tmp_path)

    assert mode == 'wizard'
    assert reason == 'executor_missing'


def test_determine_mode_wizard_when_marshal_missing(tmp_path: Path):
    """determine_mode returns wizard/marshal_missing when only the executor exists."""
    (tmp_path / 'execute-script.py').write_text('# shim')

    mode, reason = dm.determine_mode(tmp_path)

    assert mode == 'wizard'
    assert reason == 'marshal_missing'


def test_determine_mode_menu_when_both_present(tmp_path: Path):
    """determine_mode returns menu/both_exist when executor and marshal exist."""
    (tmp_path / 'execute-script.py').write_text('# shim')
    (tmp_path / 'marshal.json').write_text('{}')

    mode, reason = dm.determine_mode(tmp_path)

    assert mode == 'menu'
    assert reason == 'both_exist'


# =============================================================================
# check_structure
# =============================================================================


def test_check_structure_missing_without_project_file(tmp_path: Path):
    """check_structure reports 'missing' when _project.json is absent."""
    status, _path, count = dm.check_structure(tmp_path)

    assert status == 'missing'
    assert count == 0


def test_check_structure_missing_on_unparseable_project_file(tmp_path: Path):
    """check_structure reports 'missing' when _project.json is malformed."""
    arch = tmp_path / 'project-architecture'
    arch.mkdir()
    (arch / '_project.json').write_text('{not json')

    status, _path, count = dm.check_structure(tmp_path)

    assert status == 'missing'
    assert count == 0


def test_check_structure_missing_when_modules_index_empty(tmp_path: Path):
    """check_structure reports 'missing' when the modules index is empty/non-dict."""
    arch = tmp_path / 'project-architecture'
    arch.mkdir()
    (arch / '_project.json').write_text(json.dumps({'modules': []}))

    status, _path, count = dm.check_structure(tmp_path)

    assert status == 'missing'
    assert count == 0


def test_check_structure_missing_when_no_enriched_present(tmp_path: Path):
    """check_structure reports 'missing' when no module has an enriched.json."""
    arch = tmp_path / 'project-architecture'
    arch.mkdir()
    (arch / '_project.json').write_text(json.dumps({'modules': {'core': {}}}))

    status, _path, count = dm.check_structure(tmp_path)

    assert status == 'missing'
    assert count == 0


def test_check_structure_exists_with_enriched_module(tmp_path: Path):
    """check_structure reports 'exists' and counts modules with enriched.json."""
    arch = tmp_path / 'project-architecture'
    (arch / 'core').mkdir(parents=True)
    (arch / '_project.json').write_text(json.dumps({'modules': {'core': {}, 'web': {}}}))
    (arch / 'core' / 'enriched.json').write_text('{}')

    status, _path, count = dm.check_structure(tmp_path)

    assert status == 'exists'
    assert count == 1


# =============================================================================
# count_section_bullets
# =============================================================================


def test_count_section_bullets_returns_zero_when_section_absent():
    """count_section_bullets returns 0 when the heading is not present."""
    content = '# Title\n\nSome prose without the target section.\n'

    assert dm.count_section_bullets(content, 'Rules') == 0


def test_count_section_bullets_counts_until_next_heading():
    """count_section_bullets counts top-level bullets and stops at the next heading."""
    content = (
        '## Rules\n'
        '- one\n'
        '- two\n'
        '  - nested ignored\n'
        '## Next\n'
        '- not counted\n'
    )

    assert dm.count_section_bullets(content, 'Rules') == 2


# =============================================================================
# check_docs / fix_docs
# =============================================================================


def _write_docs(project_root: Path, claude: str | None = None, agents: str | None = None) -> None:
    """Write CLAUDE.md / agents.md fixtures into ``project_root``."""
    if claude is not None:
        (project_root / 'CLAUDE.md').write_text(claude)
    if agents is not None:
        (project_root / 'agents.md').write_text(agents)


def test_check_docs_ok_when_all_patterns_present(tmp_path: Path):
    """check_docs returns 'ok' when every required marker is present."""
    _write_docs(
        tmp_path,
        claude='Use .plan/temp here.\nAlways use Glob, Read, Grep tools.\n',
        agents='Temp files live in .plan/temp.\n',
    )

    status, missing = dm.check_docs(tmp_path)

    assert status == 'ok'
    assert missing == []


def test_check_docs_flags_missing_marker(tmp_path: Path):
    """check_docs reports a content_missing entry when a marker is absent."""
    # CLAUDE.md has the file-ops marker but not the .plan/temp marker.
    _write_docs(tmp_path, claude='Always use Glob, Read, Grep tools.\n')

    status, missing = dm.check_docs(tmp_path)

    assert status == 'needs_update'
    assert any(m['check'] == 'plan_temp' and m['reason'] == 'content_missing' for m in missing)


def test_check_docs_incomplete_when_section_short(tmp_path: Path, monkeypatch):
    """check_docs flags 'incomplete' when a min_bullets section is present-but-short."""
    monkeypatch.setattr(
        dm,
        'CONTENT_CHECKS',
        [
            {
                'key': 'rules',
                'files': ['CLAUDE.md'],
                'pattern': 'Hard Rules',
                'min_bullets': 3,
                'section_heading': 'Hard Rules',
            }
        ],
    )
    _write_docs(tmp_path, claude='## Hard Rules\n- only one\n')

    status, missing = dm.check_docs(tmp_path)

    assert status == 'needs_update'
    incomplete = next(m for m in missing if m['reason'] == 'incomplete')
    assert incomplete['found'] == '1'
    assert incomplete['expected'] == '3'


def test_fix_docs_ok_when_nothing_missing(tmp_path: Path):
    """fix_docs returns ('ok', []) when check_docs finds no gaps."""
    _write_docs(
        tmp_path,
        claude='Use .plan/temp.\nAlways use Glob, Read, Grep tools.\n',
        agents='.plan/temp usage.\n',
    )

    status, fixes = dm.fix_docs(tmp_path)

    assert status == 'ok'
    assert fixes == []


def test_fix_docs_appends_missing_content(tmp_path: Path):
    """fix_docs appends the verbatim block for a missing marker and reports it."""
    # Missing the .plan/temp marker; the file-ops marker is present.
    _write_docs(tmp_path, claude='Always use Glob, Read, Grep tools.')

    status, fixes = dm.fix_docs(tmp_path)

    assert status == 'fixed'
    assert 'plan_temp:CLAUDE.md' in fixes
    assert '.plan/temp' in (tmp_path / 'CLAUDE.md').read_text()


def test_fix_docs_skips_incomplete_entries(tmp_path: Path, monkeypatch):
    """fix_docs leaves present-but-short sections untouched (no appendable fix)."""
    monkeypatch.setattr(
        dm,
        'CONTENT_CHECKS',
        [
            {
                'key': 'rules',
                'files': ['CLAUDE.md'],
                'pattern': 'Hard Rules',
                'min_bullets': 5,
                'section_heading': 'Hard Rules',
            }
        ],
    )
    original = '## Hard Rules\n- one\n'
    _write_docs(tmp_path, claude=original)

    status, fixes = dm.fix_docs(tmp_path)

    assert status == 'ok'
    assert fixes == []
    # The file is unchanged — drift is reconciled manually, not by appending.
    assert (tmp_path / 'CLAUDE.md').read_text() == original


def test_fix_docs_skips_checks_without_fix_content(tmp_path: Path, monkeypatch):
    """fix_docs skips a missing check whose key has no FIX_CONTENT entry."""
    monkeypatch.setattr(
        dm,
        'CONTENT_CHECKS',
        [{'key': 'unknown_key', 'files': ['CLAUDE.md'], 'pattern': 'NEVER-PRESENT-MARKER'}],
    )
    _write_docs(tmp_path, claude='nothing relevant here')

    status, fixes = dm.fix_docs(tmp_path)

    assert status == 'ok'
    assert fixes == []


# =============================================================================
# command-handler wrappers
# =============================================================================


def test_cmd_mode_envelope(tmp_path: Path):
    """cmd_mode wraps determine_mode output in a success envelope."""
    result = dm.cmd_mode(_ns(plan_dir=str(tmp_path)))

    assert result['status'] == 'success'
    assert result['mode'] == 'wizard'


def test_cmd_check_docs_surfaces_messages_for_incomplete(tmp_path: Path, monkeypatch):
    """cmd_check_docs adds a human-readable 'messages' field for incomplete drift."""
    monkeypatch.setattr(
        dm,
        'CONTENT_CHECKS',
        [
            {
                'key': 'hard_rules',
                'files': ['CLAUDE.md'],
                'pattern': 'Hard Rules',
                'min_bullets': 4,
                'section_heading': 'Hard Rules',
            }
        ],
    )
    _write_docs(tmp_path, claude='## Hard Rules\n- one\n')

    result = dm.cmd_check_docs(_ns(project_root=str(tmp_path)))

    assert result['check_status'] == 'needs_update'
    assert 'messages' in result
    assert 'incomplete' in result['messages']


def test_cmd_fix_docs_reports_fixed_count(tmp_path: Path):
    """cmd_fix_docs reports the number of files it fixed."""
    _write_docs(tmp_path, claude='Always use Glob, Read, Grep tools.')

    result = dm.cmd_fix_docs(_ns(project_root=str(tmp_path)))

    assert result['fix_status'] == 'fixed'
    assert result['fixed_count'] == 1
    assert 'fixes' in result


def test_cmd_check_structure_envelope(tmp_path: Path):
    """cmd_check_structure surfaces the structure status and module count."""
    result = dm.cmd_check_structure(_ns(plan_dir=str(tmp_path)))

    assert result['status'] == 'success'
    assert result['check_status'] == 'missing'
    assert result['modules_count'] == 0


def test_cmd_check_worktree_plan_local_refuse_includes_detail(tmp_path: Path):
    """cmd_check_worktree_plan_local emits 'refuse' + detail for a bare worktree."""
    worktree = tmp_path / 'main' / '.plan' / 'local' / 'worktrees' / 'plan-x'
    worktree.mkdir(parents=True)

    result = dm.cmd_check_worktree_plan_local(_ns(repo_root=str(worktree), scaffold=False))

    assert result['status'] == 'refuse'
    assert result['is_worktree'] is True
    assert 'refusing executor' in result['detail']


# =============================================================================
# _read_finalize_steps
# =============================================================================


def test_read_finalize_steps_none_when_marshal_absent(tmp_path: Path):
    """_read_finalize_steps returns None when marshal.json is absent."""
    assert dm._read_finalize_steps(tmp_path) is None


def test_read_finalize_steps_none_when_unparseable(tmp_path: Path):
    """_read_finalize_steps returns None when marshal.json is malformed."""
    (tmp_path / 'marshal.json').write_text('{broken')

    assert dm._read_finalize_steps(tmp_path) is None


def test_read_finalize_steps_returns_list(tmp_path: Path):
    """_read_finalize_steps returns the configured steps list."""
    marshal = {'plan': {'phase-6-finalize': {'steps': ['default:push']}}}
    (tmp_path / 'marshal.json').write_text(json.dumps(marshal))

    assert dm._read_finalize_steps(tmp_path) == ['default:push']


# =============================================================================
# detect_working_prefixes_drift / cmd_check_working_prefixes
# =============================================================================


def _default_prefixes() -> list[str]:
    """Return the canonical working_prefixes default entries."""
    from _config_defaults import DEFAULT_PROJECT

    return list(DEFAULT_PROJECT['working_prefixes'])


def _write_project_marshal(plan_dir: Path, project_block: dict) -> None:
    """Write a marshal.json carrying the given project block."""
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / 'marshal.json').write_text(json.dumps({'project': project_block}))


def test_drift_absent_when_key_missing(tmp_path: Path):
    """detect_working_prefixes_drift reports 'absent' when the key is missing."""
    _write_project_marshal(tmp_path, {})

    result = dm.detect_working_prefixes_drift(tmp_path)

    assert result['outcome'] == 'absent'
    assert result['missing_keys'] == ['working_prefixes']


def test_drift_when_value_not_a_list(tmp_path: Path):
    """detect_working_prefixes_drift reports 'drift' for a non-list value."""
    _write_project_marshal(tmp_path, {'working_prefixes': 'feature/'})

    assert dm.detect_working_prefixes_drift(tmp_path)['outcome'] == 'drift'


def test_drift_when_default_entry_missing(tmp_path: Path):
    """detect_working_prefixes_drift reports 'drift' when a default entry is absent."""
    partial = _default_prefixes()[:1]
    _write_project_marshal(tmp_path, {'working_prefixes': partial})

    assert dm.detect_working_prefixes_drift(tmp_path)['outcome'] == 'drift'


def test_drift_ok_for_superset(tmp_path: Path):
    """detect_working_prefixes_drift honours operator supersets as 'ok'."""
    superset = _default_prefixes() + ['experimental/']
    _write_project_marshal(tmp_path, {'working_prefixes': superset})

    assert dm.detect_working_prefixes_drift(tmp_path)['outcome'] == 'ok'


def test_drift_ok_when_marshal_absent(tmp_path: Path):
    """detect_working_prefixes_drift degrades to 'ok' when marshal.json is absent."""
    assert dm.detect_working_prefixes_drift(tmp_path)['outcome'] == 'ok'


def test_drift_ok_when_marshal_unparseable(tmp_path: Path):
    """detect_working_prefixes_drift degrades to 'ok' for malformed marshal.json."""
    (tmp_path / 'marshal.json').write_text('{nope')

    assert dm.detect_working_prefixes_drift(tmp_path)['outcome'] == 'ok'


def test_cmd_check_working_prefixes_absent(tmp_path: Path):
    """cmd_check_working_prefixes surfaces status:missing/detail:absent."""
    _write_project_marshal(tmp_path, {})

    result = dm.cmd_check_working_prefixes(_ns(plan_dir=str(tmp_path)))

    assert result['status'] == 'missing'
    assert result['detail'] == 'absent'


def test_cmd_check_working_prefixes_drift(tmp_path: Path):
    """cmd_check_working_prefixes surfaces status:missing/detail:drift."""
    _write_project_marshal(tmp_path, {'working_prefixes': _default_prefixes()[:1]})

    result = dm.cmd_check_working_prefixes(_ns(plan_dir=str(tmp_path)))

    assert result['status'] == 'missing'
    assert result['detail'] == 'drift'


def test_cmd_check_working_prefixes_ok(tmp_path: Path):
    """cmd_check_working_prefixes returns status:ok for a complete config."""
    _write_project_marshal(tmp_path, {'working_prefixes': _default_prefixes()})

    assert dm.cmd_check_working_prefixes(_ns(plan_dir=str(tmp_path)))['status'] == 'ok'


# =============================================================================
# cmd_check_missing_finalize_steps
# =============================================================================


def test_cmd_check_missing_finalize_steps_ok_without_marshal(tmp_path: Path):
    """cmd_check_missing_finalize_steps reports ok when nothing can be compared."""
    result = dm.cmd_check_missing_finalize_steps(_ns(plan_dir=str(tmp_path), project_root=str(tmp_path)))

    assert result['status'] == 'ok'
    assert result['missing_count'] == 0


def test_cmd_check_missing_finalize_steps_reports_dropped_project_step(tmp_path: Path):
    """cmd_check_missing_finalize_steps surfaces a shipped project: step absent from steps."""
    project_root = tmp_path / 'repo'
    skill_dir = project_root / '.claude' / 'skills' / 'finalize-step-custom'
    skill_dir.mkdir(parents=True)
    (skill_dir / 'SKILL.md').write_text('# finalize-step-custom\n')
    plan_dir = project_root / '.plan'
    plan_dir.mkdir(parents=True)
    (plan_dir / 'marshal.json').write_text(
        json.dumps({'plan': {'phase-6-finalize': {'steps': ['default:push']}}})
    )

    result = dm.cmd_check_missing_finalize_steps(
        _ns(plan_dir=str(plan_dir), project_root=str(project_root))
    )

    assert result['status'] == 'missing'
    assert 'project:finalize-step-custom' in result['missing_project_finalize_steps']


# =============================================================================
# check-staleness / run_preflight (health-menu staleness preflight)
# =============================================================================


def _fake_subprocess(monkeypatch, *, returncode: int, stdout: str = '', stderr: str = ''):
    """Replace dm's module-global ``subprocess`` with a call-recording fake.

    Returns the ``calls`` dict; ``calls['cmd']`` holds the argv the code under
    test passed to ``subprocess.run``.
    """
    import types

    calls: dict = {}

    class _Result:
        pass

    result = _Result()
    result.returncode = returncode
    result.stdout = stdout
    result.stderr = stderr

    def _fake_run(cmd, capture_output=False, text=False, timeout=None):
        calls['cmd'] = cmd
        calls['timeout'] = timeout
        return result

    monkeypatch.setattr(dm, 'subprocess', types.SimpleNamespace(run=_fake_run, TimeoutExpired=subprocess.TimeoutExpired))
    return calls


def test_run_preflight_routes_to_generate_executor_preflight(monkeypatch):
    """run_preflight invokes the sibling generate_executor.py with the 'preflight' verb."""
    calls = _fake_subprocess(
        monkeypatch,
        returncode=0,
        stdout='status: success\nexecutor_action: fresh\nmarshal_status: fresh\n',
    )

    result = dm.run_preflight()

    cmd = calls['cmd']
    assert cmd[0] == 'python3'
    assert cmd[-1] == 'preflight'
    assert cmd[1].endswith('generate_executor.py')
    assert 'tools-script-executor' in cmd[1]
    assert result['status'] == 'success'
    assert result['executor_action'] == 'fresh'
    assert result['marshal_status'] == 'fresh'


def test_run_preflight_error_when_generator_missing(tmp_path: Path, monkeypatch):
    """run_preflight returns a structured error when generate_executor.py is absent."""
    monkeypatch.setattr(dm, '_generate_executor_script', lambda: tmp_path / 'nope.py')

    result = dm.run_preflight()

    assert result['status'] == 'error'
    assert 'not found' in result['error']


def test_run_preflight_error_on_nonzero_exit(monkeypatch):
    """run_preflight surfaces the subprocess stderr when the preflight verb exits non-zero."""
    _fake_subprocess(monkeypatch, returncode=1, stderr='boom')

    result = dm.run_preflight()

    assert result['status'] == 'error'
    assert result['error'] == 'boom'


def test_run_preflight_error_on_unparseable_output(monkeypatch):
    """run_preflight returns an error when the preflight output does not parse to a dict."""
    _fake_subprocess(monkeypatch, returncode=0, stdout='')

    result = dm.run_preflight()

    assert result['status'] == 'error'


def test_run_preflight_passes_timeout_to_subprocess(monkeypatch):
    """run_preflight bounds the subprocess.run call with a finite timeout."""
    calls = _fake_subprocess(
        monkeypatch,
        returncode=0,
        stdout='status: success\nexecutor_action: fresh\nmarshal_status: fresh\n',
    )

    dm.run_preflight()

    assert calls['timeout'] == 60


def test_run_preflight_error_on_timeout(monkeypatch):
    """run_preflight returns a structured error instead of hanging when the subprocess times out."""
    import types

    def _timeout_run(cmd, capture_output=False, text=False, timeout=None):
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=timeout)

    monkeypatch.setattr(
        dm, 'subprocess', types.SimpleNamespace(run=_timeout_run, TimeoutExpired=subprocess.TimeoutExpired)
    )

    result = dm.run_preflight()

    assert result['status'] == 'error'
    assert 'timed out' in result['error']


def test_run_preflight_error_on_subprocess_oserror(monkeypatch):
    """run_preflight returns a structured error when the subprocess raises OSError."""
    import types

    def _raising_run(cmd, capture_output=False, text=False, timeout=None):
        raise OSError('python3 not found')

    monkeypatch.setattr(
        dm, 'subprocess', types.SimpleNamespace(run=_raising_run, TimeoutExpired=subprocess.TimeoutExpired)
    )

    result = dm.run_preflight()

    assert result['status'] == 'error'
    assert 'preflight execution failed' in result['error']


def test_cmd_check_staleness_surfaces_preflight_toon(monkeypatch):
    """cmd_check_staleness surfaces the run_preflight TOON verbatim."""
    monkeypatch.setattr(
        dm,
        'run_preflight',
        lambda: {'status': 'success', 'executor_action': 'regenerated', 'marshal_status': 'stale'},
    )

    result = dm.cmd_check_staleness(_ns())

    assert result['status'] == 'success'
    assert result['executor_action'] == 'regenerated'
    assert result['marshal_status'] == 'stale'


def test_generate_executor_script_path_resolves_to_sibling_skill():
    """_generate_executor_script points at the tools-script-executor generator."""
    path = dm._generate_executor_script()

    assert path.name == 'generate_executor.py'
    assert path.parent.name == 'scripts'
    assert path.parent.parent.name == 'tools-script-executor'
    # The generator actually ships at the resolved path in the marketplace tree.
    assert path.is_file()


# =============================================================================
# main() dispatch
# =============================================================================


def test_main_mode_dispatch(tmp_path: Path, monkeypatch, capsys):
    """main() routes the 'mode' subcommand and prints a TOON result."""
    monkeypatch.setattr(sys, 'argv', ['determine_mode', 'mode', '--plan-dir', str(tmp_path)])

    rc = dm.main()

    assert rc == 0
    assert 'mode: wizard' in capsys.readouterr().out


def test_main_check_structure_dispatch(tmp_path: Path, monkeypatch, capsys):
    """main() routes 'check-structure' and reports the missing status."""
    monkeypatch.setattr(
        sys, 'argv', ['determine_mode', 'check-structure', '--plan-dir', str(tmp_path)]
    )

    rc = dm.main()

    assert rc == 0
    assert 'check_status: missing' in capsys.readouterr().out


def test_main_check_working_prefixes_dispatch(tmp_path: Path, monkeypatch, capsys):
    """main() routes 'check-working-prefixes' and reports ok for a complete config."""
    _write_project_marshal(tmp_path, {'working_prefixes': _default_prefixes()})
    monkeypatch.setattr(
        sys, 'argv', ['determine_mode', 'check-working-prefixes', '--plan-dir', str(tmp_path)]
    )

    rc = dm.main()

    assert rc == 0
    assert 'status: ok' in capsys.readouterr().out


def test_main_check_staleness_dispatch(monkeypatch, capsys):
    """main() registers the 'check-staleness' health-menu option and routes it to the preflight.

    The subparser is present (no argparse rejection) and the command routes to
    run_preflight, whose TOON is surfaced on stdout. run_preflight is stubbed so
    the test does not shell out to the real generator.
    """
    monkeypatch.setattr(
        dm,
        'run_preflight',
        lambda: {'status': 'success', 'executor_action': 'fresh', 'marshal_status': 'fresh'},
    )
    monkeypatch.setattr(sys, 'argv', ['determine_mode', 'check-staleness'])

    rc = dm.main()

    assert rc == 0
    out = capsys.readouterr().out
    assert 'status: success' in out
    assert 'executor_action: fresh' in out
    assert 'marshal_status: fresh' in out


# =============================================================================
# helpers
# =============================================================================


class _NS:
    """Minimal attribute bag standing in for argparse.Namespace."""

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def _ns(**kwargs):
    """Construct a namespace-like object for command-handler calls."""
    return _NS(**kwargs)
