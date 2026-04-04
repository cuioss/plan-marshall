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
        self.assertEqual(result['status'], 'error')

    def test_categorize_not_array(self):
        """Test error when input is not an array."""
        stdout, _, code = run_pw_script(['categorize', '--domains', '"single-string"'])
        self.assertEqual(code, 1)
        result = parse_toon(stdout)
        self.assertEqual(result['status'], 'error')
        self.assertIn('array', result['error'])


class TestCategorizeEdgeCases(unittest.TestCase):
    """Test edge cases for categorize (#42)."""

    def test_categorize_domain_star_prefix(self):
        """Test that 'domain:*' is NOT treated as universal (vestigial format)."""
        domains = ['domain:*']
        stdout, _, code = run_pw_script(['categorize', '--domains', json.dumps(domains)])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        # domain:* is not a valid format — should be classified as unknown, not universal
        self.assertEqual(result['categories']['unknown'], 1)
        self.assertEqual(result['categories']['universal'], 0)


class TestApplyEdgeCasesExtended(unittest.TestCase):
    """Extended edge case tests for apply (#43)."""

    def _write_settings(self, domains: list[str], path: str) -> str:
        """Write a settings.json with WebFetch permissions."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        settings = {
            'permissions': {
                'allow': [f'WebFetch({d})' for d in domains],
            },
        }
        p.write_text(json.dumps(settings))
        return str(p)

    def test_remove_nonexistent_domain_is_noop(self):
        """Removing a domain that doesn't exist should be a graceful no-op."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_settings(['keep.com'], f'{tmpdir}/settings.json')
            stdout, _, code = run_pw_script(
                [
                    'apply',
                    '--file',
                    path,
                    '--remove',
                    json.dumps(['does-not-exist.com']),
                ]
            )
            self.assertEqual(code, 0)
            result = parse_toon(stdout)
            self.assertEqual(result['status'], 'success')
            self.assertEqual(result['removed'], 0)
            self.assertIn('keep.com', result['final_domains'])


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
            local_file = self._write_settings(['github.com', 'my-project-docs.com'], tmpdir + '/local')

            stdout, _, code = run_pw_script(
                [
                    'analyze',
                    '--global-file',
                    global_file,
                    '--local-file',
                    local_file,
                ]
            )
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
            global_file = self._write_settings(['*', 'docs.oracle.com', 'github.com'], tmpdir)
            stdout, _, code = run_pw_script(
                [
                    'analyze',
                    '--global-file',
                    global_file,
                ]
            )
            self.assertEqual(code, 0)
            result = parse_toon(stdout)
            # docs.oracle.com and github.com are redundant due to wildcard
            self.assertGreater(result['statistics']['redundant_found'], 0)

    def test_analyze_missing_file(self):
        """Test analysis handles missing files gracefully."""
        stdout, _, code = run_pw_script(
            [
                'analyze',
                '--global-file',
                '/nonexistent/settings.json',
            ]
        )
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        self.assertEqual(result['status'], 'success')
        self.assertTrue(result['statistics'].get('global_missing'))

    def test_analyze_invalid_json_file(self):
        """Test analysis reports invalid JSON in settings file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('not valid json{{{')
            f.flush()
            stdout, _, code = run_pw_script(
                [
                    'analyze',
                    '--global-file',
                    f.name,
                ]
            )
            self.assertEqual(code, 1)
            result = parse_toon(stdout)
            self.assertEqual(result['status'], 'error')
            self.assertIn('Invalid JSON', result['error'])

    def test_analyze_generates_recommendations(self):
        """Test that analysis generates actionable recommendations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            global_file = self._write_settings([], tmpdir + '/global')
            local_file = self._write_settings(['docs.oracle.com', 'unknown-site.xyz'], tmpdir + '/local')

            stdout, _, code = run_pw_script(
                [
                    'analyze',
                    '--global-file',
                    global_file,
                    '--local-file',
                    local_file,
                ]
            )
            self.assertEqual(code, 0)
            result = parse_toon(stdout)
            # Should have at least a move_to_global rec for docs.oracle.com
            # and a research rec for unknown-site.xyz
            actions = [r['action'] for r in result['recommendations']]
            self.assertIn('move_to_global', actions)
            self.assertIn('research', actions)


