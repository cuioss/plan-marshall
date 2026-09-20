#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for git-workflow.py - consolidated git workflow script.

Tier 2 (direct import) tests with subprocess tests for CLI plumbing.
"""

from __future__ import annotations

import os
import re
import subprocess
from argparse import Namespace
from pathlib import Path

import pytest
from toon_parser import parse_toon

from conftest import get_script_path, load_script_module, run_script

# Script under test (for subprocess CLI plumbing tests)
SCRIPT_PATH = get_script_path('plan-marshall', 'workflow-integration-git', 'git-workflow.py')

# The entrypoint filename is kebab-case (git-workflow.py), which is not a
# valid Python module identifier — load it via importlib instead of `import`.
git_workflow = load_script_module('plan-marshall', 'workflow-integration-git', 'git-workflow.py', 'git_workflow')
_SKIP_DIRS = git_workflow._SKIP_DIRS
SAFE_ARTIFACT_PATTERNS = git_workflow.SAFE_ARTIFACT_PATTERNS
UNCERTAIN_ARTIFACT_PATTERNS = git_workflow.UNCERTAIN_ARTIFACT_PATTERNS
VALID_TYPES = git_workflow.VALID_TYPES

# ⛔ Vacuity guard — the vocabulary is production's, so emptying it there collects zero
# cases at the parametrize below and still reports green.
assert VALID_TYPES, 'git_workflow.VALID_TYPES is empty'
analyze_diff = git_workflow.analyze_diff
cmd_detect_artifacts = git_workflow.cmd_detect_artifacts
cmd_format_commit = git_workflow.cmd_format_commit
get_tracked_files = git_workflow.get_tracked_files
scan_artifacts = git_workflow.scan_artifacts
wrap_text = git_workflow.wrap_text


def run_git_script(args: list) -> tuple:
    """Run git_workflow.py with args and return (stdout, stderr, returncode)."""
    result = run_script(SCRIPT_PATH, *args)
    return result.stdout, result.stderr, result.returncode


def _format_commit_args(**overrides) -> Namespace:
    """Build a cmd_format_commit Namespace with sensible defaults for unset fields."""
    fields = {
        'commit_type': 'feat',
        'scope': None,
        'subject': 'subject',
        'body': None,
        'breaking': None,
        'footer': None,
    }
    fields.update(overrides)
    return Namespace(**fields)


def _create_file(root: Path, relpath: str) -> None:
    """Create a file (with parents) within ``root``."""
    full = root / relpath
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text('test')


def _git_init_with_identity(repo: Path) -> None:
    """Initialise a git repo with a throwaway committer identity."""
    subprocess.run(['git', 'init'], cwd=repo, capture_output=True)
    subprocess.run(['git', 'config', 'user.email', 'test@test.com'], cwd=repo, capture_output=True)
    subprocess.run(['git', 'config', 'user.name', 'Test'], cwd=repo, capture_output=True)


def _repo_with_live_worktree(root: Path, worktree_path: Path, branch: str = 'feature/EXAMPLE-PLAN') -> Path:
    """Init ``root`` as a repo with one commit and a linked worktree at ``worktree_path``.

    Models how plan-marshall runs a plan: in a linked git worktree that
    ``git ls-files`` treats as a separate-checkout boundary (it never
    enumerates the worktree's contents), while ``os.walk`` descends into it.
    Returns ``worktree_path`` for convenience.
    """
    _git_init_with_identity(root)
    _create_file(root, 'README.md')
    subprocess.run(['git', 'add', '.'], cwd=root, capture_output=True)
    subprocess.run(['git', 'commit', '-m', 'init'], cwd=root, capture_output=True)
    subprocess.run(['git', 'branch', branch], cwd=root, capture_output=True)
    worktree_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(['git', 'worktree', 'add', str(worktree_path), branch], cwd=root, capture_output=True)
    return worktree_path


#: A running plan's live audit trail, sited directly under the scan root.
_PLAN_STATE_WORKLOG = '.plan/local/plans/EXAMPLE-PLAN/logs/work.log'


def _plan_worktree_scan_root(root: Path) -> None:
    """Model a plan worktree as the scan ROOT: live plan state plus a control artifact.

    Distinct from :func:`_repo_with_live_worktree`, which sites the plan checkout
    *beneath* the scan root where the nested-boundary pruning already covers it.
    Here the plan state is a plain directory directly under the root, so no
    boundary pruning applies and only the unconditional plan-state exclusion can
    keep it out of the offered buckets.
    """
    _git_init_with_identity(root)
    _create_file(root, 'README.md')
    subprocess.run(['git', 'add', 'README.md'], cwd=root, capture_output=True)
    subprocess.run(['git', 'commit', '-m', 'init'], cwd=root, capture_output=True)
    _create_file(root, _PLAN_STATE_WORKLOG)
    _create_file(root, 'scratch.temp')


def _assert_plan_state_excluded_control_safe(result: dict) -> None:
    """The plan's own work.log is offered nowhere, while the control still reaches ``safe``.

    The control assertion is the non-vacuity guard: an empty scan would satisfy
    the negative on its own, which is precisely the confusion this epic is named
    for.
    """
    offered = result['safe'] + result['uncertain']
    assert not any('work.log' in f for f in offered), (
        f"the scan root's own live plan state was offered for deletion: {offered}"
    )
    assert 'scratch.temp' in result['safe'], (
        f'control artifact missing from safe — the exclusion above would be vacuous on an empty scan: {result["safe"]}'
    )


# The identity an unconfigured checkout commits under. Owned by
# manage-run-config (COMMIT_TRAILER_*_DEFAULT) and documented in CLAUDE.md
# § "Commit Trailer"; restated here as the executable form of it.
DEFAULT_COAUTHOR_TRAILER = 'Co-Authored-By: plan-marshall <noreply@cuioss.de>'

# Assistant and vendor names that must never appear in a trailer, whatever the
# configured identity is. The trailer names the system that produced the commit,
# so any of these in one means the convention has been reverted somewhere.
FORBIDDEN_COAUTHOR_TOKENS = (
    'anthropic',
    'claude',
    'openai',
    'chatgpt',
    'gpt-',
    'copilot',
    'gemini',
    'codex',
    'cursor',
)

# Matches a trailer wherever it appears — in a commit template, a skill's worked
# example, or a test fixture's expected output — and captures the identity ONLY,
# not the line around it. Matching the whole line would flag prose that merely
# names a file (CLAUDE.md) beside a perfectly canonical trailer. Assembled from
# concatenated pieces so this pattern does not itself match the sweep.
_TRAILER_PATTERN = re.compile('Co-Authored' + r'-By:\s*[^<>\n]*<[^<>\n]*>')

# The path shape of a dated run record: a numbered report filed under a
# ``cloud-runs/`` directory. Derived from the shape rather than from a list of
# the reports that exist today, so a run filed later is exempt without editing
# this test — the same population-derived contract the two sweeps below keep.
_RUN_RECORD_PATH = re.compile(r'(^|/)cloud-runs/[^/]+/report-\d+\.md$')


def _is_dated_run_record(rel: str) -> bool:
    """Whether a repo-relative path is a dated record of one past execution."""
    return bool(_RUN_RECORD_PATH.search(rel))


def _repo_root() -> Path:
    """Repository root, resolved from git rather than from __file__ depth."""
    result = subprocess.run(
        ['git', 'rev-parse', '--show-toplevel'],
        cwd=Path(__file__).resolve().parent,
        capture_output=True,
        text=True,
        check=True,
    )
    return Path(result.stdout.strip())


def _tracked_trailer_lines() -> tuple[list[tuple[str, str]], int]:
    """Every stated co-author trailer in tracked files, with the files scanned.

    Returns ``(occurrences, files_scanned)`` where each occurrence is
    ``(repo-relative path, the trailer text)`` — the trailer alone, so
    surrounding prose cannot be mistaken for part of the identity.
    ``files_scanned`` is published so an empty or truncated sweep cannot pass as
    a clean result.

    A trailer carrying a ``{placeholder}`` is a composition template rather than
    a stated identity, and is excluded: the value it renders is decided at
    runtime, so judging the template against a literal identity would be a
    category error.

    A dated run record — a ``cloud-runs/**/report-NN.md`` — is excluded for the
    same reason in the other direction: it states the identity a past execution
    committed under, not the identity the convention prescribes now, so judging
    it against the current default is the same category error. The exclusion is
    a path-shape predicate (``_is_dated_run_record``), never a list of the
    reports that happen to exist, and it removes those paths from the swept
    population rather than from its reported size, so ``files_scanned`` stays
    the count of files this sweep actually judged.
    """
    root = _repo_root()
    listing = subprocess.run(
        ['git', 'ls-files', '-z'],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )
    occurrences: list[tuple[str, str]] = []
    scanned = 0
    for rel in listing.stdout.split('\0'):
        if not rel:
            continue
        if _is_dated_run_record(rel):
            continue
        path = root / rel
        try:
            content = path.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            continue  # binary or unreadable — carries no trailer
        scanned += 1
        for match in _TRAILER_PATTERN.finditer(content):
            trailer = match.group(0)
            if '{' in trailer:
                continue
            occurrences.append((rel, trailer))
    return occurrences, scanned


class TestIgnoreExclusionHelpers:
    """Unit coverage for the ignore-set partitioning and prefix-aware exclusion.

    These pin the gitignore-contract logic (D5(a)) deterministically, without
    depending on whether a particular git version collapses a given ignored
    directory: they assert directly that a path *under* a reported ignored
    directory is excluded.
    """

    def test_is_ignored_matches_exact_file_entry(self):
        assert git_workflow._is_ignored('build/output.log', {'build/output.log'}, ())

    def test_is_ignored_matches_path_under_ignored_directory(self):
        # git collapses a fully-ignored directory to one trailing-slash entry;
        # every descendant must still be treated as ignored.
        ignored_dirs = ('.plan/local/worktrees/EXAMPLE-PLAN/',)
        assert git_workflow._is_ignored('.plan/local/worktrees/EXAMPLE-PLAN/logs/work.log', set(), ignored_dirs)


class TestIgnoreQueryHonesty:
    """An ignore set that could not be READ must not be reported as an empty one.

    ``git ls-files --others --ignored --exclude-standard`` enumerates every
    ignored FILE individually. Measured in this repository that is 213256
    entries, against 207 for the same query with ``--directory`` — so without
    the flag the query routinely exceeds its own 30s timeout on a tree carrying
    a mypy cache and a virtualenv.

    Pre-fix, every failure path returned ``set()``, which ``scan_artifacts``
    could not distinguish from "nothing is ignored". An unresolvable ignore set
    was therefore reported as a tree with no ignored files, and the entire
    ignored subtree — including a running plan's live ``.plan/local`` state and
    its in-flight logs — was offered in the auto-deletable ``safe`` bucket. That
    is absence read as measurement, and it is the one failure mode a
    delete-these-files surface must never have.

    The helper tests above cannot catch it: they hand ``_is_ignored`` an
    ``ignored_dirs`` tuple directly, so they stay green while the real query
    never produces a non-empty one.
    """

    def test_unresolvable_ignore_set_offers_nothing_as_safe(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """An unreadable ignore set yields no ``safe`` entry at all."""
        _create_file(tmp_path, 'scratch.temp')
        monkeypatch.setattr(git_workflow, 'get_gitignored_files', lambda root: None)

        result = scan_artifacts(tmp_path, respect_gitignore=True)

        assert result['gitignore_resolved'] is False
        assert result['safe'] == [], f'unresolvable ignore set still offered safe deletions: {result["safe"]}'
        # The artifact was still SEEN — reported, just never as auto-deletable.
        # Without this, a scan that matched nothing would satisfy the assertion
        # above vacuously and the test would pass for the wrong reason.
        assert 'scratch.temp' in result['uncertain']

    def test_resolved_ignore_set_still_offers_safe(self, tmp_path: Path):
        """Matched negative control: the degradation must not suppress the normal path.

        A fix that simply stopped populating ``safe`` would satisfy the test
        above while breaking every real scan, so the ordinary resolved case is
        pinned alongside it.
        """
        _git_init_with_identity(tmp_path)
        _create_file(tmp_path, 'scratch.temp')

        result = scan_artifacts(tmp_path, respect_gitignore=True)

        assert result['gitignore_resolved'] is True
        assert 'scratch.temp' in result['safe']

    def test_ignore_query_requests_collapsed_directory_entries(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """The query passes ``--directory`` so ignored directories collapse.

        Asserted against the constructed argv at the subprocess boundary rather
        than against the returned set, because the flag's absence is precisely
        what keeps ``_split_ignored``'s dirs tuple permanently empty — making
        the prefix arm of ``_is_ignored`` unable to fire for any real input.
        """
        seen: list[list[str]] = []

        class _CompletedStub:
            returncode = 0
            stdout = ''

        def _fake_run(argv, **kwargs):
            seen.append(argv)
            return _CompletedStub()

        monkeypatch.setattr(git_workflow.subprocess, 'run', _fake_run)
        git_workflow.get_gitignored_files(tmp_path)

        assert seen, 'ignore query issued no subprocess call'
        assert '--directory' in seen[0], f'ignore query omits --directory: {seen[0]}'

    def test_query_failure_returns_none_not_empty_set(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """A failed query returns ``None`` — the unknown sentinel — never ``set()``."""

        def _raise_timeout(argv, **kwargs):
            raise subprocess.TimeoutExpired(cmd=argv, timeout=30)

        monkeypatch.setattr(git_workflow.subprocess, 'run', _raise_timeout)

        assert git_workflow.get_gitignored_files(tmp_path) is None


class TestTrackednessOraclePathSpelling:
    """The trackedness oracle must spell paths the way ``scan_artifacts`` does.

    Both git observations parsed newline-delimited output under a strict UTF-8
    decode and called ``.strip()`` on every line. Two reachable defects follow,
    and the second is the dangerous one:

    1. ``.strip()`` destroys leading and trailing spaces, and with
       ``core.quotePath`` at its default git additionally QUOTES any pathname
       carrying non-ASCII bytes or a newline. Either way the returned set does
       not spell the path the way ``scan_artifacts`` spells its ``rel``, so the
       ``rel in tracked`` demotion MISSES — and a tracked, committed fixture
       lands in ``safe[]``, which the subcommand documents as delete-them.
    2. A strict decode raises ``UnicodeDecodeError`` — a ``ValueError``, outside
       the caught tuple — so it escapes instead of yielding the documented
       fail-closed result.

    The remedy is already codified in this repository:
    ``_plan_state_exemption._observe_z`` runs the same class of observation with
    ``-z``, ``errors='surrogateescape'`` and a NUL split, and its own docstring
    names ``path in tracked`` as "the failure ``-z`` was adopted to end". These
    functions are reused rather than re-derived, so the repository keeps one
    predicate instead of a fourth private copy with a fourth path spelling.
    """

    def test_tracked_file_with_leading_space_is_demoted_not_offered(self, tmp_path: Path):
        """A tracked ``' leading.log'`` is recognised and demoted to uncertain.

        Red pre-fix: ``.strip()`` turns the reported ``' leading.log'`` into
        ``'leading.log'``, which never equals the walked ``rel``, so the tracked
        demotion misses and the committed fixture is offered as safe to delete.
        """
        _git_init_with_identity(tmp_path)
        _create_file(tmp_path, ' leading.log')
        subprocess.run(['git', 'add', ' leading.log'], cwd=tmp_path, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'commit spaced fixture'], cwd=tmp_path, capture_output=True)

        result = scan_artifacts(tmp_path, respect_gitignore=True)

        assert ' leading.log' in result['uncertain'], (
            f'tracked spaced fixture not demoted: uncertain={result["uncertain"]}'
        )
        assert ' leading.log' not in result['safe'], f'tracked spaced fixture offered for deletion: {result["safe"]}'

    def test_both_git_observations_are_nul_delimited_and_surrogate_decoded(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """Both oracles request ``-z`` output and decode with ``surrogateescape``.

        Asserted on the constructed call at the subprocess boundary: ``-z`` is
        what makes git emit paths verbatim instead of quoting them, and
        ``surrogateescape`` is what stops a non-UTF-8 byte raising
        ``UnicodeDecodeError`` past the caught tuple. Neither guarantee is
        observable from the returned set on a well-behaved tree, so a
        return-value assertion would pass on a build that had silently lost
        either one.
        """
        seen: list[tuple[list[str], dict]] = []

        class _CompletedStub:
            returncode = 0
            stdout = ''

        def _fake_run(argv, **kwargs):
            seen.append((argv, kwargs))
            return _CompletedStub()

        monkeypatch.setattr(git_workflow.subprocess, 'run', _fake_run)
        git_workflow.get_gitignored_files(tmp_path)
        git_workflow.get_tracked_files(tmp_path)

        assert len(seen) == 2, f'expected two git observations, saw {len(seen)}'
        for argv, kwargs in seen:
            assert '-z' in argv, f'observation is not NUL-delimited: {argv}'
            assert kwargs.get('errors') == 'surrogateescape', (
                f'observation does not decode with surrogateescape: {kwargs}'
            )
            assert not kwargs.get('text'), f'observation still uses strict text=True decoding: {kwargs}'

    def test_unresolvable_tracked_set_offers_nothing_as_safe(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """An unreadable TRACKED set fails closed, exactly as the ignore set does.

        Both oracles feed the same safety decision. An unknown tracked set means
        no match can be proven untracked, so promoting any match to ``safe``
        would be the same absence-read-as-measurement the ignore arm already
        refuses.
        """
        _create_file(tmp_path, 'scratch.temp')
        monkeypatch.setattr(git_workflow, 'get_tracked_files', lambda root: None)

        result = scan_artifacts(tmp_path, respect_gitignore=False)

        assert result['tracked_resolved'] is False
        assert result['safe'] == [], f'unresolvable tracked set still offered safe deletions: {result["safe"]}'
        assert 'scratch.temp' in result['uncertain']

    def test_resolved_oracles_still_offer_safe(self, tmp_path: Path):
        """Matched negative control for BOTH fail-closed arms above.

        A change that simply stopped populating ``safe`` would satisfy every
        degradation assertion in this class and in
        :class:`TestIgnoreQueryHonesty` while breaking every real scan.
        """
        _git_init_with_identity(tmp_path)
        _create_file(tmp_path, 'scratch.temp')

        result = scan_artifacts(tmp_path, respect_gitignore=True)

        assert result['gitignore_resolved'] is True
        assert result['tracked_resolved'] is True
        assert 'scratch.temp' in result['safe']

    def test_walked_path_is_normalised_once_for_every_consumer(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Every consumer of the walked path sees the same ``/``-spelled form.

        ``os.path.relpath`` returns OS-native separators, while ``_observe_z``
        returns the ``/``-spelled paths git emits. The ignore check normalised
        for itself (``rel.replace(os.sep, '/')``) but the artifact-pattern match
        and the ``rel in tracked`` demotion did not, so on a ``\\``-separator
        platform those two diverged from the oracle they are compared against —
        a nested tracked artifact like ``build/output.log`` misses the demotion
        and the ``**/*.log`` safe pattern then routes it to the auto-deletable
        bucket.

        The separator is faked rather than the platform, so the asymmetry is
        exercised on every runner instead of only on Windows: patching
        ``os.sep`` and ``os.path.relpath`` to speak ``\\`` reproduces exactly
        the divergence the native path produces there. On POSIX the production
        normalisation is a no-op, which is precisely why this defect could sit
        unnoticed behind a green suite.
        """
        _git_init_with_identity(tmp_path)
        _create_file(tmp_path, 'build/output.log')
        subprocess.run(['git', 'add', 'build/output.log'], cwd=tmp_path, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'commit nested fixture'], cwd=tmp_path, capture_output=True)

        real_relpath = os.path.relpath

        def _backslash_relpath(path, start=None):
            return real_relpath(path, start).replace('/', '\\')

        monkeypatch.setattr(git_workflow.os, 'sep', '\\')
        monkeypatch.setattr(git_workflow.os.path, 'relpath', _backslash_relpath)

        result = scan_artifacts(tmp_path, respect_gitignore=True)

        offered = result['safe'] + result['uncertain']
        assert not any('output.log' in f for f in result['safe']), (
            f'tracked nested fixture offered as safe under \\ separators: {result["safe"]}'
        )
        # Positive population: it WAS seen and classified, so the negative above
        # is not a scan that simply matched nothing.
        assert any('output.log' in f for f in offered), f'tracked nested fixture not classified at all: {offered}'

    def test_is_ignored_no_false_prefix_match(self):
        # A sibling path that merely shares a name prefix must NOT be excluded.
        ignored_dirs = ('build/',)
        assert not git_workflow._is_ignored('build-tools/main.py', set(), ignored_dirs)

    def test_is_ignored_empty_set_excludes_nothing(self):
        assert not git_workflow._is_ignored('any/path.log', set(), ())

    def test_is_nested_git_boundary_detects_dot_git(self, tmp_path: Path):
        nested = tmp_path / 'sub'
        nested.mkdir()
        (nested / '.git').write_text('gitdir: /elsewhere\n')  # linked-worktree marker
        assert git_workflow._is_nested_git_boundary(str(nested))

    def test_is_nested_git_boundary_false_for_plain_dir(self, tmp_path: Path):
        plain = tmp_path / 'sub'
        plain.mkdir()
        assert not git_workflow._is_nested_git_boundary(str(plain))


