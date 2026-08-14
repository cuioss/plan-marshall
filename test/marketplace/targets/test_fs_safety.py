# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the shared filesystem-safety containment primitives.

One containment helper is shared by both target emitters (the Claude
verbatim mirror and the OpenCode emitter) so a destructive ``rmtree`` can
never be proven contained by two subtly-different copies of the check.
"""

from pathlib import Path

import pytest

from marketplace.targets.fs_safety import is_within, safe_rmtree


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
