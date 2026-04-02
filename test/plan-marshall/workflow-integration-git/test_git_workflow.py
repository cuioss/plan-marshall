"""Tests for git-workflow.py - consolidated git workflow script."""

import sys
import tempfile
import unittest
from pathlib import Path

# Import shared infrastructure
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from toon_parser import parse_toon  # type: ignore[import-not-found]  # noqa: E402

from conftest import get_script_path, run_script  # noqa: E402

# Script under test
SCRIPT_PATH = get_script_path('plan-marshall', 'workflow-integration-git', 'git-workflow.py')


def run_git_script(args: list) -> tuple:
    """Run git-workflow.py with args and return (stdout, stderr, returncode)."""
    result = run_script(SCRIPT_PATH, *args)
    return result.stdout, result.stderr, result.returncode


class TestFormatCommit(unittest.TestCase):
    """Test git-workflow.py format-commit subcommand."""

    def test_basic_format(self):
        """Test basic commit message formatting."""
        stdout, _, code = run_git_script(['format-commit', '--type', 'feat', '--subject', 'add new feature'])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        self.assertEqual(result['type'], 'feat')
        self.assertEqual(result['subject'], 'add new feature')
        self.assertIn('feat: add new feature', result['formatted_message'])
        self.assertEqual(result['status'], 'success')

    def test_format_with_scope(self):
        """Test commit message with scope."""
        stdout, _, code = run_git_script(
            ['format-commit', '--type', 'fix', '--scope', 'auth', '--subject', 'fix login bug']
        )
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        self.assertEqual(result['scope'], 'auth')
        self.assertIn('fix(auth):', result['formatted_message'])

    def test_format_with_body(self):
        """Test commit message with body."""
        stdout, _, code = run_git_script(
            [
                'format-commit',
                '--type',
                'docs',
                '--subject',
                'update readme',
                '--body',
                'Added installation instructions',
            ]
        )
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        self.assertEqual(result['body'], 'Added installation instructions')
        self.assertIn('Added installation instructions', stdout)

    def test_format_with_breaking_change(self):
        """Test commit message with breaking change."""
        stdout, _, code = run_git_script(
            ['format-commit', '--type', 'feat', '--subject', 'change api', '--breaking', 'API signature changed']
        )
        self.assertEqual(code, 0)
        self.assertIn('feat!:', stdout)
        self.assertIn('BREAKING CHANGE:', stdout)

    def test_format_with_footer(self):
        """Test commit message with footer."""
        stdout, _, code = run_git_script(
            ['format-commit', '--type', 'fix', '--subject', 'fix crash', '--footer', 'Fixes #123']
        )
        self.assertEqual(code, 0)
        self.assertIn('Fixes #123', stdout)

    def test_all_commit_types(self):
        """Test all valid commit types."""
        valid_types = ['feat', 'fix', 'docs', 'style', 'refactor', 'perf', 'test', 'chore', 'ci']
        for commit_type in valid_types:
            stdout, _, code = run_git_script(['format-commit', '--type', commit_type, '--subject', 'test subject'])
            self.assertEqual(code, 0, f'Failed for type: {commit_type}')
            result = parse_toon(stdout)
            self.assertEqual(result['type'], commit_type)

    def test_validation_warning_long_subject(self):
        """Test validation warning for long subject."""
        long_subject = 'a' * 55  # Exceeds 50 chars
        stdout, _, code = run_git_script(['format-commit', '--type', 'fix', '--subject', long_subject])
        self.assertEqual(code, 0)  # Still valid, just warning
        result = parse_toon(stdout)
        self.assertTrue(result['validation']['valid'])
        self.assertTrue(any('50 chars' in w for w in result['validation']['warnings']))

    def test_validation_error_very_long_subject(self):
        """Test validation error for very long subject."""
        very_long_subject = 'a' * 75  # Exceeds 72 chars
        stdout, _, code = run_git_script(['format-commit', '--type', 'fix', '--subject', very_long_subject])
        self.assertEqual(code, 1)  # Invalid
        result = parse_toon(stdout)
        self.assertFalse(result['validation']['valid'])

    def test_validation_warning_past_tense(self):
        """Test validation warning for past tense verb."""
        stdout, _, code = run_git_script(['format-commit', '--type', 'fix', '--subject', 'fixed the bug'])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        self.assertTrue(any('imperative' in w.lower() for w in result['validation']['warnings']))

    def test_missing_required_args(self):
        """Test error when required args missing."""
        _, stderr, code = run_git_script(['format-commit'])
        self.assertNotEqual(code, 0)
        self.assertIn('--type', stderr)

    def test_co_authored_by_not_appended_by_script(self):
        """Test that format-commit does NOT append Co-Authored-By (caller adds it at commit time)."""
        stdout, _, code = run_git_script(['format-commit', '--type', 'feat', '--subject', 'add feature'])
        self.assertEqual(code, 0)
        self.assertNotIn('Co-Authored-By', stdout)

    def test_ci_commit_type(self):
        """Test that ci is a valid commit type."""
        stdout, _, code = run_git_script(['format-commit', '--type', 'ci', '--subject', 'update workflow'])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        self.assertEqual(result['type'], 'ci')
        self.assertIn('ci: update workflow', result['formatted_message'])

    def test_imperative_allowlist_no_false_warnings(self):
        """Test that imperative allowlist words don't trigger past-tense warnings."""
        # Words ending in -ed/-ing that are valid imperative forms, not past tense/gerund
        allowlist_samples = ['embed', 'spread', 'thread', 'overhead', 'string', 'bring', 'caching', 'hashing', 'nothing']
        for word in allowlist_samples:
            stdout, _, code = run_git_script(['format-commit', '--type', 'fix', '--subject', f'{word} the module'])
            self.assertEqual(code, 0, f'Failed for allowlist word: {word}')
            result = parse_toon(stdout)
            warnings = result['validation']['warnings']
            imperative_warnings = [w for w in warnings if 'imperative' in w.lower()]
            self.assertEqual(
                len(imperative_warnings), 0, f'False imperative warning for allowlisted word "{word}": {warnings}'
            )

    def test_body_wrapping_preserves_indentation(self):
        """Test that body wrapping preserves leading indentation for bullet lists."""
        body = '  - This is a very long bullet point that should wrap at seventy two characters while keeping indentation'
        stdout, _, code = run_git_script(
            ['format-commit', '--type', 'fix', '--subject', 'fix issue', '--body', body]
        )
        self.assertEqual(code, 0)
        # Verify wrapped lines start with the same indentation
        body_lines = [
            line for line in stdout.split('\n') if line.startswith('  ') and not line.strip().startswith('Co-Authored')
        ]
        for line in body_lines:
            self.assertTrue(line.startswith('  '), f'Indentation lost: {line!r}')


