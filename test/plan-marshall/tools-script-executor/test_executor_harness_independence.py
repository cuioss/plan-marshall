#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""One executor serves every harness (PLAN-LB-94 D1-D5).

The plan retires the per-harness executor: the generated file must be a function
of the checkout and the installed roots, never of the harness that generated it,
and a call from any harness must dispatch. Each test names the deliverable it
evidences and isolates its own project tree under ``tmp_path``, so no case can
read or write the checkout's own executor.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import types
from pathlib import Path

import pytest

from conftest import MARKETPLACE_ROOT, load_script_module

ge = load_script_module('plan-marshall', 'tools-script-executor', 'generate_executor.py')

#: Every platform env signal the runtime detector reads.
_SIGNALS = ('CLAUDE_CODE_SESSION_ID', 'OPENCODE', 'ANTIGRAVITY_AGENT')

#: signal -> harness, one entry per supported harness.
_ENV_SIGNAL = {
    'claude': ('CLAUDE_CODE_SESSION_ID', '1'),
    'opencode': ('OPENCODE', '1'),
    'antigravity': ('ANTIGRAVITY_AGENT', '1'),
}

#: The harness roster, restated so a new harness fails the matrix instead of
#: silently escaping it.
_HARNESSES = ('claude', 'opencode', 'antigravity')


def _clear_signals(monkeypatch: pytest.MonkeyPatch) -> None:
    for signal in _SIGNALS:
        monkeypatch.delenv(signal, raising=False)


def _generate(
    monkeypatch: pytest.MonkeyPatch,
    plan_dir: Path,
    target: str,
    *,
    harness: str | None = None,
    mappings: dict[str, str] | None = None,
    roots: tuple[tuple[str, str], ...] | None = None,
    versions: tuple[tuple[str, str], ...] | None = None,
) -> Path:
    """Generate a real executor into ``plan_dir`` and return its path.

    ``roots`` / ``versions`` replace the machine's installed harnesses, so a
    fixture can own both installs a case is about. Everything else runs the
    production generation path.
    """
    plan_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv('PLAN_BASE_DIR', str(plan_dir))
    _clear_signals(monkeypatch)
    if harness is not None:
        monkeypatch.setenv(*_ENV_SIGNAL[harness])
    if roots is not None:
        monkeypatch.setattr(ge, 'installed_harness_roots', lambda: list(roots))
    if versions is not None:
        monkeypatch.setattr(ge, 'installed_harness_versions', lambda _roots=None: list(versions))
    result = ge.generate_executor(mappings or {}, MARKETPLACE_ROOT, dry_run=False, target=target)
    assert result['status'] == 'success', result
    executor = plan_dir / 'execute-script.py'
    assert executor.is_file()
    return executor