class TestArtifactConfigLoading:
    """Test that artifact patterns are loaded from artifact-patterns.json config."""

    def test_safe_patterns_loaded(self):
        """Safe artifact patterns are loaded from config."""
        assert isinstance(SAFE_ARTIFACT_PATTERNS, list)
        assert len(SAFE_ARTIFACT_PATTERNS) > 0
        patterns_str = ' '.join(SAFE_ARTIFACT_PATTERNS)
        assert '*.class' in patterns_str
        assert '*.pyc' in patterns_str
        assert '.DS_Store' in patterns_str

    def test_uncertain_patterns_loaded(self):
        """Uncertain artifact patterns are loaded from config."""
        assert isinstance(UNCERTAIN_ARTIFACT_PATTERNS, list)
        assert len(UNCERTAIN_ARTIFACT_PATTERNS) > 0
        assert 'target/**' in ' '.join(UNCERTAIN_ARTIFACT_PATTERNS)

    def test_skip_dirs_loaded(self):
        """Skip directories are loaded from config."""
        assert isinstance(_SKIP_DIRS, set)
        assert '.git' in _SKIP_DIRS
        assert 'node_modules' in _SKIP_DIRS
        assert '.venv' in _SKIP_DIRS

    def test_no_overlap_between_skip_dirs_and_uncertain(self):
        """skip_dirs entries are not also in uncertain_patterns."""
        for skip_dir in _SKIP_DIRS:
            for pattern in UNCERTAIN_ARTIFACT_PATTERNS:
                assert not (pattern.startswith(f'{skip_dir}/') or pattern.startswith(f'{skip_dir}/**')), (
                    f'skip_dir "{skip_dir}" overlaps with uncertain pattern "{pattern}"'
                )