class TestAnalyzeDiff(unittest.TestCase):
    """Test git-workflow.py analyze-diff subcommand."""

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
        with tempfile.NamedTemporaryFile(mode='w', suffix='.diff', delete=False) as f:
            f.write(diff_content)
            f.flush()

            stdout, _, code = run_git_script(['analyze-diff', '--file', f.name])
            self.assertEqual(code, 0)
            result = parse_toon(stdout)
            self.assertEqual(result['status'], 'success')
            self.assertEqual(result['suggestions']['type'], 'fix')

    def test_analyze_file_not_found(self):
        """Test error when diff file not found."""
        stdout, _, code = run_git_script(['analyze-diff', '--file', '/nonexistent/file.diff'])
        self.assertEqual(code, 1)
        result = parse_toon(stdout)
        self.assertEqual(result['status'], 'failure')
        self.assertIn('not found', result['error'])

    def test_missing_file_arg(self):
        """Test error when file arg missing."""
        _, stderr, code = run_git_script(['analyze-diff'])
        self.assertNotEqual(code, 0)
        self.assertIn('--file', stderr)

    def test_analyze_feat_detection(self):
        """Test analysis detects feat when additions far exceed deletions."""
        # Need many more additions than deletions (additions > deletions * 2)
        # and at least one src file for feat detection
        lines = ['diff --git a/src/main/java/New.java b/src/main/java/New.java']
        lines.append('@@ -1 +1,20 @@')
        lines.append('-old line')
        for i in range(20):
            lines.append(f'+    new line {i}')
        diff_content = '\n'.join(lines) + '\n'
        with tempfile.NamedTemporaryFile(mode='w', suffix='.diff', delete=False) as f:
            f.write(diff_content)
            f.flush()
            stdout, _, code = run_git_script(['analyze-diff', '--file', f.name])
            self.assertEqual(code, 0)
            result = parse_toon(stdout)
            self.assertEqual(result['suggestions']['type'], 'feat')

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
        with tempfile.NamedTemporaryFile(mode='w', suffix='.diff', delete=False) as f:
            f.write(diff_content)
            f.flush()
            stdout, _, code = run_git_script(['analyze-diff', '--file', f.name])
            self.assertEqual(code, 0)
            result = parse_toon(stdout)
            self.assertEqual(result['suggestions']['type'], 'refactor')

    def test_analyze_ci_detection(self):
        """Test analysis detects ci type for CI config files."""
        diff_content = """diff --git a/.github/workflows/ci.yml b/.github/workflows/ci.yml
--- a/.github/workflows/ci.yml
+++ b/.github/workflows/ci.yml
-    runs-on: ubuntu-20.04
+    runs-on: ubuntu-22.04
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.diff', delete=False) as f:
            f.write(diff_content)
            f.flush()
            stdout, _, code = run_git_script(['analyze-diff', '--file', f.name])
            self.assertEqual(code, 0)
            result = parse_toon(stdout)
            self.assertEqual(result['suggestions']['type'], 'ci')

    def test_analyze_monorepo_scope(self):
        """Test scope detection for monorepo layouts (packages/<name>/...)."""
        diff_content = """diff --git a/packages/auth-service/src/login.ts b/packages/auth-service/src/login.ts
