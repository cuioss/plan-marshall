"""Tests for permission_web.py - WebFetch permission analysis script."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

# Import shared infrastructure
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from toon_parser import parse_toon  # type: ignore[import-not-found]  # noqa: E402

from conftest import get_script_path, run_script  # noqa: E402

# Script under test
SCRIPT_PATH = get_script_path('plan-marshall', 'workflow-permission-web', 'permission_web.py')


def run_pw_script(args: list) -> tuple:
    """Run permission_web.py with args and return (stdout, stderr, returncode)."""
    result = run_script(SCRIPT_PATH, *args)
    return result.stdout, result.stderr, result.returncode


class TestCategorizeDomains(unittest.TestCase):
    """Test permission_web.py categorize subcommand."""

    def test_categorize_major_domain(self):
        """Test that known major domains are correctly categorized."""
        domains = ['docs.oracle.com', 'maven.apache.org', 'junit.org']
        stdout, _, code = run_pw_script(['categorize', '--domains', json.dumps(domains)])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['categories']['major'], 3)

    def test_categorize_high_reach_domain(self):
        """Test that high-reach platforms are correctly categorized."""
        domains = ['github.com', 'stackoverflow.com']
        stdout, _, code = run_pw_script(['categorize', '--domains', json.dumps(domains)])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        self.assertEqual(result['categories']['high_reach'], 2)

    def test_categorize_unknown_domain(self):
        """Test that unknown domains are categorized as unknown."""
        domains = ['my-internal-tool.example.com']
        stdout, _, code = run_pw_script(['categorize', '--domains', json.dumps(domains)])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        self.assertEqual(result['categories']['unknown'], 1)

    def test_categorize_suspicious_domain(self):
        """Test that domains with red flags are flagged as suspicious."""
        domains = ['free-downloads-keygen.tk']
        stdout, _, code = run_pw_script(['categorize', '--domains', json.dumps(domains)])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        self.assertEqual(result['categories']['suspicious'], 1)
        # TOON parser renders dict keys with array notation; check key prefix
        self.assertTrue(
            any(k.startswith('free-downloads-keygen.tk') for k in result['red_flags']),
            f'Expected domain in red_flags keys: {result["red_flags"]}',
        )

    def test_categorize_universal_wildcard(self):
        """Test that wildcard is categorized as universal."""
        domains = ['*']
        stdout, _, code = run_pw_script(['categorize', '--domains', json.dumps(domains)])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        self.assertEqual(result['categories']['universal'], 1)

    def test_categorize_subdomain_of_known(self):
        """Test that subdomains of known domains inherit parent category."""
        domains = ['api.github.com', 'javadoc.docs.oracle.com']
        stdout, _, code = run_pw_script(['categorize', '--domains', json.dumps(domains)])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        # api.github.com -> high_reach (parent: github.com)
        # javadoc.docs.oracle.com -> major (parent: docs.oracle.com)
        self.assertEqual(result['categories']['high_reach'], 1)
        self.assertEqual(result['categories']['major'], 1)

    def test_categorize_mixed_domains(self):
        """Test categorization of a mixed set of domains."""
        domains = ['docs.oracle.com', 'github.com', 'unknown.example.com', '*']
        stdout, _, code = run_pw_script(['categorize', '--domains', json.dumps(domains)])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        self.assertEqual(result['total'], 4)
        self.assertEqual(result['categories']['major'], 1)
        self.assertEqual(result['categories']['high_reach'], 1)
        self.assertEqual(result['categories']['unknown'], 1)
        self.assertEqual(result['categories']['universal'], 1)

    def test_categorize_empty_list(self):
        """Test categorization of empty domain list."""
        stdout, _, code = run_pw_script(['categorize', '--domains', '[]'])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        self.assertEqual(result['total'], 0)

    def test_categorize_invalid_json(self):
        """Test error on invalid JSON input."""
        stdout, _, code = run_pw_script(['categorize', '--domains', 'not-json'])
        self.assertEqual(code, 1)
        result = parse_toon(stdout)
        self.assertEqual(result['status'], 'failure')

    def test_categorize_not_array(self):
        """Test error when input is not an array."""
        stdout, _, code = run_pw_script(['categorize', '--domains', '"single-string"'])
        self.assertEqual(code, 1)
        result = parse_toon(stdout)
        self.assertEqual(result['status'], 'failure')
        self.assertIn('array', result['error'])


class TestAnalyze(unittest.TestCase):
    """Test permission_web.py analyze subcommand."""

    def _write_settings(self, domains: list[str], tmpdir: str) -> str:
        """Write a settings.json with WebFetch permissions."""
        parent = Path(tmpdir)
        parent.mkdir(parents=True, exist_ok=True)
        path = parent / 'settings.json'
        settings = {
            'permissions': {
                'allow': [f'WebFetch({d})' for d in domains],
            },
        }
        path.write_text(json.dumps(settings))
        return str(path)

    def test_analyze_both_files(self):
        """Test analysis of both global and local settings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            global_file = self._write_settings(
                ['docs.oracle.com', 'github.com', 'unknown.example.com'], tmpdir + '/global'
            )
            local_file = self._write_settings(
                ['github.com', 'my-project-docs.com'], tmpdir + '/local'
            )

            stdout, _, code = run_pw_script([
                'analyze', '--global-file', global_file, '--local-file', local_file,
            ])
            self.assertEqual(code, 0)
            result = parse_toon(stdout)
            self.assertEqual(result['status'], 'success')
            self.assertEqual(result['global_count'], 3)
            self.assertEqual(result['local_count'], 2)
            self.assertEqual(result['total_unique'], 4)
            # github.com is in both
            self.assertIn('github.com', result['duplicates'])
            self.assertEqual(result['statistics']['domains_analyzed'], 4)
            self.assertEqual(result['statistics']['files_read'], 2)

    def test_analyze_with_universal_wildcard(self):
        """Test analysis detects universal wildcard redundancy."""
        with tempfile.TemporaryDirectory() as tmpdir:
            global_file = self._write_settings(
                ['*', 'docs.oracle.com', 'github.com'], tmpdir
            )
            stdout, _, code = run_pw_script([
                'analyze', '--global-file', global_file,
            ])
            self.assertEqual(code, 0)
            result = parse_toon(stdout)
            # docs.oracle.com and github.com are redundant due to wildcard
            self.assertGreater(result['statistics']['redundant_found'], 0)

    def test_analyze_missing_file(self):
        """Test analysis handles missing files gracefully."""
        stdout, _, code = run_pw_script([
            'analyze', '--global-file', '/nonexistent/settings.json',
        ])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        self.assertEqual(result['status'], 'success')
        self.assertTrue(result['statistics'].get('global_missing'))

    def test_analyze_invalid_json_file(self):
        """Test analysis reports invalid JSON in settings file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('not valid json{{{')
            f.flush()
            stdout, _, code = run_pw_script([
                'analyze', '--global-file', f.name,
            ])
            self.assertEqual(code, 1)
            result = parse_toon(stdout)
            self.assertEqual(result['status'], 'failure')
            self.assertIn('Invalid JSON', result['error'])

    def test_analyze_generates_recommendations(self):
        """Test that analysis generates actionable recommendations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            global_file = self._write_settings([], tmpdir + '/global')
            local_file = self._write_settings(
                ['docs.oracle.com', 'unknown-site.xyz'], tmpdir + '/local'
            )

            stdout, _, code = run_pw_script([
                'analyze', '--global-file', global_file, '--local-file', local_file,
            ])
            self.assertEqual(code, 0)
            result = parse_toon(stdout)
            # Should have at least a move_to_global rec for docs.oracle.com
            # and a research rec for unknown-site.xyz
            actions = [r['action'] for r in result['recommendations']]
            self.assertIn('move_to_global', actions)
            self.assertIn('research', actions)