class TestFindRedundant(unittest.TestCase):
    """Test find_redundant for subdomain and www. detection."""

    def test_subdomain_redundancy(self):
        """Test that api.github.com is redundant when github.com is present."""
        from permission_web import find_redundant  # type: ignore[import-not-found]

        result = find_redundant(['github.com', 'api.github.com', 'docs.oracle.com'])
        self.assertIn('api.github.com', result['subdomain_redundant'])
        self.assertNotIn('github.com', result['subdomain_redundant'])
        self.assertNotIn('docs.oracle.com', result['subdomain_redundant'])

    def test_www_prefix_redundancy(self):
        """Test that www.github.com is redundant when github.com is present."""
        from permission_web import find_redundant  # type: ignore[import-not-found]

        result = find_redundant(['github.com', 'www.github.com'])
        self.assertIn('www.github.com', result['subdomain_redundant'])
        self.assertNotIn('github.com', result['subdomain_redundant'])

    def test_no_redundancy_for_different_domains(self):
        """Test that unrelated domains are not flagged as redundant."""
        from permission_web import find_redundant  # type: ignore[import-not-found]

        result = find_redundant(['github.com', 'gitlab.com'])
        self.assertEqual(result['subdomain_redundant'], [])

    def test_universal_wildcard_makes_all_redundant(self):
        """Test that wildcard makes all specific domains redundant."""
        from permission_web import find_redundant  # type: ignore[import-not-found]

        result = find_redundant(['*', 'github.com', 'docs.oracle.com'])
        self.assertEqual(sorted(result['universal_redundant']), ['docs.oracle.com', 'github.com'])


class TestAnalyzeMissingLocalFile(unittest.TestCase):
    """Test analyze with missing local file specifically."""

    def test_analyze_missing_local_file(self):
        """Test analysis handles missing local file gracefully."""
        stdout, _, code = run_pw_script(
            [
                'analyze',
                '--local-file',
                '/nonexistent/local-settings.json',
            ]
        )
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        self.assertEqual(result['status'], 'success')
        self.assertTrue(result['statistics'].get('local_missing'))


class TestAnalyzeExtractDomains(unittest.TestCase):
    """Test domain extraction from settings structures."""

    def test_extract_from_allow_section(self):
        """Test extraction from permissions.allow."""
        from permission_web import extract_webfetch_domains  # type: ignore[import-not-found]

        settings = {'permissions': {'allow': ['WebFetch(example.com)', 'Bash(ls)', 'WebFetch(api.test.com)']}}
        domains = extract_webfetch_domains(settings)
        self.assertEqual(sorted(domains), ['api.test.com', 'example.com'])

    def test_extract_from_deny_section(self):
        """Test extraction from permissions.deny requires explicit section='deny'."""
        from permission_web import extract_webfetch_domains  # type: ignore[import-not-found]

        settings = {'permissions': {'deny': ['WebFetch(blocked.com)']}}
        # Default section='allow' returns empty for deny-only settings
        self.assertEqual(extract_webfetch_domains(settings), [])
        # Explicit section='deny' returns deny-listed domains
        self.assertEqual(extract_webfetch_domains(settings, section='deny'), ['blocked.com'])
        # section='all' returns both
        self.assertEqual(extract_webfetch_domains(settings, section='all'), ['blocked.com'])

    def test_extract_empty_settings(self):
        """Test extraction from empty settings."""
        from permission_web import extract_webfetch_domains  # type: ignore[import-not-found]

        self.assertEqual(extract_webfetch_domains({}), [])
        self.assertEqual(extract_webfetch_domains({'permissions': {}}), [])


