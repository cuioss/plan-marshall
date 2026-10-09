# SPDX-License-Identifier: FSL-1.1-ALv2
"""Destination-symlink tests for the component-tree deploy of marketplace/targets/sync.py.

The deploy never acts through a symbolic link it finds in an install
location. A link at a path it would write, chmod, descend into or prune
through is refused as that target's ``error`` result, naming the link; a
stale link the generated tree no longer holds is removed as a link.

Every refusal case starts from a real previous install whose source has
since changed and which carries a stale managed skill, so an install tree
that is byte-identical after the run proves the refusal preceded every
mutation — not merely the one behind the link.
"""

from __future__ import annotations

import io
import os
import shutil
import stat
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

import pytest
from toon_parser import parse_toon

from conftest import PROJECT_ROOT, run_script
from marketplace.targets.sync import (
    TARGET_CONFIGS,
    DestinationLinkRefused,
    _deploy_agent,
    _deploy_command,
    _deploy_root_assets,
    _deploy_skill,
    _prune_managed,
    main,
    sync_target,
)

SYNC_SCRIPT = PROJECT_ROOT / 'marketplace' / 'targets' / 'sync.py'

SENTINEL = b'operator data, not ours\n'

#: Every install path the opencode deploy writes or descends into, with the
#: kind of entry the link planted there points at.
REFUSED_LINK_SITES = [
    ('skills', 'dir'),
    ('skills/demo-skill', 'dir'),
    ('skills/demo-skill/SKILL.md', 'file'),
    ('skills/demo-skill/refs', 'dir'),
    ('agents', 'dir'),
    ('agents/demo-agent.md', 'file'),
    ('commands', 'dir'),
    ('commands/demo-cmd.md', 'file'),
    ('opencode.json', 'file'),
]


class Sandbox(NamedTuple):
    source: Path
    install: Path
    outside: Path


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


def _make_opencode_source(source: Path, marker: str) -> None:
    _write(source / 'skill' / 'demo-skill' / 'SKILL.md', f'---\nname: demo-skill\n---\n{marker}\n')
    _write(source / 'skill' / 'demo-skill' / 'refs' / 'guide.md', f'guide {marker}\n')
    _write(source / 'agent' / 'demo-agent.md', f'agent {marker}\n')
    _write(source / 'command' / 'demo-cmd.md', f'command {marker}\n')
    _write(source / 'opencode.json', f'{{"marker": "{marker}"}}\n')


def _snapshot(root: Path) -> dict[str, tuple[object, ...]]:
    """Every entry under ``root`` with its kind, mode and bytes; links are not followed."""
    entries: dict[str, tuple[object, ...]] = {}
    for current, dirnames, filenames in os.walk(root):
        for name in dirnames + filenames:
            path = Path(current) / name
            rel = path.relative_to(root).as_posix()
            if path.is_symlink():
                entries[rel] = ('link', os.readlink(path))
            elif path.is_dir():
                entries[rel] = ('dir', stat.S_IMODE(path.stat().st_mode))
            else:
                entries[rel] = ('file', stat.S_IMODE(path.stat().st_mode), path.read_bytes())
    return entries


def _relink(path: Path, target: Path) -> Path:
    """Replace whatever is at ``path`` with a link to ``target``."""
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink(missing_ok=True)
    path.symlink_to(target, target_is_directory=target.is_dir())
    return path


def _make_outside(outside: Path) -> None:
    """Operator data outside the install tree, shaped so an unguarded sync would destroy it.

    ``demo-old`` carries a managed-looking name the prune would remove, and
    ``keep.txt`` is a file no generated skill holds.
    """
    outside.mkdir()
    (outside / 'keep.txt').write_bytes(SENTINEL)
    (outside / 'keep.txt').chmod(0o600)
    (outside / 'demo-old').mkdir()
    (outside / 'demo-old' / 'data.txt').write_bytes(SENTINEL)


@pytest.fixture
def sandbox(tmp_path: Path) -> Sandbox:
    """A previous opencode install whose source has since changed, plus outside data.

    The install also holds the stale managed skill ``demo-old``, which a sync
    that is not refused removes.
    """
    box = Sandbox(tmp_path / 'source', tmp_path / 'install', tmp_path / 'outside')
    _make_opencode_source(box.source, 'v1')
    assert sync_target('opencode', source=box.source, dest=box.install, stdout=io.StringIO()) == 0
    _write(box.install / 'skills' / 'demo-old' / 'SKILL.md', 'stale\n')
    _make_opencode_source(box.source, 'v2')
    _make_outside(box.outside)
    return box


