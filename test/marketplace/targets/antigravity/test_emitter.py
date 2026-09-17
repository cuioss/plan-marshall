# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the Antigravity emitter."""

from __future__ import annotations

import json
import stat
import subprocess
from pathlib import Path

import pytest

from conftest import PROJECT_ROOT
from marketplace.targets.antigravity.emitter import (
    VERBATIM_SKILL_SUBDIRS,
    emit_bundles,
    iter_bundle_dirs,
)
from marketplace.targets.antigravity.frontmatter import (
    UnmappedFrontmatterError,
    UnmappedToolError,
)


def _write(path: Path, content: str | bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding='utf-8')


@pytest.fixture()
def antigravity_config_dir() -> Path:
    return Path(PROJECT_ROOT) / 'marketplace' / 'targets' / 'antigravity'


@pytest.fixture()
def fixture_bundle(tmp_path: Path) -> Path:
    marketplace = tmp_path / 'bundles'
    bundle = marketplace / 'demo'
    plugin_doc = (
        json.dumps(
            {
                'name': 'demo',
                'version': '0.0.1',
                'description': 'Demo bundle',
                'agents': ['./agents/demo-agent.md'],
                'commands': ['./commands/demo-cmd.md'],
                'skills': ['./skills/demo-skill'],
            },
            indent=2,
        )
        + '\n'
    )
    _write(bundle / '.claude-plugin' / 'plugin.json', plugin_doc)
    _write(
        bundle / 'skills' / 'demo-skill' / 'SKILL.md',
        '---\nname: demo-skill\ndescription: a demo skill\n---\n# Skill body\n',
    )
    for sub in VERBATIM_SKILL_SUBDIRS:
        _write(bundle / 'skills' / 'demo-skill' / sub / f'{sub}-sample.txt', f'{sub} content')

    _write(
        bundle / 'agents' / 'demo-agent.md',
        '---\nname: demo-agent\ndescription: demo agent\nmodel: sonnet\ntools: Read, Write\n---\nagent body\n',
    )
    _write(
        bundle / 'commands' / 'demo-cmd.md',
        '---\nname: demo-cmd\ndescription: demo command\n---\ncommand body\n',
    )
    return marketplace


def test_emit_bundles_copies_verbatim_subdirs(fixture_bundle: Path, tmp_path: Path, antigravity_config_dir: Path):
    out = tmp_path / 'out'
    emit_bundles(fixture_bundle, out, antigravity_config_dir)

    skill_out = out / 'skills' / 'demo-demo-skill'
    assert (skill_out / 'SKILL.md').is_file()
    for sub in VERBATIM_SKILL_SUBDIRS:
        sample = skill_out / sub / f'{sub}-sample.txt'
        assert sample.is_file(), f'expected verbatim file {sample}'
        assert sample.read_text() == f'{sub} content'


def test_emit_bundles_prunes_stale_files(fixture_bundle: Path, tmp_path: Path, antigravity_config_dir: Path):
    out = tmp_path / 'out'
    stale_skill = out / 'skills' / 'old-bundle-old-skill' / 'SKILL.md'
    _write(stale_skill, 'stale')

    emit_bundles(fixture_bundle, out, antigravity_config_dir)
    assert not stale_skill.exists(), 'stale skill file must be pruned on full emit'


def test_emit_bundles_refuses_overlap(tmp_path: Path, antigravity_config_dir: Path):
    marketplace = tmp_path / 'bundles'
    with pytest.raises(ValueError, match='Refusing to emit'):
        emit_bundles(marketplace, marketplace, antigravity_config_dir)


def test_emit_bundles_emits_install_script_and_readme(
    fixture_bundle: Path, tmp_path: Path, antigravity_config_dir: Path
):
    out = tmp_path / 'out'
    written = emit_bundles(fixture_bundle, out, antigravity_config_dir)

    # 1. install.sh emission & permissions
    install_sh = out / 'install.sh'
    assert install_sh.is_file(), 'install.sh was not emitted'
    assert install_sh in written
    assert install_sh.stat().st_mode & stat.S_IXUSR, 'install.sh must be executable'

    # 2. Syntax validation
    subprocess.run(['bash', '-n', str(install_sh)], check=True)

    # 3. Help flag
    res = subprocess.run([str(install_sh), '--help'], check=True, capture_output=True, text=True)
    assert 'Plan Marshall - Google Antigravity Plugin Installer' in res.stdout

    # 4. Local install & uninstall execution
    test_dest = tmp_path / 'installed_plugin'
    subprocess.run([str(install_sh), '--target-dir', str(test_dest)], check=True)
    assert (test_dest / 'plugin.json').is_file()
    assert (test_dest / 'skills').is_dir()

    subprocess.run([str(install_sh), '--target-dir', str(test_dest), '--uninstall'], check=True)
    assert not test_dest.exists()

    # 5. README.adoc emission
    readme = out / 'README.adoc'
    assert readme.is_file(), 'README.adoc was not emitted'
    assert readme in written
    assert '= Installation (Google Antigravity)' in readme.read_text(encoding='utf-8')
