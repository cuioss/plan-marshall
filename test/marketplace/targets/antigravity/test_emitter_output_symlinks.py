# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the Antigravity emitter's refusal to write through an output-side symlink.

Every file the emitter writes outside a skill directory — agents, their level
variants, commands, user-invocable command wrappers and the root-level files —
lands at a path that may already hold a link. A symlinked ``agents/`` or
``commands/`` directory is refused before anything is written; a link at an
emitted file path is replaced by the file.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import PROJECT_ROOT
from marketplace.targets.antigravity.emitter import emit_bundles

#: Content of the file placed outside the output tree; an emit must leave it byte-identical.
SENTINEL = b'outside the output tree\n'

_LEVEL_EXECUTOR = 'plan-marshall:extension-api/standards/ext-point-dynamic-level-executor'

#: Every output path the emitter writes outside a skill directory.
EMITTED_FILE_PATHS = (
    'agents/demo-agent.md',
    'agents/level-agent.md',
    'agents/level-agent-level-1.md',
    'commands/demo-cmd.md',
    'commands/demo-demo-skill.md',
    'plugin.json',
    'bundle-components.json',
    'install.sh',
    'README.adoc',
)


@pytest.fixture()
def antigravity_config_dir() -> Path:
    return Path(PROJECT_ROOT) / 'marketplace' / 'targets' / 'antigravity'


@pytest.fixture()
def marketplace(tmp_path: Path) -> Path:
    """Build a bundle with an agent, a level-executor agent, a command and a user-invocable skill."""
    root = tmp_path / 'bundles'
    bundle = root / 'demo'
    manifest = {
        'name': 'demo',
        'agents': ['./agents/demo-agent.md', './agents/level-agent.md'],
        'commands': ['./commands/demo-cmd.md'],
        'skills': ['./skills/demo-skill'],
    }
    files = {
        '.claude-plugin/plugin.json': json.dumps(manifest) + '\n',
        'skills/demo-skill/SKILL.md': '---\nname: demo-skill\ndescription: demo desc\nuser-invocable: true\n---\n# Body\n',
        'agents/demo-agent.md': (
            '---\nname: demo-agent\ndescription: demo agent\nmodel: sonnet\ntools: Read, Write\n---\nagent body\n'
        ),
        'agents/level-agent.md': (
            '---\nname: level-agent\ndescription: a level agent\ntools: Read, Write\n'
            f'implements: {_LEVEL_EXECUTOR}\nlevels: [level-1]\n---\nlevel body\n'
        ),
        'commands/demo-cmd.md': '---\nname: demo-cmd\ndescription: demo command\n---\ncommand body\n',
    }
    for rel, content in files.items():
        path = bundle / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')
    return root


@pytest.fixture()
def outside(tmp_path: Path) -> Path:
    """A directory outside the output tree holding one file an emit must never touch."""
    directory = tmp_path / 'outside'
    directory.mkdir()
    (directory / 'victim').write_bytes(SENTINEL)
    return directory


def _files_under(directory: Path) -> dict[str, bytes]:
    return {p.relative_to(directory).as_posix(): p.read_bytes() for p in directory.rglob('*') if p.is_file()}


def test_fixture_emits_every_listed_path(marketplace: Path, tmp_path: Path, antigravity_config_dir: Path):
    """Control: each path the link tests plant a symlink at is one a clean emit writes."""
    out = tmp_path / 'out'

    emit_bundles(marketplace, out, antigravity_config_dir)

    assert [rel for rel in EMITTED_FILE_PATHS if not (out / rel).is_file()] == []


@pytest.mark.parametrize('subdir', ['agents', 'commands'])
def test_symlinked_output_directory_is_refused(
    subdir: str, marketplace: Path, outside: Path, tmp_path: Path, antigravity_config_dir: Path
):
    """A symlinked ``agents/`` or ``commands/`` directory is refused and nothing lands in its target."""
    out = tmp_path / 'out'
    out.mkdir()
    link = out / subdir
    link.symlink_to(outside, target_is_directory=True)
    before = _files_under(outside)

    with pytest.raises(ValueError, match='symbolic link') as excinfo:
        emit_bundles(marketplace, out, antigravity_config_dir)

    assert str(link) in str(excinfo.value)
    assert _files_under(outside) == before


@pytest.mark.parametrize('rel', EMITTED_FILE_PATHS)
def test_symlink_at_an_emitted_file_path_is_replaced_not_written_through(
    rel: str, marketplace: Path, outside: Path, tmp_path: Path, antigravity_config_dir: Path
):
    """A symlink where an emitted file belongs is replaced by the file; its target keeps its content."""
    out = tmp_path / 'out'
    emitted = out / rel
    emitted.parent.mkdir(parents=True, exist_ok=True)
    emitted.symlink_to(outside / 'victim')

    emit_bundles(marketplace, out, antigravity_config_dir)

    assert not emitted.is_symlink()
    assert emitted.is_file()
    assert _files_under(outside) == {'victim': SENTINEL}