class TestExtractBySection(unittest.TestCase):
    """Test extract_webfetch_domains_by_section for allow/deny tracking."""

    def test_separates_allow_and_deny(self):
        """Test that allow and deny domains are tracked separately."""
        from permission_web import extract_webfetch_domains_by_section  # type: ignore[import-not-found]

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
        from permission_web import extract_webfetch_domains_by_section  # type: ignore[import-not-found]

        result = extract_webfetch_domains_by_section({})
        self.assertEqual(result['allow'], [])
        self.assertEqual(result['deny'], [])

    def test_filters_non_webfetch(self):
        """Test that non-WebFetch entries are ignored."""
        from permission_web import extract_webfetch_domains_by_section  # type: ignore[import-not-found]

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
            stdout, _, code = run_pw_script(
                [
                    'analyze',
                    '--global-file',
                    global_file,
                ]
            )
            self.assertEqual(code, 0)
            result = parse_toon(stdout)
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
            stdout, _, code = run_pw_script(
                [
                    'analyze',
                    '--global-file',
                    global_file,
                    '--local-file',
                    local_file,
                ]
            )
            self.assertEqual(code, 0)
            result = parse_toon(stdout)
            denied = result['denied_domains']
            self.assertIn('blocked-global.com', denied)
            self.assertIn('blocked-local.com', denied)


class TestApply(unittest.TestCase):
    """Test permission_web.py apply subcommand."""

    def _write_settings(self, domains: list[str], path: str) -> str:
        """Write a settings.json with WebFetch permissions."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        settings = {
            'permissions': {
                'allow': [f'WebFetch({d})' for d in domains] + ['Bash(ls)'],
            },
        }
        p.write_text(json.dumps(settings))
        return str(p)

    def test_add_domains(self):
        """Test adding domains to a settings file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_settings(['existing.com'], f'{tmpdir}/settings.json')
            stdout, _, code = run_pw_script(
                [
                    'apply',
                    '--file',
                    path,
                    '--add',
                    json.dumps(['new-domain.com', 'another.org']),
                ]
            )
            self.assertEqual(code, 0)
            result = parse_toon(stdout)
            self.assertEqual(result['status'], 'success')
            self.assertEqual(result['added'], 2)
            self.assertEqual(result['removed'], 0)
            self.assertIn('new-domain.com', result['final_domains'])
            self.assertIn('existing.com', result['final_domains'])

    def test_remove_domains(self):
        """Test removing domains from a settings file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_settings(['keep.com', 'remove-me.com'], f'{tmpdir}/settings.json')
            stdout, _, code = run_pw_script(
                [
                    'apply',
                    '--file',
                    path,
                    '--remove',
                    json.dumps(['remove-me.com']),
                ]
            )
            self.assertEqual(code, 0)
            result = parse_toon(stdout)
            self.assertEqual(result['removed'], 1)
            self.assertIn('keep.com', result['final_domains'])
            self.assertNotIn('remove-me.com', result['final_domains'])

    def test_add_and_remove(self):
        """Test adding and removing in one call."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_settings(['old.com', 'keep.com'], f'{tmpdir}/settings.json')
            stdout, _, code = run_pw_script(
                [
                    'apply',
                    '--file',
                    path,
                    '--add',
                    json.dumps(['new.com']),
                    '--remove',
                    json.dumps(['old.com']),
                ]
            )
            self.assertEqual(code, 0)
            result = parse_toon(stdout)
            self.assertEqual(result['added'], 1)
            self.assertEqual(result['removed'], 1)
            self.assertIn('new.com', result['final_domains'])
            self.assertNotIn('old.com', result['final_domains'])

    def test_preserves_non_webfetch_entries(self):
        """Test that apply does not touch non-WebFetch permissions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_settings(['example.com'], f'{tmpdir}/settings.json')
            run_pw_script(
                [
                    'apply',
                    '--file',
                    path,
                    '--add',
                    json.dumps(['new.com']),
                ]
            )
            # Re-read and verify Bash(ls) is still there
            settings = json.loads(Path(path).read_text())
            self.assertIn('Bash(ls)', settings['permissions']['allow'])

    def test_no_duplicate_add(self):
        """Test that adding an already-existing domain doesn't duplicate."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_settings(['exists.com'], f'{tmpdir}/settings.json')
            stdout, _, code = run_pw_script(
                [
                    'apply',
                    '--file',
                    path,
                    '--add',
                    json.dumps(['exists.com']),
                ]
            )
            self.assertEqual(code, 0)
            result = parse_toon(stdout)
            self.assertEqual(result['added'], 0)

    def test_missing_file(self):
        """Test error when file does not exist."""
        stdout, _, code = run_pw_script(
            [
                'apply',
                '--file',
                '/nonexistent/settings.json',
                '--add',
                json.dumps(['example.com']),
            ]
        )
        self.assertEqual(code, 1)
        result = parse_toon(stdout)
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['error_code'], 'NOT_FOUND')

    def test_no_add_or_remove(self):
        """Test error when neither --add nor --remove provided."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_settings([], f'{tmpdir}/settings.json')
            stdout, _, code = run_pw_script(
                [
                    'apply',
                    '--file',
                    path,
                ]
            )
            self.assertEqual(code, 1)
            result = parse_toon(stdout)
            self.assertEqual(result['status'], 'error')
            self.assertEqual(result['error_code'], 'INVALID_INPUT')

    def test_invalid_json_add(self):
        """Test error on invalid JSON for --add."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_settings([], f'{tmpdir}/settings.json')
            stdout, _, code = run_pw_script(
                [
                    'apply',
                    '--file',
                    path,
                    '--add',
                    'not-json',
                ]
            )
            self.assertEqual(code, 1)
            result = parse_toon(stdout)
            self.assertEqual(result['error_code'], 'INVALID_INPUT')


