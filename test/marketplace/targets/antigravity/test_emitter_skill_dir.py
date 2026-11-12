# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the Antigravity emitter's whole-skill-directory emission.

A skill ships every file of its directory beside the transformed ``SKILL.md``,
whatever sub-directory the file lives in. What is left out is a short, explicit
list: cache directories, dot-files, and files a ``targets:`` declaration scopes
away from this target.

A sub-file whose suffix is ``.md`` is written through the target's SUB-FILE
transform — the dispatch-block applier only, deliberately not the full body
transformer: the ``Skill:`` / ``Read:`` directives a sub-file carries are often
quoted examples, and rewriting them would corrupt the document the target
ships. Every other file (and every ``.md`` when no sub-file transform is
supplied) is copied byte-identical.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

import marketplace.targets.antigravity.emitter as ag_emitter
from conftest import PROJECT_ROOT
from marketplace.targets.antigravity.emitter import emit_bundles
from marketplace.targets.antigravity.target import AntigravityTarget
from marketplace.targets.body_transform_engine import (
    load_transform_rules,
    make_sub_file_transformer,
)
from marketplace.targets.component_targets import SourceSymlinkError

#: Skill-relative files the target must emit byte-identical. None of the
#: sub-directories is one a name-based allow-list would have known.
EMITTED_FILES = {
    'workflow/a.md': b'# workflow a\n',
    'assets/b.json': b'{"k": [1, 2]}\n',
    'workflow/sub/c.md': b'# nested c\n',
    'extension.py': b'VALUE = 1\n',
    # A CRLF body with nothing to rewrite: the decode/rewrite/encode route must
    # not normalise its line endings.
    'workflow/crlf.md': b'# crlf\r\n\r\nA body with no dispatch block.\r\n',
    # A `.md` file that is not UTF-8: the sub-file transform must fall back to a
    # byte copy rather than fail the emit.
    'workflow/not-utf8.md': b'\xff\xfe# not utf-8\n',
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
    """A skill file with nothing to rewrite survives the real target's emit byte-identical.

    The sub-file transformer is the one the target installs, so this pins the
    decode/rewrite/encode round trip a ``.md`` file now takes rather than the
    plain copy path it took before.
    """
    out = tmp_path / 'out'

    written = emit_bundles(
        _marketplace(source_skill),
        out,
        antigravity_config_dir,
        sub_file_transformer=_sub_file_transformer(antigravity_config_dir),
    )

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


# =============================================================================
# The sub-file transform (dispatch applier only)
# =============================================================================

#: A sub-file as the source corpus writes one: a load directive, a ``Skill:``
#: directive and a dispatch block. The first two are quoted catalogue rows a
#: reader must still see verbatim; only the dispatch line has no meaning for
#: this target.
_SUB_FILE_WITH_DISPATCH = (
    '# Workflow\n'
    '\n'
    'Skill: demo:other-skill\n'
    'Read: standards/thing.md\n'
    '\n'
    '```text\n'
    'Task: plan-marshall:{target}\n'
    '  prompt: |\n'
    '    name: demo-envelope\n'
    '```\n'
)

_TARGETED_DISPATCH_RE = re.compile(r'^\s*Task: plan-marshall:', re.MULTILINE)


def _sub_file_transformer(antigravity_config_dir: Path):
    rules = load_transform_rules(antigravity_config_dir / 'mapping.json')
    return make_sub_file_transformer(rules)


def _dispatch_skill(marketplace: Path) -> Path:
    """Build a one-skill bundle whose workflow sub-file carries a dispatch block."""
    bundle = marketplace / 'demo'
    skill = bundle / 'skills' / 'demo-skill'
    (skill / 'workflow').mkdir(parents=True)
    (skill / 'SKILL.md').write_text('---\nname: demo-skill\ndescription: demo desc\n---\n# Body\n', encoding='utf-8')
    (skill / 'workflow' / 'execution.md').write_text(_SUB_FILE_WITH_DISPATCH, encoding='utf-8')
    manifest = bundle / '.claude-plugin' / 'plugin.json'
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({'name': 'demo', 'skills': ['./skills/demo-skill']}) + '\n', encoding='utf-8')
    return marketplace


