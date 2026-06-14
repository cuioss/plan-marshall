"""Tests for permission_web.py - WebFetch permission analysis script.

Tier 2 (direct import) tests with 3 subprocess tests for CLI plumbing.
"""

import json
import tempfile
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


def _write_settings_path(domains: list[str], path: str, extra_allow: list[str] | None = None) -> Path:
    """Write a settings.json with WebFetch permissions, returning the Path."""
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


def _write_settings_dir(domains: list[str], tmpdir: str) -> str:
    """Write a settings.json with WebFetch permissions, returning the str path."""
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


def _write_settings_allow_deny(allow: list[str], deny: list[str], tmpdir: str) -> str:
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


# =============================================================================
# categorize_domains (direct import)
# =============================================================================


def test_categorize_major_domain():
    """Test that known major domains are correctly categorized."""
    categories = categorize_domains(['docs.oracle.com', 'maven.apache.org', 'junit.org'])

    assert len(categories['major']) == 3


def test_categorize_high_reach_domain():
    """Test that high-reach platforms are correctly categorized."""
    categories = categorize_domains(['github.com', 'stackoverflow.com'])

    assert len(categories['high_reach']) == 2


def test_categorize_unknown_domain():
    """Test that unknown domains are categorized as unknown."""
    categories = categorize_domains(['my-internal-tool.example.com'])

    assert len(categories['unknown']) == 1


def test_categorize_suspicious_domain():
    """Test that domains with red flags are flagged as suspicious."""
    categories = categorize_domains(['free-downloads-keygen.tk'])

    assert len(categories['suspicious']) == 1
    flags = check_red_flags('free-downloads-keygen.tk')
    assert len(flags) > 0


def test_categorize_universal_wildcard():
    """Test that wildcard is categorized as universal."""
    categories = categorize_domains(['*'])

    assert len(categories['universal']) == 1


def test_categorize_subdomain_of_known():
    """Test that subdomains of known domains inherit parent category."""
    categories = categorize_domains(['api.github.com', 'javadoc.docs.oracle.com'])

    # api.github.com -> high_reach (parent: github.com)
    # javadoc.docs.oracle.com -> major (parent: docs.oracle.com)
    assert len(categories['high_reach']) == 1
    assert len(categories['major']) == 1


def test_categorize_mixed_domains():
    """Test categorization of a mixed set of domains."""
    categories = categorize_domains(['docs.oracle.com', 'github.com', 'unknown.example.com', '*'])

    assert len(categories['major']) == 1
    assert len(categories['high_reach']) == 1
    assert len(categories['unknown']) == 1
    assert len(categories['universal']) == 1


def test_categorize_empty_list():
    """Test categorization of empty domain list."""
    categories = categorize_domains([])

    total = sum(len(v) for v in categories.values())
    assert total == 0


# =============================================================================
# cmd_categorize (direct import)
# =============================================================================


def test_categorize_invalid_json():
    """Test error on invalid JSON input."""
    result = cmd_categorize(Namespace(domains='not-json'))

    assert result['status'] == 'error'


def test_categorize_not_array():
    """Test error when input is not an array."""
    result = cmd_categorize(Namespace(domains='"single-string"'))

    assert result['status'] == 'error'
    assert 'array' in result['error']


# =============================================================================
# categorize edge cases (#42)
# =============================================================================


def test_categorize_domain_star_prefix():
    """Test that 'domain:*' is NOT treated as universal (vestigial format)."""
    categories = categorize_domains(['domain:*'])

    # domain:* is not a valid format — should be classified as unknown, not universal
    assert len(categories['unknown']) == 1
    assert len(categories['universal']) == 0


# =============================================================================
# apply (direct import)
# =============================================================================


def test_add_domains():
    """Test adding domains to a settings file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = _write_settings_path(['existing.com'], f'{tmpdir}/settings.json')

        result = apply_recommendations(path, ['new-domain.com', 'another.org'], [])

        assert result['status'] == 'success'
        assert result['added'] == 2
        assert result['removed'] == 0
        assert 'new-domain.com' in result['final_domains']
        assert 'existing.com' in result['final_domains']


def test_remove_domains():
    """Test removing domains from a settings file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = _write_settings_path(['keep.com', 'remove-me.com'], f'{tmpdir}/settings.json')

        result = apply_recommendations(path, [], ['remove-me.com'])

        assert result['removed'] == 1
        assert 'keep.com' in result['final_domains']
        assert 'remove-me.com' not in result['final_domains']


