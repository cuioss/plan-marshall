# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the Claude verbatim emitter's refusal of source symlinks.

The mirror copies by content, so a symbolic link inside a bundle would be
followed and whatever it points at shipped. The rule itself is
``component_targets.iter_source_files`` and is pinned there; what is pinned
here is that the Claude emit is wired to it, and that a refusal costs nothing
already on disk.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from marketplace.targets.claude.emitter import emit_bundle_verbatim
from marketplace.targets.component_targets import SourceSymlinkError

#: Content of the file standing outside the bundle. No emitted tree may ever
#: contain it.
_OUTSIDE_CONTENT = 'not part of any bundle\n'

_BUNDLE_FILES = {
    '.claude-plugin/plugin.json': json.dumps({'name': 'demo', 'version': '0.0.1', 'description': 'd'}) + '\n',
    'README.md': '# demo bundle\n',
    'agents/demo-agent.md': '---\nname: demo-agent\n---\nbody',
    'skills/demo-skill/SKILL.md': '---\nname: demo-skill\ndescription: demo\n---\n# demo',
    'skills/demo-skill/standards/rule.md': '# rule\n',
    'skills/demo-skill/__pycache__/junk.pyc': 'cache\n',
}


@pytest.fixture()
def bundle_dir(tmp_path: Path) -> Path:
    """A complete one-skill bundle that holds no link."""
    bundle = tmp_path / 'bundles' / 'demo'
    for rel, text in _BUNDLE_FILES.items():
        path = bundle / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')
    return bundle


@pytest.fixture()
def outside_dir(tmp_path: Path) -> Path:
    """A directory beside the marketplace holding a readable file."""
    outside = tmp_path / 'outside'
    outside.mkdir()
    (outside / 'secret.txt').write_text(_OUTSIDE_CONTENT, encoding='utf-8')
    return outside


def _emitted_files(dest_root: Path) -> dict[str, bytes]:
    files = (path for path in dest_root.rglob('*') if path.is_file())
    return {path.relative_to(dest_root).as_posix(): path.read_bytes() for path in files}


def test_a_bundle_without_links_is_mirrored_byte_for_byte(bundle_dir: Path, tmp_path: Path):
    """The refusal changes nothing for a bundle that holds no link."""
    out_dir = tmp_path / 'out'

    written = emit_bundle_verbatim(bundle_dir, out_dir)

    expected = {
        rel: text.encode('utf-8')
        for rel, text in _BUNDLE_FILES.items()
        if rel != '.claude-plugin/plugin.json' and '__pycache__' not in rel
    }
    assert _emitted_files(out_dir / 'demo') == expected
    assert sorted(written) == sorted(out_dir / 'demo' / rel for rel in expected)


@pytest.mark.parametrize(
    ('link_rel', 'target_rel', 'is_directory'),
    [
        pytest.param('skills/demo-skill/standards/leak.md', 'secret.txt', False, id='file-link-in-a-skill'),
        pytest.param('agents/leak.md', 'secret.txt', False, id='file-link-among-the-agents'),
        pytest.param('leak.md', 'secret.txt', False, id='file-link-at-the-bundle-root'),
        pytest.param('skills/linked-skill', '', True, id='directory-link'),
        pytest.param('skills/demo-skill/__pycache__/leak.pyc', 'secret.txt', False, id='link-under-an-excluded-dir'),
    ],
)
def test_a_symlink_inside_a_bundle_fails_the_emit_naming_the_link(
    bundle_dir: Path, outside_dir: Path, tmp_path: Path, link_rel: str, target_rel: str, is_directory: bool
):
    """A link anywhere in the bundle refuses the emit, and nothing is written.

    An excluded directory is not exempt: the rule is that the tree holds no
    link, not that no emitted path does.
    """
    link = bundle_dir / link_rel
    link.symlink_to(outside_dir / target_rel, target_is_directory=is_directory)
    out_dir = tmp_path / 'out'

    with pytest.raises(SourceSymlinkError) as excinfo:
        emit_bundle_verbatim(bundle_dir, out_dir)

    assert str(link) in str(excinfo.value)
    assert not out_dir.exists()


def test_a_link_to_a_file_inside_the_same_bundle_is_refused_too(bundle_dir: Path, tmp_path: Path):
    """Where the link points does not matter; that it is a link does."""
    link = bundle_dir / 'skills' / 'demo-skill' / 'standards' / 'alias.md'
    link.symlink_to(bundle_dir / 'README.md')

    with pytest.raises(SourceSymlinkError) as excinfo:
        emit_bundle_verbatim(bundle_dir, tmp_path / 'out')

    assert str(link) in str(excinfo.value)


def test_a_refused_emit_leaves_the_previous_output_untouched(bundle_dir: Path, outside_dir: Path, tmp_path: Path):
    """The source is walked BEFORE the destination is wiped.

    Refusing after the wipe would delete the last good mirror and then abort,
    leaving an empty destination for one stray link.
    """
    out_dir = tmp_path / 'out'
    emit_bundle_verbatim(bundle_dir, out_dir)
    before = _emitted_files(out_dir / 'demo')
    (bundle_dir / 'skills' / 'demo-skill' / 'leak.md').symlink_to(outside_dir / 'secret.txt')

    with pytest.raises(SourceSymlinkError):
        emit_bundle_verbatim(bundle_dir, out_dir)

    assert before, 'fixture precondition: the first emit wrote something'
    assert _emitted_files(out_dir / 'demo') == before