def test_a_markdown_sub_file_is_written_through_the_dispatch_applier_only(tmp_path: Path, antigravity_config_dir: Path):
    """The sub-file transform is the dispatch applier: directives stay, dispatch goes.

    The scope is deliberate — the full transformer would also rewrite the
    ``Skill:`` and ``Read:`` lines, which sub-files carry as quoted examples a
    reader must still see verbatim.
    """
    marketplace = _dispatch_skill(tmp_path / 'bundles')
    out = tmp_path / 'out'

    emit_bundles(
        marketplace,
        out,
        antigravity_config_dir,
        sub_file_transformer=_sub_file_transformer(antigravity_config_dir),
    )

    emitted = (out / 'skills' / 'demo-demo-skill' / 'workflow' / 'execution.md').read_text(encoding='utf-8')
    assert not _TARGETED_DISPATCH_RE.search(emitted), 'the dispatch line survived'
    assert '`invoke_subagent`' in emitted
    assert 'subagent_type: "{target}"' in emitted
    assert 'Skill: demo:other-skill' in emitted, 'the Skill: directive is an example, not a target directive here'
    assert 'Read: standards/thing.md' in emitted, 'the Read: directive is an example, not a target directive here'


def test_without_a_sub_file_transformer_a_markdown_sub_file_is_byte_identical(
    tmp_path: Path, antigravity_config_dir: Path
):
    """The sub-file transform is opt-in: an emitter called without it copies bytes."""
    marketplace = _dispatch_skill(tmp_path / 'bundles')
    out = tmp_path / 'out'

    emit_bundles(marketplace, out, antigravity_config_dir)

    emitted = (out / 'skills' / 'demo-demo-skill' / 'workflow' / 'execution.md').read_text(encoding='utf-8')
    assert emitted == _SUB_FILE_WITH_DISPATCH


def test_a_crlf_sub_file_keeps_its_line_endings_across_the_rewrite(tmp_path: Path, antigravity_config_dir: Path):
    """The transform rewrites the dispatch header and leaves every CRLF intact."""
    marketplace = _dispatch_skill(tmp_path / 'bundles')
    skill = marketplace / 'demo' / 'skills' / 'demo-skill'
    (skill / 'workflow' / 'crlf.md').write_bytes(
        b'# crlf\r\n\r\nTask: plan-marshall:{target}\r\n  prompt: |\r\n    name: demo-envelope\r\n'
    )
    out = tmp_path / 'out'

    emit_bundles(
        marketplace,
        out,
        antigravity_config_dir,
        sub_file_transformer=_sub_file_transformer(antigravity_config_dir),
    )

    emitted = (out / 'skills' / 'demo-demo-skill' / 'workflow' / 'crlf.md').read_bytes()
    assert b'`invoke_subagent`' in emitted
    assert b'Task: plan-marshall:' not in emitted
    assert emitted.count(b'\r\n') == 5, f'CRLF line endings were lost: {emitted!r}'
    assert b'\n' not in emitted.replace(b'\r\n', b''), f'a bare LF appeared: {emitted!r}'


def test_generated_plan_marshall_workflow_carries_no_bare_dispatch_line(tmp_path: Path):
    """Generating the target over the real bundle leaves the two dispatch sites native."""
    out = tmp_path / 'out'

    AntigravityTarget().generate(Path(PROJECT_ROOT) / 'marketplace' / 'bundles', out, bundles=['plan-marshall'])

    execution = out / 'skills' / 'plan-marshall-plan-marshall' / 'workflow' / 'execution.md'
    text = execution.read_text(encoding='utf-8')
    assert not _TARGETED_DISPATCH_RE.search(text)
    sites = [line for line in text.splitlines() if line.strip().startswith('Call the `invoke_subagent` tool')]
    assert len(sites) == 2, f'expected the phase-5 and verification-feedback dispatch sites, got {sites}'
    assert all('subagent_type: "{target}"' in line for line in sites), (
        f'every dispatch instruction must name the resolved target, got {sites}'
    )


@pytest.mark.parametrize('document', ['phase-5-execute', 'execute-task'])
def test_generated_phase_five_documents_carry_no_bare_task_line(document: str, tmp_path: Path):
    """No generated ``phase-5-execute`` / ``execute-task`` document keeps a bare dispatch line."""
    out = tmp_path / 'out'

    AntigravityTarget().generate(Path(PROJECT_ROOT) / 'marketplace' / 'bundles', out, bundles=['plan-marshall'])

    emitted_skill = out / 'skills' / f'plan-marshall-{document}'
    offenders = [
        f'{path.relative_to(emitted_skill).as_posix()}:{number}'
        for path in sorted(emitted_skill.rglob('*.md'))
        for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), start=1)
        if re.match(r'^\s*Task:', line)
    ]
    assert not offenders, f'generated documents carry a bare dispatch line: {offenders}'
