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

    def test_co_authored_by_footer_present(self):
        """Test that Co-Authored-By footer is present."""
        stdout, _, code = run_git_script(['format-commit', '--type', 'feat', '--subject', 'add feature'])
        self.assertEqual(code, 0)
        self.assertIn('Co-Authored-By: Claude <noreply@anthropic.com>', stdout)

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
