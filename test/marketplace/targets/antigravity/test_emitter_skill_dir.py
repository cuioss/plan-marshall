# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the Antigravity emitter's whole-skill-directory emission.

A skill ships every file of its directory beside the transformed ``SKILL.md``,
whatever sub-directory the file lives in. What is left out is a short, explicit
list: cache directories, dot-files, and files a ``targets:`` declaration scopes
away from this target.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import marketplace.targets.antigravity.emitter as ag_emitter
from conftest import PROJECT_ROOT
from marketplace.targets.antigravity.emitter import emit_bundles

#: Skill-relative files the target must emit byte-identical. None of the
#: sub-directories is one a name-based allow-list would have known.
EMITTED_FILES = {
    'workflow/a.md': b'# workflow a\n',
    'assets/b.json': b'{"k": [1, 2]}\n',
    'workflow/sub/c.md': b'# nested c\n',
    'extension.py': b'VALUE = 1\n',
}

#: Skill-relative files this target does not emit.
NOT_EMITTED_FILES = ('__pycache__/x.pyc', '.DS_Store')

#: A file whose own ``targets:`` declaration omits this target.
SCOPED_AWAY_FILE = 'references/claude-only.md'

EMITTED_SKILL = Path('skills') / 'demo-demo-skill'


@pytest.fixture()
def antigravity_config_dir() -> Path:
    return Path(PROJECT_ROOT) / 'marketplace' / 'targets' / 'antigravity'


@pytest.fixture()
def source_skill(tmp_path: Path) -> Path:
    """Build a one-skill bundle and return the source skill directory."""
    bundle = tmp_path / 'bundles' / 'demo'
    skill = bundle / 'skills' / 'demo-skill'
    files: dict[str, bytes] = {
        'SKILL.md': b'---\nname: demo-skill\ndescription: demo desc\n---\n# Body\n',
        SCOPED_AWAY_FILE: b'---\ntargets: [claude]\n---\n# claude only\n',
        **EMITTED_FILES,
        **dict.fromkeys(NOT_EMITTED_FILES, b'\x00'),
    }
    for rel, content in files.items():
        path = skill / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    manifest = bundle / '.claude-plugin' / 'plugin.json'
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({'name': 'demo', 'skills': ['./skills/demo-skill']}) + '\n', encoding='utf-8')
    return skill


def _marketplace(source_skill: Path) -> Path:
    return source_skill.parents[2]


@pytest.mark.parametrize('rel', sorted(EMITTED_FILES))
def test_skill_file_is_emitted_byte_identical(
    rel: str, source_skill: Path, tmp_path: Path, antigravity_config_dir: Path
):
    """A skill file is emitted byte-identical."""
    out = tmp_path / 'out'

    written = emit_bundles(_marketplace(source_skill), out, antigravity_config_dir)

    emitted = out / EMITTED_SKILL / rel
    assert emitted.read_bytes() == EMITTED_FILES[rel]
    assert emitted in written


@pytest.mark.parametrize('rel', [*NOT_EMITTED_FILES, SCOPED_AWAY_FILE])
def test_excluded_skill_file_is_not_emitted(rel: str, source_skill: Path, tmp_path: Path, antigravity_config_dir: Path):
    """Cache files, dot-files and files scoped to another target stay absent."""
    out = tmp_path / 'out'

    emit_bundles(_marketplace(source_skill), out, antigravity_config_dir)

    assert (source_skill / rel).is_file(), 'the fixture must carry the file the emit leaves out'
    assert not (out / EMITTED_SKILL / rel).exists()


def test_emitted_skill_directory_holds_exactly_the_shipped_files(
    source_skill: Path, tmp_path: Path, antigravity_config_dir: Path
):
    """The emitted skill directory holds ``SKILL.md`` and the shipped files, nothing else."""
    out = tmp_path / 'out'

    emit_bundles(_marketplace(source_skill), out, antigravity_config_dir)

    emitted_root = out / EMITTED_SKILL
    emitted = {p.relative_to(emitted_root).as_posix() for p in emitted_root.rglob('*') if p.is_file()}
    assert emitted == {'SKILL.md', *EMITTED_FILES}


def test_scoped_emit_drops_a_file_removed_from_source(source_skill: Path, tmp_path: Path, antigravity_config_dir: Path):
    """A file removed from a surviving skill leaves the emitted directory on a scoped emit too."""
    out = tmp_path / 'out'
    marketplace = _marketplace(source_skill)
    emit_bundles(marketplace, out, antigravity_config_dir)
    (source_skill / 'workflow' / 'sub' / 'c.md').unlink()

    emit_bundles(marketplace, out, antigravity_config_dir, bundles=['demo'])

    assert not (out / EMITTED_SKILL / 'workflow' / 'sub').exists()
    assert (out / EMITTED_SKILL / 'workflow' / 'a.md').is_file()


def test_re_emit_replaces_a_directory_that_became_a_file(
    source_skill: Path, tmp_path: Path, antigravity_config_dir: Path
):
    """A source path that changes from a directory to a file is re-emitted as the file."""
    out = tmp_path / 'out'
    marketplace = _marketplace(source_skill)
    emit_bundles(marketplace, out, antigravity_config_dir)
    (source_skill / 'assets' / 'b.json').unlink()
    (source_skill / 'assets').rmdir()
    (source_skill / 'assets').write_bytes(b'now a file\n')

    emit_bundles(marketplace, out, antigravity_config_dir)

    assert (out / EMITTED_SKILL / 'assets').read_bytes() == b'now a file\n'


def test_emitter_exposes_no_subdirectory_allow_list():
    """The emitter carries no name-based allow-list of skill sub-directories."""
    assert not hasattr(ag_emitter, 'VERBATIM_SKILL_SUBDIRS')
    assert 'VERBATIM_SKILL_SUBDIRS' not in ag_emitter.__all__
