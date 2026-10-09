# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the shared filesystem-safety containment primitives.

One containment helper is shared by both target emitters (the Claude
verbatim mirror and the OpenCode emitter) so a destructive ``rmtree`` can
never be proven contained by two subtly-different copies of the check.
"""

from pathlib import Path

import pytest

from marketplace.targets.fs_safety import (
    is_within,
    iter_tree_without_following_links,
    refuse_escaping_output_dir,
    refuse_symlink,
    refuse_tree_overlap,
    safe_rmtree,
    trees_overlap,
    unlink_if_symlink,
)


def test_is_within_true_for_descendant(tmp_path: Path):
    root = tmp_path / 'out'
    (root / 'a').mkdir(parents=True)
    assert is_within(root / 'a', root) is True


def test_is_within_true_for_self(tmp_path: Path):
    root = tmp_path / 'out'
    root.mkdir()
    assert is_within(root, root) is True


def test_is_within_false_for_sibling(tmp_path: Path):
    root = tmp_path / 'out'
    other = tmp_path / 'other'
    root.mkdir()
    other.mkdir()
    assert is_within(other, root) is False


def test_is_within_false_for_parent(tmp_path: Path):
    inner = tmp_path / 'out' / 'inner'
    inner.mkdir(parents=True)
    assert is_within(tmp_path / 'out', inner) is False


def test_is_within_rejects_prefix_sibling(tmp_path: Path):
    """A sibling sharing a leading string prefix ('out-sibling' vs 'out') is
    NOT contained — the ``+ '/'`` boundary guards the naive prefix test.
    """
    root = tmp_path / 'out'
    sibling = tmp_path / 'out-sibling'
    root.mkdir()
    sibling.mkdir()
    assert is_within(sibling, root) is False


# =============================================================================
# trees_overlap / refuse_tree_overlap — the UNDIRECTED question
# =============================================================================
#
# ``is_within`` is directed, and a destructive emit needs the undirected
# answer. Both emitters used to ask the directed one — "is the output inside
# the source?" — from an identical private copy of the test, so the two copies
# drifted TOGETHER: neither covered a source lying inside the output, which is
# the direction that lets the removed-bundle prune sweep delete the source
# tree outright. Both directions are pinned here, plus the disjoint control
# that keeps a refuse-everything guard from passing the negative cases.


def test_trees_overlap_true_when_the_output_lies_inside_the_source(tmp_path: Path):
    source = tmp_path / 'marketplace'
    output = source / 'target'
    output.mkdir(parents=True)
    assert trees_overlap(output, source) is True


def test_trees_overlap_true_when_the_source_lies_inside_the_output(tmp_path: Path):
    """The direction ``is_within(output, source)`` answers False for.

    Nothing about a destructive sweep cares which tree is nested in which —
    the source is just as gone when the OUTPUT is its parent.
    """
    output = tmp_path / 'repo'
    source = output / 'marketplace'
    source.mkdir(parents=True)
    assert is_within(output, source) is False, 'fixture precondition: directed test passes'
    assert trees_overlap(output, source) is True


def test_trees_overlap_true_for_the_same_tree(tmp_path: Path):
    same = tmp_path / 'both'
    same.mkdir()
    assert trees_overlap(same, same) is True


def test_trees_overlap_false_for_disjoint_siblings(tmp_path: Path):
    """Matched control: the predicate must not answer True for everything."""
    source = tmp_path / 'marketplace'
    output = tmp_path / 'target'
    source.mkdir()
    output.mkdir()
    assert trees_overlap(output, source) is False


def test_refuse_tree_overlap_raises_when_the_output_contains_the_source(tmp_path: Path):
    output = tmp_path / 'repo'
    source = output / 'marketplace'
    source.mkdir(parents=True)
    with pytest.raises(ValueError, match='source tree'):
        refuse_tree_overlap(output, source)


def test_refuse_tree_overlap_raises_when_the_output_is_inside_the_source(tmp_path: Path):
    source = tmp_path / 'marketplace'
    output = source / 'target'
    output.mkdir(parents=True)
    with pytest.raises(ValueError, match='source tree'):
        refuse_tree_overlap(output, source)


def test_refuse_tree_overlap_permits_a_disjoint_destination(tmp_path: Path):
    """Positive control: a legitimate build location is NOT refused.

    A guard that raised unconditionally would satisfy both negative cases
    above while breaking every real emit.
    """
    source = tmp_path / 'marketplace'
    output = tmp_path / 'target' / 'claude'
    source.mkdir()
    refuse_tree_overlap(output, source)  # must not raise — output need not exist yet


def test_safe_rmtree_removes_contained(tmp_path: Path):
    root = tmp_path / 'out'
    victim = root / 'a'
    victim.mkdir(parents=True)
    (victim / 'f.txt').write_text('x', encoding='utf-8')
    safe_rmtree(victim, root)
    assert not victim.exists()


def test_safe_rmtree_refuses_outside(tmp_path: Path):
    """Negative control: a target outside the output dir is refused and nothing
    is deleted.
    """
    root = tmp_path / 'out'
    outside = tmp_path / 'outside'
    root.mkdir()
    outside.mkdir()
    (outside / 'keep.txt').write_text('important', encoding='utf-8')
    with pytest.raises(ValueError, match='not within output directory'):
        safe_rmtree(outside, root)
    assert (outside / 'keep.txt').exists()


# =============================================================================
# refuse_escaping_output_dir — a NESTED output directory, not the two roots
# =============================================================================
#
# ``refuse_tree_overlap`` looks at the output root and the source root only. A
# per-component directory beneath the output root can still be a symlink, or
# sit under a symlinked ancestor, and ``mkdir(exist_ok=True)`` accepts either.


def test_refuse_escaping_output_dir_raises_for_a_symlinked_directory(tmp_path: Path):
    root = tmp_path / 'out'
    outside = tmp_path / 'outside'
    root.mkdir()
    outside.mkdir()
    link = root / 'skill-dir'
    link.symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError, match='symbolic link') as excinfo:
        refuse_escaping_output_dir(link, root)

    assert str(link) in str(excinfo.value)


def test_refuse_escaping_output_dir_raises_for_a_symlink_pointing_inside_the_output(tmp_path: Path):
    """A link is refused wherever it points — containment of the target is not enough."""
    root = tmp_path / 'out'
    (root / 'real').mkdir(parents=True)
    link = root / 'skill-dir'
    link.symlink_to(root / 'real', target_is_directory=True)

    with pytest.raises(ValueError, match='symbolic link'):
        refuse_escaping_output_dir(link, root)


def test_refuse_escaping_output_dir_raises_under_a_symlinked_ancestor(tmp_path: Path):
    """A not-yet-created directory beneath a symlinked ancestor resolves outside the output."""
    root = tmp_path / 'out'
    outside = tmp_path / 'outside'
    root.mkdir()
    outside.mkdir()
    (root / 'skills').symlink_to(outside, target_is_directory=True)
    nested = root / 'skills' / 'skill-dir'

    with pytest.raises(ValueError, match='outside output directory') as excinfo:
        refuse_escaping_output_dir(nested, root)

    assert str(nested) in str(excinfo.value)
    assert not (outside / 'skill-dir').exists()


@pytest.mark.parametrize('create', [True, False], ids=['existing', 'not-yet-created'])
def test_refuse_escaping_output_dir_permits_a_real_directory(create: bool, tmp_path: Path):
    """Positive control: a real nested directory passes, whether or not it exists yet."""
    root = tmp_path / 'out'
    nested = root / 'skills' / 'skill-dir'
    if create:
        nested.mkdir(parents=True)

    refuse_escaping_output_dir(nested, root)  # must not raise


def test_refuse_escaping_output_dir_permits_a_symlinked_output_root(tmp_path: Path):
    """Both operands are resolved, so an output root reached through a link is not an escape."""
    real_root = tmp_path / 'real-out'
    (real_root / 'skills' / 'skill-dir').mkdir(parents=True)
    root = tmp_path / 'out'
    root.symlink_to(real_root, target_is_directory=True)

    refuse_escaping_output_dir(root / 'skills' / 'skill-dir', root)  # must not raise


# =============================================================================
# refuse_symlink — a destination that is neither followed nor replaced
# =============================================================================


@pytest.mark.parametrize('kind', ['file', 'directory', 'dangling'])
def test_refuse_symlink_raises_for_a_link_and_leaves_it_in_place(kind: str, tmp_path: Path):
    """A link is refused wherever it points, named in the message, and not removed."""
    target = tmp_path / 'target'
    if kind == 'file':
        target.write_text('important', encoding='utf-8')
    elif kind == 'directory':
        target.mkdir()
    link = tmp_path / 'link'
    link.symlink_to(target, target_is_directory=kind == 'directory')

    with pytest.raises(ValueError, match='symbolic link') as excinfo:
        refuse_symlink(link)

    assert str(link) in str(excinfo.value)
    assert link.is_symlink()
    assert target.exists() is (kind != 'dangling')


@pytest.mark.parametrize('create', [True, False], ids=['real-file', 'missing'])
def test_refuse_symlink_permits_a_non_link(create: bool, tmp_path: Path):
    """Control: a real file passes and so does a path that does not exist yet."""
    path = tmp_path / 'file.txt'
    if create:
        path.write_text('kept', encoding='utf-8')

    refuse_symlink(path)  # must not raise

    assert path.exists() is create


# =============================================================================
# unlink_if_symlink — clear a link before a write would go through it
# =============================================================================


def test_unlink_if_symlink_removes_the_link_and_keeps_its_target(tmp_path: Path):
    target = tmp_path / 'target.txt'
    target.write_text('important', encoding='utf-8')
    link = tmp_path / 'link.txt'
    link.symlink_to(target)

    unlink_if_symlink(link)

    assert not link.is_symlink()
    assert target.read_text(encoding='utf-8') == 'important'


def test_unlink_if_symlink_removes_a_dangling_link(tmp_path: Path):
    link = tmp_path / 'link.txt'
    link.symlink_to(tmp_path / 'missing')

    unlink_if_symlink(link)

    assert not link.is_symlink()


@pytest.mark.parametrize('create', [True, False], ids=['real-file', 'missing'])
def test_unlink_if_symlink_leaves_a_non_link_alone(create: bool, tmp_path: Path):
    """Control: only a link is removed — a real file survives, a missing path does not raise."""
    path = tmp_path / 'file.txt'
    if create:
        path.write_text('kept', encoding='utf-8')

    unlink_if_symlink(path)

    assert path.exists() is create


# =============================================================================
# iter_tree_without_following_links — the walk a destructive sweep may use
# =============================================================================


def test_iter_tree_yields_a_symlinked_directory_without_walking_its_target(tmp_path: Path):
    root = tmp_path / 'out'
    outside = tmp_path / 'outside'
    (root / 'real').mkdir(parents=True)
    (root / 'real' / 'f.txt').write_text('x', encoding='utf-8')
    outside.mkdir()
    (outside / 'keep.txt').write_text('important', encoding='utf-8')
    (root / 'link').symlink_to(outside, target_is_directory=True)

    walked = list(iter_tree_without_following_links(root))

    assert walked == [root / 'link', root / 'real', root / 'real' / 'f.txt']


def test_iter_tree_tolerates_unlinking_each_entry_as_it_is_yielded(tmp_path: Path):
    """The sweep's own usage: removing a yielded link neither breaks the walk nor reaches its target."""
    root = tmp_path / 'out'
    outside = tmp_path / 'outside'
    (root / 'real').mkdir(parents=True)
    (root / 'real' / 'f.txt').write_text('x', encoding='utf-8')
    outside.mkdir()
    (outside / 'keep.txt').write_text('important', encoding='utf-8')
    (root / 'link').symlink_to(outside, target_is_directory=True)

    for entry in iter_tree_without_following_links(root):
        if entry.is_symlink() or entry.is_file():
            entry.unlink()

    assert [p.name for p in root.iterdir()] == ['real']
    assert not any((root / 'real').iterdir())
    assert (outside / 'keep.txt').read_text(encoding='utf-8') == 'important'
