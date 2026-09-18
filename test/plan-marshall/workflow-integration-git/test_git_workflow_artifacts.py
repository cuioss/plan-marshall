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


class TestDetectArtifacts:
    """Test git_workflow.py detect-artifacts via direct import."""

    def test_detects_safe_artifacts(self, tmp_path: Path):
        """Detection of safe-to-delete artifacts."""
        _create_file(tmp_path, 'src/main/java/Example.class')
        _create_file(tmp_path, '.DS_Store')
        _create_file(tmp_path, 'module/__pycache__/foo.pyc')
        _create_file(tmp_path, 'scratch.temp')

        result = scan_artifacts(tmp_path, respect_gitignore=False)

        assert len(result['safe']) >= 4
        safe_str = '\n'.join(result['safe'])
        assert '.class' in safe_str
        assert '.DS_Store' in safe_str

    def test_detects_uncertain_artifacts(self, tmp_path: Path):
        """Detection of uncertain artifacts in target/build dirs."""
        _create_file(tmp_path, 'target/classes/App.class')
        _create_file(tmp_path, 'target/output.jar')
        _create_file(tmp_path, 'build/libs/app.jar')

        result = scan_artifacts(tmp_path, respect_gitignore=False)

        assert len(result['uncertain']) >= 1 or len(result['safe']) >= 1
        assert result['total'] > 0

    def test_detects_python_egg_artifacts(self, tmp_path: Path):
        """Detection of Python .egg-info and .eggs artifacts."""
        _create_file(tmp_path, 'mypackage.egg-info/PKG-INFO')
        _create_file(tmp_path, '.eggs/some-egg.egg')

        result = scan_artifacts(tmp_path, respect_gitignore=False)

        assert len(result['safe']) >= 2
        safe_str = '\n'.join(result['safe'])
        assert 'egg-info' in safe_str
        assert '.eggs' in safe_str

    def test_detects_typescript_buildinfo(self, tmp_path: Path):
        """Detection of TypeScript .tsbuildinfo files."""
        _create_file(tmp_path, 'tsconfig.tsbuildinfo')
        _create_file(tmp_path, 'packages/lib/tsconfig.tsbuildinfo')

        result = scan_artifacts(tmp_path, respect_gitignore=False)

        safe_str = '\n'.join(result['safe'])
        assert 'tsbuildinfo' in safe_str
        assert len(result['safe']) >= 2

    def test_excludes_plan_state_dir_from_scan(self, tmp_path: Path):
        """A path whose FIRST SEGMENT is ``.plan/`` is excluded unconditionally.

        The exclusion is keyed on the first path segment and applied BEFORE the
        ignore lookup, so it depends on no ignore mechanism. ``respect_gitignore
        =False`` is the load-bearing part of the arrangement: with the ignore
        oracle never consulted, an exclusion that leaned on it would not fire,
        and ``.plan/temp`` would reappear in ``safe``. The same independence is
        what makes the exclusion survive a ``.gitignore`` carrying no ``.plan``
        rule and an empty-but-successful ignore set.

        This inverts an earlier assertion that ``.plan/temp`` IS offered as
        safe. That contract is retired: ``.plan/`` is this repository's
        scratch AND live-plan-state directory, and offering any of it for
        deletion is what let a running plan's own audit trail be destroyed.
        Cleanup of ``.plan/temp`` is owned by the retention machinery
        (``system.retention.temp_on_maintenance``), not by artifact scanning.
        """
        _create_file(tmp_path, '.plan/temp/scratch.txt')
        _create_file(tmp_path, '.plan/temp/debug.log')
        # Positive population: a real artifact OUTSIDE .plan/ that the scan must
        # still offer, so the two absences below are not a vacuous empty scan.
        _create_file(tmp_path, 'scratch.temp')

        result = scan_artifacts(tmp_path, respect_gitignore=False)

        assert '.plan/temp' not in '\n'.join(result['safe']), (
            f'.plan/ state offered as safe-to-delete: {result["safe"]}'
        )
        assert '.plan/temp' not in '\n'.join(result['uncertain']), (
            f'.plan/ state offered for deletion at all: {result["uncertain"]}'
        )
        assert 'scratch.temp' in result['safe'], f'control artifact missing from safe: {result["safe"]}'

    def test_detects_dist_next_as_uncertain(self, tmp_path: Path):
        """dist/ and .next/ directories are uncertain."""
        _create_file(tmp_path, 'dist/bundle.js')
        _create_file(tmp_path, '.next/cache/data.json')

        result = scan_artifacts(tmp_path, respect_gitignore=False)

        uncertain_str = '\n'.join(result['uncertain'])
        assert 'dist/' in uncertain_str
        assert '.next/' in uncertain_str

    def test_detects_root_level_artifacts(self, tmp_path: Path):
        """Detection of artifacts at repo root."""
        _create_file(tmp_path, 'Example.class')
        _create_file(tmp_path, '.DS_Store')
        _create_file(tmp_path, 'scratch.temp')

        result = scan_artifacts(tmp_path, respect_gitignore=False)

        assert len(result['safe']) >= 3
        safe_str = '\n'.join(result['safe'])
        assert 'Example.class' in safe_str
        assert '.DS_Store' in safe_str
        assert 'scratch.temp' in safe_str

    def test_clean_directory_returns_empty(self, tmp_path: Path):
        """Scanning a directory with no artifacts returns empty results."""
        _create_file(tmp_path, 'src/main/java/App.java')
        _create_file(tmp_path, 'README.md')

        result = scan_artifacts(tmp_path, respect_gitignore=False)

        assert result['total'] == 0
        assert result['safe'] == []
        assert result['uncertain'] == []

    def test_nonexistent_root_fails(self):
        """Error when root directory doesn't exist."""
        result = cmd_detect_artifacts(Namespace(root='/nonexistent/path', no_gitignore=False))

        assert result['status'] == 'error'
        assert 'not found' in result['error']

    def test_skips_git_directory(self, tmp_path: Path):
        """.git/ directory contents are excluded from results."""
        _create_file(tmp_path, '.git/objects/pack/pack-abc.class')
        _create_file(tmp_path, '.git/hooks/pre-commit.pyc')
        _create_file(tmp_path, 'src/real.temp')

        result = scan_artifacts(tmp_path, respect_gitignore=False)

        all_files = result['safe'] + result['uncertain']
        assert all(not f.startswith('.git/') for f in all_files)
        assert any('real.temp' in f for f in result['safe'])

    def test_fixture_path_classified_as_uncertain(self, tmp_path: Path):
        """Fixture files under test/**/fixtures/** land in uncertain, not safe."""
        _create_file(tmp_path, 'test/foo/fixtures/sample.dat')

        result = scan_artifacts(tmp_path, respect_gitignore=False)

        assert 'test/foo/fixtures/sample.dat' in '\n'.join(result['uncertain'])
        assert 'test/foo/fixtures/sample.dat' not in '\n'.join(result['safe'])

    def test_non_repo_graceful_degradation(self, tmp_path: Path):
        """scan_artifacts must not raise when called outside a git repo."""
        # No git init — tmp_path is a plain directory. Create a benign file so
        # traversal has something to process.
        _create_file(tmp_path, 'src/main.py')

        result = scan_artifacts(tmp_path, respect_gitignore=False)

        assert isinstance(result, dict)
        assert 'safe' in result
        assert 'uncertain' in result
        assert 'total' in result
        # get_tracked_files degrades to an empty set when no git repo exists.
        assert get_tracked_files(tmp_path) == set()


