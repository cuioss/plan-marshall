#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The two git commands the unified-triage hook takes its fix evidence from.

``phase-6-finalize`` item 7c step (0) stamps a held ``fixed`` finding only with a
commit that is shown to carry the change, and it finds that commit with one git
command per recovery:

- a stamp that does not reach the pull request head is written again with the
  single commit ``git log --cherry-mark`` marks ``=``: the commit whose patch for
  the finding's file equals the replaced commit's;
- an unstamped inline fix is stamped with the single commit ``git log --grep``
  lists whose subject is the message the hook commits inline edits with.

The documents depend on how git answers both. That ``--cherry-mark`` compares
patches restricted to the path given after ``--`` is observed behaviour, so this
suite runs the commands for real: it reads each command line from the skill
document, fills in the placeholders, and runs it against a repository built in
``tmp_path``. The repository configures its own identity and reads neither the
global nor the system git configuration, and nothing here reaches the network.
"""

from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path

from conftest import get_skill_dir

_FINALIZE_SKILL = get_skill_dir('plan-marshall', 'phase-6-finalize') / 'SKILL.md'

#: The message the hook commits the triage's inline edits with.
_INLINE_MESSAGE = 'fix(review): apply inline review dispositions'

#: How each documented command line starts. Exactly one line of the skill
#: document starts with each.
_COMPARISON_START = 'git -C {worktree_path} log --cherry-mark '
_SEARCH_START = 'git -C {worktree_path} log --no-merges --format=%H%x09%s '

#: The path restriction both commands end in.
_PATH_RESTRICTION = ' -- {file_path}'

#: A well-formed commit id no repository built here contains.
_UNKNOWN_COMMIT = 'deadbeef' * 5

_REVIEWED_FILE = 'reviewed.txt'
_OTHER_FILE = 'other.txt'

_ORIGINAL = 'one\ntwo\nthree\nfour\nfive\n'
_FIXED = 'one\ntwo\nthree, fixed\nfour\nfive\n'
_FIXED_ANOTHER_WAY = 'one\ntwo\nthree, repaired differently\nfour\nfive\n'

#: Git reads no configuration but the repository's own.
_GIT_ENV = {**os.environ, 'GIT_CONFIG_GLOBAL': os.devnull, 'GIT_CONFIG_NOSYSTEM': '1', 'GIT_TERMINAL_PROMPT': '0'}


def _git(repo: Path, *args: str) -> str:
    """Run one git command in ``repo`` and return its output. A failing command raises."""
    done = subprocess.run(
        ['git', '-C', str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
        env=_GIT_ENV,
    )
    return done.stdout.strip()


def _init(tmp_path: Path) -> Path:
    """Create an empty repository on branch ``main`` with its own identity."""
    repo = tmp_path / 'repo'
    repo.mkdir()
    _git(repo, 'init', '--quiet')
    _git(repo, 'symbolic-ref', 'HEAD', 'refs/heads/main')
    _git(repo, 'config', 'user.name', 'Evidence Test')
    _git(repo, 'config', 'user.email', 'evidence@example.invalid')
    _git(repo, 'config', 'commit.gpgsign', 'false')
    return repo


def _commit(repo: Path, message: str, files: dict[str, str]) -> str:
    """Write ``files``, commit them under ``message`` and return the new commit id."""
    for name, content in files.items():
        (repo / name).write_text(content, encoding='utf-8')
    _git(repo, 'add', '--all')
    _git(repo, 'commit', '--quiet', '-m', message)
    return _git(repo, 'rev-parse', 'HEAD')


def _documented(start: str) -> str:
    """The single line of the skill document that starts with ``start``."""
    text: str = _FINALIZE_SKILL.read_text(encoding='utf-8')
    lines = [line.strip() for line in text.splitlines() if line.strip().startswith(start)]
    assert len(lines) == 1, f'expected one documented command starting with {start!r}, found {lines}'
    return lines[0]


def _fill(command: str, values: dict[str, str]) -> list[str]:
    """Replace every placeholder of ``command`` and split it as a shell would."""
    for name, value in values.items():
        command = command.replace('{' + name + '}', shlex.quote(value))
    assert '{' not in command, f'placeholder left unfilled in: {command}'
    return shlex.split(command)


def _run(argv: list[str]) -> subprocess.CompletedProcess[str]:
    """Run a filled command. The caller asserts on the exit status."""
    return subprocess.run(argv, check=False, capture_output=True, text=True, env=_GIT_ENV)


def _counted(stdout: str) -> list[str]:
    """The commits of the search output whose subject IS the inline message.

    This is the counting rule of the hook: a line is a commit id, a tab and the
    subject, and it counts only when the text after the tab equals the message.
    """
    found: list[str] = []
    for line in stdout.splitlines():
        commit, tab, subject = line.partition('\t')
        if tab and subject == _INLINE_MESSAGE:
            found.append(commit)
    return found


# ---------------------------------------------------------------------------
# The helpers, before anything rests on them
# ---------------------------------------------------------------------------


def test_both_commands_are_read_from_the_skill_document():
    """Vacuity guard: one line each, ending in the path restriction, with the stated operands."""
    comparison = _documented(_COMPARISON_START)
    search = _documented(_SEARCH_START)

    assert comparison.endswith(_PATH_RESTRICTION)
    assert search.endswith(_PATH_RESTRICTION)
    assert '{stamped_commit_sha}...{pushed_head_sha} ^{stamped_commit_sha}^ ^origin/{base_branch}' in comparison
    assert f'--fixed-strings --grep="{_INLINE_MESSAGE}" {{reviewed_commit_sha}}..{{pushed_head_sha}}' in search
    assert '|' not in comparison
    assert '|' not in search


def test_fill_replaces_every_placeholder_and_keeps_a_quoted_argument_whole():
    argv = _fill(
        'git -C {worktree_path} log --grep="a b" {from}..{to}', {'worktree_path': '/x y', 'from': 'p', 'to': 'q'}
    )

    assert argv == ['git', '-C', '/x y', 'log', '--grep=a b', 'p..q']


def test_counting_rule_takes_an_exact_subject_only():
    """Positive control, then a longer subject, a line with no tab, and an empty output."""
    output = f'aaa\t{_INLINE_MESSAGE}\nbbb\t{_INLINE_MESSAGE} again\nccc {_INLINE_MESSAGE}\nddd\tdocs: other\n'

    assert _counted(output) == ['aaa']
    assert _counted('') == []


# ---------------------------------------------------------------------------
# (a) A stamp that does not reach the pull request head
# ---------------------------------------------------------------------------


def _rewritten_branch(tmp_path: Path) -> tuple[Path, str]:
    """A repository whose fix commit was replaced by a rewrite.

    ``main`` holds the base, and ``origin/main`` points at it. The commit that
    made the fix — the stamped one — sits on a branch that was left behind. The
    checked-out branch ``rewritten`` starts from a newer ``main`` and holds
    nothing yet. Returns the repository and the stamped commit.
    """
    repo = _init(tmp_path)
    _commit(repo, 'chore: base', {_REVIEWED_FILE: _ORIGINAL, _OTHER_FILE: 'other\n', 'upstream.txt': 'upstream\n'})
    _git(repo, 'checkout', '--quiet', '-b', 'replaced')
    stamped = _commit(repo, 'fix: the fix', {_REVIEWED_FILE: _FIXED, _OTHER_FILE: 'other, as the fix left it\n'})
    _git(repo, 'checkout', '--quiet', 'main')
    upstream = _commit(repo, 'chore: upstream', {'upstream.txt': 'upstream, moved on\n'})
    _git(repo, 'update-ref', 'refs/remotes/origin/main', upstream)
    _git(repo, 'checkout', '--quiet', '-b', 'rewritten')
    return repo, stamped


def _compare(
    repo: Path, stamped: str, *, base_branch: str = 'main', restricted: bool = True
) -> subprocess.CompletedProcess[str]:
    """Run the documented comparison between ``stamped`` and the head of ``repo``."""
    command = _documented(_COMPARISON_START)
    if not restricted:
        command = command.removesuffix(_PATH_RESTRICTION)
    values = {
        'worktree_path': str(repo),
        'stamped_commit_sha': stamped,
        'pushed_head_sha': _git(repo, 'rev-parse', 'HEAD'),
        'base_branch': base_branch,
        'file_path': _REVIEWED_FILE,
    }
    if not restricted:
        del values['file_path']
    return _run(_fill(command, values))


def test_the_same_change_to_the_file_is_the_one_line_marked_equal(tmp_path):
    """The rewritten commit changes the file as the stamped one did, and another file differently."""
    repo, stamped = _rewritten_branch(tmp_path)
    unrelated = _commit(repo, 'chore: unrelated', {'unrelated.txt': 'unrelated\n'})
    evidence = _commit(
        repo, 'fix: the fix, rewritten', {_REVIEWED_FILE: _FIXED, _OTHER_FILE: 'other, as the rewrite left it\n'}
    )
    later = _commit(repo, 'docs: a later edit', {_REVIEWED_FILE: _FIXED + 'six\n'})

    done = _compare(repo, stamped)
    lines = done.stdout.splitlines()

    assert done.returncode == 0, done.stderr
    assert [line for line in lines if line.startswith('=')] == [f'={evidence}']
    # A later commit that changes the file differently is listed, and not as equal.
    assert f'>{later}' in lines
    # A commit that does not touch the file is not listed at all.
    assert all(unrelated not in line for line in lines)
    assert evidence != stamped


def test_without_the_path_the_same_commit_is_not_marked_equal(tmp_path):
    """Matched control: the path restriction is what makes the patch comparison per file."""
    repo, stamped = _rewritten_branch(tmp_path)
    evidence = _commit(
        repo, 'fix: the fix, rewritten', {_REVIEWED_FILE: _FIXED, _OTHER_FILE: 'other, as the rewrite left it\n'}
    )

    restricted = _compare(repo, stamped)
    whole_commit = _compare(repo, stamped, restricted=False)

    assert restricted.returncode == 0, restricted.stderr
    assert whole_commit.returncode == 0, whole_commit.stderr
    assert restricted.stdout.splitlines() == [f'={evidence}']
    assert f'>{evidence}' in whole_commit.stdout.splitlines()
    assert not any(line.startswith('=') for line in whole_commit.stdout.splitlines())


def test_a_different_change_to_the_file_is_not_marked_equal(tmp_path):
    repo, stamped = _rewritten_branch(tmp_path)
    other_fix = _commit(repo, 'fix: another fix', {_REVIEWED_FILE: _FIXED_ANOTHER_WAY})

    done = _compare(repo, stamped)

    assert done.returncode == 0, done.stderr
    assert done.stdout.splitlines() == [f'>{other_fix}']


def test_a_dropped_fix_leaves_no_line(tmp_path):
    """The rewrite kept other work and lost the fix: nothing on the branch touches the file."""
    repo, stamped = _rewritten_branch(tmp_path)
    _commit(repo, 'chore: unrelated', {'unrelated.txt': 'unrelated\n'})

    done = _compare(repo, stamped)

    assert done.returncode == 0, done.stderr
    assert done.stdout.splitlines() == []


def test_an_unknown_stamped_commit_exits_non_zero(tmp_path):
    repo, _stamped = _rewritten_branch(tmp_path)
    _commit(repo, 'fix: the fix, rewritten', {_REVIEWED_FILE: _FIXED})

    done = _compare(repo, _UNKNOWN_COMMIT)

    assert done.returncode != 0
    assert done.stdout == ''


def test_a_stamped_commit_without_a_parent_and_an_unknown_base_exit_non_zero(tmp_path):
    """The two other operands the hook names as reasons for a non-zero exit status."""
    repo, stamped = _rewritten_branch(tmp_path)
    _commit(repo, 'fix: the fix, rewritten', {_REVIEWED_FILE: _FIXED})
    root = _git(repo, 'rev-list', '--max-parents=0', 'HEAD')

    no_parent = _compare(repo, root)
    unknown_base = _compare(repo, stamped, base_branch='no-such-branch')

    assert len(root) == 40, root
    assert no_parent.returncode != 0
    assert no_parent.stdout == ''
    assert unknown_base.returncode != 0
    assert unknown_base.stdout == ''


# ---------------------------------------------------------------------------
# (b) An inline fix a stopped firing left unstamped
# ---------------------------------------------------------------------------


def _reviewed_repo(tmp_path: Path) -> tuple[Path, str]:
    """A repository whose head is the commit the review read. Returns it and that commit."""
    repo = _init(tmp_path)
    reviewed = _commit(repo, 'feat: the reviewed change', {_REVIEWED_FILE: _ORIGINAL, _OTHER_FILE: 'other\n'})
    return repo, reviewed


def _search(repo: Path, reviewed: str) -> subprocess.CompletedProcess[str]:
    """Run the documented search from ``reviewed`` to the head of ``repo``."""
    values = {
        'worktree_path': str(repo),
        'reviewed_commit_sha': reviewed,
        'pushed_head_sha': _git(repo, 'rev-parse', 'HEAD'),
        'file_path': _REVIEWED_FILE,
    }
    return _run(_fill(_documented(_SEARCH_START), values))


def test_one_inline_commit_that_touches_the_file_is_the_one_counted_line(tmp_path):
    repo, reviewed = _reviewed_repo(tmp_path)
    inline = _commit(repo, _INLINE_MESSAGE, {_REVIEWED_FILE: _FIXED})
    _commit(repo, 'chore: unrelated', {'unrelated.txt': 'unrelated\n'})

    done = _search(repo, reviewed)

    assert done.returncode == 0, done.stderr
    assert done.stdout.splitlines() == [f'{inline}\t{_INLINE_MESSAGE}']
    assert _counted(done.stdout) == [inline]
    assert len(inline) == 40, inline


def test_a_commit_with_another_subject_that_touches_the_file_is_not_listed(tmp_path):
    """A changed file alone is no evidence: the discarded file-differs check would have stamped here."""
    repo, reviewed = _reviewed_repo(tmp_path)
    _commit(repo, 'refactor: touch the file', {_REVIEWED_FILE: _FIXED})

    done = _search(repo, reviewed)

    assert done.returncode == 0, done.stderr
    assert done.stdout == ''
    assert _counted(done.stdout) == []


def test_an_inline_commit_that_touches_only_another_file_is_not_listed(tmp_path):
    repo, reviewed = _reviewed_repo(tmp_path)
    _commit(repo, _INLINE_MESSAGE, {_OTHER_FILE: 'other, suppressed\n'})

    done = _search(repo, reviewed)

    assert done.returncode == 0, done.stderr
    assert _counted(done.stdout) == []


def test_two_inline_commits_that_touch_the_file_are_two_counted_lines(tmp_path):
    """Two is not one: the hook stamps nothing, because it cannot tell which holds the edit."""
    repo, reviewed = _reviewed_repo(tmp_path)
    first = _commit(repo, _INLINE_MESSAGE, {_REVIEWED_FILE: _FIXED})
    second = _commit(repo, _INLINE_MESSAGE, {_REVIEWED_FILE: _FIXED + 'six\n'})

    done = _search(repo, reviewed)

    assert done.returncode == 0, done.stderr
    assert sorted(_counted(done.stdout)) == sorted([first, second])
    assert first != second


def test_a_message_that_only_quotes_the_inline_message_is_listed_and_not_counted(tmp_path):
    """``--grep`` matches any line of a message, so the subject comparison does the counting."""
    repo, reviewed = _reviewed_repo(tmp_path)
    quoting = _commit(
        repo,
        f'docs: explain the hook\n\nThe hook commits inline edits with\n{_INLINE_MESSAGE}\n',
        {_REVIEWED_FILE: _FIXED},
    )
    longer = _commit(repo, f'{_INLINE_MESSAGE} again', {_REVIEWED_FILE: _FIXED + 'six\n'})

    done = _search(repo, reviewed)
    listed = [line.partition('\t')[0] for line in done.stdout.splitlines()]

    assert done.returncode == 0, done.stderr
    # Both were matched by --grep, which is why the output alone is not the count.
    assert sorted(listed) == sorted([quoting, longer])
    assert _counted(done.stdout) == []


def test_an_inline_commit_made_before_the_reviewed_commit_is_not_listed(tmp_path):
    """The range starts after the reviewed commit, so an inline commit the review already read is out."""
    repo = _init(tmp_path)
    _commit(repo, _INLINE_MESSAGE, {_REVIEWED_FILE: _ORIGINAL})
    reviewed = _commit(repo, 'feat: the reviewed change', {_REVIEWED_FILE: _FIXED})
    _commit(repo, 'chore: unrelated', {'unrelated.txt': 'unrelated\n'})

    done = _search(repo, reviewed)

    assert done.returncode == 0, done.stderr
    assert done.stdout == ''


def test_an_unknown_reviewed_commit_exits_non_zero(tmp_path):
    repo, _reviewed = _reviewed_repo(tmp_path)
    _commit(repo, _INLINE_MESSAGE, {_REVIEWED_FILE: _FIXED})

    done = _search(repo, _UNKNOWN_COMMIT)

    assert done.returncode != 0
    assert _counted(done.stdout) == []