def _sync(box: Sandbox, capsys: pytest.CaptureFixture[str], *extra: str) -> tuple[int, dict]:
    argv = ['--target', 'opencode', '--source', str(box.source), '--target-dir', str(box.install), *extra]
    exit_code = main(argv)
    captured = capsys.readouterr()
    assert captured.err == ''
    return exit_code, parse_toon(captured.out)


def _plant(box: Sandbox, site: str, kind: str) -> Path:
    return _relink(box.install / site, box.outside if kind == 'dir' else box.outside / 'keep.txt')


@pytest.mark.parametrize(('site', 'kind'), REFUSED_LINK_SITES, ids=[site for site, _ in REFUSED_LINK_SITES])
@pytest.mark.parametrize('dry_run', [False, True], ids=['real-run', 'dry-run'])
def test_link_at_a_written_path_is_refused_and_nothing_is_changed(
    site: str, kind: str, dry_run: bool, sandbox: Sandbox, capsys: pytest.CaptureFixture[str]
):
    """A refused link is named, kept, and neither its target nor the rest of the install changes."""
    link = _plant(sandbox, site, kind)
    install_before = _snapshot(sandbox.install)
    outside_before = _snapshot(sandbox.outside)

    exit_code, data = _sync(sandbox, capsys, *(['--dry-run'] if dry_run else []))

    assert exit_code == 1
    assert data['status'] == 'error'
    assert data['target'] == 'opencode'
    assert 'opencode sync refused' in data['summary_message']
    assert str(link) in data['summary_message']
    assert _snapshot(sandbox.outside) == outside_before
    assert _snapshot(sandbox.install) == install_before


def test_sync_without_a_link_updates_the_install_and_prunes_the_stale_skill(
    sandbox: Sandbox, capsys: pytest.CaptureFixture[str]
):
    """Control: the fixture's pending changes do land when nothing is refused."""
    exit_code, data = _sync(sandbox, capsys)

    assert exit_code == 0
    assert data['status'] == 'success'
    assert 'v2' in (sandbox.install / 'skills' / 'demo-skill' / 'SKILL.md').read_text(encoding='utf-8')
    assert 'v2' in (sandbox.install / 'opencode.json').read_text(encoding='utf-8')
    assert not (sandbox.install / 'skills' / 'demo-old').exists()


