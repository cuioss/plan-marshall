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


class TestAnalyzeDiff:
    """Test git_workflow.py analyze-diff via direct import."""

    def test_analyze_bug_fix(self):
        """Analysis detects bug-fix patterns from comment keywords."""
        diff_content = """diff --git a/src/main/java/Service.java b/src/main/java/Service.java
--- a/src/main/java/Service.java
+++ b/src/main/java/Service.java
-    return null;
+    // Fix null pointer when value is absent
+    if (value == null) throw new IllegalArgumentException();
+    return value;
"""
        suggestions = analyze_diff(diff_content)

        assert suggestions['type'] == 'fix'

    def test_analyze_file_not_found(self):
        """Error when diff file not found."""
        result = cmd_detect_artifacts(Namespace(root='/nonexistent/path', no_gitignore=False))

        assert result['status'] == 'error'
        assert 'not found' in result['error']

    def test_analyze_feat_detection(self):
        """Analysis detects feat when additions far exceed deletions."""
        lines = ['diff --git a/src/main/java/New.java b/src/main/java/New.java']
        lines.append('@@ -1 +1,20 @@')
        lines.append('-old line')
        for i in range(20):
            lines.append(f'+    new line {i}')
        diff_content = '\n'.join(lines) + '\n'

        suggestions = analyze_diff(diff_content)

        assert suggestions['type'] == 'feat'

    def test_analyze_refactor_detection(self):
        """Analysis detects refactor when additions roughly equal deletions."""
        diff_content = """diff --git a/src/main/java/Util.java b/src/main/java/Util.java
--- a/src/main/java/Util.java
+++ b/src/main/java/Util.java
-    public void oldMethodName() {
+    public void newMethodName() {
-        int x = getValue();
+        int x = computeValue();
-        String s = format(x);
+        String s = formatOutput(x);
"""
        suggestions = analyze_diff(diff_content)

        assert suggestions['type'] == 'refactor'

    def test_analyze_ci_detection(self):
        """Analysis detects ci type for CI config files."""
        diff_content = """diff --git a/.github/workflows/ci.yml b/.github/workflows/ci.yml
--- a/.github/workflows/ci.yml
+++ b/.github/workflows/ci.yml
-    runs-on: ubuntu-20.04
+    runs-on: ubuntu-22.04
"""
        suggestions = analyze_diff(diff_content)

        assert suggestions['type'] == 'ci'

    def test_analyze_monorepo_scope(self):
        """Scope detection for monorepo layouts (packages/<name>/...)."""
        diff_content = """diff --git a/packages/auth-service/src/login.ts b/packages/auth-service/src/login.ts
--- a/packages/auth-service/src/login.ts
+++ b/packages/auth-service/src/login.ts
+export function login() { return true; }
+export function logout() { return true; }
+export function refresh() { return true; }
"""
        suggestions = analyze_diff(diff_content)

        assert suggestions['scope'] == 'auth-service'

    def test_analyze_python_scope_detection(self):
        """Scope detection for Python file layouts (src/<package>/*.py)."""
        diff_content = """diff --git a/src/mypackage/utils.py b/src/mypackage/utils.py
--- a/src/mypackage/utils.py
+++ b/src/mypackage/utils.py
+def helper():
+    return True
+def another():
+    return False
+def third():
+    return None
"""
        suggestions = analyze_diff(diff_content)

        assert suggestions['scope'] == 'mypackage'

    def test_analyze_generic_scope_detection(self):
        """Scope detection falls back to top-level directory."""
        diff_content = """diff --git a/config/settings.ini b/config/settings.ini
--- a/config/settings.ini
+++ b/config/settings.ini
+[database]
+host = localhost
+port = 5432
"""
        suggestions = analyze_diff(diff_content)

        assert suggestions['scope'] == 'config'

    def test_analyze_test_only_changes(self):
        """Analysis detects 'test' type when only test files change."""
        diff_content = """diff --git a/test/java/ServiceTest.java b/test/java/ServiceTest.java
--- a/test/java/ServiceTest.java
+++ b/test/java/ServiceTest.java
+    @Test
+    public void testNewFeature() {
+        assertEquals(1, service.compute());
+    }
"""
        suggestions = analyze_diff(diff_content)

        assert suggestions['type'] == 'test'

    def test_analyze_docs_only_changes(self):
        """Analysis detects 'docs' type when only documentation files change."""
        diff_content = """diff --git a/README.md b/README.md
--- a/README.md
+++ b/README.md
+## Installation
+Run `npm install` to get started.
"""
        suggestions = analyze_diff(diff_content)

        assert suggestions['type'] == 'docs'

    def test_analyze_empty_diff(self):
        """Analysis of an empty diff returns default suggestions."""
        suggestions = analyze_diff('')

        assert suggestions['type'] == 'chore'
        assert suggestions['scope'] is None