class TestTrackedFileFilter:
    """Test that tracked files matching safe patterns are demoted to uncertain."""

    def test_tracked_safe_pattern_file_downgrades_to_uncertain(self, tmp_path: Path):
        """A committed *.log file appears in uncertain (never in safe)."""
        _git_init_with_identity(tmp_path)
        _create_file(tmp_path, 'debug.log')
        subprocess.run(['git', 'add', 'debug.log'], cwd=tmp_path, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'commit debug.log'], cwd=tmp_path, capture_output=True)

        result = scan_artifacts(tmp_path, respect_gitignore=False)

        assert 'debug.log' in result['uncertain']
        assert 'debug.log' not in result['safe']

    def test_untracked_safe_pattern_file_stays_safe(self, tmp_path: Path):
        """An untracked *.log file (not gitignored) remains in safe (regression guard)."""
        _git_init_with_identity(tmp_path)
        # No .gitignore is created, so the file is not gitignored.
        # No `git add` — the file remains untracked.
        _create_file(tmp_path, 'debug.log')

        result = scan_artifacts(tmp_path, respect_gitignore=False)

        assert 'debug.log' in result['safe']
        assert 'debug.log' not in result['uncertain']

    def test_tracked_file_scanned_from_subdir_still_downgrades(self, tmp_path: Path):
        """Scanning a subdirectory of a repo still demotes tracked safe matches.

        Regression guard for the ``--full-name`` bug: ``git ls-files`` must
        return paths relative to the scanned ``root`` (the subdir) so the
        ``rel in tracked`` check matches.
        """
        _git_init_with_identity(tmp_path)
        _create_file(tmp_path, 'sub/debug.log')
        subprocess.run(['git', 'add', 'sub/debug.log'], cwd=tmp_path, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'commit sub/debug.log'], cwd=tmp_path, capture_output=True)

        result = scan_artifacts(tmp_path / 'sub', respect_gitignore=False)

        assert 'debug.log' in result['uncertain']
        assert 'debug.log' not in result['safe']