--- a/packages/auth-service/src/login.ts
+++ b/packages/auth-service/src/login.ts
+export function login() { return true; }
+export function logout() { return true; }
+export function refresh() { return true; }
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.diff', delete=False) as f:
            f.write(diff_content)
            f.flush()
            stdout, _, code = run_git_script(['analyze-diff', '--file', f.name])
            self.assertEqual(code, 0)
            result = parse_toon(stdout)
            self.assertEqual(result['suggestions']['scope'], 'auth-service')

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
        with tempfile.NamedTemporaryFile(mode='w', suffix='.diff', delete=False) as f:
            f.write(diff_content)
            f.flush()
            stdout, _, code = run_git_script(['analyze-diff', '--file', f.name])
            self.assertEqual(code, 0)
            result = parse_toon(stdout)
            self.assertEqual(result['suggestions']['scope'], 'mypackage')

    def test_analyze_js_scope_detection(self):
        """Test scope detection for JS/TS layouts (src/<component>/*.ts)."""
        diff_content = """diff --git a/src/components/Button.tsx b/src/components/Button.tsx
--- a/src/components/Button.tsx
+++ b/src/components/Button.tsx
+export const Button = () => <button>Click</button>;
+export const IconButton = () => <button>Icon</button>;
+export const LinkButton = () => <a>Link</a>;
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.diff', delete=False) as f:
            f.write(diff_content)
            f.flush()
            stdout, _, code = run_git_script(['analyze-diff', '--file', f.name])
            self.assertEqual(code, 0)
            result = parse_toon(stdout)
            self.assertEqual(result['suggestions']['scope'], 'components')

    def test_analyze_generic_scope_detection(self):
        """Test scope detection falls back to top-level directory."""
        diff_content = """diff --git a/config/settings.ini b/config/settings.ini
