"""Tests for permission_web.py - WebFetch permission analysis script.

Tier 2 (direct import) tests with 3 subprocess tests for CLI plumbing.
"""

import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from toon_parser import parse_toon  # type: ignore[import-not-found]

from conftest import get_script_path, run_script

# Script under test (for subprocess CLI plumbing tests)
SCRIPT_PATH = get_script_path('plan-marshall', 'workflow-permission-web', 'permission_web.py')

# Tier 2 direct imports — conftest sets up PYTHONPATH for cross-skill imports
from permission_web import (  # type: ignore[import-not-found]  # noqa: E402
    apply_recommendations,
    categorize_domains,
    check_red_flags,
    cmd_analyze,
    cmd_categorize,
    extract_webfetch_domains,
    extract_webfetch_domains_by_section,
    find_redundant,
)


class TestCategorizeDomains(unittest.TestCase):
    """Test permission_web.py categorize via direct import."""

    def test_categorize_major_domain(self):
        """Test that known major domains are correctly categorized."""
        categories = categorize_domains(['docs.oracle.com', 'maven.apache.org', 'junit.org'])
        self.assertEqual(len(categories['major']), 3)

    def test_categorize_high_reach_domain(self):
        """Test that high-reach platforms are correctly categorized."""
        categories = categorize_domains(['github.com', 'stackoverflow.com'])
        self.assertEqual(len(categories['high_reach']), 2)

    def test_categorize_unknown_domain(self):
        """Test that unknown domains are categorized as unknown."""
        categories = categorize_domains(['my-internal-tool.example.com'])
        self.assertEqual(len(categories['unknown']), 1)

    def test_categorize_suspicious_domain(self):
        """Test that domains with red flags are flagged as suspicious."""
        categories = categorize_domains(['free-downloads-keygen.tk'])
        self.assertEqual(len(categories['suspicious']), 1)
        flags = check_red_flags('free-downloads-keygen.tk')
        self.assertTrue(len(flags) > 0)

    def test_categorize_universal_wildcard(self):
        """Test that wildcard is categorized as universal."""
        categories = categorize_domains(['*'])
        self.assertEqual(len(categories['universal']), 1)

    def test_categorize_subdomain_of_known(self):
        """Test that subdomains of known domains inherit parent category."""
        categories = categorize_domains(['api.github.com', 'javadoc.docs.oracle.com'])
        # api.github.com -> high_reach (parent: github.com)
        # javadoc.docs.oracle.com -> major (parent: docs.oracle.com)
        self.assertEqual(len(categories['high_reach']), 1)
        self.assertEqual(len(categories['major']), 1)

    def test_categorize_mixed_domains(self):
        """Test categorization of a mixed set of domains."""
        categories = categorize_domains(['docs.oracle.com', 'github.com', 'unknown.example.com', '*'])
        self.assertEqual(len(categories['major']), 1)
        self.assertEqual(len(categories['high_reach']), 1)
        self.assertEqual(len(categories['unknown']), 1)
        self.assertEqual(len(categories['universal']), 1)

    def test_categorize_empty_list(self):
        """Test categorization of empty domain list."""
        categories = categorize_domains([])
        total = sum(len(v) for v in categories.values())
        self.assertEqual(total, 0)


class TestCategorizeCmd(unittest.TestCase):
    """Test cmd_categorize via direct import."""

    def test_categorize_invalid_json(self):
        """Test error on invalid JSON input."""
        result = cmd_categorize(Namespace(domains='not-json'))
        self.assertEqual(result['status'], 'error')

    def test_categorize_not_array(self):
        """Test error when input is not an array."""
        result = cmd_categorize(Namespace(domains='"single-string"'))
        self.assertEqual(result['status'], 'error')
        self.assertIn('array', result['error'])


class TestCategorizeEdgeCases(unittest.TestCase):
    """Test edge cases for categorize (#42)."""

    def test_categorize_domain_star_prefix(self):
        """Test that 'domain:*' is NOT treated as universal (vestigial format)."""
        categories = categorize_domains(['domain:*'])
        # domain:* is not a valid format — should be classified as unknown, not universal
        self.assertEqual(len(categories['unknown']), 1)
        self.assertEqual(len(categories['universal']), 0)