class TestApplyAddAndRemoveSameDomain(unittest.TestCase):
    """Test apply when a domain is in both --add and --remove (#33)."""

    def test_add_and_remove_same_domain(self):
        """Adding and removing the same domain — remove should win."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / 'settings.json'
            path.write_text(json.dumps({'permissions': {'allow': ['WebFetch(target.com)']}}))
            stdout, _, code = run_pw_script(
                [
                    'apply',
                    '--file',
                    str(path),
                    '--add',
                    json.dumps(['target.com']),
                    '--remove',
                    json.dumps(['target.com']),
                ]
            )
            self.assertEqual(code, 0)
            result = parse_toon(stdout)
            self.assertEqual(result['status'], 'success')
            # Domain was removed, add should not re-add it (add skips entries in remove set)
            self.assertNotIn('target.com', result['final_domains'])


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

            stdout, _, code = run_pw_script(
                [
                    'analyze',
                    '--global-file',
                    str(global_path),
                    '--local-file',
                    str(local_path),
                ]
            )
            self.assertEqual(code, 0)
            result = parse_toon(stdout)
            self.assertEqual(result['status'], 'success')
            self.assertEqual(result['global_count'], 0)
            self.assertEqual(result['local_count'], 0)
            self.assertEqual(result['total_unique'], 0)


class TestCategorizeProtocolPrefix(unittest.TestCase):
    """Test categorize with protocol-prefixed domains (#35)."""

    def test_protocol_prefix_stripped(self):
        """Domains with https:// prefix are normalized — protocol is stripped before categorization."""
        domains = ['https://github.com']
        stdout, _, code = run_pw_script(['categorize', '--domains', json.dumps(domains)])
        self.assertEqual(code, 0)
        result = parse_toon(stdout)
        # https://github.com is recognized as github.com after protocol stripping
        self.assertEqual(result['categories']['high_reach'], 1)


class TestApplyEdgeCases(unittest.TestCase):
    """Test permission_web.py apply edge cases."""

    def test_apply_invalid_json_in_file(self):
        """Test apply with a settings file containing invalid JSON."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('not valid json{{{')
            f.flush()
            stdout, _, code = run_pw_script(
                [
                    'apply',
                    '--file',
                    f.name,
                    '--add',
                    json.dumps(['example.com']),
                ]
            )
            self.assertEqual(code, 1)
            result = parse_toon(stdout)
            self.assertEqual(result['status'], 'error')
            self.assertEqual(result['error_code'], 'PARSE_ERROR')

    def test_apply_invalid_json_remove(self):
        """Test error on invalid JSON for --remove."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / 'settings.json'
            path.write_text(json.dumps({'permissions': {'allow': []}}))
            stdout, _, code = run_pw_script(
                [
                    'apply',
                    '--file',
                    str(path),
                    '--remove',
                    'not-json',
                ]
            )
            self.assertEqual(code, 1)
            result = parse_toon(stdout)
            self.assertEqual(result['status'], 'error')


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
        self.assertIn('apply', stdout)


if __name__ == '__main__':
    unittest.main()