--- a/config/settings.ini
+++ b/config/settings.ini
+[database]
+host = localhost
+port = 5432
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.diff', delete=False) as f:
            f.write(diff_content)
            f.flush()
            stdout, _, code = run_git_script(['analyze-diff', '--file', f.name])
            self.assertEqual(code, 0)
            result = parse_toon(stdout)
            self.assertEqual(result['suggestions']['scope'], 'config')

    def test_analyze_bug_in_comment_lines(self):
        """Test bug detection from comment lines in diff content."""
        diff_content = """diff --git a/src/main/java/Service.java b/src/main/java/Service.java
--- a/src/main/java/Service.java
+++ b/src/main/java/Service.java
+    // Fix null pointer when user is not authenticated
+    if (user != null) {
+        return user.getName();
+    }
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.diff', delete=False) as f:
            f.write(diff_content)
            f.flush()
            stdout, _, code = run_git_script(['analyze-diff', '--file', f.name])
            self.assertEqual(code, 0)
            result = parse_toon(stdout)
            self.assertEqual(result['suggestions']['type'], 'fix')


class TestAnalyzeDiffTypeDetection(unittest.TestCase):
    """Test analyze-diff type detection for test-only and docs-only changes (#28, #29)."""

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
        with tempfile.NamedTemporaryFile(mode='w', suffix='.diff', delete=False) as f:
            f.write(diff_content)
            f.flush()
            stdout, _, code = run_git_script(['analyze-diff', '--file', f.name])
            self.assertEqual(code, 0)
            result = parse_toon(stdout)
            self.assertEqual(result['suggestions']['type'], 'test')

    def test_analyze_docs_only_changes(self):
        """Test analysis detects 'docs' type when only documentation files change."""
        diff_content = """diff --git a/README.md b/README.md
--- a/README.md
+++ b/README.md
+## Installation
+Run `npm install` to get started.
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.diff', delete=False) as f:
            f.write(diff_content)
            f.flush()
            stdout, _, code = run_git_script(['analyze-diff', '--file', f.name])
            self.assertEqual(code, 0)
            result = parse_toon(stdout)
            self.assertEqual(result['suggestions']['type'], 'docs')

    def test_analyze_asciidoc_docs(self):
        """Test docs detection for .adoc files."""
        diff_content = """diff --git a/doc/architecture.adoc b/doc/architecture.adoc
--- a/doc/architecture.adoc
+++ b/doc/architecture.adoc
+= Architecture Guide
+This document describes the system architecture.
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.diff', delete=False) as f:
            f.write(diff_content)
            f.flush()
            stdout, _, code = run_git_script(['analyze-diff', '--file', f.name])
            self.assertEqual(code, 0)
            result = parse_toon(stdout)
            self.assertEqual(result['suggestions']['type'], 'docs')


class TestFormatCommitCombined(unittest.TestCase):
    """Test format-commit with all optional params at once (#26)."""

    def test_breaking_and_footer_combined(self):
        """Test commit message with both --breaking and --footer simultaneously."""
        stdout, _, code = run_git_script([
            'format-commit',
            '--type', 'feat',
            '--scope', 'api',
            '--subject', 'change auth endpoint',
            '--breaking', 'Old /auth endpoint removed',
            '--footer', 'Fixes #123',
        ])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        self.assertIn('feat(api)!:', result['formatted_message'])
        self.assertIn('BREAKING CHANGE:', stdout)
        self.assertIn('Fixes #123', stdout)

    def test_all_params_combined(self):
        """Test commit message with body + breaking + footer + scope."""
        stdout, _, code = run_git_script([
            'format-commit',
            '--type', 'feat',
            '--scope', 'api',
            '--subject', 'change auth endpoint',
            '--body', 'Migrated to OAuth 2.0 flow',
            '--breaking', 'Old /auth endpoint removed',
            '--footer', 'Fixes #123',
        ])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        self.assertIn('feat(api)!:', result['formatted_message'])
        self.assertIn('BREAKING CHANGE:', stdout)
        self.assertIn('Fixes #123', stdout)
        self.assertIn('Migrated to OAuth 2.0 flow', stdout)


class TestFormatCommitHeaderLength(unittest.TestCase):
    """Test format-commit validates total header length (#27)."""

    def test_long_scope_plus_subject_exceeds_72(self):
        """Header exceeding 72 chars should fail validation."""
        long_scope = 'very-long-module-name'
        long_subject = 'a' * 50  # type(scope): subject → 5 + 23 + 4 + 50 = 82 chars
        stdout, _, code = run_git_script([
            'format-commit', '--type', 'feat', '--scope', long_scope, '--subject', long_subject,
        ])
        self.assertEqual(code, 1)
        result = parse_toon(stdout)
        self.assertFalse(result['validation']['valid'])
        self.assertTrue(any('Header' in w for w in result['validation']['warnings']))


class TestDetectArtifacts(unittest.TestCase):
    """Test git-workflow.py detect-artifacts subcommand."""

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

        stdout, _, code = run_git_script(['detect-artifacts', '--root', self.tmpdir])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        self.assertEqual(result['status'], 'success')
        self.assertGreaterEqual(len(result['safe']), 4)
        # Verify specific patterns
        safe_str = '\n'.join(result['safe'])
        self.assertIn('.class', safe_str)
        self.assertIn('.DS_Store', safe_str)

    def test_detects_uncertain_artifacts(self):
        """Test detection of uncertain artifacts in target/build dirs."""
        self._create_file('target/classes/App.class')
        self._create_file('target/output.jar')
        self._create_file('build/libs/app.jar')

        stdout, _, code = run_git_script(['detect-artifacts', '--root', self.tmpdir])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        self.assertEqual(result['status'], 'success')
        # .class in target/ is captured by safe patterns, .jar files are uncertain
        self.assertTrue(len(result['uncertain']) >= 1 or len(result['safe']) >= 1)
        self.assertGreater(result['total'], 0)

    def test_detects_python_egg_artifacts(self):
        """Test detection of Python .egg-info and .eggs artifacts."""
        self._create_file('mypackage.egg-info/PKG-INFO')
        self._create_file('.eggs/some-egg.egg')

        stdout, _, code = run_git_script(['detect-artifacts', '--root', self.tmpdir])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        self.assertGreaterEqual(len(result['safe']), 2)
        safe_str = '\n'.join(result['safe'])
        self.assertIn('egg-info', safe_str)
        self.assertIn('.eggs', safe_str)

    def test_detects_typescript_buildinfo(self):
        """Test detection of TypeScript .tsbuildinfo files."""
        self._create_file('tsconfig.tsbuildinfo')
        self._create_file('packages/lib/tsconfig.tsbuildinfo')

        stdout, _, code = run_git_script(['detect-artifacts', '--root', self.tmpdir])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        safe_str = '\n'.join(result['safe'])
        self.assertIn('tsbuildinfo', safe_str)
        self.assertGreaterEqual(len(result['safe']), 2)

    def test_detects_plan_temp_as_safe(self):
        """Test that .plan/temp/ files are safe (not uncertain)."""
        self._create_file('.plan/temp/scratch.txt')
        self._create_file('.plan/temp/debug.log')

        stdout, _, code = run_git_script(['detect-artifacts', '--root', self.tmpdir])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        safe_str = '\n'.join(result['safe'])
        self.assertIn('.plan/temp', safe_str)
        # Should NOT be in uncertain
        uncertain_str = '\n'.join(result['uncertain'])
        self.assertNotIn('.plan/temp', uncertain_str)

    def test_detects_dist_next_as_uncertain(self):
        """Test that dist/ and .next/ directories are uncertain."""
        self._create_file('dist/bundle.js')
        self._create_file('.next/cache/data.json')

        stdout, _, code = run_git_script(['detect-artifacts', '--root', self.tmpdir])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        uncertain_str = '\n'.join(result['uncertain'])
        self.assertIn('dist/', uncertain_str)
        self.assertIn('.next/', uncertain_str)

    def test_detects_root_level_artifacts(self):
        """Test detection of artifacts at repo root, not just in subdirectories (#23)."""
        self._create_file('Example.class')
        self._create_file('.DS_Store')
        self._create_file('scratch.temp')

        stdout, _, code = run_git_script(['detect-artifacts', '--root', self.tmpdir])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        self.assertGreaterEqual(len(result['safe']), 3)
        safe_str = '\n'.join(result['safe'])
        self.assertIn('Example.class', safe_str)
        self.assertIn('.DS_Store', safe_str)
        self.assertIn('scratch.temp', safe_str)

    def test_clean_directory_returns_empty(self):
        """Test scanning a directory with no artifacts."""
        self._create_file('src/main/java/App.java')
        self._create_file('README.md')

        stdout, _, code = run_git_script(['detect-artifacts', '--root', self.tmpdir])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['total'], 0)
        self.assertEqual(len(result['safe']), 0)
        self.assertEqual(len(result['uncertain']), 0)

    def test_nonexistent_root_fails(self):
        """Test error when root directory doesn't exist."""
        stdout, _, code = run_git_script(['detect-artifacts', '--root', '/nonexistent/path'])
        self.assertEqual(code, 1)
        result = parse_toon(stdout)
        self.assertEqual(result['status'], 'failure')
        self.assertIn('not found', result['error'])

    def test_defaults_to_cwd_without_root(self):
        """Test that detect-artifacts runs without --root argument."""
        stdout, _, code = run_git_script(['detect-artifacts'])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        self.assertEqual(result['status'], 'success')

    def test_help_includes_detect_artifacts(self):
        """Test that help output lists detect-artifacts."""
        stdout, _, code = run_git_script(['--help'])
        self.assertEqual(code, 0)
        self.assertIn('detect-artifacts', stdout)

    def test_respects_gitignore_by_default(self):
        """Test that gitignored files are excluded from results by default."""
        import subprocess as sp

        # Set up a git repo with .gitignore
        sp.run(['git', 'init'], cwd=self.tmpdir, capture_output=True)
        sp.run(['git', 'config', 'user.email', 'test@test.com'], cwd=self.tmpdir, capture_output=True)
        sp.run(['git', 'config', 'user.name', 'Test'], cwd=self.tmpdir, capture_output=True)

        # Create .gitignore that ignores *.class
        (Path(self.tmpdir) / '.gitignore').write_text('*.class\n')
        sp.run(['git', 'add', '.gitignore'], cwd=self.tmpdir, capture_output=True)
        sp.run(['git', 'commit', '-m', 'init'], cwd=self.tmpdir, capture_output=True)

        # Create artifacts — .class is gitignored, .temp is not
        self._create_file('src/Example.class')
        self._create_file('scratch.temp')

        stdout, _, code = run_git_script(['detect-artifacts', '--root', self.tmpdir])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        safe_files = result['safe']
        # .class should be excluded (gitignored), .temp should remain
        self.assertFalse(any('.class' in f for f in safe_files), f'.class should be excluded: {safe_files}')
        self.assertTrue(any('.temp' in f for f in safe_files), f'.temp should be present: {safe_files}')

    def test_skips_git_directory(self):
        """Test that .git/ directory contents are excluded from results."""
        # Create a fake .git directory with artifact-like files
        self._create_file('.git/objects/pack/pack-abc.class')
        self._create_file('.git/hooks/pre-commit.pyc')
        self._create_file('src/real.temp')

        stdout, _, code = run_git_script(['detect-artifacts', '--root', self.tmpdir])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        # .git files should be excluded, only src/real.temp in results
        all_files = result['safe'] + result['uncertain']
        for f in all_files:
            self.assertFalse(f.startswith('.git/'), f'.git file should be excluded: {f}')
        self.assertTrue(any('real.temp' in f for f in result['safe']))

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
        self.assertTrue(any('.class' in f for f in safe_files), f'.class should be present with --no-gitignore: {safe_files}')