class TestToonContract:
    """Verify output matches the contract documented in SKILL.md."""

    def test_format_commit_output_contract(self):
        """format-commit output has all documented fields."""
        result = cmd_format_commit(_format_commit_args(commit_type='feat', scope='auth', subject='add login'))

        required_fields = {'type', 'scope', 'subject', 'formatted_message', 'validation', 'status'}
        assert required_fields - set(result.keys()) == set()
        assert 'valid' in result['validation']
        assert 'warnings' in result['validation']


class TestWorktreeRemoveMoveBackPrecondition:
    """worktree-remove — the two script-enforced removal preconditions.

    Proves (a) removal REFUSES with ``plan_dir_not_moved_back`` while the
    worktree still holds the sole plan-state copy and main holds no plan dir;
    (b) the refusal persists under ``--force`` (the flag keeps its dirty-tree
    meaning only); (c) removal succeeds after the plan dir is moved to main's
    ``.plan/local/plans/{plan_id}/``; (d) the existing noop branch (target
    absent) is unchanged. Fixture ``.gitignore`` covers ``.plan/`` so
    worktree-resident plan state never blocks the non-force removal.

    It also proves (e) the independent ``cwd_inside_removal_target`` refusal:
    standing at or beneath the target refuses even once the move-back has
    landed, refuses under ``--force``, and refuses while the move-back
    predicate is forced to report success — the last of these is what shows the
    two preconditions are carried by two defences rather than by one. Those
    cases vary **cwd** via ``monkeypatch.chdir`` and never patch a resolver,
    because a patched resolver cannot observe where the process is standing;
    each is paired with a matched control that differs in cwd alone.
    """

    PLAN_ID = 'moveback-plan'
    BRANCH = 'feature/moveback-plan'

    def _seed_main_and_worktree(self, tmp_path: Path) -> tuple[Path, Path]:
        """Create a main repo plus a registered worktree holding plan state."""
        main = tmp_path / 'main'
        main.mkdir()
        _git_init_with_identity(main)
        (main / '.gitignore').write_text('.plan/\n')
        (main / 'file.txt').write_text('one')
        subprocess.run(['git', 'add', '.'], cwd=main, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'init'], cwd=main, capture_output=True)

        worktree = tmp_path / 'wt'
        subprocess.run(
            ['git', '-C', str(main), 'worktree', 'add', '-b', self.BRANCH, str(worktree)],
            capture_output=True,
            check=True,
        )
        # Worktree-resident plan state — the sole authoritative copy pre-move-back.
        plan_dir = worktree / '.plan' / 'local' / 'plans' / self.PLAN_ID
        plan_dir.mkdir(parents=True)
        (plan_dir / 'status.json').write_text('{}')
        return main, worktree

    @staticmethod
    def _pin_main_anchor(monkeypatch, main: Path) -> None:
        """Tell the move-back guard which tree is "main", via the real resolver.

        ``_plan_dir_on_main_checkout`` probes through
        ``marketplace_paths.resolve_main_anchored_path``, whose FIRST precedence branch
        is the ``PLAN_BASE_DIR`` / ``set_base_dir()`` override — so pinning the override
        at ``{main}/.plan/local`` points the guard at the fixture's main tree without
        replacing the resolver. ``main_checkout_root`` is pinned separately by
        :meth:`_patch`, because it is a different resolver serving a different need (the
        ``git -C`` target, which must name a real git checkout).
        """
        import file_ops  # local import: the handle is needed only to patch a seam here

        monkeypatch.setenv('PLAN_BASE_DIR', str(main / '.plan' / 'local'))
        monkeypatch.setattr(file_ops, '_BASE_DIR_OVERRIDE', None)

    def _patch(self, monkeypatch, main: Path, worktree: Path) -> None:
        monkeypatch.setattr(git_workflow, '_resolve_worktree_path_for_plan', lambda plan_id: (worktree, None))
        monkeypatch.setattr(git_workflow, 'main_checkout_root', lambda: main)
        self._pin_main_anchor(monkeypatch, main)
        monkeypatch.setattr(git_workflow, '_read_metadata_field', lambda plan_id, field: '')

    def _land_plan_dir_on_main(self, main: Path) -> None:
        """Simulate integrate_into_main landing the plan dir back on main."""
        main_plan_dir = main / '.plan' / 'local' / 'plans' / self.PLAN_ID
        main_plan_dir.mkdir(parents=True)
        (main_plan_dir / 'status.json').write_text('{}')

    def _worktree_status_json(self, worktree: Path) -> Path:
        return worktree / '.plan' / 'local' / 'plans' / self.PLAN_ID / 'status.json'

    def _remove(self, force: bool = False) -> dict:
        return dict(git_workflow.cmd_worktree_remove(Namespace(plan_id=self.PLAN_ID, force=force)))

    def test_refuses_while_plan_dir_not_moved_back(self, tmp_path: Path, monkeypatch):
        """(a) plan dir only in the worktree, main empty → refusal, tree intact."""
        main, worktree = self._seed_main_and_worktree(tmp_path)
        self._patch(monkeypatch, main, worktree)

        result = self._remove()

        assert result['status'] == 'error'
        assert result['error'] == 'plan_dir_not_moved_back', (
            f'Expected the move-back precondition refusal, got {result!r}.'
        )
        assert 'integrate_into_main' in result['message']
        assert worktree.exists(), 'The refusal must leave the worktree (the sole plan-state copy) intact.'

    def test_force_does_not_override_refusal(self, tmp_path: Path, monkeypatch):
        """(b) --force keeps its dirty-tree meaning only — refusal persists."""
        main, worktree = self._seed_main_and_worktree(tmp_path)
        self._patch(monkeypatch, main, worktree)

        result = self._remove(force=True)

        assert result['status'] == 'error'
        assert result['error'] == 'plan_dir_not_moved_back', (
            f'--force must NOT bypass the move-back precondition, got {result!r}.'
        )
        assert worktree.exists()

    def test_succeeds_after_plan_dir_moved_to_main(self, tmp_path: Path, monkeypatch):
        """(c) plan dir landed on main → removal proceeds."""
        main, worktree = self._seed_main_and_worktree(tmp_path)
        self._patch(monkeypatch, main, worktree)
        self._land_plan_dir_on_main(main)

        result = self._remove()

        assert result['status'] == 'success', f'Expected removal to proceed, got {result!r}.'
        assert result['action'] == 'removed'
        assert not worktree.exists()

    def test_noop_branch_unchanged_when_target_absent(self, tmp_path: Path, monkeypatch):
        """(d) absent worktree still short-circuits to the noop success."""
        main, _worktree = self._seed_main_and_worktree(tmp_path)
        absent = tmp_path / 'absent-wt'
        monkeypatch.setattr(git_workflow, '_resolve_worktree_path_for_plan', lambda plan_id: (absent, None))
        monkeypatch.setattr(git_workflow, 'main_checkout_root', lambda: main)
        monkeypatch.setattr(git_workflow, '_read_metadata_field', lambda plan_id, field: '')

        result = self._remove()

        assert result['status'] == 'success'
        assert result['action'] == 'noop', (
            f'The target-absent noop branch must fire BEFORE the move-back precondition, got {result!r}.'
        )

    @pytest.mark.parametrize('subdir', ['', 'nested/deeper'])
    def test_refuses_when_cwd_inside_removal_target(self, tmp_path: Path, monkeypatch, subdir: str):
        """(e) cwd at — or beneath — the target refuses, move-back notwithstanding.

        The plan dir HAS landed on main here, so the move-back precondition is
        satisfied and the only thing left to refuse is the containment test.
        """
        main, worktree = self._seed_main_and_worktree(tmp_path)
        self._patch(monkeypatch, main, worktree)
        self._land_plan_dir_on_main(main)
        cwd = worktree / subdir if subdir else worktree
        cwd.mkdir(parents=True, exist_ok=True)
        monkeypatch.chdir(cwd)

        result = self._remove()

        assert result['status'] == 'error'
        assert result['error'] == 'cwd_inside_removal_target', (
            f'Standing at {cwd} must refuse the removal, got {result!r}.'
        )
        assert Path(result['cwd']) == cwd.resolve()
        assert 'change directory out of the worktree' in result['message']
        assert 'Pass --force' not in result['message'], 'The message must name the remedy, not offer --force as one.'
        assert worktree.exists()

    def test_cwd_refusal_not_overridable_by_force(self, tmp_path: Path, monkeypatch):
        """(e) --force does not buy a way out of the containment refusal."""
        main, worktree = self._seed_main_and_worktree(tmp_path)
        self._patch(monkeypatch, main, worktree)
        self._land_plan_dir_on_main(main)
        monkeypatch.chdir(worktree)

        result = self._remove(force=True)

        assert result['status'] == 'error'
        assert result['error'] == 'cwd_inside_removal_target', (
            f'--force must NOT bypass the cwd-containment refusal, got {result!r}.'
        )
        assert worktree.exists()

    def test_cwd_refusal_survives_a_neutralised_move_back_predicate(self, tmp_path: Path, monkeypatch):
        """(e) the refusal does not ride on the move-back predicate's verdict.

        The predicate is forced to report "moved back" while main in fact holds
        no plan dir at all — the geometry in which the two defences would be
        indistinguishable if one predicate carried both. The worktree-resident
        ``status.json`` surviving is the property under test; the return code
        alone would not show that the file the refusal exists to protect is
        still there.
        """
        main, worktree = self._seed_main_and_worktree(tmp_path)
        self._patch(monkeypatch, main, worktree)
        monkeypatch.setattr(git_workflow, '_plan_dir_on_main_checkout', lambda plan_id: True)
        monkeypatch.chdir(worktree)

        result = self._remove()

        assert result['error'] == 'cwd_inside_removal_target', (
            f'The containment test must refuse on its own, got {result!r}.'
        )
        assert self._worktree_status_json(worktree).is_file(), (
            'The refusal exists to protect the worktree-resident plan state.'
        )

    def test_matched_control_cwd_on_main_still_succeeds(self, tmp_path: Path, monkeypatch):
        """(e) matched negative control — identical fixture, cwd on main.

        Differs from ``test_refuses_when_cwd_inside_removal_target`` in cwd and
        nothing else, which is what makes that refusal attributable to where the
        process stands rather than to anything the fixture set up.
        """
        main, worktree = self._seed_main_and_worktree(tmp_path)
        self._patch(monkeypatch, main, worktree)
        self._land_plan_dir_on_main(main)
        monkeypatch.chdir(main)

        result = self._remove()

        assert result['status'] == 'success', f'Standing on main must still reach the existing outcome, got {result!r}.'
        assert result['action'] == 'removed'
        assert not worktree.exists()


