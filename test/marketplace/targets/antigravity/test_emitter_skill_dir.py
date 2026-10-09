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
from marketplace.targets.component_targets import SourceSymlinkError

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

#: Content of every file placed outside the output tree; an emit must leave it byte-identical.
SENTINEL = b'outside the output tree\n'


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


@pytest.fixture()
def outside(tmp_path: Path) -> Path:
    """A directory outside the output tree holding files an emit must never touch.

    The names match paths the emit writes, so a write THROUGH a link is caught
    as well as a delete through one.
    """
    directory = tmp_path / 'outside'
    for rel in ('SKILL.md', 'a.md'):
        (directory / rel).parent.mkdir(parents=True, exist_ok=True)
        (directory / rel).write_bytes(SENTINEL)
    return directory


def _files_under(directory: Path) -> dict[str, bytes]:
    return {p.relative_to(directory).as_posix(): p.read_bytes() for p in directory.rglob('*') if p.is_file()}


def test_symlinked_skill_output_directory_is_refused_before_anything_is_touched(
    source_skill: Path, outside: Path, tmp_path: Path, antigravity_config_dir: Path
):
    """A skill output directory that is a symlink is refused, and its target is left as it was."""
    out = tmp_path / 'out'
    link = out / EMITTED_SKILL
    link.parent.mkdir(parents=True)
    link.symlink_to(outside, target_is_directory=True)
    before = _files_under(outside)

    with pytest.raises(ValueError, match='symbolic link') as excinfo:
        emit_bundles(_marketplace(source_skill), out, antigravity_config_dir)

    assert str(link) in str(excinfo.value)
    assert _files_under(outside) == before
    assert link.is_symlink()


def test_skill_output_directory_under_a_symlinked_parent_is_refused(
    source_skill: Path, outside: Path, tmp_path: Path, antigravity_config_dir: Path
):
    """A skill output directory reached through a symlinked parent is refused before it is created."""
    out = tmp_path / 'out'
    out.mkdir()
    (out / EMITTED_SKILL.parent).symlink_to(outside, target_is_directory=True)
    before = _files_under(outside)

    with pytest.raises(ValueError, match='outside output directory'):
        emit_bundles(_marketplace(source_skill), out, antigravity_config_dir)

    assert _files_under(outside) == before
    assert not (outside / EMITTED_SKILL.name).exists()


@pytest.mark.parametrize('link_name', ['workflow', 'stale-link'], ids=['at-an-emitted-directory', 'at-a-stale-name'])
def test_symlinked_subdirectory_is_removed_as_a_link(
    link_name: str, source_skill: Path, outside: Path, tmp_path: Path, antigravity_config_dir: Path
):
    """A symlinked sub-directory of a real skill output directory is unlinked, never traversed or written through."""
    out = tmp_path / 'out'
    emitted_root = out / EMITTED_SKILL
    emitted_root.mkdir(parents=True)
    link = emitted_root / link_name
    link.symlink_to(outside, target_is_directory=True)
    before = _files_under(outside)

    emit_bundles(_marketplace(source_skill), out, antigravity_config_dir)

    assert not link.is_symlink()
    assert _files_under(outside) == before
    assert _files_under(emitted_root).keys() == {'SKILL.md', *EMITTED_FILES}


def test_symlink_at_an_emitted_file_path_is_replaced_not_written_through(
    source_skill: Path, outside: Path, tmp_path: Path, antigravity_config_dir: Path
):
    """A symlink where an emitted file belongs is replaced by the file; its target keeps its content."""
    out = tmp_path / 'out'
    emitted_md = out / EMITTED_SKILL / 'SKILL.md'
    emitted_md.parent.mkdir(parents=True)
    emitted_md.symlink_to(outside / 'SKILL.md')

    emit_bundles(_marketplace(source_skill), out, antigravity_config_dir)

    assert not emitted_md.is_symlink()
    assert emitted_md.is_file()
    assert (outside / 'SKILL.md').read_bytes() == SENTINEL


@pytest.mark.parametrize(
    'stale_link',
    [EMITTED_SKILL.parent / 'gone-skill' / 'workflow', Path('agents') / 'stale-link'],
    ids=['under-a-removed-skill', 'under-the-agents-directory'],
)
def test_full_emit_removes_a_stale_symlinked_directory_as_a_link(
    stale_link: Path, source_skill: Path, outside: Path, tmp_path: Path, antigravity_config_dir: Path
):
    """A symlinked directory at a stale output location is unlinked; its target is not swept."""
    out = tmp_path / 'out'
    link = out / stale_link
    link.parent.mkdir(parents=True)
    link.symlink_to(outside, target_is_directory=True)
    before = _files_under(outside)

    emit_bundles(_marketplace(source_skill), out, antigravity_config_dir)

    assert not link.is_symlink()
    assert _files_under(outside) == before
    assert not (out / EMITTED_SKILL.parent / 'gone-skill').exists()


def test_source_symlink_is_refused_with_the_previous_output_untouched(
    source_skill: Path, outside: Path, tmp_path: Path, antigravity_config_dir: Path
):
    """A skill source holding a symlink is refused and the skill's earlier output stays byte-identical."""
    out = tmp_path / 'out'
    marketplace = _marketplace(source_skill)
    emit_bundles(marketplace, out, antigravity_config_dir)
    before = _files_under(out / EMITTED_SKILL)
    (source_skill / 'workflow' / 'linked.md').symlink_to(outside / 'a.md')

    with pytest.raises(SourceSymlinkError):
        emit_bundles(marketplace, out, antigravity_config_dir)

    assert _files_under(out / EMITTED_SKILL) == before


def test_source_symlink_is_refused_before_the_output_directory_is_created(
    source_skill: Path, outside: Path, tmp_path: Path, antigravity_config_dir: Path
):
    """A refused skill leaves no output directory behind on a first emit."""
    out = tmp_path / 'out'
    (source_skill / 'workflow' / 'linked.md').symlink_to(outside / 'a.md')

    with pytest.raises(SourceSymlinkError):
        emit_bundles(_marketplace(source_skill), out, antigravity_config_dir)

    assert not (out / EMITTED_SKILL).exists()


def test_emitter_exposes_no_subdirectory_allow_list():
    """The emitter carries no name-based allow-list of skill sub-directories."""
    assert not hasattr(ag_emitter, 'VERBATIM_SKILL_SUBDIRS')
    assert 'VERBATIM_SKILL_SUBDIRS' not in ag_emitter.__all__