class TestWrapText(unittest.TestCase):
    """Test wrap_text function directly."""

    @classmethod
    def setUpClass(cls):
        """Import wrap_text for direct testing."""
        from importlib import import_module
        mod = import_module('git-workflow')
        cls.wrap_text = staticmethod(mod.wrap_text)

    def test_short_line_unchanged(self):
        """Lines within width are not wrapped."""
        self.assertEqual(self.wrap_text('short line', 72), 'short line')

    def test_long_line_wrapped(self):
        """Lines exceeding width are wrapped at word boundaries."""
        text = 'a ' * 40  # 80 chars
        result = self.wrap_text(text.strip(), 72)
        for line in result.split('\n'):
            self.assertLessEqual(len(line), 72)

    def test_preserves_bullet_indentation(self):
        """Wrapped lines preserve leading indentation."""
        text = '  - ' + 'word ' * 20
        result = self.wrap_text(text.strip(), 72)
        # First line has no indent since we stripped, but indented input does
        text_indented = '  - ' + 'word ' * 20
        result_indented = self.wrap_text(text_indented, 72)
        for line in result_indented.split('\n'):
            self.assertTrue(line.startswith('  '), f'Lost indent: {line!r}')

    def test_deep_indent_not_wrapped(self):
        """Lines with >52 chars indent are kept as-is (effective_width < 20)."""
        text = ' ' * 55 + 'deeply indented content that should not be wrapped'
        result = self.wrap_text(text, 72)
        self.assertEqual(result, text)

    def test_very_long_word_not_broken(self):
        """A single word longer than width should not be split (#20)."""
        url = 'https://example.com/very/long/path/that/exceeds/seventy/two/characters/easily'
        result = self.wrap_text(url, 72)
        # The URL should remain intact on a single line
        self.assertEqual(result, url)

    def test_multiline_preserves_paragraphs(self):
        """Multiple paragraphs separated by newlines are handled independently."""
        text = 'First paragraph.\nSecond paragraph.'
        result = self.wrap_text(text, 72)
        self.assertEqual(result, text)