class TestAnalyzeExtractDomains(unittest.TestCase):
    """Test domain extraction from settings structures."""

    def test_extract_from_allow_section(self):
        """Test extraction from permissions.allow."""
        from permission_web import extract_webfetch_domains  # type: ignore[import-not-found]

        settings = {'permissions': {'allow': ['WebFetch(example.com)', 'Bash(ls)', 'WebFetch(api.test.com)']}}
        domains = extract_webfetch_domains(settings)
        self.assertEqual(sorted(domains), ['api.test.com', 'example.com'])

    def test_extract_from_deny_section(self):
        """Test extraction from permissions.deny."""
        from permission_web import extract_webfetch_domains  # type: ignore[import-not-found]

        settings = {'permissions': {'deny': ['WebFetch(blocked.com)']}}
        domains = extract_webfetch_domains(settings)
        self.assertEqual(domains, ['blocked.com'])

    def test_extract_empty_settings(self):
        """Test extraction from empty settings."""
        from permission_web import extract_webfetch_domains  # type: ignore[import-not-found]

        self.assertEqual(extract_webfetch_domains({}), [])
        self.assertEqual(extract_webfetch_domains({'permissions': {}}), [])


class TestMain(unittest.TestCase):
    """Test permission_web.py main entry point."""

    def test_no_subcommand(self):
        """Test error when no subcommand provided."""
        _, stderr, code = run_pw_script([])
        self.assertNotEqual(code, 0)

    def test_help(self):
        """Test help output."""
        stdout, _, code = run_pw_script(['--help'])
        self.assertEqual(code, 0)
        self.assertIn('analyze', stdout)
        self.assertIn('categorize', stdout)


if __name__ == '__main__':
    unittest.main()