def test_add_and_remove():
    """Test adding and removing in one call."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = _write_settings_path(['old.com', 'keep.com'], f'{tmpdir}/settings.json')

        result = apply_recommendations(path, ['new.com'], ['old.com'])

        assert result['added'] == 1
        assert result['removed'] == 1
        assert 'new.com' in result['final_domains']
        assert 'old.com' not in result['final_domains']


def test_preserves_non_webfetch_entries():
    """Test that apply does not touch non-WebFetch permissions."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = _write_settings_path(['example.com'], f'{tmpdir}/settings.json', extra_allow=['Bash(ls)'])

        apply_recommendations(path, ['new.com'], [])

        settings = json.loads(path.read_text())
        assert 'Bash(ls)' in settings['permissions']['allow']


def test_no_duplicate_add():
    """Test that adding an already-existing domain doesn't duplicate."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = _write_settings_path(['exists.com'], f'{tmpdir}/settings.json')

        result = apply_recommendations(path, ['exists.com'], [])

        assert result['added'] == 0


def test_missing_file():
    """Test error when file does not exist."""
    result = apply_recommendations(Path('/nonexistent/settings.json'), ['example.com'], [])

    assert result['status'] == 'error'
    assert result['error_code'] == 'NOT_FOUND'


def test_apply_invalid_json_in_file():
    """Test apply with a settings file containing invalid JSON."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write('not valid json{{{')
        f.flush()

        result = apply_recommendations(Path(f.name), ['example.com'], [])

        assert result['status'] == 'error'
        assert result['error_code'] == 'PARSE_ERROR'


# =============================================================================
# apply extended edge cases (#43)
# =============================================================================


def test_remove_nonexistent_domain_is_noop():
    """Removing a domain that doesn't exist should be a graceful no-op."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / 'settings.json'
        path.write_text(json.dumps({'permissions': {'allow': ['WebFetch(keep.com)']}}))

        result = apply_recommendations(path, [], ['does-not-exist.com'])

        assert result['status'] == 'success'
        assert result['removed'] == 0
        assert 'keep.com' in result['final_domains']


# =============================================================================
# apply add and remove same domain (#33)
# =============================================================================


def test_add_and_remove_same_domain():
    """Adding and removing the same domain — remove should win."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / 'settings.json'
        path.write_text(json.dumps({'permissions': {'allow': ['WebFetch(target.com)']}}))

        result = apply_recommendations(path, ['target.com'], ['target.com'])

        assert result['status'] == 'success'
        assert 'target.com' not in result['final_domains']


# =============================================================================
# analyze (direct import)
# =============================================================================


def test_analyze_both_files():
    """Test analysis of both global and local settings."""
    with tempfile.TemporaryDirectory() as tmpdir:
        global_file = _write_settings_dir(['docs.oracle.com', 'github.com', 'unknown.example.com'], tmpdir + '/global')
        local_file = _write_settings_dir(['github.com', 'my-project-docs.com'], tmpdir + '/local')

        result = cmd_analyze(Namespace(global_file=global_file, local_file=local_file))

        assert result['status'] == 'success'
        assert result['global_count'] == 3
        assert result['local_count'] == 2
        assert result['total_unique'] == 4
        assert 'github.com' in result['duplicates']
        assert result['statistics']['domains_analyzed'] == 4
        assert result['statistics']['files_read'] == 2


def test_analyze_with_universal_wildcard():
    """Test analysis detects universal wildcard redundancy."""
    with tempfile.TemporaryDirectory() as tmpdir:
        global_file = _write_settings_dir(['*', 'docs.oracle.com', 'github.com'], tmpdir)

        result = cmd_analyze(Namespace(global_file=global_file, local_file=None))

        # docs.oracle.com and github.com are redundant due to wildcard
        assert result['statistics']['redundant_found'] > 0


