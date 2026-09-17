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



class TestScanRootPlanStateExclusion:
    """The scan ROOT's own plan state is excluded independent of every ignore mechanism.

    From phase-5 onward a plan's cwd is pinned to its own worktree and
    ``cmd_detect_artifacts`` defaults ``--root`` to ``Path.cwd()``, so the run's
    live audit trail sits directly under the scan root. That is the one case
    ``_is_nested_git_boundary`` cannot reach — it prunes only checkouts nested
    *below* the root.

    Each case below defeats a different ignore mechanism. The exclusion must
    hold in all three, which is exactly why the guarantee cannot be attributed
    to ``.gitignore``.
    """

    def test_plan_state_excluded_with_gitignore_disabled(self, tmp_path: Path):
        """``respect_gitignore=False`` leaves the reported ignore set empty."""
        _plan_worktree_scan_root(tmp_path)

        result = scan_artifacts(tmp_path, respect_gitignore=False)

        _assert_plan_state_excluded_control_safe(result)

    def test_plan_state_excluded_when_gitignore_lacks_plan_rule(self, tmp_path: Path):
        """A project whose ``.gitignore`` carries no ``.plan`` rule at all."""
        _plan_worktree_scan_root(tmp_path)
        (tmp_path / '.gitignore').write_text('*.class\n')

        result = scan_artifacts(tmp_path, respect_gitignore=True)

        _assert_plan_state_excluded_control_safe(result)

    def test_plan_state_excluded_when_ignore_set_empty_but_successful(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """An empty-but-successful ignore set — distinct from the ``None`` degradation.

        ``set()`` asserts "nothing here is ignored" and keeps
        ``gitignore_resolved`` true, so the degradation path that routes
        everything to ``uncertain`` never fires and a pre-fix ``work.log``
        reaches ``safe``.
        """
        _plan_worktree_scan_root(tmp_path)
        monkeypatch.setattr(git_workflow, 'get_gitignored_files', lambda root: set())

        result = scan_artifacts(tmp_path, respect_gitignore=True)

        _assert_plan_state_excluded_control_safe(result)



class TestCollapsedIgnoredDirPrefixBranch:
    """The prefix arm of ``_is_ignored`` reached WITHOUT nested-boundary pruning.

    Every other collapsed-ignored-directory test sites the directory at a nested
    git worktree, so the boundary pruning drops the subtree before ``_is_ignored``
    is consulted — those tests stay green when the prefix test is reverted to
    exact-string membership, which is the gap this class closes. Here the ignored
    directory is a plain, non-repo directory, so the prefix arm is the only thing
    that can exclude anything beneath it.
    """

    def test_paths_under_collapsed_ignored_dir_are_excluded(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """A collapsed ``ignored-tree/`` entry excludes its descendants, not just itself."""
        _create_file(tmp_path, 'ignored-tree/nested/output.log')
        _create_file(tmp_path, 'scratch.temp')
        assert not (tmp_path / 'ignored-tree' / '.git').exists(), (
            'the ignored directory must NOT be a git boundary, or the pruning '
            'would exclude it before _is_ignored is consulted'
        )
        monkeypatch.setattr(git_workflow, 'get_gitignored_files', lambda root: {'ignored-tree/'})
        monkeypatch.setattr(git_workflow, 'get_tracked_files', lambda root: set())

        result = scan_artifacts(tmp_path, respect_gitignore=True)
        offered = result['safe'] + result['uncertain']

        assert not any('ignored-tree' in f for f in offered), (
            f'a path beneath a collapsed ignored-directory entry was offered: {offered}'
        )
        assert 'scratch.temp' in result['safe'], (
            f'control artifact missing from safe — the exclusion would be vacuous: {result["safe"]}'
        )
