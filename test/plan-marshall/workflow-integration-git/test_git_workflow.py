"""Tests for git_workflow.py - consolidated git workflow script.

Tier 2 (direct import) tests with 3 subprocess tests for CLI plumbing.
"""

import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from toon_parser import parse_toon  # type: ignore[import-not-found]

from conftest import get_script_path, run_script

# Script under test (for subprocess CLI plumbing tests)
SCRIPT_PATH = get_script_path('plan-marshall', 'workflow-integration-git', 'git_workflow.py')

# Tier 2 direct imports — conftest sets up PYTHONPATH for cross-skill imports
from git_workflow import (  # type: ignore[import-not-found]  # noqa: E402
    _SKIP_DIRS,
    SAFE_ARTIFACT_PATTERNS,
    UNCERTAIN_ARTIFACT_PATTERNS,
    VALID_TYPES,
    analyze_diff,
    cmd_detect_artifacts,
    cmd_format_commit,
    get_tracked_files,
    scan_artifacts,
    wrap_text,
)


def run_git_script(args: list) -> tuple:
    """Run git_workflow.py with args and return (stdout, stderr, returncode)."""
    result = run_script(SCRIPT_PATH, *args)
    return result.stdout, result.stderr, result.returncode


class TestFormatCommit(unittest.TestCase):
    """Test git_workflow.py format-commit via direct import."""

    def test_basic_format(self):
        """Test basic commit message formatting."""
        result = cmd_format_commit(
            Namespace(commit_type='feat', scope=None, subject='add new feature', body=None, breaking=None, footer=None)
        )
        self.assertEqual(result['type'], 'feat')
        self.assertEqual(result['subject'], 'add new feature')
        self.assertIn('feat: add new feature', result['formatted_message'])
        self.assertEqual(result['status'], 'success')

    def test_format_with_scope(self):
        """Test commit message with scope."""
        result = cmd_format_commit(
            Namespace(commit_type='fix', scope='auth', subject='fix login bug', body=None, breaking=None, footer=None)
        )
        self.assertEqual(result['scope'], 'auth')
        self.assertIn('fix(auth):', result['formatted_message'])

    def test_format_with_body(self):
        """Test commit message with body."""
        result = cmd_format_commit(
            Namespace(
                commit_type='docs',
                scope=None,
                subject='update readme',
                body='Added installation instructions',
                breaking=None,
                footer=None,
            )
        )
        self.assertEqual(result['body'], 'Added installation instructions')

    def test_format_with_breaking_change(self):
        """Test commit message with breaking change."""
        result = cmd_format_commit(
            Namespace(
                commit_type='feat',
                scope=None,
                subject='change api',
                body=None,
                breaking='API signature changed',
                footer=None,
            )
        )
        self.assertIn('feat!:', result['formatted_message'])
        self.assertIn('BREAKING CHANGE:', result['formatted_message'])

    def test_format_with_footer(self):
        """Test commit message with footer."""
        result = cmd_format_commit(
            Namespace(
                commit_type='fix',
                scope=None,
                subject='fix crash',
                body=None,
                breaking=None,
                footer='Fixes #123',
            )
        )
        self.assertIn('Fixes #123', result['formatted_message'])

    def test_all_commit_types(self):
        """Test all valid commit types."""
        for commit_type in VALID_TYPES:
            result = cmd_format_commit(
                Namespace(
                    commit_type=commit_type, scope=None, subject='test subject', body=None, breaking=None, footer=None
                )
            )
            self.assertEqual(result['type'], commit_type, f'Failed for type: {commit_type}')

    def test_validation_warning_long_subject(self):
        """Test validation warning for long subject."""
        long_subject = 'a' * 55  # Exceeds 50 chars
        result = cmd_format_commit(
            Namespace(commit_type='fix', scope=None, subject=long_subject, body=None, breaking=None, footer=None)
        )
        self.assertTrue(result['validation']['valid'])
        self.assertTrue(any('50 chars' in w for w in result['validation']['warnings']))

    def test_validation_error_very_long_subject(self):
        """Test validation error for very long subject."""
        very_long_subject = 'a' * 75  # Exceeds 72 chars
        result = cmd_format_commit(
            Namespace(commit_type='fix', scope=None, subject=very_long_subject, body=None, breaking=None, footer=None)
        )
        self.assertFalse(result['validation']['valid'])

    def test_validation_warning_past_tense(self):
        """Test validation warning for past tense verb."""
        result = cmd_format_commit(
            Namespace(commit_type='fix', scope=None, subject='fixed the bug', body=None, breaking=None, footer=None)
        )
        self.assertTrue(any('imperative' in w.lower() for w in result['validation']['warnings']))

    def test_co_authored_by_not_appended_by_script(self):
        """Test that format-commit does NOT append Co-Authored-By."""
        result = cmd_format_commit(
            Namespace(commit_type='feat', scope=None, subject='add feature', body=None, breaking=None, footer=None)
        )
        self.assertNotIn('Co-Authored-By', result['formatted_message'])

    def test_ci_commit_type(self):
        """Test that ci is a valid commit type."""
        result = cmd_format_commit(
            Namespace(commit_type='ci', scope=None, subject='update workflow', body=None, breaking=None, footer=None)
        )
        self.assertEqual(result['type'], 'ci')
        self.assertIn('ci: update workflow', result['formatted_message'])

    def test_imperative_allowlist_no_false_warnings(self):
        """Test that imperative allowlist words don't trigger past-tense warnings."""
        allowlist_samples = [
            'embed',
            'spread',
            'thread',
            'overhead',
            'string',
            'bring',
            'caching',
            'hashing',
            'nothing',
        ]
        for word in allowlist_samples:
            result = cmd_format_commit(
                Namespace(
                    commit_type='fix', scope=None, subject=f'{word} the module', body=None, breaking=None, footer=None
                )
            )
            warnings = result['validation']['warnings']
            imperative_warnings = [w for w in warnings if 'imperative' in w.lower()]
            self.assertEqual(
                len(imperative_warnings), 0, f'False imperative warning for allowlisted word "{word}": {warnings}'
            )

    def test_breaking_and_footer_combined(self):
        """Test commit message with both --breaking and --footer simultaneously."""
        result = cmd_format_commit(
            Namespace(
                commit_type='feat',
                scope='api',
                subject='change auth endpoint',
                body=None,
                breaking='Old /auth endpoint removed',
                footer='Fixes #123',
            )
        )
        self.assertIn('feat(api)!:', result['formatted_message'])
        self.assertIn('BREAKING CHANGE:', result['formatted_message'])
        self.assertIn('Fixes #123', result['formatted_message'])

    def test_all_params_combined(self):
        """Test commit message with body + breaking + footer + scope."""
        result = cmd_format_commit(
            Namespace(
                commit_type='feat',
                scope='api',
                subject='change auth endpoint',
                body='Migrated to OAuth 2.0 flow',
                breaking='Old /auth endpoint removed',
                footer='Fixes #123',
            )
        )
        self.assertIn('feat(api)!:', result['formatted_message'])
        self.assertIn('BREAKING CHANGE:', result['formatted_message'])
        self.assertIn('Fixes #123', result['formatted_message'])
        self.assertIn('Migrated to OAuth 2.0 flow', result['formatted_message'])

    def test_long_scope_plus_subject_exceeds_72(self):
        """Header exceeding 72 chars should fail validation."""
        long_scope = 'very-long-module-name'
        long_subject = 'a' * 50  # type(scope): subject -> 5 + 23 + 4 + 50 = 82 chars
        result = cmd_format_commit(
            Namespace(
                commit_type='feat', scope=long_scope, subject=long_subject, body=None, breaking=None, footer=None
            )
        )
        self.assertFalse(result['validation']['valid'])
        self.assertTrue(any('Header' in w for w in result['validation']['warnings']))