# =============================================================================
# Subprocess (Tier 3) tests -- CLI plumbing only
# =============================================================================


class TestMain:
    """Test git_workflow.py main entry point (CLI plumbing)."""

    def test_no_subcommand(self):
        """Error when no subcommand provided."""
        _, _stderr, code = run_git_script([])

        assert code != 0

    def test_help(self):
        """Help output lists the subcommands."""
        stdout, _, code = run_git_script(['--help'])

        assert code == 0
        assert 'format-commit' in stdout
        assert 'analyze-diff' in stdout

    def test_missing_required_args(self):
        """Error when required args missing."""
        _, stderr, code = run_git_script(['format-commit'])

        assert code != 0
        assert '--type' in stderr


class TestCoAuthorTrailerConvention:
    """The co-author trailer names the system, not an assistant or its vendor.

    Both sweeps are population-derived: they enumerate tracked files rather than
    a hand-maintained list of "the places that state the trailer", so a site
    added later is covered without editing this test. The two invariants have
    genuinely different populations, which is why they are separate:

    * No tracked file anywhere may name a vendor or assistant in a trailer.
    * Every trailer OUTSIDE ``test/`` states the default identity. Test code is
      excluded by a derived partition, not by a file list, because exercising a
      configured override is exactly what the run-config knob's tests do.
    """

    def test_sweep_covers_a_non_empty_population(self):
        """A clean result is only meaningful if files were actually read."""
        occurrences, scanned = _tracked_trailer_lines()

        assert scanned > 100, f'implausibly small sweep: {scanned} files read'
        assert occurrences, (
            f'no trailer line found in {scanned} tracked files — the probe no '
            'longer matches anything, so a passing sweep proves nothing'
        )

    def test_run_record_exclusion_covers_a_report_and_nothing_wider(self):
        """The exemption is the ``cloud-runs/**/report-NN.md`` shape exactly.

        Both arms matter: an exclusion that stopped matching would red the
        sweep on historical records it must not judge, and one that matched
        wider would silently shrink the population the other two tests sweep.
        """
        excluded = '.plan/orchestrator/truthful-signals/cloud-runs/380-x/report-01.md'

        assert _is_dated_run_record(excluded)
        assert not _is_dated_run_record('.plan/orchestrator/truthful-signals/README.md')
        assert not _is_dated_run_record(
            '.plan/orchestrator/truthful-signals/cloud-runs/380-x/plan.md'
        )

    def test_no_tracked_trailer_names_an_assistant_or_vendor(self):
        """The trailer identifies the producing system, never who powered it."""
        occurrences, scanned = _tracked_trailer_lines()

        deviations = [
            (rel, line)
            for rel, line in occurrences
            if any(token in line.lower() for token in FORBIDDEN_COAUTHOR_TOKENS)
        ]

        assert not deviations, (
            f'assistant/vendor identity in {len(deviations)} of '
            f'{len(occurrences)} trailer occurrences across {scanned} tracked '
            'files: ' + '; '.join(f'{rel}: {line}' for rel, line in deviations)
        )

    def test_every_non_test_trailer_is_the_default_identity(self):
        """Documentation and workflow sites state the resolver's default.

        The default, not a configured override: run-configuration.json is
        git-ignored, so a fresh clone resolves to the default and that is what
        the documentation must show.
        """
        occurrences, scanned = _tracked_trailer_lines()
        non_test = [(rel, line) for rel, line in occurrences if not rel.startswith('test/')]

        assert non_test, (
            f'no trailer found outside test/ in {scanned} tracked files — the '
            'documented convention has no stated site left to check'
        )
        deviations = [(rel, line) for rel, line in non_test if line != DEFAULT_COAUTHOR_TRAILER]

        assert not deviations, (
            f'non-default co-author trailer in {len(deviations)} of '
            f'{len(non_test)} non-test occurrences across {scanned} tracked '
            'files: ' + '; '.join(f'{rel}: {line}' for rel, line in deviations)
        )
