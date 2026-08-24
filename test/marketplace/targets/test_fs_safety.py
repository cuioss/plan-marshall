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
    refuse_tree_overlap,
    safe_rmtree,
    trees_overlap,
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