class TestDetectArtifactsGitignore:
    """Test detect-artifacts with gitignore integration (subprocess-dependent)."""

    def test_respects_gitignore_by_default(self, tmp_path: Path):
        """Gitignored files are excluded from results by default."""
        _git_init_with_identity(tmp_path)
        (tmp_path / '.gitignore').write_text('*.class\n')
        subprocess.run(['git', 'add', '.gitignore'], cwd=tmp_path, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'init'], cwd=tmp_path, capture_output=True)
        _create_file(tmp_path, 'src/Example.class')
        _create_file(tmp_path, 'scratch.temp')

        stdout, _, code = run_git_script(['detect-artifacts', '--root', str(tmp_path)])

        assert code == 0
        result = parse_toon(stdout)
        safe_files = result['safe']
        assert not any('.class' in f for f in safe_files), f'.class should be excluded: {safe_files}'
        assert any('.temp' in f for f in safe_files), f'.temp should be present: {safe_files}'

    def test_no_gitignore_flag_includes_all(self, tmp_path: Path):
        """--no-gitignore includes gitignored files."""
        _git_init_with_identity(tmp_path)
        (tmp_path / '.gitignore').write_text('*.class\n')
        subprocess.run(['git', 'add', '.gitignore'], cwd=tmp_path, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'init'], cwd=tmp_path, capture_output=True)
        _create_file(tmp_path, 'src/Example.class')

        stdout, _, code = run_git_script(['detect-artifacts', '--root', str(tmp_path), '--no-gitignore'])

        assert code == 0
        result = parse_toon(stdout)
        safe_files = result['safe']
        assert any('.class' in f for f in safe_files), f'.class should be present with --no-gitignore: {safe_files}'