class TestAnalyzeDiff(unittest.TestCase):
    """Test git_workflow.py analyze-diff via direct import."""

    def test_analyze_bug_fix(self):
        """Test analysis detects bug fix patterns from comment keywords."""
        diff_content = """diff --git a/src/main/java/Service.java b/src/main/java/Service.java
--- a/src/main/java/Service.java
+++ b/src/main/java/Service.java
-    return null;
+    // Fix null pointer when value is absent
+    if (value == null) throw new IllegalArgumentException();
+    return value;
"""
        suggestions = analyze_diff(diff_content)
        self.assertEqual(suggestions['type'], 'fix')

    def test_analyze_file_not_found(self):
        """Test error when diff file not found."""
        result = cmd_detect_artifacts(Namespace(root='/nonexistent/path', no_gitignore=False))
        self.assertEqual(result['status'], 'error')
        self.assertIn('not found', result['error'])

    def test_analyze_feat_detection(self):
        """Test analysis detects feat when additions far exceed deletions."""
        lines = ['diff --git a/src/main/java/New.java b/src/main/java/New.java']
        lines.append('@@ -1 +1,20 @@')
        lines.append('-old line')
        for i in range(20):
            lines.append(f'+    new line {i}')
        diff_content = '\n'.join(lines) + '\n'
        suggestions = analyze_diff(diff_content)
        self.assertEqual(suggestions['type'], 'feat')

    def test_analyze_refactor_detection(self):
        """Test analysis detects refactor when additions roughly equal deletions."""
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
        self.assertEqual(suggestions['type'], 'refactor')

    def test_analyze_ci_detection(self):
        """Test analysis detects ci type for CI config files."""
        diff_content = """diff --git a/.github/workflows/ci.yml b/.github/workflows/ci.yml
--- a/.github/workflows/ci.yml
+++ b/.github/workflows/ci.yml
-    runs-on: ubuntu-20.04
+    runs-on: ubuntu-22.04
"""
        suggestions = analyze_diff(diff_content)
        self.assertEqual(suggestions['type'], 'ci')

    def test_analyze_monorepo_scope(self):
        """Test scope detection for monorepo layouts (packages/<name>/...)."""
        diff_content = """diff --git a/packages/auth-service/src/login.ts b/packages/auth-service/src/login.ts
--- a/packages/auth-service/src/login.ts
+++ b/packages/auth-service/src/login.ts
+export function login() { return true; }
+export function logout() { return true; }
+export function refresh() { return true; }
"""
        suggestions = analyze_diff(diff_content)
        self.assertEqual(suggestions['scope'], 'auth-service')

    def test_analyze_python_scope_detection(self):
        """Test scope detection for Python file layouts (src/<package>/*.py)."""
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
        self.assertEqual(suggestions['scope'], 'mypackage')

    def test_analyze_generic_scope_detection(self):
        """Test scope detection falls back to top-level directory."""
        diff_content = """diff --git a/config/settings.ini b/config/settings.ini
--- a/config/settings.ini
+++ b/config/settings.ini
+[database]
+host = localhost
+port = 5432
"""
        suggestions = analyze_diff(diff_content)
        self.assertEqual(suggestions['scope'], 'config')

    def test_analyze_test_only_changes(self):
        """Test analysis detects 'test' type when only test files change."""
        diff_content = """diff --git a/test/java/ServiceTest.java b/test/java/ServiceTest.java
--- a/test/java/ServiceTest.java
+++ b/test/java/ServiceTest.java
+    @Test
+    public void testNewFeature() {
+        assertEquals(1, service.compute());
+    }
"""
        suggestions = analyze_diff(diff_content)
        self.assertEqual(suggestions['type'], 'test')

    def test_analyze_docs_only_changes(self):
        """Test analysis detects 'docs' type when only documentation files change."""
        diff_content = """diff --git a/README.md b/README.md
--- a/README.md
+++ b/README.md
+## Installation
+Run `npm install` to get started.
"""
        suggestions = analyze_diff(diff_content)
        self.assertEqual(suggestions['type'], 'docs')

    def test_analyze_empty_diff(self):
        """Test analysis of an empty diff returns default suggestions."""
        suggestions = analyze_diff('')
        self.assertEqual(suggestions['type'], 'chore')
        self.assertIsNone(suggestions['scope'])