def test_executable_root_asset_link_is_not_chmodded_through(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    """The antigravity ``install.sh`` link is refused; its target keeps its bytes and its mode."""
    source, install, outside = tmp_path / 'source', tmp_path / 'install', tmp_path / 'outside'
    _write(source / 'skills' / 'demo-skill' / 'SKILL.md', '---\nname: demo-skill\n---\n')
    _write(source / 'install.sh', '#!/bin/sh\n')
    _make_outside(outside)
    install.mkdir()
    link = _relink(install / 'install.sh', outside / 'keep.txt')
    outside_before = _snapshot(outside)

    exit_code = main(['--target', 'antigravity', '--source', str(source), '--target-dir', str(install)])

    data = parse_toon(capsys.readouterr().out)
    assert exit_code == 1
    assert data['status'] == 'error'
    assert str(link) in data['summary_message']
    assert _snapshot(outside) == outside_before
    assert _snapshot(install) == {'install.sh': ('link', str(outside / 'keep.txt'))}


def test_stale_managed_skill_link_is_removed_as_a_link(sandbox: Sandbox, capsys: pytest.CaptureFixture[str]):
    """A stale managed skill entry that is a link is unlinked; the sync succeeds."""
    link = _relink(sandbox.install / 'skills' / 'demo-old', sandbox.outside / 'demo-old')
    outside_before = _snapshot(sandbox.outside)

    exit_code, data = _sync(sandbox, capsys)

    assert exit_code == 0
    assert data['status'] == 'success'
    assert data['removed'] == [{'kind': 'skills', 'name': 'demo-old'}]
    assert not link.is_symlink()
    assert _snapshot(sandbox.outside) == outside_before


def test_stale_managed_skill_link_survives_a_dry_run(sandbox: Sandbox, capsys: pytest.CaptureFixture[str]):
    link = _relink(sandbox.install / 'skills' / 'demo-old', sandbox.outside / 'demo-old')

    exit_code, data = _sync(sandbox, capsys, '--dry-run')

    assert exit_code == 0
    assert data['removed'] == [{'kind': 'skills', 'name': 'demo-old'}]
    assert link.is_symlink()


def test_stale_links_inside_a_real_skill_directory_are_removed_as_links(
    sandbox: Sandbox, capsys: pytest.CaptureFixture[str]
):
    """Links the generated skill does not hold are unlinked, never walked or written through."""
    skill = sandbox.install / 'skills' / 'demo-skill'
    dir_link = _relink(skill / 'legacy', sandbox.outside)
    file_link = _relink(skill / 'old.md', sandbox.outside / 'keep.txt')
    outside_before = _snapshot(sandbox.outside)

    exit_code, data = _sync(sandbox, capsys)

    assert exit_code == 0
    assert data['status'] == 'success'
    assert not dir_link.is_symlink()
    assert not file_link.is_symlink()
    assert _snapshot(sandbox.outside) == outside_before


def test_symlinked_destination_root_is_synced_into(sandbox: Sandbox, tmp_path: Path):
    """Control: the destination root itself may be a link — it is resolved once."""
    root_link = tmp_path / 'install-link'
    root_link.symlink_to(sandbox.install, target_is_directory=True)

    exit_code = sync_target('opencode', source=sandbox.source, dest=root_link, stdout=io.StringIO())

    assert exit_code == 0
    assert root_link.is_symlink()
    assert 'v2' in (sandbox.install / 'agents' / 'demo-agent.md').read_text(encoding='utf-8')


def _prune(box: Sandbox) -> None:
    _prune_managed(box.install, {'demo-skill'}, {'demo-cmd.md'}, {'demo'}, dry_run=False)


DEPLOY_STEPS: dict[str, tuple[str, str, Callable[[Sandbox], object]]] = {
    'skill': (
        'skills/demo-skill',
        'dir',
        lambda box: _deploy_skill(box.source / 'skill' / 'demo-skill', box.install, dry_run=False),
    ),
    'agent': (
        'agents/demo-agent.md',
        'file',
        lambda box: _deploy_agent(box.source / 'agent' / 'demo-agent.md', box.install, dry_run=False),
    ),
    'command': (
        'commands',
        'dir',
        lambda box: _deploy_command(box.source / 'command' / 'demo-cmd.md', box.install, dry_run=False),
    ),
    'root-asset': (
        'opencode.json',
        'file',
        lambda box: _deploy_root_assets(box.source, box.install, TARGET_CONFIGS['opencode'], dry_run=False),
    ),
    'prune': ('skills', 'dir', _prune),
}


@pytest.mark.parametrize('step', sorted(DEPLOY_STEPS))
def test_each_deploy_step_refuses_a_link_on_its_own(step: str, sandbox: Sandbox):
    """No step relies on the up-front check: each refuses the link at the point of its write."""
    site, kind, run = DEPLOY_STEPS[step]
    link = _plant(sandbox, site, kind)
    install_before = _snapshot(sandbox.install)
    outside_before = _snapshot(sandbox.outside)

    with pytest.raises(DestinationLinkRefused) as excinfo:
        run(sandbox)

    assert str(link) in str(excinfo.value)
    assert _snapshot(sandbox.outside) == outside_before
    assert _snapshot(sandbox.install) == install_before


def test_refusal_in_an_all_targets_run_fails_that_target_only(tmp_path: Path):
    """One refused harness is an ``error`` row; the next harness is still synced."""
    project, home, outside = tmp_path / 'project', tmp_path / 'home', tmp_path / 'outside'
    _write(project / 'target' / 'opencode' / 'skill' / 'demo-skill' / 'SKILL.md', '---\nname: demo-skill\n---\n')
    _write(project / 'target' / 'antigravity' / 'skills' / 'demo-skill' / 'SKILL.md', '---\nname: demo-skill\n---\n')
    _make_outside(outside)
    opencode_install = home / '.config' / 'opencode'
    opencode_install.mkdir(parents=True)
    link = _relink(opencode_install / 'skills', outside)
    outside_before = _snapshot(outside)

    result = run_script(SYNC_SCRIPT, cwd=project, timeout=60, env_overrides={'HOME': str(home)})

    assert result.returncode == 1
    assert 'Traceback' not in result.stderr
    data = parse_toon(result.stdout)
    assert data['opencode']['status'] == 'error'
    assert str(link) in data['opencode']['summary_message']
    assert data['antigravity']['status'] == 'success'
    assert (home / '.gemini' / 'config' / 'plugins' / 'plan-marshall' / 'skills' / 'demo-skill' / 'SKILL.md').is_file()
    assert _snapshot(outside) == outside_before
