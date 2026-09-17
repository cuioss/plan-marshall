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


class TestFormatCommit:
    """Test git_workflow.py format-commit via direct import."""

    def test_basic_format(self):
        """Basic commit message formatting."""
        result = cmd_format_commit(_format_commit_args(commit_type='feat', subject='add new feature'))

        assert result['type'] == 'feat'
        assert result['subject'] == 'add new feature'
        assert 'feat: add new feature' in result['formatted_message']
        assert result['status'] == 'success'

    def test_format_with_scope(self):
        """Commit message with scope."""
        result = cmd_format_commit(_format_commit_args(commit_type='fix', scope='auth', subject='fix login bug'))

        assert result['scope'] == 'auth'
        assert 'fix(auth):' in result['formatted_message']

    def test_format_with_body(self):
        """Commit message with body."""
        result = cmd_format_commit(
            _format_commit_args(commit_type='docs', subject='update readme', body='Added installation instructions')
        )

        assert result['body'] == 'Added installation instructions'

    def test_format_with_breaking_change(self):
        """Commit message with breaking change."""
        result = cmd_format_commit(
            _format_commit_args(commit_type='feat', subject='change api', breaking='API signature changed')
        )

        assert 'feat!:' in result['formatted_message']
        assert 'BREAKING CHANGE:' in result['formatted_message']

    def test_format_with_footer(self):
        """Commit message with footer."""
        result = cmd_format_commit(_format_commit_args(commit_type='fix', subject='fix crash', footer='Fixes #123'))

        assert 'Fixes #123' in result['formatted_message']

    @pytest.mark.parametrize('commit_type', sorted(VALID_TYPES))
    def test_valid_commit_type_accepted(self, commit_type):
        """Every valid commit type is accepted and echoed back."""
        result = cmd_format_commit(_format_commit_args(commit_type=commit_type, subject='test subject'))

        assert result['type'] == commit_type

    def test_validation_warning_long_subject(self):
        """Subject over 50 chars warns but stays valid."""
        long_subject = 'a' * 55  # Exceeds 50 chars

        result = cmd_format_commit(_format_commit_args(commit_type='fix', subject=long_subject))

        assert result['validation']['valid']
        assert any('50 chars' in w for w in result['validation']['warnings'])

    def test_validation_error_very_long_subject(self):
        """Subject over 72 chars fails validation."""
        very_long_subject = 'a' * 75  # Exceeds 72 chars

        result = cmd_format_commit(_format_commit_args(commit_type='fix', subject=very_long_subject))

        assert not result['validation']['valid']

    def test_validation_warning_past_tense(self):
        """Past-tense verb produces an imperative-mood warning."""
        result = cmd_format_commit(_format_commit_args(commit_type='fix', subject='fixed the bug'))

        assert any('imperative' in w.lower() for w in result['validation']['warnings'])

    def test_co_authored_by_not_appended_by_script(self):
        """format-commit does NOT append Co-Authored-By."""
        result = cmd_format_commit(_format_commit_args(commit_type='feat', subject='add feature'))

        assert 'Co-Authored-By' not in result['formatted_message']

    def test_ci_commit_type(self):
        """'ci' is a valid commit type."""
        result = cmd_format_commit(_format_commit_args(commit_type='ci', subject='update workflow'))

        assert result['type'] == 'ci'
        assert 'ci: update workflow' in result['formatted_message']

    @pytest.mark.parametrize(
        'word',
        ['embed', 'spread', 'thread', 'overhead', 'string', 'bring', 'caching', 'hashing', 'nothing'],
    )
    def test_imperative_allowlist_word_no_false_warning(self, word):
        """Allowlisted words must not trigger a past-tense imperative warning."""
        result = cmd_format_commit(_format_commit_args(commit_type='fix', subject=f'{word} the module'))

        imperative_warnings = [w for w in result['validation']['warnings'] if 'imperative' in w.lower()]
        assert imperative_warnings == []

    def test_breaking_and_footer_combined(self):
        """Commit message with both --breaking and --footer simultaneously."""
        result = cmd_format_commit(
            _format_commit_args(
                commit_type='feat',
                scope='api',
                subject='change auth endpoint',
                breaking='Old /auth endpoint removed',
                footer='Fixes #123',
            )
        )

        assert 'feat(api)!:' in result['formatted_message']
        assert 'BREAKING CHANGE:' in result['formatted_message']
        assert 'Fixes #123' in result['formatted_message']

    def test_all_params_combined(self):
        """Commit message with body + breaking + footer + scope."""
        result = cmd_format_commit(
            _format_commit_args(
                commit_type='feat',
                scope='api',
                subject='change auth endpoint',
                body='Migrated to OAuth 2.0 flow',
                breaking='Old /auth endpoint removed',
                footer='Fixes #123',
            )
        )

        assert 'feat(api)!:' in result['formatted_message']
        assert 'BREAKING CHANGE:' in result['formatted_message']
        assert 'Fixes #123' in result['formatted_message']
        assert 'Migrated to OAuth 2.0 flow' in result['formatted_message']

    def test_long_scope_plus_subject_exceeds_72(self):
        """Header exceeding 72 chars fails validation."""
        long_scope = 'very-long-module-name'
        long_subject = 'a' * 50  # type(scope): subject -> 5 + 23 + 4 + 50 = 82 chars

        result = cmd_format_commit(_format_commit_args(commit_type='feat', scope=long_scope, subject=long_subject))

        assert not result['validation']['valid']
        assert any('Header' in w for w in result['validation']['warnings'])


class TestWrapText:
    """Test wrap_text function directly."""

    def test_short_line_unchanged(self):
        """Lines within width are not wrapped."""
        assert wrap_text('short line', 72) == 'short line'

    def test_long_line_wrapped(self):
        """Lines exceeding width are wrapped at word boundaries."""
        text = 'a ' * 40  # 80 chars

        result = wrap_text(text.strip(), 72)

        assert all(len(line) <= 72 for line in result.split('\n'))

    def test_preserves_bullet_indentation(self):
        """Wrapped lines preserve leading indentation."""
        text_indented = '  - ' + 'word ' * 20

        result_indented = wrap_text(text_indented, 72)

        assert all(line.startswith('  ') for line in result_indented.split('\n'))

    def test_deep_indent_not_wrapped(self):
        """Lines with >52 chars indent are kept as-is (effective_width < 20)."""
        text = ' ' * 55 + 'deeply indented content that should not be wrapped'

        assert wrap_text(text, 72) == text

    def test_very_long_word_not_broken(self):
        """A single word longer than width is not split."""
        url = 'https://example.com/very/long/path/that/exceeds/seventy/two/characters/easily'

        assert wrap_text(url, 72) == url

    def test_multiline_preserves_paragraphs(self):
        """Multiple paragraphs separated by newlines are handled independently."""
        text = 'First paragraph.\nSecond paragraph.'

        assert wrap_text(text, 72) == text