class TestAnalyzeDiffCli:
    """CLI-level tests for analyze-diff --project-dir / --cached.

    These exercise ``cmd_analyze_diff`` end-to-end: a real git worktree is
    initialised, changes are introduced (unstaged or staged), and the script
    is invoked as a subprocess so the CLI plumbing (argparse flags, in-process
    ``git diff`` capture, TOON output) is covered.
    """

    @staticmethod
    def _git(repo: Path, *args: str) -> None:
        """Run a git command in the fixture worktree."""
        subprocess.run(['git', '-C', str(repo), *args], capture_output=True, check=True)

    def _seed_worktree(self, repo: Path) -> None:
        """Initialise the fixture worktree with a single committed file."""
        self._git(repo, 'init')
        self._git(repo, 'config', 'user.email', 'test@test.com')
        self._git(repo, 'config', 'user.name', 'Test')
        seed = repo / 'src' / 'mypackage' / 'utils.py'
        seed.parent.mkdir(parents=True, exist_ok=True)
        seed.write_text('def existing():\n    return 1\n')
        self._git(repo, 'add', 'src/mypackage/utils.py')
        self._git(repo, 'commit', '-m', 'initial')

    def test_unstaged_diff_captured_and_analyzed(self, tmp_path: Path):
        """--project-dir captures the unstaged diff and emits suggestions."""
        self._seed_worktree(tmp_path)
        # Introduce an unstaged feat-style change (many additions, few deletions).
        target = tmp_path / 'src' / 'mypackage' / 'utils.py'
        new_lines = ['def existing():', '    return 1', '']
        for i in range(20):
            new_lines.append(f'def helper_{i}():')
            new_lines.append(f'    return {i}')
            new_lines.append('')
        target.write_text('\n'.join(new_lines))

        stdout, stderr, code = run_git_script(['analyze-diff', '--project-dir', str(tmp_path)])

        assert code == 0, f'stderr={stderr}'
        result = parse_toon(stdout)
        assert result['status'] == 'success'
        assert result['mode'] == 'analysis'
        suggestions = result['suggestions']
        assert 'type' in suggestions
        # Scope is detected from the Python file layout (src/<package>/...).
        assert suggestions['scope'] == 'mypackage'

    def test_cached_flag_captures_staged_changes(self, tmp_path: Path):
        """--cached selects the staged diff so unstaged-only changes are ignored."""
        self._seed_worktree(tmp_path)
        # Stage a docs change.
        readme = tmp_path / 'README.md'
        readme.write_text('## Installation\nRun the thing.\n')
        self._git(tmp_path, 'add', 'README.md')
        # Add an unstaged-only change in another file that --cached must NOT see.
        unstaged = tmp_path / 'src' / 'mypackage' / 'utils.py'
        unstaged.write_text('def existing():\n    return 999\n')

        stdout, stderr, code = run_git_script(['analyze-diff', '--project-dir', str(tmp_path), '--cached'])

        assert code == 0, f'stderr={stderr}'
        result = parse_toon(stdout)
        assert result['status'] == 'success'
        # Staged content was a docs-only change, so analyzer classifies it as docs.
        assert result['suggestions']['type'] == 'docs'

    def test_invalid_worktree_path_returns_error(self, tmp_path: Path):
        """A non-existent worktree path produces a structured error result.

        Per the script's TOON output contract (see ``script-shared`` helpers),
        expected errors are surfaced via ``status: error`` in the TOON payload
        and the process still exits 0 — non-zero exits are reserved for
        uncaught exceptions.
        """
        bogus = str(tmp_path / 'does-not-exist')

        stdout, stderr, code = run_git_script(['analyze-diff', '--project-dir', bogus])

        assert code == 0, f'stderr={stderr}'
        result = parse_toon(stdout)
        assert result['status'] == 'error'
        # Error message should reference the missing worktree path.
        assert 'not found' in result.get('error', '').lower()