def _run(executor: Path, args: list[str], harness: str | None) -> subprocess.CompletedProcess[str]:
    """Run ``executor`` with exactly one platform signal set."""
    env = {key: value for key, value in os.environ.items() if key not in _SIGNALS}
    env.pop('PYTHONPATH', None)
    if harness is not None:
        signal, value = _ENV_SIGNAL[harness]
        env[signal] = value
    return subprocess.run(
        [sys.executable, str(executor), *args],
        cwd=executor.parent.parent,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _write_script(path: Path, body: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding='utf-8')
    return path


def _flat_install_script(root: Path, bundle: str, skill: str, script: str, body: str) -> Path:
    """Create ``{root}/{bundle}-{skill}/scripts/{script}.py`` (the flat deploy shape)."""
    return _write_script(root / f'{bundle}-{skill}' / 'scripts' / f'{script}.py', body)


def _nested_install_script(root: Path, bundle: str, version: str, skill: str, script: str, body: str) -> Path:
    """Create ``{root}/{bundle}/{version}/skills/{skill}/scripts/{script}.py`` (nested shape)."""
    return _write_script(root / bundle / version / 'skills' / skill / 'scripts' / f'{script}.py', body)


def _manifest(root: Path, version: str, *, executor_changed_at: str = '0.1.0') -> None:
    root.mkdir(parents=True, exist_ok=True)
    payload: dict[str, str] = {'version': version}
    if executor_changed_at:
        payload['executor_changed_at_version'] = executor_changed_at
    (root / 'dist-manifest.json').write_text(json.dumps(payload), encoding='utf-8')


# =============================================================================
# D1 — the generated executor does not depend on which harness generated it
# =============================================================================


def test_d1_the_three_targets_emit_byte_identical_executors(tmp_path, monkeypatch):
    """One fixture, three ``--target`` values × three ambient signals: one file.

    The retired design stamped the harness, its plugin root and a per-target
    resolver body into the file, so any two of these nine generations differed.
    """
    blobs: dict[tuple[str, str], bytes] = {}
    for target in _HARNESSES:
        for harness in (None, *_HARNESSES):
            plan_dir = tmp_path / f'{target}-{harness or "terminal"}' / '.plan'
            executor = _generate(monkeypatch, plan_dir, target, harness=harness)
            blobs[(target, harness or 'terminal')] = executor.read_bytes()

    unique = set(blobs.values())
    assert len(unique) == 1, (
        'the executor bytes must not depend on --target or on the ambient harness; '
        f'{len(unique)} distinct files were generated'
    )


def test_d1_the_stamp_is_informational(tmp_path, monkeypatch):
    """``GENERATED_FOR`` carries a fixed value and no harness name is a lock."""
    executor = _generate(monkeypatch, tmp_path / '.plan', 'claude')
    text = executor.read_text(encoding='utf-8')

    assert "GENERATED_FOR = 'any'" in text
    assert '_EXECUTOR_TARGET' not in text, 'the retired lock stamp must be gone'


def test_d1_the_plugin_root_and_recovery_roots_list_every_harness(tmp_path, monkeypatch):
    """Both root stamps name every installed harness, not the generating one."""
    roots = (
        ('claude', str(tmp_path / 'claude-root')),
        ('opencode', str(tmp_path / 'opencode-root')),
        ('antigravity', str(tmp_path / 'antigravity-root')),
    )
    executor = _generate(monkeypatch, tmp_path / '.plan', 'opencode', roots=roots)
    text = executor.read_text(encoding='utf-8')

    for harness, root in roots:
        assert f"('{harness}', '{root}')" in text, f'{harness} root missing from _INSTALLED_ROOTS'
        assert f"'{root}'" in text
    assert "EXECUTOR_PLUGIN_ROOT = '" in text
    # The informational plugin root is never the invoking harness's own root
    # alone: with no tree above the fixture it is the joined root list.
    plugin_root_line = next(line for line in text.splitlines() if line.startswith('EXECUTOR_PLUGIN_ROOT'))
    assert 'opencode-root' in plugin_root_line


# =============================================================================
# D2 — no harness refuses another harness's executor; a call dispatches
# =============================================================================


def test_d2_one_generated_executor_dispatches_under_every_harness(tmp_path, monkeypatch):
    """An executor generated under one harness dispatches for all three."""
    script = _write_script(
        tmp_path / 'scripts' / 'tool.py',
        "import sys\nprint('dispatched', *sys.argv[1:])\n",
    )
    executor = _generate(
        monkeypatch,
        tmp_path / 'project' / '.plan',
        'claude',
        harness='claude',
        mappings={'demo:skill:tool': str(script)},
    )

    for harness in _HARNESSES:
        result = _run(executor, ['demo:skill:tool', 'arg'], harness)
        assert result.returncode == 0, f'{harness}: {result.stdout}{result.stderr}'
        assert 'dispatched arg' in result.stdout, f'{harness}: {result.stdout}{result.stderr}'
        assert 'executor_target_mismatch' not in result.stdout


def test_d2_a_foreign_install_resolves_with_one_note(tmp_path, monkeypatch):
    """With only the other harness's install present, the call resolves and notes it."""
    foreign_root = tmp_path / 'claude-install'
    own_root = tmp_path / 'opencode-install'
    own_root.mkdir()
    foreign_script = _nested_install_script(
        foreign_root,
        'demo',
        '0.1.9',
        'skill',
        'tool',
        "print('from the foreign install')\n",
    )
    roots = (('opencode', str(own_root)), ('claude', str(foreign_root)))
    executor = _generate(
        monkeypatch,
        tmp_path / 'project' / '.plan',
        'opencode',
        harness='opencode',
        mappings={'demo:skill:tool': str(foreign_script)},
        roots=roots,
    )

    result = _run(executor, ['demo:skill:tool'], 'opencode')

    assert result.returncode == 0, result.stdout + result.stderr
    assert 'from the foreign install' in result.stdout
    note_lines = [line for line in result.stderr.splitlines() if line.startswith('note:')]
    assert len(note_lines) == 1, result.stderr
    assert 'claude install' in note_lines[0]


def test_d2_a_normal_path_stays_silent(tmp_path, monkeypatch):
    """A call served by the tree says nothing on stderr."""
    checkout = tmp_path / 'checkout'
    tree_script = _write_script(
        checkout / 'marketplace' / 'bundles' / 'demo' / 'skills' / 'skill' / 'scripts' / 'tool.py',
        "print('from the tree')\n",
    )
    executor = _generate(monkeypatch, checkout / '.plan', 'opencode', mappings={'demo:skill:tool': str(tree_script)})

    result = _run(executor, ['demo:skill:tool'], 'opencode')

    assert result.returncode == 0
    assert 'from the tree' in result.stdout
    assert 'note:' not in result.stderr


# =============================================================================
# D3 — mappings and surfaces do not bind the executor to the generating install
# =============================================================================


def test_d3_nested_and_flat_notations_resolve_to_the_tree(tmp_path, monkeypatch):
    """Every notation, the four nested-shape entries included, resolves to the tree."""
    checkout = tmp_path / 'checkout'
    flat = _write_script(
        checkout / 'marketplace' / 'bundles' / 'demo' / 'skills' / 'flat' / 'scripts' / 'tool.py',
        "print('tree-flat')\n",
    )
    nested = _write_script(
        checkout / 'marketplace' / 'bundles' / 'demo' / 'skills' / 'nested' / 'scripts' / 'workflow' / 'tool.py',
        "print('tree-nested')\n",
    )
    # Mappings point at a deployed copy, exactly as a cache-first discovery would.
    deployed = tmp_path / 'deployed'
    deployed_flat = _flat_install_script(deployed, 'demo', 'flat', 'tool', "print('deployed-flat')\n")
    deployed_nested = _nested_install_script(
        deployed, 'demo', '0.1.1', 'nested', 'workflow/tool', "print('deployed-nested')\n"
    )
    executor = _generate(
        monkeypatch,
        checkout / '.plan',
        'claude',
        mappings={'demo:flat:tool': str(deployed_flat), 'demo:nested:tool': str(deployed_nested)},
    )

    for harness in ('claude', 'opencode'):
        flat_result = _run(executor, ['demo:flat:tool'], harness)
        nested_result = _run(executor, ['demo:nested:tool'], harness)
        assert 'tree-flat' in flat_result.stdout, f'{harness} flat: {flat_result.stdout}{flat_result.stderr}'
        assert 'tree-nested' in nested_result.stdout, f'{harness} nested: {nested_result.stdout}{nested_result.stderr}'
    assert Path(flat).is_file() and Path(nested).is_file()


def test_d3_each_harness_resolves_its_own_install_and_its_own_pythonpath(tmp_path, monkeypatch):
    """Two installs, one executor: each harness runs its own copy's helpers."""
    claude_root = tmp_path / 'claude-install'
    opencode_root = tmp_path / 'opencode-install'
    probe = "import os\nprint('{origin}', os.environ.get('PYTHONPATH', '').split(':')[0])\n"
    _nested_install_script(claude_root, 'demo', '0.1.9', 'skill', 'tool', probe.format(origin='claude'))
    _flat_install_script(opencode_root, 'demo', 'skill', 'tool', probe.format(origin='opencode'))
    roots = (('claude', str(claude_root)), ('opencode', str(opencode_root)))
    versions = (('claude', '0.1.9'), ('opencode', '0.1.9'))
    executor = _generate(
        monkeypatch,
        tmp_path / 'project' / '.plan',
        'claude',
        mappings={},
        roots=roots,
        versions=versions,
    )

    for harness, own_root in (('claude', claude_root), ('opencode', opencode_root)):
        result = _run(executor, ['demo:skill:tool'], harness)
        assert result.returncode == 0, result.stdout + result.stderr
        origin, first_pythonpath = result.stdout.split(None, 1)
        assert origin == harness, result.stdout
        assert str(own_root.resolve()) in first_pythonpath, (
            f"{harness} ran its own script but fed it another root's helpers: {first_pythonpath}"
        )


def test_d3_a_surface_is_only_applied_to_the_script_it_came_from(tmp_path, monkeypatch):
    """A surface derived from one version cannot reject another version's flag."""
    claude_root = tmp_path / 'claude-install'
    opencode_root = tmp_path / 'opencode-install'
    # Install A's script does NOT declare --new-flag, so the derived surface
    # rejects it. Install B's script does declare it.
    old_script = _nested_install_script(
        claude_root,
        'demo',
        '0.1.1',
        'skill',
        'tool',
        (
            'import argparse\n'
            'parser = argparse.ArgumentParser()\n'
            "parser.add_argument('--old-flag')\n"
            'parser.parse_args()\n'
            "print('old-script')\n"
        ),
    )
    _flat_install_script(
        opencode_root,
        'demo',
        'skill',
        'tool',
        (
            'import argparse\n'
            'parser = argparse.ArgumentParser()\n'
            "parser.add_argument('--old-flag')\n"
            "parser.add_argument('--new-flag', action='store_true')\n"
            'parser.parse_args()\n'
            "print('new-script')\n"
        ),
    )
    roots = (('claude', str(claude_root)), ('opencode', str(opencode_root)))
    executor = _generate(
        monkeypatch,
        tmp_path / 'project' / '.plan',
        'claude',
        mappings={'demo:skill:tool': str(old_script)},
        roots=roots,
    )

    # Control: under the harness that owns the script the surface applies, so the
    # flag it never declared is still refused. Without this arm the case would
    # pass on an executor that validates nothing at all.
    control = _run(executor, ['demo:skill:tool', '--new-flag'], 'claude')
    assert control.returncode == 2, control.stdout + control.stderr
    assert 'unknown_flag' in control.stdout

    # The other harness resolves a NEWER script whose surface was never embedded:
    # the embedded surface must be ignored and the call must spawn.
    result = _run(executor, ['demo:skill:tool', '--new-flag'], 'opencode')
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'new-script' in result.stdout
    assert 'unknown_flag' not in result.stdout


# =============================================================================
# D4 — staleness and version are judged per runtime harness
# =============================================================================


def test_d4_the_executor_carries_a_version_per_harness(tmp_path, monkeypatch):
    """One stamp, three answers: each harness reads its own published version."""
    roots = (
        ('claude', str(tmp_path / 'claude-install')),
        ('opencode', str(tmp_path / 'opencode-install')),
        ('antigravity', str(tmp_path / 'antigravity-install')),
    )
    versions = (('claude', '0.1.5'), ('opencode', '0.1.2'), ('antigravity', ''))
    plan_dir = tmp_path / '.plan'
    executor = _generate(monkeypatch, plan_dir, 'claude', roots=roots, versions=versions)
    monkeypatch.setenv('PLAN_BASE_DIR', str(plan_dir))

    assert ge.read_executor_version('claude') == '0.1.5'
    assert ge.read_executor_version('opencode') == '0.1.2'
    # A harness with no published version falls back to the single stamp, which
    # is the newest installed version — never the generating harness's.
    assert ge.read_executor_version('antigravity') == '0.1.5'
    assert executor.read_text(encoding='utf-8').count("('claude', '0.1.5')") == 1


@pytest.mark.parametrize(('harness', 'version'), [('claude', '0.1.5'), ('opencode', '0.1.2')])
def test_d4_preflight_reports_the_running_harness_own_staleness(tmp_path, monkeypatch, harness, version):
    """``preflight`` under each harness reports that harness's own version."""
    claude_root = tmp_path / 'claude-install'
    opencode_root = tmp_path / 'opencode-install'
    _manifest(claude_root, '0.1.5')
    _manifest(opencode_root, '0.1.2')
    roots = (('claude', str(claude_root)), ('opencode', str(opencode_root)))
    versions = (('claude', '0.1.5'), ('opencode', '0.1.2'))
    plan_dir = tmp_path / '.plan'
    _generate(monkeypatch, plan_dir, 'claude', roots=roots, versions=versions)
    monkeypatch.setenv('PLAN_BASE_DIR', str(plan_dir))

    harness_root = {'claude': claude_root, 'opencode': opencode_root}[harness]
    monkeypatch.setattr(ge, 'get_base_path', lambda **kwargs: harness_root)
    args = types.SimpleNamespace(marketplace=False, marketplace_root=None, target=harness)

    result = ge.cmd_preflight(args)

    assert result['status'] == 'success', result
    assert result['executor_version'] == version, result
    # Neither harness is stale merely because the other one generated the file.
    assert result['executor_action'] == 'fresh', result
    assert result['installed_version'] == version, result


# =============================================================================
# D5 — regeneration converges; a harness difference is never a reason to rewrite
# =============================================================================


def test_d5_a_no_change_regeneration_leaves_the_file_untouched(tmp_path, monkeypatch):
    """Regenerating identical bytes does not rewrite the file or move its mtime."""
    plan_dir = tmp_path / '.plan'
    executor = _generate(monkeypatch, plan_dir, 'claude')
    before = executor.stat().st_mtime_ns
    original = executor.read_bytes()
    time.sleep(0.02)

    again = _generate(monkeypatch, plan_dir, 'opencode')

    assert again.read_bytes() == original
    assert again.stat().st_mtime_ns == before, 'an unchanged regeneration must not touch the file'


def test_d5_a_killed_generation_leaves_the_previous_executor_intact(tmp_path, monkeypatch):
    """A generation that dies after the temp write never damages the live file."""
    plan_dir = tmp_path / '.plan'
    executor = _generate(monkeypatch, plan_dir, 'claude')
    original = executor.read_bytes()

    def _boom(_src, _dst):
        raise OSError('simulated kill before replace')

    monkeypatch.setattr(ge.os, 'replace', _boom)
    monkeypatch.setattr(ge, 'newest_version', lambda _versions: '9.9.9')
    with pytest.raises(OSError):
        ge.generate_executor({}, MARKETPLACE_ROOT, dry_run=False, target='claude')

    assert executor.read_bytes() == original
    assert not (plan_dir / 'execute-script.py.tmp').exists()


def test_d5_interleaved_generations_converge_on_one_valid_file(tmp_path, monkeypatch):
    """Two harnesses alternating leave the same single valid file."""
    plan_dir = tmp_path / '.plan'
    first = _generate(monkeypatch, plan_dir, 'claude', harness='claude')
    reference = first.read_bytes()
    _generate(monkeypatch, plan_dir, 'opencode', harness='opencode')
    third = _generate(monkeypatch, plan_dir, 'antigravity', harness='antigravity')

    assert third.read_bytes() == reference
    compile(third.read_text(encoding='utf-8'), str(third), 'exec')


def test_d5_generation_leaves_the_checkout_executor_untouched(tmp_path, monkeypatch):
    """The group's own fixture writes never reach this checkout's executor.

    The generator resolves its target from ``PLAN_BASE_DIR``; a test that forgets
    to isolate that must fail here rather than silently rewrite the executor a
    running session dispatches through.
    """
    checkout_executor = Path(__file__).resolve().parents[3] / '.plan' / 'execute-script.py'
    assert checkout_executor.is_file(), f'expected the checkout executor at {checkout_executor}'
    before_bytes = checkout_executor.read_bytes()
    before_mtime = checkout_executor.stat().st_mtime_ns

    _generate(monkeypatch, tmp_path / '.plan', 'claude')

    assert checkout_executor.read_bytes() == before_bytes
    assert checkout_executor.stat().st_mtime_ns == before_mtime


_SHIPPED_TEXT = (
    Path(__file__).resolve().parents[3]
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'runbook-lane'
    / 'SKILL.md',
    Path(__file__).resolve().parents[3] / '.claude' / 'skills' / 'finalize-step-sync-plugin-cache' / 'SKILL.md',
    Path(__file__).resolve().parents[3]
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'marshall-steward'
    / 'SKILL.md',
)


@pytest.mark.parametrize('path', _SHIPPED_TEXT, ids=lambda p: p.parent.name)
def test_d5_no_shipped_text_regenerates_on_a_target_mismatch(path):
    """No lane, steward or finalize instruction cites the retired refusal."""
    if not path.is_file():
        pytest.skip(f'{path} is not present in this checkout')
    text = path.read_text(encoding='utf-8')

    assert 'executor_target_mismatch' not in text
    assert 'executor targets' not in text
    if path.parent.name == 'runbook-lane':
        # The positive rule, not only the absences: the lane must SAY that a
        # target difference is not a regeneration trigger.
        assert 'target difference is not a regeneration trigger' in text


# =============================================================================
# Review follow-ups: the cases the first pass left uncovered
# =============================================================================


def test_d3_rewrite_maps_a_nested_entry_to_the_tree(tmp_path, monkeypatch):
    """The mapping rewrite resolves a sub-directory entry by its OWN suffix.

    A ``{script}.py`` join silently leaves exactly these four entries pointing
    into the generating harness's install, which is the D3 defect.
    """
    tree = tmp_path / 'checkout' / 'marketplace' / 'bundles'
    tree_script = tree / 'demo' / 'skills' / 'skill' / 'scripts' / 'workflow' / 'tool.py'
    tree_script.parent.mkdir(parents=True)
    tree_script.write_text('# tree', encoding='utf-8')
    monkeypatch.setattr(ge, '_shared_get_base_path', lambda *args, **kwargs: tree)
    deployed = '/somewhere/install/demo/0.1.1/skills/skill/scripts/workflow/tool.py'

    rewritten = ge._rewrite_mappings_to_tree({'demo:skill:tool': deployed}, tree)

    assert rewritten['demo:skill:tool'] == str(tree_script.resolve())


def test_d3_pythonpath_on_a_tree_script_never_puts_a_foreign_install_first(tmp_path, monkeypatch):
    """A tree script's helpers come from the tree, never a foreign install's."""
    checkout = tmp_path / 'checkout'
    tree_script = _write_script(
        checkout / 'marketplace' / 'bundles' / 'demo' / 'skills' / 'skill' / 'scripts' / 'tool.py',
        ("import os\nprint('PYTHONPATH=' + os.environ.get('PYTHONPATH', '').split(':')[0])\n"),
    )
    foreign_root = tmp_path / 'foreign-install'
    _flat_install_script(foreign_root, 'demo', 'skill', 'tool', 'print("foreign")\n')
    roots = (('opencode', str(foreign_root)),)
    executor = _generate(
        monkeypatch,
        checkout / '.plan',
        'claude',
        mappings={'demo:skill:tool': str(tree_script)},
        roots=roots,
    )

    result = _run(executor, ['demo:skill:tool'], 'opencode')

    assert result.returncode == 0, result.stdout + result.stderr
    first = result.stdout.strip().removeprefix('PYTHONPATH=')
    assert str(checkout) in first, f'the tree must lead the PYTHONPATH, got {first}'
    assert str(foreign_root) not in first


def test_d4_executor_skew_judges_the_running_harness(tmp_path):
    """One executor, two harnesses, two verdicts — the running harness decides."""
    rl = load_script_module('plan-marshall', 'runbook-lane', 'runbook_lane.py', 'rl_skew_under_test')
    executor = tmp_path / 'execute-script.py'
    executor.write_text(
        "MARSHALL_VERSION = '0.1.5'\n"
        '_INSTALLED_VERSIONS = (\n'
        "    ('claude', '0.1.5'),\n"
        "    ('opencode', '0.1.2'),\n"
        ')\n',
        encoding='utf-8',
    )
    original = rl._lane_text_version
    rl._lane_text_version = lambda *args, **kwargs: '0.1.4'
    try:
        assert rl._executor_skew(executor, target='claude') == 'match'
        assert rl._executor_skew(executor, target='opencode') == 'skew'
    finally:
        rl._lane_text_version = original


def test_d4_a_harness_without_its_own_version_still_resolves_a_valid_notation(tmp_path, monkeypatch):
    """A valid notation with no copy anywhere resolves to nothing, not to a guess."""
    ns = types.ModuleType('resolver_valid_but_absent')
    module = load_script_module('plan-marshall', 'tools-script-executor', 'generate_executor.py', 'ge_absent')
    code = module.generate_target_aware_resolver_code('claude')
    ns.__dict__.update(
        {
            'Path': Path,
            'os': os,
            'SCRIPTS': {},
            '_INSTALLED_ROOTS': (('claude', str(tmp_path / 'nowhere')),),
            '_runtime_harness': lambda: 'claude',
            '__file__': str(tmp_path / 'checkout' / '.plan' / 'execute-script.py'),
        }
    )
    exec(compile(code, '<resolver>', 'exec'), ns.__dict__)

    assert ns._resolve_notation_by_target('demo:skill:tool') is None


def test_d4_hidden_version_dirs_are_skipped(tmp_path):
    """A hidden version directory carrying the script is not selected."""
    root = tmp_path / 'install'
    hidden = root / 'demo' / '.hidden-version' / 'skills' / 'skill' / 'scripts'
    hidden.mkdir(parents=True)
    (hidden / 'tool.py').write_text('# hidden', encoding='utf-8')

    ns = types.ModuleType('resolver_hidden_dir')
    code = ge.generate_target_aware_resolver_code('claude')
    ns.__dict__.update(
        {
            'Path': Path,
            'os': os,
            'SCRIPTS': {},
            '_INSTALLED_ROOTS': (('claude', str(root)),),
            '_runtime_harness': lambda: 'claude',
            '__file__': str(tmp_path / 'x' / 'execute-script.py'),
        }
    )
    exec(compile(code, '<resolver>', 'exec'), ns.__dict__)

    assert ns._resolve_notation_by_target('demo:skill:tool') is None


#: Snapshot of the checkout's own executor at module import, so the guards below
#: can prove this module never wrote it. The suite-wide half of D5's last clause
#: lives here because a shared-conftest guard would have to fail every session
#: that touched it — including sessions this plan does not own.
_CHECKOUT_EXECUTOR = Path(__file__).resolve().parents[3] / '.plan' / 'execute-script.py'
_CHECKOUT_BEFORE = (
    (_CHECKOUT_EXECUTOR.read_bytes(), _CHECKOUT_EXECUTOR.stat().st_mtime_ns) if _CHECKOUT_EXECUTOR.is_file() else None
)


def test_d5_zz_the_module_left_the_checkout_executor_untouched():
    """Session guard: nothing in this module rewrote the live executor."""
    if _CHECKOUT_BEFORE is None:
        pytest.skip('no checkout executor in this checkout')
    after = (_CHECKOUT_EXECUTOR.read_bytes(), _CHECKOUT_EXECUTOR.stat().st_mtime_ns)

    assert after == _CHECKOUT_BEFORE, 'a test in this module rewrote the checkout executor'
