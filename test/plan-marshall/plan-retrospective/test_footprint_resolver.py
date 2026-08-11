#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the shared plan-footprint resolver (``_footprint_resolver``).

Pins the D4 tiers that let an ARCHIVED plan — whose worktree branch-cleanup
removed — resolve a footprint instead of falling to UNRESOLVED:

* Tier 2 — the ``references.realized_footprint`` capture (the capture-while-true
  side effect), and its precedence over the legacy key.
* Tier 3 — the merge-commit fallback (``git diff {sha}^1 {sha}``), for BOTH a
  linear/squash landing and a true merge commit, and its fall-through on a bad SHA.
* Tier 4 — the legacy ``references.modified_files`` key.
* Tier 5 — the negative control: nothing resolvable yields FOOTPRINT_UNRESOLVED, a
  present-but-empty capture is a resolved-empty set (never the sentinel).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from conftest import load_script_module

_fr = load_script_module('plan-marshall', 'plan-retrospective', '_footprint_resolver.py')


# =============================================================================
# Git fixture helpers
# =============================================================================


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ['git', '-C', str(repo), '-c', 'commit.gpgsign=false', *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout


def _init_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, 'init', '--initial-branch=main')
    _git(repo, 'config', 'user.email', 'test@example.com')
    _git(repo, 'config', 'user.name', 'Test User')


def _commit(repo: Path, message: str, files: dict[str, str]) -> str:
    for rel, content in files.items():
        target = repo / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
    _git(repo, 'add', '-A')
    _git(repo, 'commit', '-m', message)
    return _git(repo, 'rev-parse', 'HEAD').strip()


def _write_refs(plan_dir: Path, refs: dict) -> None:
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / 'references.json').write_text(json.dumps(refs, indent=2))


# =============================================================================
# _coerce_path_set — the shared tier-value decoder
# =============================================================================


def test_coerce_path_set_missing_key_is_none():
    assert _fr._coerce_path_set(None) is None


def test_coerce_path_set_bare_string_is_one_element():
    assert _fr._coerce_path_set('a.py') == {'a.py'}


def test_coerce_path_set_empty_list_is_resolved_empty():
    # A present-but-empty list is a resolved, genuinely-empty footprint — NOT None.
    assert _fr._coerce_path_set([]) == set()


def test_coerce_path_set_non_list_is_none():
    assert _fr._coerce_path_set(42) is None


# =============================================================================
# Tier 2 — realized-footprint capture (and its precedence)
# =============================================================================


def test_tier2_realized_footprint_capture(tmp_path):
    """An archived plan (no worktree) resolves via references.realized_footprint."""
    plan_dir = tmp_path / 'plan'
    _write_refs(plan_dir, {'realized_footprint': ['src/a.py', 'src/b.py']})

    resolved = _fr.resolve_footprint(plan_dir, None)
    assert _fr.footprint_resolved(resolved)
    assert resolved == {'src/a.py', 'src/b.py'}


def test_tier2_preferred_over_legacy_key(tmp_path):
    """The capture is PREFERRED over the legacy modified_files key."""
    plan_dir = tmp_path / 'plan'
    _write_refs(
        plan_dir,
        {'realized_footprint': ['captured.py'], 'modified_files': ['legacy.py']},
    )

    resolved = _fr.resolve_footprint(plan_dir, None)
    assert resolved == {'captured.py'}


def test_tier2_present_but_empty_is_resolved_empty(tmp_path):
    """A present-but-empty capture is a resolved-empty set, never the sentinel."""
    plan_dir = tmp_path / 'plan'
    _write_refs(plan_dir, {'realized_footprint': []})

    resolved = _fr.resolve_footprint(plan_dir, None)
    assert _fr.footprint_resolved(resolved)
    assert resolved == set()


# =============================================================================
# Tier 3 — merge-commit fallback (squash AND true-merge shapes)
# =============================================================================