class TestApply(unittest.TestCase):
    """Test permission_web.py apply via direct import."""

    def _write_settings(self, domains: list[str], path: str, extra_allow: list[str] | None = None) -> Path:
        """Write a settings.json with WebFetch permissions."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        allow = [f'WebFetch({d})' for d in domains]
        if extra_allow:
            allow.extend(extra_allow)
        settings = {
            'permissions': {
                'allow': allow,
            },
        }
        p.write_text(json.dumps(settings))
        return p

    def test_add_domains(self):
        """Test adding domains to a settings file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_settings(['existing.com'], f'{tmpdir}/settings.json')
            result = apply_recommendations(path, ['new-domain.com', 'another.org'], [])
            self.assertEqual(result['status'], 'success')
            self.assertEqual(result['added'], 2)
            self.assertEqual(result['removed'], 0)
            self.assertIn('new-domain.com', result['final_domains'])
            self.assertIn('existing.com', result['final_domains'])

    def test_remove_domains(self):
        """Test removing domains from a settings file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_settings(['keep.com', 'remove-me.com'], f'{tmpdir}/settings.json')
            result = apply_recommendations(path, [], ['remove-me.com'])
            self.assertEqual(result['removed'], 1)
            self.assertIn('keep.com', result['final_domains'])
            self.assertNotIn('remove-me.com', result['final_domains'])

    def test_add_and_remove(self):
        """Test adding and removing in one call."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_settings(['old.com', 'keep.com'], f'{tmpdir}/settings.json')
            result = apply_recommendations(path, ['new.com'], ['old.com'])
            self.assertEqual(result['added'], 1)
            self.assertEqual(result['removed'], 1)
            self.assertIn('new.com', result['final_domains'])
            self.assertNotIn('old.com', result['final_domains'])

    def test_preserves_non_webfetch_entries(self):
        """Test that apply does not touch non-WebFetch permissions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_settings(['example.com'], f'{tmpdir}/settings.json', extra_allow=['Bash(ls)'])
            apply_recommendations(path, ['new.com'], [])
            # Re-read and verify Bash(ls) is still there
            settings = json.loads(path.read_text())
            self.assertIn('Bash(ls)', settings['permissions']['allow'])

    def test_no_duplicate_add(self):
        """Test that adding an already-existing domain doesn't duplicate."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_settings(['exists.com'], f'{tmpdir}/settings.json')
            result = apply_recommendations(path, ['exists.com'], [])
            self.assertEqual(result['added'], 0)

    def test_missing_file(self):
        """Test error when file does not exist."""
        result = apply_recommendations(Path('/nonexistent/settings.json'), ['example.com'], [])
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['error_code'], 'NOT_FOUND')

    def test_apply_invalid_json_in_file(self):
        """Test apply with a settings file containing invalid JSON."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('not valid json{{{')
            f.flush()
            result = apply_recommendations(Path(f.name), ['example.com'], [])
            self.assertEqual(result['status'], 'error')
            self.assertEqual(result['error_code'], 'PARSE_ERROR')


class TestApplyEdgeCasesExtended(unittest.TestCase):
    """Extended edge case tests for apply (#43)."""

    def test_remove_nonexistent_domain_is_noop(self):
        """Removing a domain that doesn't exist should be a graceful no-op."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / 'settings.json'
            path.write_text(json.dumps({'permissions': {'allow': ['WebFetch(keep.com)']}}))
            result = apply_recommendations(path, [], ['does-not-exist.com'])
            self.assertEqual(result['status'], 'success')
            self.assertEqual(result['removed'], 0)
            self.assertIn('keep.com', result['final_domains'])


class TestApplyAddAndRemoveSameDomain(unittest.TestCase):
    """Test apply when a domain is in both add and remove (#33)."""

    def test_add_and_remove_same_domain(self):
        """Adding and removing the same domain — remove should win."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / 'settings.json'
            path.write_text(json.dumps({'permissions': {'allow': ['WebFetch(target.com)']}}))
            result = apply_recommendations(path, ['target.com'], ['target.com'])
            self.assertEqual(result['status'], 'success')
            self.assertNotIn('target.com', result['final_domains'])


class TestAnalyze(unittest.TestCase):
    """Test permission_web.py analyze via direct import."""

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
            local_file = self._write_settings(['github.com', 'my-project-docs.com'], tmpdir + '/local')

            result = cmd_analyze(Namespace(global_file=global_file, local_file=local_file))
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
            global_file = self._write_settings(['*', 'docs.oracle.com', 'github.com'], tmpdir)
            result = cmd_analyze(Namespace(global_file=global_file, local_file=None))
            # docs.oracle.com and github.com are redundant due to wildcard
            self.assertGreater(result['statistics']['redundant_found'], 0)

    def test_analyze_missing_file(self):
        """Test analysis handles missing files gracefully."""
        result = cmd_analyze(Namespace(global_file='/nonexistent/settings.json', local_file=None))
        self.assertEqual(result['status'], 'success')
        self.assertTrue(result['statistics'].get('global_missing'))

    def test_analyze_invalid_json_file(self):
        """Test analysis reports invalid JSON in settings file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('not valid json{{{')
            f.flush()
            result = cmd_analyze(Namespace(global_file=f.name, local_file=None))
            self.assertEqual(result['status'], 'error')
            self.assertIn('Invalid JSON', result['error'])

    def test_analyze_generates_recommendations(self):
        """Test that analysis generates actionable recommendations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            global_file = self._write_settings([], tmpdir + '/global')
            local_file = self._write_settings(['docs.oracle.com', 'unknown-site.xyz'], tmpdir + '/local')

            result = cmd_analyze(Namespace(global_file=global_file, local_file=local_file))
            # Should have at least a move_to_global rec for docs.oracle.com
            # and a research rec for unknown-site.xyz
            actions = [r['action'] for r in result['recommendations']]
            self.assertIn('move_to_global', actions)
            self.assertIn('research', actions)


class TestFindRedundant(unittest.TestCase):
    """Test find_redundant for subdomain and www. detection."""

    def test_subdomain_redundancy(self):
        """Test that api.github.com is redundant when github.com is present."""
        result = find_redundant(['github.com', 'api.github.com', 'docs.oracle.com'])
        self.assertIn('api.github.com', result['subdomain_redundant'])
        self.assertNotIn('github.com', result['subdomain_redundant'])
        self.assertNotIn('docs.oracle.com', result['subdomain_redundant'])

    def test_www_prefix_redundancy(self):
        """Test that www.github.com is redundant when github.com is present."""
        result = find_redundant(['github.com', 'www.github.com'])
        self.assertIn('www.github.com', result['subdomain_redundant'])
        self.assertNotIn('github.com', result['subdomain_redundant'])

    def test_no_redundancy_for_different_domains(self):
        """Test that unrelated domains are not flagged as redundant."""
        result = find_redundant(['github.com', 'gitlab.com'])
        self.assertEqual(result['subdomain_redundant'], [])

    def test_universal_wildcard_makes_all_redundant(self):
        """Test that wildcard makes all specific domains redundant."""
        result = find_redundant(['*', 'github.com', 'docs.oracle.com'])
        self.assertEqual(sorted(result['universal_redundant']), ['docs.oracle.com', 'github.com'])


class TestAnalyzeMissingLocalFile(unittest.TestCase):
    """Test analyze with missing local file specifically."""

    def test_analyze_missing_local_file(self):
        """Test analysis handles missing local file gracefully."""
        result = cmd_analyze(Namespace(global_file=None, local_file='/nonexistent/local-settings.json'))
        self.assertEqual(result['status'], 'success')
        self.assertTrue(result['statistics'].get('local_missing'))


class TestAnalyzeExtractDomains(unittest.TestCase):
    """Test domain extraction from settings structures."""

    def test_extract_from_allow_section(self):
        """Test extraction from permissions.allow."""
        settings = {'permissions': {'allow': ['WebFetch(example.com)', 'Bash(ls)', 'WebFetch(api.test.com)']}}
        domains = extract_webfetch_domains(settings)
        self.assertEqual(sorted(domains), ['api.test.com', 'example.com'])

    def test_extract_from_deny_section(self):
        """Test extraction from permissions.deny requires explicit section='deny'."""
        settings = {'permissions': {'deny': ['WebFetch(blocked.com)']}}
        # Default section='allow' returns empty for deny-only settings
        self.assertEqual(extract_webfetch_domains(settings), [])
        # Explicit section='deny' returns deny-listed domains
        self.assertEqual(extract_webfetch_domains(settings, section='deny'), ['blocked.com'])
        # section='all' returns both
        self.assertEqual(extract_webfetch_domains(settings, section='all'), ['blocked.com'])

    def test_extract_empty_settings(self):
        """Test extraction from empty settings."""
        self.assertEqual(extract_webfetch_domains({}), [])
        self.assertEqual(extract_webfetch_domains({'permissions': {}}), [])


class TestExtractBySection(unittest.TestCase):
    """Test extract_webfetch_domains_by_section for allow/deny tracking."""

    def test_separates_allow_and_deny(self):
        """Test that allow and deny domains are tracked separately."""
        settings = {
            'permissions': {
                'allow': ['WebFetch(good.com)', 'WebFetch(safe.org)'],
                'deny': ['WebFetch(blocked.com)', 'WebFetch(bad.io)'],
            },
        }
        result = extract_webfetch_domains_by_section(settings)
        self.assertEqual(sorted(result['allow']), ['good.com', 'safe.org'])
        self.assertEqual(sorted(result['deny']), ['bad.io', 'blocked.com'])

    def test_empty_settings(self):
        """Test empty settings returns empty lists."""
        result = extract_webfetch_domains_by_section({})
        self.assertEqual(result['allow'], [])
        self.assertEqual(result['deny'], [])

    def test_filters_non_webfetch(self):
        """Test that non-WebFetch entries are ignored."""
        settings = {
            'permissions': {
                'allow': ['Bash(ls)', 'WebFetch(example.com)', 'Read(*.md)'],
            },
        }
        result = extract_webfetch_domains_by_section(settings)
        self.assertEqual(result['allow'], ['example.com'])
        self.assertEqual(result['deny'], [])


class TestAnalyzeDenyTracking(unittest.TestCase):
    """Test that analyze command tracks denied domains separately."""

    def _write_settings(self, allow: list[str], deny: list[str], tmpdir: str) -> str:
        """Write settings.json with both allow and deny WebFetch permissions."""
        parent = Path(tmpdir)
        parent.mkdir(parents=True, exist_ok=True)
        path = parent / 'settings.json'
        settings = {
            'permissions': {
                'allow': [f'WebFetch({d})' for d in allow],
                'deny': [f'WebFetch({d})' for d in deny],
            },
        }
        path.write_text(json.dumps(settings))
        return str(path)

    def test_denied_domains_reported_separately(self):
        """Test that denied domains appear in denied_domains, not in categories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            global_file = self._write_settings(
                allow=['docs.oracle.com'],
                deny=['malicious.example.com'],
                tmpdir=tmpdir + '/global',
            )
            result = cmd_analyze(Namespace(global_file=global_file, local_file=None))
            self.assertEqual(result['status'], 'success')
            # Denied domain should be in denied_domains
            self.assertIn('malicious.example.com', result['denied_domains'])
            # Only allow-list domain counts toward global_count
            self.assertEqual(result['global_count'], 1)

    def test_deny_from_both_files_combined(self):
        """Test that denied domains from global and local are combined."""
        with tempfile.TemporaryDirectory() as tmpdir:
            global_file = self._write_settings(
                allow=['github.com'],
                deny=['blocked-global.com'],
                tmpdir=tmpdir + '/global',
            )
            local_file = self._write_settings(
                allow=['stackoverflow.com'],
                deny=['blocked-local.com'],
                tmpdir=tmpdir + '/local',
            )
            result = cmd_analyze(Namespace(global_file=global_file, local_file=local_file))
            denied = result['denied_domains']
            self.assertIn('blocked-global.com', denied)
            self.assertIn('blocked-local.com', denied)


class TestAnalyzeEmptyPermissions(unittest.TestCase):
    """Test analyze when settings have no permissions key (#34)."""

    def test_analyze_files_with_no_permissions_key(self):
        """Settings files with just {} should not error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            global_path = Path(tmpdir) / 'global' / 'settings.json'
            global_path.parent.mkdir(parents=True, exist_ok=True)
            global_path.write_text('{}')
            local_path = Path(tmpdir) / 'local' / 'settings.json'
            local_path.parent.mkdir(parents=True, exist_ok=True)
            local_path.write_text('{}')

            result = cmd_analyze(Namespace(global_file=str(global_path), local_file=str(local_path)))
            self.assertEqual(result['status'], 'success')
            self.assertEqual(result['global_count'], 0)
            self.assertEqual(result['local_count'], 0)
            self.assertEqual(result['total_unique'], 0)


class TestCategorizeProtocolPrefix(unittest.TestCase):
    """Test categorize with protocol-prefixed domains (#35)."""

    def test_protocol_prefix_stripped(self):
        """Domains with https:// prefix are normalized — protocol is stripped."""
        categories = categorize_domains(['https://github.com'])
        # https://github.com is recognized as github.com after protocol stripping
        self.assertEqual(len(categories['high_reach']), 1)


# =============================================================================
# Subprocess (Tier 3) tests — CLI plumbing only
# =============================================================================


def run_pw_script(args: list) -> tuple:
    """Run permission_web.py with args and return (stdout, stderr, returncode)."""
    result = run_script(SCRIPT_PATH, *args)
    return result.stdout, result.stderr, result.returncode


class TestMain(unittest.TestCase):
    """Test permission_web.py main entry point (CLI plumbing)."""

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
        self.assertIn('apply', stdout)

    def test_no_add_or_remove(self):
        """Test error when neither --add nor --remove provided."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / 'settings.json'
            path.write_text(json.dumps({'permissions': {'allow': []}}))
            stdout, _, code = run_pw_script(
                [
                    'apply',
                    '--file',
                    str(path),
                ]
            )
            self.assertEqual(code, 0)
            result = parse_toon(stdout)
            self.assertEqual(result['status'], 'error')
            self.assertEqual(result['error_code'], 'INVALID_INPUT')


if __name__ == '__main__':
    unittest.main()
