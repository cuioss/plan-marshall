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

"Tracked" is the UNION of the index and HEAD, not the index alone: a ``git rm``'d
``.plan/`` file has left the index while HEAD still carries it, and an index-only
oracle would exempt exactly the deletion the guards exist to surface. The oracle
also reads NUL-delimited git output throughout, so a path whose name git QUOTES in
the default porcelain line form is spelled verbatim here — that spelling is the
contract the dirty-side observation must meet.

The trackedness cases run against throwaway git repositories because trackedness
is a property only a real index can answer.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

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


def _index_paths(repo: Path) -> set[str]:
    """The ``.plan/`` paths the INDEX holds — the ``git ls-files -z`` half alone.

    Used to state the precondition of the staged-deletion cases directly: the
    union is only load-bearing when the index really has stopped reporting the
    path, so the tests assert that rather than assuming it.
    """
    out = _git(repo, 'ls-files', '-z', '--', '.plan/').stdout
    return {entry for entry in out.split('\0') if entry}


def _break_the_head_tree(repo: Path) -> None:
    """Make ``ls-tree HEAD`` fail while HEAD itself still resolves.

    Deletes the loose object holding the HEAD commit's TREE. ``git rev-parse
    --verify HEAD`` reads the COMMIT object and still succeeds; ``git ls-tree -r
    HEAD`` has to read the tree the commit points at and cannot. That is the
    real shape of "the repository HAS a HEAD and the HEAD observation failed
    anyway" — the case an unborn-repository carve-out must not be allowed to
    cover.

    Skips when the object is already packed (nothing loose to unlink), so the
    test never passes on an unexercised path.
    """
    tree_sha = _git(repo, 'rev-parse', 'HEAD^{tree}').stdout.strip()
    loose = repo / '.git' / 'objects' / tree_sha[:2] / tree_sha[2:]
    if not loose.is_file():
        pytest.skip(f'HEAD tree object {tree_sha} is not loose; nothing to unlink')
    loose.unlink()

    probe = subprocess.run(
        ['git', '-C', str(repo), 'ls-tree', '-r', '--name-only', 'HEAD'],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert probe.returncode != 0, (
        'precondition: ls-tree must fail after the tree object is removed, or '
        f'this fixture exercises nothing (stdout={probe.stdout!r})'
    )
    head = subprocess.run(
        ['git', '-C', str(repo), 'rev-parse', '--verify', '--quiet', 'HEAD'],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert head.returncode == 0, (
        'precondition: HEAD must still resolve, or this is indistinguishable '
        'from the unborn-repository case the carve-out legitimately covers'
    )


#: Probe filename for the quoted-path cases. A NON-ASCII name is the first
#: choice because ``core.quotePath`` (on by default) makes git render it both
#: quoted AND ``\NNN``-escaped in the default porcelain line form while ``-z``
#: emits it verbatim — the exact divergence the shared encoding closes. A
#: space-containing name is NOT a usable substitute: git quotes it but does not
#: escape it, so naive quote-stripping recovers the byte-identical spelling and
#: the probe would prove nothing.
_QUOTED_PROBE_RELPATH = '.plan/ünï.json'


def _repo_with_quoted_tracked_plan_file(root: Path, name: str) -> tuple[Path, str]:
    """A repo whose one tracked ``.plan/`` file is committed, dirtied, and quoted by git.

    Returns ``(repo, spelling)`` where ``spelling`` is how ``git ls-files -z``
    reports the path. The spelling is READ BACK from git rather than reused from
    the source literal on purpose: a filesystem that normalises the filename
    (macOS stores NFD) would otherwise make the literal and the on-disk name
    disagree for a reason that has nothing to do with the encoding contract
    under test.

    The helper asserts its own anti-vacuity precondition — git must actually
    render the probe path differently in the default porcelain line form than in
    ``-z``. A name git spells identically in both modes exercises nothing.
    """
    repo = root / name
    repo.mkdir(parents=True)
    _git(repo, 'init', '--initial-branch=main')
    target = repo / _QUOTED_PROBE_RELPATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text('{"schema": 1}\n', encoding='utf-8')
    _git(repo, 'add', '-f', _QUOTED_PROBE_RELPATH)
    _git(repo, 'commit', '-m', 'chore: seed a quoted plan path')
    target.write_text('{"schema": 1, "dirty": true}\n', encoding='utf-8')

    tracked = sorted(_index_paths(repo))
    assert len(tracked) == 1, (
        f'probe repo must hold exactly one tracked .plan/ path, got {tracked}'
    )
    spelling = tracked[0]

    line_form = _git(repo, 'status', '--porcelain').stdout.strip()
    assert line_form != f'M {spelling}', (
        'precondition: git must render this probe path differently in the '
        'default porcelain line form than in -z, or the probe is vacuous. Got '
        f'{line_form!r} against the -z spelling {spelling!r}'
    )
    return repo, spelling


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


def test_partition_retains_staged_deleted_tracked_plan_file(tmp_path: Path) -> None:
    """A ``git rm``'d tracked ``.plan/`` file is RETAINED, not exempted.

    ``git rm`` drops the path from the INDEX while HEAD still carries it. An
    index-only trackedness oracle answers "untracked" there and exempts exactly
    the edit the guards exist to surface — the deletion of tracked plan state.
    Trackedness is the UNION of index and HEAD, so the path stays tracked and
    the deletion is reported.
    """
    repo = _repo_with_tracked_plan_file(tmp_path)
    _git(repo, 'rm', '.plan/marshal.json')
    assert '.plan/marshal.json' not in _index_paths(repo), (
        'precondition: the staged deletion must have removed the path from the '
        'index, or the union is not what this test exercises'
    )

    retained, exempted = pse.partition_plan_state_exemption(['.plan/marshal.json'], repo)

    assert retained == ['.plan/marshal.json']
    assert exempted == []


def test_partition_still_exempts_untracked_plan_file_after_a_staged_deletion(
    tmp_path: Path,
) -> None:
    """(matched negative control) The index∪HEAD widening does not over-reach.

    In the SAME repository whose tracked ``.plan/marshal.json`` has been
    ``git rm``'d, a never-tracked ``.plan/`` path is STILL exempted. Without
    this control, an oracle that simply retained every ``.plan/`` candidate
    would satisfy the positive case above while silently reinstating the
    prefix-blind behaviour the module exists to correct.
    """
    repo = _repo_with_tracked_plan_file(tmp_path)
    _git(repo, 'rm', '.plan/marshal.json')

    retained, exempted = pse.partition_plan_state_exemption(
        ['.plan/marshal.json', '.plan/local/status.json'], repo
    )

    assert retained == ['.plan/marshal.json']
    assert exempted == ['.plan/local/status.json']


def test_partition_retains_tracked_plan_file_whose_name_git_quotes(
    outside_repo_dir: Path,
) -> None:
    """A tracked ``.plan/`` path git renders QUOTED is retained, spelled verbatim.

    This is the TRACKED side of the one-encoding contract: the oracle reads
    NUL-delimited git output, so it reports the path byte-for-byte as
    ``git ls-files -z`` spells it — never quote-wrapped and never
    ``\\NNN``-escaped. The dirty side must meet that spelling; its red-first
    partner is ``test_capture_main_dirty_files_spells_a_quoted_tracked_plan_path_as_git_does``
    in ``test/plan-marshall/plan-marshall/test_invariants.py``, where the
    default porcelain line form used to produce a spelling that matched nothing
    here.

    The throwaway repository is created under ``outside_repo_dir`` — outside
    this repository's own tree — so a probe filename git has to quote never
    lands inside the checkout.
    """
    repo, spelling = _repo_with_quoted_tracked_plan_file(outside_repo_dir, 'quoted-tracked')

    assert pse.tracked_plan_paths(repo) == {spelling}
    assert not spelling.startswith('"'), 'the -z spelling must not be quote-wrapped'

    retained, exempted = pse.partition_plan_state_exemption([spelling], repo)

    assert retained == [spelling]
    assert exempted == []


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


def test_partition_fails_closed_when_tree_is_not_a_repo(outside_repo_dir: Path) -> None:
    """A ``.plan/`` candidate against a non-repo tree is RETAINED, never exempted.

    An unusable trackedness observation must not manufacture a silent exemption —
    the guards exist to surface possibly-unpushable tracked edits. The tree must
    be genuinely outside any git repository: under ``./pw`` ``tmp_path`` is rooted
    INSIDE this repo (``build.py`` sets ``--basetemp`` there), so a ``tmp_path``
    subdir would resolve the enclosing plan-marshall repo rather than failing —
    hence ``outside_repo_dir``.
    """
    not_a_repo = outside_repo_dir / 'plain'
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


def test_tracked_plan_paths_unions_index_and_head(tmp_path: Path) -> None:
    """The oracle is index ∪ HEAD — a HEAD-only path is reported as tracked.

    After ``git rm`` the index half is empty for ``.plan/`` while HEAD still
    carries the file. Asserting the index half separately is what makes this a
    union test rather than a restatement of the plain tracked case.
    """
    repo = _repo_with_tracked_plan_file(tmp_path)
    _git(repo, 'rm', '.plan/marshal.json')

    assert _index_paths(repo) == set(), 'precondition: the index half must be empty'
    assert pse.tracked_plan_paths(repo) == {'.plan/marshal.json'}


def test_tracked_plan_paths_falls_back_to_index_when_head_unresolvable(
    tmp_path: Path,
) -> None:
    """A repository with NO commits has no HEAD — the index answer is still usable.

    ``ls-tree HEAD`` exits non-zero in a fresh repository, which is a legitimate
    state rather than an unusable observation. The oracle keeps the index answer
    instead of failing closed to ``None``.

    This is the MATCHED CONTROL for the two fail-closed cases below: they tighten
    the branch so a failing ``ls-tree`` in a repository that HAS a HEAD returns
    ``None``, and a tightening that swept up the unborn repository too would
    satisfy them while retaining every ``.plan/`` path in a fresh checkout. The
    discriminator must be HEAD's existence, not the ``ls-tree`` failure itself.
    """
    repo = tmp_path / 'no-commits'
    repo.mkdir()
    _git(repo, 'init', '--initial-branch=main')
    staged = repo / '.plan' / 'marshal.json'
    staged.parent.mkdir(parents=True, exist_ok=True)
    staged.write_text('{"schema": 1}\n', encoding='utf-8')
    _git(repo, 'add', '-f', '.plan/marshal.json')

    assert pse.tracked_plan_paths(repo) == {'.plan/marshal.json'}


def test_tracked_plan_paths_none_when_head_resolves_but_the_head_read_fails(
    tmp_path: Path,
) -> None:
    """An unusable HEAD observation fails CLOSED — it is not the unborn-repo case.

    ``_observe_z`` answers ``None`` both when there is no HEAD and when the HEAD
    read did not work, and the two mean opposite things. Treating every failing
    ``ls-tree`` as the legitimate no-commits state resolves an unusable answer in
    the fail-OPEN direction, silently narrowing trackedness back to the index —
    the index-only oracle this module exists to replace. Here the repository HAS
    commits and HEAD resolves, so the failure is unusable and ``None`` is the
    only honest answer.
    """
    repo = _repo_with_tracked_plan_file(tmp_path)
    _break_the_head_tree(repo)

    assert pse.tracked_plan_paths(repo) is None


def test_partition_retains_a_staged_deletion_when_the_head_read_fails(
    tmp_path: Path,
) -> None:
    """The consequence at the caller: the hidden edit is the staged deletion.

    ``git rm`` leaves the path out of the index while HEAD still carries it. With
    the HEAD half unusable and the branch falling back to the index, the path is
    classified untracked and EXEMPTED — the guard reports clean over the deletion
    of tracked plan state, which is the precise failure the module docstring
    names. Failing closed retains it instead.
    """
    repo = _repo_with_tracked_plan_file(tmp_path)
    _git(repo, 'rm', '.plan/marshal.json')
    assert '.plan/marshal.json' not in _index_paths(repo), (
        'precondition: the staged deletion must have left the index'
    )
    _break_the_head_tree(repo)

    retained, exempted = pse.partition_plan_state_exemption(
        ['.plan/marshal.json', '.plan/local/status.json'], repo
    )

    assert retained == ['.plan/local/status.json', '.plan/marshal.json']
    assert exempted == []


def test_tracked_plan_paths_none_when_not_a_repo(outside_repo_dir: Path) -> None:
    # ``outside_repo_dir`` (not ``tmp_path``) because under ``./pw`` ``tmp_path``
    # is inside this repo, so ``git -C`` there resolves the enclosing repo instead
    # of failing.
    plain = outside_repo_dir / 'plain'
    plain.mkdir()
    assert pse.tracked_plan_paths(plain) is None