def test_tier3_merge_commit_linear_squash_shape(tmp_path):
    """A linear landing commit (one parent) resolves via git diff {sha}^1 {sha}.

    This is the squash shape: the landing commit's single parent is the base, so
    the first-parent range names exactly the paths the landing introduced.
    """
    repo = tmp_path / 'repo'
    _init_repo(repo)
    _commit(repo, 'base', {'base.txt': 'base\n'})
    landing = _commit(repo, 'squash landing', {'feat/a.py': 'a\n', 'feat/b.py': 'b\n'})
    _write_refs(repo, {'merge_commit_sha': landing})

    resolved = _fr.resolve_footprint(repo, None)
    assert _fr.footprint_resolved(resolved)
    assert resolved == {'feat/a.py', 'feat/b.py'}


def test_tier3_merge_commit_true_merge_shape(tmp_path):
    """A true merge commit (two parents) resolves the merged-in side via {sha}^1.

    The first parent of a merge commit is the base branch, so {sha}^1..{sha} names
    the feature's changes — exact, and free of sibling contamination.
    """
    repo = tmp_path / 'repo'
    _init_repo(repo)
    _commit(repo, 'base', {'base.txt': 'base\n'})
    _git(repo, 'checkout', '-b', 'feature')
    _commit(repo, 'feature change', {'feat/only.py': 'x\n'})
    _git(repo, 'checkout', 'main')
    # Advance main with a sibling file the merge must NOT attribute to the feature.
    _commit(repo, 'sibling on main', {'sibling.py': 's\n'})
    _git(repo, 'merge', '--no-ff', 'feature', '-m', 'merge feature')
    merge_sha = _git(repo, 'rev-parse', 'HEAD').strip()
    _write_refs(repo, {'merge_commit_sha': merge_sha})

    resolved = _fr.resolve_footprint(repo, None)
    assert _fr.footprint_resolved(resolved)
    # Only the feature's file — the sibling that landed on main independently is
    # excluded because {sha}^1 is main's tip at merge time.
    assert resolved == {'feat/only.py'}


def test_tier3_bad_sha_falls_through_to_legacy(tmp_path):
    """A recorded SHA that git cannot resolve falls through, never fabricating a set."""
    repo = tmp_path / 'repo'
    _init_repo(repo)
    _commit(repo, 'base', {'base.txt': 'base\n'})
    _write_refs(
        repo,
        {'merge_commit_sha': '0' * 40, 'modified_files': ['legacy.py']},
    )

    resolved = _fr.resolve_footprint(repo, None)
    assert resolved == {'legacy.py'}


def test_resolve_merge_commit_absent_sha_is_none(tmp_path):
    """No merge_commit_sha → the tier answers None (skip)."""
    assert _fr.resolve_merge_commit_footprint(tmp_path, {}) is None
    assert _fr.resolve_merge_commit_footprint(tmp_path, {'merge_commit_sha': '  '}) is None


# =============================================================================
# Tier 4 / Tier 5 — legacy key and the unresolvable negative control
# =============================================================================


def test_tier4_legacy_modified_files(tmp_path):
    plan_dir = tmp_path / 'plan'
    _write_refs(plan_dir, {'modified_files': ['legacy/a.py', 'legacy/b.py']})

    resolved = _fr.resolve_footprint(plan_dir, None)
    assert resolved == {'legacy/a.py', 'legacy/b.py'}


def test_tier5_unresolvable_negative_control(tmp_path):
    """Nothing resolvable → FOOTPRINT_UNRESOLVED, never a graded empty set.

    The D4 negative control: an unresolvable footprint must stay unresolvable so
    the consumer reports `inconclusive`, not a confident zero.
    """
    plan_dir = tmp_path / 'plan'
    _write_refs(plan_dir, {'base_branch': 'main'})

    resolved = _fr.resolve_footprint(plan_dir, None)
    assert resolved is _fr.FOOTPRINT_UNRESOLVED
    assert not _fr.footprint_resolved(resolved)


def test_missing_references_file_is_unresolvable(tmp_path):
    """No references.json at all → unresolvable (the resolver reads {} defensively)."""
    plan_dir = tmp_path / 'plan'
    plan_dir.mkdir()
    resolved = _fr.resolve_footprint(plan_dir, None)
    assert resolved is _fr.FOOTPRINT_UNRESOLVED