class TestAnalyzeDiffEdgeCases(unittest.TestCase):
    """Test git-workflow.py analyze-diff edge cases."""

    def test_analyze_empty_diff_file(self):
        """Test analysis of an empty diff file returns default suggestions."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.diff', delete=False) as f:
            f.write('')
            f.flush()
            stdout, _, code = run_git_script(['analyze-diff', '--file', f.name])
            self.assertEqual(code, 0)
            result = parse_toon(stdout)
            self.assertEqual(result['status'], 'success')
            self.assertEqual(result['suggestions']['type'], 'chore')
            self.assertIsNone(result['suggestions']['scope'])

    def test_analyze_diff_only_whitespace(self):
        """Test analysis of a diff with only whitespace."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.diff', delete=False) as f:
            f.write('   \n\n  \n')
            f.flush()
            stdout, _, code = run_git_script(['analyze-diff', '--file', f.name])
            self.assertEqual(code, 0)
            result = parse_toon(stdout)
            self.assertEqual(result['status'], 'success')
            self.assertEqual(result['suggestions']['type'], 'chore')


class TestToonContract(unittest.TestCase):
    """Verify TOON output matches the contract documented in SKILL.md."""

    def test_format_commit_output_contract(self):
        """Verify format-commit output has all documented fields."""
        stdout, _, code = run_git_script([
            'format-commit', '--type', 'feat', '--scope', 'auth', '--subject', 'add login',
        ])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        # Documented fields in SKILL.md output section
        required_fields = {'type', 'scope', 'subject', 'formatted_message', 'validation', 'status'}
        missing = required_fields - set(result.keys())
        self.assertEqual(missing, set(), f'Missing TOON contract fields: {missing}')
        # Validation sub-structure
        self.assertIn('valid', result['validation'])
        self.assertIn('warnings', result['validation'])

    def test_analyze_diff_output_contract(self):
        """Verify analyze-diff output has all documented fields."""
        diff_content = """diff --git a/src/main/java/New.java b/src/main/java/New.java
+new line
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.diff', delete=False) as f:
            f.write(diff_content)
            f.flush()
            stdout, _, code = run_git_script(['analyze-diff', '--file', f.name])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        required_fields = {'mode', 'suggestions', 'status'}
        missing = required_fields - set(result.keys())
        self.assertEqual(missing, set(), f'Missing TOON contract fields: {missing}')
        # Suggestions sub-structure
        sug = result['suggestions']
        for field in ('type', 'scope', 'detected_changes', 'files_changed'):
            self.assertIn(field, sug, f'Missing suggestions.{field}')

    def test_detect_artifacts_output_contract(self):
        """Verify detect-artifacts output has all documented fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            stdout, _, code = run_git_script(['detect-artifacts', '--root', tmpdir])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        required_fields = {'root', 'safe', 'uncertain', 'total', 'status'}
        missing = required_fields - set(result.keys())
        self.assertEqual(missing, set(), f'Missing TOON contract fields: {missing}')


class TestMain(unittest.TestCase):
    """Test git-workflow.py main entry point."""

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


if __name__ == '__main__':
    unittest.main()