def test_analyze_missing_file():
    """Test analysis handles missing files gracefully."""
    result = cmd_analyze(Namespace(global_file='/nonexistent/settings.json', local_file=None))

    assert result['status'] == 'success'
    assert result['statistics'].get('global_missing')


def test_analyze_invalid_json_file():
    """Test analysis reports invalid JSON in settings file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write('not valid json{{{')
        f.flush()

        result = cmd_analyze(Namespace(global_file=f.name, local_file=None))

        assert result['status'] == 'error'
        assert 'Invalid JSON' in result['error']


def test_analyze_generates_recommendations():
    """Test that analysis generates actionable recommendations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        global_file = _write_settings_dir([], tmpdir + '/global')
        local_file = _write_settings_dir(['docs.oracle.com', 'unknown-site.xyz'], tmpdir + '/local')

        result = cmd_analyze(Namespace(global_file=global_file, local_file=local_file))

        # Should have at least a move_to_global rec for docs.oracle.com
        # and a research rec for unknown-site.xyz
        actions = [r['action'] for r in result['recommendations']]
        assert 'move_to_global' in actions
        assert 'research' in actions


# =============================================================================
# find_redundant (direct import)
# =============================================================================


def test_subdomain_redundancy():
    """Test that api.github.com is redundant when github.com is present."""
    result = find_redundant(['github.com', 'api.github.com', 'docs.oracle.com'])

    assert 'api.github.com' in result['subdomain_redundant']
    assert 'github.com' not in result['subdomain_redundant']
    assert 'docs.oracle.com' not in result['subdomain_redundant']


def test_www_prefix_redundancy():
    """Test that www.github.com is redundant when github.com is present."""
    result = find_redundant(['github.com', 'www.github.com'])

    assert 'www.github.com' in result['subdomain_redundant']
    assert 'github.com' not in result['subdomain_redundant']


def test_no_redundancy_for_different_domains():
    """Test that unrelated domains are not flagged as redundant."""
    result = find_redundant(['github.com', 'gitlab.com'])

    assert result['subdomain_redundant'] == []


def test_universal_wildcard_makes_all_redundant():
    """Test that wildcard makes all specific domains redundant."""
    result = find_redundant(['*', 'github.com', 'docs.oracle.com'])

    assert sorted(result['universal_redundant']) == ['docs.oracle.com', 'github.com']


# =============================================================================
# analyze with missing local file
# =============================================================================


def test_analyze_missing_local_file():
    """Test analysis handles missing local file gracefully."""
    result = cmd_analyze(Namespace(global_file=None, local_file='/nonexistent/local-settings.json'))

    assert result['status'] == 'success'
    assert result['statistics'].get('local_missing')


# =============================================================================
# domain extraction from settings structures
# =============================================================================


def test_extract_from_allow_section():
    """Test extraction from permissions.allow."""
    settings = {'permissions': {'allow': ['WebFetch(example.com)', 'Bash(ls)', 'WebFetch(api.test.com)']}}

    domains = extract_webfetch_domains(settings)

    assert sorted(domains) == ['api.test.com', 'example.com']


def test_extract_from_deny_section():
    """Test extraction from permissions.deny requires explicit section='deny'."""
    settings = {'permissions': {'deny': ['WebFetch(blocked.com)']}}

    # Default section='allow' returns empty for deny-only settings
    assert extract_webfetch_domains(settings) == []
    # Explicit section='deny' returns deny-listed domains
    assert extract_webfetch_domains(settings, section='deny') == ['blocked.com']
    # section='all' returns both
    assert extract_webfetch_domains(settings, section='all') == ['blocked.com']


def test_extract_empty_settings():
    """Test extraction from empty settings."""
    assert extract_webfetch_domains({}) == []
    assert extract_webfetch_domains({'permissions': {}}) == []


# =============================================================================
# extract_webfetch_domains_by_section for allow/deny tracking
# =============================================================================