class TestDetectArtifactsLivePlanArtifacts:
    """A running plan's own live artifacts must never be offered as safe-to-delete.

    plan-marshall runs a plan in a linked git worktree under
    ``.plan/local/worktrees/{plan}/``. ``git ls-files --others --ignored
    --exclude-standard`` collapses that nested-worktree boundary to a single
    trailing-slash directory entry instead of enumerating its contents, while
    ``os.walk`` descends into it. An exact-string ``rel in ignored`` membership
    test therefore misses every file beneath the worktree — including the
    running plan's in-flight ``logs/work.log`` (its live audit trail) and its
    build caches — and offers them as safe. A caller that follows the
    documented "for safe artifacts, delete them" instruction then destroys the
    evidence of the run still producing it.
    """

    def test_live_plan_worklog_never_offered_as_safe(self, tmp_path: Path):
        """D5(b): the running plan's own logs/work.log is never in ``safe``.

        Red pre-fix: the worktree boundary collapses in ``git ls-files`` and the
        exact-match exclusion misses ``…/logs/work.log``, so it lands in ``safe``.
        """
        worktree = _repo_with_live_worktree(tmp_path, tmp_path / '.plan' / 'local' / 'worktrees' / 'EXAMPLE-PLAN')
        _create_file(worktree, 'logs/work.log')
        _create_file(worktree, '.mypy_cache/3.11/builtins.data.json')
        # A control artifact OUTSIDE any worktree that SHOULD be offered as safe.
        _create_file(tmp_path, 'scratch.temp')

        result = scan_artifacts(tmp_path, respect_gitignore=True)
        offered = result['safe'] + result['uncertain']

        assert not any('work.log' in f for f in result['safe']), (
            f"live plan's own work.log offered as safe: {result['safe']}"
        )
        assert not any('EXAMPLE-PLAN' in f for f in offered), (
            f'running-plan worktree path offered for deletion: {offered}'
        )
        # Positive population: the scan DID classify a real artifact, so the
        # absence above is meaningful rather than a scan that matched nothing.
        assert 'scratch.temp' in result['safe'], f'control artifact missing from safe: {result["safe"]}'

    def test_nested_plan_worktree_caches_excluded_by_boundary_pruning(self, tmp_path: Path):
        """A nested plan worktree's caches are offered nowhere — via boundary pruning.

        Named for the mechanism it actually pins. The worktree is a nested git
        boundary, so ``_is_nested_git_boundary`` drops the whole subtree during
        traversal, before ``_is_ignored`` is ever consulted. This test therefore
        stays green even if the collapsed-directory prefix arm is reverted to
        exact-string membership, and it is NOT coverage of that arm —
        ``TestCollapsedIgnoredDirPrefixBranch`` is.
        """
        (tmp_path / '.gitignore').write_text('.plan/\n')
        worktree = _repo_with_live_worktree(tmp_path, tmp_path / '.plan' / 'local' / 'worktrees' / 'EXAMPLE-PLAN')
        _create_file(worktree, '.mypy_cache/3.11/builtins.data.json')
        _create_file(worktree, 'module/__pycache__/foo.pyc')
        _create_file(tmp_path, 'scratch.temp')

        result = scan_artifacts(tmp_path, respect_gitignore=True)
        offered = result['safe'] + result['uncertain']

        assert not any('.mypy_cache' in f for f in offered), (
            f'gitignored worktree cache offered for deletion: {offered}'
        )
        assert not any('__pycache__' in f for f in offered), (
            f'gitignored worktree cache offered for deletion: {offered}'
        )
        # Positive population — the exclusions above are not a vacuous empty scan.
        assert 'scratch.temp' in result['safe'], f'control artifact missing from safe: {result["safe"]}'

    def test_exposure_derivation_nonempty_and_excludes_live_member(self, tmp_path: Path):
        """D5(c): the exposure derivation is asserted non-empty and contains a
        known member, while the live-plan member is excluded.

        The positive half (``safe`` non-empty and containing a known control
        artifact) is the guard the epic's namesake defect defeats: a scan that
        matched nothing looks identical to a clean tree, so a negative like
        D5(b) would pass vacuously. Pairing it with the negative (the live
        plan's own ``work.log`` is absent) makes this test red pre-fix and
        proves the derivation both examined a populated tree and filtered the
        live member out of it.
        """
        worktree = _repo_with_live_worktree(tmp_path, tmp_path / '.plan' / 'local' / 'worktrees' / 'EXAMPLE-PLAN')
        _create_file(worktree, 'logs/work.log')
        _create_file(tmp_path, 'scratch.temp')

        result = scan_artifacts(tmp_path, respect_gitignore=True)

        assert result['safe'], 'scan produced an empty safe set — the negatives would be vacuous'
        assert 'scratch.temp' in result['safe'], f'control artifact missing from safe: {result["safe"]}'
        assert not any('work.log' in f for f in result['safe']), (
            f"live plan's own work.log offered as safe: {result['safe']}"
        )

    def test_worklog_excluded_independent_of_gitignore(self, tmp_path: Path):
        """D3 independence: the invariant holds for a worktree at a NON-gitignored
        path scanned with ``respect_gitignore=False``.

        This proves the protection is not merely a side effect of the gitignore
        contract: with the ignore set never consulted, a running plan's own
        checkout is still never offered for deletion.
        """
        worktree = _repo_with_live_worktree(tmp_path, tmp_path / 'nested-wt')
        _create_file(worktree, 'logs/work.log')
        _create_file(tmp_path, 'scratch.temp')

        result = scan_artifacts(tmp_path, respect_gitignore=False)

        assert not any('work.log' in f for f in result['safe']), (
            f"live plan's work.log offered as safe without gitignore: {result['safe']}"
        )
        assert 'scratch.temp' in result['safe'], f'control artifact missing from safe: {result["safe"]}'