class TestDetectArtifacts(unittest.TestCase):
    """Test git_workflow.py detect-artifacts via direct import."""

    def setUp(self):
        """Create a temporary directory with artifact files."""
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up temporary directory."""
        import shutil

        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _create_file(self, relpath: str) -> None:
        """Create a file within the temp directory."""
        full = Path(self.tmpdir) / relpath
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text('test')

    def test_detects_safe_artifacts(self):
        """Test detection of safe-to-delete artifacts."""
        self._create_file('src/main/java/Example.class')
        self._create_file('.DS_Store')
        self._create_file('module/__pycache__/foo.pyc')
        self._create_file('scratch.temp')

        result = scan_artifacts(Path(self.tmpdir), respect_gitignore=False)
        self.assertGreaterEqual(len(result['safe']), 4)
        safe_str = '\n'.join(result['safe'])
        self.assertIn('.class', safe_str)
        self.assertIn('.DS_Store', safe_str)

    def test_detects_uncertain_artifacts(self):
        """Test detection of uncertain artifacts in target/build dirs."""
        self._create_file('target/classes/App.class')
        self._create_file('target/output.jar')
        self._create_file('build/libs/app.jar')

        result = scan_artifacts(Path(self.tmpdir), respect_gitignore=False)
        self.assertTrue(len(result['uncertain']) >= 1 or len(result['safe']) >= 1)
        self.assertGreater(result['total'], 0)

    def test_detects_python_egg_artifacts(self):
        """Test detection of Python .egg-info and .eggs artifacts."""
        self._create_file('mypackage.egg-info/PKG-INFO')
        self._create_file('.eggs/some-egg.egg')

        result = scan_artifacts(Path(self.tmpdir), respect_gitignore=False)
        self.assertGreaterEqual(len(result['safe']), 2)
        safe_str = '\n'.join(result['safe'])
        self.assertIn('egg-info', safe_str)
        self.assertIn('.eggs', safe_str)

    def test_detects_typescript_buildinfo(self):
        """Test detection of TypeScript .tsbuildinfo files."""
        self._create_file('tsconfig.tsbuildinfo')
        self._create_file('packages/lib/tsconfig.tsbuildinfo')

        result = scan_artifacts(Path(self.tmpdir), respect_gitignore=False)
        safe_str = '\n'.join(result['safe'])
        self.assertIn('tsbuildinfo', safe_str)
        self.assertGreaterEqual(len(result['safe']), 2)

    def test_detects_plan_temp_as_safe(self):
        """Test that .plan/temp/ files are safe (not uncertain)."""
        self._create_file('.plan/temp/scratch.txt')
        self._create_file('.plan/temp/debug.log')

        result = scan_artifacts(Path(self.tmpdir), respect_gitignore=False)
        safe_str = '\n'.join(result['safe'])
        self.assertIn('.plan/temp', safe_str)
        uncertain_str = '\n'.join(result['uncertain'])
        self.assertNotIn('.plan/temp', uncertain_str)

    def test_detects_dist_next_as_uncertain(self):
        """Test that dist/ and .next/ directories are uncertain."""
        self._create_file('dist/bundle.js')
        self._create_file('.next/cache/data.json')

        result = scan_artifacts(Path(self.tmpdir), respect_gitignore=False)
        uncertain_str = '\n'.join(result['uncertain'])
        self.assertIn('dist/', uncertain_str)
        self.assertIn('.next/', uncertain_str)

    def test_detects_root_level_artifacts(self):
        """Test detection of artifacts at repo root (#23)."""
        self._create_file('Example.class')
        self._create_file('.DS_Store')
        self._create_file('scratch.temp')

        result = scan_artifacts(Path(self.tmpdir), respect_gitignore=False)
        self.assertGreaterEqual(len(result['safe']), 3)
        safe_str = '\n'.join(result['safe'])
        self.assertIn('Example.class', safe_str)
        self.assertIn('.DS_Store', safe_str)
        self.assertIn('scratch.temp', safe_str)

    def test_clean_directory_returns_empty(self):
        """Test scanning a directory with no artifacts."""
        self._create_file('src/main/java/App.java')
        self._create_file('README.md')

        result = scan_artifacts(Path(self.tmpdir), respect_gitignore=False)
        self.assertEqual(result['total'], 0)
        self.assertEqual(len(result['safe']), 0)
        self.assertEqual(len(result['uncertain']), 0)

    def test_nonexistent_root_fails(self):
        """Test error when root directory doesn't exist."""
        result = cmd_detect_artifacts(Namespace(root='/nonexistent/path', no_gitignore=False))
        self.assertEqual(result['status'], 'error')
        self.assertIn('not found', result['error'])

    def test_skips_git_directory(self):
        """Test that .git/ directory contents are excluded from results."""
        self._create_file('.git/objects/pack/pack-abc.class')
        self._create_file('.git/hooks/pre-commit.pyc')
        self._create_file('src/real.temp')

        result = scan_artifacts(Path(self.tmpdir), respect_gitignore=False)
        all_files = result['safe'] + result['uncertain']
        for f in all_files:
            self.assertFalse(f.startswith('.git/'), f'.git file should be excluded: {f}')
        self.assertTrue(any('real.temp' in f for f in result['safe']))

    def test_fixture_path_classified_as_uncertain(self):
        """Fixture files under test/**/fixtures/** should land in uncertain, not safe."""
        self._create_file('test/foo/fixtures/sample.dat')

        result = scan_artifacts(Path(self.tmpdir), respect_gitignore=False)
        uncertain_str = '\n'.join(result['uncertain'])
        safe_str = '\n'.join(result['safe'])
        self.assertIn('test/foo/fixtures/sample.dat', uncertain_str)
        self.assertNotIn('test/foo/fixtures/sample.dat', safe_str)

    def test_non_repo_graceful_degradation(self):
        """scan_artifacts must not raise when called outside a git repo."""
        # No git init — tmpdir is a plain directory. Create a benign file so
        # traversal has something to process.
        self._create_file('src/main.py')

        # Must complete without raising and return a valid dict shape.
        result = scan_artifacts(Path(self.tmpdir), respect_gitignore=False)
        self.assertIsInstance(result, dict)
        self.assertIn('safe', result)
        self.assertIn('uncertain', result)
        self.assertIn('total', result)

        # get_tracked_files should degrade to an empty set when no git repo exists.
        tracked = get_tracked_files(Path(self.tmpdir))
        self.assertEqual(tracked, set())


class TestTrackedFileFilter(unittest.TestCase):
    """Test that tracked files matching safe patterns are demoted to uncertain."""

    def setUp(self):
        """Create a temporary directory for git-backed scenarios."""
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up temporary directory."""
        import shutil

        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _create_file(self, relpath: str) -> None:
        """Create a file within the temp directory."""
        full = Path(self.tmpdir) / relpath
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text('test')

    def _git_init_with_identity(self) -> None:
        """Initialise a git repo with a throwaway committer identity."""
        import subprocess as sp

        sp.run(['git', 'init'], cwd=self.tmpdir, capture_output=True)
        sp.run(['git', 'config', 'user.email', 'test@test.com'], cwd=self.tmpdir, capture_output=True)
        sp.run(['git', 'config', 'user.name', 'Test'], cwd=self.tmpdir, capture_output=True)

    def test_tracked_safe_pattern_file_downgrades_to_uncertain(self):
        """A committed *.log file must appear in uncertain (never in safe)."""
        import subprocess as sp

        self._git_init_with_identity()
        self._create_file('debug.log')
        sp.run(['git', 'add', 'debug.log'], cwd=self.tmpdir, capture_output=True)
        sp.run(['git', 'commit', '-m', 'commit debug.log'], cwd=self.tmpdir, capture_output=True)

        result = scan_artifacts(Path(self.tmpdir), respect_gitignore=False)

        self.assertIn('debug.log', result['uncertain'])
        self.assertNotIn('debug.log', result['safe'])

    def test_untracked_safe_pattern_file_stays_safe(self):
        """An untracked *.log file (not gitignored) must remain in safe (regression guard)."""
        self._git_init_with_identity()
        # No .gitignore is created, so the file is not gitignored.
        # No `git add` — the file remains untracked.
        self._create_file('debug.log')

        result = scan_artifacts(Path(self.tmpdir), respect_gitignore=False)

        self.assertIn('debug.log', result['safe'])
        self.assertNotIn('debug.log', result['uncertain'])

    def test_tracked_file_scanned_from_subdir_still_downgrades(self):
        """Scanning a subdirectory of a repo must still demote tracked safe matches.

        Regression guard for the ``--full-name`` bug: ``git ls-files`` must
        return paths relative to the scanned ``root`` (the subdir) so the
        ``rel in tracked`` check matches. Without ``cwd=root`` + no
        ``--full-name``, tracked files in a subdir scan leak into ``safe``.
        """
        import subprocess as sp

        self._git_init_with_identity()
        self._create_file('sub/debug.log')
        sp.run(['git', 'add', 'sub/debug.log'], cwd=self.tmpdir, capture_output=True)
        sp.run(['git', 'commit', '-m', 'commit sub/debug.log'], cwd=self.tmpdir, capture_output=True)

        subdir = Path(self.tmpdir) / 'sub'
        result = scan_artifacts(subdir, respect_gitignore=False)

        self.assertIn('debug.log', result['uncertain'])
        self.assertNotIn('debug.log', result['safe'])


class TestDetectArtifactsGitignore(unittest.TestCase):
    """Test detect-artifacts with gitignore integration (subprocess-dependent)."""

    def setUp(self):
        """Create a temporary directory."""
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up temporary directory."""
        import shutil

        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _create_file(self, relpath: str) -> None:
        """Create a file within the temp directory."""
        full = Path(self.tmpdir) / relpath
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text('test')

    def test_respects_gitignore_by_default(self):
        """Test that gitignored files are excluded from results by default."""
        import subprocess as sp

        sp.run(['git', 'init'], cwd=self.tmpdir, capture_output=True)
        sp.run(['git', 'config', 'user.email', 'test@test.com'], cwd=self.tmpdir, capture_output=True)
        sp.run(['git', 'config', 'user.name', 'Test'], cwd=self.tmpdir, capture_output=True)

        (Path(self.tmpdir) / '.gitignore').write_text('*.class\n')
        sp.run(['git', 'add', '.gitignore'], cwd=self.tmpdir, capture_output=True)
        sp.run(['git', 'commit', '-m', 'init'], cwd=self.tmpdir, capture_output=True)

        self._create_file('src/Example.class')
        self._create_file('scratch.temp')

        stdout, _, code = run_git_script(['detect-artifacts', '--root', self.tmpdir])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        safe_files = result['safe']
        self.assertFalse(any('.class' in f for f in safe_files), f'.class should be excluded: {safe_files}')
        self.assertTrue(any('.temp' in f for f in safe_files), f'.temp should be present: {safe_files}')

    def test_no_gitignore_flag_includes_all(self):
        """Test that --no-gitignore includes gitignored files."""
        import subprocess as sp

        sp.run(['git', 'init'], cwd=self.tmpdir, capture_output=True)
        sp.run(['git', 'config', 'user.email', 'test@test.com'], cwd=self.tmpdir, capture_output=True)
        sp.run(['git', 'config', 'user.name', 'Test'], cwd=self.tmpdir, capture_output=True)

        (Path(self.tmpdir) / '.gitignore').write_text('*.class\n')
        sp.run(['git', 'add', '.gitignore'], cwd=self.tmpdir, capture_output=True)
        sp.run(['git', 'commit', '-m', 'init'], cwd=self.tmpdir, capture_output=True)

        self._create_file('src/Example.class')

        stdout, _, code = run_git_script(['detect-artifacts', '--root', self.tmpdir, '--no-gitignore'])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        safe_files = result['safe']
        self.assertTrue(
            any('.class' in f for f in safe_files), f'.class should be present with --no-gitignore: {safe_files}'
        )


class TestWrapText(unittest.TestCase):
    """Test wrap_text function directly."""

    def test_short_line_unchanged(self):
        """Lines within width are not wrapped."""
        self.assertEqual(wrap_text('short line', 72), 'short line')

    def test_long_line_wrapped(self):
        """Lines exceeding width are wrapped at word boundaries."""
        text = 'a ' * 40  # 80 chars
        result = wrap_text(text.strip(), 72)
        for line in result.split('\n'):
            self.assertLessEqual(len(line), 72)

    def test_preserves_bullet_indentation(self):
        """Wrapped lines preserve leading indentation."""
        text_indented = '  - ' + 'word ' * 20
        result_indented = wrap_text(text_indented, 72)
        for line in result_indented.split('\n'):
            self.assertTrue(line.startswith('  '), f'Lost indent: {line!r}')

    def test_deep_indent_not_wrapped(self):
        """Lines with >52 chars indent are kept as-is (effective_width < 20)."""
        text = ' ' * 55 + 'deeply indented content that should not be wrapped'
        result = wrap_text(text, 72)
        self.assertEqual(result, text)

    def test_very_long_word_not_broken(self):
        """A single word longer than width should not be split (#20)."""
        url = 'https://example.com/very/long/path/that/exceeds/seventy/two/characters/easily'
        result = wrap_text(url, 72)
        self.assertEqual(result, url)

    def test_multiline_preserves_paragraphs(self):
        """Multiple paragraphs separated by newlines are handled independently."""
        text = 'First paragraph.\nSecond paragraph.'
        result = wrap_text(text, 72)
        self.assertEqual(result, text)


class TestArtifactConfigLoading(unittest.TestCase):
    """Test that artifact patterns are loaded from artifact-patterns.json config."""

    def test_safe_patterns_loaded(self):
        """Test that safe artifact patterns are loaded from config."""
        self.assertIsInstance(SAFE_ARTIFACT_PATTERNS, list)
        self.assertTrue(len(SAFE_ARTIFACT_PATTERNS) > 0)
        patterns_str = ' '.join(SAFE_ARTIFACT_PATTERNS)
        self.assertIn('*.class', patterns_str)
        self.assertIn('*.pyc', patterns_str)
        self.assertIn('.DS_Store', patterns_str)

    def test_uncertain_patterns_loaded(self):
        """Test that uncertain artifact patterns are loaded from config."""
        self.assertIsInstance(UNCERTAIN_ARTIFACT_PATTERNS, list)
        self.assertTrue(len(UNCERTAIN_ARTIFACT_PATTERNS) > 0)
        patterns_str = ' '.join(UNCERTAIN_ARTIFACT_PATTERNS)
        self.assertIn('target/**', patterns_str)

    def test_skip_dirs_loaded(self):
        """Test that skip directories are loaded from config."""
        self.assertIsInstance(_SKIP_DIRS, set)
        self.assertIn('.git', _SKIP_DIRS)
        self.assertIn('node_modules', _SKIP_DIRS)
        self.assertIn('.venv', _SKIP_DIRS)

    def test_no_overlap_between_skip_dirs_and_uncertain(self):
        """Test that skip_dirs entries are not also in uncertain_patterns."""
        for skip_dir in _SKIP_DIRS:
            for pattern in UNCERTAIN_ARTIFACT_PATTERNS:
                self.assertFalse(
                    pattern.startswith(f'{skip_dir}/') or pattern.startswith(f'{skip_dir}/**'),
                    f'skip_dir "{skip_dir}" overlaps with uncertain pattern "{pattern}"',
                )


class TestToonContract(unittest.TestCase):
    """Verify output matches the contract documented in SKILL.md."""

    def test_format_commit_output_contract(self):
        """Verify format-commit output has all documented fields."""
        result = cmd_format_commit(
            Namespace(commit_type='feat', scope='auth', subject='add login', body=None, breaking=None, footer=None)
        )
        required_fields = {'type', 'scope', 'subject', 'formatted_message', 'validation', 'status'}
        missing = required_fields - set(result.keys())
        self.assertEqual(missing, set(), f'Missing contract fields: {missing}')
        self.assertIn('valid', result['validation'])
        self.assertIn('warnings', result['validation'])


# =============================================================================
# Subprocess (Tier 3) tests -- CLI plumbing only
# =============================================================================


class TestMain(unittest.TestCase):
    """Test git_workflow.py main entry point (CLI plumbing)."""

    def test_no_subcommand(self):
        """Test error when no subcommand provided."""
        _, stderr, code = run_git_script([])
        self.assertNotEqual(code, 0)

    def test_help(self):
        """Test help output."""
        stdout, _, code = run_git_script(['--help'])
        self.assertEqual(code, 0)
        self.assertIn('format-commit', stdout)
        self.assertIn('analyze-diff', stdout)

    def test_missing_required_args(self):
        """Test error when required args missing."""
        _, stderr, code = run_git_script(['format-commit'])
        self.assertNotEqual(code, 0)
        self.assertIn('--type', stderr)


if __name__ == '__main__':
    unittest.main()
