#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for the shared ``.plan/`` dirty-source exemption predicate.

``_plan_state_exemption.partition_plan_state_exemption`` is the SINGLE rule both
finalize-band guards (the post-run source guard and the layer-D main-checkout
drift capture) use to decide whether a dirty ``.plan/`` path is an unpushable
tracked edit or ordinary untracked plan state. The rule is keyed on git
TRACKEDNESS, not on the ``.plan/`` prefix:

- a git-TRACKED ``.plan/`` file (``marshal.json``, an architecture descriptor) is
  RETAINED — it is real tracked source and a post-gate write to it is unpushable;
- an UNTRACKED ``.plan/`` path (status, logs, findings) is EXEMPTED;
- a path outside ``.plan/`` is always retained;
- when trackedness cannot be observed (not a repository, git absent), ``.plan/``
  candidates are RETAINED — the guards must never hide a possibly-tracked edit
  behind a silent exemption (fail closed).

The trackedness cases run against throwaway git repositories because trackedness
is a property only a real index can answer.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import _plan_state_exemption as pse


# =============================================================================
# git repo helpers
# =============================================================================


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    """Run one git command against ``repo`` with a pinned, hermetic identity."""
    return subprocess.run(
        [
            'git',
            '-C',
            str(repo),
            '-c',
            'user.name=Test',
            '-c',
            'user.email=test@example.invalid',
            '-c',
            'commit.gpgsign=false',
            *args,
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    )


def _repo_with_tracked_plan_file(tmp_path: Path) -> Path:
    """A git repo with ``.plan/marshal.json`` tracked (force-added) and committed."""
    repo = tmp_path / 'repo'
    repo.mkdir()
    _git(repo, 'init', '--initial-branch=main')
    marshal = repo / '.plan' / 'marshal.json'
    marshal.parent.mkdir(parents=True, exist_ok=True)
    marshal.write_text('{"schema": 1}\n', encoding='utf-8')
    (repo / 'README.md').write_text('# repo\n', encoding='utf-8')
    _git(repo, 'add', '-f', '.plan/marshal.json', 'README.md')
    _git(repo, 'commit', '-m', 'chore: seed')
    return repo


# =============================================================================
# is_plan_state_path — prefix membership only
# =============================================================================


def test_is_plan_state_path_matches_prefix() -> None:
    assert pse.is_plan_state_path('.plan/marshal.json') is True
    assert pse.is_plan_state_path('.plan/project-architecture/x/enriched.json') is True


def test_is_plan_state_path_is_prefix_not_substring() -> None:
    """Only a leading ``.plan/`` qualifies — not ``.plan`` mid-path or as a suffix."""
    assert pse.is_plan_state_path('my.plan/foo.py') is False
    assert pse.is_plan_state_path('src/.plan/bar.py') is False
    assert pse.is_plan_state_path('README.md') is False
    assert pse.is_plan_state_path('.plans/x') is False


# =============================================================================
# partition_plan_state_exemption — the shared predicate
# =============================================================================


def test_partition_no_plan_paths_retains_all(tmp_path: Path) -> None:
    """With no ``.plan/`` candidate, everything is retained and no git query runs.

    ``tmp_path`` is deliberately NOT a git repository: because there is no
    ``.plan/`` candidate, the predicate must not need a trackedness observation
    at all, so a non-repo tree still returns cleanly.
    """
    retained, exempted = pse.partition_plan_state_exemption(
        ['src/main.py', 'README.md'], tmp_path
    )
    assert retained == ['README.md', 'src/main.py']  # sorted, de-duplicated
    assert exempted == []


def test_partition_empty_input(tmp_path: Path) -> None:
    assert pse.partition_plan_state_exemption([], tmp_path) == ([], [])


def test_partition_retains_tracked_plan_file(tmp_path: Path) -> None:
    """(positive) A dirty TRACKED ``.plan/`` file is retained."""
    repo = _repo_with_tracked_plan_file(tmp_path)
    retained, exempted = pse.partition_plan_state_exemption(['.plan/marshal.json'], repo)
    assert retained == ['.plan/marshal.json']
    assert exempted == []


def test_partition_exempts_untracked_plan_file(tmp_path: Path) -> None:
    """(negative, D5b) A dirty UNTRACKED ``.plan/`` file is exempted."""
    repo = _repo_with_tracked_plan_file(tmp_path)
    retained, exempted = pse.partition_plan_state_exemption(['.plan/local/status.json'], repo)
    assert retained == []
    assert exempted == ['.plan/local/status.json']


def test_partition_mixed_population(tmp_path: Path) -> None:
    """Tracked ``.plan/`` and non-``.plan/`` retained; untracked ``.plan/`` exempted."""
    repo = _repo_with_tracked_plan_file(tmp_path)
    paths = [
        '.plan/marshal.json',        # tracked   → retained
        '.plan/local/work.log',      # untracked → exempted
        'src/main.py',               # non-.plan → retained
        'my.plan/foo.py',            # not a .plan/ path → retained
    ]
    retained, exempted = pse.partition_plan_state_exemption(paths, repo)
    assert retained == ['.plan/marshal.json', 'my.plan/foo.py', 'src/main.py']
    assert exempted == ['.plan/local/work.log']


def test_partition_sorts_and_dedupes(tmp_path: Path) -> None:
    repo = _repo_with_tracked_plan_file(tmp_path)
    paths = ['src/z.py', 'src/a.py', 'src/z.py', '.plan/marshal.json']
    retained, exempted = pse.partition_plan_state_exemption(paths, repo)
    assert retained == ['.plan/marshal.json', 'src/a.py', 'src/z.py']
    assert exempted == []


def test_partition_fails_closed_when_tree_is_not_a_repo(tmp_path: Path) -> None:
    """A ``.plan/`` candidate against a non-repo tree is RETAINED, never exempted.

    An unusable trackedness observation must not manufacture a silent exemption —
    the guards exist to surface possibly-unpushable tracked edits.
    """
    not_a_repo = tmp_path / 'plain'
    not_a_repo.mkdir()
    retained, exempted = pse.partition_plan_state_exemption(
        ['.plan/marshal.json', '.plan/local/work.log'], not_a_repo
    )
    assert retained == ['.plan/local/work.log', '.plan/marshal.json']
    assert exempted == []


# =============================================================================
# tracked_plan_paths — the trackedness observation
# =============================================================================


def test_tracked_plan_paths_returns_tracked_set(tmp_path: Path) -> None:
    repo = _repo_with_tracked_plan_file(tmp_path)
    (repo / '.plan' / 'local').mkdir(parents=True, exist_ok=True)
    (repo / '.plan' / 'local' / 'status.json').write_text('{}\n', encoding='utf-8')
    tracked = pse.tracked_plan_paths(repo)
    assert tracked == {'.plan/marshal.json'}


def test_tracked_plan_paths_none_when_not_a_repo(tmp_path: Path) -> None:
    plain = tmp_path / 'plain'
    plain.mkdir()
    assert pse.tracked_plan_paths(plain) is None