class TestDetectArtifactsIndeterminateIgnoreSet:
    """Under default flags, an ignore set that cannot be read is an error, not a result.

    ``cmd_detect_artifacts`` used to return ``status: 'success'`` carrying
    ``gitignore_resolved: False`` on this input. The output contract tells every
    caller to branch on ``status``, so that payload was indistinguishable from a
    scan that genuinely resolved a clean tree.

    The failure is driven at the ``_observe_z`` seam — the lowest one that still
    lets the real ``get_gitignored_files`` run and return its documented ``None``
    with no exception escaping. Only the ``--ignored`` observation is failed, so
    the trackedness oracle stays real and the error is attributable to the ignore
    oracle alone.
    """

    @staticmethod
    def _repo_with_one_gitignored_artifact(root: Path) -> None:
        _git_init_with_identity(root)
        (root / '.gitignore').write_text('*.class\n')
        subprocess.run(['git', 'add', '.gitignore'], cwd=root, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'init'], cwd=root, capture_output=True)
        _create_file(root, 'src/Example.class')

    @staticmethod
    def _fail_only_the_ignore_query(monkeypatch: pytest.MonkeyPatch) -> None:
        real_observe = git_workflow._observe_z

        def _observe(tree, git_args):
            if '--ignored' in git_args:
                return None
            return real_observe(tree, git_args)

        monkeypatch.setattr(git_workflow, '_observe_z', _observe)

    def test_default_flags_error_when_ignore_set_indeterminate(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Default flags -> ``status: error`` naming the root, and no ``safe`` list."""
        self._repo_with_one_gitignored_artifact(tmp_path)
        self._fail_only_the_ignore_query(monkeypatch)

        result = cmd_detect_artifacts(Namespace(root=str(tmp_path), no_gitignore=False))

        assert result['status'] == 'error'
        assert result['error_code'] == git_workflow.ErrorCode.FETCH_FAILURE
        assert result['root'] == str(tmp_path)
        assert 'safe' not in result, f'an errored scan still offered artifacts for deletion: {result}'

    def test_no_gitignore_still_succeeds_on_the_same_tree(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """``--no-gitignore`` is the documented path for a tree with no readable ignore set.

        Matched positive control for the error above: the same tree and the same
        failed observation still produce a usable result when the caller opts out
        of the ignore oracle, so the error is the flag's consequence rather than
        the tree being unscannable.
        """
        self._repo_with_one_gitignored_artifact(tmp_path)
        self._fail_only_the_ignore_query(monkeypatch)

        result = cmd_detect_artifacts(Namespace(root=str(tmp_path), no_gitignore=True))

        assert result['status'] == 'success'
        assert any('.class' in f for f in result['safe']), (
            f'--no-gitignore should still offer the gitignored artifact: {result["safe"]}'
        )
