# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for git-workflow.py - consolidated git workflow script.

Tier 2 (direct import) tests with subprocess tests for CLI plumbing.
"""

from __future__ import annotations

import importlib.util
import subprocess
from argparse import Namespace
from pathlib import Path

import pytest
from toon_parser import parse_toon

from conftest import get_script_path, run_script

# Script under test (for subprocess CLI plumbing tests)
SCRIPT_PATH = get_script_path('plan-marshall', 'workflow-integration-git', 'git-workflow.py')

# The entrypoint filename is kebab-case (git-workflow.py), which is not a
# valid Python module identifier — load it via importlib instead of `import`.
_spec = importlib.util.spec_from_file_location('git_workflow', SCRIPT_PATH)
assert _spec is not None and _spec.loader is not None
git_workflow = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(git_workflow)
_SKIP_DIRS = git_workflow._SKIP_DIRS
SAFE_ARTIFACT_PATTERNS = git_workflow.SAFE_ARTIFACT_PATTERNS
UNCERTAIN_ARTIFACT_PATTERNS = git_workflow.UNCERTAIN_ARTIFACT_PATTERNS
VALID_TYPES = git_workflow.VALID_TYPES
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

        result = cmd_format_commit(
            _format_commit_args(commit_type='feat', scope=long_scope, subject=long_subject)
        )

        assert not result['validation']['valid']
        assert any('Header' in w for w in result['validation']['warnings'])


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


class TestBranchSyncState:
    """branch-sync-state — push-parity verdicts driving the barrier re-fire rule.

    Repo-fixture tests reproducing the nifi #445 shape: a work repo with a
    ``file://`` bare origin. Metadata resolution (worktree path + branch) is
    monkeypatched onto the real fixture repo; the git comparison itself runs
    against real refs.
    """

    BRANCH = 'feature/sync-plan'

    def _seed_repo_with_origin(self, tmp_path: Path) -> Path:
        """Create a work repo on BRANCH with a ``file://`` bare origin."""
        origin = tmp_path / 'origin.git'
        origin.mkdir()
        subprocess.run(['git', 'init', '--bare'], cwd=origin, capture_output=True)
        work = tmp_path / 'work'
        work.mkdir()
        _git_init_with_identity(work)
        # Worktree fixtures carry a .gitignore covering .plan/ per the
        # established fixture convention.
        (work / '.gitignore').write_text('.plan/\n')
        (work / 'file.txt').write_text('one')
        subprocess.run(['git', 'add', '.'], cwd=work, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'init'], cwd=work, capture_output=True)
        subprocess.run(['git', 'checkout', '-b', self.BRANCH], cwd=work, capture_output=True)
        subprocess.run(
            ['git', 'remote', 'add', 'origin', f'file://{origin}'], cwd=work, capture_output=True
        )
        return work

    def _push(self, work: Path) -> None:
        subprocess.run(['git', 'push', '-u', 'origin', self.BRANCH], cwd=work, capture_output=True)

    def _commit_past_origin(self, work: Path) -> None:
        (work / 'file.txt').write_text('two')
        subprocess.run(['git', 'commit', '-am', 'local-only'], cwd=work, capture_output=True)

    def _rev_parse(self, work: Path, ref: str) -> str:
        result = subprocess.run(
            ['git', 'rev-parse', ref], cwd=work, capture_output=True, text=True
        )
        return result.stdout.strip()

    def _state(self, monkeypatch, work: Path) -> dict:
        monkeypatch.setattr(
            git_workflow, '_resolve_worktree_path_for_plan', lambda plan_id: (work, None)
        )
        monkeypatch.setattr(
            git_workflow, '_read_metadata_field', lambda plan_id, field: self.BRANCH
        )
        return dict(git_workflow.cmd_branch_sync_state(Namespace(plan_id='sync-plan')))

    def test_synced_after_push(self, tmp_path: Path, monkeypatch):
        """Local HEAD equal to origin/{branch} reports state: synced."""
        work = self._seed_repo_with_origin(tmp_path)
        self._push(work)

        result = self._state(monkeypatch, work)

        assert result['status'] == 'success'
        assert result['state'] == 'synced'
        assert result['branch'] == self.BRANCH
        assert result['head_sha'] == self._rev_parse(work, 'HEAD')
        assert result['remote_sha'] == result['head_sha']

    def test_ahead_after_local_commit(self, tmp_path: Path, monkeypatch):
        """A local commit past origin reports state: ahead (re-fire verdict)."""
        work = self._seed_repo_with_origin(tmp_path)
        self._push(work)
        self._commit_past_origin(work)

        result = self._state(monkeypatch, work)

        assert result['status'] == 'success'
        assert result['state'] == 'ahead'
        assert result['head_sha'] == self._rev_parse(work, 'HEAD')
        assert result['remote_sha'] == self._rev_parse(work, f'origin/{self.BRANCH}')
        assert result['head_sha'] != result['remote_sha']

    def test_no_remote_when_never_pushed(self, tmp_path: Path, monkeypatch):
        """A branch with no origin tracking ref reports state: no_remote, no remote_sha."""
        work = self._seed_repo_with_origin(tmp_path)

        result = self._state(monkeypatch, work)

        assert result['status'] == 'success'
        assert result['state'] == 'no_remote'
        assert result['head_sha'] == self._rev_parse(work, 'HEAD')
        assert 'remote_sha' not in result

    def test_missing_branch_metadata_is_error(self, tmp_path: Path, monkeypatch):
        """Absent worktree_branch metadata surfaces worktree_not_materialized."""
        work = self._seed_repo_with_origin(tmp_path)
        monkeypatch.setattr(
            git_workflow, '_resolve_worktree_path_for_plan', lambda plan_id: (work, None)
        )
        monkeypatch.setattr(git_workflow, '_read_metadata_field', lambda plan_id, field: '')

        result = git_workflow.cmd_branch_sync_state(Namespace(plan_id='sync-plan'))

        assert result['status'] == 'error'
        assert result['error'] == 'worktree_not_materialized'

    def test_verdict_token_drives_refire_skip_mapping(self, tmp_path: Path, monkeypatch):
        """The state token drives the documented barrier mapping.

        Per phase-6-finalize/SKILL.md item 1 (push-specific branch):
        ahead -> RE-FIRE, no_remote -> RE-FIRE, synced -> SKIP.
        """
        documented_mapping = {'ahead': 'RE-FIRE', 'no_remote': 'RE-FIRE', 'synced': 'SKIP'}

        # no_remote: never pushed
        work = self._seed_repo_with_origin(tmp_path)
        no_remote_state = self._state(monkeypatch, work)['state']
        # synced: pushed, no local commits
        self._push(work)
        synced_state = self._state(monkeypatch, work)['state']
        # ahead: committed locally past origin
        self._commit_past_origin(work)
        ahead_state = self._state(monkeypatch, work)['state']

        verdicts = {
            state: ('SKIP' if state == 'synced' else 'RE-FIRE')
            for state in (no_remote_state, synced_state, ahead_state)
        }
        assert verdicts == documented_mapping


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

    def test_detects_plan_temp_as_safe(self, tmp_path: Path):
        """.plan/temp/ files are safe (not uncertain)."""
        _create_file(tmp_path, '.plan/temp/scratch.txt')
        _create_file(tmp_path, '.plan/temp/debug.log')

        result = scan_artifacts(tmp_path, respect_gitignore=False)

        assert '.plan/temp' in '\n'.join(result['safe'])
        assert '.plan/temp' not in '\n'.join(result['uncertain'])

    def test_detects_dist_next_as_uncertain(self, tmp_path: Path):
        """dist/ and .next/ directories are uncertain."""
        _create_file(tmp_path, 'dist/bundle.js')
        _create_file(tmp_path, '.next/cache/data.json')

        result = scan_artifacts(tmp_path, respect_gitignore=False)

        uncertain_str = '\n'.join(result['uncertain'])
        assert 'dist/' in uncertain_str
        assert '.next/' in uncertain_str

    def test_detects_root_level_artifacts(self, tmp_path: Path):
        """Detection of artifacts at repo root (#23)."""
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
        """A single word longer than width is not split (#20)."""
        url = 'https://example.com/very/long/path/that/exceeds/seventy/two/characters/easily'

        assert wrap_text(url, 72) == url

    def test_multiline_preserves_paragraphs(self):
        """Multiple paragraphs separated by newlines are handled independently."""
        text = 'First paragraph.\nSecond paragraph.'

        assert wrap_text(text, 72) == text


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
                assert not (
                    pattern.startswith(f'{skip_dir}/') or pattern.startswith(f'{skip_dir}/**')
                ), f'skip_dir "{skip_dir}" overlaps with uncertain pattern "{pattern}"'


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
    """worktree-remove — the script-enforced plan-dir move-back precondition.

    Proves (a) removal REFUSES with ``plan_dir_not_moved_back`` while the
    worktree still holds the sole plan-state copy and main holds no plan dir;
    (b) the refusal persists under ``--force`` (the flag keeps its dirty-tree
    meaning only); (c) removal succeeds after the plan dir is moved to main's
    ``.plan/local/plans/{plan_id}/``; (d) the existing noop branch (target
    absent) is unchanged. Fixture ``.gitignore`` covers ``.plan/`` so
    worktree-resident plan state never blocks the non-force removal.
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

    def _patch(self, monkeypatch, main: Path, worktree: Path) -> None:
        monkeypatch.setattr(
            git_workflow, '_resolve_worktree_path_for_plan', lambda plan_id: (worktree, None)
        )
        monkeypatch.setattr(git_workflow, '_find_plan_root_from_cwd', lambda: main)
        monkeypatch.setattr(git_workflow, '_read_metadata_field', lambda plan_id, field: '')

    def _remove(self, force: bool = False) -> dict:
        return dict(
            git_workflow.cmd_worktree_remove(Namespace(plan_id=self.PLAN_ID, force=force))
        )

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
        assert worktree.exists(), (
            'The refusal must leave the worktree (the sole plan-state copy) intact.'
        )

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
        # Simulate integrate_into_main: land the plan dir on main.
        main_plan_dir = main / '.plan' / 'local' / 'plans' / self.PLAN_ID
        main_plan_dir.mkdir(parents=True)
        (main_plan_dir / 'status.json').write_text('{}')

        result = self._remove()

        assert result['status'] == 'success', f'Expected removal to proceed, got {result!r}.'
        assert result['action'] == 'removed'
        assert not worktree.exists()

    def test_noop_branch_unchanged_when_target_absent(self, tmp_path: Path, monkeypatch):
        """(d) absent worktree still short-circuits to the noop success."""
        main, _worktree = self._seed_main_and_worktree(tmp_path)
        absent = tmp_path / 'absent-wt'
        monkeypatch.setattr(
            git_workflow, '_resolve_worktree_path_for_plan', lambda plan_id: (absent, None)
        )
        monkeypatch.setattr(git_workflow, '_find_plan_root_from_cwd', lambda: main)
        monkeypatch.setattr(git_workflow, '_read_metadata_field', lambda plan_id, field: '')

        result = self._remove()

        assert result['status'] == 'success'
        assert result['action'] == 'noop', (
            'The target-absent noop branch must fire BEFORE the move-back '
            f'precondition, got {result!r}.'
        )


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