def test_separates_allow_and_deny():
    """Test that allow and deny domains are tracked separately."""
    settings = {
        'permissions': {
            'allow': ['WebFetch(good.com)', 'WebFetch(safe.org)'],
            'deny': ['WebFetch(blocked.com)', 'WebFetch(bad.io)'],
        },
    }

    result = extract_webfetch_domains_by_section(settings)

    assert sorted(result['allow']) == ['good.com', 'safe.org']
    assert sorted(result['deny']) == ['bad.io', 'blocked.com']


def test_extract_by_section_empty_settings():
    """Test empty settings returns empty lists."""
    result = extract_webfetch_domains_by_section({})

    assert result['allow'] == []
    assert result['deny'] == []


def test_filters_non_webfetch():
    """Test that non-WebFetch entries are ignored."""
    settings = {
        'permissions': {
            'allow': ['Bash(ls)', 'WebFetch(example.com)', 'Read(*.md)'],
        },
    }

    result = extract_webfetch_domains_by_section(settings)

    assert result['allow'] == ['example.com']
    assert result['deny'] == []


# =============================================================================
# analyze command deny tracking
# =============================================================================


def test_denied_domains_reported_separately():
    """Test that denied domains appear in denied_domains, not in categories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        global_file = _write_settings_allow_deny(
            allow=['docs.oracle.com'],
            deny=['malicious.example.com'],
            tmpdir=tmpdir + '/global',
        )

        result = cmd_analyze(Namespace(global_file=global_file, local_file=None))

        assert result['status'] == 'success'
        assert 'malicious.example.com' in result['denied_domains']
        assert result['global_count'] == 1


def test_deny_from_both_files_combined():
    """Test that denied domains from global and local are combined."""
    with tempfile.TemporaryDirectory() as tmpdir:
        global_file = _write_settings_allow_deny(
            allow=['github.com'],
            deny=['blocked-global.com'],
            tmpdir=tmpdir + '/global',
        )
        local_file = _write_settings_allow_deny(
            allow=['stackoverflow.com'],
            deny=['blocked-local.com'],
            tmpdir=tmpdir + '/local',
        )

        result = cmd_analyze(Namespace(global_file=global_file, local_file=local_file))

        denied = result['denied_domains']
        assert 'blocked-global.com' in denied
        assert 'blocked-local.com' in denied


# =============================================================================
# analyze when settings have no permissions key (#34)
# =============================================================================


def test_analyze_files_with_no_permissions_key():
    """Settings files with just {} should not error."""
    with tempfile.TemporaryDirectory() as tmpdir:
        global_path = Path(tmpdir) / 'global' / 'settings.json'
        global_path.parent.mkdir(parents=True, exist_ok=True)
        global_path.write_text('{}')
        local_path = Path(tmpdir) / 'local' / 'settings.json'
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_text('{}')

        result = cmd_analyze(Namespace(global_file=str(global_path), local_file=str(local_path)))

        assert result['status'] == 'success'
        assert result['global_count'] == 0
        assert result['local_count'] == 0
        assert result['total_unique'] == 0


# =============================================================================
# categorize with protocol-prefixed domains (#35)
# =============================================================================


def test_protocol_prefix_stripped():
    """Domains with https:// prefix are normalized — protocol is stripped."""
    categories = categorize_domains(['https://github.com'])

    # https://github.com is recognized as github.com after protocol stripping
    assert len(categories['high_reach']) == 1


# =============================================================================
# Subprocess (Tier 3) tests — CLI plumbing only
# =============================================================================


def run_pw_script(args: list) -> tuple:
    """Run permission_web.py with args and return (stdout, stderr, returncode)."""
    result = run_script(SCRIPT_PATH, *args)
    return result.stdout, result.stderr, result.returncode


def test_no_subcommand():
    """Test error when no subcommand provided."""
    _, stderr, code = run_pw_script([])

    assert code != 0


def test_help():
    """Test help output."""
    stdout, _, code = run_pw_script(['--help'])

    assert code == 0
    assert 'analyze' in stdout
    assert 'categorize' in stdout
    assert 'apply' in stdout


def test_no_add_or_remove():
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

        assert code == 0
        result = parse_toon(stdout)
        assert result['status'] == 'error'
        assert result['error_code'] == 'INVALID_INPUT'
